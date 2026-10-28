#!/usr/bin/env bash
# v2.4 batch step 1: extract every in-domain seed source (extract_fq.v2 + option rules), 8 sources in parallel.
cd "$(dirname "$0")/../.."
. ~/.config/benchbook/env; export PYTHONPATH=code BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE=1
.venv/bin/python -c "from pipeline.ingest import registry as R; print('\n'.join(s['id'] for s in R.load_registry()['sources']))" |
  xargs -P 8 -I{} sh -c '.venv/bin/python -m pipeline.ingest extract --source {} > results/datagen-2026-10-28/logs/extract-{}.log 2>&1; echo "done {} $(tail -c 300 results/datagen-2026-10-28/logs/extract-{}.log | tr "\n" " ")"'
