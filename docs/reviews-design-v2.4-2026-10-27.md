# Cold review: design v2.4 + build brief v2.4 (2026-10-27)

Scope: `CLAUDE.md`, `context/DATA-PIPELINE-DESIGN-v2.md` (v2.4), `BUILD-BRIEF-v2.4-2026-10-27.md`,
`docs/HYPOTHESES.md`, `docs/RISK-REGISTER.md` (R50–R56), `context/PDF-RECONCILIATION-2026-10-25.md`, PDF v0.4 text,
spot-checks of `code/`. Ranked most severe first. "Fix" text is meant to be pasted into the design or brief.

---

## 1. BLOCKER: thin cards make the gold for flip and augmented items unanswerable

**Where:** design §9.3 ("Eval runs both views on `relevant` and `augmented`"), §5.2, §10 step 2; brief W1, W6.

**Problem:**
- A thin card drops `flip_conditions`. But gold `via` for a flip pair names a `would_change` item on the served card.
  For an augmented pair it names X′'s back-flip item. The model cannot cite an item it cannot see.
- `bench/schema/reply.py` l.188 and `format.v1.md` l.88 require `via` exactly when the relation is `flips`. So every
  correct thin-card flip reply fails the schema or fails the exact `via` check in the RS filter. Acceptance for those
  items will be 0%, rationalization will fail too, and the thin training share will hold only follows and decoy items.
- Without Φ, `flips` and `distinguished` can't be told apart, so the relation label is ill-defined as well.
- `ServedCase.build` (`bench/schema/case.py` l.218–221) renames prose references, so `reasoning.uncertainty` keeps
  "REF1-flip1" (as in PDF p. 16). The thin card would then point at an item that no longer exists, and the prose can
  leak the flip condition.

**Fix (needs Peter, because it changes a §9.3 ruling; add it to "Stop and ask"):** recommended for T1:
> "`card_view: thin` applies only to pairs whose gold relation is `follows` or `distinguished` (restyle, add_fact,
> revised). Pairs whose gold relation is `flips` (relevant flips and augmented) are always served `full`. A thin
> card also removes every `<REF>-flip*`/`noflip*`/`watch*` reference from the reasoning prose, and the leak gate
> checks that none remain."

Alternative: on thin cards, gold `via: null`, the relation accepts `flips|distinguished`, and the schema allows
`flips` without `via` when `card_view == thin`.

## 2. The split rule gives almost no in-domain test set; "a test split per family" can't be built as written

**Where:** brief "Goal" (Eval set); design §13.5; `pipeline/ingest/registry.py` l.62 `SPLIT_RULE`.

**Problem:**
- The code puts the first family (sorted by hash) in test, the second in dev and every other family in train.
- Families are single decisions (`OHA-26-0087`, …). With ~40 OHA families, test holds one decision.
- Nothing implements "one whole source domain held out".
- Episodes from one document can land in different families (`family_of` uses `ep.family` first). Then one
  document can sit in both train and test.
- Leak risk: training uses X's own trace (augmented arm) and its restyles (relevant, revised). Running `self` or
  `none` on any train-lineage trace would therefore test memorized items.

**Fix (W8/W4):**
> "Splits: within each domain, sort families by sha256 and assign ~20% to test, ~10% to dev and the rest to train,
> with at least 5 test families per training domain. All families of the held-out domain go to `test`. Every
> episode from one source document shares that document's family. Eval items (every arm) come only from
> `test`/`eval-only` scenarios. Assert that no eval trace scenario shares a lineage root with any train pair."

Version `SPLIT_RULE` and re-split **before** perturbing. The brief's stop rule (held-out < 15 items) should also
apply to in-domain test (< 30 items).

## 3. Augmented from add_fact: wrong relation and gold written by a model that saw X; flip back-items unverified

**Where:** design §7.2 augmented row ("or add_fact(X) when its verdict changed … relation `flips` via X′'s back-flip
item"); brief W2; `perturb/add_fact.py` l.145–170.

**Problem:**
- An add_fact X′ has no stated flip that it reverses. Its back item is written by the composer (`TASK_A`, which sees
  the parent's worked answer and X's choice), with `need_back`. So the `via` label was tailored by a model that saw
  the gold. That breaks design §1: "never comes from a solver that has seen C".
- The item's `if` is "the added fact is absent", which X's trace satisfies trivially. That makes it pure lookup.
- For flip-derived X′, nobody checks that the reversed item's `if` actually holds in X's **rendered** trace (X may
  simply not mention the fact).

**Fix:**
> "T1 augmented = flip pairs only (add_fact augmented is T2). For each augmented pair, run flip's existing
> condition-holds verifier on X′'s back-flip `if` against X's rendered trace. On failure, drop the pair and log
> the reason."

## 4. Decoy SFT targets train the very judgment the rules say must not be trained

**Where:** design §10 ("Not governed … Y ends at applicability … followed by a verdict … the filter checks only
`governs` and relation"); CLAUDE.md ("nothing it does after deciding not_governed is rewarded or punished").

**Problem:**
- SFT loss on the decoy verdict's `choice`, `course` and `now` trains Granite's own unverified case-free decisions.
  That is reward after `not_governed`.
- Decoys are also the cheapest items to accept (two exact fields), so "≥ 150 train items" can be met by a
  decoy-heavy mix.
- Separately, design §13.3 needs decoy **choice** scored in eval (PDF falsifier 3: decoy vs none). Nothing says
  eval scores what training ignores.

**Fix (design §10, §11, §12):**
> "For decoy items, the SFT loss mask ends at the end of the `applicability` document. The verdict document stays
> in the target text but is masked (labels = -100). In eval, the decoy `verdict.choice` is scored against T's own
> answer for falsifier 3 only; it is never a training signal."

Brief "Definition of done":
> "Per-arm floors for train items with targets: relevant ≥ 60, augmented ≥ 20, revised ≥ 20. Decoy ≤ 20% of train
> items."

## 5. Decoy gold is unsafe by construction, and the decoy pool is tiny

**Where:** design §7.2 decoy row; `pipeline/pair/build.py` `decoy_records` (l.52–80).

**Problem:**
- The thesis is that cross-domain cases can govern. The RS prompt's own worked example (PDF pp. 14–18) is
  cross-domain, all facts `live_only`/`case_only`, with `governs: true`.
- All domains share one 28-equity set (`data/registry/equities/pilot.yaml`). So an OGE-ethics card can genuinely
  govern an OHA trace, for example on `due_process`, `lawful_authority` or `institutional_credibility`.
- `equity_jaccard` is computed but never used to filter.
- Train has about two domains (OHA, OGE 2635). Each OHA trace's "different domain" decoy is drawn from a handful of
  OGE cards, so **card identity predicts `not_governed`**.

**Fix (W2):**
> "Decoy C must have equity Jaccard ≤ 0.2 with T over consideration equities, and no shared `decisive`-consideration
> equity. Any one card serves as a decoy in at most 3 train pairs. Same-domain, different-family decoys are allowed
> when they pass the equity filter."

Also log R57: "Decoy card identity predicts `not_governed`."

## 6. Code paths the brief assumes won't work for the new arms

**Where:** brief W2/W5; `pair/build.py`, `render/render.py`.

- **Hand-up cap and position use the wrong gold.** `is_handup(T)` and `gold_position(T)` read
  `T.case.verdict.choice` (build.py l.40, l.108–110). For `revised`, gold = C′'s choice ≠ T's verdict.
  Fix: "compute hand-up and position from `PairRecord.choice`, never from T's verdict."
- **Trace reuse is not supported.**
  - `render_pair` writes `pairs/<pair-id>/trace.json`, so traces are per pair.
  - Design §7.1 ("one rendered trace … several cases … at no render cost") needs a trace store keyed by trace
    scenario.
  - `balance_positions` re-orders T into a **new scenario copy** (`reorder.py`), which forces a new render and
    defeats reuse.
  - Fix: "Traces live at `data/store/traces/<trace-scenario-id>/` (trace.json, span map, channels,
    `recommended_option`). Pairs reference them. No T-copy reordering in v2.4."
- **Position now means something else.** Options are no longer a menu, so T's option-list order isn't what the
  policy sees. What it does see is (a) the order in which options are first mentioned in τ (from `σ.options`) and
  (b) the served card's option order.
  Fix: "Balance and report gold position as (a) first-mention rank in τ and (b) the card-order position of the
  gold's card counterpart."
- **Channels and recommendations belong to the trace, but gold differs by arm.** The same trace has gold c for
  relevant/self and c′ for revised. So "channel doesn't predict gold" and "recommended-is-gold ≈ 50% per arm" can't
  both be enforced per arm.
  Fix: "Assign channels by a seeded random permutation per trace, never conditioned on which option is gold (that
  makes channel independent of gold in every arm). Pick `recommended_option` per trace. The per-arm
  recommended-is-gold rate is reported, not controlled."
- **`pair_id` collides.** It is hash(C, T, intent) (l.31), with no arm or card_view. Fix: "card_view is assigned per
  train pair at pair time (seeded) and is part of the id. Eval views are expanded at project time."
- `project_pair` defaults to `mode="B"` and hard-codes `arm: "relevant"` (`project.py` l.72, l.84–88). The brief
  should say "pass mode C."
- No LoRA serving path exists (`inference/serve.sh` has no `--enable-lora`). The SFT eval needs `--enable-lora
  --lora-modules sft=<dir>` or a merged checkpoint. vLLM runs at `GPU_UTIL=0.90` and must be stopped before
  `sft_lora.py`.

## 7. "augmented" already means "revised card" in the Checkpoint-2 code and in the reconciliation file

**Where:**
- `library/convert/scenarios.py` l.7 ("augmented served = the `-r1` revised card");
- `bench/schema/scenario.py` l.19 `Arm`;
- `eval/core.py` l.26 `ARMS`;
- `eval/stats.py` l.220;
- reconciliation §F ("revised-card control (the PDF's 'augmented case')").

**Problem:** v2.4 redefines `augmented` as a reversed flip and adds `revised`. A builder extending `eval/` will mix
the two meanings, and the CP2 numbers labelled "augmented" are really revised.

**Fix:**
> "In CP2 code and results, rename arm `augmented` → `revised` (schema migration plus a note in
> results). Update reconciliation §E/§F: the PDF's augmented = case facts altered so its conclusion flips
> (design v2.4 §7.2); revised C′ is an addition."

## 8. New shortcut cues introduced by the arm design

- **Trace provenance predicts the relation.** In training, source traces (X's own) appear only in `augmented`
  (always `flips`) and `decoy` (`not_governed`); `self` and `none` are eval-only. Derived traces appear in
  relevant/revised. Fix (cheap, no render):
  > "Add `reverse_restyle` training pairs: card = restyle(X), trace = X, gold = X's answer, `follows`. Also run
  > `revised` on X's own trace in half the cases."
- **Augmented is always direct lookup.** X's trace states X's original fact, and X′'s back item restates it.
  `indirect_share` only shapes X′'s trace. Fix: "Tag augmented pairs `realization: direct`, report them apart, and
  never pool them with indirect flips."
- **The source answer is nearly always the `act` move.** Stored OHA scenarios have `real_move: act`, with
  ask/hold/partial authored distractors (DR-OHA-26-0087-1: O1 deny = act, the others ask/hold/partial). Every
  source-gold arm (augmented, decoy, self, none) then rewards "pick the act option", and OHA's skew toward denial
  adds to it. Fix:
  - W4 option rule: "Each set includes the opposite disposition as an `act` option (grant vs deny)."
  - W6 baselines: "always-`act`" and "majority disposition", per arm.
  - Log R58.
- **Revised cards show a stated edit.** The "the deployer now weighs X above Y" text marks the arm. Gold = copy the
  card, so this is harmless for choice. But report the copy-the-case baseline on revised (it is 100% by
  construction) so nobody reads revised accuracy as reasoning.

## 9. Parts of G come from models that saw C (not covered by the "never" rule)

**Where:** design §1, §9.1; `perturb/flip.py` TASK (rewrites considerations, favors and weight with C visible);
`add_fact.py` `TASK_A` (composes A′ with the parent's worked answer in the prompt).

**Problem:** K_T and M^K are gold for the RS filter's "every decisive consideration in the right bucket". For
add_fact (tier `model-solved`), only the verdict is blind. The considerations, `decisive` and the consideration map
were composed by a model holding C and its answer.

**Fix (design §9.1):**
> "The never-saw-C rule covers verdict, relation, `via` and `governs`. K_T, `decisive` and M^K for flip and add_fact
> are `composed-with-C` (provenance tag). For `model-solved` pairs, the RS filter drops the consideration-bucket
> condition and keeps only the fact buckets and the exact fields."

## 10. RS filter and SFT export: guesses that cost time or produce bad targets

**Where:** design §10; brief W1. Add these to §10:
- **Denominator:** "Bucket agreement = agreeing gold items / **all** gold items (unaligned gold items count as
  disagreements). This also requires fact recall ≥ 0.6 (weighted)." Without it, a sample that enumerates 3 of 12
  facts passes.
- **Consideration alignment:** "Align the model's considerations to K_T with `scorers.alignment.align` (two-pass
  Choice, greedy) on `equity + why + cited fact texts`."
- **`via`:** "Translate served ids (REF1-flip2) to global ids through `ServedCase.table` before comparing."
- **Rationalize hint:** "Gold choice, relation **and `via`** (served ids)." Without `via`, rationalized flips still
  fail.
- **SFT prompt:** "The SFT prompt is the plain harness prompt for the item: no worked examples and no rationalize
  hint." Otherwise gold leaks into training prompts. Also, prompt + examples (~18k tokens) exceed `sft_lora.v1`
  `max_length: 20000`, and longer rows are **dropped silently** there.
- **AR prompt in training:** not specified. Proposed: "AR prompt on for 50% of training prompts (seeded)", so that
  the AR-off eval cells aren't out of distribution.
- **Thin view:** "card_view is assigned per train item (30%, seeded) **before** sampling. Sample N only for that
  view."
- **Second worked example path:** `ideas/benchbook-analogical-pipeline-example-v6.yaml`. The v2.4 brief doesn't
  give it; it is only in the superseded 2f brief.

## 11. Feasibility of "150+ items, SFT and the eval grid in one day"

**Likely bottleneck: GPU decode for rejection sampling, then the eval grid, on one L40S, with the Jev judge
close behind.**
- **Rejection sampling:**
  - Prompts are ~15–20k tokens (trace + card + equities + format spec + two worked examples of ~4–5k each).
  - Outputs are 4–8k tokens in mode C, with `max_tokens 12000`.
  - With ~27 GB left for the KV cache at `GPU_UTIL 0.9`, only a few n=8 requests fit at once.
  - ~250 items × 8 samples × ~5k tokens ≈ 10M output tokens. That is several hours, plus rationalization.
- **Eval grid:** about 15 cells per test trace (none, relevant×AR×view, augmented×AR×view, revised×AR, decoy×AR,
  self×AR, plus equities) × 2 models. That is another 2–3 h.
- **Judge:** `align` makes one Jev call per gold item and one per generated item, for facts, considerations and
  options: ~40–50 calls per sample. With `max_workers=8`, ~2,000 samples take hours unless gated.
- **Integration:** W1, W5 and W6 all depend on W2's `PairRecord` and `ServedCase` changes. These are not "one
  package each". Fix: "W2 lands the schema fields (`arm`, `card_view`, `recommended_option`, `d`, `writer`, trace
  store) first, within ~1 h, as the contract. Then launch W1/W5/W6."

**Cut in this order:**
1. **Eval grid:** run AR-on, full card, mode C, n=1 across the six arms. Drop AR-off, the thin eval view and the
   equities cells to a second pass.
2. **Rejection-sampling cost:**
   - N = 8 → 4 for the first pass, with `max_tokens` 8000;
   - filter exact-first: option alignment → choice/relation/`via`/`governs`, and run fact/consideration alignment
     only on survivors;
   - `--enable-prefix-caching`.
3. **W4 extras:** the episode finder, the incomplete store and refusal recording. Use hand-picked episodes; extract
   option rules and the names check stay.
4. **Thin training share:** set it to 0 for run 1. This also sidesteps finding 1.
5. **W7:** drop the second model family. The teacher-writer path stays untouched.

**Do not cut:** the split fix (2), the held-out domain, the decoy filter (5) and the loss mask (4).

## 12. Headline graph: which cells go into the curves isn't specified

**Where:** design §13.2 ("one curve per model") vs CLAUDE.md ("one curve per arm (base / harness / SFT / SFT+RL)").

**Problem:**
- Revised pairs (all-matched M^F, K_T = C′'s K) sit at d ≈ 0 with `self` and restyle, so the d = 0 bin fills with
  copy-the-card items.
- Decoys sit at d = 1 with a different gold semantics.

**Fix:**
> "Headline curves: base+none, base+relevant ('harness'), SFT+none, SFT+relevant. The x-axis is the relevant pair's
> d (the none rows are plotted at their trace's relevant-pair d). Cells: AR on, full card. Arms pooled: relevant
> only. `self` is plotted as the d = 0 point. Augmented, revised and decoy go in the by-arm graph. The
> within-family curves (R56) are plotted next to it."

## 13. Leak gate vs trace reuse

**Where:** design §8.4 gate 2 ("no … case text"); §8.3 ("no verbatim runs of 8+ words from F").

**Problem:** For restyle, self and augmented, the served card's facts are by design (near-)restatements of the
trace's facts, so a "case text" scan fires on legitimate content and drops pairs. It also isn't defined which
card(s) to scan against when a trace is reused.

**Fix:**
> "Leak scan scope = option ids and labels, menu shape, and text from the A part of **every** card that will be
> served with this trace (verdict, reasoning, Φ, lesson, limits). Facts are excluded (they are covered by the
> 8-word rule against T's own F)."

## 14. Revised arm details

**Where:** design §7.3; brief W3.
- **The added "deployer-policy consideration" has no facts in T,** so the gold K_T contains a consideration the
  model can't enumerate from the trace. Fix: "An added consideration must cite ≥ 1 existing C fact. A pure policy
  statement goes in `reasoning.weighing`, not in K."
- **Pick one trace option.** With C's own trace, the minimal-pair partner is `self`, which is eval-only, so "follows
  both" can't be measured in training and the partner is a d = 0 copy item. Fix: "T1: the revised trace is always
  C's restyle, so the minimal-pair partner is the `relevant` restyle pair."
- **The hand-up cap on source-gold arms** (augmented, decoy, self, none) can only be met by dropping items. Say:
  "subsample to the cap and report what was dropped."

## 15. Smaller contradictions and stale pointers

- The PDF card (p. 14) carries `move`, `irreversible` and `to:` on options. Design §9.3 calls the served card "the
  PDF card" yet strips `move`/`irreversible` (§5.1, R52), and says nothing about `to:` (a hand-up target, which
  reveals a hand-up option). Because the PDF wins on conflicts, this needs a ruling recorded in the reconciliation
  file. Add: "strip `to:` too (Peter to confirm)."
- PDF secondary metrics (p. 26): "% incorrect irreversible decisions" and "% ask a human" are missing from design
  §13.3. Both can be computed from backend tags; add them to W6.
- Brief test command covers only `code/pipeline code/bench`. W6 changes `ServedCase`, which `harness/`, `library/`,
  `eval/`, `scorers/` and `training/` tests use. Run all of `code/`.
- Design header points to `docs/pipeline-system-flow.v4.html`, which doesn't exist (v1–v3 only).
- CLAUDE.md "Where things are" still says `code/{eval,harness,inference,training}` are empty.
- Brief W2 says "hand-up cap per arm"; design §7.4 says per arm **and per intent within arm**. Pick one.
