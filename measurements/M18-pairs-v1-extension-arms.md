# M18 · 2026-11-14 · pairs-v1 extension arms: cross-domain neighbor, cross-domain non-flip edit, flip-neighbor

**Status: COMPLETE** (build). No model has been evaluated on these cells yet.

## Question

Peter (2026-11-13) asked for three more case-trace relationships: a neighbor of a cross-domain transfer, a non-flip
edit of a cross-domain transfer, and a neighbor of an in-domain flip. Neighbor here means F changes slightly while K
and V stay fixed. What do the operator chains yield, and are the new served cases what the arm says they are?

## Data and method

- Recipes: `code/pipeline/ops/recipes/pairs_v1_ext/`. Each is a chain of existing operators applied to the served
  cases (X2) of an existing pairs-v1 arm, not to anchors, so the lineage chain is anchor -> earlier arm -> extension:

  | arm | input (X2s of) | steps |
  |---|---|---|
  | `xd_neighbor` | `transfer` | surface_edit neighbor (setting proposed) -> match_options -> permute (balance) |
  | `xd_noflip` | `transfer` | structural_edit target_f on each would_not_change item -> permute (balance) |
  | `flip_neighbor` | `same_domain_flip` | surface_edit neighbor -> match_options -> permute (balance) |

- Builder: `python -m pipeline.datasets.pairs_v1 extend --tag full --batch <b>` then `assemble-ext --tag full`.
  - Two batches: `pilot` (100 anchors drawn with `random.Random('pairs-v1-ext-pilot|0')`,
    `data/datasets/pairs-v1/ext-pilot-anchors.txt`), checked by hand, then `rest` (the other anchors). Balanced
    permutes balance within each batch.
  - Output: `data/datasets/pairs-v1/cells-full-ext.json` (cell ids `PV1-full-x00000`...),
    `manifest-full-ext.json`, `attempts-full-ext.jsonl`, `build-full-ext-{pilot,rest}.json`. `cells-full.json` and its
    cell ids are untouched (SFT gen1 and the evals refer to them).
  - Key: X1's gold for all three arms. `phi`: the flip item (flip_neighbor; the neighbor writer keeps flip-condition
    ids and their `then`) or the realized non-flip item (xd_noflip).
- Run 2026-11-14 00:24-02:00 UTC. LLM involvement: the operators' Bedrock roles (GPT-6 Luna as `transfer_writer` and
  `transfer_checker`; gates as in M14). Bedrock spend on 2026-11-14 to this point: $10.44 (estimate, `bench.costs`;
  includes this build and nothing else large).

## Results

| arm | inputs | step-1 outcomes (pilot + rest) | served cells | |
|---|---|---|---|---|
| xd_neighbor | 514 transfers | 447 accepted, 63 hard (setting adds a strong consideration), 4 rejected | 402 (78% of inputs) | |
| xd_noflip | 514 transfers, 531 jobs (one per would_not_change item) | 283 accepted, 138 skipped (item already holds: a no-op, not served), 109 rejected, 1 error | 283 | |
| flip_neighbor | 1,006 in-domain flips | 816 accepted, 163 hard, 27 rejected | 696 (69%) | |
| **total** | | | **1,381** | 729 (with trace 1,282 cells) |

- Later losses on the neighbor arms are at match_options (option_equivalence gate: the rewritten options no longer the
  same course of action): 45 for xd_neighbor, 120 for flip_neighbor.
- xd_noflip rejections: condition_realized (the edit did not make the item true) and writer failures; one job raised
  `KeyError: 'id'` in `_target_f_noflip` (writer output without an id; not retried).
- Split of the anchors (X1): train 764, val 113, test 494, eval-only 10 cells.

  | arm | train | val | test | eval-only |
  |---|---|---|---|---|
  | xd_neighbor | 227 | 34 | 139 | 2 |
  | xd_noflip | 157 | 23 | 98 | 5 |
  | flip_neighbor | 380 | 56 | 257 | 3 |

- Checks:
  - Domain: every xd_neighbor and xd_noflip X2 is in a different domain from its X1 (685 of 685); every
    flip_neighbor X2 is in X1's domain (696 of 696).
  - By hand (pilot, Claude-read): a flip_neighbor (PV1-full-x00007, Iraq 1980 -> a fictional state) keeps the flipped
    verdict ("decides against") and the reversed would_change item, which holds in X1. An xd_noflip (PV1-full-x00017)
    keeps V with the condition realized as a fact.
  - Like the base noflip arm, the realized non-flip item is no longer listed in the served case's flip conditions
    (it now holds as a fact): 0 of 34 pilot xd_noflip X2s and 0 of 40 base noflip X2s list it. Consistent, but it means
    `phi` names an item the model cannot cite.

## Caveats

- The neighbor writer for flip_neighbor works from the flipped case; nothing checks that the neighbor's changed facts
  still make the reversed condition false in X2. Structure (K and V held) is checked; the condition's truth is not.
- No blind-solve check of the new X2s is reported here (the operators annotate it but the run logs do not carry it).

## Next

- Evaluate base and SFT Granite on the val cells of these arms (format v4, mode B) together with the other arms, per
  relationship. Decide with Peter whether gen2 SFT targets include these arms.
