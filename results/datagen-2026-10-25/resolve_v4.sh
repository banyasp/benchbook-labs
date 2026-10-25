#!/usr/bin/env bash
cd ~/benchbook-labs; . ~/.config/benchbook/env; export PYTHONPATH=code HF_HOME=/data/hf HF_HUB_OFFLINE=1
L=results/datagen-2026-10-25/logs/resolve-v4; mkdir -p $L
xargs -P 8 -I{} bash -c '.venv/bin/python -m pipeline.solve --pair {} > '$L'/{}.log 2>&1; grep -h "accepted" '$L'/{}.log | head -1' < results/datagen-2026-10-25/pairs-resolve-v4.txt
echo "RESOLVE DONE $(date -u +%T)"
