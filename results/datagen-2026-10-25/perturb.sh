#!/usr/bin/env bash
# 2f run: perturb every non-eval source scenario with restyle, flip, add_fact (one process per scenario, in parallel).
cd ~/benchbook-labs
. ~/.config/benchbook/env
export PYTHONPATH=code
L=results/datagen-2026-10-25/logs
for id in DR-OGE-2635-204a-6@v1 DR-OGE-2635-204b-1@v1 DR-OGE-2635-206a1-2@v1 DR-OHA-26-0087-1@v1 DR-OHA-26-0087-2@v1 DR-OHA-26-0100-1@v1 DR-OHA-26-0100-2@v1 DR-OHA-26-0122@v1; do
  ( for op in restyle flip add-fact; do
      echo "== $(date -u +%T) $op $id"
      .venv/bin/python -m pipeline.perturb $op --scenario $id || echo "FAILED $op $id"
    done ) > $L/perturb-$id.log 2>&1 &
done
wait
echo "PERTURB DONE $(date -u +%T)"
