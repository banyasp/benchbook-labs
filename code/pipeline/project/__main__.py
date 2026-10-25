import argparse
import json
import sys

from pipeline.store import DATA, Store

from . import project_all


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.project")
    ap.add_argument("--version", required=True)
    ap.add_argument("--all", action="store_true", help="all pairs in the store (default; kept for symmetry)")
    ap.add_argument("--pair", action="append", help="only these pairs (repeatable)")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--equities")
    ap.add_argument("--mode", default="B", choices=["B", "C", "Cprime"])
    a = ap.parse_args(argv)
    st = Store(a.data)
    pairs = [st.pair(p) for p in a.pair] if a.pair else None
    m = project_all(st, a.version, pairs, a.equities, a.mode)
    print(json.dumps({k: m[k] for k in ("version", "counts", "skipped", "by_intent", "by_relation", "files")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
