#!/usr/bin/env bash
# v2.4 step 6: Granite rejection sampling (mode C, N=4+4, rationalize) on a list of train pairs; --redo re-samples.
cd "$(dirname "$0")/../.."
. ~/.config/benchbook/env; export PYTHONPATH=code HF_HOME=/data/hf
.venv/bin/python -m pipeline.solve --pairs-file "$1" --concurrency ${CONC:-24} ${REDO:+--redo}
