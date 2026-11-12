#!/usr/bin/env bash
# M11 extension (Peter, 2026-11-12): the scaffold ablation on four more local models of Granite's size class, to ask
# whether Granite's schema cost is common to the class. Same data as M11 (pilot 2: 28 X1s, 151 prompts), same three
# scaffolds, k=4 (as Granite), thinking first (mode A). Schema uses the v2 mode lines (as Luna's clean re-run).
# One model at a time on the L40S; Granite's server is restarted at the end.
#
#   nohup bash scripts/scaffold_compare_chain.sh [qwen35 olmo3 gemma4 ministral3] > logs/scaffold-compare-chain.log 2>&1 &
cd /home/ubuntu/benchbook-labs
export PYTHONPATH=code
MODELS_TO_RUN="${*:-qwen35 olmo3 gemma4 ministral3}"
CONC="${CONC:-8}"
say() { echo "$(date -u +%FT%TZ) $*"; }
wait_up() {   # up to 25 min for weights + compile
  for i in $(seq 1 150); do
    curl -sf -o /dev/null http://localhost:8000/v1/models && return 0
    tmux has-session -t bb-vllm 2>/dev/null || return 1
    sleep 10
  done
  return 1
}
for m in $MODELS_TO_RUN; do
  say "== $m: waiting for its download"
  case $m in
    qwen35) repo=Qwen/Qwen3.5-9B ;; olmo3) repo=allenai/Olmo-3-7B-Think ;;
    gemma4) repo=google/gemma-4-12B-it ;; ministral3) repo=mistralai/Ministral-3-14B-Reasoning-2512 ;;
  esac
  until grep -q "done $repo" logs/model-downloads-20261112.log; do sleep 30; done
  bash code/inference/serve_compare.sh --stop >/dev/null; sleep 10
  bash code/inference/serve_compare.sh $m
  if ! wait_up; then say "!! $m: server did not come up; skipping (see code/inference/logs/vllm-*.log)"; continue; fi
  say "$m: server up"
  for sc in schema guided free; do
    tag=$sc; [ $sc = schema ] && tag=schemaA
    d=results/transfer/pilot2-$m-$tag
    mkdir -p $d; [ -f $d/cells.json ] || cp results/transfer/pilot2/cells.json $d/cells.json
    mv_flag=""; [ $sc = schema ] && mv_flag="--modes-version v2"
    .venv/bin/python -m eval.allpairs run --run $d --cells $d/cells.json --model $m --mode A --scaffold $sc $mv_flag \
        -k 4 --max-tokens 20000 --concurrency $CONC >> logs/pilot2-$m-$tag.log 2>&1 &
  done
  wait
  for sc in schemaA guided free; do
    .venv/bin/python -m eval.transfer_report --run results/transfer/pilot2-$m-$sc > /dev/null 2>&1
    say "$m $sc: $(wc -l < results/transfer/pilot2-$m-$sc/samples.jsonl) samples"
  done
done
bash code/inference/serve_compare.sh --stop >/dev/null; sleep 10
bash code/inference/serve.sh && say "granite server restarted"
say "chain done"
