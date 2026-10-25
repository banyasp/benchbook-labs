# Benchbook data pipeline — design v2.1 (draft for Peter's review, 2026-10-25)

*v2.1 adds §4a (getting beyond lookup) and §10 (tonight's critical path vs deferred work). v2.0 is in
`context/versions/`. Risks and assumptions are logged in `docs/RISK-REGISTER.md` (ids R*/A*/I* below).*

*Supersedes v1 (`DATA-PIPELINE-DESIGN-v1.md`, kept). Built from Peter's whiteboards of 2026-10-25 ("Data
Operators"; trace / case / answer decomposition) and the discussion around them. Ground truth for formats is the
Research Plan v0.4 PDF. Nothing here is built until Peter approves it; then it becomes workstream 2f.*

## 1. The thesis, stated as the data problem

A values oracle **O** (the practitioner at the edge: the deployer's SME) answers scenarios. The human has paid for
O on a case C, giving A_C, but not on the live scenario T. The policy π must produce
**verdict(π(T, C)) = verdict(O(T))**. Its reasoning may differ from O's, because it sees T through C; its verdict
should not. Training teaches the generalization from A_C to A_T.

The data pipeline exists to manufacture (C, T, gold) triples where the gold is O's answer to T, obtained without
asking the policy's own kind of solver to invent it.

**Assumption to record:** for a pair, A_C and A_T come from the same oracle (one value system). Pairs across value
systems are the later pluralism experiment, not training data.

## 2. Notation

- **R**: the raw corpus (immutable sources, addressed by span ids).
- **Scenario X = (F_X, Q_X, A_X)** — the role-agnostic unit:
  - **F**: atomic facts (id, kind, status, text, span refs or `authored`).
  - **Q**: the question frame: the question, the decider and the agent's role/authority, and the options (each with
    an abstract move type and irreversibility).
  - **A**: the answer: considerations (facts → equity → favors → weight → why), reasoning, verdict (choice, basis,
    decisive), flip conditions (`would_change` with `then:`, `would_not_change`, `watch_for`), lesson, limits.
- **Roles, not kinds:** a scenario served by the harness is a **case C** (rendered as a card); a scenario rendered as
  agent context is a **trace T**. Any scenario can play either role.
- **M_{C,T}**: the mapping between C and T (facts: matched / corresponding / live_only / case_only; options map;
  considerations; applicability; relation; `via`).
- **A_{T|C}**: T's answer as reasoned through C (the policy's output at runtime).

## 3. The data operators

| Operator | Signature | What it does | Model | Gold status of what it produces |
|---|---|---|---|---|
| **extract** | R → F, Q;  then  R, F, Q → A | Build a scenario from source material. F and Q first, so A is conditioned on the facts as triaged. A takes the source's **endorsed** answer and stated reasons where they exist. | gpt-oss-120b (Bedrock) | F grounded (span refs); A's verdict `source-endorsed` if the source endorses it, else `model-solved` |
| **perturb** | X, operator → X′ | Change F (or Q) by a named operator and update A to match. | code + gpt-oss-120b | A′ verdict `by-construction` when the operator realizes a flip condition; else `model-solved` (independent: never sees any case) |
| **pair** | store → (C, T, intent) | Choose pairs with an intended relation and distance: derived pairs (T = perturb(C)), natural pairs (independent scenarios matched by structure), decoys, transfers, revised cards. Enforces balance. | code (+ structural index) | sets the pair's gold relation by construction where possible |
| **render** | R, F_T, Q_T → T (+ span map) | Write the agent trace: deployment, timeline, tool results, noise from R. | gpt-oss-120b | — (checked by gates, §5) |
| **solve** | C = (F_C, Q_C, A_C), F_T, Q_T → M_{C,T}, A_{T|C} | The dependent solver: the same function the policy performs at runtime. Used to **write the process** (mapping, considerations, reasoning) toward an **already-fixed gold verdict**, never to decide it. | base model, label-conditioned (PDF), or a larger allowlisted model if Peter allows | process text; must agree with the gold verdict, relation and `via`, or the item is reviewed |
| **project** | (C, T) pair record → card(C), T, SFT string, RLVR JSON | Deterministic views of one record. | code | — |

**Where the gold verdict for T comes from (strictly in this order):**
1. **By construction** — T = perturb(C or its source scenario) with a known effect: `follows` → C's choice through
   the options map; `flips` via w → w's `then:`; revised card C′ → C′'s answer.
2. **Source-endorsed** — T extracted from its own raw material, which states the endorsed answer.
3. **Model-solved, independent** — an independent solve of T **without C** standing in for O; tagged, sampled for
   Peter's review. This is where `distinguished` labels come from.

`solve` (dependent) is never a gold source. Disagreement between `solve` and the gold is a review signal: a bad
analogy, a case that shouldn't govern, or a bad anchor.

## 4. perturb: the operator set

Each operator declares what it changes, how A must change, and the resulting relation for the pair (C, X′).

| Operator | Changes | A′ | Relation for (X, X′) |
|---|---|---|---|
| restyle | surface wording of F and Q | unchanged | follows |
| trap | applies a `would_not_change` item | verdict unchanged | follows |
| a fortiori | strengthens the winning side | verdict unchanged | follows |
| flip | applies one `would_change` item | verdict = its `then:` | flips, `via` = that item |
| add fact | a new fact (may implicate an equity) | independent re-solve | follows or distinguished (reviewed) |
| remove fact | drops a fact | unchanged, or flip if the fact was dispositive (re-solve) | follows / flips / distinguished |
| revise fact | changes a fact's value (magnitude) | by construction if it crosses a stated flip threshold, else re-solve | follows / flips |
| option set (Q) | add / remove / reshape an option | re-solve; options map updated | by construction where the map is clear |
| authority / role (Q) | changes the decider or the agent's role | re-solve | often flips; reviewed |
| transfer | re-instantiates X's skeleton in another domain (new F, same equities in tension) | by construction from the skeleton: preserved → same move; flip analog → its move | follows / flips (Peter checks faithfulness yes/no) |
| near-miss decoy | keeps most surface facts, changes the equities at stake | independent re-solve | not_governed |
| revise card | edits A (the weighing), not F or Q | the revised verdict | (T, C′): follows C′ |

The **distance** of a pair is a function of the operators applied (axis, number of facts touched, magnitude) for
derived pairs, and of the structural signature distance for natural pairs. Store the features; weights are Peter's.

## 4a. Getting beyond lookup (Peter, 2026-10-25; risk R1)

By-construction flips and traps come straight from the card's own `would_change` / `would_not_change` lists, so
on their own they teach a lookup ("is a listed item present?"), not reasoning from the weighing. Rules:
- **Listed-item variants are a minority** of training pairs, and are realized **indirectly**: the changed fact is
  stated in different terms, in another channel, as a magnitude that crosses a threshold the weighing implies, or
  in another domain — never as a paraphrase of the list item.
- **Unlisted changes** (add / remove / revise a fact the card never mentions) are labeled by an **independent
  solve** (strongest allowlisted model, high reasoning effort, never sees C) and tagged `model-solved`. These are
  the pairs that exercise the weighing and produce `distinguished`.
- **Natural pairs and transfers** (independent scenarios matched by structure; source-endorsed or skeleton-built
  gold) carry the real test (I2).
- **Thin cards:** a share of training serves the card with flip conditions withheld, so the model must reason from
  the weighing; the same ablation at eval measures how much accuracy came from the lists.
- Results are always reported **per variant family**, so lookup performance can't hide in the average.

## 5. render, and its gates

**Output:** the trace T plus a **span map**: for every fact in F_T, where it appears in T (message index, character
range) and how it is realized (`stated` / `paraphrased` / `implied` / `split`). Also a list of the true-but-not-in-F_T
details the renderer added (the **allowed list**) and any planted look-alikes.

**Design rules:** facts spread across channels (operator messages, tool results, documents); varied explicitness;
decisive facts 10–25% of words, never highlighted or last; noise drawn from R where possible; salient and
non-salient content written in the **same register** (salient facts sometimes inside messy tool output; vivid,
important-sounding details that don't matter).

**Gates (a trace that fails is re-rendered, not kept):**
1. **Coverage:** every fact in F_T is locatable via the span map; decisive facts are not merely `implied` unless
   the operator intends it.
2. **A/B test with a reference solver** (a strong model, not the policy): solve from (T, C) and from (F_T, Q_T, C).
   Different verdicts → the render lost information (Peter's cause 1) → re-render. If the reference solver gets it
   and the policy later doesn't, that's the policy's extraction weakness (cause 2), the training signal.
3. **Salience probe:** a cheap classifier on surface features only (sentence length, position, register, message
   type, formatting) predicting which sentences carry F_T facts, trained per batch. Accuracy well above chance →
   style is leaking salience → re-render that batch with style-matching.
4. Leak scan (no option labels, no gold, no case text in the trace); word bounds.

## 6. The answer record and its projections

One **pair record** per (C, T): pair intent and relation, gold verdict and its source tier, M_{C,T}, gold F_T with
weights (facts behind decisive considerations ×2), the allowed list, Q_T gold (question, decider, role, options
with hidden ids), `via`, the solve output (process) and its agreement flags, provenance.

- **SFT string** = the PDF's generated steps, `kind:` documents (or inside `<think>`, per the mode Checkpoint 2
  selects), live ids numbered in trace order from the span map.
- **RLVR JSON** = the same record without reasoning and applicability-why; keeps `governs`, relation, `via`.
- **Scoring F_T** is precision/recall, not exact match: the model's enumeration is legitimately case-conditioned.
  Recall against gold F_T (weighted); precision penalizes only facts absent from the trace (hallucinations) at full
  weight, and padding lightly; allowed-list items are neutral.

## 7. extract in detail (the ingestion half)

Stages, each with an artifact and a gate:

| Stage | Artifact | Gate |
|---|---|---|
| Registry | `registry/sources.yaml` (from `context/sources/source-catalog.csv`) | public; license recorded |
| Acquire | `raw/<sha256>` + `.meta.json` (fetched from the EC2 box; manual drop where blocked) | hash recorded; immutable |
| Normalize | `docs/<sha12>.jsonl`: text with span ids `src:<sha12>#p<page>.<para>[a:b]` | span ids stable on re-run |
| Find episodes | `episodes/`: candidate decision points (several per document allowed), scored | in safety scope; score ≥ threshold; rejects kept with reason |
| Extract F, Q | facts with span refs; the question frame as the source presents it (human decider) | grounding check: a judge confirms each span supports its fact |
| Extract A | considerations, reasoning from the source's own stated reasons, the endorsed verdict and who endorsed it (`basis`), flip conditions only where the source states counterfactuals | verdict grounded; every authored field tagged |
| Cast for an agent | agent role and authority, option set rewritten as a **matched set** (same length and specificity, real option included) | only when the decision's structure carries over; option-specificity baseline at chance |
| Derive | `skeleton` (tension, decisive + conditions, move structure, authority shape) and `world` (actors, timeline of when each fact becomes known and through which channel, artifacts with source quotes) | schema-valid |
| Review | Peter rules on sampled holdings and model-solved labels | `approved` |

Incidents covered by several sources are clustered into one **family**; splits are assigned per family (and one
whole domain held out) at this point, before any perturbation.

## 8. Storage and ids

As in v1 §5–6, renamed: `data/raw/`, `data/docs/`, `data/episodes/`, `data/scenarios/<family>/<X>.yaml` (each with
`F`, `Q`, `A`, `skeleton`, `world`, `provenance`, `status`, `lineage`), `data/pairs/<pair-id>/` (pair record, trace,
span map), `data/exports/<version>/{sft,rl,eval}`. Global ids for scenarios and their facts/considerations/options;
served and rendered views renumber (`REF1-…`, `LIVE-…`) with stored translation tables. Every artifact records input
hashes, operator, model id and prompt version.

## 9. Open questions for Peter

1. First sources and the held-out domain.
2. Who writes the SFT process text in `solve`: the base model (PDF) or a larger allowlisted model?
3. Distance weights per operator axis.
4. Where your ≤5 h of review goes: holdings, model-solved labels (`distinguished`), or transfer faithfulness.
5. Equities: the 28 values, or a shorter deployment-facing list per deployment?
6. Can a single rendered trace be paired with several cases (one served at a time)? (Recommended: yes — that is how
   decoys and revised cards reuse one trace.)

## 10. Tonight's critical path vs deferred work (Peter, 2026-10-25)

**Goal:** one thin path from raw sources to SFT/RLVR/eval records, end to end, tonight. Robustness analyses are
logged in `docs/RISK-REGISTER.md` and built after the path works.

**Critical path (build now):**
1. **Scenario store** (`data/scenarios/`) seeded with the 10 converted pilot scenarios (eval-only) plus new
   extractions.
2. **extract** on 3–5 public sources → 6–10 scenarios (F, Q, A) with span refs; endorsed verdict + `basis`;
   options as a matched set; family id and split assigned. Gate: schema validation and span refs present.
3. **perturb**, three operators: `restyle`, `flip` (realized indirectly, §4a), `add fact` (independent re-solve).
4. **pair**: derived pairs + decoys (unrelated scenarios); cap hand-up golds per arm (R7).
5. **render**: trace + span map (emitted now, gated later).
6. **solve**: label-conditioned process text toward the fixed gold (PDF: the base model, Granite, if passing the
   format verifier; fallback gpt-oss-120b).
7. **project**: SFT jsonl, RLVR JSON, Inspect samples, using the 2a schemas and 2d scorers.
**Done when:** ≥20 pairs flow end to end, load in the SFT builder and the scorers, and Peter has read 3 of them.

**Deferred (logged, built after):** grounding judge (span supports fact), A/B render test (R3), salience probe
(R4), verbatim check (R5), option-specificity baseline gate (R6), two-solver agreement (R2), thin-card training
share (R1), natural-pair matching via the structural index, transfer operator, review UI, judge validation set
(R13), oracle-consistency audit (A1).

**Models:** extract / perturb / render / independent solve on Bedrock gpt-oss-120b (high reasoning effort for the
independent solve); judge = Jev (OpenRouter); solve = Granite on the local server when the GPU is free.
