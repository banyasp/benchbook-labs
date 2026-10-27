# Build brief — design v2.4.1: rebuild, scale to 150+ pairs, train and eval (2026-10-27/28)

*Work order for the EC2 session, from Peter's claude.ai session after his full walkthrough of the pipeline.
v2 of this brief: amended after an independent cold review (`docs/reviews-design-v2.4-2026-10-27.md`). v1 is in
`versions/`.*

**Read first, in order:**
1. `CLAUDE.md`
2. `context/DATA-PIPELINE-DESIGN-v2.md` (**v2.4.1**, the design; section numbers below refer to it)
3. this brief
4. `docs/HYPOTHESES.md`
5. `docs/RISK-REGISTER.md`

**Precedence.** This brief supersedes `BUILD-BRIEF-2f-2026-10-25.md` (kept). Where the two differ, this brief wins. Where
this brief and the design differ, the design wins, and you tell Peter.

## Goal and definition of done (Peter: "150+ pairs, training and eval tomorrow; parallelize")

**Training data**
- ≥ 150 **train** items with an SFT target (accepted, or rationalized and tagged).
- **Per-arm floors:** relevant ≥ 60 (including ≥ 10 reverse-restyle), augmented ≥ 20, revised ≥ 20.
- Decoys ≤ 20% of train items. They are the cheapest to accept, so they must not fill the quota.

**Eval set**
- Built only from `test` and `eval-only` scenarios (design §13.5).
- Two parts: in-domain test (≥ 30 items) and **one whole held-out source domain** (≥ 15 items). The pilot imports are a
  third, separately reported set.

**Training and eval runs**
- One LoRA SFT run on Granite 4.2 8B.
- Evaluate base and SFT on the core grid (below).

**Reports**
- `results/RESULTS-2026-10-28.md`, with:
  - the headline graph: four curves, design §13.2;
  - the by-arm graph;
  - the breakdowns and baselines of design §13.3.
- In parallel: `results/H3-PILOT-2026-10-28.md`.

**Out of scope for tomorrow:** RLVR. Start it only if everything above is done.

## What exists vs what v2.4.1 asks (from a survey of the code at b695b0a)

| Area | Today | v2.4.1 |
|---|---|---|
| SFT writer (`code/pipeline/solve/`) | gpt-oss **teacher that sees full gold**, N=3 | **Granite rejection sampling, no gold, N = 8 adaptive (4+4), mode C**; the teacher is kept as `writer: teacher` |
| Splits (`ingest/registry.py` `SPLIT_RULE` l.53–62) | 1 family to test, 1 to dev, rest to train; no held-out domain; episodes of one document can split | per-document families; ~20/10/70 per domain (≥ 5 test families); one domain held out whole (§13.5) |
| Arms (`bench/schema/pipeline.py` `PairRecord`) | no `arm`; `project` hard-codes `relevant`; pair id = hash(C, T, intent) | `arm`, `card_view`; id = hash(C, T, intent, arm, card_view) |
| Traces (`render/render.py`) | stored per pair; `balance_positions` writes reordered T copies | **trace store** `data/store/traces/<trace-scenario-id>/` (trace, σ, channels, `recommended_option`); no reordered copies |
| Augmented / revised | schema literal only; in Checkpoint 2 code "augmented" = revised card | augmented = reversed flip pairs (flips only); revised = new `revise_card`; rename Checkpoint 2's `augmented` → `revised` |
| Balance (`pair/build.py` l.40, l.108–126) | hand-up and position read **T's own verdict**; per intent | from **`PairRecord.choice`**; hand-up cap per arm; position = first mention in τ + card order |
| Decoys (`pair/build.py` `decoy_records`) | different family, preferably different domain; `equity_jaccard` computed but unused | equity Jaccard ≤ 0.2, no shared decisive equity; ≤ 3 uses per card; domain alone never makes a decoy |
| Served card (`bench/schema/case.py` `ServedCase.build`) | serves `move` / `irreversible` / `to:`; no thin view | strip all three; `card_view: thin` only on non-flip pairs, with flip-condition references removed from the prose |
| Render (`render.v2.md`) | options made "reachable" by **tools** | options are text, discoverable, never a menu; channels per trace; R49 rule |
| SFT export (`project.py` l.72, `training/sft_data.py`) | mode B default; loss on the whole target | mode C; decoy loss masked after `applicability`; no worked examples or hints in SFT prompts |
| SFT eval serving (`inference/serve.sh`) | no LoRA path | `--enable-lora --lora-modules sft=<dir>` (or a merged checkpoint); stop vLLM before `sft_lora.py` |
| Refusals; incomplete; episodes | generic retry; dropped; hand-picked | record refusals; incomplete store; pass/fail episode finder (cut first if time is short) |
| Tests | not runnable in a fresh checkout | box venv: `PYTHONPATH=code <venv>/bin/python -m pytest -q code` (**all of `code/`**, since `ServedCase` is used everywhere) |

## Step 0 — the contract first (≈ 1 hour, before anything else)

**W2a** lands the schema and the store layout. W1, W5 and W6 build against it.
- **`PairRecord` gains:** `arm`, `card_view`, `recommended_option`, `d`, `writer`, `trace_ref`. Old records load with
  `arm: relevant`, `card_view: full`.
- **The pair id includes** arm and card_view.
- **New store:** `data/store/traces/<trace-scenario-id>/`.
- **`ServedCase`:** `card_view`, plus stripping `move` / `irreversible` / `to:`.

Then re-split (W4a) **before** any new perturbation. Commit and push the contract, then launch the other workstreams.

## Parallel workstreams (one Sonnet subagent each; you integrate; tests with fakes, no live calls)

### W1 — SFT writer (design §10)
Package: `code/pipeline/solve/`.

**New `rs.py`.** Build the sampling prompt as:
- the harness prompt for the item's arm, card view and AR setting;
- two worked examples:
  - the PDF journalist/raft example (pp. 14–18);
  - `ideas/benchbook-analogical-pipeline-example-v6.yaml`, converted to PDF names (no `confidence`; add `via`).
- **No gold anywhere in the prompt.**

Sampling: mode C. N = 4 per item, then 4 more only for items with no accepted sample. `n` per vLLM request,
`max_tokens` 8000, `--enable-prefix-caching`.

**Filter `check_rs`.** Run it cheapest first (design §10 step 2):
1. Align options (Jev Choice).
2. Exact checks: choice, relation, `via`, `governs`. Translate served ids through `ServedCase.table` first.
3. **Only for survivors:** align facts and considerations, then:
   - fact bucket agreement over **all** gold items ≥ 0.7;
   - weighted fact recall ≥ 0.6;
   - decisive items right;
   - consideration buckets ≥ 0.7, **skipped for `model-solved` pairs**.

Decoys: check `governs` and relation only. Log every sub-score.

**Rationalize.** For items with no accepted sample, run one pass with a hint: gold choice, relation and `via` (served
ids). Tag the results `rationalized`.

**Teacher.** Keep the existing teacher path as `--writer teacher`.

**Logging.** Write acceptance per arm / intent / family / tier / card view to `data/store/solve.acceptance.json`.

### W2 — Arms, pair, gold, distance (design §7, §9)
Files: `pipeline/pair/`, `solve/structure.py`.

**relevant.** Derived pairs as built, plus **reverse_restyle**:
- card = restyle(X);
- trace = X's trace;
- gold = X's answer; relation `follows`; all matched.

**augmented** (flip pairs only):
- case = X′, trace = X's trace.
- Gold = X's answer. Relation `flips` via X′'s back-flip item; assert that the item exists and that its `then:` is X's choice.
- Mapping = Δ inverted. Tier = X's tier. Tag `realization: direct`.
- **Gate:** run flip's condition-holds verifier on the back item's `if` against X's **rendered** trace. Drop the pair on failure.

**revised:**
- case = C′ (from W3), trace = **restyle(C)'s trace**.
- Gold choice = C′'s choice through the options map. K_T = C′'s considerations. Relation `follows`. Tag `revised-authored`.

**decoy:**
- C from another family, with consideration-equity Jaccard ≤ 0.2 and no shared decisive equity.
- Same domain is allowed. Each card is used ≤ 3 times in train.

**self / none:** eval only, from test traces.

**Balance, always from `PairRecord.choice`:**
- hand-up ≤ 1/3 per arm (subsample source-gold arms; report what was dropped);
- position = first-mention rank in τ and card-order position;
- channels = a seeded random permutation per trace, never conditioned on gold;
- `recommended_option` per trace (≈ 50% of traces); the recommended-is-gold rate is reported per arm.

**Distance:** d per design §7.5, stored with its features.

**card_view and AR:** assign per train item before sampling (seeded):
- thin only on non-flip pairs, with share 0 in run 1;
- AR prompt on for 50% of items.

**Provenance:** tag K_T, `decisive` and M^K of flip and add_fact pairs `composed-with-C`.

### W3 — perturb (design §6)
Package: `pipeline/perturb/`.

**flip**
- `indirect_share` = 0.7 (config). The paraphrase path skips the overlap ceiling but keeps the model verify.
- Record `realization` in Δ.
- Regularize X′'s Φ (R35, R53): same `would_change` count as X; the touched consideration not systematically `weak`;
  shuffled order; back-flip item present.

**restyle:** **reject** numeric drift in decisive facts (R43).

**New `revise_card`** (design §7.3):
- Code picks a target choice ≠ C's, balanced by move; hand-ups count toward the cap.
- The model re-weights considerations, or adds one consideration **that cites ≥ 1 existing C fact**. Pure policy text
  goes in `reasoning.weighing`. It then updates reasoning, verdict and Φ.
- **F and Q are unchanged** (assert this).
- Δ_K lists the considerations that changed.
- Prompt: `perturb/prompts/revise_card.v1.md`.

### W4 — Ingest and extract (design §4, §5, §13.5)
Packages: `pipeline/ingest/`, `bench/models.py`, `datagen/llm.py`.

**W4a — splits (do this first, right after Step 0).** Version `SPLIT_RULE`:
- all episodes of a document share one family;
- per domain, ~20% of families go to test (≥ 5), ~10% to dev, the rest to train;
- the held-out domain goes entirely to test;
- assert that no eval trace shares a lineage root with any train pair.

**Option rules.** New prompt `extract_fq.v2.md`, plus a validator:
- no justification ("because", "in order to", "since", "to ensure" → reject and retry);
- complete courses of action, in matched form;
- **the set includes the opposite disposition as an `act` option** (grant vs deny; R58).

**Names.** No personal names in facts, the frame or options. Strip source-narration phrases (R40).

**Scenario fields:** `content_domain`, `refusal_sensitivity`.

**Cut first if time is short:**
- the episode finder: gpt-oss, the 4 pass/fail criteria, rejects to `data/store/episodes/rejected.jsonl`;
- refusal recording: Bedrock `stopReason` plus refusal-shaped replies, written to provenance; the fallback router is T2;
- the incomplete store: `data/store/incomplete/` with `missing:`.

If you cut these, use hand-picked episodes.

### W5 — Render (design §8)
Package: `pipeline/render/`. New prompt `render.v3.md`.

**Options.** Options are text, not tools.
- Each option appears through the channel pre-assigned in the trace store.
- **Never a menu.**
- When the trace has a `recommended_option`, someone recommends it, in the same register as everything else.

**R49 single-hop rule.** Every relevant fact must be readable in one hop.

**Span map.** σ gains `options: [{option, message, start, end, channel}]`, located in code.

**Gates:**
- every decisive fact and every option is located;
- leak scan: option ids/labels, menu shape, gold, and **text from the A part of every card that will be served with
  this trace** (facts excluded);
- no person names.

On failure: 2 re-render tries, then drop with the reason logged.

**Storage:** write to the trace store, not per pair.

### W6 — Harness, project, training, eval (design §9.3, §11–13)

**Harness**
- Thin view removes Φ, lesson and limits, plus every flip-condition reference in the prose; the leak check confirms it.

**Project**
- Mode C, passed explicitly.
- **SFT prompt = the plain harness prompt** (no worked examples or hints).
- Decoy loss mask ends at the end of `applicability` (in `training/sft_data.py`: labels −100 after it).
- Log rows dropped by `max_length`.
- Meta: arm, card_view, AR, writer, rationalized, d, realization, tier, intent, family, split.

**Training**
- LoRA SFT with `code/training/sft_lora.py`.
- Stop vLLM first, then serve the adapter (`--enable-lora`) for eval.

**Eval, core grid:** {base, SFT} × {none, relevant, augmented, revised, decoy, self}. AR prompt on, full card, n = 1.

**Eval, second pass if time allows:** AR off; the thin view on eligible relevant pairs; the equities cells (E_d on/off ×
card none/relevant).

**Eval, outputs**
- **Headline:** four curves (design §13.2).
- **By-arm graph.**
- Off-menu rate.
- **Baselines:**
  - copy-the-case, by intent (100% on revised by construction; say so);
  - always-hand-up;
  - always-`act`;
  - majority disposition per domain.
- Accuracy conditional on the gold option being enumerated.
- Revised "follows both" rate, against the relevant restyle partner.
- Decoy vs none.
- % incorrect irreversible; % ask a human.
- Within-family curves (R56).
- Breakdowns by arm, intent, realization, tier and family; the held-out domain as its own panel.

**Rename:** Checkpoint 2's arm `augmented` → `revised` (`bench/schema/scenario.py` `Arm`, `eval/core.py` `ARMS`,
`eval/stats.py`, `library/convert/scenarios.py`). Add a note in `results/RESULTS-2026-10-25.md`.

### W7 — H3 pilot (design §13.4; CPU + Bedrock only; start immediately; independent)

**Data**
- Find 15–30 DOE OHA decisions that each cite an earlier OHA decision as controlling or analogous. Record the citing
  sentence.
- Extract C from the cited decision and T from the citing one.

**Runs**
- Stand-in R\* = gpt-oss-120b, plus a second Bedrock model family if time allows (cut this first).
- Each stand-in extends C to T, and also answers T **without** C.

**Report**
- Agreement with O(T), with and without C, by band: same guideline and issue vs different.
- The majority-class baseline.

**Outputs:** `results/H3-PILOT-2026-10-28.md` + `results/h3-pilot/`. Soft cap $20.

### W8 — Sources and the batch

**Sources**
- ~30–40 more DOE OHA decisions (varied guidelines and outcomes).
- More 5 CFR 2635 examples if useful.
- **One new public-domain decision domain, held out whole for test.** Choose from `context/sources/source-catalog.csv`
  (e.g. MSPB or GAO decisions, IG reports) and say which you chose and why.

Acquire now. Run extraction after W4a and the option rules land.

**Batch:** extract → perturb → revise_card → pair (all arms) → render (into the trace store) → gold.
- Per train scenario: 1 restyle, 1–2 flips, 1 add_fact, 1 revise_card.
- Target ~35 train scenarios.
- Bedrock: 8–16 calls in flight, with backoff.

## Order of the day

1. **Morning**
   - Pull; get tests green.
   - Step 0 contract, then W4a splits.
   - Launch W1, W3, W4, W5, W6 and W7. W8 acquires.
2. **Midday:** run the batch. Put 5 traces and 5 revised cards in `results/DATAGEN-2026-10-28.md` for Peter.
3. **Afternoon**
   - Rejection sampling on the GPU.
   - Export `data/exports/v1/`.
   - LoRA SFT.
4. **Evening**
   - Serve the adapter.
   - Core eval grid; report.
   - Push as results land.

**Where time runs out** (the GPU is the bottleneck: ~15–20k-token prompts, multi-thousand-token outputs; Jev calls
close behind), cut in this order:
1. the eval second pass;
2. N's second round of 4;
3. the W4 extras;
4. the H3 second model family.

**Never cut:** the split fix, the held-out domain, the decoy filter, the decoy loss mask, the never-saw-C gold rule.

## Rules
- **Gold**
  - **Gold never comes from a solver that has seen C** (verdict, relation, `via`, `governs`).
  - G is a code-only join.
  - Order: by construction → source-endorsed → independent solve.
- **Provenance** on every field: `writer`, model id, prompt version, input hashes, gold tier, `composed-with-C` where it
  applies.
- **Safety scope**
  - In scope: decision ethics, law and policy. Decision-level content about force or authority is in scope: tag it, don't
    drop it.
  - Out of scope: operational technique.
  - Never route around a refusal of out-of-scope content.
- **Judge** = Jev via OpenRouter, through the cached interface.
- **Spend:** Bedrock soft cap $150 for the day; report the actual spend.
- **Housekeeping**
  - Keep every version. Commit and push after each workstream.
  - New risks get the next free id after R58.
  - Fix stale notes:
    - `code/pipeline/PIPELINE.md` (says teacher);
    - the `config/models.yaml` allowlist comment;
    - CLAUDE.md "Where things are" (code dirs are no longer empty).
- **2f example pairs**
  - Reject P-1217d16660.
  - Re-tag P-7b3fe9966f as a paraphrase-realized flip.
  - P-2c6540bbdd is T2.

## Stop and ask Peter
- Anything that changes a ruling in the design.
- The teacher as the default writer.
- Non-rationalized Granite acceptance < 20% of train items. Train anyway with rationalized items included, and flag it at
  the top of the report.
- Any per-arm floor that can't be met.
- In-domain test < 30 items, or held-out domain < 15.
- Deleting data.

## Deferred
**T2**, after the first training run:
- skeleton + world kit, with conditions-driven fact selection;
- trap, a fortiori, remove/revise fact, Q operators, near-miss decoys;
- add_fact-derived augmented pairs;
- the fallback router;
- A/B render test, salience probe, single-hop check, grounding judge, two-solver agreement, twin-contrast filter, Horty
  checker;
- RLVR.

**v2** (`docs/V2-PRIORITIES.md`):
- natural pairs + the structural index;
- token space for derived facts;
- multiple served cases;
- the near-neighbor arm;
- transfer.
