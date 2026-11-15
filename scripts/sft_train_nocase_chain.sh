#!/usr/bin/env bash
# M20 (2026-11-15, Peter): memorization check. No-case replies on the 438 gen1 training X1s, base Granite and the
# final gen1 adapter served together, same prompt as M17 (scaffold v4, mode B, pilot2), k=2. Plain server restarted after.
#   nohup bash scripts/sft_train_nocase_chain.sh > logs/sft-train-nocase-chain.log 2>&1 &
cd /home/ubuntu/benchbook-labs
export PYTHONPATH=code
D=results/pairs-v1/eval-train-nocase
CELLS=$D/cells-train-x1.json
say() { echo "$(date -u +%FT%TZ) $*"; }
bash code/inference/serve.sh --stop >/dev/null 2>&1; bash code/inference/serve_compare.sh --stop >/dev/null 2>&1; sleep 10
LORA=results/sft/run-gen1/adapter bash code/inference/serve.sh
for i in $(seq 1 120); do curl -sf -o /dev/null http://localhost:8000/v1/models && break; sleep 10; done
say "server up: base + sft"
for m in base sft; do
  name=$([ $m = base ] && echo base-v4B || echo sft-final-v4B)
  mkdir -p $D/$name
  .venv/bin/python -m eval.allpairs run --run $D/$name --cells $CELLS --control-only --model $m --mode B --scaffold v4 \
      -k 2 --max-tokens 8000 --concurrency 12 >> logs/train-nocase-$name.log 2>&1 &
done
wait
say "base: $(wc -l < $D/base-v4B/samples.jsonl); sft-final: $(wc -l < $D/sft-final-v4B/samples.jsonl)"
bash code/inference/serve.sh --stop >/dev/null; sleep 10
bash code/inference/serve.sh && say "granite server restarted (no adapter)"
say "chain done"
