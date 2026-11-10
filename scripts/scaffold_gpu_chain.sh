#!/usr/bin/env bash
# GPU queue for the scaffold ablation (2026-11-10, M11). Sample-major schedules make any idx prefix a balanced subset.
# 1. let pilot2-modeA (Granite, schema, think first) reach k=4 (idx 0-3 of all 151 items = 604 samples), then stop it;
# 2. run Granite guided and free (think first, k=4) side by side;
# 3. resume pilot2-modeA to its configured k=8 (completed samples are skipped).
cd /home/ubuntu/benchbook-labs
export PYTHONPATH=code
log=logs/scaffold-gpu-chain.log
n_idx_le3() { python3 -c "import json; print(sum(1 for l in open('results/transfer/pilot2-modeA/samples.jsonl') if json.loads(l)['idx']<=3))"; }
echo "chain start $(date -u +%FT%TZ)" >> $log
while [ "$(n_idx_le3)" -lt 604 ]; do sleep 120; done
pid=$(pgrep -f "allpairs run --run results/transfer/pilot2-mode[A]")
echo "modeA reached k=4 ($(n_idx_le3) samples idx<=3); stopping pid $pid $(date -u +%FT%TZ)" >> $log
[ -n "$pid" ] && kill $pid; sleep 30
for sc in guided free; do
  mkdir -p results/transfer/pilot2-granite-$sc; cp results/transfer/pilot2/cells.json results/transfer/pilot2-granite-$sc/cells.json
  .venv/bin/python -m eval.allpairs run --run results/transfer/pilot2-granite-$sc --cells results/transfer/pilot2-granite-$sc/cells.json \
      --model base --mode A --scaffold $sc -k 4 --max-tokens 20000 --concurrency 12 >> logs/pilot2-granite-$sc.log 2>&1 &
done
wait
echo "granite guided+free done $(date -u +%FT%TZ)" >> $log
for sc in guided free; do .venv/bin/python -m eval.transfer_report --run results/transfer/pilot2-granite-$sc > /dev/null 2>&1; done
.venv/bin/python -m eval.allpairs run --run results/transfer/pilot2-modeA --cells results/transfer/pilot2-modeA/cells.json --mode A -k 8 \
    --max-tokens 20000 --concurrency 24 >> logs/pilot2-modeA.log 2>&1 && .venv/bin/python -m eval.transfer_report --run results/transfer/pilot2-modeA > /dev/null 2>&1
echo "modeA resumed run done $(date -u +%FT%TZ)" >> $log
