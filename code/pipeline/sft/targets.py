"""SFT-building operator, step 2: the target text for one pairs-v1 cell (Peter, 2026-11-12).

Target = the reply documents  F,Q | M_F | K | M_K | applicability | W | V  for X1 with C(X2) served.

    fixed      F,Q (fact_enumeration) and K (consideration_enumeration): X1's recorded gold, verbatim, rendered by code
               (revised arm: K is C''s on X1's facts). Maps, applicability flags, verdict choice / relation / via /
               decisive / flip conditions: the pair gold (pairgold.py), by code.
    writer     Luna (role sft_writer, prompt prompts/writer.v1.md = solve teacher.v4 + amendments) writes the prose:
               mapping notes / roles / assumptions, applicability why, W, verdict course and now, from the full gold.
               Its F and K documents are replaced by the fixed ones; the structure is checked (solve.check.check_reply).
    restate    base Granite (role sft_restater) restates every prose field the writer wrote in its own words; the
               structure is re-emitted by code, so it cannot drift. Gates (Jev): the restated W still supports the gold
               choice; the restated W makes the same argument as the writer's (no significant deviation).
    granite_rs gold-conditioned rejection sampling (the comparison arm): Granite gets the writer's documents through
               applicability as a prefill and writes W and V itself; kept iff the full reply passes check_reply.
    random     (arm random, relation not_governed) W and V come from base Granite WITHOUT the case: the no-case prompt
               for X1, prefilled with the fixed F and K documents; its reasoning and verdict are spliced in after the
               applicability document (relation not_governed, via null). Peter's design, 2026-11-12.

Every target is emitted by `emit()` in one layout (format.v1 style: block keys, one flow mapping per list item).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from bench.models import complete
from harness.settings import HarnessSettings
from pipeline.project.project import gold_for
from pipeline.render.util import prompt_ref
from pipeline.solve.check import check_reply, clean_reply
from pipeline.solve.episode import student_episode
from pipeline.solve.solve import gold_brief, trace_quotes
from pipeline.solve.structure import GoldStructure, local

from .pairgold import Built, pair_gold

HERE = Path(__file__).parent
PROMPTS = HERE / "prompts"          # every prompt of the SFT operator is a file here (console /prompts)
WRITER_PROMPT = PROMPTS / "writer.v1.md"
ORDER = ["fact_enumeration", "fact_mapping", "consideration_enumeration", "consideration_mapping", "applicability",
         "reasoning", "verdict"]
GRANITE = "granite-4.2-8b"


# ============================================================================================== emit (one layout)
BARE = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*$")
YAML_WORDS = {"yes", "no", "true", "false", "null", "on", "off", "y", "n", "~"}


def _scalar(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if BARE.match(s) and s.lower() not in YAML_WORDS:
        return s
    return json.dumps(s, ensure_ascii=False)


def _flow(v) -> str:
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_flow(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_flow(x) for x in v) + "]"
    return _scalar(v)


def _block(k, v, ind: int) -> list[str]:
    pad = "  " * ind
    if isinstance(v, dict):
        if not v:
            return [f"{pad}{k}: {{}}"]
        out = [f"{pad}{k}:"]
        for kk, vv in v.items():
            out += _block(kk, vv, ind + 1)
        return out
    if isinstance(v, list):
        if not v:
            return [f"{pad}{k}: []"]
        if all(not isinstance(x, (dict, list)) and (x is None or BARE.match(str(x))) for x in v):
            return [f"{pad}{k}: {_flow(v)}"]          # id lists
        return [f"{pad}{k}:"] + [f"{pad}  - {_flow(x)}" for x in v]
    return [f"{pad}{k}: {_scalar(v)}"]


def emit(docs: list[dict]) -> str:
    out = []
    for d in docs:
        lines = []
        for k, v in d.items():
            lines += _block(k, v, 0)
        out.append("\n".join(lines))
    return "\n---\n".join(out) + "\n"


def parse_docs(text: str) -> dict[str, dict]:
    """kind -> document. Strict YAML per document; a document that does not parse is left out (the structure check then
    rejects the sample: Granite's own YAML often has unquoted colons)."""
    docs = {}
    for part in re.split(r"(?m)^---+\s*$", clean_reply(text)):
        try:
            d = yaml.safe_load(part)
        except yaml.YAMLError:
            continue
        if isinstance(d, dict) and d.get("kind"):
            docs[str(d["kind"])] = d
    return docs


# ============================================================================================== prepare + fixed docs
@dataclass
class Prep:
    cell: dict
    built: Built
    g: GoldStructure
    ep: object
    settings: HarnessSettings
    quotes: dict = field(default_factory=dict)


def prepare(store, cell: dict, mode: str = "B", call=None, aligned: dict | None = None) -> Prep:
    """aligned: a stored aligner output for this cell (reuse it: the aligner is an LLM and can differ run to run)."""
    b = pair_gold(store, cell, call=call, aligned=aligned)
    g, _ = gold_for(b.pair, store, C=b.C, T=b.T)
    settings = HarnessSettings(mode=mode, model=GRANITE, max_tokens=6000, format_spec="v3")   # v3: reasoning after not_governed (Peter 2026-11-12)
    ep = student_episode(b.pair, store, settings=settings, C=b.C)
    try:
        q = trace_quotes(b.pair, store, g)
    except Exception:                                                   # noqa: BLE001
        q = {}
    return Prep(cell=cell, built=b, g=g, ep=ep, settings=settings, quotes=q)


def fixed_docs(g: GoldStructure) -> dict[str, dict]:
    T = g.T.case
    fe = {"kind": "fact_enumeration",
          "frame": {"question": T.question, "decider": T.decider, "my_role": T.agent},
          "facts": [{"id": f, "kind": g.fact(f).kind, "status": g.fact(f).status, "fact": g.fact(f).fact}
                    for f in g.fact_order],
          "options": {o: T.options[local(g.live[o])].do for o in g.option_ids}}
    ce = {"kind": "consideration_enumeration", "considerations": g.considerations_live()}
    return {"fact_enumeration": fe, "consideration_enumeration": ce}


def _served_id(g: GoldStructure) -> str:
    return g.served.prefix if g.served else "REF1"


def normalize(docs: dict[str, dict], g: GoldStructure) -> list[dict]:
    """Writer docs -> the target documents: fixed F / K pasted in, gold-only verdict fields forced, key order fixed."""
    fx = fixed_docs(g)
    out = []
    for k in ORDER:
        if k in fx:
            out.append(fx[k])
            continue
        if k not in docs:
            continue
        d = dict(docs[k])
        d["kind"] = k
        if k == "verdict":
            fl = g.flips_live()
            d = {"kind": "verdict", "choice": d.get("choice"), "course": d.get("course"), "relation": d.get("relation"),
                 "via": d.get("via"), "decisive": d.get("decisive"), "now": d.get("now"),
                 "flip_conditions": {"would_change": [{"id": w["id"], "if": w["if"], "then": w["then"], "why": w["why"]}
                                                      for w in fl["would_change"]],
                                     "would_not_change": fl["would_not_change"], "watch_for": fl["watch_for"]}}
        out.append({"kind": k, **{kk: vv for kk, vv in d.items() if kk != "kind"}})
    return out


# ============================================================================================== writer (Luna)
def writer_messages(p: Prep) -> list[dict]:
    system = prompt_ref(WRITER_PROMPT)[0]
    student = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in p.ep.messages)
    brief = gold_brief(p.g, p.quotes)
    if p.g.pair.relation == "not_governed":
        brief["note"] = "The case does not govern: write the documents through `applicability` and stop (A3)."
    fixed = emit(list(fixed_docs(p.g).values()))
    user = ("STUDENT PROMPT (everything the student sees)\n<student_prompt>\n" + student + "\n</student_prompt>\n\n"
            "GOLD STRUCTURE (fixed; the student does not see it)\n<gold>\n"
            + yaml.safe_dump(brief, sort_keys=False, allow_unicode=True, width=140)
            + "</gold>\n\nFIXED DOCUMENTS (reproduce unchanged)\n<fixed>\n" + fixed + "</fixed>\n\n"
            "Write the student's reply now: the YAML documents only.")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def write(p: Prep, tries: int = 2, call=None) -> dict:
    msgs = writer_messages(p)
    last = None
    for t in range(1, tries + 1):
        raw = (call or (lambda m: complete("sft_writer", m, stage="sft-write")))(msgs) or ""
        docs = parse_docs(raw)
        text = emit(normalize(docs, p.g))
        chk = check_reply(text, p.g) if p.g.pair.relation != "not_governed" else _check_through_applicability(text, p.g)
        last = {"try": t, "raw": raw, "text": text, "accepted": chk["accepted"], "reasons": chk["reasons"],
                "flags": chk["flags"]}
        if chk["accepted"]:
            break
    return last


def _check_through_applicability(text: str, g: GoldStructure) -> dict:
    """Random arm: the writer stops at applicability. Check what is there with a placeholder verdict appended."""
    stub = text.rstrip() + "\n---\n" + emit([{"kind": "verdict", "choice": g.choice, "course": "x", "relation":
                                               "not_governed", "via": None, "decisive": [], "now": ["x"],
                                               "flip_conditions": {"would_change": [], "would_not_change": [],
                                                                   "watch_for": []}}])
    c = check_reply(stub, g)
    c["reasons"] = [r for r in c["reasons"] if not r.startswith("choice")]
    c["accepted"] = not c["reasons"]
    return c


# ============================================================================================== prose fields
def prose_paths(docs: list[dict]) -> list[tuple]:
    """(doc index, path...) of every free-text field the writer wrote (not F, K, flip conditions, ids)."""
    out = []
    for i, d in enumerate(docs):
        k = d["kind"]
        if k == "fact_mapping":
            if isinstance(d.get("note"), str):
                out.append((i, "note"))
            for j, it in enumerate(d.get("corresponding") or []):
                if isinstance(it, dict) and isinstance(it.get("note"), str):
                    out.append((i, "corresponding", j, "note"))
        elif k == "consideration_mapping":
            for b in ("matched", "corresponding"):
                for j, it in enumerate(d.get(b) or []):
                    if isinstance(it, dict) and isinstance(it.get("role"), str):
                        out.append((i, b, j, "role"))
            for j, it in enumerate(d.get("case_only") or []):
                if isinstance(it, dict) and isinstance(it.get("assumption"), str):
                    out.append((i, "case_only", j, "assumption"))
        elif k == "applicability":
            if isinstance(d.get("why"), str):
                out.append((i, "why"))
        elif k == "reasoning":
            for f in ("case_approach", "weighing", "tradecraft", "uncertainty", "handoff"):
                if isinstance(d.get(f), str):
                    out.append((i, f))
            tw = d.get("tempting_wrong")
            if isinstance(tw, dict):
                for f in ("pull", "why_wrong"):
                    if isinstance(tw.get(f), str):
                        out.append((i, "tempting_wrong", f))
            for o, v in (d.get("rejected") or {}).items():
                if isinstance(v, str):
                    out.append((i, "rejected", o))
        elif k == "verdict":
            if isinstance(d.get("course"), str):
                out.append((i, "course"))
            for j, v in enumerate(d.get("now") or []):
                if isinstance(v, str):
                    out.append((i, "now", j))
    return out


def _get(docs, path):
    x = docs[path[0]]
    for k in path[1:]:
        x = x[k]
    return x


def _set(docs, path, v):
    x = docs[path[0]]
    for k in path[1:-1]:
        x = x[k]
    x[path[-1]] = v


def w_text(docs: list[dict]) -> str:
    """W as plain text (the reasoning document without its kind/case lines), for the gates."""
    r = next((d for d in docs if d["kind"] == "reasoning"), None)
    return emit([{k: v for k, v in r.items() if k not in ("kind", "case")}]) if r else ""


# ============================================================================================== restate (Granite)
RESTATE = (PROMPTS / "restate.v1.md").read_text()      # retired 2026-11-13 (M13: Granite copied); kept for the record


def restate(p: Prep, text: str, call=None, tries: int = 2) -> dict:
    docs = list(yaml.safe_load_all(text))
    paths = prose_paths(docs)
    passages = "\n".join(f"{n}. {_get(docs, pth)}" for n, pth in enumerate(paths, 1))
    msgs = [{"role": "user", "content": RESTATE.format(record=text, passages=passages, n=len(paths))}]
    err = None
    for t in range(1, tries + 1):
        raw = (call or (lambda m: complete("sft_restater", m, stage="sft-restate")))(msgs) or ""
        try:
            got = {int(m.group(1)): m.group(2).strip().strip('"').strip()
                   for m in re.finditer(r"(?m)^\s*\[(\d+)\]\s*(.+?)\s*$", raw)}
            if set(got) != set(range(1, len(paths) + 1)):
                raise ValueError(f"passages {sorted(set(range(1, len(paths) + 1)) - set(got))} missing")
        except Exception as e:                                          # noqa: BLE001
            err = f"{type(e).__name__}: {e}"[:200]
            continue
        new = [json.loads(json.dumps(d)) for d in docs]
        for n, pth in enumerate(paths, 1):
            _set(new, pth, got[n])
        out = emit(new)
        chk = check_reply(out, p.g) if p.g.pair.relation != "not_governed" else {"accepted": True, "reasons": [],
                                                                                 "flags": {}}
        ids_lost = sorted({i for n, pth in enumerate(paths, 1)
                           for i in re.findall(r"\b(?:LIVE|REF\d)-[A-Za-z]+\d+\b", str(_get(docs, pth)))
                           if i not in got[n]})
        return {"try": t, "raw": raw, "text": out, "accepted": chk["accepted"], "reasons": chk["reasons"],
                "ids_lost": ids_lost, "n_passages": len(paths)}
    return {"try": tries, "raw": None, "text": None, "accepted": False, "reasons": [f"restate failed: {err}"]}


# ============================================================================================== gates (Jev)
_GATES = yaml.safe_load((PROMPTS / "jev_gates.v1.yaml").read_text())
SUPPORTS_Q, SAME_ARG_Q = _GATES["supports"], _GATES["same_argument"]


def gate(p: Prep, text: str, judge, reference: str | None = None, choice: str | None = None) -> dict:
    """supports: the reasoning alone (verdict hidden) points to `choice` (default the gold choice; the random arm
    passes Granite's own no-case choice). same_argument: vs the reference reasoning (the writer's), when given."""
    docs = list(yaml.safe_load_all(text))
    w = w_text(docs)
    if not w:
        return {"supports": None, "same_argument": None}
    opts = [p.g.T.case.options[local(p.g.live[o])].do for o in p.g.option_ids]
    dist = judge.choice(w, opts, instruction=SUPPORTS_Q)
    top = max(range(len(dist)), key=lambda i: dist[i])
    want = choice or p.g.choice
    if want not in p.g.option_ids:
        return {"supports": False, "p_gold": None, "top": None, "note": f"choice {want} is not a live option"}
    gold_i = p.g.option_ids.index(want)
    out = {"supports": top == gold_i, "p_gold": round(dist[gold_i], 3),
           "top": p.g.option_ids[top] if top < len(opts) else "none"}
    if reference is not None:
        ref_w = w_text(list(yaml.safe_load_all(reference)))
        py = judge.noul(ref_w, w, SAME_ARG_Q)
        out.update(same_argument=py >= 0.5, p_same=round(py, 3))
    return out


# ============================================================================================== Granite W+V (gold-conditioned)
def prefix_through_applicability(text: str) -> str:
    docs = [d for d in yaml.safe_load_all(text) if d["kind"] in ORDER[:5]]
    return emit(docs) + "---\nkind: reasoning\n"


def granite_rs(p: Prep, writer_text: str, k: int = 8, seed0: int = 0) -> list[dict]:
    """k continuations of the gold prefix (F..applicability, writer's prose) by base Granite, mode B."""
    from harness.client import continue_episode
    partial = prefix_through_applicability(writer_text)           # mode B: the harness prepends the empty think block
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(k) as ex:           # k requests in flight; vLLM batches them
        comps = list(ex.map(lambda i: continue_episode(p.ep, p.settings.with_(seed=seed0 + i), partial, role="policy",
                                                       seed=seed0 + i), range(k)))
    out = []
    for i, c in enumerate(comps):
        raw = c.raw_text
        body = raw.split("</think>", 1)[-1]        # mode B: the empty think block sits on the first document's line
        # structure is checked on Granite's own text (a YAML error rejects the sample); the target is emitted from the
        # checker's own parse, so acceptance and target always read the reply the same way
        chk = check_reply(body, p.g)
        docs = dict(chk["parsed"].steps) if chk["accepted"] else parse_docs(body)
        text = emit(normalize(docs, p.g)) if chk["accepted"] else raw
        out.append({"i": i, "raw": raw, "text": text, "accepted": chk["accepted"], "reasons": chk["reasons"],
                    "finish": c.finish_reason, "choice": (docs.get("verdict") or {}).get("choice"),
                    "relation": (docs.get("verdict") or {}).get("relation")})
    return out


# ============================================================================================== random arm: no-case W+V
def nocase_wv(store, p: Prep, k: int = 4, seed0: int = 0) -> list[dict]:
    """Granite on X1 WITHOUT the case (the -noref prompt), prefilled with the fixed F and K documents; returns its
    reasoning and verdict documents per sample."""
    from eval.allpairs import none_pair
    from harness.client import continue_episode
    np_ = none_pair(store, p.cell["x1"], p.built.pair.equities)
    ep = student_episode(np_, store, settings=p.settings)
    partial = emit(list(fixed_docs(p.g).values())) + "---\nkind: reasoning\n"
    out = []
    for i in range(k):
        c = continue_episode(ep, p.settings.with_(seed=seed0 + i), partial, role="policy", seed=seed0 + i)
        docs = parse_docs(c.raw_text.split("</think>", 1)[-1])
        out.append({"i": i, "raw": c.raw_text, "reasoning": docs.get("reasoning"), "verdict": docs.get("verdict"),
                    "finish": c.finish_reason})
    return out


def splice_random(writer_text: str, r: dict, v: dict, g: GoldStructure) -> str:
    docs = [d for d in yaml.safe_load_all(writer_text) if d["kind"] in ORDER[:5]]
    # no case_approach after not_governed: the case was judged irrelevant (Peter, 2026-11-12; reply schema relaxed)
    reasoning = {"kind": "reasoning", "case": _served_id(g),
                 **{k: x for k, x in r.items() if k not in ("kind", "case", "case_approach")}}
    fl = g.flips_live()                       # V's flip conditions are X1's gold, as on every other arm
    verdict = {"kind": "verdict", "choice": v.get("choice"), "course": v.get("course"), "relation": "not_governed",
               "via": None, "decisive": v.get("decisive"), "now": v.get("now"),
               "flip_conditions": {"would_change": fl["would_change"], "would_not_change": fl["would_not_change"],
                                   "watch_for": fl["watch_for"]}}
    return emit(docs + [reasoning, verdict])


# ============================================================================================== Granite W+V guided by notes
NOTES = "\n\n" + (PROMPTS / "notes.v1.md").read_text()      # appended to the student's last user message


CASE_APPROACH_GUIDE = "\n\n" + (PROMPTS / "case_approach_guide.v1.md").read_text()   # generation-only (M13 addendum)


def guided_episode(p: Prep, writer_text: str, guide: bool = False):
    """(episode, prefill) exactly as guided_rs sends them: the student prompt + the writer's reasoning and verdict as
    notes (+ the case_approach guidance), and the writer's documents through applicability as the assistant prefill.
    Generation only: the SFT row's prompt is the plain student prompt (p.ep)."""
    from pipeline.solve.rs import _rerender
    docs = list(yaml.safe_load_all(writer_text))
    notes = emit([d for d in docs if d["kind"] in ("reasoning", "verdict")])
    msgs = [dict(m) for m in p.ep.messages]
    msgs[-1]["content"] = msgs[-1]["content"] + NOTES.format(notes=notes) + (CASE_APPROACH_GUIDE if guide else "")
    return _rerender(p.ep, msgs, p.settings), prefix_through_applicability(writer_text)


def guided_rs(p: Prep, writer_text: str, k: int = 2, seed0: int = 100, guide: bool = False) -> list[dict]:
    """Variant of granite_rs: the writer's reasoning and verdict are added to the prompt as notes (not prefilled);
    Granite writes W and V after the gold prefill (F..applicability). Kept iff the reply passes check_reply."""
    from concurrent.futures import ThreadPoolExecutor
    from harness.client import continue_episode
    ep, partial = guided_episode(p, writer_text, guide)
    with ThreadPoolExecutor(k) as ex:
        comps = list(ex.map(lambda i: continue_episode(ep, p.settings.with_(seed=seed0 + i), partial, role="policy",
                                                       seed=seed0 + i), range(k)))
    out = []
    for i, c in enumerate(comps):
        body = c.raw_text.split("</think>", 1)[-1]
        chk = check_reply(body, p.g)
        d2 = dict(chk["parsed"].steps) if chk["accepted"] else parse_docs(body)
        text = emit(normalize(d2, p.g)) if chk["accepted"] else body
        out.append({"i": i, "raw": c.raw_text, "text": text, "accepted": chk["accepted"], "reasons": chk["reasons"],
                    "finish": c.finish_reason, "choice": (d2.get("verdict") or {}).get("choice"),
                    "relation": (d2.get("verdict") or {}).get("relation")})
    return out


# ============================================================================================== case_approach quality
CA_Q = _GATES["case_account"]
DIRECTIVE = re.compile(r"^(weigh|weight|request|identify|continue|treat|consider|assess|determine|ensure|use|apply|"
                       r"check|keep|give|prioriti[sz]e|balance|evaluate|compare|focus|first)\b", re.I)


def case_approach_quality(p: Prep, text: str, judge) -> dict:
    """Jev Noul against the served case's own recorded reasoning (read + weighing), plus cheap form checks."""
    docs = parse_docs(text)
    ca = str((docs.get("reasoning") or {}).get("case_approach") or "")
    if not ca:
        return {}
    r = p.built.C.case.reasoning
    ref = f"{r.read} {r.weighing}"
    return {"p_case_account": round(judge.noul(ref, ca, CA_Q), 3), "directive": bool(DIRECTIVE.match(ca.strip())),
            "ref_ids": len(set(re.findall(r"\bREF1-[A-Za-z]+\d+\b", ca))),
            "live_ids": len(set(re.findall(r"\bLIVE-[A-Za-z]+\d+\b", ca))), "words": len(ca.split())}
