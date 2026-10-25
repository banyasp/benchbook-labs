# Open post-training recipes and compute/cost anchors, for a ~$23K AWS budget

Research question this supports: whether to test a new skill (structured analogical
reasoning over injected precedent cases) as (a) appended after full post-training, or
(b) mixed into the SFT/RLVR stages of post-training itself, without redoing pretraining.
(b) requires a fully open recipe with released data, code, and intermediate checkpoints.

Compiled 2026-09-28. Every number below is tagged with its source and a confidence note.
Where two sources disagreed or a figure could not be found, that is flagged explicitly —
see the "NOT VERIFIED / FLAGGED" list at the end.

---

## 1. AI2 Tülu 3 (SFT → DPO → RLVR) and OLMo 2

### 1.1 What Tülu 3 itself is (base: Llama 3.1)

Tülu 3 is AI2's fully open **post-training recipe**, applied on top of Meta's Llama 3.1
base checkpoints (not a from-scratch pretrain). Five stages: prompt curation, SFT, DPO
(on- and off-policy preference data), RLVR (a new RL stage using verifiable rewards
instead of a learned reward model for tasks with checkable answers — GSM8K, MATH,
IFEval), and a standardized eval suite.

- Paper: Tülu 3: Pushing Frontiers in Open Language Model Post-Training —
  https://arxiv.org/abs/2411.15124 (PDF: https://arxiv.org/pdf/2411.15124)
- Blog/overview: https://allenai.org/blog/tulu-3-technical
- Code (training + eval pipeline): **open-instruct** —
  https://github.com/allenai/open-instruct
  (recipe doc: https://github.com/allenai/open-instruct/blob/main/docs/tulu3.md)
- Datasets collection: https://huggingface.co/collections/allenai/tulu-3-datasets-673b8df14442393f7213f372
- 405B scale-up (surpassing DeepSeek V3): https://allenai.org/blog/tulu-3-405b

**Sizes released for Tülu 3 proper: 8B and 70B (and later 405B).** No native 1B or 13B
Tülu-3-branded model — those sizes come from OLMo 2 (see 1.3), which reuses the Tülu 3
*recipe* but is a separate model family.

### 1.2 SFT mix size

Final SFT mixture ("Tulu 3 SFT Mix"): **939,344 examples**, verified directly on the
dataset card. Composed of ~18 sources: FLAN v2 (89,982), Aya (100,000), Evol CodeAlpaca
(107,276), NuminaMath-TIR (64,312), WildGuardMix (50,000), WildJailbreak (50,000),
CoCoNot (10,983), OpenAssistant Guanaco (7,132), SciRIFF (10,000), TableGPT (5,000), etc.
- Dataset card: https://huggingface.co/datasets/allenai/tulu-3-sft-mixture

### 1.3 RLVR setup

RLVR replaces the reward *model* with a verification *function* for tasks that have a
checkable ground-truth answer (math final-answer matching for GSM8K/MATH, constraint
satisfaction for IFEval). Reported gains over the DPO checkpoint: up to **+1.7 (MATH),
+3.3 (GSM8K), +1.3 (IFEval)** points. The open-instruct docs describe the underlying
algorithm as a PPO-style on-policy RL loop (their later work names this "RLVR" and a
GRPO/PPO variant is configurable in open-instruct). I could not pin down from the
fetched text alone whether the paper explicitly names "PPO" vs a custom variant as the
default — treat that specific algorithmic label as needing a direct read of the
paper's RL section (§6) rather than my extraction.

### 1.4 Released checkpoints

Confirmed on HF / in the open-instruct docs, for **8B and 70B** (and 405B):
- `allenai/Llama-3.1-Tulu-3-8B-SFT`, `-70B-SFT` (and 405B)
- `allenai/Llama-3.1-Tulu-3-8B-DPO`, `-70B-DPO`, `-405B-DPO`
- `allenai/Llama-3.1-Tulu-3-8B-RM` (reward model, used for a PPO-based RLVR variant/ablation)
- `allenai/Llama-3.1-Tulu-3-8B`, `-70B`, `-405B` (final, post-RLVR)
- A later `Llama-3.1-Tulu-3.1-8B` also exists.

**So for 8B/70B, base → SFT → DPO → final(RLVR) are all separately released** — this is
the strongest "fully open, every intermediate checkpoint available" case for option (b).

### 1.5 Reported compute (SFT / DPO stages) — CONFLICTING SOURCES, flagged

Two different extractions of ostensibly the same numbers disagreed and I could not
reconcile them from what the fetch tool returned; both are given below with source,
and I recommend reading the paper's compute/appendix section directly before budgeting
against these.

**From the arXiv PDF (per one extraction pass):**
| Stage | 8B | 70B |
|---|---|---|
| SFT | 32 GPUs (H100) × 6 hours ≈ 192 GPU-hr | 64 GPUs × 50 hours ≈ 3,200 GPU-hr |
| DPO | 8 H100s × 10 hours = 80 GPU-hr | 64 H100s × 19 hours ≈ 1,216 GPU-hr |
| RLVR | not disclosed in the excerpt reached | not disclosed |

**From `open-instruct/docs/tulu3.md` (per a separate extraction pass):**
| Stage | 8B | 70B |
|---|---|---|
| SFT | 64 H100s (8 nodes × 8 GPUs), 2 epochs, batch 128 — **no wall-clock given** | 64 H100s, 2 epochs |
| DPO | 8 H100s (1 node), 1 epoch, batch 128 — **no wall-clock given** | 64 H100s, 1 epoch |
| RLVR/PPO | ~7 actor GPUs + separate inference/learner GPUs (exact total unclear) | multi-node, exact GPU count unclear from what was extracted |

The GPU **counts** for 8B SFT disagree (32 vs 64) and neither source gave me a clean,
directly-quotable RLVR wall-clock figure for 8B or 70B. **Treat all of the above as
approximate / needs-primary-source-confirmation**, not as numbers to size a budget
against without re-checking Table references in the paper (§9/Appendix) or the
`docs/tulu3.md` scripts (`scripts/train/tulu3/*.sh`) directly.

- Sources: https://arxiv.org/pdf/2411.15124 ; https://github.com/allenai/open-instruct/blob/main/docs/tulu3.md

### 1.6 OLMo 2 — checkpoints across 1B / 7B / 13B / 32B

OLMo 2 is AI2's own base-model family (own pretraining, not Llama-based), post-trained
with the Tülu 3 recipe. Confirmed full checkpoint inventory (HF collection):
https://huggingface.co/collections/allenai/olmo-2-674117b93ab84e98afc72edc

- **1B** (`OLMo-2-0425-1B`, a later/April-2025 release): Base, SFT, DPO, **RLVR1**,
  Instruct, plus GGUF variants. Recipe per the model card: **SFT + DPO + GRPO**
  (GRPO used as their RLVR algorithm at this scale) on a mid-trained checkpoint
  (50B Dolmino-Mix-1124 tokens). Preference mix:
  https://huggingface.co/datasets/allenai/olmo-2-0425-1b-preference-mix
  — **No GPU-hour/compute figures published** for the 1B post-training stages
  (checked model card directly).
- **7B** (`OLMo-2-1124-7B`): Base, SFT, DPO, RM, Instruct.
- **13B** (`OLMo-2-1124-13B`): Base, SFT, DPO, RM, Instruct, plus **RLVR1/RLVR2**
  preliminary variants.
- **32B** (`OLMo-2-0325-32B`): Base, SFT, DPO, Instruct (no separate RM/RLVR checkpoint
  seen in the listing).

So **1B, 7B, 13B, and 32B all have base+SFT+DPO+final released**, making OLMo 2 (not
just Tülu 3 8B/70B) a strong candidate if 1B-scale experiments are wanted with a fully
open recipe. Pretraining scale: "up to 5T tokens" (7B ≈ 1 epoch, 13B ≈ 1.2 epochs to 5T);
no separate post-training GPU-hour figures were found for OLMo 2 either.

- Blog: https://allenai.org/blog/olmo2

---

## 2. OLMo 3 (Nov 2025, updated 3.1 in Dec 2025)

Ai2's newest fully-open family; explicitly pitched as the "most open" release,
overhauling the whole pipeline (pretraining data → mid-training → long-context →
post-training) with fresh code and data at every stage.

- Blog: https://allenai.org/blog/olmo3
- Deep-dive analysis: https://www.interconnects.ai/p/olmo-3-americas-truly-open-reasoning
- Deep-dive analysis #2: https://cameronrwolfe.substack.com/p/olmo-3
- HF collection: https://huggingface.co/collections/allenai/olmo-3

### 2.1 What was released

Four model lines, **7B and 32B**:
- **Olmo 3-Base** (7B, 32B)
- **Olmo 3-Think** (7B, 32B) — reasoning model with visible `<think>` traces
- **Olmo 3-Instruct** (7B only at initial release) — low-latency chat model
- **Olmo 3-RL Zero** (7B) — RL-from-base-model experimental line, released as **4
  separate checkpoints/datasets per data domain** (math, code, instruction-following,
  general), confirmed via `allenai/Olmo-3-7B-RL-Zero-General` and
  `allenai/Olmo-3.1-7B-RL-Zero-Code` on HF.
- **Dec-2025 (v3.1) update** added **Olmo 3.1-Think-32B** and **Olmo 3.1-Instruct-32B**,
  plus refreshed RL Zero 7B variants (`allenai/Olmo-3.1-32B-Think` confirmed on HF).

### 2.2 Post-training data: "Dolci"

**Dolci is confirmed real and inspected directly** (dataset cards, not secondary
summaries):
- `allenai/Dolci-Instruct-SFT` — **2,152,112 examples**, a mixture of 22 sources
  (OpenThoughts 3: 941,166; Tülu-3-derived math/code/algebra subsets; WildGuardMix
  49,373; Aya 99,987; Evol CodeAlpaca 107,270; plus new AI2 contributions — Dolci
  Tülu 3 Precise IF 136,833, Dolci Instruct Python Algorithms 186,345, logic puzzles
  159,882, "verifiable reasoning" 310,572, Dolci Instruct Tool Use 227,579).
  https://huggingface.co/datasets/allenai/Dolci-Instruct-SFT
- `allenai/Dolci-Think-SFT-32B` — **2,253,684 examples / 36GB**, reasoning-trace
  variant for the 32B Think model (OpenThoughts 3, SYNTHETIC-2, Nemotron
  Post-training data, plus new AI2 "Dolci Think" subsets — Persona IF 220,530,
  Precise IF 135,722, Think Python 466,676).
  https://huggingface.co/datasets/allenai/Dolci-Think-SFT-32B
- `allenai/Dolci-Instruct-SFT-Tool-Use` (a smaller tool-use-specific SFT set) also
  exists as a separate dataset.
- I did **not** independently confirm exact example counts for a "Dolci-*-DPO" or
  "Dolci-*-RLVR" dataset card (I saw the DPO/RLVR **checkpoints** — see 2.3 — but
  didn't pull the matching dataset cards' row counts).

### 2.3 Intermediate checkpoints — confirmed open, full SFT→DPO→RLVR chain

Directly confirmed on the `Olmo-3-7B-Instruct-SFT` model card:
- Pipeline: `allenai/Olmo-3-1025-7B` (base) → **`Olmo-3-7B-Instruct-SFT`** (trained
  on Dolci-Instruct-SFT-7B, 2.15M examples, + a small 1.6k-example tool-use set) →
  **`Olmo-3-7B-Instruct-DPO`** → **`Olmo-3-7B-Instruct`** (final, post-RLVR).
- https://huggingface.co/allenai/Olmo-3-7B-Instruct-SFT
- The Ai2 blog and the interconnects.ai / substack write-ups both independently state
  the release includes "checkpoints from each major training milestone" (base,
  mid-trained, long-context-extended, post-training stages) and that data is
  "available for download without any license restrictions."
- **This makes OLMo 3 7B the single best-documented fully-open target for option (b)**
  (mixing new SFT data into the real SFT mix, and new verifiable rewards into the real
  RLVR stage) among everything surveyed here, given both the checkpoint chain and the
  dataset composition are independently inspectable.

### 2.4 Compute figures

- **Pretraining (official, from Ai2's own Discord, relayed by a third party — not the
  tech report itself):** 7B ≈ **234,000 H100-GPU-hours**; 32B ≈ **1,050,000
  H100-GPU-hours** (includes restarts/evals/checkpointing overhead). Source:
  https://muxup.com/2025q4/minipost-olmo3-training-cost (this is a blog post relaying
  a Discord answer from the Olmo 3 team — treat pretraining figures as
  semi-official/unverified-primary-source).
- Separately, the Ai2 blog itself states pretraining used **up to 1,024 H100 GPUs**
  (7B, ~7.7K tokens/device/sec), mid-training used **128 H100 GPUs**, and
  **post-training used 256 H100 GPUs**, with "4x efficiency improvements" claimed from
  RL infrastructure work — but **no wall-clock or total GPU-hour figure for
  post-training specifically** was stated. Source: https://allenai.org/blog/olmo3
- **Post-training compute (GPU-hours) is explicitly NOT reported** — the muxup.com
  minipost states the initial Olmo 3 technical report "has little to say" on
  post-training compute/energy and promises detail "in a future version of the
  paper." As a rough anchor only, that same post notes DeepSeek-V3.2's post-training
  compute was reported at >10% of its pretraining compute — suggesting (not
  confirming) Olmo-3-7B post-training might be very roughly in the tens-of-thousands
  of GPU-hours range, but this is speculative and NOT an Ai2-sourced number.

### 2.5 Code

- Pretraining/mid-training framework: https://github.com/allenai/OLMo-core
- Post-training pipeline: same **open-instruct** repo as Tülu 3 —
  https://github.com/allenai/open-instruct
- Supporting tools mentioned: `datamap-rs`, `duplodocus`, `OLMES` (eval), `decon`.

---

## 3. Other fully open post-training recipes with intermediate checkpoints

- **Hugging Face SmolLM3 (3B):** Base + final (Instruct/reasoning) checkpoints
  released (`HuggingFaceTB/SmolLM3-3B-Base`, `HuggingFaceTB/SmolLM3-3B`). Post-training
  recipe: SFT on **1.8B tokens** (1B non-reasoning + 0.8B reasoning, 12+10 datasets,
  some reasoning traces synthesized by prompting Qwen3-32B) → **Anchored Preference
  Optimization (APO)**, a DPO variant, using the Tülu 3 preference dataset for
  non-reasoning mode and Qwen3-generated synthetic pairs for reasoning mode → a final
  **model-merge** step (0.9/0.1 linear merge of the APO checkpoint with a
  mid-training checkpoint) to recover long-context ability. Training code:
  https://github.com/huggingface/smollm ; blog: https://huggingface.co/blog/smollm3 ;
  data: SmolTalk2 collection (Mid/SFT/Preference subsets) + `smollm3-configs`.
  **Caveat:** intermediate SFT-only and APO-only checkpoints (as separately loadable
  HF models) were not confirmed — the blog says training logs/checkpoints are on
  Weights & Biases, which is not the same as a downloadable HF checkpoint per stage.
  Pretraining compute (384 H100s × 24 days, 11.2T tokens) is well documented;
  **post-training-specific GPU-hours were not found** in the blog or subsequent
  searches.
- **Marin (Stanford, 8B):** Fully open training code, data recipes (each experiment
  declared in code + tracked via GitHub issues), base + instruct weights
  (`marin-community/marin-8b-base`, `marin-community/marin-8b-instruct`). As of the
  announcement post, the instruct model was SFT-only (~5B tokens) — **the team
  explicitly states they had "not yet done any RLHF, not even DPO"** as of that post,
  so it is *not* currently a fully-open SFT+DPO+RLVR reference (may have since been
  extended — not re-checked beyond the announcement post). Compute: trained mostly on
  Google TPU Research Cloud allocation; no GPU/TPU-hour figures published.
  Blog: https://marin.community/blog/2025/05/19/announcement/
- **LLM360 K2 (65B):** "base, chat" models released, with intermediate **pretraining**
  checkpoints extensively published (e.g., stage-1/stage-2 checkpoint series) and a
  full datasets repo (`LLM360/K2Datasets`, 13 datasets, 1.3T tokens). LLM360 advertises
  full transparency ("code, data, model checkpoints, intermediate results"). **I could
  not confirm from the model card whether the chat/post-training stage (SFT/RLHF) has
  its own separately released intermediate checkpoints** the way OLMo 3's Dolci
  pipeline does — this needs a direct read of the K2 tech report
  (https://arxiv.org/html/2501.07124v3) rather than the HF card alone. A newer
  **K2-V2** ("360-Open, Reasoning-Enhanced") also exists (arXiv 2512.06201) — not
  investigated in depth here.
  HF: https://huggingface.co/LLM360/K2

**Bottom line for option (b):** of everything surveyed, **OLMo 3 (7B) and OLMo 2
(1B/7B/13B/32B) are the only recipes with a *fully* open, well-documented, multi-stage
(SFT→DPO→RLVR) checkpoint chain plus matching open data**, both built on the same
**open-instruct** codebase. Tülu 3 (8B/70B on Llama 3.1) is equally open but has no
native 1B. SmolLM3, Marin, and K2 are open in spirit/code/data but each has a gap
(SmolLM3: unclear per-stage checkpoints; Marin: no RLHF/DPO stage as of the last
checked post; K2: post-training openness unconfirmed) that would need to be closed
before treating them as (b)-ready.

---

## 4. Cost anchors: AWS GPU pricing and rough GPU-hour/cost estimates

### 4.1 AWS on-demand list prices (verified against two independent sources each)

- **p5.48xlarge (8× H100 80GB):** **$55.04/hr** on-demand → **$6.88/GPU-hr**.
  Confirmed by both https://instances.vantage.sh/aws/ec2/p5.48xlarge and
  https://www.thundercompute.com/blog/aws-p5-vs-thunder-compute (which gives a
  $55.04–$68.80/hr range depending on region, i.e. up to $8.60/GPU-hr in the more
  expensive regions).
- **p4d.24xlarge (8× A100 40GB):** **$21.96/hr** on-demand (≈$21.957642 precisely) →
  **≈$2.74/GPU-hr**. Source: https://instances.vantage.sh/aws/ec2/p4d.24xlarge
  (not independently cross-checked against a second source — flagged below).
- These are **on-demand list prices**, the most expensive AWS tier. AWS also offers
  **EC2 Capacity Blocks for ML** (reserved short-term blocks, typically cheaper than
  on-demand) at https://aws.amazon.com/ec2/capacityblocks/pricing — I did not pull
  actual Capacity Block or Spot rates; treat true achievable pricing as likely lower
  than the on-demand figures above, especially for a planned, non-urgent training run.

### 4.2 Rough GPU-hour / dollar estimates to re-run the Tülu 3-style recipe (SFT+DPO+RLVR)

These are **my own back-of-envelope estimates**, built from the (already
uncertain/conflicting, see §1.5) reported Tülu 3 8B/70B figures, extrapolated down to
1B by rough parameter-count scaling. They are NOT independently sourced figures —
use them only as an order-of-magnitude sanity check, not a budget input.

- **8B, using the higher of the two conflicting SFT/DPO readings (§1.5) as an upper
  bound:** SFT ≈ 192–384 GPU-hr, DPO ≈ 80 GPU-hr. RLVR/PPO compute for 8B was not
  disclosed in either source I could reach; RLVR/PPO rollout-heavy training is
  typically the most expensive of the three stages in absolute wall-clock (multiple
  rollout generations per gradient step), so a plausible (unverified) planning
  assumption is that RLVR costs somewhere between 1–5× the DPO stage. Under that
  assumption, total 8B post-training ≈ **500–1,500 H100-GPU-hours**, i.e. roughly
  **$3,400–$10,300** at the $6.88/GPU-hr on-demand H100 rate (or **$1,400–$4,100** at
  the $2.74/GPU-hr A100 rate, ignoring throughput differences — A100 runs would take
  proportionally longer wall-clock for the same GPU-hour budget since H100 is
  meaningfully faster per-GPU for this class of model).
- **1B:** No primary-source compute figures exist for Tülu-recipe post-training at 1B
  (OLMo-2-0425-1B's model card gives no GPU-hour numbers). Scaling very roughly by
  parameter count (1B is ~1/8 of 8B), a plausible planning estimate is **on the order
  of 100–300 H100-GPU-hours** total for SFT+DPO+RLVR at 1B, i.e. roughly
  **$700–$2,100** at on-demand H100 pricing. This is a rough extrapolation, not a
  measured number — actual RLVR cost at 1B could differ substantially since rollout
  generation cost doesn't always scale linearly with parameters (smaller models can
  need more RL steps/samples to reach comparable competence).
- **Budget implication:** a $23,000 on-demand-H100 AWS budget comfortably covers
  *multiple* full 1B recipe re-runs (base recipe + your modified-injection variant,
  with margin for failed runs/hyperparameter search), and plausibly **2–5 full 8B
  SFT+DPO+RLVR re-runs** at the rough estimates above — but given how uncertain the
  RLVR-stage compute figure is, I'd treat the 8B case as "likely feasible for a
  handful of runs" rather than a number to plan precisely against. It does **not**
  come close to covering a 70B-scale re-run (70B SFT alone was ≈3,200 GPU-hr per the
  paper-extraction reading in §1.5, i.e. ≈$22,000 at on-demand H100 pricing for SFT
  *alone*, before DPO/RLVR).

---

## 5. Instruct checkpoints as RLVR starting points — standard practice, confirmed

The pattern of taking an **already-instruction-tuned** checkpoint (not a raw base
model) and applying RLVR/GRPO-style RL directly on top of it — i.e., closer to
research question (a), "append a new skill's RL stage after full post-training" — is
well established in the academic RLVR literature. Directly confirmed examples:

1. **"Spurious Rewards: Rethinking Training Signals in RLVR"** (Shao et al., 2025,
   arXiv:2506.10947) — confirmed via full-text fetch to use **Llama-3.1-8B and
   Llama-3.1-8B-Instruct**, **Qwen2.5-7B** and **Qwen2.5-Math-7B**, **Llama3.2-3B and
   Llama3.2-3B-Instruct**, and **OLMo2-7B and OLMo2-7B-SFT** — i.e., it directly
   compares RLVR starting from base vs. already-instruction-tuned checkpoints across
   three model families, explicitly including Llama-3.1-8B-Instruct.
   https://arxiv.org/abs/2506.10947 (full text via
   https://ar5iv.labs.arxiv.org/html/2506.10947)
2. **"Reinforcement Learning for Reasoning in Large Language Models with One Training
   Example"** ("1-Shot RLVR", Wang et al., 2025, arXiv:2504.20571) — confirmed to use
   **Llama3.2-3B-Instruct** as one of its RLVR starting checkpoints (alongside
   Qwen2.5-Math-1.5B/7B and DeepSeek-R1-Distill-Qwen-1.5B), explicitly stating
   "substantial improvements are observed across various models (Qwen2.5-Math-7B,
   Llama3.2-3B-Instruct, DeepSeek-R1-Distill-Qwen-1.5B)."
   https://arxiv.org/abs/2504.20571
3. **Tülu 3 / open-instruct itself** — RLVR is applied as the *final* stage on top of
   an already SFT+DPO-tuned (i.e., already "instruct-level") checkpoint, not a raw
   base model (§1.1–1.4 above) — this is the origin of the term "RLVR" and is itself
   evidence that "RL on top of an already post-trained model" is the standard shape
   of this stage, even when the earlier SFT/DPO stages were also done in-house.

**Not independently confirmed:** I was not able to pin down, via full-text fetch, one
single canonical paper that names the *exact* checkpoint `Qwen2.5-7B-Instruct` (as
opposed to `Qwen2.5-7B` base or `Qwen2.5-Math-7B`) as an RLVR starting point, though
it is a very commonly seen checkpoint name in community GRPO/RLVR projects on Hugging
Face (e.g., `virtuoussy/Qwen2.5-7B-Instruct-RLVR`,
`amaydle/grpo-coder-qwen-2-5-7b-instruct`). Given the confirmed pattern above (the
same practice demonstrated with Llama-3.1-8B-Instruct and OLMo2-7B-SFT), I'm confident
the general claim ("academic/community RLVR work commonly starts from
instruction-tuned checkpoints, including Qwen2.5-*-Instruct models") is well
supported, but flag the single-example-with-that-exact-name gap for anyone who wants
a citation with that literal checkpoint string.

---

## NOT VERIFIED / FLAGGED — summary for quick reference

- **Tülu 3 SFT/DPO GPU-hour figures (§1.5):** two extraction passes over
  arXiv PDF vs. `open-instruct/docs/tulu3.md` gave inconsistent GPU counts for 8B SFT
  (32 vs 64 GPUs) and the RLVR-stage wall-clock was not recovered from either source.
  **Re-check the primary paper table directly before using these for budgeting.**
- **Tülu 3 RLVR algorithm label** (PPO vs. a named variant) — not confirmed from the
  text reached; needs a direct read of paper §6.
- **OLMo 2 and OLMo 3 post-training GPU-hours** — explicitly not published by Ai2 as
  of the sources checked (OLMo 3 tech report reportedly promises this in "a future
  version"; OLMo 2 model cards give none).
- **OLMo 3 pretraining GPU-hour figures (234k H100-hr for 7B, 1.05M for 32B)** — from
  a third-party blog relaying an Ai2 Discord answer, not the official tech report
  text itself; treat as semi-official.
- **AWS p4d.24xlarge $21.96/hr figure** — only one source (vantage.sh) checked; not
  independently cross-confirmed against a second pricing source.
- **My own 1B and 8B total GPU-hour/dollar estimates in §4.2** — explicitly
  extrapolated/assumption-based, not sourced figures. Treat as a sanity-check
  order-of-magnitude, not a number to commit a budget to.
- **SmolLM3, Marin, K2 "intermediate post-training checkpoint" claims** — each has a
  specific gap noted in §3 (SmolLM3: per-stage checkpoints unconfirmed as downloadable
  HF models vs. only W&B logs; Marin: no RLHF/DPO stage as of the checked post; K2:
  post-training-stage openness not confirmed from the HF card, needs the tech report).
- **A canonical paper using the exact checkpoint name `Qwen2.5-7B-Instruct` as an RLVR
  starting point** — not found via full-text fetch; only inferred from HF community
  model names and the closely-analogous confirmed cases in §5.
- **Dolci-*-DPO / Dolci-*-RLVR dataset row counts** — I confirmed the DPO/RLVR
  *checkpoints* exist (§2.3) but did not pull matching dataset-card example counts the
  way I did for the two SFT sets.

---

## Full URL list (all sources cited above)

- https://arxiv.org/abs/2411.15124 (Tülu 3 paper)
- https://arxiv.org/pdf/2411.15124
- https://allenai.org/blog/tulu-3-technical
- https://allenai.org/blog/tulu-3-405b
- https://github.com/allenai/open-instruct
- https://github.com/allenai/open-instruct/blob/main/docs/tulu3.md
- https://huggingface.co/collections/allenai/tulu-3-datasets-673b8df14442393f7213f372
- https://huggingface.co/datasets/allenai/tulu-3-sft-mixture
- https://allenai.org/blog/olmo2
- https://huggingface.co/collections/allenai/olmo-2-674117b93ab84e98afc72edc
- https://huggingface.co/allenai/OLMo-2-0425-1B
- https://huggingface.co/datasets/allenai/olmo-2-0425-1b-preference-mix
- https://allenai.org/blog/olmo3
- https://www.interconnects.ai/p/olmo-3-americas-truly-open-reasoning
- https://cameronrwolfe.substack.com/p/olmo-3
- https://huggingface.co/collections/allenai/olmo-3
- https://huggingface.co/allenai/Olmo-3-7B-Instruct
- https://huggingface.co/allenai/Olmo-3-7B-Instruct-SFT
- https://huggingface.co/allenai/Olmo-3-7B-RL-Zero-General
- https://huggingface.co/allenai/Olmo-3.1-7B-RL-Zero-Code
- https://huggingface.co/allenai/Olmo-3.1-32B-Think
- https://huggingface.co/datasets/allenai/Dolci-Instruct-SFT
- https://huggingface.co/datasets/allenai/Dolci-Think-SFT-32B
- https://huggingface.co/datasets/allenai/Dolci-Instruct-SFT-Tool-Use
- https://github.com/allenai/OLMo-core
- https://muxup.com/2025q4/minipost-olmo3-training-cost
- https://huggingface.co/blog/smollm3
- https://github.com/huggingface/smollm
- https://huggingface.co/HuggingFaceTB/SmolLM3-3B
- https://huggingface.co/HuggingFaceTB/SmolLM3-3B-Base
- https://marin.community/blog/2025/05/19/announcement/
- https://huggingface.co/marin-community/marin-8b-base
- https://huggingface.co/marin-community/marin-8b-instruct
- https://huggingface.co/LLM360/K2
- https://arxiv.org/html/2501.07124v3 (LLM360 K2 tech report)
- https://arxiv.org/html/2512.06201v1 (K2-V2)
- https://instances.vantage.sh/aws/ec2/p5.48xlarge
- https://instances.vantage.sh/aws/ec2/p4d.24xlarge
- https://www.thundercompute.com/blog/aws-p5-vs-thunder-compute
- https://aws.amazon.com/ec2/instance-types/p5/
- https://aws.amazon.com/ec2/capacityblocks/pricing
- https://arxiv.org/abs/2506.10947 (Spurious Rewards)
- https://ar5iv.labs.arxiv.org/html/2506.10947
- https://arxiv.org/abs/2504.20571 (1-Shot RLVR)
- https://huggingface.co/virtuoussy/Qwen2.5-7B-Instruct-RLVR
- https://huggingface.co/amaydle/grpo-coder-qwen-2-5-7b-instruct
