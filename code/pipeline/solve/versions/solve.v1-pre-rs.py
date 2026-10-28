"""solve: the TEACHER writes the student's full reply for a pair, given the trace, equities, served case AND the full
gold structure plus the structure-mapping rubric (design 4b). Process text only: the gold verdict is never decided
here. Accept a sample iff it parses strictly and matches gold (see check.py). Never the policy/base model.

Writer hook: `rewrite(text, ctx) -> text` runs on each parsed sample before the check (a later self-distillation
rewrite step plugs in here). Default: the teacher's text as written.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import yaml

from bench.models import complete as default_complete
from bench.models import role
from bench.schema.pipeline import PairRecord, SolveSample, sha256_obj, sha256_text
from pipeline.render.util import make_step, prompt_ref
from pipeline.store import Store, write_json, write_yaml

from .check import check_reply
from .episode import load_equities, student_episode
from .structure import GoldStructure

PROMPT = Path(__file__).parent / "prompts" / "teacher.v4.md"


def trace_quotes(pair: PairRecord, store: Store, g: GoldStructure) -> dict[str, str]:
    """LIVE fact id -> the text in the trace that realizes it (computed from the span map and trace.json)."""
    msgs = json.loads((store.pair_dir(pair.id) / pair.trace).read_text())["messages"]
    out: dict[str, list[str]] = defaultdict(list)
    for e in pair.span_map.entries if pair.span_map else []:
        lid = g.glob2live.get(e.fact)
        if lid:
            out[lid].append(msgs[e.message]["content"][e.start:e.end])
    return {k: " ... ".join(v) for k, v in out.items()}


def gold_brief(g: GoldStructure, quotes: dict[str, str] | None = None) -> dict:
    """The full gold structure in the ids the student uses (LIVE-* / REF1-*), as a dict for the teacher prompt."""
    T, p = g.T.case, g.pair
    pm = lambda m: [{"live": a, "case": b} for a, b in m]
    facts = []
    for f in g.fact_order:
        x = g.fact(f)
        d = {"id": f, "kind": x.kind, "status": x.status, "fact": x.fact}
        if quotes and f in quotes:
            d["appears_in_trace_as"] = quotes[f]
        facts.append(d)
    brief = {
        "frame_of_the_live_decision": {"question": T.question, "decider": T.decider, "my_role": T.agent},
        "frame_comparison_with_REF1": p.frame.model_dump(),
        "live_facts_in_trace_order": facts,
        "live_options": {o: g.T.case.options[o.replace("LIVE-", "")].do for o in g.option_ids},
        "options_map (live -> REF1, null = none)": dict(g.options_map),
        "fact_mapping": {"matched": pm(g.fact_map["matched"]), "corresponding": pm(g.fact_map["corresponding"]),
                         "live_only": g.fact_map["live_only"], "case_only": g.fact_map["case_only"]},
        "live_considerations": g.considerations_live(),
        "consideration_mapping": {"matched": pm(g.cons_map["matched"]), "corresponding": pm(g.cons_map["corresponding"]),
                                  "live_only": g.cons_map["live_only"], "case_only": g.cons_map["case_only"]},
        "applicability": {"governs": p.governs},
        "relation": p.relation,
        "via (REF1 would_change ids that fired)": list(g.via) or None,
        "verdict_choice": g.choice,
        "decisive_considerations": g.decisive,
        "live_flip_conditions": g.flips_live(),
        "independent_notes_on_the_live_scenario (written without the case; use for tradecraft, uncertainty, handoff, "
        "tempting_wrong, rejected; rephrase)": {
            "tradecraft": g.live_text(T.reasoning.tradecraft), "uncertainty": g.live_text(T.reasoning.uncertainty),
            "handoff": g.live_text(T.reasoning.handoff),
            "tempting_wrong": {"option": g.lid(T.reasoning.tempting_wrong.option),
                               "pull": g.live_text(T.reasoning.tempting_wrong.pull),
                               "why_wrong": g.live_text(T.reasoning.tempting_wrong.why_wrong)},
            "rejected": {g.lid(k): g.live_text(v) for k, v in T.reasoning.rejected.items()}},
    }
    t = p.touched
    if t:
        item = g.case2served.get(t.item) if t.item else None
        brief["TOUCHED_CONDITION"] = {"served_id": item, "condition": t.condition, "what_changed_or_was_tested": t.how}
    if p.relation == "not_governed":
        brief["note"] = "The case does not govern: write no `reasoning` document."
    return brief


def teacher_messages(g: GoldStructure, ep, quotes=None) -> list[dict]:
    system = prompt_ref(PROMPT)[0]
    student = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in ep.messages)
    user = ("STUDENT PROMPT (everything the student sees)\n<student_prompt>\n" + student + "\n</student_prompt>\n\n"
            "GOLD STRUCTURE (fixed; the student does not see it)\n<gold>\n"
            + yaml.safe_dump(gold_brief(g, quotes), sort_keys=False, allow_unicode=True, width=140)
            + "</gold>\n\nWrite the student's reply now: the YAML documents only.")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def solve_pair(pair: PairRecord, store: Store, equities=None, n: int | None = None, llm: Callable | None = None,
               rewrite: Callable | None = None, settings=None, require_touched: bool = False) -> PairRecord:
    llm = llm or default_complete
    n = n or role("teacher").get("samples", 3)
    C, T = store.scenario(pair.case_scenario), store.scenario(pair.trace_scenario)
    eq = load_equities(equities, T) if not hasattr(equities, "equities") else equities
    g = GoldStructure.build(pair, C, T)
    ep = student_episode(pair, store, eq, settings, C=C)
    msgs = teacher_messages(g, ep, trace_quotes(pair, store, g))
    pdir = store.pair_dir(pair.id)
    ps = prompt_ref(PROMPT)

    def one(k):
        t0 = time.time()
        raw = llm("teacher", msgs, stage="solve")
        text = raw
        if rewrite:
            first = check_reply(raw, g, require_touched)
            text = rewrite(first["clean"] or raw, {"gold": g, "episode": ep, "raw": raw}) if first["accepted"] else raw
        res = check_reply(text, g, require_touched)
        return k, raw, text, res, round(time.time() - t0, 1)

    with ThreadPoolExecutor(max_workers=max(1, min(n, 4))) as ex:
        results = list(ex.map(one, range(1, n + 1)))
    inputs = {"trace": sha256_obj(json.loads((pdir / pair.trace).read_text())["messages"]),
              "gold": sha256_obj(gold_brief(g)), "teacher_prompt": sha256_text(msgs[0]["content"]),
              "equities": sha256_obj(eq.model_dump()), "case": sha256_obj(C.case.dump())}
    samples = []
    for k, raw, text, res, secs in results:
        step = make_step(f"solve.{k}", "solve", "teacher", ps, inputs, {"sample": k, "rewritten": bool(rewrite)}).model_dump()
        rel = f"solve/sample-{k}.yaml"
        write_yaml(pdir / rel, {"k": k, "accepted": res["accepted"], "reasons": res["reasons"], "flags": res["flags"],
                                "seconds": secs, "reply": res["clean"], "raw": raw, "provenance": step})
        samples.append(SolveSample(path=f"pairs/{pair.id}/{rel}", accepted=res["accepted"], reasons=res["reasons"]))
    pair.solve = samples
    pair.provenance.steps = [s for s in pair.provenance.steps if not s.id.startswith("solve")]
    pair.provenance.step(**make_step("solve", "solve", "teacher", ps, inputs, {"n": n, "accepted": sum(s.accepted for s in samples),
                                                                           "gold_warnings": len(g.warnings)}).model_dump())
    pair.provenance.fields["solve"] = "solve"
    store.save_pair(pair)
    return pair


def acceptance_report(pairs: list[PairRecord], store: Store | None = None) -> dict:
    """Acceptance per pair intent (R27): samples accepted / total, pairs with at least one accepted sample."""
    agg: dict[str, dict] = defaultdict(lambda: {"pairs": 0, "pairs_with_accept": 0, "samples": 0, "accepted": 0, "accepted_touched_cited": 0, "accepted_with_touched": 0, "reasons": defaultdict(int)})
    for p in pairs:
        if not p.solve:
            continue
        a = agg[p.intent]
        a["pairs"] += 1
        a["samples"] += len(p.solve)
        a["accepted"] += sum(s.accepted for s in p.solve)
        a["pairs_with_accept"] += any(s.accepted for s in p.solve)
        if store is not None:
            for s in p.solve:
                if s.accepted:
                    f = yaml.safe_load((store.root.parent / s.path.replace("pairs/", "store/pairs/", 1)).read_text())
                    a["accepted_touched_cited"] += bool(f.get("flags", {}).get("touched_cited"))
                    a["accepted_with_touched"] += "touched_cited" in f.get("flags", {})
        for s in p.solve:
            for r in s.reasons:
                a["reasons"][r.split(":")[0].split(" got")[0][:32]] += 1
    out = {}
    for k, a in agg.items():
        out[k] = {**a, "reasons": dict(a["reasons"]),
                  "sample_rate": round(a["accepted"] / a["samples"], 3) if a["samples"] else None,
                  "pair_rate": round(a["pairs_with_accept"] / a["pairs"], 3) if a["pairs"] else None}
    return out
