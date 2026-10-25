# 21b. Starting models from other origins (Qwen / DeepSeek / Kimi / GLM / others) and RLVR-specific pitfalls

Compiled 2026-09-29. Purpose: pick a starting checkpoint for an alignment RL experiment in which a LoRA adapter is
appended to an already post-trained open-weight instruct model and trained with GRPO (verifiable rewards) on one
80GB GPU. The model reads an agentic scenario plus 1-3 injected YAML "case cards" and emits a structured YAML
"mapping" before choosing an action. Needs: instruction following, structured output, reasoning, agentic/tool use,
16k+ context, coding a plus.

"Other origins" is read here as non-U.S./non-Western-lab (Qwen, DeepSeek, Moonshot, Zhipu) plus any other 2026 small
model that shows up on small-model agentic / instruction-following comparisons. I did not find a 21a file in this
directory (latest is 20-open-recipes-and-costs.md), so the "adjacent, likely covered elsewhere" section (Section 1.5)
is deliberately short.

## 0. Method and verification legend

Tools used: WebSearch and WebFetch only (no curl). Every model card, paper abstract and GitHub issue cited below was
opened with WebFetch during this session unless tagged otherwise.

Important caveat about the tool: WebFetch answers questions about a page through a small summarizing model, not a raw
dump. That produced at least four demonstrable errors during this session, so every number below is tagged by how it
was obtained:

- [CARD-RAW] read from the model card's raw README (`.../raw/main/README.md`) with a "quote verbatim" prompt. Most reliable.
- [CARD] read from the rendered HF card via the summarizer. Usually right; spot-checked where it mattered.
- [API] Hugging Face JSON API (`huggingface.co/api/models/...`): repo `createdAt`, license tag, safetensors parameter
  count. Reliable for identity, size and repo-creation date (which can precede the public announcement).
- [CONFIG] read from `config.json` or `chat_template.jinja`.
- [PAPER] read from an arXiv abstract page (reliable) or the PDF/HTML body (summarizer, less reliable).
- [ISSUE] a GitHub issue/PR as summarized; status is "as of fetch", not guaranteed current.
- [AGG] third-party aggregator/blog. Treated as unreliable. Several contradicted HF's own API (see Section 4).
- [MINE] my own arithmetic or inference. Not sourced.

Errors caught in the tool's output (kept here so nobody re-imports them):
1. The first summary of the Qwen3.5-4B card called it "sparse Mixture-of-Experts". Wrong: the config shows a dense-FFN
   hybrid (Gated DeltaNet + gated attention, 3:1). Fixed via [CONFIG].
2. The GLM-4.7-Flash card summary gave "release date Aug 8 2025 (arXiv 2508.06471)". Wrong (that is the GLM-4.5
   report). The HF API says the repo was created 2026-01-19.
3. The DeepSeek-R1-0528-Qwen3-8B summary attributed "BFCL v3 MultiTurn 37.0" to the 8B distill. The raw README shows
   that number belongs to the full DeepSeek-R1-0528 column. The 8B distill's card reports no BFCL or IFEval number.
4. The verl releases page summary printed 2024 dates; the GitHub API shows v0.9.0 = 2026-08-14 and v0.8.0 = 2026-06-01.

## 1. Part 1: survey of candidates

### 1.1 Bottom line for a single 80GB GPU (judgment, [MINE])

- "Small" here is really decided by memory, not by the marketing label. GRPO with a colocated vLLM engine on one
  80GB card is practical for roughly <=9B dense models. The 27B-35B class does not leave room for rollouts plus
  optimizer/activations (Unsloth's own bf16-LoRA figures: Qwen3.5-27B 56GB, Qwen3.5-35B-A3B 74GB, GLM-4.7-Flash
  ~57-76GB, Qwen3-30B-A3B 63GB at 4K context; all before any vLLM KV cache). QLoRA is explicitly discouraged for
  Qwen3.5 and for MoE models by Unsloth.
- Strongest published small-model numbers from other origins are the Qwen3.5 small dense pair (9B, 4B). They also
  carry the most tooling friction (Section 1.4).
- The safest mature-tooling starting points are the older plain-transformer Qwen3 models (Qwen3-4B-Instruct-2507,
  Qwen3-8B), which have first-class TRL / Unsloth / verl / vLLM-LoRA paths and a non-thinking mode (or non-thinking
  only).
- Nothing from DeepSeek, Moonshot or Zhipu in 2026 is small enough for this setup. Their 2026 releases are all
  >=180B total parameters, with one 31B exception (GLM-4.7-Flash) that is a memory-heavy MoE.

### 1.2 Tier A: candidates that plausibly fit 1x80GB for GRPO + LoRA

All numbers are as printed on the model cards. **Cards are vendor self-reports with different harnesses; they are
not comparable across rows** (for example, the same Qwen3-30B-A3B-Thinking-2507 scores tau2 = 41.9 in Qwen's Qwen3.5
table and 49.0 in Zhipu's GLM-4.7-Flash table).

| Model (HF repo id) | Repo created [API] / listed release | Params | Context | License | Thinking | Tool calling | Card numbers |
|---|---|---|---|---|---|---|---|
| **Qwen/Qwen3.5-9B** | 2026-02-27 [API]; Qwen3.8 README lists 2026-03-02 | 9.65B safetensors incl. vision encoder; dense FFN, 32 layers, 3 Gated-DeltaNet : 1 gated-attention [CONFIG] | 262,144 native [CONFIG] | Apache-2.0 | Card: thinking ON by default; off via `chat_template_kwargs={"enable_thinking": False}`; no `/think` soft switch. Unsloth says small Qwen3.5 (0.8-9B) default OFF in their GGUF path (conflict, Section 4) | vLLM `--tool-call-parser qwen3_coder --reasoning-parser qwen3` | [CARD-RAW] IFEval 91.5, IFBench 64.5, MultiChallenge 54.5, BFCL-V4 66.1, TAU2 79.1, LiveCodeBench v6 65.6, AA-LCR 63.0, LongBench v2 55.2. **No non-thinking scores on the card.** |
| **Qwen/Qwen3.5-4B** | 2026-02-27 [API]; listed 2026-03-02 | 4.66B safetensors incl. vision encoder; dense hybrid | 262,144 | Apache-2.0 | same as 9B | same | [CARD-RAW] IFEval 89.8, IFBench 59.2, MultiChallenge 49.0, BFCL-V4 50.3, TAU2 79.9, LCB v6 55.8 |
| **Qwen/Qwen3-4B-Instruct-2507** | 2025-08-05 [API] | 4.02B dense (3.6B non-embedding) | 262,144 native | Apache-2.0 | **Non-thinking only** (no `<think>` blocks) | Qwen-Agent / MCP; standard hermes-style parsers work in vLLM | [CARD] IFEval 83.4, Arena-Hard v2 43.4, MultiIF 69.0, BFCL-v3 61.9, TAU1-Retail 48.7, TAU1-Airline 32.0, TAU2-Retail 40.4, TAU2-Airline 24.0, TAU2-Telecom 13.2, LCB v6 35.1 |
| **Qwen/Qwen3-8B** | 2025-04-27 [API] | 8.19B dense (6.95B non-embedding); 36 layers, 8 KV heads, head_dim 128 [CONFIG] | 32,768 native; 131,072 with YaRN (card) | Apache-2.0 | Hybrid: `enable_thinking` True (default) / False, plus `/think` `/no_think` soft switches | Qwen-Agent / MCP | Card gives only "IFStruct v1 79.75". Tech report (PDF, summarizer, unconfirmed): non-thinking IFEval-strict 83.0, BFCL v3 60.2; thinking AIME'24 76.0 |
| **deepseek-ai/DeepSeek-R1-0528-Qwen3-8B** | 2025-05-29 [API] | 8.19B dense (Qwen3 architecture, Qwen3-8B-Base distilled from R1-0528 CoT) | 131,072 (YaRN x4 on 32,768) [CONFIG] | MIT | Always thinks; no documented off switch; system prompts supported; card says no need to force `<think>` | Card claims "enhanced function calling" for the R1-0528 family; no 8B-specific BFCL/IFEval number | [CARD] AIME24 86.0, AIME25 76.3, HMMT Feb25 61.5, GPQA-D 61.1, LCB 60.5 |
| **Qwen/Qwen3-30B-A3B-Instruct-2507** | 2025-07-28 [API] | 30.5B total / 3.3B active MoE | 262,144 native | Apache-2.0 | Non-thinking only | Qwen-Agent / MCP | [CARD] IFEval 84.7, Arena-Hard v2 69.0, BFCL-v3 65.1, TAU1-Retail 59.1, TAU1-Airline 40.0, TAU2-Retail 57.0, TAU2-Airline 38.0, TAU2-Telecom 12.3, LCB v6 43.2. **Memory: 61GB of bf16 weights alone; Unsloth reports 63GB LoRA at 4K context. Not viable for GRPO on 80GB.** |
| **Qwen/Qwen3.5-35B-A3B** | listed 2026-02-24 | 35B total / 3B active MoE (256 experts, 8 routed + 1 shared) | 262,144 | Apache-2.0 | thinking default ON, toggle as above | `qwen3_coder` | [CARD-RAW] IFEval 91.9, IFBench 70.2, MultiChallenge 60.0, BFCL-V4 67.3, TAU2 81.2, SWE-bench Verified 69.2, LCB v6 74.6. **Unsloth bf16 LoRA 74GB: not viable for GRPO on 80GB.** |
| **Qwen/Qwen3.6-35B-A3B** | 2026-04-15 [API]; listed 2026-04-16 | 35.95B safetensors / 3B active | 262,144 | Apache-2.0 | default ON; `enable_thinking=False`; `preserve_thinking` for agent turns | `qwen3_coder` | [CARD] SWE-bench Verified 73.4, MMLU-Pro 85.2, GPQA 86.0; general-agent block uses TAU3-Bench / MCP-Atlas, not tau2/BFCL; **no IFEval/IFBench row found**. Same memory problem. |
| **zai-org/GLM-4.7-Flash** | 2026-01-19 [API] | 31.2B total ("30B-A3B" on card); 47 layers, 64 routed experts, 4 active + 1 shared, MLA [CONFIG] | 202,752 [CONFIG] | MIT | Hybrid; template has `enable_thinking` and `clear_thinking` [CONFIG]; "Preserved Thinking" for multi-turn agents | vLLM/SGLang `--tool-call-parser glm47 --reasoning-parser glm45`; XML-style `<tool_call>` | [CARD-RAW] AIME25 91.6, GPQA 75.2, LCB v6 64.0, SWE-bench Verified 59.2, tau2-Bench 79.5, BrowseComp 42.8. **No IFEval/BFCL on the card.** Unsloth: 16-bit LoRA ~60GB (57-76GB by sequence length), needs transformers v5. |

### 1.3 Tier B/C: too large for this setup, listed so they are not re-investigated

| Model | Facts | Why out |
|---|---|---|
| Qwen/Qwen3.5-27B | created 2026-02-24 [API]; 27.78B dense; Apache-2.0; 262,144; [CARD-RAW] IFEval 95.0, IFBench 76.5, BFCL-V4 68.5, TAU2 79.0, SWE-bench V 72.4 | Unsloth bf16 LoRA 56GB before rollouts; QLoRA discouraged |
| Qwen/Qwen3.6-27B | listed 2026-04-22; 27B dense; Apache-2.0; SWE-bench V 77.2, SWE-bench Pro 53.5 [CARD]; card has no IF/BFCL rows | same |
| Qwen/Qwen3.8-27B | created 2026-08-05 [API]; listed 2026-08-14; 27.78B; Apache-2.0; 262,144; `reasoning_effort` xhigh/medium/low; IFBench 79.5, Terminal-Bench 2.1 73.0, SWE-bench Pro 61.7 [CARD]; Artificial Analysis lists it at the top of its small-open-weight page (Intelligence Index 34 at xhigh; page partial, no IFBench/tau2 shown) | same; Unsloth page says "LoRA needs >36GB" which conflicts with its 56GB figure for Qwen3.5-27B (unresolved) |
| moonshotai/Kimi-Linear-48B-A3B-Instruct | created 2025-10-30 [API]; 49.1B total / 3B active; MIT; 1M context; KDA linear attention + MLA hybrid; card shows only MMLU-Pro 51.0 @4k and RULER; no thinking mode or tool-parser documented [CARD] | ~98GB in bf16; only 2025 Moonshot model under 50B besides Kimi-VL-A3B (April/June 2025) and Moonlight-16B-A3B (Feb 2025) |
| Kimi K2.5 / K2.6 / K2.7-Code / K3 | 2026-01-01, 04-14, 06-11, 06-13 [API listing]; ~1T to 2.8T total [AGG for sizes] | trillion-scale. No small Kimi released in 2026 (HF org listing of newest 25 repos back to Feb 2025) |
| zai-org/GLM-5.3-Flash | created 2026-08-25 [API]; 321B safetensors; MIT; `reasoning_effort` low/high/max on card [CARD] | "Flash" is not small in the GLM-5 generation |
| zai-org/GLM-4.6V-Flash | created 2025-12-07 [API listing]; 9B VLM; MIT; 128K; card says text-only QA "still has significant room for improvement" [CARD] | vision-first, weak text backbone by its own admission |
| zai-org/GLM-4-9B-0414 | created 2025-04-07 [API]; 9.4B; MIT; supports JSON tool calls | 2025 model, superseded by the 4.7-Flash/Qwen3.5 tier |
| deepseek-ai/DeepSeek-V4-Flash / V4.1-Flash | V4-Flash created 2026-04-22; V4.1-Flash 2026-09-10, 763B safetensors [API]; MIT | hundreds of billions of parameters |
| Qwen/Qwen3.8-Flash-Next | created 2026-08-24 [API]; ~180B; license tag "qwen-community-1.0" [API] | large; aggregator claimed 125B/MIT (wrong per API) |

DeepSeek small models: the newest DeepSeek repos on the HF org listing are V4-family plus speculative-decoding
draft models for Qwen3-4B/8B/14B and Gemma 4 12B (`eagle3_*`, `dflash_*`, `dspark_*`, 2026-06-28), which are not
usable as base models. The only DeepSeek "distill" that is a usable small checkpoint in the listing window is
R1-0528-Qwen3-8B (May 2025). The January-2025 R1-Distill-Qwen/Llama models predate the listing window and were not
re-verified this session.

### 1.4 Tooling support: TRL, Unsloth, verl, vLLM (LoRA + GRPO)

**Qwen3 / Qwen2.5 (plain transformer, dense or MoE): mature.**
- TRL GRPOTrainer: supported; Qwen3 has a patched tool-training chat template [CARD-level, TRL docs summary].
- Unsloth: dedicated GRPO notebook for Qwen3 (4B), also Qwen3 8B FP8, DeepSeek-R1-0528-Qwen3 (8B), Llama 3.1 8B,
  Llama 3.2 3B, Phi-4, Mistral v0.3, Gemma 3/4, gpt-oss-20B (Unsloth RL guide).
- verl: README lists Qwen3 and Qwen2.5; LoRA + GRPO reference handbook (Jan 2026 post) used Qwen2.5-3B-Instruct on
  4xA100-80GB; verl's own LoRA docs contain no single-GPU example.
- vLLM: native LoRA serving for standard Qwen3 architectures.

**Qwen3.5 / 3.6 / 3.8 (Gated DeltaNet hybrid, `qwen3_5` architecture, vision encoder shipped even in "text" checkpoints): works, but with version pinning and open bugs.**
- Requirements: transformers v5 (Unsloth). Without `flash-linear-attention` and `causal-conv1d` the 24 DeltaNet layers of
  Qwen3.5-9B fall back to an fp32 torch loop: 1.22 s/step vs 0.70 s/step with fla (transformers issue #48718) [ISSUE].
- TRL: text-only Qwen3.5 checkpoints could not sync weights into vLLM (TRL #5269, vLLM #36275: "no module or parameter
  named 'model'"; "completely blocks vLLM with GRPOTrainer", workaround = disable vLLM at 10-24x slowdown). Closed:
  vLLM PR #50210 (merged 2026-07-29 per the issue) ships in vLLM >=0.27.0. TRL docs list vLLM 0.19.1 to 0.28.0 as
  supported [ISSUE + TRL docs]. Net: use vLLM >=0.27.0 and a current TRL.
- Unsloth: LoRA supported for 0.8B to 397B; docs list a Qwen3.5-4B GRPO notebook (vision variant) and instruct users to
  set `fast_inference=False` for RL (i.e. no vLLM speed-up). PR #10891 ("Allow fast_inference for Qwen3.5") was still
  in development when fetched [ISSUE]. bf16 LoRA: 9B ~22GB, 27B ~56GB. QLoRA 4-bit "not recommended" for any Qwen3.5.
- verl: v0.8.0 (2026-06-01) notes "add qwen3.5 fsdp grpo training support", GRPO demos for Qwen3.5-122B-A10B/30B; v0.9.0
  (2026-08-14) notes "Qwen3.5 LoRA & MTP support (with Megatron-Bridge)" [API release notes]. Field reports: 9B GRPO ran on
  8xB200 (151 s/step, tuned to 110 s) [issue #7847]; illegal-memory-access with transformers 5.3.0 fixed by 5.4.0
  [issue #6549]; flash-attn wheel gap with vLLM 0.18/torch 2.10 [issue #6662]. Conflicting signal: a Sept 2026 paper
  states "verl does not support Qwen3.5" and moved to NeMo-RL [PAPER arXiv 2609.28765]. That statement is likely stale
  relative to v0.8/0.9 but shows the friction is real.
- vLLM native LoRA on Qwen3.5: several open or regressed problems. #36372 (27B LoRA IndexError, March 2026, dev
  build); #36478 (2B, closed not planned); #47639 (partial LoRA on fused GatedDeltaNet `in_proj_qkv` without `in_proj_z`
  crashes, regression in v0.21.0 through v0.27.1, open at fetch). A third-party repo reports PEFT (transformers 5.17)
  adapters for Qwen3.5 saved with `...model.layers...` keys are silently ignored by vLLM, which expects
  `...language_model.layers...` (adapter served as a no-op; key-rename workaround) [ISSUE, third-party repo
  whilehq/whileai-sdk #588]. Practical rule: **if the training loop serves the adapter through vLLM's native LoRA path
  (verl vLLM rollout, or `vllm serve --enable-lora` for eval), verify the adapter actually changes outputs.** Whether
  TRL syncs merged weights or an adapter into vLLM was not verifiable from the source I could read (Section 4).

**GLM-4.7-Flash:** Unsloth supports fine-tuning (router layer frozen by default, bf16 recommended, "75% reasoning /
25% non-reasoning" data mix advice) but its MoE page does not mention GRPO; no TRL or verl recipe found. verl v0.9.0 lists
GLM-5 (not 4.7-Flash). MLA KV cache was initially mis-instantiated in vLLM (about 20k tokens fit on a 96GB card before the fix).

**DeepSeek-R1-0528-Qwen3-8B:** Qwen3 architecture, so all Qwen3 tooling applies; Unsloth has a GRPO notebook for it.

**Kimi-Linear:** vLLM supported; no LoRA-GRPO recipe found.

### 1.5 Adjacent non-Chinese 2026 small models seen on comparisons (short; likely covered elsewhere)

| Model | Facts | Notes |
|---|---|---|
| google/gemma-4-26B-A4B-it | created 2026-03-11 [API]; 25.8B total / 3.8B active MoE; Apache-2.0; 256K; thinking toggled via `<|think|>` in the system prompt; native function calling [CARD] | Card: tau2 68.2, MMLU-Pro 82.6, LCB v6 77.1, AIME26 88.3; no IFEval/BFCL. Card summary cited arXiv 2607.02770 (July 2026), which conflicts with the March repo date. Gemma 4 E4B: tau2 42.2. On the AgentFloor small-model study, gemma4:26b reached parity with GPT-5 on their tool-use ladder (arXiv 2605.00334). |
| meta-models/Muse-Glimmer-30B | created 2026-08-09 [API]; ~29.8B dense incl. vision encoder; Apache-2.0; 131K+ context; reasoning-strength levels via system prompt [CARD] | Card compares to Gemma4-31B and Qwen3.6-27B on agentic sets; IFBench 77.0 appears only in Qwen3.8-27B's table. 60GB bf16 weights: too big for this setup. |
| nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 | released 2025-12-15 [CARD]; 30B / ~3.5B active hybrid Mamba2-Transformer MoE; NVIDIA Nemotron Open Model License; 1M ctx; `enable_thinking` toggle; `qwen3_coder` parser | Card: IFBench 71.5, BFCL v4 53.8, Arena-Hard-V2 67.7. Post-trained with multi-environment synchronous GRPO in NeMo RL. |
| mistralai/Ministral-3-8B-Instruct-2512 | Dec 2025; ~9B incl. 0.4B vision encoder; Apache-2.0; 256K; native function calling; separate Reasoning variants [CARD] | Card benchmarks are Arena-Hard 0.509, WildBench 66.8; no IFEval/BFCL |

Independent leaderboards: I found no independent small-model IF/tool leaderboard I could read. BenchLM's per-model page
states its Qwen3.6-35B-A3B scores are "official exact-value snapshot from the Hugging Face model card" (provider
self-reported); the BFCL V4 leaderboard page is JavaScript-rendered and returned no rows (page says last updated
2026-04-12); the Artificial Analysis small-open-weight page returned only five rows. The only third-party study of
small open models I opened is AgentFloor (arXiv 2605.00334): 16 models 0.27B-32B (Qwen3 0.6B-32B, Qwen3.5-2B,
Ministral-3, Gemma 4, Nemotron-3-Nano-4B, gpt-oss-20B, Granite 4, Mistral-Small-3.2); it did not evaluate Qwen3.5-9B/4B,
GLM-4.7-Flash or Qwen3.6+, and reported that no model reached acceptable reliability on long-horizon constraint tracking.

### 1.6 Memory arithmetic for the two best fits ([MINE], from verified configs; not measured)

- KV cache per token, bf16: Qwen3.5-9B has only 8 full-attention layers (32 layers, 3:1), 4 KV heads, head_dim 256:
  8 x 4 x 256 x 2 x 2 B = 32 KiB/token, about 0.5 GiB per 16k-token sequence. Qwen3-8B (and R1-0528-Qwen3-8B): 36 layers x 8 KV heads
  x 128 x 2 x 2 B = 144 KiB/token, about 2.25 GiB per 16k-token sequence. For 64 concurrent 16k sequences: ~32 GiB vs ~144 GiB.
  The DeltaNet layers add a constant recurrent state per sequence (assuming fp32 and the config's 32 value heads x 128 x 128
  x 24 layers: about 50 MB/sequence). Long injected precedent context is therefore much cheaper on Qwen3.5 than on Qwen3.
- Weights: Qwen3.5-9B safetensors is ~19.3 GB (four shards, [API]); a rank-16..32 all-linear LoRA is negligible next to that.
- TRL defaults for colocated vLLM: `vllm_gpu_memory_utilization=0.3`, `vllm_enable_sleep_mode` available, `max_completion_length=512`
  default, `num_generations=8` default, `loss_type="dapo"` default, `beta=0.0`, `mask_truncated_completions=False`, `chat_template_kwargs`
  exposed [TRL grpo_config.py, summarizer].
- 16k+ context is not a constraint for any Tier A model. Qwen3-8B is the only one below 262k natively (32k, 131k with YaRN).
  Because the precedent cards must be aligned field-by-field to the scenario, a hybrid with linear-attention layers deserves an
  explicit copy/retrieval probe at your real prompt length before committing ([MINE]; Qwen3.5-9B's card shows AA-LCR 63.0, LongBench v2 55.2,
  which are not the same thing as exact field copying).

## 2. Part 2: RLVR-specific pitfalls in choosing the starting model

### 2(a) Spurious Rewards (Shao et al.) and the multi-family requirement

Source: https://arxiv.org/abs/2506.10947 (v1 2025-06-12; v2 2026-02-25); authors Rulin Shao, Shuyue Stella Li, Rui Xin, Scott Geng,
Yiping Wang, Sewoong Oh, Simon Du, Nathan Lambert, Sewon Min, Ranjay Krishna, Yulia Tsvetkov, Hannaneh Hajishirzi, Pang Wei Koh,
Luke Zettlemoyer. Code: https://github.com/ruixin31/Spurious_Rewards (built on TTRL/OpenRLHF).

- Abstract [PAPER, confirmed]: RLVR "can elicit strong mathematical reasoning in certain language models even with spurious rewards";
  random rewards on Qwen2.5-Math-7B give +21.4 points on MATH-500 vs +29.1 for ground truth; attributed to a GRPO clipping bias that amplifies
  high-prior behaviors, notably "code reasoning" (reasoning in code without execution); spurious rewards "proved ineffective for other model families like
  Llama3 and OLMo2", "highlighting the necessity of cross-model validation".
- Per-model MATH-500 deltas from the PDF body [PAPER, summarizer; verify at table level before quoting]:
  - Qwen2.5-Math-7B: ground truth +29.1, majority vote +13.8, format +24.1, incorrect labels +27.1, random +21.4.
  - Qwen2.5-7B: ground truth +26.0, format +27.8, random +7.4.
  - OLMo2-7B: ground truth +9.0; majority vote -6.4, format -8.3, incorrect -2.1, random -11.5.
  - Llama3.1-8B-Instruct: ground truth +36.8; majority vote -1.3, format -6.3, incorrect -2.2, random -1.3.
  Llama3.2-3B (Instruct) also "rarely" benefited (HTML page). Note format-only reward matched ground truth on the Qwen models.
- Mechanism: code-reasoning frequency in Qwen2.5-Math-7B rose from ~65% to ~90% within 15 steps (95.6% under random rewards); answers using it were 60.9% accurate vs 28.0% without.
  Removing GRPO clipping removes the random-reward gain. Llama/OLMo are characterized as "No-Code" or "Bad-Code".
- Training config: GRPO, lr 5e-7, rollout batch 64, 16 rollouts/prompt, temperature 1.0, clip 0.2, KL off, ~300 steps.
- Recommendation from the authors: "future RLVR research should be confirmed on other models and using spurious rewards as dummy baselines"; many recent RLVR
  papers drew conclusions "primarily or exclusively" from Qwen (they cite ten Qwen2.5-Math-7B-centric works).
- Scope limits: no Qwen3 or Qwen3.5 results in the paper; math benchmarks only. Whether random/format rewards inflate gains on Qwen3.5-9B for YAML-mapping tasks is
  unknown ([MINE] inference: format reward on a structured-output task is exactly the kind of signal that "works" on Qwen).
- Lambert's blog on the result (https://www.interconnects.ai/p/reinforcement-learning-with-random, 2025-05-27/28) reports an earlier 15.8-point
  random-reward gain and the quote: "The right course here is to try and replicate the results on more open models rather than fixating on off-behaviors of any one model."

Implications for this experiment ([MINE]):
1. Any claim that the appended adapter teaches analogical mapping must survive (i) a random-reward control, (ii) a format-only reward control, and (iii) a second, non-Qwen family.
2. Report the format-compliance gain separately from the mapping-quality gain; the first is expected to be large regardless of what the reward "means".
3. Prefer a starting model whose family also has a non-Qwen sibling with the same recipe available in TRL (see 2(d)).

### 2(b) "RL elicits what is already there", contamination, and family differences

- Yue et al. 2025, "Does RL Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model?" https://arxiv.org/abs/2504.13837 (NeurIPS 2025; v5 2025-11-24) [PAPER,
  abstract confirmed]: RLVR models win at small k, base models win at large k (up to 128-1024 samples); "the current training setup does not elicit fundamentally
  new reasoning patterns"; six RL algorithms perform similarly; distillation does add new patterns. Models: primarily Qwen2.5 7B/14B/32B, "additionally LLaMA-3.1-8B",
  DeepSeek-R1-Distill-Qwen, Qwen2.5-VL-7B; the accessible text gives no separate per-family LLaMA curves, so I cannot say the Qwen and Llama results differ or match
  beyond the general claim. Scope: math, code, visual reasoning; not structured output or agentic tasks; predates Qwen3/3.5.
  Project page: https://limit-of-rlvr.github.io/
- Wu et al. 2025, "Reasoning or Memorization? Unreliable Results of RL Due to Data Contamination" https://arxiv.org/abs/2507.10532 (submitted 2025-07-14, revised 2025-12-17)
  [PAPER, abstract confirmed]: Qwen2.5 is contaminated on MATH-500/AMC/AIME; on a leak-free arithmetic generator (RandomCalculation) only accurate rewards help and
  random/incorrect rewards do not. From the PDF body [summarizer]: 60%-prefix exact-match completion on MATH-500 is 54.6% (Qwen2.5-Math-7B), 21.2% (Qwen2.5-7B) vs 3.8% (Llama3.1-8B);
  on LiveMathBench v202505 all are ~0%; **Qwen3 (4B, 8B, 14B) showed the same contamination pattern as Qwen2.5**. They recommend uncontaminated benchmarks and multiple model series.
- Gandhi et al. 2025, "Cognitive Behaviors that Enable Self-Improving Reasoners" https://arxiv.org/abs/2503.01307 [PAPER, abstract confirmed]: under identical RL on Countdown, Qwen-2.5-3B improves far more than
  Llama-3.2-3B because Qwen already shows verification, backtracking, subgoal setting, backward chaining; priming Llama with those behaviors (even from incorrect solutions) lets it match Qwen.
- Wang et al. 2025, OctoThinker https://arxiv.org/abs/2506.20512 [PAPER, abstract level]: studies why Llama and Qwen respond differently to RL; a two-stage mid-training (200B + 20B tokens) closes much of the gap.
- Yan et al. (Lecheng Yan and colleagues), submitted Jan 2026, revised Jun 2026, "Spurious Rewards Paradox" https://arxiv.org/abs/2601.11061 [PAPER, abstract confirmed] (Qwen 2.5): spurious rewards lower answer-token perplexity while prompt coherence degrades; an "Anchor-Adapter circuit" in middle/late layers implements a memorization shortcut.
- Rahman et al. (Salman Rahman and colleagues), Apr 2026, "When Can LLMs Learn to Reason with Weak Supervision?" https://arxiv.org/html/2604.18574 [PAPER, summarizer]: weak-reward generalization "not universal", depends on pre-RL reasoning faithfulness;
  Qwen2.5 on math/science succeeded, Llama failed in every domain and Qwen failed on graph tasks even while training reward saturated.
- Fang Wu et al., "The Invisible Leash" https://arxiv.org/abs/2507.14843 (2025-07-20, revised 2026-02-04) [PAPER, abstract confirmed]: RLVR is a support-constrained optimizer; pass@1 rises while empirical support shrinks.
- Lu et al., "Generalization of RLVR Using Causal Reasoning as a Testbed" https://arxiv.org/html/2512.20760v2 [PAPER, summarizer]: on Qwen2.5-Instruct 3B/7B/32B, "RLVR is ineffective when the reasoning capability of the base model is too poor prior to fine-tuning".
- Qwen3 technical report https://arxiv.org/abs/2505.09388 [PAPER, summarizer]: the 0.6B-14B dense and 30B-A3B Qwen3 models did not get their own RL stage; they were strong-to-weak distilled (off-policy then on-policy from larger teachers), reported to need ~1/10 of the GPU hours of the four-stage recipe. The flagship's reasoning-RL stage used 3,995 query-verifier pairs with GRPO.
  I did not find the equivalent recipe statement for Qwen3.5's small models (not verified).

What this means for choosing a model ([MINE], built on the sources above):
- Check initial reward variance before any RL. GRPO gets no gradient from prompts where all G samples get the same reward. The instruct model must already produce valid, partially-correct YAML mappings on a decent fraction of prompts.
- Because RLVR mostly sharpens what is present, "the LoRA improved the mapping" and "the LoRA made the model more reliably emit the mapping it could already produce" are different claims; the second is what most of the literature above would predict.
- Contamination is largely irrelevant if the scenarios and case cards are private and novel, but becomes relevant if any evaluation uses public ethics/national-security/decision benchmarks; Qwen-family models have documented memorization on public math benchmarks (Qwen2.5, Qwen3), and no contamination audit for Qwen3.5 was found.
- Same-family distillation ancestry matters for interpreting generalization: DeepSeek-R1-0528-Qwen3-8B is a Qwen3-8B derivative, so it is not an independent second family.

### 2(c) Cost of GRPO with thinking models; can hybrids disable thinking during RL?

Evidence gathered:
- Qwen3.5 model cards recommend `max_tokens=32768` for standard queries and `81920` for complex tasks; thinking is the default for 4B/9B/27B/35B (card) and the HF thread "How to disable or reduce thinking" (Qwen3.5-9B discussion #13) includes the complaint that thinking "needlessly burns thousands of tokens thinking itself in circles" (Apr 11 comment). https://huggingface.co/Qwen/Qwen3.5-9B/discussions/13
- DAPO (https://arxiv.org/abs/2503.14476) trained Qwen2.5-32B with a 16,384-token base limit plus 4,096-token soft overlong buffer (20,480 total) and added overlong reward shaping, token-level loss, dynamic sampling and clip-higher [PAPER, summarizer]. Dr. GRPO (https://arxiv.org/abs/2503.20783) shows GRPO's normalization "artificially increases response length (especially for incorrect outputs)". ScaleRL (https://arxiv.org/abs/2510.13786): >400,000 GPU-hours of ablations; loss aggregation/normalization mostly change efficiency rather than ceiling.
- TRL exposes `mask_truncated_completions` (default False), `loss_type` in {grpo, dr_grpo, dapo (default), bnpo, cispo, sapo, luspo, vespo}, `importance_sampling_level` (token default; sequence = GSPO), `vllm_importance_sampling_correction=True`, `max_tool_calling_iterations`, and `chat_template_kwargs` (documented use: `enable_thinking=False`) [TRL grpo_config.py].
- Which hybrids allow thinking off, verified from templates/cards:
  - Qwen3-8B: yes (`enable_thinking`, `/no_think`).
  - Qwen3.5 (4B/9B/27B/35B-A3B), Qwen3.6, Qwen3.8: yes via `chat_template_kwargs={"enable_thinking": False}`; **no `/think` soft switch on Qwen3.5**. Verified in the Qwen3.5-9B chat template: with thinking off the generation prompt is `<|im_start|>assistant\n<think>\n\n</think>\n\n` (an empty think block is pre-filled); with thinking on it is `<|im_start|>assistant\n<think>\n`. Qwen3.8 additionally has `reasoning_effort` (xhigh default / medium / low) and `preserve_thinking`.
  - GLM-4.7-Flash: template has `enable_thinking`/`clear_thinking` [CONFIG]; the model card documents "Preserved Thinking" but no explicit off instruction.
  - Qwen3-4B-Instruct-2507, Qwen3-30B-A3B-Instruct-2507: non-thinking only, nothing to toggle.
  - R1-0528-Qwen3-8B: always thinks.
  - Gemma 4 (`<|think|>` system token) and Nemotron-3-Nano (`enable_thinking`) also toggle.
- Existence proof of non-thinking GRPO+LoRA: a Sept 2026 HF adapter (`sandeep123/grpo-qwen3-4b-nonthinking-entropy-2048-20260918`, https://huggingface.co/sandeep123/grpo-qwen3-4b-nonthinking-entropy-2048-20260918)
  trained Qwen3-4B-Instruct-2507 with LoRA r=16/alpha=32, 64 prompts x 8 rollouts, 8,192-token window, `enable_thinking=False` rendered at training time. It is a single third-party card, not a study.

Cost model ([MINE], illustrative, not measured): decode tokens per optimizer step = prompts x G x mean completion length. With 16 prompts x G=8 = 128 rollouts:
~1k-token YAML completions give ~0.13M tokens/step; if thinking adds 6-10k tokens, that is ~0.8-1.3M tokens/step, a 6-10x decode increase, plus more truncation
(a truncated `<think>` never reaches the YAML, so the reward is 0 by construction and adds noise unless masked), plus higher variance in sequence lengths across the group (the
straggler problem in colocated vLLM). The 6-10k figure is an assumption consistent with the 32k/81k `max_tokens` guidance and community reports above, not a measurement of your task.

Research-design consequences ([MINE]):
- Your task emits an explicit YAML mapping "before choosing an action". If a hidden `<think>` block also exists, the reward attaches to the YAML and action while much of the actual reasoning is unrewarded and unobserved by the verifier; the mapping may stop being a faithful trace of the computation. For a study of whether a structured mapping drives behavior, non-thinking mode (mapping = the visible reasoning) is the cleaner design as well as the cheaper one.
- Cards report thinking-mode numbers and do not give non-thinking numbers for Qwen3.5-9B/4B. The only non-thinking small-Qwen3.5 table I found is the 2B card: IFEval 61.2 (0.8B: 52.1) vs Qwen3-4B-Instruct-2507's 83.4 in the same table. That does not tell us the 9B number, but it is a warning that the headline IFEval 91.5 may not survive `enable_thinking=False`. Measure the baseline in the exact mode you will train.
- Train and evaluate in the same mode; a LoRA trained with the empty-think prefill may not transfer to thinking mode.

### 2(d) Which families are common RLVR starting points, and which have mature GRPO + LoRA recipes

I found no systematic tally. The awesome-RLVR list (https://github.com/opendilab/awesome-RLVR, 135+ papers) gives no base-model statistics. What the sources above do show:
- Qwen dominates published RLVR: Spurious Rewards counts at least ten Qwen2.5-Math-7B-centric papers; DAPO used Qwen2.5-32B; Yue et al. used Qwen2.5 7B/14B/32B primarily; Dr. GRPO used Qwen2.5-Math; the agentic-RL interference paper (arXiv 2602.00994) used Qwen2.5 3B/7B, Qwen2.5-7B-Coder, Qwen3-14B and Llama3.1-8B; a Sept 2026 small-search-agent paper (arXiv 2609.28765) trained only Qwen3.5-0.8B and states that every checkpoint is Qwen3.5-0.8B with no cross-architecture validation.
- Non-Qwen starting points that appear: Llama-3.1-8B (Thinking Machines chose it as the base for its RL-LoRA experiments because "other models had pretraining advantages on math"), Llama 3.1/3.2 and OLMo 2 (Spurious Rewards, Tulu 3 RLVR per 20-open-recipes-and-costs.md, not re-opened here), SmolLM3-3B (TRL's LoRA-without-regret guide), Nemotron-3-Nano (NVIDIA's own GRPO), Gemma 3/4 and gpt-oss-20B (Unsloth notebooks).
- HF `downloads` counter (window unspecified) as a popularity proxy [API]: Qwen3-8B 12.5M; Gemma-4-26B-A4B-it 11.5M; Qwen3.5-9B 9.2M; Qwen3.5-4B 7.1M; Qwen3.8-27B 6.6M; Qwen3-4B-Instruct-2507 3.9M; Qwen3.6-35B-A3B 3.2M; Qwen3.5-27B 2.3M; GLM-4.7-Flash 1.9M; Kimi-Linear-48B 0.17M. This measures inference/fine-tune traffic, not RLVR papers.
- LoRA in RL: Thinking Machines "LoRA Without Regret" (https://thinkingmachines.ai/blog/lora/, 2025-09-29) reports LoRA matches full fine-tuning for policy-gradient RL "even with ranks as low as 1", because advantage-driven learning carries O(1) bits per episode; apply LoRA to all layers including MLP; optimal LoRA LR is ~10x full-FT LR. TRL's recipe (https://huggingface.co/docs/trl/en/lora_without_regret): r=1..32, `target_modules="all-linear"`, effective batch < 32, on SmolLM3-3B.

Maturity ranking for TRL/Unsloth/verl/vLLM-LoRA GRPO ([MINE], from Section 1.4 evidence):
1. High: Qwen2.5 and Qwen3 dense (4B, 8B) incl. Qwen3-4B-Instruct-2507; Llama 3.1/3.2; DeepSeek-R1-0528-Qwen3-8B (Qwen3 architecture).
2. Medium: Gemma 3/4 and gpt-oss-20B (Unsloth notebooks); Nemotron-3-Nano (native NeMo-RL).
3. Working but friction-heavy, pin versions: Qwen3.5 / 3.6 / 3.8 (transformers v5, vLLM >=0.27.0 for TRL weight sync, fla + causal-conv1d kernels, vLLM native-LoRA bugs, Unsloth `fast_inference` caveat).
4. Undocumented for GRPO: GLM-4.7-Flash, Kimi-Linear, Muse-Glimmer.

## 3. Working recommendation (judgment; the choice is yours)

- Primary: **Qwen/Qwen3.5-9B**, trained with `enable_thinking=False` in TRL (vLLM >=0.27.0, fla + causal-conv1d, transformers v5). Strongest documented small-model IF/agentic numbers, cheapest long-context KV, Apache-2.0, native 262k. Gate: a non-thinking baseline on your own held-out prompts must clear a threshold before you spend RL compute (card numbers are thinking-mode).
- Mature-tooling fallback and cheap debug model: **Qwen/Qwen3-4B-Instruct-2507** (non-thinking only, plain transformer, Unsloth/TRL/verl recipes exist), or Qwen3-8B with thinking off.
- Second family for the Spurious-Rewards-style control: a non-Qwen dense ~8B instruct (Llama-3.1-8B-Instruct or OLMo-3-7B-Instruct per file 20, or Ministral-3-8B/Gemma 4 small) trained with the same reward and recipe. Note DeepSeek-R1-0528-Qwen3-8B does not count as a second family.
- Controls: random-reward, format-only-reward, shuffled/irrelevant case cards, and evaluation with pass@k at large k in addition to pass@1 (Yue et al.).

## 4. Facts I could not verify, or where sources conflict

1. Official public release date of Qwen3.5-9B/4B: HF repo `createdAt` 2026-02-27 [API] vs 2026-03-02 in the QwenLM/Qwen3.8 README table; the first summary said "February 2026". Not resolved.
2. Default thinking state of Qwen3.5 small models: the HF 9B/4B cards and chat template say ON by default; Unsloth docs and an Unsloth GGUF discussion say small models (0.8-9B) default to reasoning disabled; the 2B card says "non-thinking mode by default". Likely differs by size and by packaging; always set it explicitly.
3. Whether the Qwen3.5 card benchmark rows are thinking-mode: the 9B/4B/27B/35B cards do not label rows; the 2B card labels separate tables. Assumed thinking-mode.
4. Non-thinking IFEval/BFCL/tau2 for Qwen3.5-9B/4B: not published on their cards.
5. IFEval/BFCL/tau2 for Qwen3.6-27B, Qwen3.6-35B-A3B and Qwen3.8-27B: not found on the cards (only IFBench 79.5 for 3.8-27B; Qwen3.6 reports TAU3-Bench and other agentic sets). Qwen3.6-35B-A3B's TAU3 values were not captured.
6. Qwen3-8B tool-use and IFEval figures come from the tech report PDF via the summarizer (non-thinking IFEval 83.0, BFCL v3 60.2); the Table 17/18/21 numbers could not be re-extracted from the HTML version.
7. All Spurious Rewards per-model numbers except the abstract's 21.4/29.1 came via the PDF summarizer; not table-verified. Also v1 vs v2 (Feb 2026) changes are not known; the Notion blog page was JavaScript-only and returned nothing.
8. Yue et al.: no per-family (Llama vs Qwen) results found in the accessible text.
9. How TRL moves LoRA weights into vLLM (merged weights vs adapter): not verifiable from the source excerpt I could read; TRL's vLLM doc says LoRA handling is not detailed.
10. Current state of the vLLM Qwen3.5 LoRA bugs (#36372, #47639, and the third-party no-op-adapter report) after v0.27.1; Unsloth PR #10891 merge state; whether the Unsloth `fast_inference=False` advice is still current.
11. verl: Qwen3.5 FSDP-LoRA support (release notes say LoRA + MTP "with Megatron-Bridge"); whether verl supports Qwen3.5 well enough for a Sept 2026 paper to still call it unsupported.
12. Whether Qwen3.5-9B's small hybrid models received their own RL stage or were distilled (no source found for Qwen3.5; the Qwen3 report says Qwen3 small models were distilled, not RL-trained).
13. GLM-4.7-Flash: no explicit thinking-off instruction on the card; whether a TRL/verl GRPO recipe exists; exact active parameters (card says A3B; config shows 4 routed + 1 shared expert of 64).
14. Kimi and DeepSeek: I cannot rule out small models older than the HF org listing windows (Kimi back to 2025-02, DeepSeek back to 2025-11).
15. Aggregators disagree with HF: DeepSeek-V4.1-Flash size (aggregator 552B vs API 763B), Qwen3.8-Flash-Next (aggregator 125B/MIT vs API ~180B/"qwen-community-1.0"), GLM-5.3-Flash date/context (Feb 17 2026 + 300K vs API 2026-08-25). Irrelevant to sizing here but a reminder not to trust aggregators.
16. Gemma 4 release date (repo created 2026-03-11 vs card citing a July 2026 arXiv number); Nemotron/Ministral numbers are card-summarizer only.
17. Throughput numbers and thinking-length assumptions in Section 2(c): not measured.
18. The HF `downloads` window (assumed 30 days) is not stated by the API summary.

## 5. Source index (all opened this session unless marked)

Model cards / repos
- https://huggingface.co/Qwen/Qwen3.5-9B , .../Qwen3.5-4B , .../Qwen3.5-2B , .../Qwen3.5-27B , .../Qwen3.5-35B-A3B
- https://huggingface.co/Qwen/Qwen3.6-27B , .../Qwen3.6-35B-A3B , https://huggingface.co/Qwen/Qwen3.8-27B
- https://huggingface.co/Qwen/Qwen3-8B , .../Qwen3-4B-Instruct-2507 , .../Qwen3-30B-A3B-Instruct-2507
- https://github.com/QwenLM/Qwen3.8 (release table 3.5/3.6/3.8)
- https://huggingface.co/zai-org/GLM-4.7-Flash , .../GLM-5.3-Flash , .../GLM-4.6V-Flash , .../GLM-4-9B-0414
- https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B
- https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Instruct
- https://huggingface.co/google/gemma-4-26B-A4B-it , https://huggingface.co/meta-models/Muse-Glimmer-30B , https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 , https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512
- HF API listings used for dates/sizes: https://huggingface.co/api/models?author=deepseek-ai (also moonshotai, zai-org, Qwen) and per-model `/api/models/<id>`
- Qwen3.5 chat template: https://huggingface.co/Qwen/Qwen3.5-9B/raw/main/chat_template.jinja ; GLM template: https://huggingface.co/zai-org/GLM-4.7-Flash/raw/main/chat_template.jinja

Papers
- https://arxiv.org/abs/2506.10947 (Spurious Rewards) ; https://arxiv.org/abs/2504.13837 (Yue et al.) ; https://arxiv.org/abs/2507.10532 (Wu et al., contamination)
- https://arxiv.org/abs/2503.01307 (Gandhi et al.) ; https://arxiv.org/abs/2506.20512 (OctoThinker) ; https://arxiv.org/abs/2507.14843 (Invisible Leash) ; https://arxiv.org/abs/2601.11061 (Spurious Rewards Paradox)
- https://arxiv.org/html/2604.18574 (weak supervision) ; https://arxiv.org/html/2512.20760v2 (causal-reasoning RLVR) ; https://arxiv.org/html/2602.00994v3 (reasoning vs tool-use in agentic RL) ; https://arxiv.org/html/2609.28765 (small search agents, Qwen3.5-0.8B)
- https://arxiv.org/abs/2505.09388 (Qwen3 report) ; https://arxiv.org/abs/2503.14476 (DAPO) ; https://arxiv.org/abs/2503.20783 (Dr. GRPO) ; https://arxiv.org/abs/2510.13786 (ScaleRL) ; https://arxiv.org/html/2605.00334v1 (AgentFloor)
- https://thinkingmachines.ai/blog/lora/ ; https://www.interconnects.ai/p/reinforcement-learning-with-random ; https://github.com/ruixin31/Spurious_Rewards ; https://github.com/opendilab/awesome-RLVR

Tooling
- TRL: https://github.com/huggingface/trl/blob/main/trl/trainer/grpo_config.py ; https://github.com/huggingface/trl/blob/main/docs/source/grpo_trainer.md ; https://huggingface.co/docs/trl/vllm_integration ; https://huggingface.co/docs/trl/reducing_memory_usage ; https://huggingface.co/docs/trl/en/lora_without_regret ; https://github.com/huggingface/trl/issues/5269
- Unsloth: https://unsloth.ai/docs/models/qwen3.5/fine-tune ; https://unsloth.ai/docs/models/qwen3.5 ; https://unsloth.ai/docs/models/qwen3.8/train ; https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide ; https://unsloth.ai/docs/basics/faster-moe ; https://unsloth.ai/docs/models/tutorials/glm-4.7-flash ; https://github.com/unslothai/unsloth/pull/10891
- verl: https://github.com/verl-project/verl (README) ; release notes via https://api.github.com/repos/verl-project/verl/releases ; https://verl.readthedocs.io/en/latest/advance/ppo_lora.html ; https://huggingface.co/blog/Weyaxi/engineering-handbook-grpo-lora-with-verl ; issues https://github.com/verl-project/verl/issues/6549 , /6662 , /5937 , /7847
- vLLM: https://github.com/vllm-project/vllm/issues/36275 , /36372 , /36478 , /40869 (vllm-ascend) , /47639 ; third-party https://github.com/whilehq/whileai-sdk/issues/588
- transformers: https://github.com/huggingface/transformers/issues/48718

Aggregators consulted but not relied on: codersera.com Qwen guide; local-ai-zone.github.io flash-tier comparison; deepseekmodel.com; benchlm.ai; thundercompute.com; computingforgeeks.com; llm-stats.com; artificialanalysis.ai (partial page).
