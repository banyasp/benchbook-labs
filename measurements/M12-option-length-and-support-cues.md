# M12 · Shortcut cues in the scenario store: gold option length and fact support

**Status: COMPLETE (CORRECTED 2026-11-11 ~17:30 UTC).** The first version (copy in
`versions/M12-option-length-and-support-cues.v1-wrong-tie-handling.md`) reported "gold is the longest option in 66% of
anchors vs 44% chance". **That was wrong**: the metric (`drift()` in `code/pipeline/ops/analytics.py`, word-count
rank) counted a TIE for longest as "longest", and the chance level used 1/n, which ignores ties. Peter chose to "fix at
anchors first" on the strength of the wrong number; see "Consequence" below.

## What was measured
- **Question.** Do two shortcut cues Peter asked to watch (CLAUDE.md: answer length, number of supporting facts)
  appear in the scenarios? R6 requires a "longest option" baseline to score at chance.
- **Data.** All 1,082 anchors in `data/store/scenarios/*/` (no lineage parent) and the 371 derived outputs in the
  store after the operator-lineage migration (`results/ops/ANALYTICS-20261111.md`).

## How
- Corrected metric (`pipeline.ops.analytics.drift`, deterministic): option length in characters; "gold uniquely
  longest" = the gold is the single longest option; chance = 1/n for scenarios with a unique longest option, 0 when the
  longest is tied; gold/other length = gold characters / mean characters of the other options.
- Anchors: ad-hoc loop over every anchor (2026-11-11, not saved as a script; same definitions as the fixed `drift`).
- Derived outputs: `PYTHONPATH=code .venv/bin/python -m pipeline.ops analytics --out results/ops/ANALYTICS-20261111.md`.
- LLMs: none in this measurement.

## What was observed
- **Anchors: no length cue.** Gold uniquely longest by characters in 424/1,082 (39%); chance 39%. Gold length / mean
  other length: median 1.00, mean 1.003. By option count: 2 options 46% (chance 50%), 3 options 30% (33%), 4 options
  22% (25%). By words: uniquely longest 23% (chance 23%), tied 40%.
- **Transfer sisters: a real length cue.** Gold uniquely longest in 40/63 accepted transfer outputs vs 26 expected
  by chance; gold about 15% longer than the other options on average (ratio 1.15). The cross-domain writer
  (`pipeline/transfer/prompts/write.v1.md`) elaborates the chosen option.
- Other operator outputs are at chance: flips 34/106 (chance 38; ratio 0.99), rewords 26/78 (24; 0.99), target_f
  13/45 (14; 1.00), judgment_edit 26/66 (19; 1.03, slight).
- **Fact support** (facts cited by considerations favoring the gold vs each other option): 5.8 vs 1.3 in anchors.
  This follows from the weighing (the considerations that decide the case favor the gold); every fact appears in the
  trace whatever it supports, so it is not a surface cue a model can read without weighing. Kept as a monitor.

## Consequence
- The fix belongs after the transfer writer, not at the anchors: `surface_edit` mode `match_options` (built
  2026-11-11) runs as a step after `transfer` in the pair-dataset recipe.
- Logged: O22 (corrected), R6 (corrected).
