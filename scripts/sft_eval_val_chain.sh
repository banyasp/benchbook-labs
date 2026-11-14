#!/usr/bin/env bash
# SFT gen1 evaluation on the pairs-v1 val cells (M16 next step, 2026-11-14). Waits for the GPU (a running chain's pid),
# then: base Granite and the final adapter (served together: base + LoRA "sft"), then checkpoint-300 (end of epoch 1).
# Same prompt as SFT training: scaffold v4 (format v4, analogical prompt, modes v1) in mode B, equities pilot2
# (eval.allpairs SCAFFOLDS["v4"]: byte-identical to the training prompts). k=4. Val split only: test stays untouched
# until the checkpoint and settings are fixed. Granite's plain server is restarted at the end.
#
#   nohup bash scripts/sft_eval_val_chain.sh [wait_pid] > logs/sft-eval-val-chain.log 2>&1 &
cd /home/ubuntu/benchbook-labs
export PYTHONPATH=code
D=results/pairs-v1/eval-val
CELLS=$D/cells-val.json
K="${K:-4}"; CONC="${CONC:-12}"; MAXTOK="${MAXTOK:-8000}"
say() { echo "$(date -u +%FT%TZ) $*"; }
wait_up() {
  for i in $(seq 1 120); do
    curl -sf -o /dev/null http://localhost:8000/v1/models && return 0
    sleep 10
  done
  return 1
}
run() {   # run <dir> <model>
  mkdir -p "$1"
  .venv/bin/python -m eval.allpairs run --run "$1" --cells $CELLS --model "$2" --mode B --scaffold v4 \
      -k $K --max-tokens $MAXTOK --concurrency $CONC >> "logs/$(basename "$1").log" 2>&1
}
serve_lora() {   # serve_lora <adapter dir>
  bash code/inference/serve.sh --stop >/dev/null 2>&1; bash code/inference/serve_compare.sh --stop >/dev/null 2>&1; sleep 10
  LORA="$1" bash code/inference/serve.sh
  wait_up || { say "!! server with $1 did not come up"; exit 1; }
  say "server up: base + sft = $1"
}
if [ -n "$1" ]; then say "waiting for pid $1"; while kill -0 "$1" 2>/dev/null; do sleep 60; done; fi

serve_lora results/sft/run-gen1/adapter
# smoke: 4 items each, then the full runs (resumable: done sample ids are skipped)
for m in base sft; do
  .venv/bin/python -m eval.allpairs run --run $D/smoke-$m-v4B --cells $CELLS --model $m --mode B --scaffold v4 \
      -k 1 --max-tokens $MAXTOK --concurrency 4 --limit 4 > logs/sft-eval-smoke-$m.log 2>&1
  n=$(wc -l < $D/smoke-$m-v4B/samples.jsonl 2>/dev/null || echo 0)
  say "smoke $m: $n samples"; [ "$n" -ge 3 ] || { say "!! smoke $m failed; see logs/sft-eval-smoke-$m.log"; exit 1; }
done
run $D/base-v4B base &
run $D/sft-final-v4B sft &
wait
say "base: $(wc -l < $D/base-v4B/samples.jsonl) samples; sft-final: $(wc -l < $D/sft-final-v4B/samples.jsonl) samples"

serve_lora results/sft/run-gen1/checkpoint-300
run $D/sft-ckpt300-v4B sft
say "sft-ckpt300: $(wc -l < $D/sft-ckpt300-v4B/samples.jsonl) samples"

bash code/inference/serve.sh --stop >/dev/null; sleep 10
bash code/inference/serve.sh && say "granite server restarted (no adapter)"
say "chain done"
