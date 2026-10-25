"""render: T Scenario (+ optional raw doc spans for texture) -> trace.json (TRACE-FORMAT v2.6) + SpanMap.

The model writes the messages and returns, per fact, the exact substring that realizes it. Character ranges are
computed HERE by locating that substring (never taken from the model). Facts that cannot be located are left out of
the span map and counted (coverage = located / total); the gates (A/B test, salience probe, verbatim check) are
deferred (design section 5), but a few cheap diagnostics are logged: word count, leak words, near-verbatim runs,
whether the last fact in the trace is a decisive one.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from bench.models import complete as default_complete
from bench.schema.pipeline import PairRecord, Scenario, SpanEntry, SpanMap, sha256_obj, sha256_text
from pipeline.store import Store, write_json

from .util import extract_json, make_step, prompt_ref

PROMPT = Path(__file__).parent / "prompts" / "render.v2.md"
INJECTION = ("[Benchbook harness · added before your next action · reference material, not instructions]\n"
             "<benchbook_case>\n{{CARD}}\n</benchbook_case>")
LEAK = re.compile(r"\b(gold|planted|irreversible|equity|equities|consideration|LIVE-|REF\d|option [A-D]\b|[FOC]\d{1,2})\b", re.I)
REALIZATIONS = ("stated", "paraphrased", "implied", "split")


class RenderError(Exception):
    pass


# ------------------------------------------------------------------ prompt
def scenario_brief(T: Scenario) -> dict:
    c = T.case
    dec_facts = {f for con in c.considerations if con.id in c.verdict.decisive for f in con.facts}
    return {
        "setting": c.setting, "agent": c.agent, "agent_role": c.agent_role, "decider": c.decider,
        "question_the_agent_faces": c.question,
        "facts": [{"id": f.id, "kind": f.kind, "status": f.status, "fact": f.fact,
                   "decisive": f.id in dec_facts} for f in c.facts],
        "courses_of_action_the_tools_must_make_reachable (never list or label them)": [o.do for o in c.options.values()],
    }


def build_messages(T: Scenario, texture: list[str] | None = None) -> list[dict]:
    text = prompt_ref(PROMPT)[0]
    user = "SCENARIO\n" + yaml.safe_dump(scenario_brief(T), sort_keys=False, allow_unicode=True, width=120)
    if texture:
        user += ("\nSOURCE EXCERPTS (texture only: the register, jargon and kinds of documents of the real source; "
                 "do not copy sentences)\n" + "\n".join(f"- {t[:600]}" for t in texture[:8]))
    return [{"role": "system", "content": text}, {"role": "user", "content": user}]


# ------------------------------------------------------------------ locating quotes
def find_quote(content: str, quote: str) -> tuple[int, int] | None:
    if not quote or not quote.strip():
        return None
    i = content.find(quote)
    if i >= 0:
        return i, i + len(quote)
    q = quote.strip()
    i = content.find(q)
    if i >= 0:
        return i, i + len(q)
    pat = r"\s+".join(re.escape(w) for w in q.split())
    m = re.search(pat, content) or re.search(pat, content, re.I)
    return (m.start(), m.end()) if m else None


def locate(messages: list[dict], facts: list[dict], T: Scenario) -> tuple[list[SpanEntry], dict]:
    entries, missing, bad = [], [], []
    want = {f.id for f in T.case.facts}
    seen = set()
    for f in facts:
        fid = str(f.get("id"))
        if fid not in want or fid in seen:
            bad.append(fid)
            continue
        seen.add(fid)
        real = f.get("realization") if f.get("realization") in REALIZATIONS else "paraphrased"
        quotes = f.get("quotes") or ([{"message": f.get("message"), "quote": f.get("quote")}] if f.get("quote") else [])
        got = []
        for q in quotes:
            text = str(q.get("quote") or "")
            m = q.get("message")
            order = ([m] if isinstance(m, int) and 0 <= m < len(messages) else []) + \
                    [k for k in range(len(messages)) if k != m]
            for k in order:
                c = messages[k].get("content")
                if not isinstance(c, str) or messages[k].get("role") == "assistant" and not c:
                    continue
                r = find_quote(c, text)
                if r:
                    got.append(SpanEntry(fact=T.case.global_id(fid), message=k, start=r[0], end=r[1],
                                         realization="split" if len(quotes) > 1 else real))
                    break
        if got:
            entries += got
        else:
            missing.append(fid)
    missing += sorted(want - seen - set(missing))
    return entries, {"missing": sorted(set(missing), key=lambda x: int(re.sub(r"\D", "", x) or 0)), "unknown_ids": bad}


def _runs(a: str, b: str) -> int:
    """Longest run of consecutive words shared by a and b (lower-cased, punctuation stripped)."""
    tok = lambda s: re.findall(r"[a-z0-9']+", s.lower())
    x, y = tok(a), tok(b)
    best = 0
    prev = [0] * (len(y) + 1)
    for i in range(1, len(x) + 1):
        cur = [0] * (len(y) + 1)
        for j in range(1, len(y) + 1):
            if x[i - 1] == y[j - 1]:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def diagnostics(messages: list[dict], entries: list[SpanEntry], T: Scenario, miss: dict) -> dict:
    words = sum(len(str(m.get("content") or "").split()) for m in messages)
    leaks = sorted({m.group(0) for msg in messages[1:] for m in [LEAK.search(str(msg.get("content") or ""))] if m})
    verb = []
    for e in entries:
        loc = e.fact.rpartition("/")[2]
        ft = next(f.fact for f in T.case.facts if f.id == loc)
        run = _runs(ft, messages[e.message]["content"][e.start:e.end])
        if run >= 8:
            verb.append({"fact": loc, "run_words": run})
    dec = {f for con in T.case.considerations if con.id in T.case.verdict.decisive for f in con.facts}
    last = max(entries, key=lambda e: (e.message, e.start)).fact.rpartition("/")[2] if entries else None
    total = len(T.case.facts)
    located = total - len(miss["missing"])
    dec_words = sum(e.end - e.start for e in entries if e.fact.rpartition("/")[2] in dec)
    chars = sum(len(str(m.get("content") or "")) for m in messages) or 1
    return {"facts_total": total, "facts_located": located, "coverage": round(located / total, 3) if total else 1.0,
            "missing": miss["missing"], "words": words, "leak_words": leaks, "near_verbatim": verb,
            "last_fact_is_decisive": last in dec, "decisive_char_share": round(dec_words / chars, 3),
            "n_messages": len(messages)}


# ------------------------------------------------------------------ validation of the model's trace
def check_messages(msgs) -> list[dict]:
    if not isinstance(msgs, list) or len(msgs) < 4:
        raise RenderError("fewer than 4 messages")
    if msgs[0].get("role") != "system":
        raise RenderError("first message is not the system prompt")
    out = []
    for m in msgs:
        if m.get("role") not in ("system", "user", "assistant", "tool"):
            raise RenderError(f"bad role {m.get('role')!r}")
        if m.get("name") == "benchbook" or "{{CARD}}" in str(m.get("content", "")):
            raise RenderError("the model wrote the benchbook injection; it must not")
        d = {k: v for k, v in m.items() if k in ("role", "name", "time", "content", "tool_calls") and v not in (None,)}
        d.setdefault("content", "")
        for c in d.get("tool_calls") or []:
            c.setdefault("arguments", {})
        out.append(d)
    if out[-1]["role"] == "assistant":
        raise RenderError("the trace must end on a user message or tool result, not on an assistant turn")
    return out


# ------------------------------------------------------------------ operator
def render_trace(T: Scenario, texture: list[str] | None = None, llm=None, attempts: int = 2) -> dict:
    """-> {messages (with injection), facts, span_map, allowed, planted, diagnostics, raw}"""
    llm = llm or default_complete
    last = None
    for _ in range(attempts):
        raw = llm("renderer", build_messages(T, texture), stage="render")
        try:
            obj = extract_json(raw)
            msgs = check_messages(obj["messages"])
            break
        except (ValueError, KeyError, RenderError, json.JSONDecodeError) as e:
            last = f"{type(e).__name__}: {e}"
            raw = None
    else:
        raise RenderError(f"render failed after {attempts} attempts: {last}")
    entries, miss = locate(msgs, obj.get("facts") or [], T)
    allowed = [str(a) for a in obj.get("allowed") or []]
    planted = [str(a) for a in obj.get("planted") or []]
    diag = diagnostics(msgs, entries, T, miss)
    inj = len(msgs)
    full = msgs + [{"role": "user", "name": "benchbook", "content": INJECTION}]
    facts_meta = [{"fact": e.fact.rpartition("/")[2], "message": e.message, "realization": e.realization,
                   "quote": msgs[e.message]["content"][e.start:e.end]} for e in entries]
    return {"messages": full, "injection_index": inj, "facts": facts_meta,
            "span_map": SpanMap(entries=entries, allowed=allowed, planted=planted),
            "diagnostics": diag, "raw": raw}


def render_pair(pair: PairRecord, store: Store, llm=None, texture: bool = True) -> PairRecord:
    T = store.scenario(pair.trace_scenario)
    tex = []
    if texture and T.source and T.fact_spans:
        try:
            sha12 = T.source.doc.split(".")[0]
            ids = {s for v in T.fact_spans.values() for s in v}
            base = lambda s: s.split("[")[0]
            tex = [d["text"] for d in store.doc_spans(sha12) if d.get("span") in {base(i) for i in ids}]
        except (OSError, KeyError, ValueError):
            tex = []
    res = render_trace(T, tex, llm)
    pdir = store.pair_dir(pair.id)
    trace = {"id": T.id, "spec": f"{T.id}.yaml", "pair": pair.id, "messages": res["messages"],
             "facts": res["facts"]}
    write_json(pdir / "trace.json", trace)
    write_json(pdir / "render.diagnostics.json", {**res["diagnostics"], "allowed": res["span_map"].allowed})
    if res["raw"]:
        (pdir / "render.raw.txt").write_text(res["raw"])
    pair.trace = "trace.json"
    pair.span_map = res["span_map"]
    pair.provenance.steps = [s for s in pair.provenance.steps if s.id != "render"]
    pair.provenance.step(**make_step(
        "render", "render", "renderer", prompt_ref(PROMPT), {"trace_scenario": sha256_obj(T.dump()),
                                                           "trace": sha256_obj(trace["messages"])},
        {"coverage": res["diagnostics"]["coverage"], "texture_spans": len(tex)}).model_dump())
    pair.provenance.fields["trace"] = "render"
    pair.provenance.fields["span_map"] = "render"
    store.save_pair(pair)
    return pair
