# M11 · Scaffold ablation: step guidance vs schema imposition, with and without a case

**Status: PARTIAL**, launched 2026-11-10.
- Luna guided and Luna free (k=8 each) started 21:30 UTC.
- Granite guided and Granite free (k=4 each) are queued behind the think-first run (M09) by
  `scripts/scaffold_gpu_chain.sh`, whose log is `logs/scaffold-gpu-chain.log`.
- Views are regenerated from the tensor as runs fill in.

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

**Reading (Luna).**
- Scaffolding buys a frontier model nothing. It reasons as well, or slightly better, when told only "decide", and the
  structure costs a few points on the no-case and transferred arms.
- The benefit of a case comes from the case itself, not from the steps.
- The one place the steps may help is the flipped case (+7 for guided over free, not significant). That is where
  checking the case's flip conditions should matter.

### Granite: PENDING

Queued behind M09's k=4 (`logs/scaffold-gpu-chain.log`).
