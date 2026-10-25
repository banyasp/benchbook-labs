"""python -m pipeline.ingest {registry|acquire|normalize|extract [--source ID]|import-pilot|status}"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from pipeline.store import DATA, Store

from . import registry as R


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.ingest", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("registry")
    a = sub.add_parser("acquire"); a.add_argument("--refresh", action="store_true")
    sub.add_parser("normalize")
    e = sub.add_parser("extract"); e.add_argument("--source"); e.add_argument("--episode", type=int)
    sub.add_parser("import-pilot")
    sub.add_parser("status")
    args = ap.parse_args(argv)

    if args.cmd == "registry":
        print(R.write_registry())
    elif args.cmd == "acquire":
        from .acquire import acquire
        acq = acquire(R.load_registry()["sources"], R.load_acquired(), refresh=args.refresh)
        R.save_acquired(acq)
        for k, v in acq.items():
            print(k, v["sha12"])
    elif args.cmd == "normalize":
        from .normalize import normalize
        acq = R.load_acquired()
        for s in R.load_registry()["sources"]:
            out = normalize(acq[s["id"]]["sha256"], s["format"])
            print(s["id"], out, sum(1 for _ in open(out)), "paragraphs")
    elif args.cmd == "extract":
        from .extract import extract_all
        for line in extract_all(args.source, args.episode):
            print(line)
    elif args.cmd == "import-pilot":
        from .importpilot import import_pilot
        for sid in import_pilot():
            print(sid)
    elif args.cmd == "status":
        st = Store()
        print("raw:", len([p for p in (DATA / "raw").glob("*") if not p.name.endswith(".meta.json")]) if (DATA / "raw").exists() else 0)
        print("docs:", len(list((DATA / "docs").glob("*.jsonl"))) if (DATA / "docs").exists() else 0)
        sc = st.scenarios() if (st.root / "scenarios").exists() else []
        print("scenarios:", len(sc), dict(Counter(s.split for s in sc)))
        for s in sc:
            n, g = len(s.case.facts), len(s.grounded_facts())
            print(f"  {s.id:34} {s.split:9} {s.verdict_tier:15} facts {g}/{n} grounded  choice {s.case.verdict.choice}  tags {s.tags}")


if __name__ == "__main__":
    main()
