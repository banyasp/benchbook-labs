# M07 · Transfer pilot 2, Granite 4.2 8B, YAML-only reasoning (mode C)

**Status: COMPLETE.** 1,208 of 1,208 samples.
- The run started 2026-11-09 23:45 UTC.
- It died when the Claude session ended (2026-11-10 05:54 UTC, at 859 samples).
- It was restarted detached (`nohup setsid`) with the same `config.json`; completed samples were skipped.
- It finished 2026-11-10 18:22 UTC.

## What was measured
Same cells, traces, equities and k as M06. Granite runs in mode C (the seven YAML steps are written inside `<think>`),
with a 12,000-token budget.

## What was observed

| Arm | X1s | Samples | Accuracy [95% CI] | Copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 224 | 45% [32-60] | — |
| own case | 28 | 224 | 81% [72-88] | — |
| transferred sister | 28 | 320 | 73% [63-83] | 73% |
| flipped sister | 20 | 216 | 19% [8-33] | 57% [42-72] |
| other anchor's sister | 28 | 224 | 46% [33-59] | — |

Paired per-X1 differences:
- transfer − no case: +28 points [+15, +41].
- transfer − decoy: +28 [+14, +41].
- own case − no case: +36 [+22, +50].
- flip − no case: −24 [−37, −11].

**Off-menu and truncation by arm.** "Truncated" means the reply hit 12,000 tokens; "thinking" counts characters of
YAML-in-think.

| Arm | Off-menu | Truncated | Mean thinking characters |
|---|---|---|---|
| no case | 9% | 1% | 9,620 |
| own case | 9% | 8% | 13,287 |
| transferred sister | 9% | 9% | 14,851 |
| flipped sister | 8% | 8% | 15,983 |
| other anchor's sister | 17% | 4% | 14,783 |

## How
- **Run.** `PYTHONPATH=code .venv/bin/python -m eval.allpairs run --run results/transfer/pilot2 --cells results/transfer/pilot2/cells.json -k 8 --max-tokens 12000 --concurrency 24`;
  then `eval.transfer_report --run results/transfer/pilot2`.
- **Off-menu and truncation tables.** `PYTHONPATH=code .venv/bin/python -m eval.analysis.mode_compare --runs pilot2 pilot2-luna --out results/transfer/MODE-COMPARE-pilot2-granite-C-vs-luna-full-20261110.md`
  (deterministic).
- **LLMs.**
  - Policy: Granite on local vLLM (bf16).
  - Judge: Jev Choice.
- **Data.** `results/transfer/pilot2/` (`samples.jsonl`, `raw/`, `details/`, `report.md`); log `logs/pilot2-granite.log`.

## Key observations
- **Granite gains a lot from a same-K case** (+28 over no case), but a flipped case drives it 24 points below no case.
  It copies the case's verdict 57% of the time even when that verdict is wrong for X1.
- **Against Luna** (M06), the gap is 10-21 points on most arms and 57 points on the flip arm.
- **About 8-9% of the replies on the case arms truncate at 12,000 tokens.** This slightly understates mode C on those
  arms.
