#!/usr/bin/env bash
# v2.4 batch step 2: perturb train + test source scenarios, 8 scenarios in parallel.
cd "$(dirname "$0")/../.."
. ~/.config/benchbook/env; export PYTHONPATH=code BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE=1
.venv/bin/python results/datagen-2026-10-28/perturb_jobs.py "${1:-train,test}" | xargs -P 8 -I{} bash results/datagen-2026-10-28/perturb_one.sh {}
