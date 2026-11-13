#!/usr/bin/env bash
# Serve one local COMPARISON policy on :8000 (2026-11-12, Peter: run the M11 scaffold ablation on Qwen3.5-9B, Gemma 4
# 12B-it, Olmo 3 7B Think and Ministral 3 14B Reasoning). Same tmux session as serve.sh ("bb-vllm"), so only one model
# holds the L40S at a time: `bash serve.sh --stop` (or this script's --stop) first.
#
#   bash code/inference/serve_compare.sh qwen35|gemma4|olmo3|ministral3
#   bash code/inference/serve_compare.sh --stop
#
# Each model gets its own vLLM reasoning parser, so the chat endpoint returns the thinking separately
# (eval.allpairs saves it as <think>..</think> in the raw reply). No tool parser: the eval sends no tools.
# Sampling: set per request from each model card's recommendation (config/models.yaml policy_<key> roles).
set -euo pipefail
cd "$(dirname "$0")"
SESSION=bb-vllm
VENV="${VENV:-$(cd ../.. && pwd)/.venv}"
export HF_HOME="${HF_HOME:-/data/hf}"
case "${1:-}" in
  --stop) tmux kill-session -t "$SESSION" 2>/dev/null && echo "stopped $SESSION" || echo "$SESSION not running"; exit 0 ;;
  qwen35)     MODEL=Qwen/Qwen3.5-9B;                         NAME=qwen3.5-9b;                PARSER=qwen3;   EXTRA_M="" ;;
  gemma4)     MODEL=google/gemma-4-12B-it;                   NAME=gemma-4-12b-it;            PARSER=gemma4;  EXTRA_M="--limit-mm-per-prompt '{\"image\":0,\"audio\":0}'" ;;
  olmo3)      MODEL=allenai/Olmo-3-7B-Think;                 NAME=olmo-3-7b-think;           PARSER=olmo3;   EXTRA_M="" ;;
  ministral3) MODEL=mistralai/Ministral-3-14B-Reasoning-2512; NAME=ministral-3-14b-reasoning; PARSER=mistral; EXTRA_M="--tokenizer-mode mistral --config-format mistral --load-format mistral --limit-mm-per-prompt '{\"image\":0}'" ;;
  *) echo "usage: $0 qwen35|gemma4|olmo3|ministral3|--stop" >&2; exit 2 ;;
esac
MAX_LEN="${MAX_LEN:-49152}"     # ~20k-token prompts + 20k max_tokens (Olmo 3 tops out at 65k)
GPU_UTIL="${GPU_UTIL:-0.90}"
if tmux has-session -t "$SESSION" 2>/dev/null; then echo "$SESSION already running (stop it first)"; exit 1; fi
mkdir -p logs
log="logs/vllm-$NAME-$(date +%Y%m%d-%H%M%S).log"
ENVS="HF_HOME=$HF_HOME VLLM_USE_FLASHINFER_SAMPLER=0"
tmux new-session -d -s "$SESSION" "env $ENVS $VENV/bin/vllm serve $MODEL \
  --served-model-name $NAME --dtype bfloat16 --port 8000 \
  --max-model-len $MAX_LEN --gpu-memory-utilization $GPU_UTIL \
  --reasoning-parser $PARSER --enable-prefix-caching $EXTRA_M ${EXTRA:-} 2>&1 | tee $PWD/$log"
echo "started $SESSION: $NAME ($MODEL)  log: code/inference/$log"
