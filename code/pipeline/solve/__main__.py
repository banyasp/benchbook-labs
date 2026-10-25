import argparse
import json
import sys

from pipeline.store import DATA, Store, write_json

from . import acceptance_report, solve_pair


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.solve")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pair")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--equities", help="equities yaml path or set id (default: the T scenario's, else `pilot`)")
    ap.add_argument("-n", type=int, help="samples per pair (default: role teacher samples)")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--require-touched", action="store_true", help="also require the touched condition to be cited (R25)")
    a = ap.parse_args(argv)
    st = Store(a.data)
    pairs = st.pairs() if a.all else [st.pair(a.pair)]
    done = []
    for p in pairs:
        if not p.trace:
            print(f"{p.id}: no trace, skipped (run render)", file=sys.stderr)
            continue
        if p.solve and not a.redo and not a.pair:
            done.append(p)
            continue
        p = solve_pair(p, st, a.equities, a.n, require_touched=a.require_touched)
        done.append(p)
        print(f"{p.id} [{p.intent}]: {sum(s.accepted for s in p.solve)}/{len(p.solve)} accepted", file=sys.stderr)
    rep = acceptance_report(done, st)
    write_json(st.root / "solve.acceptance.json", rep)
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
