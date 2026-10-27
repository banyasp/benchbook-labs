# Build brief — design v2.4: rebuild, scale to 150+ pairs, train and eval (2026-10-27/28)

*The work order for the EC2 session. Written in Peter's claude.ai session after his full walkthrough of the
pipeline. **Read first:** `CLAUDE.md` → `context/DATA-PIPELINE-DESIGN-v2.md` (**v2.4**, the design; section numbers
below refer to it) → this brief → `docs/HYPOTHESES.md` → `docs/RISK-REGISTER.md`. This brief supersedes
`BUILD-BRIEF-2f-2026-10-25.md` (kept). Where this brief and older files differ, this brief wins; where it and the
design differ, the design wins and you tell Peter.*

## Goal and definition of done (Peter: "150+ pairs, training and eval tomorrow; parallelize")

- **Training data.** ≥ 150 **train** items with an accepted SFT target (accepted or rationalized), spread across the arms
  `relevant`, `augmented`, `revised` and `decoy` (design §7.2).
- **Eval set.** A test split per family, **one whole source domain held out**, and the eval-only pilot imports.
- **Models.** One LoRA SFT run on Granite 4.2 8B; the base and SFT models evaluated on the v1 grid (design §13).
- **Report.** `results/RESULTS-2026-10-28.md` with the headline graph: choice accuracy vs d(C, T), one curve per model, 95% CIs.
  It also gives accuracy by arm and the breakdowns and baselines of design §13.3.
- **In parallel:** the H3 pilot report, `results/H3-PILOT-2026-10-28.md`.
- RLVR is **not** in tomorrow's definition of done. Start it only if everything above is finished.

## What exists vs what v2.4 asks (from a survey of the code at b695b0a)

| Area | Today | v2.4 |
|---|---|---|
| SFT writer (`code/pipeline/solve/`) | gpt-oss **teacher that sees full gold**, N=3 | **Granite rejection sampling, no gold, N=8, mode C**; teacher kept as `writer: teacher` |
| Arms (`bench/schema/pipeline.py` `PairRecord`) | no `arm` field; `project` hard-codes `relevant` | `arm` ∈ relevant / augmented / revised / decoy / none / self; plus `card_view` |
| Augmented / revised | schema literal only, no generator | augmented = reversed flip pairs; revised = new `revise_card` operator |
| Hand-up cap (`pair/build.py` l.114–126) | per intent | per arm (and per intent within arm) |
| Served card (`bench/schema/case.py` `ServedCase.build`) | serves option `move` / `irreversible`; no thin view | strip `move`/`irreversible`; `card_view: full \| thin` |
| Render (`render/render.py`, `render.v2.md`) | options made "reachable" by **tools** | options are text, discoverable, never a menu; channel per option in σ; recommendations sometimes wrong; R49 rule |
| Episodes | hand-picked seed | pass/fail episode finder; rejects kept |
| Refusals | generic retry; Bedrock `stopReason` ignored (`datagen/llm.py` l.183–219) | detect + record; fallback router is T2 |
| Incomplete extractions | dropped after 3 tries | saved to `data/store/incomplete/` with `missing:` |
| Flip realization (`perturb/flip.py`, `overlap.py`) | always indirect | `indirect_share` = 0.7; paraphrase path tagged |
| Distance | features only | default scalar d (design §7.5) + features |
| Tests | not runnable in a fresh checkout | run with the box's venv (below) |

## Parallel workstreams (one Sonnet subagent each, one package each; you integrate)

Run tests with `PYTHONPATH=code <venv>/bin/python -m pytest -q code/pipeline code/bench` (the box venv; recreate
it per `code/datagen/README.md` if missing). Every workstream adds tests with fakes and **no live calls in tests**.
Keep every version (`store.write_yaml` already does; prompts get a new `.vN` file, never an edit in place).

**W1 — SFT writer (design §10).** `code/pipeline/solve/`.
- New `rs.py` (rejection sampling):
  - Prompt = the harness prompt for the item's arm and card view + two worked examples (PDF journalist/raft pp.
    14–18; the v6 same-domain flip converted to PDF names, no `confidence`, with `via`).
  - **No gold anywhere in the prompt.** Mode C. N = 8 through the vLLM server (`n=8` in one request).
- Filter (`check.py`, new `check_rs`):
  - Align the model's live facts and options to gold with the 2d scorers (greedy; Jev Choice for option text).
  - Exact on choice, relation, `via`, `governs`. Bucket agreement ≥ 0.7 on aligned items, with every decisive fact and
    consideration correct.
  - Decoys: check only `governs` and relation; nothing after `not_governed` is scored.
  - Log all sub-scores per sample.
- Rationalize: pairs with 0 accepted samples get one pass with the gold verdict + relation as a hint, tagged `rationalized`.
- Keep the existing teacher path as `--writer teacher`; tag its samples `writer: teacher`. The default export uses
  Granite samples.
- Log acceptance per arm / intent / family / tier / card view to `data/store/solve.acceptance.json`.

**W2 — Arms, pair, gold, distance (design §7, §9).** `bench/schema/pipeline.py`, `pipeline/pair/`, `solve/structure.py`.
- `PairRecord` gains `arm`, `card_view`, `recommended_option`, `d`, `writer`. Bump the schema version; old records
  load with `arm: relevant`.
- **augmented:**
  - For every flip pair, and every add_fact pair whose verdict changed, build (case = X′, trace = X's trace).
  - Gold = X's answer; relation `flips` via X′'s **back-flip item** (assert it exists and its `then:` = X's choice);
    mapping = Δ inverted; tier = X's tier.
  - X's trace: reuse the trace already rendered for X (decoys render source scenarios); render one if missing.
- **revised:** pair C′ (from W3) with C's own trace or its restyle. Gold choice = C′'s choice through the options map;
  K_T = C′'s considerations; relation `follows`; tag `revised-authored`.
- **self** (eval only): card(X) with X's trace; all matched; d = 0. **none** (eval only): no card.
- Hand-up cap ≤ 1/3 per arm. Gold-position balance per (arm, n options). Recommendation-is-gold ≈ 50% per arm.
- d per design §7.5, stored with its features.

**W3 — perturb (design §6).** `pipeline/perturb/`.
- `flip`:
  - `indirect_share` = 0.7 (config). The paraphrase path skips the overlap ceiling and keeps the model verify.
  - Record `realization` in Δ.
  - Regularize X′'s Φ (R35): same `would_change` count as X; the touched weight not systematically `weak`; back-flip item present.
- `restyle`: **reject** numeric drift in decisive facts (R43), don't just warn.
- **New `revise_card`** (design §7.3):
  - Code picks a target choice ≠ C's, balanced by move (hand-ups count toward the cap).
  - The model writes A′: re-weights or adds one deployer-policy consideration, then updates reasoning, verdict and Φ.
  - **F and Q are unchanged** (assert byte-equal).
  - Δ_K lists the considerations that changed. Prompt `perturb/prompts/revise_card.v1.md`.

**W4 — Ingest and extract (design §4, §5).** `pipeline/ingest/`, `bench/models.py`, `datagen/llm.py`.
- **Episode finder** (`episodes.py`, gpt-oss): decision points per document with span range, the 4 pass/fail
  criteria, `content_domain`, `refusal_sensitivity`. Rejects go to `data/store/episodes/rejected.jsonl` with the failed
  criterion.
- **Scenario fields:** `content_domain`, `refusal_sensitivity` (top level; add to `Scenario`).
- **Refusals:** read Bedrock `stopReason` and detect refusal-shaped replies. Record `refusal: true` + reason in
  provenance. The fallback router is **T2** (stub the config key `fallback_provider`).
- **Incomplete store:** on `ExtractionError`, save what was extracted to `data/store/incomplete/<family>/<id>.yaml`
  with `missing: [...]` and the reason.
- **Option rules** (new prompt version `extract_fq.v2.md` + validator):
  - no justification ("because", "in order to", "since", "to ensure" → reject and retry);
  - each option a complete course of action;
  - matched form.
- **Names:** no personal names in facts, frame or options (regex + a list of the source's named people) → retry.
- Strip source-narration phrases (R40).

**W5 — Render (design §8).** `pipeline/render/`. New prompt `render.v3.md`:
- **Options are text, not tools.** Each option appears in the trace through its pre-assigned **channel** (code
  assigns channels before rendering, balanced so the gold option's channel doesn't predict it): system-prompt
  scope, operator/colleague message, tool result, or document. **Never a menu** (no list of all options anywhere).
- When the pair has a `recommended_option`, someone in the trace recommends it, in the same register as everything else.
- **R49:** every decision-relevant fact readable in one hop; no arithmetic or multi-step combination; indirectness
  only by wording, channel or placement.
- σ gains `options: [{option, message, start, end, channel}]`, located in code like facts.
- **Gates (T1):** every decisive fact and every option located; leak scan (option ids, labels, gold, case text,
  menus); no person names. A failure triggers a re-render (2 tries), then the pair is dropped with the reason logged.

**W6 — Harness, project, eval (design §9.3, §11–13).** `bench/schema/case.py`, `code/harness/`, `pipeline/project/`, `code/eval/`.
- `ServedCase`: never serve `move`/`irreversible`. `card_view: thin` drops `flip_conditions`, `lesson`, `limits`.
- Thin share 30% of training prompts (seeded).
- Project meta: arm, card_view, writer, rationalized, d, realization, tier, intent, family, split. Eval samples per
  (pair, arm, card view, AR prompt on/off, equities cell).
- Eval:
  - **off-menu** rate (counted wrong in choice accuracy);
  - copy-the-case baseline split by intent;
  - always-hand-up baseline;
  - accuracy conditional on the gold option being enumerated (R29);
  - revised "follows both" minimal-pair rate;
  - the headline curve (accuracy vs d; bins of 0.1 or quantiles, 95% bootstrap CIs, one line per model);
  - breakdowns by arm, intent, realization, tier, family; the held-out domain as its own panel.
- Equities cells (eval only): E_d on/off × card none/relevant, for base and SFT.

**W7 — H3 pilot (design §13.4; runs now, CPU + Bedrock only, independent of everything else).**
- Find 15–30 DOE OHA decisions that cite an earlier OHA decision as controlling or analogous. Record the citing
  sentence as the link evidence.
- Extract both decisions with the current extractor: C from the cited one, T from the citing one.
- Stand-in R\* = gpt-oss-120b **and** a second model family on Bedrock (agreement required for a label; report each).
  Each extends C's reasoning to T, and also answers T **without** C.
- Report agreement with O(T) (the citing decision's outcome), with and without C, by a coarse band (same
  guideline and issue vs different). Note the outcome base rate (OHA outcomes skew one way; report the majority-class
  baseline).
- Output `results/H3-PILOT-2026-10-28.md` + `results/h3-pilot/`. Soft cap $20.

**W8 — Sources and the batch (starts in the morning alongside W1–W6).**
- **Sources:**
  - ~30–40 more DOE OHA decisions (varied guidelines and outcomes), more 5 CFR 2635 examples if useful, and
    **one new public-domain domain to hold out whole for test** (pick from `context/sources/source-catalog.csv`;
    decision documents with written reasons, e.g. MSPB or GAO decisions, IG reports; say which and why).
  - Acquire, normalize and run the episode finder as soon as W4 lands; acquisition can start immediately.
- **Batch**, once W2–W5 land:
  - extract → perturb (per train scenario: 1 restyle, 1–2 flips, 1 add_fact, 1 revise_card) → pair (all arms) →
    render → gold.
  - Aim for ~35 train scenarios → ~240 train items before filtering.
  - Run Bedrock calls concurrently (thread pool, ~8–16 in flight; back off on throttling).

## Order of the day

1. **Morning:**
   - pull; read; get tests green on the current code;
   - launch W1–W6 and W7 in parallel; W8 starts acquiring;
   - integrate as each lands (tests first).
2. **Midday:** run the batch (W8). Spot-print 5 rendered traces and 5 revised cards into
   `results/DATAGEN-2026-10-28.md` for Peter.
3. **Afternoon:**
   - rejection sampling on the GPU (Checkpoint 2 has no priority now);
   - export `data/exports/v1/`;
   - LoRA SFT with `code/training/sft_lora.py` (loss on Y only).
4. **Evening:** the eval grid for base and SFT, then the report. Push results as they land.

## Rules (unchanged unless noted)

- **Gold never comes from a solver that has seen C.** G is assembled by code only. Gold order: by construction →
  source-endorsed → independent solve that never sees C.
- **Provenance on every field and artifact**, with `writer`, model id, prompt version, input hashes and gold tier.
- **Safety scope.** Decision ethics, law and policy. Decision-level content about force or authority is in scope:
  tag it with `refusal_sensitivity`, don't drop it. Operational technique is out of scope (strip it, or fail the episode). Never
  route around a refusal of out-of-scope content.
- **Judge** = Jev via OpenRouter, through the existing cached interface.
- **Spend.** Bedrock soft cap $150 for the day; report actual spend.
- **Records.** Append new risks to `docs/RISK-REGISTER.md` (next free id after R56; R50–R56 were added with this brief). Keep every version. Commit and push
  after each workstream lands.
- **Stale notes to fix as you go:** `code/pipeline/PIPELINE.md` (says teacher), the `config/models.yaml` allowlist comment,
  CLAUDE.md "Known drift" item 4 (the instance role is now allowed).
- **Advice on the 2f example pairs:** reject P-1217d16660 (solver error). Keep P-7b3fe9966f, re-tagged as a
  paraphrase-realized flip. Replacing P-2c6540bbdd's authored flip with a source-stated contrast is T2.

## Stop and ask Peter (don't decide yourself)

- Anything that would change a ruling in the design.
- Making the teacher the default writer.
- Non-rationalized Granite acceptance < 20% of train items. Report it, train with rationalized included as the
  default, and flag it at the top of the report.
- Deleting data.
- The held-out domain having fewer than ~15 eval items.

## Deferred (T2, after the first training run): design §5.3 skeleton + world kit and conditions-driven fact
selection; trap, a fortiori, remove/revise fact, Q operators, near-miss decoys; fallback router; A/B render
test, salience probe, single-hop check, grounding judge, two-solver agreement, twin-contrast filter, Horty
checker; RLVR. **v2** (`docs/V2-PRIORITIES.md`): natural pairs + structural index, token space for derived facts,
multiple served cases, near-neighbor arm, transfer.
