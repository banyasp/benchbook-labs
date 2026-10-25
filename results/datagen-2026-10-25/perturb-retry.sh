#!/usr/bin/env bash
cd ~/benchbook-labs; . ~/.config/benchbook/env; export PYTHONPATH=code
L=results/datagen-2026-10-25/logs
grep -h "^FAILED" $L/perturb-DR-*.log | sort -u | while read _ op id; do
  echo "== $(date -u +%T) retry $op $id"
  .venv/bin/python -m pipeline.perturb $op --scenario $id > $L/retry-$op-$id.log 2>&1 && grep -h "relation=" $L/retry-$op-$id.log | sed 's/  (.*//' || { echo "FAILED-AGAIN $op $id: $(grep -h 'Error' $L/retry-$op-$id.log | tail -1 | cut -c1-200)"; }
done
echo "RETRY DONE $(date -u +%T)"
