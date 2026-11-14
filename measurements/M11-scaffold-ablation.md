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


## Size-class comparison: four more local models (COMPLETE, 2026-11-12 to 2026-11-14)

Peter, 2026-11-12: is Granite's schema cost common to models of its size class? Same data (pilot 2: 28 X1s, 151
prompts), same three scaffolds, k=4, thinking first. Status: **Qwen, Olmo, Ministral COMPLETE (2026-11-13); Gemma 4
COMPLETE (2026-11-14 01:02-06:05Z)** (vLLM 0.27.1 could not load it; served from `.venv-gemma4` with vLLM 0.33.0, after
the SFT training).

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

### Results (2026-11-13; Gemma 4 added 2026-11-14)

Accuracy against X1's key, per arm (X1-averaged, idx 0-3). "As scored" counts an unreadable reply as wrong;
"readable" keeps only replies with a verdict whose choice maps to an option (selection-biased: unreadable replies
may be the harder items; read it as an indication, not an estimate). Granite's schema row is M09 (mode line v1.A,
first four samples).

| Model | Scaffold | No case | Own case | Transferred | Flipped (copies) | Other anchor | Readable | Readable only: no case / own / transf / flip / other |
|---|---|---|---|---|---|---|---|---|
| Granite 4.2 8B | free | 50 | 95 | 81 | 28 (49%) | 50 | 95% | 55 / 96 / 82 / 29 / 54 |
| | guided | 53 | 96 | 82 | 29 (48%) | 47 | 94% | 57 / 96 / 86 / 30 / 59 |
| | schema | 45 | 88 | 76 | 31 (48%) | 48 | 88% | 53 / 96 / 86 / 32 / 57 |
| Qwen3.5 9B | free | 50 | 93 | 88 | 33 (36%) | 55 | 92% | 59 / 96 / 91 / 37 / 65 |
| | guided | 59 | 89 | 91 | 54 (24%) | 59 | 90% | 70 / 95 / 95 / 60 / 70 |
| | schema | 29 | 40 | 45 | 23 (23%) | 33 | **48%** | 63 / 93 / 94 / 49 / 62 |
| Olmo 3 7B Think | free | 59 | 82 | 78 | 16 (69%) | 39 | 83% | 65 / 96 / 92 / 20 / 59 |
| | guided | 54 | 92 | 91 | 21 (69%) | 50 | 91% | 60 / 96 / 96 / 24 / 60 |
| | schema | 8 | 38 | 34 | 5 (42%) | 21 | **37%** | 55 / 94 / 88 / 11 / 51 |
| Ministral 3 14B | free | 37 | 81 | 78 | 26 (50%) | 46 | 80% | 56 / 96 / 89 / 28 / 66 |
| | guided | 45 | 79 | 64 | 30 (31%) | 32 | 71% | 62 / 95 / 85 / 39 / 57 |
| | schema | 54 | 80 | 73 | 23 (49%) | 41 | 77% | 64 / 93 / 96 / 30 / 65 |
| Gemma 4 12B | free | 63 | 98 | 91 | 42 (35%) | 60 | 95% | 69 / 98 / 93 / 44 / 65 |
| | guided | 60 | 97 | 92 | 61 (22%) | 60 | 95% | 65 / 98 / 94 / 61 / 64 |
| | schema | 59 | 96 | 91 | 55 (29%) | 62 | 96% | 62 / 97 / 93 / 56 / 63 |
| GPT-6 Luna (k=8) | free / guided / schema | 73 / 67 / 71 | 95 / 93 / 94 | 93 / 88 / 88 | 70 / 77 / 80 (10-11%) | 71 / 72 / 75 | 95-96% | — |

Unreadable replies, by cause (Claude-checked from `samples.jsonl` and raw replies):
- **Qwen and Olmo, schema:** off-menu in 47% / 49% of replies. They give a choice id (LIVE-O1…) but leave the
  `options` list out of `fact_enumeration` (options found = 0 in ~95% of their off-menu replies), so the id cannot be
  mapped and is scored wrong. The smoke-test problem, at scale. Olmo also has no verdict in 14%.
- **Ministral, every scaffold:** no verdict in 14% (free), 23% (guided), 19% (schema). It often writes the verdict
  as Markdown (`**choice:** O2`, `**course:** …`) instead of the YAML block.

Gemma 4 diagnostics: off-menu 4.5% / 4.6% / 3.8% (free / guided / schema), no verdict ≤0.3%, truncated ≤0.2%;
median completion 1,774 / 2,751 / 4,352 tokens with 6.3k / 8.8k / 10.0k characters of thinking. Source: tensor
rebuilt 2026-11-14 06:10Z (`results/tensor/replies.parquet`, 15,704 rows), numbers from `console.results.summary()`
(the `/results` page; same X1-averaged method). Intervals for Gemma (95% family bootstrap, as scored): no case
63 [49, 78] / 60 [46, 75] / 59 [45, 74]; own 98 [94, 100] / 97 [94, 100] / 96 [88, 100]; transferred 91 [80, 98] /
92 [81, 98] / 91 [81, 98]; flipped 42 [26, 58] / 61 [44, 78] / 55 [34, 72]; other anchor 60 [46, 73] / 60 [44, 76] /
62 [50, 76].

**Unrelated case: agreement with the model's own no-case choice** (Peter, 2026-11-13: the unrelated arm is read as
"does the case move the model?", not against the key). For each readable reply, the share of the same model's
readable no-case replies on that X1 (same scaffold) that chose the same option; X1-averaged, 95% family bootstrap.
The no-case row is the baseline: the same measure for a no-case reply against the model's other no-case replies
(leave-one-out), i.e. the model's own sampling consistency.

| Model | Scaffold | No case vs no case (baseline) | Unrelated case vs no case | Difference |
|---|---|---|---|---|
| Granite 4.2 8B | free | 87 [79, 95] | 86 [79, 93] | −1 |
| | guided | 83 [74, 92] | 83 [73, 91] | 0 |
| | schema (M09) | 77 [67, 85] | 78 [70, 87] | +1 |
| Qwen3.5 9B | free | 80 [66, 92] | 82 [73, 91] | +2 |
| | guided | 89 [80, 97] | 89 [82, 95] | 0 |
| | schema | 80 [60, 97] | 77 [65, 88] | −3 |
| Olmo 3 7B Think | free | 72 [61, 83] | 71 [58, 83] | −1 |
| | guided | 68 [57, 81] | 61 [50, 71] | −7 |
| | schema | 100 [100, 100] (15% readable) | 68 [45, 90] | n/a |
| Ministral 3 14B | free | 65 [49, 80] | 69 [58, 80] | +4 |
| | guided | 68 [52, 83] | 63 [51, 76] | −5 |
| | schema | 73 [60, 85] | 73 [61, 84] | 0 |
| Gemma 4 12B | free | 90 [81, 96] | 84 [76, 92] | −6 |
| | guided | 86 [77, 95] | 85 [77, 92] | −1 |
| | schema | 84 [72, 94] | 82 [73, 91] | −2 |
| GPT-6 Luna (k=8) | free | 96 [93, 99] | 90 [83, 97] | −6 |
| | guided | 86 [78, 94] | 86 [78, 94] | 0 |
| | schema | 89 [82, 97] | 89 [80, 96] | 0 |

- An unrelated case moves no model beyond its own sampling noise: every difference is inside the intervals (O28).
  Olmo schema's baseline rests on the 15% of no-case replies that are readable and is not interpretable.

**Relation labels (schema scaffold only; free and guided replies have no relation field).** Share of replies with a
verdict whose relation is the one the arm expects (own and transferred: follows; flipped: flips; unrelated:
not_governed). X1-averaged, 95% family bootstrap. Console metric "Relation label correct" (added 2026-11-14).

| Model | Own case (follows) | Transferred (follows) | Flipped (flips) | Unrelated (not_governed) |
|---|---|---|---|---|
| Granite 4.2 8B (M09) | 96 [88, 100] | 92 [84, 98] | 9 [3, 16] | 8 [5, 12] |
| Qwen3.5 9B | 96 [88, 100] | 93 [85, 99] | 33 [22, 44] | 21 [13, 29] |
| Olmo 3 7B Think | 96 [88, 100] | 92 [84, 99] | 13 [5, 23] | 0 [0, 0] |
| Ministral 3 14B | 82 [72, 91] | 82 [73, 90] | 7 [0, 16] | 27 [17, 40] |
| Gemma 4 12B | 97 [91, 100] | 94 [84, 100] | 50 [33, 67] | 37 [24, 49] |
| GPT-6 Luna | 96 [89, 100] | 89 [79, 97] | 55 [39, 71] | 100 [100, 100] |

- **Small models do not say an unrelated case is irrelevant, yet it does not move their choice.** On the unrelated arm
  Granite labels 105 of 224 replies `follows`, 84 `distinguished`, 17 `not_governed` (18 no verdict); Olmo never says
  `not_governed` (78 follows, 15 distinguished, 6 flips). Luna says `not_governed` in 223 of 224. The agreement table
  above shows the choices stay at the no-case level all the same, so the label is wrong while the decision is not:
  the small models file an unrelated case as "followed" or "distinguished" and then decide on the live facts.
  (`distinguished` is the natural fallback label for them; relevant to the distinguished-arm design.)
- Flipped: Gemma (50) and Luna (55) label about half their flip replies `flips`; Granite, Olmo and Ministral 7-13.

**Reading (size class, Claude; written 2026-11-13, Gemma 4 added 2026-11-14).**
- **Gemma 4 12B is the strongest small model and the only one that resists the flip.** Flipped accuracy as scored
  42 (free), 61 (guided), 55 (schema), copying the flipped sister's verdict in 35%, 22% and 29% of replies; Granite
  scores 28 / 29 / 31 with copy rates 49% / 48% / 49%. Gemma guided's flip score (61 [44, 78]) is 16 points below
  Luna guided (77) and 32 above Granite guided (29). Own case 98 / 97 / 96 and transferred 91 / 92 / 91 match Luna
  (95 / 93 / 94 and 93 / 88 / 88). No case 63 / 60 / 59, against Granite's 50 / 53 / 45 and Luna's 73 / 67 / 71.
- **Gemma has no schema cost at all:** 96% of its schema replies are readable (free 95%, guided 95%), and its schema
  scores are within 1 point of free on own and transferred. Like Qwen, guidance helps its flip score (+19 over free).
- **The case benefit is universal.** Own case reaches 93-96% (readable) for every model under every scaffold, from
  50-70% with no case. A transferred sister gives +20 to +38 points.
- **The flip weakness is shared by the small models.** Flipped accuracy 11-39% (readable), against Luna's 70-80%. The
  small models copy the flipped sister's verdict 23-69% of the time (Olmo worst, 69%), against Luna's 10-11%. One
  exception: Qwen guided reaches 54% (60% readable), +21 over Qwen free, like Luna's +7 from guidance. Worth a look.
- **"Schema cost" is mostly a format-compliance cost, not a reasoning cost.** As scored, the schema is catastrophic
  for Qwen and Olmo (−20 to −55 points) because half their replies cannot be mapped. On readable replies the schema
  is within a few points of guided for every small model, Granite included (its 6-9 point cost as scored comes with
  readability falling from 94% to 88%). This revises the Granite reading above: the schema costs points mainly by
  making replies unscorable.
- **Guidance vs free: no consistent effect.** Qwen gains (no case +9, flip +21), Olmo gains on own/transferred
  (+10/+13, but its free run truncates and goes off-menu more), Ministral loses (its no-verdict rate rises).
- Caveats: 28 X1s, k=4; intervals about ±10-15 points; readable-only is selection-biased; the four comparison models
  run through the chat endpoint, Granite through raw completions.
