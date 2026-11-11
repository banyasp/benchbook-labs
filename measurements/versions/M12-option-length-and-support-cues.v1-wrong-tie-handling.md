# M12 · Shortcut cues in the scenario store: gold option length and fact support

**Status: COMPLETE**, 2026-11-11 (one pass over the store; re-run after new data with the commands below).

## What was measured
- **Question.** Do two shortcut cues Peter asked to watch (CLAUDE.md: answer length, number of supporting facts)
  appear in the scenarios? R6 requires a "longest option" baseline to score at chance.
- **Data.** 985 corpus anchors (`data/store/scenarios/CORPUS*/`, no lineage parent; scenarios the drift function
  could not read were skipped) and the 371 derived outputs in the store after the operator-lineage migration.

## How
- Code: `pipeline.ops.analytics.drift` (deterministic; option length = words in `do`; support = facts cited by the
  considerations that favor each option).
- Anchors: an ad-hoc loop over `drift(case_dict(S))` for every corpus scenario without a parent (run 2026-11-11, not
  saved as a script; same function as the analytics report).
- Derived outputs: `PYTHONPATH=code .venv/bin/python -m pipeline.ops analytics --out results/ops/ANALYTICS-20261111.md`.
- LLMs: none in this measurement (the scenarios themselves were written by the extraction and operator LLMs).

## What was observed
- **Gold is the longest option in 66% of corpus anchors (646/985); chance is 44%** (mean of 1/n options). Derived
  outputs inherit it: gold longest in 42/78 rewords, 47/63 transfers, 51/106 flips.
- **Gold position is balanced** in the anchors (2 options: 302/305; 3 options: 122/122/122).
- **Facts supporting the gold vs each other option: 5.8 vs 1.3** (mean per anchor). Rewords 8.2 vs 0.1; flips 6.2 vs
  1.5; target_f 9.1 vs 0.4.
- **Caveat.** These are scenario-level counts. The agent sees the rendered trace, whose option wording and fact
  presentation differ; a trace-level length check and a "longest option" baseline on the eval runs are still to do.
- Logged: O22; R6 updated.
