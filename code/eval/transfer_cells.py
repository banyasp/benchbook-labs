"""Cells for a transfer pilot run from a pipeline.transfer build log.

    PYTHONPATH=code .venv/bin/python -m eval.transfer_cells --log results/transfer/build-pilot-20261109.jsonl \\
        --out results/transfer/pilot1/cells.json

Per anchor X1 that has a live trace and at least one ACCEPTED sister: self (X1's own case), transfer (each accepted
sister), flip (each accepted flip), decoy (one accepted sister of another anchor, the one sharing the fewest equities
with X1's considerations). Hard and rejected sisters are left out (hard ones are kept for later).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", required=True, nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from pipeline.store import Store
    st = Store()
    recs = [json.loads(l) for f in a.log for l in Path(f).read_text().splitlines() if l.strip()]
    acc, flips = {}, {}
    for r in recs:
        if r.get("bucket") == "accepted":
            acc.setdefault(r["anchor"], []).append(r["sister"])
        f = r.get("flip") or {}
        if f.get("bucket") == "accepted" and r.get("bucket") == "accepted":
            flips.setdefault(r["anchor"], []).append(f["id"])
    eq = {x: {k.equity for k in st.scenario(x).case.considerations} for x in acc}
    cells = []
    for x1, sis in sorted(acc.items()):
        if not st.has_trace(x1):
            continue
        cells.append({"x1": x1, "x2": x1, "arm": "self"})
        cells += [{"x1": x1, "x2": s, "arm": "transfer"} for s in sis]
        cells += [{"x1": x1, "x2": f, "arm": "flip"} for f in flips.get(x1, [])]
        others = [(len(eq[x1] & eq[o]), o, acc[o][0]) for o in acc if o != x1]
        if others:
            cells.append({"x1": x1, "x2": sorted(others)[0][2], "arm": "decoy"})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(cells, indent=1))
    from collections import Counter
    print(len({c["x1"] for c in cells}), "X1s;", dict(Counter(c["arm"] for c in cells)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
