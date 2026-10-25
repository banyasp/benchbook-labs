import argparse
import sys

from pipeline.store import DATA, Store

from . import render_pair


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.render")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pair")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--redo", action="store_true", help="re-render pairs that already have a trace")
    a = ap.parse_args(argv)
    st = Store(a.data)
    pairs = st.pairs() if a.all else [st.pair(a.pair)]
    for p in pairs:
        if p.trace and not a.redo and not a.pair:
            continue
        p = render_pair(p, st)
        n = len(p.span_map.entries)
        print(f"{p.id}: rendered, {n} span entries", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
