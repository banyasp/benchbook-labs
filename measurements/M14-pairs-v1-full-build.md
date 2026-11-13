# M14 · 2026-11-13 · pairs-v1 full build: yields per arm

**Status: COMPLETE** (build and assemble; console spot-check pending).

## Question

How many pairs-v1 cells does the full anchor set yield per arm, once every operator recipe has run?

## Data

- Inputs: `data/datasets/pairs-v1/full-anchors.txt`, 878 eligible anchors (811 have a rendered trace).
- Build: `pipeline.datasets.pairs_v1 build --tag full`, started 2026-11-12T16:23Z. It stalled for about 3.5 hours;
  it was diagnosed from stack dumps, fixed, and resumed 2026-11-13T01:33Z with `resume`, finishing at about 03:30Z.
  - Cause: every revised job parsed the whole store (~7,200 files) in `revise_card.target_tally`, and
    `Store.scenario_path` globbed the store per lookup. That CPU work starved the other recipes' threads.
  - Fix: tally only the revise outputs; add an id→path index. Commit 0d86ad96.
- Run logs: `results/ops/runs/pairs_v1_*-20261112T162326Z.jsonl`. Summary: `data/datasets/pairs-v1/build-full.json`.
- Assembled 2026-11-13T04:32Z: `data/datasets/pairs-v1/cells-full.json` (not in git).

## Results

| arm | cells |
|---|---|
| self | 878 |
| transfer | 514 |
| transfer_flip | 570 |
| same_domain_flip | 1,006 |
| noflip | 478 |
| revised | 392 |
| neighbor | 548 |
| random | 878 |
| **all** | **5,264** |

- Answer keys: X1 gold for 4,872 cells. For the 392 revised cells, C′'s verdict mapped onto X1's options by text.
- 16 operator jobs errored across the recipes (counts in `build-full.json`); those cells are absent.
- Killed in-flight jobs may have left orphan revise scenario files in the store (not yet checked).

## LLMs in the loop

The operators (transfer, neighbor, flip, revise_card) call their configured Bedrock roles. Usage was not metered
(known gap). Assembly is code only.
