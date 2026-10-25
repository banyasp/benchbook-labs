"""python -m library <command>   (run from the repo root with PYTHONPATH=code)

  validate                     load and cross-check everything under data/ with the 2a models
  list                         cases, equity sets, scenarios
  convert-cases [--case ID]    v2.6 cards -> PDF-format cases via the `converter` role (skips existing; --force redoes, keeping versions)
  build-equities               write data/registry/equities/pilot.yaml (glosses by the converter role)
  build-scenarios              write LiveScenario + AnswerKey files for the pilot live scenarios (deterministic)
  index [--out PATH]           rebuild the SQLite structural index (default results/library_index.sqlite)
"""
from __future__ import annotations

import argparse
import sys

from .store import Library


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="library", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="data")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    sub.add_parser("list")
    cc = sub.add_parser("convert-cases")
    cc.add_argument("--case", action="append", help="source id (INT-301, INT-301-r1, ...); default all pilot cards")
    cc.add_argument("--force", action="store_true")
    be = sub.add_parser("build-equities")
    be.add_argument("--force", action="store_true")
    sub.add_parser("build-scenarios")
    ix = sub.add_parser("index")
    ix.add_argument("--out", default="results/library_index.sqlite")
    a = ap.parse_args(argv)
    lib = Library(a.root)

    if a.cmd == "validate":
        errs = lib.validate()
        print(f"{len(lib.case_files())} cases, {len(lib.scenario_files())} scenarios")
        for e in errs:
            print("  PROBLEM", e)
        print("OK" if not errs else f"{len(errs)} problem(s)")
        return 1 if errs else 0
    if a.cmd == "list":
        print("cases:")
        for c in lib.cases():
            print(f"  {c.id:24} {c.status:13} choice={c.verdict.choice} options={len(c.options)} facts={len(c.facts)} "
                  f"considerations={len(c.considerations)}  {c.title}")
        print("equity sets:")
        for p in sorted(lib.equities_dir.glob("*.yaml")):
            if not p.name.endswith(".meta.yaml"):
                print(f"  {p.stem}: {len(lib.equities(p.stem).equities)} equities")
        print("scenarios:")
        for s in lib.scenarios():
            print(f"  {s.id:16} family={s.family:9} split={s.split:6} variant={s.perturbation.variant:8} arms={','.join(s.arms)}")
        return 0
    if a.cmd == "convert-cases":
        from .convert.cases import SOURCES, convert_card
        ids = a.case or list(SOURCES)
        bad = 0
        for sid in ids:
            r = convert_card(sid, lib, force=a.force)
            print(f"{sid:12} {'OK ' if r.ok else 'FAIL'} attempts={r.attempts} -> {r.path}")
            for e in r.errors:
                print("    attempt error:", e[:300])
            bad += not r.ok
        lib.write_manifest()
        return 1 if bad else 0
    if a.cmd == "build-equities":
        from .convert.equities import build_pilot_equities
        print(build_pilot_equities(lib, force=a.force))
        return 0
    if a.cmd == "build-scenarios":
        from .convert.scenarios import build_all
        report = build_all(lib)
        for line in report:
            print(line)
        return 0
    if a.cmd == "index":
        from .index import build_index
        counts = build_index(lib, a.out)
        print(a.out, counts)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
