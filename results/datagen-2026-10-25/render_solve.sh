#!/usr/bin/env bash
# 2f run: render then teacher-solve each train/dev/test pair, 8 pairs at a time.
cd ~/benchbook-labs; . ~/.config/benchbook/env; export PYTHONPATH=code HF_HOME=/data/hf HF_HUB_OFFLINE=1
L=results/datagen-2026-10-25/logs; mkdir -p $L/pairs
one() {
  id=$1; L=results/datagen-2026-10-25/logs
  { echo "== $(date -u +%T) render $id"; .venv/bin/python -m pipeline.render --pair $id && \
    { echo "== $(date -u +%T) solve $id"; .venv/bin/python -m pipeline.solve --pair $id; } ; echo "== $(date -u +%T) end $id rc=$?"; } > $L/pairs/$id.log 2>&1
  tail -1 $L/pairs/$id.log
}
export -f one
date -u +%T > $L/render_solve.start
xargs -P 8 -I{} bash -c 'one {}' < results/datagen-2026-10-25/pairs-main.txt
echo "RENDER+SOLVE DONE $(date -u +%T)"
