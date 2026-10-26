#!/usr/bin/env bash
# After all Checkpoint 2 stages: faithfulness interventions (relevant arm, every mode), then the final report.
cd ~/benchbook-labs; . ~/.config/benchbook/env; export PYTHONPATH=code HF_HOME=/data/hf
R=results/checkpoint2/ckpt2-pilot-v1
until grep -q "ALL STAGES DONE" $R/run.log; do sleep 60; done
echo "=== $(date -u +%T) faithfulness"
.venv/bin/python -m eval.faithfulness $R --max-samples 40 --modes B C Cprime A --concurrency 48 --judge jev
.venv/bin/python -m eval.report $R --out results/RESULTS-2026-10-25.md
echo "=== $(date -u +%T) AFTER DONE"
