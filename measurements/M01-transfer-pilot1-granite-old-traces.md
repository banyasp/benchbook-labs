# M01 · Transfer pilot 1, Granite 4.2 8B, old traces (render.v3)

**Status: SUPERSEDED.** The run is complete (464 of 464 samples, 2026-11-09 17:34-20:17 UTC), but the X1 traces it
used were later re-rendered (M04) because they carried framing cues (M02).

## What was measured
- **Metric.** Verdict accuracy against X1's own answer key, plus the copy rate of the served case's verdict, per arm.
- **Population.** 10 X1 anchors, k=8 replies per cell, mode C, 12,000-token budget.

## What was observed

| Arm | Samples | Accuracy [95% CI] | Copies the case's verdict |
|---|---|---|---|
| no case | 80 | 8% [0-16] | — |
| own case | 80 | 89% [78-99] | — |
| transferred sister | 128 | 58% [42-72] | 58% |
| flipped sister | 96 | 5% [0-11] | 62% |
| other anchor's sister | 80 | 14% [4-25] | — |

Paired per-X1 differences: transfer − no case +51 points [+36, +65]; own case − no case +81; flip − no case −5.

## How
- **Run.** `PYTHONPATH=code .venv/bin/python -m eval.allpairs run --run results/transfer/pilot1 --cells <pilot1 cells> -k 8 --max-tokens 12000`
  followed by `python -m eval.transfer_report --run results/transfer/pilot1`. Method: see the README, "Shared method".
- **LLMs.**
  - Policy: Granite (local vLLM).
  - Judge: Jev Choice maps each verdict to an option.
  - Inputs: the sisters (GPT-6 Luna writer) and the traces (GPT-6 Luna renderer, render.v3) were made by LLMs.
- **Data.**
  - `results/transfer/pilot1/`: `config.json` (cells, settings), `samples.jsonl` (one row per reply, with
    `parsed_choice`, `translated_choice`, `gold_choice`, `correct`, `off_menu`), `raw/` (replies), `details/` (judge
    alignments), `report.md`.

## Key observations
- The no-case accuracy of 8% is below chance (about 42% for these X1s). M02 traces it to the traces, not the scorer.
- The flipped sister drives accuracy to 5% while Granite copies the case's verdict 62% of the time. This was the first
  sign of the copying problem (M08).
- Interpretation: `docs/OBSERVATIONS.md` O14, O15.
