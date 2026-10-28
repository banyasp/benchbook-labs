import argparse
import sys

from pipeline.store import DATA, Store

from . import render_pair
from .trace import DEFAULT_SEED, needed, render_many


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.render")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--trace-scenario", action="append", help="render the trace for this trace scenario id (repeatable)")
    g.add_argument("--all-needed", action="store_true",
                   help="every trace scenario a pair references (trace_ref/trace_scenario) that has no trace yet")
    g.add_argument("--pair", help="legacy v2 per-pair render")
    g.add_argument("--all", action="store_true", help="legacy v2 per-pair render of every pair")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--workers", type=int, default=12, help="parallel Bedrock calls (8-16)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--skip-rejected", action="store_true", help="with --all-needed: do not retry earlier rejections")
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args(argv)
    st = Store(a.data)
    if a.pair or a.all:
        for p in (st.pairs() if a.all else [st.pair(a.pair)]):
            if p.trace and not a.redo and not a.pair:
                continue
            p = render_pair(p, st)
            print(f"{p.id}: rendered, {len(p.span_map.entries)} span entries", file=sys.stderr)
        return 0
    sids = needed(st, a.skip_rejected) if a.all_needed else a.trace_scenario
    bad = 0

    def log(sid, r):
        nonlocal bad
        if isinstance(r, Exception):
            bad += 1
            print(f"{sid}: ERROR {type(r).__name__}: {r}", file=sys.stderr)
        elif r.diagnostics["status"] == "ok":
            print(f"{sid}: ok, {len(r.span_map.entries)} facts, {len(r.span_map.options)} options, "
                  f"rec={r.recommended_option}", file=sys.stderr)
        else:
            bad += 1
            print(f"{sid}: DROPPED ({r.diagnostics.get('reason')})", file=sys.stderr)
    render_many(st, sids, workers=a.workers, seed=a.seed, log=log)
    print(f"{len(sids)} trace scenarios, {bad} dropped/failed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
