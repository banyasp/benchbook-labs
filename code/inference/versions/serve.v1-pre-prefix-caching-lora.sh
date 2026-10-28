#!/usr/bin/env bash
# Serve Granite 4.2 8B with vLLM's OpenAI-compatible server, in its own tmux session.
#
#   bash code/inference/serve.sh            start (session "bb-vllm", log under code/inference/logs/)
#   bash code/inference/serve.sh --stop     stop it
#   bash code/inference/serve.sh --status   is it up? (GET /v1/models)
#
# Uses the Benchbook venv (Python 3.12, Firo Labs pins; see requirements-gpu.in).
# Override with env vars: MODEL, PORT, MAX_LEN, GPU_UTIL, VENV, EXTRA (more vllm serve flags).
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${MODEL:-ibm-granite/granite-4.2-8b}"
NAME="${NAME:-granite-4.2-8b}"
PORT="${PORT:-8000}"
MAX_LEN="${MAX_LEN:-32768}"
GPU_UTIL="${GPU_UTIL:-0.90}"
VENV="${VENV:-$(cd ../.. && pwd)/.venv}"
SESSION=bb-vllm
export HF_HOME="${HF_HOME:-/data/hf}"
# FlashInfer's sampler JIT-compiles a kernel and this box has no nvcc (no /usr/local/cuda); use the PyTorch sampler.
export VLLM_USE_FLASHINFER_SAMPLER=0

case "${1:-}" in
  --stop)   tmux kill-session -t "$SESSION" 2>/dev/null && echo "stopped $SESSION" || echo "$SESSION not running"; exit 0 ;;
  --status) curl -sf "http://localhost:$PORT/v1/models" && echo || echo "not up on :$PORT"; exit 0 ;;
esac

if tmux has-session -t "$SESSION" 2>/dev/null; then echo "$SESSION already running"; exit 1; fi
mkdir -p logs
log="logs/vllm-$(date +%Y%m%d-%H%M%S).log"
# granite_thinking_parser.py is IBM's plugin from the model repo (reviewed copy): it splits <think>...</think>
# into `reasoning_content` and strips the leading newline from `content`.
tmux new-session -d -s "$SESSION" "$VENV/bin/vllm serve $MODEL \
  --served-model-name $NAME --dtype bfloat16 --port $PORT \
  --max-model-len $MAX_LEN --gpu-memory-utilization $GPU_UTIL \
  --reasoning-parser granite_thinking_parser --reasoning-parser-plugin $PWD/granite_thinking_parser.py \
  --tool-call-parser qwen3_coder --enable-auto-tool-choice ${EXTRA:-} 2>&1 | tee $PWD/$log"
echo "started $SESSION  log: code/inference/$log"
