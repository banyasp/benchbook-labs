# 21a. Starting-model survey: U.S. / Western-origin and fully open LLMs, 3B-32B (as of 2026-09-29)

Purpose: pick the base model for a LoRA + GRPO (verifiable-reward) alignment experiment on 1x H100 80GB. Task: read an agentic decision scenario plus 1-3 YAML "case cards", emit a structured YAML mapping (factor tags, distinctions, verdict, confidence) before choosing an action. Needs: strong instruction following, structured-output reliability, some reasoning, tool/agentic ability, 16k+ context. Deployment: air-gapped U.S. national-security use, so provenance and license matter.

## 0. Method and source-quality warnings (read first)

- Tools: WebSearch and WebFetch only (no curl). For each model I opened the Hugging Face model card (`huggingface.co/<org>/<model>`) and, for dates/param counts/license tags, the public HF JSON record (`huggingface.co/api/models/<org>/<model>`, fetched with WebFetch). I also fetched `config.json` where context length mattered.
- **WebFetch answers are written by a small summarizing model, not raw page text.** Every number below is what that summarizer returned from the fetched page. I cross-checked the load-bearing ones across two fetches (card vs blog vs API) and flag disagreements. Spot-check any number you will quote in a paper against the card itself.
- HF `createdAt` is the repo-creation timestamp, which can precede the public launch by weeks (e.g. Gemma 4 E4B-it repo created 2026-03-02, public 2026-04-02). I give both where known.
- Two web sources are unreliable and were NOT used as evidence:
  - `neuralstack.network` "Meta Announces Llama 4 Open Weights Release for August 2026" (claims a 405B model runs on one H100, cites Bloomberg without a link; reads fabricated).
  - `spheron.network` "Deploy Microsoft Phi-5" (self-describes as pre-release speculation; no Phi-5 exists in Microsoft's HF org listing or on Wikipedia's Phi page as of today).
- "Verified" below means seen on the HF card/API or a first-party page. "Unverified" means I could not confirm it.

## 1. Bottom line

For a first LoRA+GRPO experiment on one H100, prefer a **dense, non-hybrid, Apache-2.0, 7-9B U.S.-origin instruct model whose chat template can switch reasoning off**. Ranked for this task:

1. **`ibm-granite/granite-4.2-8b`** (Aug 2026, dense 8.8B, Apache-2.0, 128K native, thinking / non-thinking / low-effort toggle, native tool calling, RL-trained with GRPO across IF, tool-use and *structured-output* environments, IFBench 79.3 on card). Control arm: **`ibm-granite/granite-4.1-8b`** (Apr 2026, non-reasoning, IFEval 87.06, BFCL v3 68.27). Risks: only ~5 weeks old; card requires temperature 1.0; reasoning parser needed in vLLM; 8B BFCL v4 number differs between card and blog.
2. **Gemma 4** (`google/gemma-4-E4B-it` 8.0B-with-embeddings/4.5B-effective, or `google/gemma-4-12B-it` 11.96B). Apache-2.0 (a change from Gemma 3), 128K/256K context, thinking toggle, native function calling, Tau2 avg 42.2 (E4B) / 69.0 (12B). Risks: E2B/E4B shared-KV `use_cache=False` bug (fix PR closed upstream, released version unconfirmed; see 3.B), 12B "unified" needs vLLM nightly per the vLLM recipe page.
3. **Fully-open arm: `allenai/Olmo-3-7B-Instruct`** (and `-Think`). Best provenance auditability (data + code + checkpoints), Apache-2.0, 65K context; but weak tool use (BFCL 49.8), Think cannot be turned off, and Think-SFT data includes DeepSeek-R1 traces.
4. **Ministral 3 8B** (`mistralai/Ministral-3-8B-Instruct-2512-BF16` / `-Reasoning-2512`): Apache-2.0, 256K, but French-origin, built by "cascade distillation" from an unstated teacher, multimodal wrapper, Instruct main repo is FP8 (use the BF16 repo for LoRA).
5. **Baselines/ceilings, not starting points:** Llama 3.1 8B Instruct (best tooling, old, restrictive license), gpt-oss-20b (strong but reasoning can't be turned off, MoE LoRA friction), Muse Glimmer 30B (strongest dense open model from Meta, but 55 GiB of bf16 weights does not leave room for rollouts on 80GB without quantizing).
6. **Avoid for RL on one GPU:** hybrid Mamba/GDN models (Nemotron-H family, Olmo Hybrid) because of training-vs-vLLM kernel mismatch and immature tooling; Ai2's own author says a 7B hybrid costs more to RL-train than the 7B dense model today.

Nothing newer than Llama 3.1 exists from Meta at small sizes: the `meta-llama` org has no new model since April 2025 (Llama 4 Scout/Maverick are 109B/402B), and Meta's only 2026 open-weights release is Muse Glimmer 30B.

## 2. Cross-cutting tables

### 2.1 Memory arithmetic (bf16 weights = params x 2 bytes; HF safetensors counts)

| Model | Params (HF safetensors) | bf16 weights | Fits LoRA + colocated vLLM rollouts on 80GB in bf16? |
|---|---|---|---|
| SmolLM3-3B | 3.08B | 5.7 GiB | Yes, trivially |
| Llama-3.1-8B | 8.03B | 15.0 GiB | Yes |
| Gemma-4-E4B (with per-layer embeddings) | 8.00B | 14.9 GiB | Yes |
| Granite-4.x-8B | 8.79B | 16.4 GiB | Yes |
| Ministral-3-8B (LM 8.4B + vision 0.4B) | ~8.8B | ~16.4 GiB | Yes |
| Apertus-v1.5-8B | 8.90B (incl. 0.29B fp32) | ~16.6 GiB | Yes |
| Gemma-4-12B | 11.96B | 22.3 GiB | Yes |
| Phi-4 (14B) | 14.66B | 27.3 GiB | Yes, but 16K context only |
| gpt-oss-20b | 20.9B (19.1B in MXFP4 U8 + 1.8B BF16) | 12.9 GiB packed / ~39 GiB dequantized (Unsloth-zoo PR #1358 numbers) | Yes with packed experts; ~39 GiB if dequantized |
| Granite-4.2-30B (nominal 30B; exact count not fetched) | ~30B | ~56 GiB | No (needs 4-bit/FP8 base) |
| Muse-Glimmer-30B | 29.78B | 55.5 GiB | No (needs 4-bit/FP8 base) |
| Gemma-4-31B | 31.27B | 58.3 GiB | No |
| Nemotron-3-Nano-30B-A3B | 31.58B | 58.8 GiB (Unsloth: 16-bit LoRA "around 60GB VRAM") | No |
| Nemotron-3.5-Lightning-30B-A3B | 32.91B | 61.3 GiB | No |

Rule of thumb used: TRL colocate mode keeps a trainable copy (LoRA + activations + optimizer for adapter only) plus a vLLM engine with its own weights and KV cache in the same GPU. An 8B in bf16 leaves ~40+ GiB for KV/activations; a 30B does not.

### 2.2 License / provenance / air-gap matrix

| Model | Developer (origin) | License on HF card/API | Gated? | Use restrictions / provenance notes |
|---|---|---|---|---|
| Granite 4.1 / 4.2 | IBM (U.S.) | Apache-2.0 | No | Granite 4.0 launch (2025-10-02) said Granite is ISO 42001-certified and every checkpoint ships with `model.sig` cryptographic signature. IBM's 4.2 docs page says "cryptographic signatures, ISO certification, and full transparency disclosures" generically; I did not verify per-release certification for 4.1/4.2. Training-data teachers for synthetic SFT data not disclosed. |
| Gemma 4 | Google (U.S.) | Apache-2.0 | No (`gated: false`) | Gemma 3 and earlier used the Gemma Terms of Use + Prohibited Use Policy (gated, remote-restriction clause, must propagate restrictions to derivatives). Gemma 4 dropped that for Apache-2.0. |
| gpt-oss-20b | OpenAI (U.S.) | Apache-2.0 + "gpt-oss usage policy" | No | Model card reports it underperforms o4-mini on instruction-hierarchy evals. |
| Olmo 3 / 3.1 / Hybrid | Ai2 (U.S.) | Apache-2.0, "for research and educational use in accordance with Ai2's Responsible Use Guidelines" | No | Guidelines are advisory, do not name military/weapons use; research use exempt (allenai.org/responsible-use). Dolci-Think-SFT reasoning traces were generated by DeepSeek R1 / R1-0528 (dataset card). Dolci-Instruct-SFT includes GPT-4.1-upgraded WildChat responses. Full data, code, checkpoints public. |
| Nemotron Nano 9B/12B v2 | NVIDIA (U.S.) | NVIDIA Open Model License (2025-10-24 text) | No | Contains a guardrail clause: rights terminate if you "bypass, disable, reduce the efficacy of, or circumvent" a guardrail without a substantially similar one. Post-training data tags include Nemotron-Post-Training-Dataset-v2, whose card says data came from DeepSeek-R1-0528 and Qwen2.5/Qwen3 models and that resulting models "may be subject to" Qwen and DeepSeek license agreements. |
| Nemotron 3 Nano 4B / 30B-A3B | NVIDIA | NVIDIA Nemotron Open Model License (2025-12-15 text) | No | Summarizer reported no guardrail clause in this version (unverified). Post-training-v3 data teachers not disclosed on the collection page. |
| Nemotron 3.5 Lightning 30B-A3B | NVIDIA | OpenMDW-1.1 (HF tag `license: other`, name openmdw-1.1) | No | OpenMDW is a Linux Foundation/PyTorch Foundation permissive model+data license (openmdw.ai). Full text not verified. |
| Llama 3.1 / 3.2 | Meta (U.S.) | Llama 3.1 / 3.2 Community License | Yes, manual | 700M-MAU clause, "Built with Llama" attribution, Acceptable Use Policy. Meta's original AUP barred military use; in Nov 2024 Meta announced an exception for U.S. government agencies and contractors (and Five Eyes) per The Register. I could not fetch the license or AUP text (401, gated), so exact clauses and naming rules are unverified. |
| Muse Glimmer 30B | Meta (U.S.) | Apache-2.0 | No | Distilled from Meta's closed Muse Spark teacher (Meta blog). Card notes not intended for users under 18. |
| Phi-4 family | Microsoft (U.S.) | MIT | No | Phi-4-reasoning-vision-15B (2026) is built on Phi-4-Reasoning. Microsoft's 2026 agentic model MagenticBrain is fine-tuned from Qwen/Qwen3-14B (Chinese-origin base). |
| Ministral 3 / Small 3.2 / Magistral | Mistral AI (France) | Apache-2.0 | No | Western but not U.S.-origin. Ministral 3 made by "Cascade Distillation" (iterative pruning + distillation); teacher not stated in the abstract. |
| SmolLM3 | Hugging Face (U.S./France) | Apache-2.0 | No | Data mixture, recipe and code public. |
| Apertus v1.5 | Swiss AI Initiative (Switzerland) | Apache-2.0 | `gated: auto` | Fully open (weights, data, recipes). |
| Essential rnj-1 / rnj-1.5 | Essential AI (U.S.) | Apache-2.0 | No | rnj-1 trained from scratch (8.4T tokens). Uses `gemma3_text` architecture class, so Gemma-3 tooling applies. |

### 2.3 Reasoning-mode matrix (can it be switched off? matters for cheap YAML rollouts)

| Model | Reasoning | Off switch |
|---|---|---|
| Granite 4.2 (3B/8B/30B) | `<think>...</think>`, default ON | Yes: `enable_thinking=False`; `low_effort=True` for short chains |
| Granite 4.1, 4.0 | none (non-reasoning) | n/a |
| Gemma 4 | `<\|think\|>` token in system prompt / `enable_thinking=True` | Yes (off unless requested; remove token) |
| gpt-oss-20b | low / medium / high via system prompt (harmony) | No documented "off" |
| Olmo 3 Instruct | none | n/a |
| Olmo 3 / 3.1 Think, Hybrid Think | always `<think>` | No documented toggle |
| Nemotron 3 Nano 4B, 30B, 3.5 Lightning | `enable_thinking` (default True) | Yes |
| Nemotron Nano 9B/12B v2 | `/think` `/no_think` in system prompt | Yes |
| Muse Glimmer 30B | "Reasoning strength: low/medium/high/xhigh" in system prompt | No "off" documented |
| Ministral 3 | separate Instruct vs Reasoning checkpoints | Choose the checkpoint |
| Phi-4-reasoning(-plus) | always Thought/Solution | No |
| Phi-4-reasoning-vision-15B | `<think>` / `<nothink>` | Yes |
| SmolLM3 | `/think` `/no_think` or `enable_thinking` | Yes |

## 3. Per-model notes

Conventions: "card" = HF model card; "API" = `huggingface.co/api/models/...` JSON; "(blog)" = first-party blog. IFEval = instruction following; BFCL = Berkeley Function-Calling Leaderboard; tau/Tau2/tau3 = agentic tool-use benchmarks. Absent numbers mean the card did not report them.

### 3.A Meta

#### Llama 3.1 8B Instruct - `meta-llama/Llama-3.1-8B-Instruct`
- URL: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct ; API: https://huggingface.co/api/models/meta-llama/Llama-3.1-8B-Instruct
- Release: 2024-07-23 (card); repo created 2024-07-18. Params: 8.03B (BF16). Dense transformer, GQA. Context 128K.
- License: Llama 3.1 Community License (gated, manual approval). See 2.2 caveats.
- Reasoning mode: none. Tool calling: yes (chat-template tool formats; `llama3_json`-style).
- Card benchmarks (8B Instruct): IFEval 80.4; BFCL 76.1; API-Bank 82.6; Nexus 38.5; MMLU 69.4 (5-shot), MMLU-Pro 48.3; GSM8K 84.5; MATH 51.9; HumanEval 72.6; GPQA 30.4. No tau-bench.
- Tooling: first-class in TRL, Unsloth (GRPO notebook "Llama 3.1 (8B)" listed), vLLM, and named explicitly in verl's README model list.
- Status: 2024 vintage; newest small Llama. Weakest reasoning of the set.

#### Llama 3.2 3B Instruct - `meta-llama/Llama-3.2-3B-Instruct`
- URL: https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct . Release 2024-09-25. 3.21B, 128K, Llama 3.2 Community License.
- Card: IFEval 77.4; BFCL V2 67.0; Nexus 34.3; GSM8K 77.7; MMLU 63.4. Pretrained on up to 9T tokens.

#### Meta 2026: nothing new under `meta-llama`; Muse Glimmer under `meta-models`
- `meta-llama` org listing (API, sorted newest first) tops out at Llama-Prompt-Guard-2 (2025-04-28) and Llama 4 (2025-04). Wikipedia: Meta released Muse Spark (closed) April 2026 as the replacement for Llama in Meta products. Digital Applied H1-2026 retrospective: "Meta shipped no new open-weight Llama family through May 16, 2026."
- **Muse Glimmer 30B** - `meta-models/Muse-Glimmer-30B` - https://huggingface.co/meta-models/Muse-Glimmer-30B ; blog https://huggingface.co/blog/muse-glimmer ; Meta https://research.meta.ai/blog/introducing-muse-glimmer-open-agentic-model
  - Release: announced 2026-08-10 (Meta; MarkTechPost; GCN); repo created 2026-08-09. Params 29.78B (BF16 safetensors) incl. ~1.8-2B vision encoder. Dense causal transformer, 52 layers, hidden 6656, GQA 32Q/2KV, sliding-window (2048) : full attention 3:1. Multimodal input.
  - Context: card and config.json say 131,072+; the HF blog text said 32,768 (discrepancy, likely serving default).
  - License: Apache-2.0. Reasoning: "Reasoning strength: low/medium/high/xhigh" in system prompt; no "off" documented. Tool calling: yes, multimodal tool calling.
  - Card benchmarks: IFBench 77.0; MCP Atlas 75.5; tau3-Banking 23.5; DeepSearch QA 74.6; SWE-Bench Verified 76.0; SWE-Bench Pro 51.2; AIME 2026 94.7; GPQA Diamond 83.5.
  - Training provenance (Meta blog): three-phase logit distillation from Meta's closed Muse Spark, then SFT + on-policy distillation + RL.
  - Tooling: HF blog says day-0 Transformers, llama.cpp, vLLM, Inference Endpoints, and "TRL fine-tuning examples ... for LoRA and GRPO"; Unsloth changelog (2026-08-10) says it can be trained on ~20GB VRAM (i.e. 4-bit) and lists a Muse Glimmer notebook. vLLM support not confirmed in the vLLM model-table excerpt I got.
  - Fit: 55.5 GiB in bf16, so LoRA+GRPO on 80GB requires 4-bit/8-bit base. Only 30B released; no smaller size found. Muse Spark 1.2 open weights were "pledged" (GCN, 2026-08-27); not released as far as I could find.

### 3.B Google

#### Gemma 4 family - https://huggingface.co/collections/google/gemma-4 ; blog https://huggingface.co/blog/gemma4 ; tech report https://arxiv.org/abs/2607.02770
- Announced 2026-04-02 (HF blog). Report submitted 2026-07-02. Repo `createdAt`: E4B-it 2026-03-02, 31B-it 2026-03-11 (pre-launch), **12B-it and 12B 2026-05-23** (Google Developers blog "Gemma 4 12B: The Developer Guide" dated 2026-06-03 per summarizer; I could not pin the exact public date of the 12B).
- License: Apache-2.0 on all (API `license:apache-2.0`, `gated: false`). Thinking: `<|think|>`/`enable_thinking=True`; can be off. Native function calling on all cards. Sampling advice: temp 1.0, top_p 0.95, top_k 64.
- The card tables do not include IFEval or BFCL. They report Tau2 (avg of 3), MMLU Pro, AIME 2026, LiveCodeBench v6, GPQA-D, BigBench Extra Hard, MRCR v2.

| Repo | Params | Arch | Ctx | Tau2 avg | MMLU Pro | AIME 2026 | GPQA-D | LCB v6 |
|---|---|---|---|---|---|---|---|---|
| `google/gemma-4-E4B-it` | 8.0B w/ embeddings (4.5B effective), 42 layers, sliding 512 | dense + per-layer embeddings, hybrid local/global attention, vision+audio encoders | 128K | 42.2 | 69.4 | 42.5 | 58.6 | 52.0 |
| `google/gemma-4-12B-it` | 11.96B, 48 layers, sliding 1024 | dense, "unified" encoder-free multimodal (`gemma4_unified`) | 256K | 69.0 | 77.2 | 77.5 | 78.8 | 72.0 |
| `google/gemma-4-26B-A4B-it` | 25.2B total / 3.8B active; 8 of 128 experts + 1 shared | MoE | 256K | 68.2 (blog) | 82.6 | 88.3 | n/r | 77.1 |
| `google/gemma-4-31B-it` | 30.7B / 31.27B safetensors, 60 layers | dense | 256K | 76.9 (blog) | 85.2 | 89.2 | 84.3 | 80.0 |

  (E4B MRCR v2 8-needle-128k 25.4; 12B 43.4. n/r = not retrieved.)
- Tooling: TRL first-class (HF blog; multimodal tool-response GRPO example on E2B); Unsloth trains E2B/E4B/12B/26B-A4B/31B (VRAM per Unsloth: E4B LoRA ~17GB, E4B QLoRA ~10GB, 31B QLoRA ~22GB; 26B-A4B LoRA >40GB, QLoRA "not recommended"); Unsloth changelog: Gemma 4 training fixed 2026-04-08; GRPO reliability improved 2026-06-18; a Gemma 4 E2B Sudoku GRPO notebook exists. vLLM recipe: `--reasoning-parser gemma4 --tool-call-parser gemma4`, needs a tool chat template file; **12B-it needed vLLM nightly** ("landed in vllm-project/vllm#44429 and has not yet shipped in a stable release" at time of the recipe page; may have shipped since, unverified). vLLM model table (summarized) shows `Gemma4ForCausalLM` LoRA supported.
- Known incompatibilities: HF transformers issue #45242 - `use_cache=False` (forced by `gradient_checkpointing=True`, used by QLoRA/TRL/PEFT) corrupts logits on **E2B** (E4B unclear), because of KV-shared layers; a fix PR (#45328) is closed/merged, version not confirmed; Unsloth shipped its own fix. MoE 26B-A4B: LoRA memory >40GB and Unsloth advises caution. Unsloth: keep >=75% reasoning examples when fine-tuning thinking variants so reasoning is preserved.
- Fit for this task: the strongest small model with an Apache license and a real off switch. E4B is 8B of weights but ~4.5B of compute (cheap rollouts); 12B is nicest quality/size but the newest and least battle-tested.

#### Gemma 3 (superseded) - https://huggingface.co/google/gemma-3-12b-it ; https://huggingface.co/google/gemma-3-27b-it
- 12B (12.19B) / 27B / 4B; repo created 2025-03-01 (public launch mid-March 2025, not verified this session); 128K context (8K output per card); **Gemma license** (gated: manual; Terms include Prohibited Use Policy incorporated by reference, remote-restriction right, and a requirement to propagate use restrictions to derivatives: https://ai.google.dev/gemma/terms). No thinking mode. Function calling and IFEval are not on the card. Only MMLU 74.5/78.6, GSM8K, HumanEval etc. Use Gemma 4 instead.

### 3.C OpenAI

#### gpt-oss-20b - `openai/gpt-oss-20b` - https://huggingface.co/openai/gpt-oss-20b ; model card https://arxiv.org/abs/2508.10925
- Repo created 2025-08-04 (public launch 2025-08-05 from my recollection, not verified this session). No newer OpenAI open-weights LLM exists: the `openai` HF org's newest entries are `privacy-filter` (2026-04-17), `circuit-sparsity` (2025-12), and `gpt-oss-safeguard-20b/120b` (2025-09-18).
- Params: 21B total / 3.6B active. MoE: 24 layers, 32 experts, 4 active per token, hidden 2880, sliding window 128 alternating with full attention; MXFP4-quantized experts (U8 19.1B params + 1.8B BF16). Context 131,072 (config `max_position_embeddings`, YaRN from 4096).
- License: Apache-2.0 + gpt-oss usage policy. Reasoning: low/medium/high via system prompt, full CoT exposed; no documented "off". **Harmony response format is mandatory** ("will not work correctly otherwise"). Tool use: function calling, web browse, Python, structured outputs.
- Benchmarks: model card (arXiv 2508.10925), 20b low/medium/high: AIME 2025 37.1/72.1/91.7; GPQA-D 56.8/66.0/71.5; MMLU 80.4/84.0/85.3; SWE-Bench Verified 37.4/53.2/60.7; **Tau-Bench Retail 35.0/47.3/54.8**; Codeforces 1366/1998/2230. HF card prints GPQA-D 58.59 and MMLU-Pro 73.6 (harness not stated; differs from the arXiv table). No IFEval or BFCL reported. Instruction-hierarchy evals: underperforms o4-mini.
- Tooling: Unsloth GRPO for gpt-oss-20b "on 15GB VRAM" (notebooks incl. 2048 game, kernel creation, OpenEnv); Unsloth changelog 2026-04-23 added low/medium/high toggles. **Unsloth docs say "vLLM does not support RL for gpt-oss since it lacks BF16 training and LoRA support for gpt-oss"**, so Unsloth uses its own inference path, while vLLM's docs table lists `GptOssForCausalLM` with LoRA supported and vLLM issue #23610 shows multi-LoRA for mxfp4 gpt-oss landing via PR #21229 with kernel/cudagraph caveats (`VLLM_MXFP4_USE_MARLIN=1`, `--no-enable-prefix-caching`). These two statements are in tension and version-dependent; test before committing. PEFT/TRL: expert LoRA needs `target_parameters` (e.g. `"7.mlp.experts.gate_up_proj"`) because experts are `nn.Parameter`s, not `nn.Linear`; OpenAI's cookbook fine-tunes on an H100 80GB with `dequantize=True` (bf16, ~39 GiB) at 2048 seq len. MXFP4 has no native backward pass in Triton.
- Fit: capability ceiling comparator; always-on reasoning makes rollouts long and the YAML arrive after CoT.

### 3.D Ai2 (Allen Institute for AI)

#### Olmo 3 7B - `allenai/Olmo-3-7B-Instruct`, `allenai/Olmo-3-7B-Think` (+ `-SFT`, `-DPO`, RL-Zero variants)
- URLs: https://huggingface.co/allenai/Olmo-3-7B-Instruct ; https://huggingface.co/allenai/Olmo-3-7B-Think ; blog https://allenai.org/blog/olmo3
- Release: repos created 2025-11-14 to 2025-11-19; paper arXiv 2512.13961 (2025-12-15). Params ~7B dense; 32 layers, hidden 4096, sliding-window (4096) : full attention 3:1, YaRN. **Context 65,536** (config).
- License: Apache-2.0 ("research and educational use in accordance with Ai2's Responsible Use Guidelines"). Fully open: data (Dolma 3 / Dolci), code, checkpoints, logs.
- Instruct card: IFEval 85.6; IFBench 32.3; **BFCL 49.8**; MATH 87.3; HumanEvalPlus 77.2; MMLU 69.1; BBH 71.2; AlpacaEval 2 LC 40.9. Default system prompt "You are a helpful function-calling AI assistant"; blog says Instruct covers tool use. Recipe: SFT -> DPO -> RLVR on Dolci datasets.
- Think card: IFEval 88.2; IFBench 41.6; MATH 95.1; AIME 2024 71.6; AIME 2025 64.6; HumanEval+ 89.9; MMLU 77.8. Always emits `<think>`; tool calling not documented for Think.
- Tooling: OLMo-core / open-instruct (Ai2's RLVR + GRPO stack, vLLM rollouts) is the reference; Transformers/vLLM support `Olmo3ForCausalLM` (not seen in my truncated vLLM table excerpt: unverified); Unsloth: no Olmo 3 notebook in its notebook index (no dedicated fine-tune notebook found). TRL generic.

#### Olmo 3 32B / Olmo 3.1 32B - `allenai/Olmo-3-32B-Think`, `allenai/Olmo-3.1-32B-Think`, `allenai/Olmo-3.1-32B-Instruct`
- URLs: https://huggingface.co/allenai/Olmo-3.1-32B-Think ; https://huggingface.co/allenai/Olmo-3.1-32B-Instruct
- Olmo 3: Nov 2025. Olmo 3.1 32B Think/Instruct: repos created 2025-12-10, announced ~2025-12-12 (Ai2 tweet). 32B dense, 64 layers, hidden 5120, 65,536 context, Apache-2.0.
- 3.1-32B-Think: IFEval 93.8; MATH 96.2; AIME 2024 80.6; HumanEvalPlus 91.5; MMLU 86.4. 3.1-32B-Instruct: IFEval 88.8; IFBench 39.7; MATH 93.4; AIME 2024 67.8; MMLU 80.9; GPQA 48.6. Tool-calling support not documented on these cards. bf16 ~60 GiB: too big for 80GB LoRA+rollouts without quantization.

#### Olmo Hybrid 7B - `allenai/Olmo-Hybrid-7B`, `-Instruct-SFT-7B`, `-Instruct-DPO-7B`, `-Think-SFT-7B`
- URLs: https://huggingface.co/allenai/Olmo-Hybrid-Instruct-DPO-7B ; blog https://allenai.org/blog/olmohybrid ; https://www.interconnects.ai/p/olmo-hybrid-and-future-llm-architectures
- Blog date 2026-03-05; repos created 2026-01-28 (base), 2026-02-19/20 (Instruct SFT/DPO), 2026-02-28 (Think-SFT). No RL-finished Instruct/Think checkpoints found (Interconnects: "3 experiment post-trained checkpoints").
- Architecture: 3 Gated DeltaNet linear-attention layers : 1 full-attention layer, 32 layers, hidden 3840; config `max_position_embeddings` 32,768 (blog: extended to 64K with YaRN/DRoPE; RULER 64K 85.0 vs 70.9 for Olmo 3). `transformers>=5.3.0`; `flash-linear-attention` recommended.
- Instruct-DPO card: IFEval 80.5; IFBench 33.3; BFCL 49.6; MATH 72.9; MMLU 73.6. Think-SFT: MATH 93.8; AIME 2024 66.2; MMLU 80.5.
- **Tooling warning (Nathan Lambert):** "the open-source software tooling support is horrific"; vLLM hybrid kernels less developed, needs `mamba_ssm_cache_dtype="float32"`, disabling cascade attention and CUDA graphs for stability (throughput drops); "the 7B hybrid model today takes more compute to train with RL than our 7B dense model"; estimates another 3-6 months for GDN tooling. vLLM's model table (summarized) shows `OlmoHybridForCausalLM` LoRA supported.
- Verdict: skip for GRPO now.

### 3.E IBM Granite

#### Granite 4.2 - `ibm-granite/granite-4.2-3b`, `-8b`, `-30b` (dense, reasoning)
- URLs: https://huggingface.co/ibm-granite/granite-4.2-8b ; https://huggingface.co/ibm-granite/granite-4.2-3b ; https://huggingface.co/ibm-granite/granite-4.2-30b ; blog https://huggingface.co/blog/ibm-granite/granite-4-2 ; IBM https://research.ibm.com/blog/introducing-granite-4-2
- Release: **2026-08-25** (card, IBM blog, MarkTechPost); repos created 2026-08-07. 8B: 8.79B params (API), decoder-only dense, 40 layers, hidden 4096, GQA 32Q/8KV, RoPE theta 1e7, untied embeddings. Built on Granite-4.1-8B-Base. **Context 128K native, extendable to 512K.** Languages: 12. License Apache-2.0.
- Reasoning: `<think>` chain-of-thought; `enable_thinking=True` (default), `enable_thinking=False`, or `low_effort=True`; prior-turn thinking stripped by default (`truncate_history_thinking=True`). **Card demands temperature 1.0, top_p 0.95**, max tokens 8,192 (thinking) / 2,048 (non-thinking).
- Tools: OpenAI function schema, `<tool_call>` blocks, "reasoning-augmented tool calling"; vLLM `--tool-call-parser qwen3_coder`; reasoning parser `granite_thinking_parser` (fallback `nemotron_v3`); vLLM >=0.20, SGLang >=0.5.18; harnesses OpenCode, Pi, OpenHands. Uses `<|im_end|>` ChatML-style delimiters.
- Training (blog): SFT ~7.2M samples / 100B tokens (31.6% agentic); **asynchronous GRPO** with leave-one-out baselines; RLVR on math, code, STEM, instruction-following, tool-calling; agentic RL (SWE, terminal, search) for 8B/30B; RLHF; card says RL environments include "structured output".
- Card benchmarks:

| | 3B | 8B | 30B |
|---|---|---|---|
| IFBench (prompt) | 74.33 | **79.33** | 77.17 |
| tau3-bench (avg) | 45.78 | 58.06 | 62.00 |
| BFCL v4 | 52.41 | 52.39 (blog table: 50.29) | 61.39 |
| MMLU-Pro | 67.84 | 74.04 | 77.60 |
| AIME25 | 78.33 | 86.67 | 89.17 |
| GPQA | 54.80 | 64.14 | 66.41 |
| Arena-Hard-V2 | 34.96 | 65.19 | 67.93 |
| RULER 64K / 128K | 67.52 / 55.30 | 80.99 / 71.41 | 89.96 / 81.38 |
| SWE-bench Verified | n/a | 47.67 | 57.00 |

- Tooling: same `granite` architecture as 4.1 (`GraniteForCausalLM`); vLLM table (summarized) lists it with LoRA; Unsloth supports Granite 4.1 3B/8B/30B fine-tuning (docs page; min 16,384 ctx recommended; **"Do NOT use CUDA 13.2"** gibberish warning) and has a Granite-4.0-H notebook, but I found no Granite 4.2-specific Unsloth or TRL page and no RL recipe. TRL generic.
- Caveat for GRPO: the default-on thinking and required temp 1.0 change reward design (strip `<think>`; cap thinking or disable). Non-thinking mode with the YAML mapping as the only "reasoning" is the cleanest setup.

#### Granite 4.1 - `ibm-granite/granite-4.1-3b`, `-8b`, `-30b`
- URLs: https://huggingface.co/ibm-granite/granite-4.1-8b ; blog https://huggingface.co/blog/ibm-granite/granite-4-1 ; https://research.ibm.com/blog/granite-4-1-ai-foundation-models
- Release **2026-04-29** (card, IBM); repos created 2026-04-06. **Dense** decoder-only (a move away from Granite 4.0's Mamba-2 hybrid MoE). 8B: 8.79B params; 40 layers; card context 131,072 (IBM blog: staged extension to 512K). Apache-2.0. No thinking mode; tool calling (OpenAI schema). Post-trained with multi-stage on-policy GRPO (DAPO loss), RLHF.
- Card (instruct): 3B / 8B / 30B: IFEval avg 82.30 / **87.06** / 89.65; BFCL v3 60.80 / **68.27** / 73.68; MMLU-Pro 55.99 (8B); GSM8K 92.49 (8B); ArenaHard 68.98 (8B); AlpacaEval 2.0 50.08 (8B). IBM: 8B "consistently matches or outperforms the Granite 4.0 32B MoE". Unsloth doc: recommended sampling temp 0.0 for deterministic IF.
- Best pick for a clean non-thinking control.

#### Granite 4.0 (hybrid; superseded) - https://huggingface.co/ibm-granite/granite-4.0-h-small
- Released 2025-10-02. H-Small: 32B total / 9B active, 4 attention + 36 Mamba-2 layers with MoE (72 experts, 10 active), 128K, Apache-2.0; IFEval 87.55, BFCL v3 64.69. H-Tiny / H-Micro cards not fetched. Hybrid + MoE = avoid for RL for the same reasons as Nemotron-H.

### 3.F NVIDIA Nemotron

All Nemotron hybrids (`nemotron_h`) use Mamba-2 layers; HF integration is `custom_code`/Transformers >=5.3.0.

#### Nemotron 3.5 Lightning 30B-A3B - `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` - https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16
- Release 2026-08-11 (card, DataCamp, MarkTechPost); repo created 2026-08-01. 30B total/3B active (HF safetensors 32.9B); Mamba-2 + MoE + attention hybrid with multi-token-prediction layers. Context up to 1M (256K used for single-H100 deployment). License OpenMDW-1.1. Reasoning on/off via `enable_thinking`. Tool calling with qwen3-coder parser.
- Card: MMLU-Pro 81.94; GPQA-D 75.44; SWE-bench Verified 51.56; IFBench (loose) 71.88; Terminal-Bench 2.1 24.58. LoRA/SFT via NeMo Automodel and Megatron Bridge; RL via NeMo RL / NeMo Gym; Unsloth listed for local tools (DataCamp).

#### Nemotron 3 Nano 30B-A3B - `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` - https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
- Release 2025-12-15 (card); repo 2025-12-04. 31.6B safetensors, 3.5B active; 23 Mamba-2/MoE layers + 6 attention; 128 routed experts + 1 shared, 6 active. Context up to 1M (256K default). NVIDIA Nemotron Open Model License. `enable_thinking` toggle, `qwen3_coder` tool parser.
- Card: IFBench (prompt) 71.5; BFCL v4 53.8; AIME25 89.1 (99.2 with tools); GPQA 73.0; MMLU-Pro 78.3; Arena-Hard-V2 67.7; RULER-100@256k 92.9, @1M 86.3; SWE-Bench (OpenHands) 38.8.
- Tooling gaps: Unsloth: 16-bit LoRA "around 60GB VRAM", router not trained by default; "single-turn rollout RL" via NeMo Gym collaboration; keep >=75% reasoning data; Unsloth issue #3854 (LoRA-merge failure on MoE expert/SCB keys, fixed by upgrading Unsloth). QLoRA example (acecloud) targets only attention + MLP projections (Mamba in_proj/out_proj LoRA not shown; unverified) and needs `mamba-ssm` + `causal-conv1d` kernels. **RL-Align RFC #434**: the same Mamba-2 op runs through three different code paths (training fused kernel, prefill, decode), so train-vs-vLLM numerics can diverge; MoE `index_add_` combine is order-nondeterministic. TRL's default truncated importance sampling for vLLM mismatch helps but does not remove this.

#### Nemotron 3 Nano 4B - `nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16` - https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16
- Release 2026-03-16 (card). 3.97B; Mamba2-Transformer hybrid (4 attention layers), compressed from Nano-9B-v2 with Nemotron Elastic. Context up to 262K. Nemotron Open Model License. `enable_thinking=False` turns reasoning off.
- Card (reasoning off): IFEval-Prompt 82.8; IFBench-Prompt 43.2; BFCL v3 61.1; Tau2 Airline/Retail/Telecom 28.0/34.8/24.9; RULER 128k 91.1. Reasoning on: IFEval-Prompt 87.9; Tau2 33.3/39.8/33.0; AIME25 78.5.

#### Nemotron Nano 9B v2 / 12B v2 - https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2 ; https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2
- 9B: card release 2025-08-18; 8.89B; hybrid (Mamba-2 + MLP + 4 attention); 128K; `/think` `/no_think`; **NVIDIA Open Model License (2025-10-24 text, guardrail-termination clause)**. Card (reasoning on): IFEval (instruction strict) 90.3; BFCL v3 66.9; AIME25 72.1; GPQA 64.0; RULER 128K 78.9.
- 12B: card 2025-08-29; 6 attention layers; 128K; AIME25 76.25; BFCL v3 66.98; IFEval prompt/instruction 84.70/89.81.
- Also `nvidia/Llama-3.1-Nemotron-Nano-8B-v1` (2025-03-18): dense Llama-3.1-based, "detailed thinking on/off", IFEval strict-prompt 74.7 (off) / 71.9 (on), BFCL v2 Live 63.9 / 63.6; carries NVIDIA Open Model License + Llama 3.1 license.
- Out of range or not needed: Nemotron 3 Super 120B-A12B, Ultra 550B-A55B, Nemotron 3 Nano Omni 30B-A3B (multimodal, Apr 2026), Nemotron Labs Puzzle 75B-A9B.

### 3.G Microsoft Phi

- **Phi-4** `microsoft/phi-4` - https://huggingface.co/microsoft/phi-4 : released 2024-12-12; 14.66B dense; **16K context**; MIT; card: MMLU 84.8, GPQA 56.1, MATH 80.4, HumanEval 82.6; no tool calling, no reasoning mode; English-centric.
- **Phi-4-reasoning / -plus** - https://huggingface.co/microsoft/Phi-4-reasoning-plus : 2025-04-30; 14B; 32K (tested to 64K); MIT; always emits Thought/Solution with `<think>`; -plus: IFEval strict 84.9, MMLU-Pro 76.0, AIME 2024 81.3, GPQA-D 68.9, ArenaHard 79.0; base: IFEval 83.4, MMLU-Pro 74.3, AIME 2024 75.3. Tool calling not mentioned.
- **Phi-4-mini-instruct** - https://huggingface.co/microsoft/Phi-4-mini-instruct : Feb 2025; 3.8B dense GQA; 128K; MIT; tool calling via `<|tool|>` JSON (card warns it "could sometimes hallucinate function names or URLs"); GSM8K 88.6, MMLU 67.3, MATH 64.0, BBH 70.4; no IFEval/BFCL on card.
- **Phi-4-reasoning-vision-15B** - https://huggingface.co/microsoft/Phi-4-reasoning-vision-15B : card date 2026-03-04 (repo 2026-01-23); 15B; SigLIP-2 encoder + Phi-4-Reasoning backbone; 16,384 context; MIT; `<think>`/`<nothink>` modes; vision benchmarks only; no tool calling. Only 2026 Phi release found.
- Microsoft's other 2026 text models: `microsoft/MagenticBrain` (2026-05-14, 14B, MIT, agentic planner/tool caller, 32K) is **fine-tuned from Qwen/Qwen3-14B**; treat as Chinese-base provenance. No Phi-5 found in the org listing.
- Tooling: Unsloth has Phi-4 (14B) GRPO and conversational notebooks. Phi family is stale (mostly 2025) and has the shortest context of any candidate at 14B.

### 3.H Mistral AI (France; Western, not U.S.)

- **Ministral 3** - https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512 ; `-Reasoning-2512` : https://huggingface.co/mistralai/Ministral-3-8B-Reasoning-2512 ; `-Instruct-2512-BF16` : https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512-BF16 ; announcement https://mistral.ai/news/mistral-3 ; paper https://arxiv.org/abs/2601.08584
  - Launched 2025-12-02 with Mistral Large 3; paper submitted 2026-01-13; repos created 2025-10-31. Sizes 3B / 8B / 14B, each Base / Instruct / Reasoning. 8B: LM 8.4B + vision encoder 0.4B. Dense, `mistral3` architecture. Context 256K. Apache-2.0. Native function calling and JSON output.
  - The main Instruct repo is FP8 (API: F8_E4M3 7.4B + BF16 1.5B); a separate `-BF16` repo exists for training. Requires vLLM >=0.12 and mistral_common >=1.8.6; Transformers main/v5.
  - Card (Instruct): Arena Hard 0.509; WildBench 66.8; MATH Maj@1 0.876; MM MTBench 8.08. No IFEval/BFCL/tau. Reasoning 8B: AIME25 0.787; AIME24 0.860; GPQA-D 0.668; LiveCodeBench 0.616; sampling temp 0.7.
  - Method: Cascade Distillation (iterative pruning + continued training with distillation); teacher not stated in the abstract.
  - Tooling: Unsloth fully supports fine-tuning and GRPO for all Ministral 3 sizes (needs Transformers v5 + latest Unsloth; a Ministral-3 Sudoku GRPO notebook exists); vLLM tool parser `mistral`.
- **Mistral Small 3.2 24B Instruct** - https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506 : repo 2025-06-19; 24.0B dense; context 131,072 (params.json); Apache-2.0; better function calling and 2x fewer repetitions than 3.1; WildBench v2 65.33; Arena Hard v2 43.1; internal IF accuracy 84.78; needs ~55 GB in bf16 (too large for rollouts on 80GB without quantization).
- **Magistral Small 2509** - https://huggingface.co/mistralai/Magistral-Small-2509 : 24B reasoning (`[THINK]` tokens), 128K (degrades past ~40K), Apache-2.0, AIME24 86.14, GPQA-D 70.07; tool parser `mistral`; off-switch not documented.
- **Out of range:** Mistral Small 4 119B-2603 (Jan/Mar 2026), Mistral Medium 3.5 128B, Leanstral 119B-A6B, Devstral 2 123B. `Shieldstral-1.0-3B` (2026-07-16) is a safety model (not evaluated).

### 3.I Hugging Face SmolLM3

- `HuggingFaceTB/SmolLM3-3B` - https://huggingface.co/HuggingFaceTB/SmolLM3-3B : repo 2025-07-08; 3.08B dense, GQA + NoPE; 11.2T tokens; Apache-2.0; native context 64K, YaRN to 128K; `/think` `/no_think` or `enable_thinking`; tool calling via `xml_tools` and `python_tools`.
- Card (no-think / think): IFEval 76.7 / 71.2; BFCL 92.3 / 88.8 (the BFCL scores look high versus Llama 3.1 8B's 76.1 on Meta's harness; comparability not established); AIME 2025 9.3 / 36.7; GPQA-D 35.7 / 41.7; LiveCodeBench v4 15.2 / 30.0; GSM-Plus 72.8 / 83.4. Post-trained with TRL (APO). No SmolLM4 or newer LLM in the HF org listing (latest text-model repo `nanowhale-100m`, 2026-04-24).
- Use as a fast pipeline-debugging model only; too weak for the final experiment.

### 3.J Other Western / fully-open candidates worth knowing (not in the required list)

- **Essential AI `EssentialAI/rnj-1.5-instruct`** - https://huggingface.co/EssentialAI/rnj-1.5-instruct : created 2026-04-22; 8.31B (stored in F32), `gemma3_text` architecture class, Apache-2.0, 160K context (up from 32K in rnj-1), block-local + interleaved global attention; card reports RULER 128K 77% and SWE-bench Verified 40% (SWE-Agent); no IFEval/BFCL/tau numbers; coding/STEM-focused. `EssentialAI/rnj-1-instruct` (2025-12-04): 8.3B trained from scratch on 8.4T tokens; HumanEval+ 83.5, GSM8k 92.6, AIME25 43.3, BFCL "top performer among comparable models" (no number retrieved), Hermes tool parser, self-identity confusion noted. Because it loads as Gemma-3 text, LoRA/GRPO tooling should work, but I did not verify RL recipes.
- **Apertus v1.5 8B** `swiss-ai/Apertus-v1.5-8B` (2026-07-24): 8.9B, Apache-2.0, 262,144 context, thinking via `<|inner_prefix|>`/`<|inner_suffix|>`, tool calling via vLLM `apertus` parser; fully open (weights, data, recipes); needs a custom Transformers branch and modified vLLM per the card; benchmark numbers "forthcoming"; `gated: auto`. Swiss, not U.S.
- **Arcee Trinity Mini** `arcee-ai/Trinity-Mini` (26.1B MoE, 3B active, 128K, `afmoe` custom code, 2025-12-01; license shown as OpenMDW-1.1 on card, HF tag "other") and Trinity Nano Preview (6B/1B active); Trinity Large Thinking (2026-04, out of range). U.S. lab. MoE + custom code = not a first choice.
- **Poolside Laguna XS 2.1** `poolside/Laguna-XS-2.1` (2026-06-20; 33B total/3B active MoE, 262K, OpenMDW-1.1, thinking toggle, coding-agent focus, SWE-bench Verified 70.9) and Laguna S 2.1 (118B/8B active, out of range).
- Not surveyed in depth: Liquid AI LFM2, ServiceNow Apriel, Marin 8B, Deep Cogito.
- Ai2's 2026 fine-tunes named `tmax-*` and `qwen35-9b-*` are built on Qwen bases (not OLMo).

## 4. Framework compatibility summary (what I could and could not confirm)

| Model | TRL (SFT/GRPO + PEFT LoRA) | Unsloth | vLLM rollouts w/ LoRA | verl | Known gaps |
|---|---|---|---|---|---|
| Granite 4.2 8B | generic HF causal LM (no model-specific doc found) | 4.1 supported; 4.2 page not found | `GraniteForCausalLM` LoRA listed | generic HF path; not named | thinking parser, temp 1.0, vLLM >=0.20 |
| Granite 4.1 8B | generic | supported, docs page | yes | generic | CUDA 13.2 gibberish warning |
| Gemma 4 E4B/12B | first-class (HF blog) | supported, RL works | `Gemma4ForCausalLM` LoRA listed; 12B needs nightly (as of recipe page) | not named (README lists Gemma2) | E2B/E4B `use_cache=False` bug (#45242) |
| gpt-oss-20b | works with `target_parameters` for experts | GRPO on 15GB | conflicting (see 3.C) | not named | MXFP4 no backward; harmony; always-on reasoning |
| Olmo 3 7B | generic | no notebook | `Olmo3` row not seen in truncated table (unverified) | not named | none known; 65K ctx |
| Olmo Hybrid 7B | needs Transformers >=5.3 + FLA | not documented | listed but fragile | not named | hybrid numerics; RL costlier than dense |
| Nemotron 3 Nano 30B / 9B / 4B | generic w/ mamba-ssm | supported (60GB 16-bit LoRA) | `NemotronHForCausalLM` listed | not named | Mamba path mismatch, MoE LoRA/merge issues |
| Ministral 3 8B | generic (Transformers v5) | supported incl. GRPO | mistral tokenizer/parser flags | not named | FP8 main repo; use BF16 repo |
| Llama 3.1 8B | first-class | GRPO notebook | first-class | named | none |
| SmolLM3 3B | first-class (HF) | no notebook in index | not confirmed | not named | none |

TRL facts (docs): `GRPOTrainer` supports `use_vllm` in colocate (default) or server mode; turns on truncated importance sampling by default to correct vLLM-vs-trainer mismatch (`vllm_importance_sampling_correction`); reward functions get `completions` plus any dataset columns; supports `tools=` and `environment_factory` for multi-turn tool use; LoRA learning-rate guidance 1e-5 for GRPO; `beta=0.0` default. TRL's PEFT doc does not describe MoE `target_parameters` or vLLM adapter sync. verl (docs): LoRA RL works on FSDP/FSDP2 with vLLM or SGLang (SGLang needs merged adapters), `lora_rank` >=32 advised, raise LR ~10x, README names Qwen, Llama3.1, Gemma2, DeepSeek explicitly and says other HF models work through Transformers integration (unverified per model).

## 5. Suggested experiment design (short, opinionated)

1. Primary: Granite 4.2 8B in non-thinking mode (`enable_thinking=False`, temperature 1.0 as required by the card), YAML mapping as the only reasoning, GRPO via TRL colocate vLLM, LoRA r>=32 on all linear layers, LR ~1e-5. Log format-validity reward separately from correctness rewards.
2. Non-reasoning control: Granite 4.1 8B (same tokenizer family, no thinking machinery) to separate "reasoning mode" effects from RL effects.
3. Cross-lab check: Gemma 4 E4B-it (cheap) and Olmo 3 7B Instruct (fully open, auditable). Only add Gemma 4 12B once vLLM stable support is confirmed.
4. Keep Llama 3.1 8B as the community-standard baseline for reviewers, but do not deploy on it for an air-gapped natsec story without legal review of the license/AUP.
5. Avoid hybrids and 30B+ in the first pass; revisit Nemotron 3.5 Lightning / Muse Glimmer with QLoRA later if capacity is the bottleneck.

## 6. What I could not verify

- Llama 3.1 license and AUP full text (HF returned 401; llama.com redirected to a stub page). The 700M MAU clause is from the card; the naming/"Built with Llama" details and the exact AUP military language are not verified this session. The Nov 2024 U.S.-government exception comes from a news report (The Register).
- Exact public dates: Gemma 4 12B (repos 2026-05-23; Google blog 2026-06-03 per summarizer); gpt-oss (2025-08-05 recollection); Olmo 3 announcement day (repos Nov 14-19, 2025); Gemma 3 launch day.
- Granite 4.2 8B BFCL v4: card 52.39 vs IBM blog table 50.29. Granite 4.2 30B exact parameter count. ISO 42001 / signing for 4.1 and 4.2 specifically (verified only for 4.0's launch text; 4.2 docs page is generic). Granite synthetic-data teacher models not disclosed.
- gpt-oss-20b: HF card GPQA-D 58.59 / MMLU-Pro 73.6 conflict with the arXiv model-card table (66.0 GPQA-D at medium); IFEval/BFCL not reported by OpenAI. vLLM gpt-oss LoRA/RL status conflicts between Unsloth docs and vLLM docs.
- Olmo 3 chat-template tool support beyond the default system prompt and the blog claim; `Olmo3ForCausalLM` row in vLLM's LoRA table; no Unsloth Olmo 3 notebook does not prove it fails.
- Nemotron 3 (Dec 2025) license text: summarizer says no guardrail clause; not double-checked. OpenMDW-1.1 full text not read. Nemotron post-training-v3 teacher models not disclosed.
- Nemotron / Mamba LoRA: which modules (in_proj/out_proj) can be LoRA-targeted in practice was not verified; Gemma 4 E4B exposure to the `use_cache` bug is unclear; which transformers version contains PR #45328 was not confirmed.
- vLLM support status for Muse Glimmer, Olmo 3, SmolLM3, Phi-4 (the vLLM models table excerpt was truncated); verl support for any of these models beyond its README list.
- Gemma 3 IFEval/BFCL (not on card); Gemma 4 IFEval/BFCL (not reported); Ministral 3 / Rnj-1.5 / Apertus IFEval/BFCL/tau (not reported on cards); SmolLM3 BFCL comparability.
- Muse Glimmer context (131,072+ in card/config vs 32,768 in HF blog); whether Muse Spark 1.2 weights have been released since 2026-08-27.
- Phi-5: no evidence it exists; only a speculative third-party post.
- I ran no models, so nothing here measures actual YAML validity, GRPO throughput or reward-hacking behavior.

## 7. Source URLs

Meta: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct ; https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct ; https://huggingface.co/meta-models/Muse-Glimmer-30B ; https://huggingface.co/blog/muse-glimmer ; https://research.meta.ai/blog/introducing-muse-glimmer-open-agentic-model ; https://gcn.com/meta-opens-muse-glimmer-billion-parameter/21144/ ; https://www.theregister.com/2024/11/06/meta_weaponizing_llama_us ; https://www.digitalapplied.com/blog/open-weight-models-h1-2026-retrospective-deepseek-qwen-llama ; https://en.wikipedia.org/wiki/Llama_(language_model)
Google: https://huggingface.co/blog/gemma4 ; https://huggingface.co/google/gemma-4-E4B-it ; https://huggingface.co/google/gemma-4-12B-it ; https://huggingface.co/google/gemma-4-26B-A4B ; https://huggingface.co/google/gemma-4-31B-it ; https://arxiv.org/abs/2607.02770 ; https://developers.googleblog.com/gemma-4-12b-the-developer-guide/ ; https://recipes.vllm.ai/Google/gemma-4-12B-it ; https://docs.vllm.ai/projects/recipes/en/stable/Google/Gemma4.html ; https://unsloth.ai/docs/models/gemma-4/train ; https://github.com/huggingface/transformers/issues/45242 ; https://huggingface.co/google/gemma-3-12b-it ; https://huggingface.co/google/gemma-3-27b-it ; https://ai.google.dev/gemma/terms
OpenAI: https://huggingface.co/openai/gpt-oss-20b ; https://huggingface.co/openai/gpt-oss-20b/raw/main/config.json ; https://arxiv.org/abs/2508.10925 ; https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune/gpt-oss-reinforcement-learning ; https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune ; https://github.com/vllm-project/vllm/issues/23610 ; https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers ; https://github.com/unslothai/unsloth-zoo/pull/1358
Ai2: https://huggingface.co/allenai/Olmo-3-7B-Instruct ; https://huggingface.co/allenai/Olmo-3-7B-Think ; https://huggingface.co/allenai/Olmo-3.1-32B-Think ; https://huggingface.co/allenai/Olmo-3.1-32B-Instruct ; https://huggingface.co/allenai/Olmo-Hybrid-Instruct-DPO-7B ; https://huggingface.co/allenai/Olmo-Hybrid-Think-SFT-7B ; https://allenai.org/blog/olmo3 ; https://allenai.org/blog/olmohybrid ; https://www.interconnects.ai/p/olmo-hybrid-and-future-llm-architectures ; https://allenai.org/responsible-use ; https://huggingface.co/datasets/allenai/Dolci-Think-SFT-7B ; https://huggingface.co/datasets/allenai/Dolci-Instruct-SFT
IBM: https://huggingface.co/ibm-granite/granite-4.2-8b ; https://huggingface.co/ibm-granite/granite-4.2-3b ; https://huggingface.co/ibm-granite/granite-4.2-30b ; https://huggingface.co/blog/ibm-granite/granite-4-2 ; https://research.ibm.com/blog/introducing-granite-4-2 ; https://www.ibm.com/granite/docs/models/granite4-2 ; https://huggingface.co/ibm-granite/granite-4.1-8b ; https://huggingface.co/ibm-granite/granite-4.1-3b ; https://huggingface.co/ibm-granite/granite-4.1-30b ; https://huggingface.co/blog/ibm-granite/granite-4-1 ; https://research.ibm.com/blog/granite-4-1-ai-foundation-models ; https://huggingface.co/ibm-granite/granite-4.0-h-small ; https://www.ibm.com/new/announcements/ibm-granite-4-0-hyper-efficient-high-performance-hybrid-models ; https://unsloth.ai/docs/models/ibm-granite-4.1
NVIDIA: https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 ; https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 ; https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16 ; https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2 ; https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2 ; https://huggingface.co/nvidia/Llama-3.1-Nemotron-Nano-8B-v1 ; https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/ ; https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/ ; https://openmdw.ai/ ; https://www.datacamp.com/blog/nemotron-3-5-lightning ; https://unsloth.ai/docs/models/nemotron-3 ; https://github.com/unslothai/unsloth/issues/3854 ; https://acecloud.ai/blog/nemotron-3-nano-multi-gpu-fine-tuning/ ; https://github.com/RL-Align/RL-Kernel/issues/434 ; https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v2 ; https://huggingface.co/collections/nvidia/nemotron-post-training-v3
Microsoft: https://huggingface.co/microsoft/phi-4 ; https://huggingface.co/microsoft/Phi-4-reasoning ; https://huggingface.co/microsoft/Phi-4-reasoning-plus ; https://huggingface.co/microsoft/Phi-4-mini-instruct ; https://huggingface.co/microsoft/Phi-4-reasoning-vision-15B ; https://huggingface.co/microsoft/MagenticBrain ; https://en.wikipedia.org/wiki/Phi_(language_model)
Mistral: https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512 ; https://huggingface.co/mistralai/Ministral-3-8B-Reasoning-2512 ; https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512-BF16 ; https://mistral.ai/news/mistral-3 ; https://arxiv.org/abs/2601.08584 ; https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506 ; https://huggingface.co/mistralai/Magistral-Small-2509 ; https://unsloth.ai/docs/models/tutorials/ministral-3
Hugging Face: https://huggingface.co/HuggingFaceTB/SmolLM3-3B
Others: https://huggingface.co/EssentialAI/rnj-1.5-instruct ; https://huggingface.co/EssentialAI/rnj-1-instruct ; https://huggingface.co/swiss-ai/Apertus-v1.5-8B ; https://huggingface.co/arcee-ai/Trinity-Mini ; https://huggingface.co/arcee-ai/Trinity-Nano-Preview ; https://huggingface.co/poolside/Laguna-XS-2.1 ; https://huggingface.co/poolside/Laguna-S-2.1
Frameworks: https://huggingface.co/docs/trl/main/en/grpo_trainer ; https://huggingface.co/docs/trl/main/en/peft_integration ; https://verl.readthedocs.io/en/latest/advance/ppo_lora.html ; https://github.com/verl-project/verl ; https://docs.vllm.ai/en/latest/models/supported_models.html ; https://unsloth.ai/docs/get-started/unsloth-notebooks ; https://unsloth.ai/docs/new/changelog
