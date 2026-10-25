"""CLI: python -m pipeline.pair build [--decoys N] [--seed S] [--dry] | stats"""
from __future__ import annotations

import argparse
import json
import sys

from pipeline.store import DATA, Store

from .build import build, stats


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.pair")
    ap.add_argument("--data", default=str(DATA))
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--decoys", type=int, default=2, help="decoy Cs per target scenario")
    b.add_argument("--seed", type=int, default=0)
    b.add_argument("--dry", action="store_true", help="report only; write nothing")
    sub.add_parser("stats")
    a = ap.parse_args(argv)
    st = Store(a.data)
    r = build(st, a.decoys, a.seed, write=not a.dry) if a.cmd == "build" else stats(st)
    print(json.dumps(r, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
