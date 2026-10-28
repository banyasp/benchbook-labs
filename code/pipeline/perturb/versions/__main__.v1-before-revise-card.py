"""CLI: python -m pipeline.perturb {restyle|flip|add-fact} --scenario ID | all [--split S] | seed-pilot"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline.store import DATA, Store

from . import OPERATORS, OperatorError, save_result
from .common import pilot_scenario, seed_rng


def run_one(store: Store, op: str, sid: str, seed: int = 0, **kw):
    X = store.scenario(sid)
    n = len(list((store.root / "scenarios").glob(f"*/DR-{X.family}-*@v1.yaml")))
    rng = seed_rng(sid, op, seed, n)
    T, partial = OPERATORS[op](X, store, rng, **kw)
    sp, pp = save_result(store, T, partial)
    print(f"{op}: {X.id} -> {T.id}  relation={partial['relation']} tier={partial['gold_tier']}  ({sp})")
    return T, partial


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.perturb")
    ap.add_argument("--data", default=str(DATA), help="data root (default: repo data/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("restyle", "flip", "add-fact"):
        p = sub.add_parser(name)
        p.add_argument("--scenario", required=True)
        p.add_argument("--seed", type=int, default=0)
        if name == "flip":
            p.add_argument("--item", help="would_change id to realize (default: random)")
    a = sub.add_parser("all")
    a.add_argument("--split", default=None)
    a.add_argument("--ops", default="restyle,flip,add_fact")
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("--again", action="store_true", help="also perturb parents that already have a child of that operator")
    sp = sub.add_parser("seed-pilot", help="copy the converted pilot cases into the store as eval-only scenarios (testing only)")
    sp.add_argument("--cases", default=str(DATA / "cases"))
    args = ap.parse_args(argv)
    store = Store(args.data)
    if args.cmd == "seed-pilot":
        for p in sorted(Path(args.cases).glob("*/DR-*.case.yaml")):
            s = pilot_scenario(p)
            store.save_scenario(s)
            print("seeded", s.id)
        return 0
    if args.cmd in ("restyle", "flip", "add-fact"):
        op = args.cmd.replace("-", "_")
        kw = {"item": args.item} if op == "flip" and args.item else {}
        run_one(store, op, args.scenario, args.seed, **kw)
        return 0
    ops = args.ops.split(",")
    done = {(s.lineage.parent, s.lineage.operator) for s in store.scenarios() if s.lineage.parent}
    fails = 0
    for X in store.scenarios(split=args.split):
        if X.lineage.parent:
            continue
        for op in ops:
            if (X.id, op) in done and not args.again:
                continue
            try:
                run_one(store, op, X.id, args.seed)
            except OperatorError as e:
                fails += 1
                print(f"FAILED {op} {X.id}: {e}", file=sys.stderr)
    print(f"done; {fails} failures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
