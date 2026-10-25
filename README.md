# Benchbook Labs

*The Benchbook: Alignment at the Edge* (Peter Banyas). Ground truth: `context/Benchbook-Research-Plan-v0.4.pdf`.
Start with `CLAUDE.md`, then `DECISIONS-2026-10-25.md` and `HANDOFF-2026-10-25.md`.

## Swap a model
`config/models.yaml` says which model does which job (policy, judges, converter...). Edit a `model:` line, or
override for one run: `BENCHBOOK_MODEL_CONVERTER=openrouter/openai/gpt-oss-120b ...`.
`PYTHONPATH=code .venv/bin/python -m bench.models` prints what is in effect.

## Layout
```
config/models.yaml          which model does which job (one file; env overrides per run)
code/
  INTERFACES.md             the contract between the packages below
  bench/                    2a  shared schemas (case, equities, reply + tolerant parser, answer key, scenario),
                                role -> model routing, the PDF worked example as reference fixtures
  library/                  2b  case store, serve/renumber, oracle retriever, index stub, v2.6 -> PDF converters
  harness/                  2c  injection, arms, reasoning modes, settings; prompts/ (analogical prompt draft)
  scorers/                  2d  one function per row of the PDF scoring table, judge client + cache, adapters
  eval/                     2e  Inspect task (Checkpoint 2), faithfulness interventions, stats, report
  training/                 2e  SFT data builder + loss masks, LoRA SFT, GRPO skeleton
  inference/                    serve.sh (vLLM), smoke.py; README has the measured numbers
  datagen/                      the v2.6 datagen pipeline (Step 3 updates it to the PDF format)
data/
  cases/<FAMILY>/           PDF-format cases, canonical local ids (F1, C1, O1, flip1); versions/ beside them
  registry/equities/        equities sets (one per deployment)
  scenarios/<FAMILY>/       live scenarios: trace ref + arms + answer keys + perturbation record
  draft/B001/               v2.6 pilot batch (eval-only, Claude-drafted)
examples-v21/               v2.6 spec + worked cases
results/                    smoke/, checkpoint2/<run>/, RESULTS-<date>.md, provenance.jsonl
context/  ideas/            design history (strong context, not law); context/ is frozen reference
```

## Environment
`.venv` (Python 3.12, Firo Labs pins + boto3 + inspect-ai; `requirements-gpu.in/.lock`). Rebuild:
`uv venv --python 3.12 .venv && VIRTUAL_ENV=.venv uv pip sync requirements-gpu.lock`. Tests: `.venv/bin/python -m pytest -q code`.
Serve Granite: `bash code/inference/serve.sh` (see `code/inference/README.md`).
