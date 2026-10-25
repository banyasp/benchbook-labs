# Benchbook exemplar schema review — 2026-09-30

Adversarial review of the v6 exemplar schema, mapping and solver, a cross-domain literature pass on how cases are represented and reasoned from, and a working prototype of the proposed replacement (v7, "the decision record").

**Main write-up (Claude Doc; revision history keeps the pre-audit version, rev 14):** https://claude.ai/code/artifact/a78af287-c8b2-40a3-a478-3bbf9d01be70 — bottom line, what breaks, what other traditions teach, v6.1 vs v7, the v7 schema, mapping v2, solver v3 results, reward v2, labeling plan, and the twelve decisions for Peter.

## Layout

| Folder | What it holds |
|---|---|
| `BRIEF.md` | The brief every research agent worked from (the v6 schema, known problems, what earlier strands covered) |
| `specs/` | `SPEC-v7-v1.md` (first design) and `SPEC-v7-v2.md` (after two implementation rounds). v7.0 will follow Peter's decisions |
| `research/` | Strands 22–27: analogy cognition and philosophy of reasons (incl. qiyās, Qing *bifu*, Talmud); decision analysis, planning, command, DMN, design rationale; expert judgment, medicine, SPJ, safety, hindsight review, ACH; ML case representations 2023–26 (contextual integrity, RLVR failure modes); legal formalisms for the gaps (n-ary, scaled factors and Horty 2021, balancing, inconsistent precedent, incomplete facts, per-allegation records); the shape of Peter's own seed data. Every claim carries a verification tag |
| `review/` | `REDTEAM.md` (3 critical, 8 major, 8 minor findings against v6, all with scripts in `review/redteam/`) and `FACTCHECK.md` (221-row verification of strands 22–26; corrections were applied in the doc, not in the strand files), and `DOC-AUDIT.md` (an independent audit of the doc; its fixes were applied in the doc's revision of 2026-09-30) |
| `hard-calls-v7/` | Six Hard Calls converted to v7 by hand: `round1/` against spec v1, `round2/` against spec v2 (with `catalog-CORE.yaml`), each with a conversion log of fits and misfits |
| `code/` | The v7 prototype, round 2 (current): `solver_v3.py`, `reward_v2.py`, `validate_v7.py`, `v7.schema.json`, catalogs, records (v6 examples, 10 DOHA + 3 FISC converted, six Hard Calls under `records/hc/`), tests, `results/` (REPORT.md = round 1, r2-results.md = round 2, doha-v3.md) |
| `code_r1/` | Snapshot of the prototype after round 1 (spec v1) |
| `src/` | Read-only copies of the inputs the code reads (solver_v2/reward from Extension Training/schema, the Hard Calls YAML, the unzipped DOHA pilot) so everything runs from this folder |

## Run it

Needs Python 3.10+, `pyyaml`, `pytest`.

```bash
cd code
./run_tests.sh            # 84 tests
python3 validate_v7.py    # schema + lints on every catalog and record
python3 doha_study.py     # v2 vs v3 on the DOHA pilot -> results/doha-v3.md
python3 hc_eval.py        # gold-plan round trip on the six Hard Calls
cd ../review/redteam && bash run_all.sh   # re-runs every red-team probe against v6
```

## Status

Prototype, not production. Open items are listed in the doc's section 11 and in `code/results/r2-results.md` ("Remaining spec issues, ranked"). Catalog entries marked `added: prototype` or `author: draft` are placeholders for Peter's judgment.
