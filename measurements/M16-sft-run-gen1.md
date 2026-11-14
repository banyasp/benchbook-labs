# M16 · 2026-11-14 · LoRA SFT of Granite 4.2 8B on gen1 (run-gen1): training and validation loss

**Status: COMPLETE** (training). Behavioral evaluation of the adapter (choice accuracy per relationship) is not yet
run; see "Next".

## Question

Does LoRA SFT on the gen1 targets (M15) fit without overfitting, and which checkpoint should be evaluated?

## Data

- Train: `results/sft/gen1/golden.jsonl`, 2,210 rows (M15: pairs-v1 train cells, every target to the answer key,
  format v4, mode B = no thinking block). 0 rows dropped for length (max_length 16,000; longest row ~11.4k tokens).
- Validation: `results/sft/gen-val/golden.jsonl`, 296 rows built the same way from the val-split cells (never trained
  on). 0 rejected.
- Trained tokens: 5.11M reply tokens per epoch (the prompt is masked).

## Method

- Code: `code/training/sft_lora.py` (TRL 1.12 SFTTrainer, PEFT 0.20); config
  `code/training/configs/sft_lora.v3-gen1.yaml`.
  - LoRA r 16, alpha 32, dropout 0.05, on all attention and MLP projections.
  - lr 1e-4, cosine, 5% warmup; 2 epochs; batch 1 x grad accum 8 (effective 8); bf16, gradient checkpointing, SDPA.
  - Validation loss every 50 steps; checkpoints every 100 steps and at the end.
- Run: 2026-11-13 16:06Z to 2026-11-14 00:57Z on the L40S, 554 steps, 31,740 s (8.8 h; each validation pass ~8 min).
  Log `logs/sft-run-gen1.log`. Metrics in wandb (metrics and metadata only):
  https://wandb.ai/peterbanyas-duke-university/benchbook/runs/prhozfsz (streamed by `training.wandb_tail` from the
  checkpoints, since this run started before wandb was wired in).
- No LLM was involved in this measurement beyond the trained model itself.

## Results

| step | epoch | val loss | val token accuracy | val entropy |
|---|---|---|---|---|
| 50 | 0.18 | 0.4646 | 0.864 | 0.487 |
| 100 | 0.36 | 0.4382 | 0.869 | 0.420 |
| 150 | 0.54 | 0.4289 | 0.871 | 0.432 |
| 200 | 0.72 | 0.4222 | 0.873 | 0.407 |
| 250 | 0.90 | 0.4175 | 0.873 | 0.416 |
| 300 | 1.08 | 0.4175 | 0.873 | 0.383 |
| 350 | 1.26 | 0.4160 | 0.874 | 0.381 |
| 400 | 1.45 | 0.4147 | 0.874 | 0.376 |
| 450 | 1.63 | 0.4135 | 0.874 | 0.374 |
| 500 | 1.81 | 0.4137 | 0.874 | 0.370 |
| 550 | 1.99 | 0.4134 | 0.875 | 0.372 |
| 554 | 2.00 | 0.4134 | 0.874 | 0.372 |

- Training loss: 0.77 at step 5; epoch-1 mean 0.472 (last fifth of epoch 1: 0.434); epoch-2 mean 0.387; final
  reported train_loss 0.429 (whole run). Training token accuracy at the end ~0.88. Grad norm 0.33 to 1.86, no spikes.
- Readings:
  - Most of the fit happens in epoch 1: validation loss falls from 0.465 to 0.4175 by step 250 and only to 0.4134 in
    epoch 2.
  - No overfitting by validation loss: it never rises. But in epoch 2 the training loss drops ~0.05 while validation
    drops ~0.004, so the second epoch is mostly fitting the training rows. A third epoch would not pay.
  - Validation entropy keeps falling in epoch 2 (0.416 -> 0.372) while loss is flat: the model gets more confident
    without getting more right per token. Worth watching for reduced diversity in sampled replies (k > 1 evals, RL).
- **Checkpoint:** evaluate the final adapter (`results/sft/run-gen1/adapter`, = step 554, lowest validation loss) and,
  as the comparison, checkpoint-300 (end of epoch 1). Validation loss cannot separate them; choice accuracy per
  relationship will.

## Caveats

- Validation loss measures imitation of the targets, not decision quality. The targets were written by Granite with
  Luna's notes (88%) or by Luna (2.9%); low loss can partly reflect Granite already writing like this.
- The validation rows come from val-split anchors but the same pipeline and arms, so they do not test new kinds of
  relationship (the extension arms of 2026-11-14 and the distinguished arm are not in gen1).

## Next

- Serve the adapter (`LORA=results/sft/run-gen1/adapter bash code/inference/serve.sh`, mode B: no thinking block) and
  run pairs-v1 val/test cells with format v4 against base Granite, reported per relationship (OUTSTANDING: "pairs-v1
  evals on format v4").
