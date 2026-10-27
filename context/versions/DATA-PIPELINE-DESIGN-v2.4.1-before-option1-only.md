# Benchbook data pipeline — design v2.4.1 (2026-10-27)

*v2.4.1: amended the same day after an independent cold review (`docs/reviews-design-v2.4-2026-10-27.md`):
thin cards scoped to non-flip pairs, splits, augmented = flips only, decoy filter and loss mask, trace store,
filter details, headline cells. v2.4 as first written: `context/versions/DATA-PIPELINE-DESIGN-v2.4-before-review.md`.*

*Status: **approved design.** Built from Peter's step-by-step walkthrough of the pipeline (2026-10-26/27) and his
answers of 2026-10-27. It supersedes v2.3 (kept at `context/versions/DATA-PIPELINE-DESIGN-v2.3-before-walkthrough.md`).
Ground truth for formats is the Research Plan v0.4 PDF; where this file and the PDF disagree, the PDF wins, and
the known differences are in `context/PDF-RECONCILIATION-2026-10-25.md`. Hypotheses: `docs/HYPOTHESES.md`. Risks:
`docs/RISK-REGISTER.md`. v2 items: `docs/V2-PRIORITIES.md`. Tomorrow's work order: `BUILD-BRIEF-v2.4-2026-10-27.md`.
Diagram: `docs/pipeline-system-flow.v4.html`.*

**How to read the labels.** Each rule says where its data lives:
- **[backend]**: stored in the pipeline, never shown to any policy model;
- **[served]**: in the policy's prompt (trace, equities, card);
- **[trained]**: in an SFT target or the RLVR gold.

Each rule also has a build tier:
- **T1**: build tomorrow, before the 150+ pair batch;
- **T2**: build after the first training run;
- **v2**: later (`docs/V2-PRIORITIES.md`).

A rule Peter didn't explicitly set is marked **(default; Peter may override)**.

## What changed from v2.3

- **SFT writer.** SFT targets come from **rejection sampling Granite** (no gold in the prompt). The gold-informed
  teacher the box built becomes an alternative writer, kept for the forgetting comparison (R48). §10.
- **Arms.** There are now six: `relevant`, **`augmented`** (the PDF's: the case's facts altered so its conclusion flips,
  built by reversing flip pairs), **`revised`** (C′: the case's judgment edited), `decoy`, `none`, and `self` (the d = 0
  anchor). **Both `augmented` and `revised` are in training and eval** (Peter, 2026-10-27). The near-neighbor arm
  moves to v2. §7.
- **Options are plain-text courses of action, not tools.**
  - They carry no justification, are matched in form and are discoverable in the trace.
  - Each option's discovery channel is recorded and balanced. Recommendations in traces are sometimes wrong.
  - The policy's options are aligned to gold by Jev Choice. An answer that matches no gold option is scored **off-menu**.
  - §5.1, §8, §12.
- **Episodes.** Episode criteria are pass/fail, and rejects are kept with their reason. Every scenario carries a `content_domain` tag and a
  `refusal_sensitivity` flag. A fallback router handles false-positive refusals only. Incomplete
  extractions go to their own store. §4.
- **Skeleton and conditions.** The skeleton gains `question_type`, a `decisive` list and `decisive_mode`. **Conditions are
  backend-only:** they choose which facts perturb changes, and are never served or trained on. §5.3, §6.2.
- **Flip realization.** It is a tunable mix (`indirect_share`), replacing "never paraphrase". **The R49 render rule:** every relevant fact is
  readable in one hop. §6.3, §8.3.
- **Mapping terms.** "Buckets" is the term for both fact and consideration mappings. "Counterpart" is defined separately. §6.4.
- **Gold tier.** It is defined and used for reporting, review and filtering. §9.2.
- **Thin cards.** Lesson and limits stay on the full card and are withheld, together with the flip conditions, on the
  thin card. §5.2, §9.3.
- **Proxy objective.** The model should faithfully extend the case (R\*), not out-guess the oracle. §1.
- **Natural pairs** move to v2 as the top priority. §7.6.

## 1. The thesis as a data problem

A values oracle **O** (the deployer's practitioner) answers scenarios. The human has paid for O on case C, giving A_C,
but not on the live scenario T. The policy π reads T through C, and its verdict should match **R\*_C(T)**: the
faithful extension of C's own reasoning to T.

**Peter's ruling (2026-10-26).** The model should faithfully carry out the reasoning shown in the case. It should not
try to guess the oracle beyond what the case supports. Where faithful extension and O(T) disagree, that is a
**library gap** (add or rewrite a case), not a training target. Corollary for case authors: state priorities and how
sensitive they are ("would weigh heavily against…"), not rigid if-then rules.

The pipeline manufactures (C, T, gold) triples. The gold is either R\*_C(T) by construction, or O(T) from a source or
an independent solve that never sees C. It never comes from a solver that has seen C. **v1 serves one case per
trace** (sets of cases are v2).

**Assumption A1:** within a pair, A_C and A_T come from one value system. Pairs across value systems are the
later pluralism experiment.

## 2. Notation

| Symbol | Meaning |
|---|---|
| R | the raw corpus (immutable sources, addressed by span ids) |
| X = (F, Q, A) | a **scenario**, role-agnostic. F = atomic facts; Q = question frame (question, decider, agent role and authority, options); A = answer (considerations K, reasoning W, verdict V, flip conditions Φ, lesson, limits) |
| C, T | **roles**, not kinds: a scenario served as a case (card), or rendered as a trace. Any scenario can play either role |
| E, E_d | the equity registry (ids and glosses) and one deployment's injected subset |
| skeleton | [backend] structural summary of X (§5.3) |
| Δ | perturb's exact record of what it changed. For a derived pair, Δ *is* the gold mapping |
| M^F, M^K | fact and consideration mappings between C and T (buckets plus counterparts, §6.4) |
| τ, σ, α | the rendered trace, its span map, its allowed list (§8) |
| G | the gold record for a pair, assembled by code only (§9) |
| Y | an SFT target: the policy's full reply in the PDF step format (§10) |
| d(C, T) | structural distance, computed from structured YAML to structured YAML, never from traces (§7.5) |

## 3. The pipeline at a glance

| # | Stage | Operator | Model | Output | Built? |
|---|---|---|---|---|---|
| 1a | acquire, normalize | — | code | `data/raw/<sha256>`, `data/docs/<sha12>.jsonl` | built |
| 1b | find episodes | — | gpt-oss-120b (Bedrock) | candidate decision points, pass/fail, rejects with reasons | **T1 new** (today: hand-picked seed) |
| 2a | extract F, Q | extract | gpt-oss-120b | facts with span refs; the frame; a matched option set | built; **T1 changes** |
| 2b | extract A | extract | gpt-oss-120b | K, W, V (endorsed), Φ, lesson, limits, `basis` | built; **T1 changes** |
| 2c | derive | derive | gpt-oss-120b | skeleton, world kit | **T2 new** |
| 3a | perturb | perturb | code + gpt-oss-120b | X′ plus Δ | built (restyle, flip, add_fact); **T1 changes** |
| 3b | A′ | (inside perturb) | by construction, or independent solve (gpt-oss-120b, high effort, never sees C) | X′'s answer and gold tier | built |
| 3c | pair | pair | code (+ gpt-oss-120b for `revise_card`) | pair records, one per (C, T, arm) | built; **T1: arms, augmented, revised, self** |
| 4 | render | render | gpt-oss-120b | τ, σ (facts + options), α | built; **T1 changes** |
| 5a | assemble gold | — | code only | G | built; **T1 changes** |
| 5b | harness prompt | — | code | prompt per arm × card view × AR prompt × equities | built; **T1 changes** |
| 6 | SFT writer | solve | **Granite 4.2 8B** (vLLM), rejection sampling | accepted Y, tagged | **T1 rebuild** (today: teacher) |
| 7 | project | project | code | SFT jsonl, RLVR jsonl, Inspect samples | built; **T1 changes** |

## 4. Ingest (1a, 1b)

### 4.1 Acquire and normalize (1a) — agreed, built

- **Raw bytes** are the original downloaded file: immutable, named by content hash: `data/raw/<sha256>` with
  `.meta.json` (URL, fetch time, license). Never edited.
- **Normalize** writes `data/docs/<sha12>.jsonl`, one paragraph per line. Each paragraph has a span id
  `src:<sha12>#p<page>.<para>`, plus an optional character range `[a:b]`. Span ids are stable on re-run.
- Public material only. If a site blocks fetching, say so and use another source; never work around a block.

### 4.2 Find episodes (1b) — T1

gpt-oss-120b reads a normalized document and lists its candidate **decision points**. Several per document are
allowed. Each candidate carries:
- its span range;
- the decision in one line;
- the criteria results, **pass/fail** per criterion (no numeric score);
- `content_domain` and `refusal_sensitivity`.

**Episode criteria (all must pass):**
1. A decider faces a real choice among at least 2 courses of action.
2. The source states or clearly implies the chosen course.
3. The source gives reasons.
4. The decision is at the level of decision ethics, law or policy.

**Rejects are kept** in `data/store/episodes/rejected.jsonl`, each with the criterion that failed.

**Safety scope, tagging and the fallback router** (Peter, 2026-10-26):
- **[backend] Tag, don't discard.** Every episode and scenario carries `content_domain` (e.g.
  `security-clearance`, `gov-ethics`, `use-of-force-policy`, `intel-oversight`, `cyber-policy`) and
  `refusal_sensitivity: low | medium | high`. Decision-level content about, for example, *whether* to employ force or
  under what authority is in scope. Tag it `high`; do not drop it. **The goal is learning which equities to weigh and
  why.** Generation stops at the decision and nothing is executed.
- **Out of scope (unchanged, CLAUDE.md):** operational *technique*. That means how to employ a weapon, target,
  intrude, collect, or communicate covertly. An episode whose decision can't be stated without technique fails
  criterion 4. Strip technique details from facts; keep the decision.
- **Fallback router.** It applies **only to false-positive refusals of in-scope decision content**. When a model refuses
  a step on such content (Bedrock `stopReason` / content filter, or a refusal-shaped reply), re-send that step
  once to a configured fallback provider and record both attempts in provenance. It is never used to get around a refusal of
  out-of-scope content. Refusal detection and recording are T1; the router is T2, before natsec sources are added.

### 4.3 Incomplete candidates — T1

When extraction can't complete a scenario, nothing is thrown away:
- Everything that was extracted is saved to `data/store/incomplete/<family>/<id>.yaml`, with
  `missing: [<field paths>]` and the failure reason. Example: A failed, or F has fewer than 4 grounded facts.
- Incomplete records are never paired, rendered or trained on until they are completed and pass the gates.

## 5. extract (2a, 2b) and derive (2c)

### 5.1 F and Q, with the option rules (2a)

- **Facts** [served via render; trained as F_T]:
  - each fact has `{id, kind, status, fact}` and cites span ids;
  - unsourced facts are listed in `provenance.authored` (at most a third);
  - people are named by office, never by personal name (T1: add a check; the v0 export leaked a judge's name).
- **Options** (Peter, 2026-10-26) [served on the card; trained via `fact_enumeration.options` and the options map]:
  - **Actions only. No justification, rationale or "because…" in the option text.**
  - Each option is a **complete course of action** (what is done, by whom, to what end), not a fragment.
  - **Matched set:** all options, the real one included, have similar length, grammatical form and specificity (R6, R33).
  - **[backend] `move` and `irreversible` are tags, not option text.** Strip them from the served card (T1); they are
    used for balance, stakes weighting and the hand-up cap.
  - Order is shuffled with a seed; the gold position is balanced in `pair` (§7.4).
  - **Opposite disposition (R58).** Source answers are mostly the `act` move (e.g. deny), with authored `ask` /
    `hold` / `partial` distractors, so "pick the act option" would score well. Every set must include the opposite
    disposition as an `act` option too (grant vs deny; disclose vs withhold).
  - **`to:`** (a hand-up target) is also stripped from the served card, since it reveals a hand-up option. The PDF
    card (p. 14) carries `move`, `irreversible` and `to:`, so this departure is recorded in the reconciliation file
    (**Peter confirmed, 2026-10-27**).

### 5.2 A (2b)

- **Considerations K** belong to A [trained]: `{id, facts[], equity, favors[], weight: strong|weak|bar, why}`.
  Equities are E ids. In the live reply, K_T is the gold for `consideration_enumeration` (this answers Peter's "within
  F or A?": in the stored scenario it lives in A; in the reply it is enumerated after the fact mapping).
- **Verdict** [trained]: `choice` (the endorsed option), `basis`, `decisive` (a **list** of consideration ids).
- **Flip conditions Φ** [served on the full card]: `would_change {id, if, then, why}`, `would_not_change`,
  `watch_for`. Use the source's stated counterfactuals where they exist; otherwise write them and tag them `authored`.
- **Lesson and limits** [served on the full card]: kept. They are not the flip conditions. The lesson is the take-away
  principle; the limits are its stated boundaries. Each carries provenance (`stated` vs `authored`). **Both are
  withheld on the thin card** (§9.3).
- No source-narration phrases in case prose ("The source emphasizes…"; R40).

### 5.3 derive: skeleton and world kit (2c) — T2

**[backend] skeleton** (Peter approved the format):
```yaml
skeleton:
  question_type: <e.g. grant-or-deny | act-now-or-wait | disclose-or-withhold | delegate-or-decide>
  tension: [<equity id>, <equity id>]          # the equities in conflict
  decisive: [<consideration id>, ...]         # one or more
  decisive_mode: each_necessary | cumulative  # backend only
  conditions:                                 # hinges in the weighing; backend only (§6.2)
    - {id, on: <consideration id>, hinge: <prose>, target_fact_state: <what F would have to say>}
  move_structure: <shape of the option set, e.g. act / partial / hold>
  authority_shape: <who may decide what>
```
- `each_necessary`: every decisive consideration is needed for the verdict.
- `cumulative`: the decisive considerations decide together, by weight.

**World kit** (for render, T2): actors, a timeline of when each fact becomes known and through which channel,
artifacts with source quotes, and a noise pool drawn from R. Until T2, render uses the source paragraphs as
texture, as built.

## 6. perturb (3a, 3b)

### 6.1 What perturb may change

**perturb changes only F or Q, never the reasoning.** The case's decision process stays fixed. The answer
follows from that rule:
- **By construction** when the change realizes a flip the case states (`would_change` → its `then:`) or leaves the
  answer untouched (restyle, trap, a fortiori). Tier `by-construction`.
- **Otherwise by an independent solve** (gpt-oss-120b, high effort). The solver sees only F′, Q′ and E, **never C or A**.
  Tier `model-solved`. Peter expects most unlisted changes to need it. `distinguished` labels come from here.

### 6.2 Conditions are backend-only

`skeleton.conditions` are **never served and never in SFT or RLVR targets**. They are used only to **choose which
facts an operator changes**. Each condition becomes a *target fact state*, and the operator is parameterized with it
("make F7 say the loss is unrecoverable"). Until the skeleton exists (T2):
- `flip` parameterizes from `would_change` items, as built;
- `add_fact` picks its mode at random, as built.

### 6.3 Operators

| Operator | Changes | A′ | Relation (C, X′) | Status |
|---|---|---|---|---|
| restyle | surface wording of F and Q | unchanged | follows | built. **T1:** reject numeric drift in decisive facts (R43) |
| flip | applies one `would_change` item | its `then:` | flips, `via` = that item | built. **T1:** `indirect_share`; regularize X′'s Φ (R35) |
| add fact | an unlisted new fact | independent solve | follows / distinguished | built |
| trap | applies a `would_not_change` item | unchanged | follows | T2 |
| a fortiori | strengthens the winning side | unchanged | follows | T2 |
| remove / revise fact | drops a fact, or changes its magnitude | by construction if a stated flip threshold is crossed, else independent solve | follows / flips / distinguished | T2 |
| option set, authority/role (Q) | reshapes options or decider | independent solve | often flips | T2 |
| transfer | the skeleton in another domain | from the skeleton | follows / flips | v2 |
| near-miss decoy | keeps surface facts, changes the equities | independent solve | not_governed | T2 |
| **revise_card** | edits A (the weighing), never F or Q | the revised verdict | (C′, T): follows C′ | **T1 new** (§7.3) |

**Flip realization: `indirect_share`** (Peter, 2026-10-26: allow "some paraphrase").
- A tunable fraction of listed-item flips is realized **indirectly**: in other terms, through another channel, or
  by placement (the built path: content-word recall ≤ 0.5, longest shared run ≤ 2 words, plus a model
  verify). The rest are realized as a **paraphrase** of the `would_change` item.
- **Default `indirect_share = 0.7` (default; Peter may override).**
- Record `realization: indirect | paraphrase` in Δ.
- Results are always reported per realization and per operator family, so lookup can't hide in the average (R1).

**Flipped scenarios that will be served as cards** (the augmented arm, §7.2) must not look flipped (R35).
- Keep X′'s `would_change` count equal to X's. Drop a vacuous item, then add a non-vacuous authored one.
- Keep the touched consideration's weight distribution the same as untouched ones.
- X′ must carry a **back-flip item** whose `then:` is X's choice (the box's re-pointing already does this; verify it).

### 6.4 Δ: every operator emits the gold mapping

For a derived pair the operator knows exactly what it changed, so Δ contains:
- for every C fact: its **bucket** and its **counterpart**;
- the T facts it added (`live_only`);
- the same for considerations, with `role`;
- the options map;
- applicability (`governs`), relation and `via`;
- the touched condition or item;
- `realization`;
- the distance features.

- **Bucket** = *which category* an item falls in: `matched` (same in both), `corresponding` (a counterpart with a
  different value or wording), `live_only`, `case_only`. "Buckets" is the term for both facts and considerations;
  "handling" is retired.
- **Counterpart** = *which specific item* on the other side it pairs with. Only `matched` and `corresponding` have one.

## 7. pair (3c): intents, arms, balance, distance

### 7.1 Pair records

One record per (served case, trace, arm). Its fields:
- `intent` (what the pair is built to exhibit: restyle / flip / add_fact / augmented / revised / decoy / self);
- `arm`;
- lineage, options map, split, gold tier, `card_view` (§9.3);
- the G fields (§9).

**One rendered trace may be paired with several cases**, one served at a time. That is how the augmented, decoy, self
and reverse-restyle pairs reuse traces at no render cost. So traces live in a **trace store keyed by the trace
scenario**: `data/store/traces/<trace-scenario-id>/` holds trace.json, σ, the option channels and `recommended_option`.
Pairs reference a trace and never copy it. No reordered T copies (they would need new renders). **Pair id =
hash(C, T, intent, arm, card_view).**

### 7.2 Arms (Peter, 2026-10-27: augmented and revised in both training and eval)

| Arm | Served case | Trace | Gold | Tier | Train | Eval |
|---|---|---|---|---|---|---|
| `relevant` | C (source scenario X) | T = perturb(X) | from Δ | per operator | yes | yes |
| `relevant`, intent `reverse_restyle` | restyle(X) | X's own trace | X's answer; `follows`; all matched | X's tier | yes | no (test traces are used by `self`) |
| `augmented` (PDF) | **X′ = flip(X)** (T1; add_fact-derived augmented is T2) | X's own trace | O(X), X's endorsed choice; relation `flips` via X′'s back-flip item (by construction); mapping = Δ inverted | X's tier (`source-endorsed` for extracted X) | yes | yes |
| `revised` | C′ = revise_card(C) | **the trace of restyle(C)** (T1) | C′'s choice through the options map; relation `follows` | by-construction (`revised-authored` tag) | yes | yes |
| `decoy` | a scenario of another family whose equities don't overlap T's: consideration-equity Jaccard ≤ 0.2 and no shared decisive equity (same domain allowed). **Domain alone never makes a decoy**: cross-domain cases can govern; that is the thesis | any trace | `not_governed` only; the verdict after it is never trained (§10) | T's tier | yes (≤ 3 uses per decoy card) | yes; the choice is scored for PDF falsifier 3 |
| `none` | no card | any trace | T's own answer | T's tier | no | yes |
| `self` | card(X) | X's own trace | X's answer; all matched; d = 0 | X's tier | no | yes (anchor for H4 at C\* = T; ceiling) |
| `near_neighbor` | a retrieved, non-optimal case | — | — | — | — | **v2** (needs the structural index) |

- **Augmented** is the PDF's "exemplar case with case facts deliberately altered so that the conclusion should flip".
  The trace-side flip (the PDF's "other direction") is the `relevant` flip pair. One flip gives both directions.
  Gate: run flip's condition-holds verifier on X′'s back-flip `if` against **X's rendered trace**; drop the pair on
  failure. X's trace states X's own fact, so augmented pairs are tagged `realization: direct` and never pooled with
  indirect flips.
- **Reverse-restyle** exists so that source traces don't appear in training only with `flips` (augmented) or
  `not_governed` (decoy) answers. Otherwise, trace provenance would predict the relation.
- **Name clash.** In the Checkpoint 2 code and results, arm `augmented` meant the revised card. Rename it `revised` there
  (schema migration plus a note in the results).
- **C\* in v1.** For by-construction derived pairs, the source case C attains the gold. So C is the C\* estimate, and
  `relevant` measures AR_C\*(T). The cost of a worse case is measured at its extreme by `decoy` now, and by
  `near_neighbor` in v2.

### 7.3 `revise_card` (new, T1)

Code picks a target choice ≠ C's choice. The pick is balanced by move, and hand-ups count toward the cap. gpt-oss-120b
then writes A′ for C:
- it re-weights or re-prioritizes considerations, or adds one consideration. **An added consideration must cite ≥ 1
  existing C fact**, so it can be enumerated from the trace. A pure policy statement ("the deployer now weighs X above Y")
  goes in `reasoning.weighing`, not in K;
- it updates the reasoning, the verdict and Φ;
- **F and Q are unchanged.**

Gate: schema-valid; verdict = target; Δ_K lists every consideration whose weight or favors changed.

Gold for (C′, T):
- M^F as in (C, T);
- K_T = C′'s considerations carried onto T's facts;
- choice = C′'s choice through the options map.

**The T1 revised trace is always restyle(C)'s trace.** So the minimal-pair partner is the `relevant` restyle pair: one
trace, two cards, two answers. The model must follow the card, not its prior. The copy-the-case baseline is 100% on
revised by construction, so revised accuracy is never read as reasoning. Report
the pair-level "follows both" rate (H4 axis 2, online edits). C′ judgments are stipulated, not an oracle's, so tag them
and report them separately (R54).

### 7.4 Balance

All balance is computed from the **pair's gold choice** (`PairRecord.choice`), never from the trace scenario's own
verdict, because they differ for `revised`.
- **Hand-up cap: ≤ 1/3 hand-up golds (`ask`, `refuse`) per arm** (default; Peter may override). It was per intent; T1
  makes it per arm and reports it per intent. The default stance is autonomy (R7). Arms whose gold is the source's
  answer (augmented, decoy, self, none) can only meet the cap by dropping items: subsample, and report what was dropped.
- **Position** now means two things, both balanced and reported:
  - the gold option's first-mention rank in τ (from σ.options), since the trace is not a menu;
  - the card-order position of the gold's counterpart on the served card.
- **Channels and recommendations belong to the trace**, but one trace has different golds in different arms. So
  channels are a seeded random permutation per trace, never conditioned on which option is gold. That makes the
  channel independent of the gold in every arm. `recommended_option` is picked per trace (≈ 50% of traces carry one),
  and the recommended-is-gold rate is reported per arm, not controlled.
- **Decoy reuse:** any one card serves as a decoy in at most 3 training pairs (R57).

### 7.5 Distance d(C, T) — computed, not served

From G, structured YAML to structured YAML. Weights are Peter's; this is the default formula until he sets them:
- d = 1 − Σ w·s / Σ w, over the union of fact and consideration items;
- s = 1 for `matched`, 0.5 for `corresponding`, 0 for `live_only` or `case_only`;
- w = 2 for items behind decisive considerations, else 1;
- add 0.1 per frame field (question, decider, role) that is not `same`, and cap d at 1.

Under this formula, restyle and self come out at about 0, and decoys at about 1. Store the raw features with it, so any
other weighting can be recomputed.

### 7.6 Natural pairs — v2, top priority

These pair independently sourced scenarios matched by structure. They have no Δ, so they need a model mapping step
with verification, plus the structural index. They carry the source-endorsed O(T). See `docs/V2-PRIORITIES.md` #1.
The H3 pilot (§13.4) uses a few natural pairs now, scoring verdicts only.

## 8. render (4)

### 8.1 Output

- The trace τ, in `examples-v21/templates/TRACE-FORMAT.md` form, ending at the decision point with the harness
  injection.
- The span map σ, with two parts:
  - `facts`: for each fact, `{fact, message, start, end, realization: stated | paraphrased | implied | split}`;
  - **`options`**: for each option, `{option, message, start, end, channel}`.
- The allowed list α: true details not in F_T. α items are neutral in scoring.

### 8.2 Options are text, not tools; discoverability

Peter's rulings, 2026-10-26:
- **Options are not tool definitions.** The policy enumerates them as plain-text courses of action in
  `fact_enumeration.options`. Jev Choice aligns them to the hidden gold option ids.
- **Every option must be discoverable in the trace, and never as a menu.** It can appear in:
  - the agent's scope or authority stated in the system prompt;
  - operator or colleague messages;
  - tool results;
  - attached documents.

  Options and recommendations are buried in the trace. No numbered list of all options appears anywhere.
- **[backend] Discovery channel per option.** Code assigns each option a channel before rendering, by a seeded
  random permutation per trace that never looks at the gold (§7.4, R51). Render records it in σ.
- **Recommendations are sometimes wrong.** In a share of traces (default 50%), someone recommends an option. The
  option is picked per trace at random among all options, so it is the gold in some arms and not in others. Record
  `recommended_option` in the trace store, and report the recommended-is-gold rate per arm (R50).

### 8.3 Render rules

- **R49, v1 rule (severe limitation).** Every decision-relevant fact is readable from the trace with **at most a
  single-hop reading**: no arithmetic and no multi-step combination. Indirectness comes only from wording, channel or
  placement, never from computation. The fix (token space for derived facts) is v2 #2.
- Facts are spread across channels. Decisive facts are 10–25% of words and are never highlighted or placed last.
- Salient and non-salient content use the same register. Noise comes from R where possible. No verbatim runs of 8+ words
  from F.

### 8.4 Gates

Diagnostics already logged (coverage, leak words, verbatim runs, decisive share). **T1 makes three of them gates:**
1. every decisive fact and every option is located in σ;
2. leak scan: no option ids or labels, no menu shape, no gold, and no text from the **A part of any card that will be
   served with this trace** (verdict, reasoning, Φ, lesson, limits). Facts are excluded, because restyle, self and
   augmented cards restate the trace's facts by design; the 8-word verbatim rule against T's own F covers them;
3. no person names.

Deferred (T2): A/B render test (R3), salience probe (R4), single-hop check on decisive facts (R49).

## 9. Gold and the harness prompt (5a, 5b)

### 9.1 G is assembled by code only

G =
- F_T with weights (facts behind decisive considerations ×2), from T's F, σ and the decisive links;
- α;
- Q_T with hidden option ids;
- M^F, K_T, M^K, from Δ (inverted for `augmented`; with C′'s K for `revised`; all matched for `self`;
  all unmatched for `decoy`);
- `governs`, relation, `via`, V_T;
- the gold tier;
- `recommended_option` and the option channels;
- d and its features.

No model writes any part of G *at assembly*: G is a join. **The never-saw-C rule covers the verdict, relation, `via`
and `governs`.** For flip and add_fact, K_T, `decisive` and M^K were composed by the perturb model with C in view.
Their provenance is tagged `composed-with-C`. For `model-solved` pairs, the SFT filter therefore drops the
consideration-bucket condition (§10). A model writes Y, and Y is kept only if its structure matches G.

### 9.2 Gold tier [backend]

`gold_tier ∈ {by-construction, source-endorsed, model-solved}` records where the gold verdict came from.
- `by-construction`: a stated flip, an untouched restyle, or a revised card. It measures **R\*_C(T)**. (An augmented reversal keeps X's own tier, because its verdict is X's answer.)
- `source-endorsed`: the source states the answer. It measures **O(T)**.
- `model-solved`: an independent solve that never saw C. It **estimates O(T)**.

Uses:
- accuracy is always reported per tier;
- Peter's sampled review goes mostly to `model-solved`;
- training can be filtered or weighted by tier;
- on pairs with both labels, O-vs-R\* disagreement estimates A-O2.

The tier is separate from the SFT-sample tag `rationalized`. The tier is about the answer; the tag is about the training text.
Pilot imports are Claude-drafted cases; tag them `eval-only-import` and report them apart (R42).

### 9.3 The harness prompt

The prompt is τ + E_d + the served card for the arm + an optional analogical-reasoning prompt. One function builds it for
eval, SFT and RL.

**`card_view`:**
- `full`: the PDF card;
- `thin`: the flip conditions, lesson and limits are withheld, so the model must reason from the weighing (R1).

**Thin cards apply only to pairs whose gold relation is `follows` or `distinguished`** (restyle, add_fact, revised,
reverse-restyle). Pairs whose gold is `flips` (relevant flips, augmented) are always served `full`. The gold `via`
names a `would_change` item, which a thin card hides, and without Φ `flips` and `distinguished` can't be told apart.
A thin card also removes every flip-condition reference (`REF…-flip*`, `noflip*`, `watch*`) from the reasoning prose,
and the leak gate checks that none remain. Peter agreed to this scoping on 2026-10-27, plus a T2 **eval-only
thin-flip set** (flip pairs served thin; gold `distinguished`, no `via`) to measure lookup directly (§16.5).

**Thin share:** 0 in the first SFT run (for speed), then 30% of eligible training items (default; Peter may override).
`card_view` is assigned per training item (seeded) **before** sampling. Eval runs both views on eligible `relevant` pairs.

**AR prompt in training:** on for 50% of training prompts (seeded), so the AR-off eval cells are not out of
distribution. Served cards never carry `move` or `irreversible` tags, conditions, the skeleton, the gold tier or provenance.

**Equities ablation (eval only):** E_d on/off × card none/relevant, run for the base and SFT models.

## 10. The SFT writer (6): rejection sampling Granite

Peter's ruling of 2026-10-25 (evening). The box's current gold-informed teacher becomes an alternative writer.

1. **Generate.** Granite 4.2 8B (the vLLM server) writes Y in the PDF step format (`kind:` documents; `via` in the
   verdict) in **reasoning mode C** (structure inside `<think>`; the most accurate mode in Checkpoint 2, and C/C′ parse best;
   default, Peter may override). The prompt contains the harness prompt plus **two worked examples**:
   - the PDF journalist/raft transfer example (pp. 14–18);
   - a same-domain flip (v6 example converted to PDF names).

   The second example's path is `ideas/benchbook-analogical-pipeline-example-v6.yaml`. **No gold in the prompt.**
   **N = 8, sampled adaptively:** 4 first, then 4 more only for items with no accepted sample. `max_tokens` is 8000,
   with vLLM prefix caching on.
2. **Filter** against G with the 2d scorers, cheapest first:
   - **(a) exact:** align options (Jev Choice). Then the choice, relation, `via` and `governs` must match. Translate served
     ids (`REF1-flip2`) to global ids through `ServedCase.table` before comparing `via`.
   - **(b) only on survivors:** align facts (greedy plus Jev Choice) and considerations
     (`scorers.alignment.align` on equity + why + cited fact texts). Then:
     - **fact bucket agreement** = agreeing gold items / **all** gold items (unaligned gold items count as
       disagreements) ≥ 0.7;
     - weighted fact recall ≥ 0.6;
     - every decisive fact in the right bucket;
     - consideration buckets ≥ 0.7 with decisive considerations right. **This condition is skipped for
       `model-solved` pairs** (§9.1).

     All thresholds are defaults; Peter may override them.

   Log every sample's sub-scores, so thresholds can move without re-sampling.
3. **Rationalize.** Pairs with zero accepted samples get one pass with the gold choice, relation and `via` (served ids) as a hint,
   filtered the same way and tagged `rationalized`. **Tomorrow's first SFT run includes them, tagged** (default
   for speed); the without-rationalized run is the first ablation.
4. **Log** acceptance per arm, intent, family, tier and card view (R27, R45). Pick one accepted sample per item, at
   random among those with the best sub-score.
5. **Alternative writer** (R48 two-writer comparison): the built teacher (gpt-oss-120b, sees gold), tagged
   `writer: teacher`. Not in the default export.

**Not governed:** for `decoy`, Y ends at `applicability: governs: false` followed by a verdict. Nothing after
`not_governed` is scored or trained. The filter checks only `governs` and relation. In SFT, **the loss mask ends at
the end of the `applicability` document**: the verdict stays in the text, with labels −100.

**The SFT prompt is the plain harness prompt for the item**: no worked examples and no rationalize hint. Those are
for sampling only. Check that prompt + Y fits `max_length`, because `sft_lora` drops longer rows silently; log any drops.

## 11. project (7)

- **SFT:** prompt (masked) + Y. Loss only on Y; for decoys, only up to the end of `applicability`. **Mode C** (pass it
  explicitly; `project_pair` defaults to B). Meta: pair, arm, intent, relation, tier, writer,
  card view, `rationalized`, d, realization, family, split.
- **RLVR:** prompt + G as JSON, without reasoning prose or applicability-why. Keeps `governs`, relation and `via`.
- **Eval (Inspect):** one sample per (pair, arm, card view, AR prompt, equities cell) + G.

## 12. Scoring notes the data must support

- The decision is scored from `verdict.choice` (tool calls are future work). Options are aligned by Jev Choice.
- **Decoys:** in eval only, the decoy `verdict.choice` is scored against T's own answer, for PDF falsifier 3 (decoy vs
  none). It is never a training signal.
- **Off-menu:** a choice that aligns to no gold option is wrong for choice accuracy and is also reported as its own rate.
- Fact matching is greedy (PDF p. 21). F_T is scored for recall (weighted) and precision. Hallucinated facts count fully
  and padding lightly; α items are neutral.
- No `confidence`. After `not_governed`, nothing is scored. The reward function is Peter's; every scorer stays a
  separate function.

## 13. Evaluation design (v1)

1. **Grid:** models {base, SFT} (SFT+RL when ready) × arms {none, relevant, augmented, revised, decoy, self} ×
   AR prompt {on, off} × card view (on relevant and augmented), plus the equities cells.
2. **Headline:** choice accuracy vs d(C, T), with 95% CIs. Four curves:
   - **base + none**;
   - **base + relevant** (the harness);
   - **SFT + none**;
   - **SFT + relevant**;
   - SFT+RL later.

   Cells: AR prompt on, full card, mode C. The x-axis is the relevant pair's d; `none` rows are plotted at their
   trace's relevant-pair d. `self` is the d = 0 point. Augmented, revised and decoy go in the **by-arm graph**, not the
   curve; revised items would pile up at d ≈ 0. The within-family curves (R56) sit beside it. Always break results down
   by intent, realization, tier and family. The held-out domain is a separate panel.
3. **Baselines and controls:**
   - copy-the-case's-verdict, split by intent (follows vs flips);
   - always-hand-up; always-`act`; majority disposition per domain (R58);
   - PDF secondary metrics: % incorrect irreversible decisions, % ask a human;
   - accuracy conditional on the gold option being enumerated (R29);
   - revised minimal-pair "follows both" rate;
   - decoy vs none (PDF falsifier 3);
   - AR(T) via the `none` arm (falsifier 2).
4. **H3 pilot (runs now, in parallel):** tests A-O2 before training.
   - Take 15–30 DOE OHA decisions that cite an earlier OHA decision as controlling or analogous.
   - Extract both decisions: C from the cited one, T from the citing one.
   - Have a frontier stand-in on Bedrock (gpt-oss-120b, plus a second model family; require agreement) extend C
     to T, and answer T without C.
   - Report agreement with O(T), with and without C, by a coarse distance band (same issue and guideline vs
     different).
5. **Splits** (assigned before any perturbation; the box's current rule puts ~1 family in test and must change):
   - every episode from one source document shares that document's family;
   - within each training domain, families are sorted by sha256: ~20% go to test (at least 5 families), ~10% to dev, the
     rest to train;
   - **one whole source domain is held out**: all of its families go to test;
   - pilot imports are eval-only;
   - **every eval item, in every arm, uses `test` or `eval-only` traces and cards only.** Assert that no eval trace shares
     a lineage root with any train pair.

## 14. Storage and ids (as built)

- **Store:**
  - `data/raw/`, `data/docs/`;
  - `data/store/registry/`;
  - `data/store/episodes/` (T1);
  - `data/store/incomplete/` (T1);
  - `data/store/scenarios/<family>/<id>.yaml`;
  - `data/store/partials/`;
  - `data/store/pairs/<pair-id>/` (pair.yaml, trace.json, span map, solve samples).
- **Exports:** `data/exports/<version>/{sft,rl,eval}`.
- **Separate:** `data/cases/` and `data/scenarios/` belong to Checkpoint 2; leave them alone.
- **Writes:** every write versions the old file.
- **Ids:** global ids are stored. Served and rendered views renumber them (`REF1-…`, `LIVE-…`) with stored translation tables.
- **Provenance:** every artifact records input hashes, operator, model id and prompt version.

## 15. Defaults set in this version (Peter may override any)

| Default | Value | Where |
|---|---|---|
| `indirect_share` | 0.7 | §6.3 |
| Hand-up cap | ≤ 1/3 per arm | §7.4 |
| Distance formula | §7.5 | §7.5 |
| Recommendation share / recommended-is-gold | 50% / 50% | §8.2 |
| Thin cards | non-flip pairs only; share 0 in run 1, then 30% | §9.3 |
| AR prompt in training | 50% | §9.3 |
| N | 8, adaptive (4 + 4) | §10 |
| Fact recall floor in the filter | 0.6 | §10 |
| Decoy filter | equity Jaccard ≤ 0.2, no shared decisive equity, ≤ 3 uses per card | §7.2 |
| Split | ~20/10/70 per training domain, ≥ 5 test families; one domain held out | §13.5 |
| SFT reasoning mode | C | §10 |
| Bucket-agreement threshold | 0.7 over all gold items, decisive items exact | §10 |
| Rationalized samples in the first SFT run | included, tagged | §10 |
| Off-menu | wrong + reported separately | §12 |
| Revised pairs | trace = C's own or its restyle | §7.3 |

## 16. Open with Peter (non-blocking)

1. Distance weights (§7.5) and the reward function.
2. Where his ≤ 5 h review goes. Proposed: `model-solved` labels first, then the revised-card judgments.
3. Spot-checks: DR-AUT-001 (`then: ask` mapped to hold), DR-INT-301-r1, DR-AGT-201; and the three example pairs
   from the 2f run (box applies the advice: reject P-1217d16660; keep P-7b3fe9966f as a paraphrase-realized flip).
4. Legal opinions as a training domain (R26); a stronger SFT writer (R23/R48); the equities list per deployment.
5. *(Resolved, Peter 2026-10-27.)* **Thin cards and flips (§9.3):** v1 applies thin cards only to non-flip pairs.
   Right after the first run (T2), add a small **eval-only thin-flip set**: flip pairs served thin, gold relation
   `distinguished` with no `via`, so the model must see from the weighing alone that the change matters. This is the
   direct lookup-vs-reasoning measure (R1).
6. *(Resolved, Peter 2026-10-27: the served card strips `move`, `irreversible` and `to:`; split by decision with a held-out domain, §13.5, agreed.)*
7. **H4 at C\* = T:** Peter's words are that the harness does *better* than the fine-tune there; at minimum it matches.
