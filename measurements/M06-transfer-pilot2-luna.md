# M06 · Transfer pilot 2, GPT-6 Luna

**Status: COMPLETE.** 1,208 of 1,208 samples, 2026-11-09 23:11-23:42 UTC.

## What was measured
- **Metric.** Accuracy against X1's key and the copy rate, per arm.
- **Population.** 28 X1 anchors (the batch-2 sisters).
- **Cells.** 28 own-case, 40 transfer, 27 flip, 28 decoy, plus 28 no-case; k=8 per cell.
- **Traces.** render.v5 (see the README's data validity notes). 16,000-token budget.

## What was observed

| Arm | X1s | Samples | Accuracy [95% CI] | Copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 224 | 66% [51-79] | — |
| own case | 28 | 224 | 91% [83-98] | — |
| transferred sister | 28 | 320 | 86% [77-93] | 86% |
| flipped sister | 20 | 216 | 76% [61-89] | 14% [2-28] |
| other anchor's sister | 28 | 224 | 70% [58-81] | — |

Paired per-X1 differences:
- transfer − no case: +20 points [+8, +35].
- transfer − decoy: +16 [+6, +26].
- own case − no case: +25 [+12, +40].
- flip − no case: +13 [−5, +31].

## How
- **Run.** `eval.allpairs run --run results/transfer/pilot2-luna --model luna --cells results/transfer/pilot2/cells.json -k 8 --max-tokens 16000`;
  then `eval.transfer_report --run results/transfer/pilot2-luna`.
- **LLMs.**
  - Policy: GPT-6 Luna on Bedrock (reasoning effort medium, hidden reasoning).
  - Judge: Jev Choice.
- **Cost.** Estimated, not metered: about $0.002 per call, so roughly $2-3 for this run (see the README).
- **Data.** `results/transfer/pilot2-luna/` (`config.json`, `samples.jsonl`, `raw/`, `details/`, `report.md`).

## Key observations
- **The same-K cross-domain case helps** (+20 over no case; +16 over a different-K case), and Luna rarely copies a
  flipped case (14%).
- **The decoy arm declares `not_governed` 97% of the time** (M08). Luna recognizes an irrelevant case and falls back on
  its own judgment.
