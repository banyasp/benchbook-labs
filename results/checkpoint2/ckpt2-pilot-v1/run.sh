#!/usr/bin/env bash
# Checkpoint 2 pilot, staged cheapest mode first (2026-10-25). Resumable: rerun this script.
set -u
cd ~/benchbook-labs
. ~/.config/benchbook/env
export PYTHONPATH=code HF_HOME=/data/hf
R="--run-id ckpt2-pilot-v1 --samples 5 --concurrency 64 --judge jev --prompts both"
for modes in "B" "C Cprime" "A"; do
  echo "=== $(date -u +%H:%M:%S) stage modes=$modes"
  .venv/bin/python -m eval.run_checkpoint2 $R --modes $modes
  .venv/bin/python -m eval.report results/checkpoint2/ckpt2-pilot-v1 --out results/RESULTS-2026-10-25.md || true
done
echo "=== $(date -u +%H:%M:%S) ALL STAGES DONE"
