#!/usr/bin/env bash
# Re-extract the sources that landed in data/store/incomplete/ after the span-repair / initials fixes.
cd "$(dirname "$0")/../.."
. ~/.config/benchbook/env; export PYTHONPATH=code BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE=1
for s in OHA-PSH-26-0011 OHA-PSH-26-0016 OHA-PSH-26-0017 OHA-PSH-26-0035 OHA-PSH-26-0085 OHA-PSH-26-0089 OHA-PSH-26-0094 OHA-PSH-26-0100; do echo $s; done |
  xargs -P 4 -I{} sh -c '.venv/bin/python -m pipeline.ingest extract --source {} > results/datagen-2026-10-28/logs/reextract-{}.log 2>&1; echo "done {}: $(grep -c split= results/datagen-2026-10-28/logs/reextract-{}.log) ok"'
