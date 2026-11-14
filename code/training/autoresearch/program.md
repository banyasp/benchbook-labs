# Autoresearch: one-epoch LoRA SFT hyperparameters (started 2026-11-14)

Peter, 2026-11-14: "unless we need the GPU for other things, try to autoresearch (as inspired by Andrej Karpathy) to
optimize hyperparams, learning rate, etc. to improve performance within 1 epoch." This file is the loop's rules, the
analogue of autoresearch's `program.md`. Claude is the agent; the GPU runs one trial at a time.

## What is fixed (never changed by a trial)

- **One epoch.** `run_trial.py` forces `num_train_epochs: 1`.
- **Data.** Proxy trials train on `results/sft/autoresearch/subset-train-q1.jsonl`: an arm-stratified quarter of the
  gen1 training rows (554 of 2,210, drawn once with `random.Random('autoresearch-q1|0')`). Confirmation runs (`--full`)
  use all 2,210. The targets, the prompt masking and max_length (16,000) are not tuned.
- **Metric.** Validation loss on all 296 gen1 validation rows (val-split anchors, never trained on), computed once at
  the end of the epoch. Lower is better. Token accuracy and entropy are recorded, not optimized.
- **Model.** Granite 4.2 8B, bf16, LoRA (no full fine-tuning, no quantized training).
- **Keep every result.** Every trial gets a row in `results.tsv` (here and in `results/sft/autoresearch/`), failures
  included (oom, crash, no-eval), and its config in `trials/<name>.yaml`. Trial names are never reused; nothing is
  deleted or reverted. Checkpoints are kept (every 50 steps + the final adapter).

## What a trial may change

`--set` overrides of the base config `code/training/configs/sft_lora.v4-1epoch.yaml`:
- `train.learning_rate`, `train.lr_scheduler_type` (cosine, linear, constant_with_warmup, cosine_with_min_lr with
  `train.lr_scheduler_kwargs`), `train.warmup_steps` (a fraction < 1 or a step count), `train.weight_decay`,
  `train.max_grad_norm`, `train.gradient_accumulation_steps` (effective batch), `train.neftune_noise_alpha`.
- `lora.r`, `lora.alpha`, `lora.dropout`, `lora.target_modules`, `lora.use_rslora`, `lora.use_dora`.
  Serving: `code/inference/serve.sh` LORA_RANK must be >= r (raise it before serving an r > 16 adapter).
- Speed settings (`train.gradient_checkpointing`, `train.per_device_train_batch_size`) are allowed if they do not
  change the math; they only make trials faster. Installing packages (liger-kernel, flash-attn) is out of scope: the
  main `.venv` is not modified.

## The loop

1. Read `results.tsv`. Compare each trial with the baseline and the current best (same data).
2. Pick the next change: one factor at a time around the current best, unless two factors are known to interact
   (learning rate with effective batch; alpha with r: the effective scale is alpha / r, or alpha / sqrt(r) with
   rsLoRA). Write one line in the queue saying what is changed and why.
3. Noise: retrain the baseline with a second seed (`--set train.seed=1`) early, to learn how big a difference has to
   be to count. Do not adopt a change smaller than that.
4. A change that wins on the proxy is confirmed on full data (`--full`, ~4 h) before it becomes the default.
5. The real test is behavior, not loss: the confirmed config's adapter is evaluated like gen1 (pairs-v1 val cells,
   format v4, mode B, per relationship; `scripts/sft_eval_val_chain.sh`). Validation loss measures imitation of the
   targets (M16 caveat); a lower loss that does not improve choices per relationship is not adopted.
6. Record the outcome in `measurements/M19-sft-autoresearch.md` (status, every trial, the command, the reading).

## Known limits of the proxy

- A quarter of the data gives ~69 optimizer steps instead of ~277. The best learning rate for a short run tends to be
  higher than for a long one, so learning-rate winners must be confirmed on full data.
- Validation loss differences in gen1 epoch 2 were ~0.004; differences that small need the seed check (step 3).
- The GPU is shared: the queue runner stops vLLM while trials run and restarts the plain Granite server when the
  queue is empty. Anything that needs the GPU (evals, SFT target generation) goes ahead of the queue: create
  `results/sft/autoresearch/STOP` to stop after the current trial.
