# Spend and usage (generated 2026-10-28T16:05:42Z)

Since: all logs. Prices: config/prices.yaml as of 2026-10-28. Regenerate: `PYTHONPATH=code .venv/bin/python -m bench.costs`.

| | USD | basis |
|---|---|---|
| Bedrock (Luna, gpt-oss) | 24.36 | **estimate**: tokens x list price (no Cost Explorer access) |
| OpenRouter: LLM calls in our logs | 0.00 | provider-reported where logged |
| OpenRouter: whole key (incl. Jev judge) | 0.54 | **exact**, live from OpenRouter; today 0.34; limit 250 |
| Local vLLM (Granite) | 0.00 | GPU instance hours billed separately |
| Jev judge calls | 21,260 calls | cost inside the OpenRouter key total |

## By model

| model | calls | input tok | output tok | cached | USD | basis |
|---|---|---|---|---|---|---|
| `bedrock/openai.gpt-oss-120b-1:0` | 5,270 | 37,728,803 | 12,359,030 | 0 | 13.07 | estimate |
| `bedrock/us.openai.gpt-6-luna` | 15,184 | 62,325 | 22,142,907 | 20,457,081 | 11.28 | estimate |
| `bedrock/mistral.mistral-large-3-675b-instruct` | 169 | 244,094 | 20,325 | 0 | 0.00 | unknown (169 unpriced) |
| `vllm/granite-4.2-8b` | 7,173 | 20,673,029 | 23,613,839 | 0 | 0.00 | local |
| `bedrock/openai.gpt-6-luna` | 1 | 0 | 0 | 0 | 0.00 | unknown (1 unpriced) |
| `bedrock/global.openai.gpt-6-luna` | 1 | 0 | 0 | 0 | 0.00 | unknown (1 unpriced) |
| `openrouter/openai/gpt-6-luna` | 1 | 23 | 21 | 0 | 0.00 | exact |

## By day and provider

| day, provider | USD |
|---|---|
| 2026-10-25 bedrock | 1.16 |
| 2026-10-25 vllm | 0.00 |
| 2026-10-26 vllm | 0.00 |
| 2026-10-27 vllm | 0.00 |
| 2026-10-28 bedrock | 23.20 |
| 2026-10-28 openrouter | 0.00 |
| 2026-10-28 vllm | 0.00 |

## Top stages

| stage, model | USD |
|---|---|
| extract | bedrock/us.openai.gpt-6-luna | 11.25 |
| extract | bedrock/openai.gpt-oss-120b-1:0 | 6.09 |
| render | bedrock/openai.gpt-oss-120b-1:0 | 3.11 |
| perturb | bedrock/openai.gpt-oss-120b-1:0 | 2.93 |
| solve | bedrock/openai.gpt-oss-120b-1:0 | 0.87 |
| h3 | bedrock/openai.gpt-oss-120b-1:0 | 0.08 |
| corpus | bedrock/us.openai.gpt-6-luna | 0.02 |
| equity | bedrock/us.openai.gpt-6-luna | 0.01 |
| smoke | bedrock/us.openai.gpt-6-luna | 0.00 |
| effort-test | bedrock/openai.gpt-oss-120b-1:0 | 0.00 |
| routing-test | bedrock/openai.gpt-oss-120b-1:0 | 0.00 |
| smoke | openrouter/openai/gpt-6-luna | 0.00 |
| routing-test | vllm/granite-4.2-8b | 0.00 |
| harness | vllm/granite-4.2-8b | 0.00 |
| harness-continue | vllm/granite-4.2-8b | 0.00 |

## Judge calls by day

| day | calls |
|---|---|
| 2026-10-25 | 7,974 |
| 2026-10-26 | 1,842 |
| 2026-10-28 | 11,444 |
