# M17 · 2026-11-14 · SFT gen1 vs base Granite on the pairs-v1 val cells, per case-trace relationship

**Status: COMPLETE** (val split; test untouched).

## Question

Does LoRA SFT on gen1 (M15, M16) make Granite reason better from served cases, for each relationship between the
served case and the live trace, including the three extension arms gen1 never trained on? Which checkpoint: the final
adapter (step 554, end of epoch 2) or checkpoint-300 (just past the end of epoch 1)?

## Data

- Cells: `results/pairs-v1/eval-val/cells-val.json`, 485 cells over 61 val-split X1s (51 families): the 384 base
  pairs-v1 val cells with a trace plus 101 extension-arm val cells (M18: flip_neighbor 48, xd_neighbor 32, xd_noflip
  21); plus the no-case control per X1. k = 4: 2,184 replies per model.
- No leakage: train and val share no X1 (438 vs 61) and no family (0 of 51). The only scenarios in both are the
  unrelated arm's served cases, which are train anchors by design (CLAUDE.md, SFT scope).
- Runs (registered in `measurements/runs.yaml`, M17):
  - `results/pairs-v1/eval-val/base-v4B`: base Granite 4.2 8B.
  - `results/pairs-v1/eval-val/sft-final-v4B`: + LoRA `results/sft/run-gen1/adapter`.
  - `results/pairs-v1/eval-val/sft-ckpt300-v4B`: + LoRA `results/sft/run-gen1/checkpoint-300`.

## Method

- Command: `scripts/sft_eval_val_chain.sh` → `eval.allpairs run --cells cells-val.json --model {base,sft} --mode B
  --scaffold v4 -k 4 --max-tokens 8000 --concurrency 12`. Scaffold v4 = format v4, analogical prompt, modes v1, equities
  pilot2: byte-identical to the SFT training prompts. Mode B: no thinking block. vLLM serves base + the adapter as
  model `sft`. 2026-11-14: base and final 06:11-16:19Z (together), checkpoint-300 16:20-21:27Z.
- Scoring: allpairs-scoring-v3 (Jev Choice option alignment, OpenRouter). Answer key per cell: X1's gold, except the
  revised arm (C′'s verdict, R94).
- Tables: `PYTHONPATH=code .venv/bin/python -m eval.analysis.m17_sft_val` → `results/pairs-v1/eval-val/m17-report.md`
  (+ `.json`). X1-averaged, 95% family bootstrap (B = 2000).
  - **Text-corrected accuracy (the headline):** when a reply's options list repeats X1's option texts verbatim, its
    choice is mapped by that text instead of by the judge. Reason: R98. The adapter numbers the options differently
    from the key in ~45% of in-domain replies, and the judge then fails on about a third of them (scored off-menu).
    Wherever the judge did map such a reply, it agreed with the text (0 disagreements), so the correction only rescues
    judge failures. As-scored numbers are given too.
  - Copy rate: the choice equals the served case's verdict traced back to X1's options through the cell's operator
    chain (`eval.analysis.tensor.served_verdict_live`, new today; the pilot-2 function assumed a single permutation and
    under-read copying on chained cells).
- LLMs: the policy (Granite, base and LoRA, local vLLM); judge Jev Choice for option alignment; Claude-read: the
  verbatim-option and label-swap counts and the cue check below (queries saved in `m17_sft_val.py` except the cue
  check, which was an ad-hoc query).

## Results

**Choice accuracy, text-corrected** (% of replies on the cell's key; * = extension arm, not in gen1):

| Relationship | replies | base | SFT ckpt-300 | SFT final |
|---|---|---|---|---|
| No case | 244 | 51.6 [41.5, 61.5] | 61.5 [51.9, 71.3] | 57.8 [48.7, 66.0] |
| Own case | 244 | 85.2 [77.5, 91.9] | 98.4 [96.1, 100.0] | 98.8 [97.2, 100.0] |
| Revised case | 120 | 95.5 [87.5, 100.0] | 96.0 [91.1, 99.1] | 96.0 [91.1, 99.6] |
| In-domain neighbor | 180 | 80.0 [70.7, 88.6] | 95.0 [91.9, 97.8] | 95.0 [91.5, 97.9] |
| Non-flip edit | 148 | 89.2 [82.4, 95.2] | 99.3 [97.8, 100.0] | 100.0 [100.0, 100.0] |
| Cross-domain transfer | 156 | 76.3 [66.4, 85.0] | 96.2 [92.9, 98.7] | 97.4 [94.7, 99.4] |
| Cross-domain neighbor* | 128 | 68.0 [54.8, 79.8] | 90.6 [82.8, 96.9] | 85.9 [77.3, 93.8] |
| Cross-domain non-flip edit* | 84 | 91.2 [82.1, 97.6] | 96.9 [92.9, 100.0] | 97.5 [93.4, 100.0] |
| In-domain flip | 272 | 3.8 [0.5, 7.9] | 89.5 [82.9, 94.9] | 95.3 [92.2, 97.8] |
| Flip-neighbor* | 192 | 15.9 [8.8, 23.6] | 79.6 [69.8, 87.8] | 90.9 [84.7, 95.9] |
| Flip-transfer | 172 | 18.4 [8.3, 29.5] | 79.0 [70.7, 87.1] | 80.1 [69.1, 89.8] |
| Unrelated case | 244 | 46.7 [38.1, 55.0] | 61.9 [52.9, 70.3] | 62.7 [53.5, 70.8] |

**As scored (judge only)**, where it differs by more than a point: own case 85.2 / 81.6 / 89.3; revised 95.5 / 71.9 /
76.8; non-flip edit 88.9 / 82.3 / 81.2; in-domain flip 3.8 / 73.9 / 82.1; flip-neighbor 15.9 / 77.1 / 89.6; cross-domain
neighbor and the other cross-domain arms are unchanged (few verbatim lists there). Full tables in the report.

**Copied the served case's verdict** (text-corrected; on the three flip arms copying is the error):

| Relationship | base | SFT ckpt-300 | SFT final |
|---|---|---|---|
| In-domain flip | 95.5 | 8.9 | 3.6 |
| Flip-neighbor* | 73.2 | 11.0 | 5.0 |
| Flip-transfer | 71.3 | 12.0 | 14.0 |
| In-domain neighbor / transfer / cross-domain neighbor* (follows) | 90.9 / 86.3 / 78.9 | 99.4 / 96.8 / 94.3 | 98.9 / 97.4 / 93.0 |

**Relation label correct** (base / ckpt-300 / final): in-domain flip 0.0 / 93.3 / 96.7; flip-neighbor* 2.0 / 88.4 / 93.6;
flip-transfer 0.0 / 86.8 / 87.5; unrelated (`not_governed`) 32.5 / 95.1 / 97.1; own case 95.9 / 98.8 / 97.5;
cross-domain transfer 90.2 / 91.7 / 94.2; cross-domain neighbor* 84.1 / 90.6 / 93.8. No arm with a relevant case is
labelled `not_governed` more than 5.9% by the adapter (flip-transfer).

**Unrelated case, agreement with the model's own no-case choice** (Peter's metric for this arm): base 76.2
[70.5, 82.1] against its no-case leave-one-out baseline 79.6 [72.7, 85.9]; ckpt-300 71.9 vs 78.1; final 68.6 [61.3,
75.1] vs 75.6 [67.5, 83.6].

**Format:** no verdict 0-4.7% per arm for base, 0-0.4% for both adapters; no truncation.

## Readings (Claude)

- **SFT gen1 fixes the flip.** Base Granite copies an in-domain flip's verdict in 95.5% of replies and is right 3.8%
  of the time; the final adapter copies 3.6% and is right 95.3%, labelling 96.7% of them `flips`. Flip-transfer goes
  18.4 → 80.1, the weakest of the flip arms (cross-domain and flipped at once).
- **It generalizes to relationships it never trained on.** Flip-neighbor 15.9 → 90.9, cross-domain neighbor 68.0 →
  85.9, cross-domain non-flip edit 91.2 → 97.5. So the adapter did not memorize the seven trained arms.
- **Cue check (ad hoc, Claude):** flip cells' served cases list one would_change item (632 of 636 flip replies; follows
  cases list one or two), and in 172 of the 636 it is `flip2` alone, which never happens in a follows case. The adapter does not use it: flip
  cells whose only item is `flip1` (indistinguishable by id and count from 652 follows replies' cells) are 94.3% right,
  while those follows cells stay 96.3% right; lone-`flip2` flip cells are lower (73.3%). Content-level cues are not
  ruled out.
- **Revised = own case, as Peter expected** (each against its own key): adapter 96.0 vs 98.8; base 95.5 vs 85.2.
- **Unrelated case:** the adapter now says the case does not govern (32.5 → 97.1%) and gets more choices right
  against the key (46.7 → 62.7), but its choices agree with its own no-case choices 7 points less than its no-case
  replies agree with each other (68.6 vs 75.6; base 76.2 vs 79.6). Within the intervals, but the direction is the one
  to watch: after `not_governed` the adapter does not simply decide as it would without a case (its training targets
  follow the answer key, not its own no-case choice).
- **No case:** +6.2 (final) / +9.9 (ckpt-300) over base: some plain weighing improves too, without a case.
- **Checkpoint:** the final adapter is ahead on in-domain flip (95.3 vs 89.5) and flip-neighbor (90.9 vs 79.6),
  checkpoint-300 on cross-domain neighbor (90.6 vs 85.9) and no case (61.5 vs 57.8); every interval overlaps. The
  second epoch bought a little flip performance at no measurable cost. This does not overturn Peter's one-epoch
  decision (M16): checkpoint-300 was taken mid-schedule (learning rate still ~half its peak), and a one-epoch run whose
  schedule decays to zero should end at or above it. The gen2 run will show.
- **Scoring artifact (R98, O30):** the adapter copies X1's option list verbatim from in-domain served cases and
  numbers it in the case's order; the judge fails on about a third of those. As-scored numbers understate the adapter
  by up to 19 points (revised).

## Caveats

- 61 X1s, 51 families, k = 4: intervals are ±3-10 points on most arms; the random-arm no-case agreement differences
  are within them.
- Mode B (no thinking) for both base and adapter; base Granite in M11 was evaluated with thinking.
- The text correction applies only to replies that list X1's option texts verbatim; it changes no judge-mapped choice.
  Adopting it in the scorer is Peter's call (R98).
- Val only. Test stays untouched until the checkpoint and settings are fixed.

## Next

- Peter: adopt the exact-text pre-pass in the scorer (R98)? If yes, rescore all runs from the saved details.
- Gen2 scope (extension arms, distinguished arm) and the autoresearch result (M19) decide the next SFT run.
- Read a sample of flip-transfer failures (the weakest arm at 80.1) and of unrelated-arm replies that disagree with
  the no-case choice.
