"""Pair dataset v1, built with the scenario operators (Peter, 2026-11-11).

Peter's rulings for v1: pilot ~100 anchors, then all; every arm (self, transfer, flipped transfer, same-domain flip,
would-not-change edit, revised C', drop option, neighbor control, decoy); X1 (the live trace) is always an anchor,
derived scenarios are only served as cases (revisit for SFT/RL); decide <-> advise parked; leaky scenarios never used.

    python -m pipeline.datasets.pairs_v1 eligibility [--workers 16]      # data/datasets/pairs-v1/eligibility.jsonl
    python -m pipeline.datasets.pairs_v1 pilot [--n 100] [--seed 0]      # data/datasets/pairs-v1/pilot-anchors.txt
    python -m pipeline.datasets.pairs_v1 build --inputs <ids.txt> --tag pilot [--workers 6] [--arms transfer,...]
        runs every arm recipe (code/pipeline/ops/recipes/pairs_v1/*.yaml) on the anchors, all in ONE process so the
        id reservation lock is shared (separate processes could mint the same derived id); writes
        data/datasets/pairs-v1/build-<tag>.json (per-recipe summaries and run-log paths)

Eligibility ("quality" anchors): every check is recorded per anchor, pass or fail with reasons; nothing is deleted.
  structure   parses; 2-4 options; gold among them; >= 1 consideration
  leak        pipeline.render.answer_leak v4 (role-aware, frame + facts) on the scenario: no leak (Peter, 2026-11-09:
              leaky scenarios are never used as X1 or X2). An unparseable check fails closed.
  technique   pipeline.ingest.technique_check: no strip-severity hit
Recorded but not gating: split / held_out, domain, n options, hand-up gold, would_change items whose then != gold
(flip capacity), would_not_change items, existing trace and its trace-leak result.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bench.schema.pipeline import Scenario
from pipeline.store import ROOT, Store

OUT = ROOT / "data" / "datasets" / "pairs-v1"
HANDUP = {"ask", "refuse"}


def anchors(store: Store) -> list[Path]:
    return [p for p in sorted((store.root / "scenarios").glob("*/*.yaml")) if not Scenario.load(p).lineage.parent]


def check_anchor(store: Store, p: Path) -> dict:
    from pipeline.ops import checks as CK
    from pipeline.render import answer_leak as AL
    S = Scenario.load(p)
    c = S.case
    gold = c.verdict.choice
    row = {"id": S.id, "file": str(p.relative_to(ROOT)), "family": S.family, "domain": S.domain, "split": S.split,
           "held_out": S.held_out, "n_options": len(c.options), "gold": gold,
           "handup_gold": c.options[gold].move in HANDUP if gold in c.options else None,
           "flip_items": [w.id for w in c.flip_conditions.would_change if w.then != gold],
           "noflip_items": [w.id for w in c.flip_conditions.would_not_change], "has_trace": store.has_trace(S.id),
           "checks": {}, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    errs = []
    if not 2 <= len(c.options) <= 4:
        errs.append(f"{len(c.options)} options")
    if gold not in c.options:
        errs.append("gold not among options")
    if not c.considerations:
        errs.append("no considerations")
    row["checks"]["structure"] = {"pass": not errs, "why": errs}
    row["checks"]["technique"] = CK.technique_gate(S)
    msgs = store.trace_json(S.id)["messages"] if row["has_trace"] else None
    try:
        lk = AL.check(S, msgs)
        bad = (lk.get("frame") or []) + (lk.get("facts") or [])
        row["checks"]["leak"] = {"pass": not bad, "check": "answer_leak v4-frame", "items": bad[:5]}
        if msgs is not None:
            row["trace_leak"] = {"leak": bool(lk.get("trace")), "items": (lk.get("trace") or [])[:5]}
    except Exception as e:                                                   # noqa: BLE001
        row["checks"]["leak"] = {"pass": False, "error": f"unparseable: {e}"[:200]}
    row["eligible"] = all(v.get("pass") for v in row["checks"].values())
    row["why_not"] = [k for k, v in row["checks"].items() if not v.get("pass")]
    return row


def eligibility(workers: int = 16) -> dict:
    store = Store()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eligibility.jsonl"
    done = {json.loads(l)["id"] for l in out.read_text().splitlines()} if out.exists() else set()
    todo = [p for p in anchors(store) if Scenario.load(p).id not in done]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(check_anchor, store, p) for p in todo]
        for f in as_completed(futs):
            row = f.result()
            with open(out, "a") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    return {"anchors": len(rows), "eligible": sum(r["eligible"] for r in rows),
            "fails": dict(Counter(k for r in rows for k in r["why_not"])), "out": str(out)}


def pilot(n: int = 100, seed: int = 0) -> dict:
    """Stratified pilot: eligible anchors, one per family at most, spread over domain x split in proportion to the pool,
    at least one per stratum when possible."""
    rows = [json.loads(l) for l in (OUT / "eligibility.jsonl").read_text().splitlines()]
    pool = [r for r in rows if r["eligible"]]
    rng = random.Random(seed)
    by_fam = defaultdict(list)
    for r in pool:
        by_fam[r["family"]].append(r)
    one = [rng.choice(sorted(v, key=lambda r: r["id"])) for _, v in sorted(by_fam.items())]
    strata = defaultdict(list)
    for r in one:
        strata[(r["domain"], r["split"])].append(r)
    for v in strata.values():
        rng.shuffle(v)
    quota = {k: max(1, round(n * len(v) / len(one))) for k, v in strata.items()}
    picked = [r for k, v in sorted(strata.items()) for r in v[:quota[k]]]
    rng.shuffle(picked)
    picked = sorted(picked[:n], key=lambda r: r["id"])
    path = OUT / "pilot-anchors.txt"
    path.write_text("# pairs-v1 pilot anchors (stratified by domain x split, one per family; seed %d)\n" % seed
                    + "\n".join(r["id"] for r in picked) + "\n")
    return {"pool_eligible": len(pool), "families": len(one), "picked": len(picked), "out": str(path),
            "by_split": dict(Counter(r["split"] for r in picked)), "by_domain": dict(Counter(r["domain"] for r in picked)),
            "n_options": dict(Counter(r["n_options"] for r in picked)), "with_trace": sum(r["has_trace"] for r in picked)}


RECIPES = ROOT / "code" / "pipeline" / "ops" / "recipes" / "pairs_v1"


def build(inputs: str, tag: str, workers: int = 6, arms: list[str] | None = None, seed: int = 0) -> dict:
    from pipeline.ops.recipes import load_recipe, run_recipe
    ids = [l.split()[0] for l in Path(inputs).read_text().splitlines() if l.strip() and not l.startswith("#")]
    files = sorted(RECIPES.glob("*.yaml"))
    if arms:
        files = [f for f in files if f.stem in arms]
    store = Store()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=len(files)) as ex:
        futs = {ex.submit(run_recipe, load_recipe(str(f)), ids, store, workers, seed): f.stem for f in files}
        res = {futs[f]: f.result() for f in as_completed(futs)}
    out = {"tag": tag, "inputs": inputs, "n_inputs": len(ids), "seed": seed, "workers": workers,
           "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "seconds": round(time.time() - t0),
           "recipes": res}
    (OUT / f"build-{tag}.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.datasets.pairs_v1")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eligibility")
    e.add_argument("--workers", type=int, default=16)
    pl = sub.add_parser("pilot")
    pl.add_argument("--n", type=int, default=100)
    pl.add_argument("--seed", type=int, default=0)
    b = sub.add_parser("build")
    b.add_argument("--inputs", required=True)
    b.add_argument("--tag", required=True)
    b.add_argument("--workers", type=int, default=6)
    b.add_argument("--arms")
    b.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        res = build(a.inputs, a.tag, a.workers, a.arms.split(",") if a.arms else None, a.seed)
    else:
        res = eligibility(a.workers) if a.cmd == "eligibility" else pilot(a.n, a.seed)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
