# pipeline.ops — scenario operators (spec: `context/OPERATORS-SPEC-v1.md`)

Five primitive operators, each `X -> OpResult(X', delta, gates, annotations, writer, solver)`. `record.finish` (code)
turns the result into one lineage step on X', inherits family / split / held-out from X, and stores X' by bucket:
`accepted` → `data/store/scenarios/<family>/`, `hard` / `rejected` → `data/store/held/<bucket>/`. Skips (e.g. a no-op
condition) and writer failures appear only in the run log `results/ops/runs/<recipe>-<ts>.jsonl`.

| Operator | Modes built (v1, no independent solver) | V′ | Module |
|---|---|---|---|
| `permute` | options / facts / considerations; order random, explicit or `gold_to` | held | `permute.py` |
| `surface_edit` | `reword` (wraps perturb.restyle), `neighbor`, `transfer` (setting given or proposed) | held | `surface.py` |
| `structural_edit` | `flip` plain (transfer flip prompt) or indirect (wraps perturb.flip); `target_f` realizing a would_not_change item | Φ `then` / held | `structural.py` |
| `frame_edit` | `drop_option` (a non-gold option; prose fixed by the writer) | held | `frame.py` |
| `judgment_edit` | weights-only revise (wraps perturb.revise_card, `weights_only=True`) | the target | `judgment.py` |

Gates (decide the bucket): structure (code), leak, technique, `condition_realized` (the strict condition verifier: a
check of the edit), `setting_adds` (→ hard). Annotations (never decide): `verdict_shift` with `k_support` (blind solve on
X and X′; `annotate: true`). Solver interface: `solver.py` (LLM backend for annotations and checks only; panel and human
are specified, not built).

## Run

```bash
export PYTHONPATH=code
.venv/bin/python -m pipeline.ops apply structural_edit --scenario <ID> --args '{"mode": "flip", "phi": "flip1"}'
.venv/bin/python -m pipeline.ops recipe code/pipeline/ops/recipes/same_domain_flip.yaml --inputs results/allpairs/B2/x1.txt --dry
.venv/bin/python -m pipeline.ops recipe code/pipeline/ops/recipes/same_domain_flip.yaml --scenario <ID> [--workers 8]
.venv/bin/python -m pipeline.ops analytics --out results/ops/ANALYTICS.md
.venv/bin/python -m pipeline.ops migrate            # dry run: legacy lineage -> steps; --apply writes (versions kept)
```

Recipes (arms as compositions) are in `recipes/`: `same_domain_flip`, `transfer_flip`, `neighbor_control`,
`lookalike_flip`, `noflip`, `drop_option`, `revised`. Planner-expanded arguments (`phi: each`, `order: balance`,
`option: random_nongold`, `setting: propose | {sketch_file}`) are documented in `recipes.py`.

Legacy modules (`pipeline.perturb.*`, `pipeline.transfer.build`, `pipeline.pair.reorder`, `pipeline.ingest.balance_options`)
are still in place; ops wraps or replaces them. Move them to `versions/` once nothing calls them.
