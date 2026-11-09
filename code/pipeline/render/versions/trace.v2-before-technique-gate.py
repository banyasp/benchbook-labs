"""render v3: T Scenario -> TraceRecord in the trace store (one per trace scenario; design §8, §7.1).

Options are text in a pre-assigned channel (never a menu), a seeded 50% of traces carry a recommendation, facts are
single-hop (R49). Everything about WHERE things are is located in code from exact substrings the model returns.
Gates (§8.4): (1) every decisive fact and every option located (and in its channel); (2) leak scan: ids, option
labels, menu shape, gold, A parts of every card served with the trace; (3) no person names. 2 re-render tries with the
failure as feedback, then the trace is dropped: saved under data/store/traces/_rejected/<id>/ with
diagnostics.status = "rejected" and diagnostics.reason (never at traces/<id>/, so has_trace() stays False).
"""
from __future__ import annotations

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

import bench.models as _models
from bench.schema import Case
from bench.schema.pipeline import OptionSpan, Scenario, SpanMap, TraceRecord, sha256_obj
from pipeline.store import Store, write_json, write_yaml

from . import channels as chan
from . import gates
from .render import INJECTION, REALIZATIONS, RenderError, check_messages, diagnostics, find_quote, locate
from .util import extract_json, make_step, prompt_ref

PROMPT3 = Path(__file__).parent / "prompts" / "render.v3.md"
MAX_RETRIES = 2                      # re-render tries after the first render (design §8.4)
LLM_TRIES = 4                        # transport-level attempts per call (backoff)
DEFAULT_SEED = 20261027
CHANNEL_ROLES = {"system_scope": ("system",), "operator_message": ("user",), "colleague_message": ("user",),
                 "tool_result": ("tool",), "attached_document": ("tool", "user")}


def refusal_types() -> tuple:
    out = []
    for mod in (_models, _import("datagen.llm")):
        t = getattr(mod, "RefusalError", None) if mod else None
        if isinstance(t, type):
            out.append(t)
    return tuple(out)


def _import(name):
    try:
        import importlib
        return importlib.import_module(name)
    except Exception:
        return None


# ------------------------------------------------------------------ prompt
def brief(T: Scenario, channels: dict[str, str], recommended: str | None) -> dict:
    c = T.case
    dec_facts = {f for con in c.considerations if con.id in c.verdict.decisive for f in con.facts}
    rec = (recommended or "").rpartition("/")[2]
    return {
        "setting": c.setting, "agent": c.agent, "agent_role": c.agent_role, "decider": c.decider,
        "question_the_agent_faces": c.question,
        "facts": [{"id": f.id, "kind": f.kind, "status": f.status, "fact": f.fact, "decisive": f.id in dec_facts}
                  for f in c.facts],
        "courses_of_action (text in the assigned channel; never list, letter or number them)": [
            {"option": oid, "course": o.do, "channel": channels[c.global_id(oid)]} for oid, o in c.options.items()],
        "recommendation": ({"recommend_option": rec, "note": "one person recommends this course, as in rule 6"}
                           if rec else "none: nobody recommends or prefers anything"),
    }


def build_messages(T, channels, recommended, texture=None) -> list[dict]:
    text = prompt_ref(PROMPT3)[0]
    user = "SCENARIO\n" + yaml.safe_dump(brief(T, channels, recommended), sort_keys=False, allow_unicode=True, width=120)
    if texture:
        user += ("\nSOURCE EXCERPTS (texture only: the register, jargon and kinds of documents of the real source; "
                 "do not copy sentences; keep no personal names)\n" + "\n".join(f"- {t[:600]}" for t in texture[:8]))
    return [{"role": "system", "content": text}, {"role": "user", "content": user}]


def texture_for(store: Store, T: Scenario) -> list[str]:
    if not (T.source and T.fact_spans):
        return []
    try:
        sha12 = T.source.doc.split(".")[0]
        ids = {s for v in T.fact_spans.values() for s in v}
        base = lambda s: s.split("[")[0]
        return [d["text"] for d in store.doc_spans(sha12) if d.get("span") in {base(i) for i in ids}]
    except (OSError, KeyError, ValueError):
        return []


# ------------------------------------------------------------------ locating options
def locate_options(msgs: list[dict], items, T: Scenario, channels: dict[str, str]) -> tuple[list[OptionSpan], list[str]]:
    case = T.case
    got: dict[str, OptionSpan] = {}
    for it in items or []:
        if not isinstance(it, dict):
            continue
        oid = str(it.get("option"))
        if oid not in case.options or oid in got:
            continue
        m, q = it.get("message"), str(it.get("quote") or "")
        order = ([m] if isinstance(m, int) and 0 <= m < len(msgs) else []) + [k for k in range(len(msgs)) if k != m]
        for k in order:
            c = msgs[k].get("content")
            if not isinstance(c, str):
                continue
            r = find_quote(c, q)
            if r:
                g = case.global_id(oid)
                got[oid] = OptionSpan(option=g, message=k, start=r[0], end=r[1], channel=channels[g])
                break
    return list(got.values()), [o for o in case.options if o not in got]


def locate_recommendation(msgs, rec, want: str | None, case: Case) -> tuple[dict | None, list[str]]:
    probs = []
    if not want:
        if rec:
            probs.append("a recommendation was written but none is asked for")
        return None, probs
    if not isinstance(rec, dict) or str(rec.get("option")) != want.rpartition("/")[2]:
        return None, [f"the recommendation for {want.rpartition('/')[2]} is missing"]
    q, m = str(rec.get("quote") or ""), rec.get("message")
    order = ([m] if isinstance(m, int) and 0 <= m < len(msgs) else []) + [k for k in range(len(msgs)) if k != m]
    for k in order:
        c = msgs[k].get("content")
        r = find_quote(c, q) if isinstance(c, str) else None
        if r:
            return {"option": want, "message": k, "start": r[0], "end": r[1]}, []
    return None, [f"the recommendation quote for {want.rpartition('/')[2]} was not found in the trace"]


def channel_problems(msgs, spans: list[OptionSpan]) -> list[str]:
    out = []
    for s in spans:
        ok = CHANNEL_ROLES[s.channel]
        role = msgs[s.message].get("role")
        if s.channel == "system_scope" and s.message != 0 or role not in ok:
            out.append(f"{s.option.rpartition('/')[2]} must show up in channel {s.channel} but was placed in message "
                       f"{s.message} (role {role})")
    return out


# ------------------------------------------------------------------ gates
def run_gates(msgs, T: Scenario, entries, miss, opt_spans, opt_missing, rec_probs, ch_probs, cards: list[Case],
              recommended: str | None = None):
    case = T.case
    dec = sorted({f for con in case.considerations if con.id in case.verdict.decisive for f in con.facts})
    dec_missing = [f for f in dec if f in miss["missing"]]
    g1 = {"pass": not (dec_missing or opt_missing or rec_probs or ch_probs), "decisive_missing": dec_missing,
          "options_missing": opt_missing, "recommendation": rec_probs, "channel": ch_probs}
    spans = [(s.option.rpartition("/")[2], s.message, s.start, s.end) for s in opt_spans]
    ids = gates.id_leaks(msgs)
    labels = gates.option_text_leaks(msgs, case)
    menu = gates.menu_problems(msgs, spans, case)
    cardl = gates.card_leaks(msgs, [*cards, case])
    grading = gates.option_grading(msgs, spans, {recommended.rpartition("/")[2]} if recommended else set())
    g2 = {"pass": not (ids or labels or menu or cardl or grading), "option_grading": grading, "ids": ids, "option_labels": labels, "menu": menu,
          "card_a_parts": cardl, "cards_checked": sorted({c.id for c in cards} | {case.id})}
    nm = gates.person_names(msgs)
    g3 = {"pass": not nm, "names": nm}
    return {"located": g1, "leak": g2, "names": g3}


def feedback(g: dict) -> str:
    L = ["Your trace failed these checks. Re-render the whole JSON object, fixing exactly these and keeping the rest."]
    a = g["located"]
    if a["decisive_missing"]:
        L.append(f"- Decisive facts not found by their quote: {a['decisive_missing']}. Quote exact substrings of the content.")
    if a["options_missing"]:
        L.append(f"- Courses of action not found by their quote: {a['options_missing']}. Give one exact quote each.")
    L += [f"- {x}" for x in a["recommendation"] + a["channel"]]
    b = g["leak"]
    if b["ids"]:
        L.append(f"- Forbidden words or ids in the trace: {b['ids']}. Remove them.")
    for x in b["option_labels"]:
        L.append(f"- Course {x['option']} copies the scenario's wording ({x['run_words']} words in a row). Re-express it.")
    L += [f"- Menu shape: {x}. Spread the courses apart, one per sentence, no list." for x in b["menu"]]
    for x in b["option_grading"]:
        L.append(f"- Course {x['option']} is introduced with a directive or graded word (\"{x['word']}\"). Make it a plain "
                 "mention of something that exists or can be done; only the recommended course may be urged.")
    for x in b["card_a_parts"]:
        L.append(f"- Text copied from reference material ({x['part']}): \"{x['run']} ...\". Write it differently.")
    if g["names"]["names"]:
        L.append(f"- Personal names found: {g['names']['names']}. Use roles, titles or handles instead.")
    return "\n".join(L)


# ------------------------------------------------------------------ one trace scenario
class Dropped(Exception):
    def __init__(self, reason, detail=None):
        super().__init__(reason)
        self.reason, self.detail = reason, detail or {}


def call_llm(llm, messages, sleep=time.sleep):
    """llm call with exponential backoff on transport errors; a refusal is not retried."""
    refusals = refusal_types()
    for i in range(LLM_TRIES):
        try:
            return llm("renderer", messages, stage="render")
        except refusals as e:
            raise Dropped("refusal", {"refusal": str(e)[:300]})
        except Exception as e:
            if i == LLM_TRIES - 1:
                raise Dropped("llm_error", {"error": f"{type(e).__name__}: {e}"[:300]})
            sleep(min(60, 2 ** i * 2) + random.random())


def render_trace_v3(T: Scenario, cards: list[Case] | None = None, *, texture: list[str] | None = None, llm=None,
                    seed: int = DEFAULT_SEED, sleep=time.sleep) -> tuple[TraceRecord, dict]:
    """-> (TraceRecord, trace_json). status ok -> gates pass; otherwise diagnostics.status = "rejected" (check it)."""
    llm = llm or _models.complete
    cards = list(cards or [])
    gid = T.case.global_id
    chs, rec, src = chan.resolve(T.id, [gid(o) for o in T.case.options], seed)
    if rec is not None and rec not in chs:
        raise ValueError(f"recommended option {rec} not among the trace's options")
    msgs_in = build_messages(T, chs, rec, texture)
    convo = list(msgs_in)
    last = {"msgs": None, "g": None, "reason": None}
    attempts = []
    for attempt in range(1 + MAX_RETRIES):
        try:
            raw = call_llm(llm, convo, sleep)
        except Dropped as d:
            attempts.append({"attempt": attempt, "dropped": d.reason})
            last.update(reason=d.reason, detail=d.detail)
            break
        try:
            obj = extract_json(raw)
            msgs = check_messages(obj["messages"])
        except (ValueError, KeyError, TypeError, RenderError, json.JSONDecodeError) as e:
            why = f"{type(e).__name__}: {e}"[:200]
            attempts.append({"attempt": attempt, "parse_error": why, "raw_head": raw[:300], "raw_tail": raw[-200:]})
            last.update(reason="unparseable", detail={"error": why})
            convo += [{"role": "assistant", "content": raw[:6000]},
                      {"role": "user", "content": f"Your reply was not a valid trace ({why}). Return the full JSON object only."}]
            continue
        entries, miss = locate(msgs, obj.get("facts") or [], T)
        opt_spans, opt_missing = locate_options(msgs, obj.get("options"), T, chs)
        recspan, rec_probs = locate_recommendation(msgs, obj.get("recommendation"), rec, T.case)
        g = run_gates(msgs, T, entries, miss, opt_spans, opt_missing, rec_probs, channel_problems(msgs, opt_spans), cards, rec)
        ok = all(v["pass"] for v in g.values())
        attempts.append({"attempt": attempt, "pass": ok, **{k: v["pass"] for k, v in g.items()},
                          **({} if ok else {"failures": feedback(g)[:1500]})})
        last.update(msgs=msgs, g=g, obj=obj, entries=entries, miss=miss, opt_spans=opt_spans, recspan=recspan,
                    reason=None if ok else "gates: " + ", ".join(k for k, v in g.items() if not v["pass"]), detail={})
        if ok:
            break
        convo += [{"role": "assistant", "content": raw[:12000]}, {"role": "user", "content": feedback(g)}]
    ok = last["msgs"] is not None and last["reason"] is None
    msgs = last["msgs"] or []
    entries, miss = last.get("entries") or [], last.get("miss") or {"missing": [f.id for f in T.case.facts], "unknown_ids": []}
    diag = diagnostics(msgs, entries, T, miss) if msgs else {}
    if msgs:
        dec = {f for con in T.case.considerations if con.id in T.case.verdict.decisive for f in con.facts}
        w = lambda s: len(s.split())
        dw = sum(w(msgs[e.message]["content"][e.start:e.end]) for e in entries if e.fact.rpartition("/")[2] in dec)
        diag["decisive_word_share"] = round(dw / (diag["words"] or 1), 3)
    diag.update(status="ok" if ok else "rejected", attempts=attempts, channel_source=src,
                n_cards_checked=len(cards), prompt="render.v3")
    if not ok:
        diag["reason"] = last["reason"]
        diag.update(last.get("detail") or {})
        if last["reason"] == "refusal":
            diag["refusal"] = (last.get("detail") or {}).get("refusal", True)
    if ok:
        diag["recommendation_span"] = last["recspan"]
    obj = last.get("obj") or {}
    full = msgs + [{"role": "user", "name": "benchbook", "content": INJECTION}] if msgs else []
    facts_meta = [{"fact": e.fact.rpartition("/")[2], "message": e.message, "realization": e.realization,
                   "quote": msgs[e.message]["content"][e.start:e.end]} for e in entries]
    opts_meta = [{"option": s.option.rpartition("/")[2], "channel": s.channel, "message": s.message,
                  "quote": msgs[s.message]["content"][s.start:s.end]} for s in last.get("opt_spans") or []]
    trace_json = {"id": T.id, "spec": f"{T.id}.yaml", "trace_scenario": T.id, "messages": full, "facts": facts_meta,
                  "options": opts_meta, "recommendation": last.get("recspan")}
    rec_ = TraceRecord(
        trace_scenario=T.id, split=T.split, span_map=SpanMap(
            entries=entries, options=last.get("opt_spans") or [] if ok else [],
            allowed=[str(a) for a in obj.get("allowed") or []] if msgs else []),
        channels=chs, recommended_option=rec, seed=seed, gates=last["g"] or {}, diagnostics=diag)
    rec_.provenance.step(**make_step("render", "render", "renderer", prompt_ref(PROMPT3),
                                     {"trace_scenario": sha256_obj(T.dump()), "trace": sha256_obj(full),
                                      "cards": ",".join(sorted({c.id for c in cards}))},
                                     {"coverage": diag.get("coverage"), "attempts": len(attempts)}).model_dump())
    rec_.provenance.fields["trace"] = "render"
    rec_.provenance.fields["span_map"] = "render"
    return rec_, trace_json


# ------------------------------------------------------------------ store
def cards_for(store: Store, sid: str) -> list[Case]:
    """The cards served with this trace scenario: C of every pair that references it (pair decides)."""
    out, seen = [], set()
    for p in store.active_pairs():
        if (p.trace_ref or p.trace_scenario) == sid and p.case_scenario and p.case_scenario not in seen:
            seen.add(p.case_scenario)
            try:
                out.append(store.scenario(p.case_scenario).case)
            except KeyError:
                pass
    return out


def save(store: Store, rec: TraceRecord, trace_json: dict) -> Path:
    if rec.diagnostics.get("status") == "ok":
        return store.save_trace(rec, trace_json)
    d = store.root / "traces" / "_rejected" / rec.trace_scenario
    write_json(d / rec.trace, trace_json)
    write_yaml(d / "trace.yaml", rec.dump())
    return d / "trace.yaml"


def render_one(store: Store, sid: str, *, cards: list[Case] | None = None, llm=None, seed: int = DEFAULT_SEED,
               texture: bool = True, sleep=time.sleep) -> TraceRecord:
    T = store.scenario(sid)
    cs = cards if cards is not None else cards_for(store, sid)
    rec, tj = render_trace_v3(T, cs, texture=texture_for(store, T) if texture else None, llm=llm, seed=seed, sleep=sleep)
    save(store, rec, tj)
    return rec


def needed(store: Store, skip_rejected: bool = False) -> list[str]:
    ids = []
    for p in store.active_pairs():
        s = p.trace_ref or p.trace_scenario
        if s and not store.has_trace(s) and s not in ids:
            if skip_rejected and (store.root / "traces" / "_rejected" / s / "trace.yaml").exists():
                continue
            ids.append(s)
    return ids


def render_many(store: Store, sids: list[str], *, workers: int = 12, llm=None, seed: int = DEFAULT_SEED,
                sleep=time.sleep, log=None) -> dict[str, TraceRecord | Exception]:
    def one(sid):
        try:
            r = render_one(store, sid, llm=llm, seed=seed, sleep=sleep)
        except Exception as e:                # a bad scenario must not stop the batch
            r = e
        if log:
            log(sid, r)
        return sid, r
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        return dict(ex.map(one, sids))
