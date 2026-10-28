"""CLI: python -m pipeline.pair {build [--decoys N] [--seed S] [--thin-share F] [--dry] | stats | gate-augmented [--limit N] [--regate] | sync-traces | housekeeping-2f}"""
from __future__ import annotations

import argparse
import json
import sys

from pipeline.store import DATA, Store

from .build import build, housekeeping_2f, stats, sync_traces
from .gate import gate_augmented


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.pair")
    ap.add_argument("--data", default=str(DATA))
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--decoys", type=int, default=2, help="decoy Cs per target scenario")
    b.add_argument("--seed", type=int, default=0)
    b.add_argument("--thin-share", type=float, default=None, help="share of eligible train items served thin (default: config thin_share, 0.0)")
    b.add_argument("--position-tolerance", type=float, default=0.15, help="max card-position share above 1/n before trimming; <0 disables")
    b.add_argument("--dry", action="store_true", help="report only; write nothing")
    sub.add_parser("stats")
    g = sub.add_parser("gate-augmented", help="after render: verify each augmented pair's back-flip `if` on X's rendered trace")
    g.add_argument("--limit", type=int, default=None)
    g.add_argument("--regate", action="store_true")
    sub.add_parser("sync-traces", help="after render: copy recommended_option from the trace store into the pairs")
    sub.add_parser("housekeeping-2f")
    a = ap.parse_args(argv)
    st = Store(a.data)
    if a.cmd == "build":
        r = build(st, a.decoys, a.seed, write=not a.dry, thin_share=a.thin_share,
                  position_tolerance=None if a.position_tolerance < 0 else a.position_tolerance)
    elif a.cmd == "stats":
        r = stats(st)
    elif a.cmd == "gate-augmented":
        r = gate_augmented(st, limit=a.limit, regate=a.regate)
    elif a.cmd == "sync-traces":
        r = sync_traces(st)
    else:
        r = housekeeping_2f(st)
    print(json.dumps(r, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
