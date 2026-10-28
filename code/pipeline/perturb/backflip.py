"""Back-flip repair for the augmented arm (batch 2026-10-28; design §6.3, §7.2).

The augmented gate requires X′'s back-flip `if` to hold on X's rendered trace. W3 wrote back-flip items as hypotheticals
or extended states ("continues producing negative PEth results after September"), which a strict reader can't conclude
from X's trace, so 13/31 train augmented pairs failed. This step rewrites only that item's `if` so it states, in other
words, the fact state X actually has, then checks it with the same strict verifier on X's rendered trace and requires
no 8-word verbatim run shared with that trace (R53: the card must not mirror the trace). The `then` is unchanged (X's
choice). Passing items are written to X′ (versioned) and the pair is re-gated; failures are left as they were.

    PYTHONPATH=code .venv/bin/python -m pipeline.perturb.backflip [--pairs P-..] [--all-failed]
"""
from __future__ import annotations

import argparse
import json
import sys

from bench.schema.pipeline import Scenario
from pipeline.pair.gate import trace_text
from pipeline.render import gates as G
from pipeline.store import Store

from .condition import condition_holds

SYS = "You rewrite one flip condition of a decision case. Reply with one JSON object only."
PROMPT = """A decision case X has these facts:
{facts}

X's decision was: {choice}

A variant case X′ (the same situation with one fact changed) carries this flip condition, whose consequence is that the
decision returns to X's decision ({choice_id}):
  if: {old_if}

The condition is written as a hypothetical or a future state, so it cannot be checked against X's facts. Rewrite ONLY
the `if` so that it states the fact state that X's facts actually establish and that leads back to X's decision:
- a strict reader of X's facts must be able to conclude it holds;
- general terms, in your own words: do not copy any phrase of 6 or more words from the facts above;
- one sentence, no new facts, no names, no option ids, no mention of "X" or "the case".
Reply: {{"if": "<the condition>"}}
{feedback}"""


def back_item(Xp: Scenario, via: str):
    return next(w for w in Xp.case.flip_conditions.would_change if Xp.case.global_id(w.id) == via)


def repair_pair(store: Store, pid: str, complete_fn=None, tries: int = 3) -> dict:
    if complete_fn is None:
        from bench.models import complete as complete_fn
    from pipeline.ingest.extract import parse_json
    p = store.pair(pid)
    Xp, X = store.scenario(p.case_scenario), store.scenario(p.trace_scenario)
    item = back_item(Xp, p.via[0])
    old_if = item.if_
    text = trace_text(store.trace_json(p.trace_ref or p.trace_scenario))
    trace_grams = G.ngrams(text)
    facts = "\n".join(f"- {f.fact}" for f in X.case.facts)
    fb, log = "", []
    for k in range(tries):
        out = parse_json(complete_fn("perturber", [{"role": "system", "content": SYS}, {"role": "user", "content": PROMPT.format(
            facts=facts, choice=X.case.options[X.case.verdict.choice].do, choice_id=X.case.verdict.choice,
            old_if=item.if_, feedback=fb)}], stage="perturb.backflip"))
        new = " ".join(str(out.get("if", "")).split())
        if not new:
            fb = "\nYour reply had no `if`."
            continue
        if G.ngrams(new) & trace_grams:
            fb = f"\nYour condition `{new}` copies 8+ words from the trace; reword it."
            log.append({"if": new, "fail": "verbatim"})
            continue
        r = condition_holds(new, text)
        log.append({"if": new, "holds": r.get("holds"), "why": r.get("why")})
        if r.get("holds") is True:
            item.if_ = new
            det = dict(Xp.lineage.detail or {})
            det["back_flip"] = {**(det.get("back_flip") or {}), "if": new, "rewritten_from": old_if}
            Xp.lineage.detail = det
            Xp.tags = sorted(set(Xp.tags) | {"backflip-rewritten"})
            Xp.provenance.step(id=f"perturb.backflip.{len(Xp.provenance.steps)}", operator="perturb", role="perturber",
                               notes=f"back-flip `if` rewritten to X's fact state (augmented gate); was: {old_if[:300]}",
                               params={"attempts": k + 1})
            Scenario.model_validate(Xp.dump())
            store.save_scenario(Xp)
            return {"pair": pid, "ok": True, "if": new, "attempts": k + 1}
        fb = f"\nA strict reader could not conclude `{new}` from X's facts ({r.get('why')}). State only what the facts establish."
    return {"pair": pid, "ok": False, "log": log}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", nargs="*")
    ap.add_argument("--all-failed", action="store_true")
    ap.add_argument("--split", default=None)
    a = ap.parse_args(argv)
    store = Store()
    ids = a.pairs or [p.id for p in store.pairs() if p.arm == "augmented" and "gate-failed" in p.tags
                      and "superseded" not in p.tags and (a.split is None or p.split == a.split)]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda i: repair_pair(store, i), ids))
    for r in res:
        print(json.dumps(r, ensure_ascii=False)[:300])
    ok = [r["pair"] for r in res if r["ok"]]
    print(f"repaired {len(ok)} of {len(ids)}")
    if ok:
        from pipeline.pair.gate import gate_augmented
        print(gate_augmented(store, regate=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
