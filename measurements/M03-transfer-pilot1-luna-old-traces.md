# M03 · Transfer pilot 1, GPT-6 Luna, old traces (render.v3)

**Status: SUPERSEDED.** The run is complete (464 of 464 samples, 2026-11-09 20:06-20:21 UTC). It used the same old
traces as M01.

A 2-sample smoke run, in which Luna refused to give "private step-by-step reasoning", is archived at
`/tmp/claude-1000/-home-ubuntu/4e83879d-8bf3-416b-b63a-9e4e4e93dd18/scratchpad/pilot1-luna-smoke1/`. After it, one
sentence was added to the start instruction saying the YAML is a decision record for the deployer.

## What was measured
- **Question.** Is the low no-case accuracy and the flip-arm copying specific to the 8B model, or does a frontier model
  show it too on the same cells and traces?
- **Population.** 10 X1s, k=8 per cell, mode C format, 16,000-token budget.

## What was observed

| Arm | Samples | Accuracy [95% CI] | Copies the case's verdict |
|---|---|---|---|
| no case | 80 | 8% [0-20] | — |
| own case | 80 | 54% [32-72] | — |
| transferred sister | 128 | 41% [21-63] | 41% |
| flipped sister | 96 | 43% [20-65] | 14% |
| other anchor's sister | 80 | 15% [0-39] | — |

**Breakdown of Luna's no-case replies (Claude-read / ad-hoc queries):**
- 32% gave no YAML verdict (Luna wrote its own free-form "disposition").
- 51% were off-menu (it decided the surface step, e.g. verifying a routing code).
- On-menu accuracy was 46%.
- On the 5 X1s with a non-gold course in the system prompt: 0 of 40.

## How
- **Run.** `eval.allpairs run --run results/transfer/pilot1-luna --model luna ...`, then `eval.transfer_report`.
- **LLMs.**
  - Policy: GPT-6 Luna on Bedrock.
  - Judge: Jev Choice.
  - The no-case breakdown is Claude-read, from queries and from reading replies.
- **Data.** `results/transfer/pilot1-luna/` (`samples.jsonl`, `raw/`, `report.md`). Examples:
  - `raw/luna_control_DR-CORPUS-NS-7d5e5ea6-E6_v1_-_0.txt`: free-form disposition citing the authority.
  - `raw/luna_control_DR-CORPUS-NX-09fb3b9c-E2_v1_-_0.txt`: decides the routing-code step.

## Key observations
- Both models scored 8% with no case, for different reasons. This pointed at the traces (M02).
- Luna does not copy the flipped case (14%) where Granite does (62%). Copying is a Granite weakness, not a property of
  the cells.
- Interpretation: `docs/OBSERVATIONS.md` O15.
