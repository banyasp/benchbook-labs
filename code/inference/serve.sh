#!/usr/bin/env bash
# Serve Granite 4.2 8B with vLLM's OpenAI-compatible server, in its own tmux session.
#
#   bash code/inference/serve.sh            start (session "bb-vllm", log under code/inference/logs/)
#   bash code/inference/serve.sh --stop     stop it
#   bash code/inference/serve.sh --status   is it up? (GET /v1/models)
#
# Uses the Benchbook venv (Python 3.12, Firo Labs pins; see requirements-gpu.in).
# Override with env vars: MODEL, PORT, MAX_LEN, GPU_UTIL, VENV, EXTRA (more vllm serve flags).
#
# Prefix caching is always on (--enable-prefix-caching): eval/rejection sampling send the same 15-20k-token prompt
# prefix many times (n per request, arms/cells sharing trace + equities).
#
# LoRA mode (serve the SFT adapter next to the base model; base = "granite-4.2-8b", adapter = "sft"):
#   LORA=results/sft/run1/adapter bash code/inference/serve.sh
#   env: LORA=<adapter dir> (turns it on), LORA_NAME (default sft), LORA_RANK (default 16; MUST be >= the adapter's r
#   in code/training/configs/sft_lora.v*.yaml), LORA_MAX (default 1 adapter at once).
#   Flag form: serve.sh --lora <dir>.
#
# Multi-GPU (data parallel): DP=<n> runs n Granite replicas, one per GPU, behind the same port (vLLM load-balances).
#   DP=4 bash code/inference/serve.sh                          # all 4 GPUs of a g6e.12xlarge
#   CUDA_VISIBLE_DEVICES=1,2,3 DP=3 bash code/inference/serve.sh   # leave GPU 0 free for training.sft_lora
# Default DP=1 (one GPU, the behaviour before 2026-10-28). Raise the client's concurrency ~DP x.
#
# GPU hand-over: vLLM holds ~90% of the 48 GB L40S. STOP vLLM (serve.sh --stop) BEFORE running training.sft_lora, and
# start it again (LoRA mode) after training. Never run both at once.
set -euo pipefail
CALLER_PWD="$PWD"      # LORA may be a path relative to where the caller stood
cd "$(dirname "$0")"

MODEL="${MODEL:-ibm-granite/granite-4.2-8b}"
NAME="${NAME:-granite-4.2-8b}"
PORT="${PORT:-8000}"
MAX_LEN="${MAX_LEN:-32768}"
GPU_UTIL="${GPU_UTIL:-0.90}"
DP="${DP:-1}"
VENV="${VENV:-$(cd ../.. && pwd)/.venv}"
SESSION=bb-vllm
export HF_HOME="${HF_HOME:-/data/hf}"
# FlashInfer's sampler JIT-compiles a kernel and this box has no nvcc (no /usr/local/cuda); use the PyTorch sampler.
export VLLM_USE_FLASHINFER_SAMPLER=0

case "${1:-}" in
  --lora)   LORA="${2:?--lora <adapter dir>}"; shift 2 ;;
  --stop)   tmux kill-session -t "$SESSION" 2>/dev/null && echo "stopped $SESSION" || echo "$SESSION not running"; exit 0 ;;
  --status) curl -sf "http://localhost:$PORT/v1/models" && echo || echo "not up on :$PORT"; exit 0 ;;
esac
case "${1:-}" in
  "") ;;
  *) echo "unknown argument $1" >&2; exit 2 ;;
esac

LORA="${LORA:-}"; LORA_NAME="${LORA_NAME:-sft}"; LORA_RANK="${LORA_RANK:-16}"; LORA_MAX="${LORA_MAX:-1}"
LORA_FLAGS=""
DP_FLAGS=""
[ "$DP" -gt 1 ] && DP_FLAGS="--data-parallel-size $DP"
if [ -n "$LORA" ]; then
  case "$LORA" in /*) ;; *) LORA="$CALLER_PWD/$LORA" ;; esac
  [ -f "$LORA/adapter_config.json" ] || { echo "no adapter_config.json in $LORA" >&2; exit 2; }
  LORA_FLAGS="--enable-lora --lora-modules $LORA_NAME=$(cd "$LORA" && pwd) --max-lora-rank $LORA_RANK --max-loras $LORA_MAX"
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then echo "$SESSION already running"; exit 1; fi
mkdir -p logs
log="logs/vllm-$(date +%Y%m%d-%H%M%S).log"
# granite_thinking_parser.py is IBM's plugin from the model repo (reviewed copy): it splits <think>...</think>
# into `reasoning_content` and strips the leading newline from `content`.
tmux new-session -d -s "$SESSION" "$VENV/bin/vllm serve $MODEL \
  --served-model-name $NAME --dtype bfloat16 --port $PORT \
  --max-model-len $MAX_LEN --gpu-memory-utilization $GPU_UTIL \
  --reasoning-parser granite_thinking_parser --reasoning-parser-plugin $PWD/granite_thinking_parser.py \
  --tool-call-parser qwen3_coder --enable-auto-tool-choice \
  --enable-prefix-caching $DP_FLAGS $LORA_FLAGS ${EXTRA:-} 2>&1 | tee $PWD/$log"
echo "started $SESSION  log: code/inference/$log"
