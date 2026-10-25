# Benchbook datagen pipeline (spec v2.6)

Python 3.10, stdlib plus `pyyaml`. `boto3` and `requests` are optional and imported only when used (urllib is the fallback for
`requests`). The validator `mvp.py` is the authority: it is imported from a path and never copied or modified.

| File | What it does |
|---|---|
| `check_batch.py` | The acceptance runner: wraps `mvp.py` and adds the batch-level checks. Most important piece. |
| `llm.py` | Model backends (`openrouter/`, `bedrock/`, `dry/`), the training-bound allowlist, the critic-family rule, `provenance.jsonl`. |
| `run_stage.py` | One drafting stage on a seed: fill the prompt, call the model, extract the block, check, repair at most twice, install. |
| `prompts/*.md` | The six stage prompts (`reference`, `revised`, `live`, `render`, `reply`, `critic`) and the shared rule blocks `_balance_rules.md`, `_rendering_rules.md`, `_scope_rules.md` (copied from BRIEF-B001). |
| `models.yaml` | Allowlisted families, refused patterns, per-stage settings (`training_bound`, spec sections, templates), worked-example paths. |
| `seeds/INT-301.seed.yaml` | An example seed (Family 1 of B001). |
| `selftest.py` | Offline tests: `python3 selftest.py`. Run it after any change. |

## Environment

| Variable | Used for |
|---|---|
| `BENCHBOOK_MVP` | Path to `mvp.py` (or pass `--mvp`). Default: `$BENCHBOOK_LABS/ideas/schema-mvp-2026-09-30/code/mvp.py`. |
| `BENCHBOOK_LABS` | Root of `benchbook-labs` (templates, examples, validator). Default: the repo `code/datagen/` sits in, else `/home/claude/bb/benchbook-labs`, else `~/Desktop/AI/benchbook-labs`. |
| `OPENROUTER_API_KEY` | `openrouter/<id>` models. Requests carry `provider: {data_collection: "deny"}`. |
| `BENCHBOOK_AWS_REGION`, `BENCHBOOK_AWS_PROFILE` | `bedrock/<modelId>` models. Both are required. Credentials come from that named profile only; the default credential chain is never used (this container's default AWS credentials are the sandbox's, not Peter's). A profile that resolves to env, instance or container credentials is refused. |
| `BENCHBOOK_PROVENANCE` | Default `provenance.jsonl` path for `llm.complete` when no path is passed (`run_stage.py` writes `DIR/provenance.jsonl`). |

## Acceptance: `check_batch.py`

```
python3 check_batch.py BATCH_DIR [--cumulative DIR ...] [--mvp PATH] [--out REPORT.md]
```

`BATCH_DIR` holds case folders (`INT-301/`, ...). Per folder it validates every `*.reference.yaml` and `*.live.yaml`; requires a trace
for each live (words 500-1200 and fact_share 0.10-0.25 are errors, plus a leak scan); scores the reply for the right card, for every
listed revised card (`<LIVE>.r1.reply.json`) and for `decoys[0]` (`<LIVE>.decoy.reply.json`); and checks revised cards (every reference
has an `-rN` card with an identical scenario and a different choice, and every `-rN` is listed on a live). A served card missing from
the folder is an error, because `mvp.py` would silently skip the flip, trap, planted and `option_map` checks.
Batch-level (and again with the `--cumulative` dirs, where floors only warn): `mvp floors` flags, gold-letter spread, hand-up gold
share, irreversible gold share, gold-is-longest share, variant mix, `PROPOSED LABEL` on novel and cross scenarios, and the option-length
table. The report is Markdown with the summary table first; `--out X.md` also writes `X.json`. Exit 1 on any error.
Only the files of a case folder are checked; `versions/` and `scratch/` are skipped. Run it before and after every merge of a family.

`--training` marks a batch bound for training. It adds two errors per offending file: a reference card whose `status` is not `signed_off` (only Peter signs off), and any card or live spec whose `provenance.drafted_by` names Claude, Anthropic or a closed GPT model (spec section 10). The batch report also lists two shortcut checks from the training handoff: `follows_share`, the share of lives a copy-the-card policy would get right (a warning above 60%), and `floor_most_specific_signature`, the score of a policy that picks the option with the most specific tool-call signature (an error above chance + 0.10).

## Drafting: `run_stage.py`

```
python3 run_stage.py STAGE --seed SEED.yaml --out DIR --model M [--judge M2] [--live ID] [--arm ARM] [--revised TAG]
```

Stage order, each reading what the earlier ones wrote under `DIR/<CASE>/`:

1. `reference`: seed to `<CASE>.reference.yaml`.
2. `revised`: reference to `<CASE>-r1.reference.yaml` (same scenario, different weighing; caveated as illustrative).
3. `live`: reference to `<LIVE>.live.yaml` for each live in the seed (options, signatures, `render`, gold).
4. `render`: live spec to `<LIVE>.trace.json`, and `<LIVE>.trace.md`.
5. `reply`: gold replies for each arm the live spec lists (`<LIVE>.reply.json`, `.r1.reply.json`, `.decoy.reply.json`). Add the decoy card to the folder and to the live spec's `decoys` first.
6. `critic`: `<LIVE>.critic.md`, a pass/fail checklist read by Peter. `--judge` is the reviewing model; `--model` (or the drafters recorded in `DIR/provenance.jsonl`) names the drafter, and a judge from the same family or lab lineage is refused.

Each stage fills its prompt (`{SPEC}` verbatim spec sections, `{TEMPLATES}`, `{EXAMPLE_*}`, `{SEED}`, `{ASSIGNMENT}`, `{REFERENCE}`, `{LIVE}`,
`{TRACE}`, `{CARD}`, and `{MODEL}`, the rule blocks), asks the model, takes the one fenced block, writes it, and runs the matching check:
`mvp.py validate` plus the balance rules and the seed's longest/shortest roles for cards and live specs; `check_trace` plus words, fact share,
leak scan and the exact harness message for traces; `reply-score` against the arm's expectations for replies. On errors it re-prompts with the
error list, at most two repairs. A file that never passes is saved as `<name>.rejected` (errors in `<name>.rejected.errors.txt`) and not
installed. A file it replaces moves to `<CASE>/versions/`. Exit 0 on success, 1 if a file was rejected, 2 on a configuration problem.

A seed has `case`, `title_hint`, `source` (the real source and notes), `assignment` (agent, decider, options with `move`/`to`/`irreversible`,
`choice`, `basis`, `longest`, `shortest`, `would_change`, `would_not_change`, `revised_cards`, `decoy`) and `lives` (id, variant, boundary,
revised tags). See `seeds/INT-301.seed.yaml`.

**Dry run.** `--model dry/anything` calls nothing: it writes every filled prompt to `DIR/_dry/` and a placeholder `<name>.dry`, so you can read
the prompts and confirm every slot resolves. The placeholder is never installed under the real name.

**Models.** `openrouter/<id>` and `bedrock/<modelId>`. Every call appends `{model, family, time, prompt hash, stage, output path, attempt}` to
`provenance.jsonl`. Try a model id with `python3 llm.py MODEL --training-bound [--prompt TEXT]`.

## Training-bound versus evaluation-only

Plan v2 authorship rule (spec section 10): training-bound text and labels come from open-weight models, real documents, the solver or Peter.

- **Training-bound** (`training_bound: true` in `models.yaml`): `reference`, `revised`, `live`, `render`, `reply`. Only the allowlisted families
  (gpt-oss, gemma-4, mistral, olmo) may draft them; `anthropic/*`, `claude*` and closed `openai/gpt-*` are refused, as is anything else.
- **Evaluation-only**: `critic` output (a review for Peter, never data; any model of a different family may write it), and anything Claude
  drafts by hand, such as the 13 MVP examples and the B001 families. Those are prototype and evaluation material under the plan v2 rule.

`status` stays `draft` in every file; only Peter signs off.
