# M19 · 2026-11-14 · Autoresearch: one-epoch LoRA SFT hyperparameters

**Status: PARTIAL** (started 2026-11-14 ~21:30Z; first five trials queued: baseline, baseline seed 1, learning rate
2e-4 / 4e-4 / 5e-5). Update as trials finish.

## Question

Peter (2026-11-14): with SFT fixed at one epoch, which hyperparameters (learning rate, LoRA rank, batch, schedule...)
give the best model, found by an autoresearch-style loop (Karpathy) while the GPU is otherwise free?

## Method

- Rules of the loop: `code/training/autoresearch/program.md`. Trial runner `code/training/autoresearch/run_trial.py`,
  queue runner `code/training/autoresearch/queue.sh` (log `logs/autoresearch-queue.log`).
- Proxy trial: one epoch on an arm-stratified quarter of the gen1 training rows (554 of 2,210;
  `results/sft/autoresearch/subset-train-q1.jsonl`, `random.Random('autoresearch-q1|0')`), ~69 optimizer steps at
  effective batch 8; validation loss on all 296 gen1 validation rows at the end. Base config
  `code/training/configs/sft_lora.v4-1epoch.yaml`.
- Winners are confirmed on full data (`--full`), then evaluated behaviorally like gen1 (pairs-v1 val cells, format v4,
  mode B, per relationship) before any default changes.
- Every trial: `code/training/autoresearch/results.tsv` and `trials/<name>.yaml` (in git);
  `results/sft/autoresearch/<name>/` on the box (config, log, checkpoints). wandb project `benchbook`, group `sft`,
  run names `ar-NNN-<time>` (metrics only).
- LLM involvement: none beyond the trained model. The choice of the next trial is Claude's (recorded per trial in
  `desc`).

## Results

Validation loss after one epoch on the q1 subset (lower is better). Full rows: `code/training/autoresearch/results.tsv`.

| Trial | Change | val loss | val token acc | train loss | min |
|---|---|---|---|---|---|
| ar-000 | baseline (lr 1e-4, r 16, alpha 32, eff. batch 8, cosine, warmup 0.05) | 0.45964 | 0.86483 | 0.52722 | 63.1 |
| ar-001 | baseline, seed 1 | 0.45873 | 0.86527 | 0.52546 | 63.2 |
| ar-002 | lr 2e-4 | 0.44728 | 0.86730 | 0.51141 | 63.2 |
| ar-003 | lr 4e-4 | 0.44134 | 0.86876 | 0.50781 | 63.2 |

**Noise floor (seed):** the two baseline seeds differ by 0.00091 in validation loss. One pair is a thin estimate, so a
change is counted only if it beats the better baseline (0.45873) by at least 0.002 (about twice the seed gap);
anything closer needs a second seed before it is adopted.
