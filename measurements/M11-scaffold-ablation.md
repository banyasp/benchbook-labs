# M11 · Scaffold ablation: step guidance vs schema imposition, with and without a case

**Status: COMPLETE**, 2026-11-11.
- Luna guided and Luna free (k=8 each): 2026-11-10 21:30-21:45 UTC.
- Granite guided and Granite free (k=4 each): 2026-11-11 00:20-03:51 UTC, run by `scripts/scaffold_gpu_chain.sh`
  (log `logs/scaffold-gpu-chain.log`) after M09 reached k=4. 604 replies each, 0 errors.
- Views: `measurements/views/SCAFFOLD-ABLATION-luna-20261110.md`, `measurements/views/SCAFFOLD-ABLATION-granite-20261111.md`.

## What is measured
- **Question** (Peter, 2026-11-10). Where does the benefit come from: decomposing the reasoning into steps (guidance
  alone), or imposing the YAML schema on those steps? And does the answer differ with and without a case, and across
  the case arms?
- **Factor 1: scaffold.** All three scaffolds end with a structured verdict block, so the choice is scored the same
  way.

  | Scaffold | Step guidance | YAML schema on the steps | Case-reasoning method prompt (analogical.v1) | Format file |
  |---|---|---|---|---|
  | `schema` | yes (as YAML documents) | yes: 4 documents without a case, 7 with | yes, with a case | `format.v1.md`, `format.v1-noref.md` |
  | `guided` | yes: the same steps as numbered prose guidance, "no particular format" | no | yes, with a case | `format.v2guided.md`, `format.v2guided-noref.md` |
  | `free` | no: "decide what to do" | no | no | `format.v2free.md`, `format.v2free-noref.md` |

  The prompts are in `code/harness/prompts/`. guided and free use the mode line from `modes.v2.yaml` (A: "Think the
  decision through first. Then write your reply as described above.").
- **Verdict block** for guided and free: `kind: verdict`, `options` (every course weighed, the agent's own ids O1…, one
  sentence each), `choice` (an id), `course` (one sentence).
  - The options are listed at the end, after the reasoning, so they do not structure it.
  - The scorer reads them when there is no `fact_enumeration` (`code/scorers/rows.py`, `agent_options`).
- **Factor 2: policy.** Granite 4.2 8B and GPT-6 Luna.
- **Factor 3: thinking.**
  - Granite runs guided and free only in think-first mode: guided and free have no structure to put inside `<think>`.
  - Luna always reasons hidden.
  - The Granite schema runs exist in both modes (M07 YAML-in-think, M09 think-first), so the clean Granite contrasts
    are all at think-first.
- **Arms.** All five (no case, own case, transferred, flipped, other anchor's case) on pilot 2's 28 X1s: the same
  cells, traces and equities as M06, M07 and M09.
- **Samples per run.** 151 prompts (schedule items) × k. Breakdown from `measurements/datasets/pilot2.md`:

  | Arm | Prompts | X1s covered | Replies at k=4 (Granite) | Replies at k=8 (Luna) |
  |---|---|---|---|---|
  | no case | 28 | 28 | 112 | 224 |
  | own case | 28 | 28 | 112 | 224 |
  | transferred | 40 | 28 (some X1s have 2+ sisters) | 160 | 320 |
  | flipped | 27 | 20 (8 X1s have no accepted flip; some have 2) | 108 | 216 |
  | other anchor's case | 28 | 28 | 112 | 224 |
  | **total** | **151** | 28 | **604** | **1,208** |

  - Accuracy cells average each X1's replies within an arm first, then average across X1s, so an X1 with two
    transferred sisters is not counted twice.
  - Paired contrasts use 28 X1s per arm, or 20 on the flipped arm.

## How
- **Runs.** `eval.allpairs run --scaffold {guided|free} --mode A ...`. Each run directory is one condition, registered
  in `measurements/runs.yaml`.

  | Run | Policy | Scaffold | k | max_tokens |
  |---|---|---|---|---|
  | `results/transfer/pilot2-luna-guided` | Luna | guided | 8 | 16000 |
  | `results/transfer/pilot2-luna-free` | Luna | free | 8 | 16000 |
  | `results/transfer/pilot2-granite-guided` | Granite | guided | 4 | 20000 |
  | `results/transfer/pilot2-granite-free` | Granite | free | 4 | 20000 |

  Granite runs at k=4 because the GPU is the bottleneck; the inference unit is the X1 (28 of them), and Granite is
  nearly deterministic per X1. Compare Granite runs with `--max-idx 3`.
- **Smoke tests** (1 X1: no case, own case, flip; both models; both scaffolds) are in
  `/tmp/claude-1000/-home-ubuntu/4e83879d-8bf3-416b-b63a-9e4e4e93dd18/scratchpad/scaffold-smoke/`. All 6 Luna replies
  parsed and aligned. Granite: see below.
- **Scoring.** Unchanged (`allpairs-scoring-v3`). The Jev Choice judge (LLM) aligns the agent's own option list to X1's
  options, two passes plus greedy assignment, threshold 0.5. `choice` is translated through that alignment.
- **Analysis.** `code/eval/analysis/tensor.py`.
  - `build` writes the reply table `results/tensor/replies.parquet` from the registry.
  - `standard --max-idx 3 --out measurements/views/SCAFFOLD-ABLATION.md` writes the designed views:
    - accuracy, copy rate, off-menu and no-verdict by policy × scaffold × thinking × arm;
    - the guidance effect (guided − free) and the schema effect (schema − guided), paired per X1;
    - the case benefit within each scaffold (arm − no case).
  - It is deterministic.
- **Limits.**
  - Contamination, the declared relation and `via` exist only in the schema scaffold. guided and free have no
    structured considerations, so those metrics are NaN there. If they are needed, an LLM reader can extract them from
    the prose later; that would be a Claude-read or judge measurement and must be labelled as such.
  - max_tokens differs by policy (see `runs.yaml`).

## What was observed

### Luna: COMPLETE

All three scaffolds have 1,208 replies at k=8; the free and guided runs finished 2026-11-10 21:45 UTC.
- View: `measurements/views/SCAFFOLD-ABLATION-luna-20261110.md`, from
  `python -m eval.analysis.tensor standard --where policy=gpt-6-luna`.
- Accuracy against X1's key, per arm, with the copy rate on the case arms:

  | Scaffold | No case | Own case | Transferred | Flipped (copies) | Other anchor's case |
  |---|---|---|---|---|---|
  | free | 73% | 95% | 93% (copies 93%) | 70% (copies 11%) | 71% |
  | guided | 67% | 93% | 88% | 77% (copies 10%) | 72% |
  | schema | 66% | 91% | 86% | 76% (copies 14%) | 70% |

- **Guidance effect** (guided − free, paired per X1): no case −5 [−12, 0]; transferred −6 [−10, −2]; flipped +7
  [−5, +18]; other arms within ±2.
- **Schema effect** (schema − guided): −1 to −3 points on every arm. No interval excludes 0.
- **Case benefit is the same under every scaffold**: transferred − no case = +20 points for free, guided and schema;
  own case − no case = +22 to +25.
- **Verdict capture works without the schema.** The free scaffold had 0% no-verdict, versus 1-4% for the schema.
  Off-menu rates are similar (0-11%).

- **Confound (found 2026-11-11).** Luna's schema run (M06) used mode C from `modes.v1.yaml` ("Your thinking is the
  structure. Write the YAML documents inside your thinking … then write the verdict document as your reply"), followed by
  the API start instruction `API_START` in `code/eval/allpairs.py` ("Your reply is the written decision record in the YAML
  documents … your private chain of thought … stays hidden. Begin your reply with `kind: fact_enumeration`"). The two
  conflict; Luna followed the second and wrote every document in its visible reply after hidden reasoning (raw replies
  in `results/transfer/pilot2-luna/raw/`). Luna guided and free used mode A from `modes.v2.yaml` plus `API_START_PROSE`.
  So Luna's schema − guided contrast also differs in the mode line, not only the scaffold.

### Luna, clean schema re-run (2026-11-11): COMPLETE

`results/transfer/pilot2-luna-schemaA`: the schema scaffold with the v2 mode-A line and `API_START` (no conflicting
mode-C line), launched 16:22 UTC, finished 16:58 UTC, 1,208 replies, 0 errors. Command:
`eval.allpairs run --run results/transfer/pilot2-luna-schemaA --cells results/transfer/pilot2-luna-schemaA/cells.json
--model luna --mode A --scaffold schema --modes-version v2 -k 8 --max-tokens 16000 --concurrency 24`. Now schema,
guided and free differ only in the format file. View: `measurements/views/SCAFFOLD-ABLATION-luna-v2A-20261111.md`
(`tensor standard --where policy=gpt-6-luna mode_line=v2.A`). Cost: about $2-3 of Bedrock (estimate).

| Scaffold (all v2 mode A) | No case | Own case | Transferred | Flipped (copies) | Other anchor's case |
|---|---|---|---|---|---|
| free | 73% | 95% | 93% | 70% (11%) | 71% |
| guided | 67% | 93% | 88% | 77% (10%) | 72% |
| schema (clean re-run) | 71% | 94% | 88% | 80% (11%) | 75% |

- **Schema effect, clean** (schema − guided): +1 to +4 points on every arm; no interval excludes 0. No-verdict 0%.
- **The contradictory prompt cost the old run** (same scaffold, mode line v2.A − v1.C, paired): no case +5 [0, +10];
  own case +3 [0, +7]; transferred +2 [−2, +7]; flipped +5 [−2, +12]; other anchor's case +6 [−1, +12].
- **Reading.** For Luna the scaffold does not matter: free, guided and schema are within a few points, and the
  earlier "schema costs 1-3 points" was the conflicting instruction, not the schema. The M06 numbers understate Luna by
  2-6 points.

**Reading (Luna).**
- Scaffolding buys a frontier model nothing. It reasons as well, or slightly better, when told only "decide", and the
  structure costs a few points on the no-case and transferred arms.
- The benefit of a case comes from the case itself, not from the steps.
- The one place the steps may help is the flipped case (+7 for guided over free, not significant). That is where
  checking the case's flip conditions should matter.

### Granite: COMPLETE (k=4)

All four Granite conditions have 604 replies at sample index 0-3: guided, free, schema think-first (M09's first four
passes) and schema YAML-in-think (M07).
- View: `measurements/views/SCAFFOLD-ABLATION-granite-20261111.md`, from
  `python -m eval.analysis.tensor standard --where policy=granite-4.2-8b --max-idx 3` (tensor rebuilt 2026-11-11 ~04:00
  UTC; M09 had 629 rows then, and `--max-idx 3` keeps its first 604).
- Accuracy against X1's key, per arm, with the copy rate on the case arms:

  | Scaffold (thinking) | No case | Own case | Transferred | Flipped (copies) | Other anchor's case |
  |---|---|---|---|---|---|
  | free (think first) | 50% | 95% | 81% (copies 81%) | 28% (copies 49%) | 50% |
  | guided (think first) | 53% | 96% | 82% | 29% (copies 48%) | 47% |
  | schema (think first, M09) | 45% | 88% | 76% | 31% (copies 48%) | 48% |
  | schema (YAML in think, M07) | 46% | 83% | 72% | 19% (copies 57%) | 43% |

- **Guidance effect** (guided − free, paired per X1): every arm within ±3 points; own case +2 [0, +4]. No interval
  excludes 0 except that one, at its edge.
- **Schema effect** (schema − guided, both think first): no case −8 [−16, +1]; own case −9 [−17, −3]; transferred
  −6 [−14, +2]; flipped +2 [−6, +10]; other anchor's case +1 [−9, +11].
- **Case benefit is the same under every scaffold**: transferred − no case = +29 to +31 at think first (+27 YAML in
  think); own case − no case = +43 to +45 (+38).
- **Flipped case hurts under every scaffold**: flip − no case = −21 (free), −22 (guided), −11 (schema think first),
  −24 (YAML in think). Granite copies the flipped sister's verdict about 48% of the time whatever the scaffold.
- **No-verdict and off-menu.** free 0% no-verdict, guided 0-3%, schema 2-10%. Off-menu 0-13% for all, with no pattern
  by scaffold.
- **Cost** (median completion tokens, including thinking): free 2,345; guided 4,565; schema think first 7,496;
  YAML in think 6,654. Truncation: 0% for guided and free, 0.2% schema think first, 7.8% YAML in think.
- **Confound.** The schema think-first run used mode line v1.A ("…then write the YAML documents as your reply");
  guided and free use v2.A ("…then write your reply as described above"). The two lines say the same thing for their
  formats, but the schema effect is not a single-factor contrast.

**Reading (Granite).**
- The same answer as Luna, more strongly. Step guidance adds nothing over "decide" (±3), and imposing the YAML schema
  costs 6-9 points on no case, own case and transferred. Free costs a third of the schema's tokens.
- The benefit of a case comes from the case, not from the steps: +30 for a transferred sister under every scaffold.
- **The flip weakness is the model's, not the format's.** Luna gained +7 on the flip arm from guidance; Granite gains
  +1, and copies the flipped verdict half the time under every scaffold. Prompted steps do not teach a small model to
  check a case's flip conditions. That is the gap SFT and RL are meant to close, and the reason for a flip arm in
  training.
- Implication for the base-model baseline: the YAML scaffold understates base Granite by 6-9 points on choice
  accuracy. Base numbers reported with the schema scaffold should say so, or be paired with the free-scaffold number.


## Size-class comparison: four more local models (PARTIAL, started 2026-11-12)

Peter, 2026-11-12: is Granite's schema cost common to models of its size class? Same data (pilot 2: 28 X1s, 151
prompts), same three scaffolds, k=4, thinking first. Status: **running** (`logs/scaffold-compare-chain.log`).

| Key | Model (HF) | Sampling (model card, thinking mode) |
|---|---|---|
| qwen35 | Qwen/Qwen3.5-9B | T 1.0, top_p 0.95, top_k 20, presence 1.5 |
| olmo3 | allenai/Olmo-3-7B-Think | T 0.6, top_p 0.95 |
| gemma4 | google/gemma-4-12B-it | T 1.0, top_p 0.95, top_k 64 |
| ministral3 | mistralai/Ministral-3-14B-Reasoning-2512 | T 1.0, top_p 0.95 |

- Runs: `results/transfer/pilot2-<key>-{schemaA,guided,free}` (registered in `runs.yaml`).
- Command: `scripts/scaffold_compare_chain.sh` → per model `code/inference/serve_compare.sh <key>` (vLLM 0.27.1, bf16,
  max-model-len 49152, the model's own reasoning parser), then
  `eval.allpairs run --model <key> --mode A --scaffold <s> [--modes-version v2 for schema] -k 4 --max-tokens 20000`.
- **Differences from Granite's runs (record when comparing):**
  - Granite runs through the raw-completions harness with a prefilled `<think>`; these four run through the chat
    endpoint (like Luna) with the API_START / API_START_PROSE instruction appended, and the model's own template
    turns thinking on. Their thinking is saved in the raw reply as `<think>…</think>`.
  - Schema uses the v2 mode-A line (as Luna's clean re-run); Granite's schema row (M09) used v1.
- **Smoke test (Qwen, 3 schema no-case items):** 2 of 3 replies omitted the `options` list from `fact_enumeration`,
  so the bare choice id could not be matched (scored wrong). Granite and Luna lose 4-6% of choices this way under
  every scaffold (measured 2026-11-12 on the M11 runs). Check this rate per model before reading the schema rows; a
  course-text fallback in the scorer would be a scoring change applied to all runs (not done).
- LLMs: the four policies above (local); judge Jev Choice (OpenRouter) as in M11.
