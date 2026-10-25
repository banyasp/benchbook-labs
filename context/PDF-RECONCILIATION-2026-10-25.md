# Reconciling the code, examples and data with Research Plan v0.4

*2026-10-25. Peter ruled the **Research Plan v0.4 PDF** (`context/Benchbook-Research-Plan-v0.4.pdf`) the ground
truth. This lists every place the other material disagrees with it. "Fix" is the change that brings the item in
line with the PDF; **ASK** marks items Peter must decide because the PDF is silent, says "still in development",
or conflicts with one of his later decisions.*

## Peter's rulings (2026-10-25)

- **B8 → verdict `choice`.** Tool calls are out of scope (future work: they test say/do, not analogical reasoning).
- **C1 → greedy** assignment, as in the PDF.
- **B7 and the overall reward → TBD**; Peter will define how the scorers combine. Scorers stay separate until then.
- B6 stands as written: nothing after `not_governed` is scored.

## A. The v7 worked example (`context/schema/benchbook-analogical-pipeline-example-v7.yaml`)

It is the same journalist/raft example as the PDF (pp. 14-18), but the names follow an earlier draft.

| # | PDF v0.4 | v7 yaml | Fix |
|---|---|---|---|
| A1 | Steps 4+5 are one block, `kind: fact_enumeration` (frame, facts, options) | `kind: discretization` | Rename |
| A2 | Fact mapping buckets: `matched`, `corresponding`, `live_only`, `case_only` | `matched`, `altered`, … | `altered` → `corresponding` |
| A3 | Consideration mapping buckets: `matched`, `corresponding`, `live_only`, `case_only` | `carried`, `revised`, … | `carried` → `matched`, `revised` → `corresponding` |
| A4 | Applicability: `frame`, `governs`, `why` | adds `decisive_in_case` | **ASK** keep it as optional or drop |
| A5 | Verdict: `choice, course, relation, decisive, now, flip_conditions` (no confidence, no via) | adds `confidence: 0.8`, `via: null` | Drop `confidence` (also Peter's Oct decision). `via`: see B5 |
| A6 | Equities list: civilian_life, mission_effect, source_protection, lawful_authority, **resource_stewardship** | swaps resource_stewardship for **partner_relationship** | **The PDF example is inconsistent with itself**: LIVE-C6 uses `partner_relationship`, which its equities list does not inject. **ASK** add partner_relationship to the PDF's list (keep resource_stewardship?) |
| A7 | Case served as `case: {id: REF1, …}` | `kind: case, ref: REF1, library: {…}` | Compatible: `library` is authoring metadata stripped before serving |

## B. `reward_v2.py` (`context/reward/v2/`) — built for a pre-v0.4 reply, does not run on PDF-format replies

| # | PDF v0.4 | reward_v2 | Fix |
|---|---|---|---|
| B1 | Reply = a sequence of YAML documents, one per step, each with `kind:` | Merges fenced YAML blocks by top-level key; `SECTIONS = facts_enumeration, facts_mapping, consideration_mapping, reasoning, verdict` | **Every PDF-format reply would fail the gate** (multi-document YAML / repeated `kind`). Rewrite the parser to split on `---` and key by `kind` |
| B2 | Separate `consideration_enumeration` and `applicability` steps; `governs` in applicability | No consideration enumeration (considerations inline under `consideration_mapping.from_case[].live` and `de_novo`); `governs` read from consideration_mapping | Restructure the gate to the PDF's steps |
| B3 | Buckets as in A2/A3 | facts `matched/altered/case_only`; considerations `carried/revised/absent` + `de_novo` | Rename and re-key (considerations referenced by id from the enumeration) |
| B4 | No confidence | Gate requires `confidence` in [0,1]; calibration term on every branch | Remove both |
| B5 | Verdict has no `via`; the agent's own `flip_conditions` cite the case's (e.g. "that is REF1-flip1") | `flips` must name a `via` would_change item or the gate fails | **ASK**: (a) score `flips` by relation only; (b) read the cited REF flip id from the verdict's flip conditions; (c) add `via` to the schema |
| B6 | (silent) | After `not_governed`, scores the decision for *invariance* (option C, +0.5·invariance) | **Conflicts with Peter's Oct decision**: not_governed ends the reasoning and nothing after it is rewarded or punished (option A; the consolidated v3 section agrees). Remove the invariance term |
| B7 | "Weighted sum of the outputs, **multiplied by the (0,1) schema gate**" (still in development) | Gate failure = −3, plus tier bands | **ASK.** Note: with a multiplicative gate a malformed reply scores 0, which beats any wrong answer that scores below 0, so the policy learns to emit broken YAML when unsure. A fixed negative for a failed gate avoids that |
| B8 | Scores the **verdict's choice**: translate the option id → exact match | Scores the **tool calls** against hidden option signatures (from the Oct 1 training plan; tool calls are not in the PDF) | **ASK**: choice label, tool calls, or both with a says/does consistency gate (reward_v2 has that gate) |
| B9 | Scoring table (pp. 23-24) covers: schema validator; facts enumeration (ENUM_GRADER); frame articulation ×3 (Jev_Noul); options enumeration; frame mapping ×3 (exact match); facts mapping and consideration mapping (translate → SET_COMPARE); consideration enumeration (ENUM_GRADER + SET_COMPARE); applicability (exact); verdict choice, course (Jev_Noul), relation, decisive (SET_COMPARE), now (ENUM_GRADER), flip conditions (ENUM_GRADER). Reasoning and applicability-why are not scored | Scores action, extra calls, relation, "differences" (case-side ids only) and calibration | **Not built anywhere yet:** frame articulation and course (Jev_Noul), frame-mapping exact matches, `now`, flip conditions, options enumeration. Facts/considerations enumeration and the mappings are in `observe_v2` (see C) |

## C. `observe_v2.py` (fact and consideration alignment) — closest to the PDF

Already uses the PDF bucket names (`matched / corresponding / live_only / case_only`) and the two-pass Jev
Choice + geometric-mean design of Fig. 6. Two differences:

| # | PDF v0.4 | observe_v2 | Fix |
|---|---|---|---|
| C1 | **Greedy** assignment in descending order of geometric means (p. 21, Fig. 6 3B) | Optimal one-to-one assignment (Hungarian, `linear_sum_assignment`) | **ASK.** They differ only when greedy picks a locally best pair that blocks a better overall matching. Switch to greedy to match the PDF, or update the PDF |
| C2 | Score = Σ found·w_found − Σ extra·w_extra, normalized by \|G.T.\|; conflated-but-present facts get their own (lower) reward (Fig. 6 footnote) | Weighted F1 with soft credit from the "none" answers; hallucinated facts count double | **ASK.** Same intent, different formula |

## D. The data (`examples-v21/`, `data/draft/B001/`, schema v2.6) vs the PDF's case and reply

| # | PDF v0.4 | v2.6 data | Consequence |
|---|---|---|---|
| D1 | Case has a `facts` list with ids (`REF1-F1…`, kind, status) and considerations that cite fact ids and an `equity` | No facts list; each consideration carries its fact as inline text and a `value` from 28 shared values; options are letters A-D; prose under `judgment`, boundaries under `boundaries` | **The PDF's fact mapping needs case fact ids, which v2.6 cards don't have.** Convert the cards (LLM-assisted, then validate) or regenerate them |
| D2 | Harness injects an equities list | Per-consideration `value` | Map the 28 values to equities; define an equities list per deployment |
| D3 | Golden reply = the 11-step sequence | Replies are the v2.6 `mapping` (frame / fit / compare / new / carry / decide) | Existing replies can't serve as SFT targets or answer keys. (They are Claude-drafted, so eval-only anyway) |
| D4 | The answer key holds the gold facts, fact mapping, considerations, consideration mapping, applicability and verdict fields | Live gold holds choice, acceptable, option_map, relation, planted changes, option signatures | Enough to score the **choice/action** today. Not enough to score the reasoning steps: those answer keys must be generated |
| D5 | Traces: not constrained by the PDF | TRACE-FORMAT v2.6 | No conflict |

**For today's untrained eval this is fine:** it scores the choice/action on the existing traces. Everything that
scores the reasoning, and all SFT, needs PDF-format cases, golden replies and answer keys.

## E. Corrections to the 2026-10-25 handoff (applied; old versions in `versions/`)

- Pipeline and bucket names now follow the PDF, not v7.
- Policy model: **Granite 4.2 8B primary, Qwen3.5 9B as the comparison** (PDF p. 18-19). My earlier
  recommendation of Qwen as primary contradicted the PDF.
- Distance: the PDF's evaluation sketch (p. 28) defines distance by **perturbation axes** — add or remove facts,
  revise a fact, inter-fact influence, the option set, authority/role. Structural distance from planted
  perturbations is now primary; embedding distance is secondary.
- Arms now follow the PDF's grid (no reference / relevant case / augmented case or scenario / decoy) × with or
  without the analogical-reasoning prompt (Checkpoint 2).

## F. In later docs, not in the PDF, but not contradicting it (kept unless Peter says otherwise)

Authorship rule (training data only from allowlisted open-weight models); revised-card control (the PDF's
"augmented case"); domain-transfer families and a held-out domain; tier bands; process credit; extra-call penalty
(the PDF's "small negative reward for superfluous actions").
