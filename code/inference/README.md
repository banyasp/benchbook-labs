# Inference: Granite 4.2 8B on vLLM

## Model
- `ibm-granite/granite-4.2-8b` (the PDF's repo id). There is no separate `-instruct` repo: this is the post-trained
  reasoning model (from Granite-4.1-8B-Base), dense `GraniteForCausalLM`, 40 layers, 8 KV heads, bf16, 17.6 GB,
  Apache-2.0, ungated. Native context 128K. Snapshot `a7042144125ce5ae64f89610e8289647fc000b9a` in `/data/hf`.
- Thinking model: by default the template opens `<think>`; `chat_template_kwargs: {enable_thinking: false}` closes
  it immediately (`<think></think>`). IBM recommends `temperature=1.0, top_p=0.95` in all modes (also the model's
  `generation_config.json`, which vLLM applies as the server default).

## Environment
`~/benchbook-labs/.venv`: Python 3.12, the Firo Labs pins (vllm 0.27.1, torch 2.13.0+cu130, transformers 5.16.1,
trl 1.12.0, peft 0.20.0, flashinfer-python 0.6.16.post3) plus `openai`. `requirements-gpu.in` / `.lock` at the repo
root. Rebuild: `uv venv --python 3.12 .venv && VIRTUAL_ENV=.venv uv pip sync requirements-gpu.lock`.

Why not the Firo venv: it is Python 3.11, and flashinfer 0.6.16.post3 annotates with `array.array[int]` (valid only
on 3.12+). vLLM 0.27.1's kernel warmup imports `flashinfer.comm` unconditionally, so `vllm serve` crashes for any
model in that venv (`TypeError: type 'array.array' is not subscriptable`). Same pins on 3.12 work. This affects the
Firo labs' vLLM paths too.

## Start / stop
```bash
bash code/inference/serve.sh            # tmux session bb-vllm, log in code/inference/logs/; ready in ~60 s
bash code/inference/serve.sh --status   # GET /v1/models
bash code/inference/serve.sh --stop
```
OpenAI-compatible at `http://localhost:8000/v1`, model name `granite-4.2-8b`, any api key.
Settings: `--dtype bfloat16 --max-model-len 32768 --gpu-memory-utilization 0.90`, reasoning parser
`granite_thinking_parser` (IBM's plugin from the model repo, reviewed copy here; it puts the `<think>` text in
`message.reasoning_content`/`reasoning`), tool parser `qwen3_coder`. torch.compile and CUDA graphs on (defaults).
`VLLM_USE_FLASHINFER_SAMPLER=0`: FlashInfer's top-k/top-p sampler JIT-compiles a kernel and the box has no `nvcc`.
Override with `MAX_LEN=`, `GPU_UTIL=`, `PORT=`, `EXTRA="..."`.

## Measured (2026-10-25, L40S 48 GB)
- Startup ~60 s (weights 1.4 s, torch.compile 16 s, graph capture 7 s). GPU memory in use ~41 GB at 0.90.
- KV cache 22.5 GiB = **147,584 tokens**: 4.5 concurrent 32K requests, or one 128K request
  (`MAX_LEN=131072`; fits by the numbers, not yet run).
- Single-stream decode **~39 tok/s** (38.4 thinking, 39.6 non-thinking) on a 3.8K-token prompt. Batch throughput
  not measured yet; Inspect runs should send requests concurrently.
- Smoke test (`smoke.py`): see `results/smoke/NOTES.md`.
