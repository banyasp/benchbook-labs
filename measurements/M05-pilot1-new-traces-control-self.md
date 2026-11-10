# M05 · Pilot 1 X1s on re-rendered traces: no case and own case, both models

**Status: COMPLETE** for three runs; **ABORTED** for the Granite render.v4 run. Ran 2026-11-09 22:05-23:14 UTC.

## What was measured
- **Question.** Does fixing the trace framing (M02, M04) remove the below-chance no-case accuracy?
- **Arms.** No case and own case only, on the same 10 X1s, k=8 per cell.

## What was observed

| Run | Traces | Model | No case | Own case | Samples |
|---|---|---|---|---|---|
| M03 `pilot1-luna` (before) | render.v3 | Luna | 8% [0-20] | 54% [32-72] | 160 of 464 |
| `pilot1-v4-luna` | render.v4 | Luna | 54% [31-75] | 84% [61-98] | 160 |
| `pilot1-v5-luna` | render.v5 | Luna | 62% [35-88] | 86% [66-100] | 160 |
| M01 `pilot1` (before) | render.v3 | Granite | 8% [0-16] | 89% [78-99] | 160 of 464 |
| `pilot1-v5` | render.v5 | Granite | 54% [31-75] | 88% [80-94] | 160 |

- **Luna's no-case failures before and after v4.** With no YAML verdict: 32% → 10%. Off-menu: 51% → 26%.
- **ABORTED run.** Granite on render.v4 traces (40 of 160 samples) was stopped because the traces moved to v5
  mid-run, which would have mixed versions. Archived at `results/transfer/versions/pilot1-v4-granite-partial-render-v4/`.
  Do not use it.

## How
- **Run.** `eval.allpairs run` with control and self cells only; `eval.transfer_report`.
- **Traces.** Re-rendered per M04 before the runs started. The trace files were last written 22:17-22:18 UTC; the runs
  started at 22:05 (v4-luna, on v4 traces) and 22:19 or later (v5).
- **LLMs.**
  - Policy: Granite or Luna.
  - Judge: Jev Choice.
  - Traces by the GPT-6 Luna renderer, with LLM gates.
- **Data.** `results/transfer/pilot1-v4-luna/`, `pilot1-v5-luna/`, `pilot1-v5/` (`samples.jsonl`, `raw/`,
  `report.md`).

## Key observations
- Fixing the framing raised no-case accuracy from 8% to 54-62% for both models. The case's benefit over no case stays
  large: +24 to +34 points.
- With n = 10 X1s, the CIs are wide. Pilot 2 (M06, M07) repeats this on 28 X1s.
- Interpretation: `docs/OBSERVATIONS.md` O16.
