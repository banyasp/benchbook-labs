# Audit of the Claude Doc "Benchbook Exemplar Schema — Adversarial Review and v7 Proposal" (2026-09-30)

Doc read in full (rev 14). Paths below are relative to `pkg/schema-review-2026-09-30/` unless absolute. Every script was run on a scratch copy (`/tmp/audit`). The package itself was not changed: `diff -rq` finds no differences apart from caches.

**What reproduces exactly.**
- `./run_tests.sh` → `84 passed`.
- `python3 doha_study.py` regenerates `results/doha-v3.md` byte-identically.
- `review/redteam/run_all.sh` regenerates `outputs.txt` identically.
- `python3 hc_eval.py` gives the doc's per-case Hard Calls table: 27/33 atoms, 13/33 without π, 16/21 flips.

**Numbers that check out** (no action needed):
- 96/100 and 88/90 (`review/redteam/outputs.txt` 227–229).
- 31/100 and 21/100 (outputs 237, 251).
- 139/318 and 318 in all (outputs 223).
- C 49 / B 43 / A 2 (outputs 219–220).
- 23/80 (REDTEAM 173).
- 10/10, 9/10 and 1-NN 8/10 (doha-v3.md).
- 0.83, 1.83 vs 2.50, +1.0 vs −0.5, 0.167/0.042, 1.000 vs 0.989, 0.850/0.872, ±1.25 (REDTEAM).
- 0.67 (RT-7a).
- 49% = 144/293 (strand 27 L42).
- 210/318 = 66% (strand 27 L217).
- 28% (strand 27 L219).
- 99 of 100, 3.3 (3.27), 85 (strand 27 L201–202).
- A tempting in 80 (strand 27 L225).
- 8 of 36 = 22% (round-1 log L313).
- 6 minutes per case (round-1 log L329: 36.7/6 = 6.1).
- Chance level 1 in 3.6 (36 cases have 3 options and 64 have 4).
- The DOHA table rows shown.
- The per-case Hard Calls table.
- The stakes table and p* formula (`solver_v3.py` 22–24, AUT.yaml).
- The AUT-001 vs AUT-101 COMPARE line: `S.compare` returns distinguished, significant [DEP-A1, DEP-A3], and DEP-B2@even is covered.
- ICD 403 §E.14 (FACTCHECK 23.28).
- Horty 2021 Definition 9 (2b): I checked it on the page image of the uploaded PDF. It is the overlined Premise(r) ⊩ W, on p. 282.

The findings follow, most important first.

---

## 1. The AUT-101 end-to-end exhibit does not reproduce as stated

- **Section:** 8, "AUT-101, end to end". The same problem affects the mapping example in section 7.
- **Doc text:** "Served only AUT-001 (a different precedent), with π = {A: 0.3, B: 0.7}, the solver composes the record's gold plan exactly".
- **Problem:** This is false under the stated conditions.
  - Served only AUT-001, no card settles PREP, and the mapping gives no π for PREP. So the harness routes PREP (`inform`) and only proceeds on it as an interim step.
  - The DEP route recommends B, but the gold says `recommend: null`.
  - Result: 2 of 4 gold atoms match, 1 is missing, 2 are extra and 1 has an attribute mismatch.
  - The passing test does something different. `tests/test_aut.py` 15–28 serves AUT-101's own PREP holding plus AUT-001, with no π.
  - AUT-001 has no effect on the plan. With no cards at all and the same π, the DEP atoms are identical. The authority gate and π decide everything here.
  - The section 7 mapping therefore shows a PLAN ("proceed PREP A") that its own READ/SETTLE blocks would not produce.
- **Evidence:** in `/tmp/audit/code`, `S.compose(aut, cards_from_record(AUT-001), situation(AUT-101), {"DEP":{"A":0.3,"B":0.7}})` → `plan_diff` gives:
  - missing `[('proceed','PREP','A',None,False)]`
  - extra `[('route','PREP','B'), ('proceed','PREP','A',interim)]`
  - attr `recommend: (None,'B')`

  Serving no cards at all gives the same DEP atoms.
- **Fix, section 8 replacement:** "**AUT-101, end to end.** With AUT-101's own PREP holding served alongside AUT-001, and no π, the solver reproduces all four gold atoms (tests/test_aut.py). AUT-001 is distinguished on the missing DEP-A1 and DEP-A3 (DEP-B2@even is covered) and changes nothing. Departure is routed to the master because the pre-delegation's trigger is unmet, whatever any precedent says. Preparation proceeds because AUT-101's own holding settles it."
- **Fix, section 7:** add `PREP pi = {A: 0.9, B: 0.1}` to SETTLE. Also either add `recommend: B` plus `hidden_resolution: {DEP: B}` to the AUT-101 gold, or drop "(recommend B)" from PLAN.

## 2. The Hard Calls results are in-sample, and mostly not from precedent

- **Section:** 8, "Six Hard Calls converted to v7"; also section 11, decision 1.
- **Doc text:** "Each record was served to itself, with π set to the author's hidden resolution … Totals: 27/33 atoms and 16/21 flips. Every mismatch traces to a named spec gap".
- **Problem:** The doc states the method but not what it implies. The test is circular in four ways:
  - One converter wrote every catalog "with these very cases in front of me. That flatters the schema" (round-1 log L11; round-2 log L232).
  - Spec v2 adopted 20 of the converter's 28 constructs (round-2 log, Appendix B).
  - Each record is its own precedent.
  - π is the author's own answer.

  An ablation shows how little the precedent layer contributes. I served no cards and kept π = hidden:

  | Case | Atoms matched, no cards |
  |---|---|
  | AUT-102 | 3/5 |
  | AUT-103 | 6/8 |
  | REL-105 | 4/5 |
  | INT-109 | 4/6 |
  | ANL-107 | 3/5 |
  | AGT-106 | 1/4 |
  | **Total** | **21/33** |

  The gate alone (no cards and no π) gives 9/33. So self-served precedent accounts for 6 of the 27 matched atoms.
  - The six cases' selection is not documented. "Six of six decomposed" is not a sample estimate.
- **Evidence:** the ablation script in the audit notes (it uses `S.compose_record` over `hc_eval.load`). Its totals are `with cards 27/33`, `no cards 21/33`, `cards, no pi 13/33`, `no cards, no pi 9/33`.
- **Fix:** add after the table: "Read this as a consistency check, not a test. One converter wrote the catalogs with these cases open, the spec was amended to fit them, each record is served to itself, and π is the author's own answer. Without any precedent card, 21 of 33 atoms still reproduce; the authority gate alone gives 9. The test is the order-of-work step 2 run on unseen AUT cases."
- **Fix, order of work step 2:** tighten the gate to "serve *other* records' cards, report strict (no π) and hidden side by side, and stop if hidden < 80% **or** if removing the cards changes fewer than a stated share of atoms".

## 3. Strongest objection from a skeptical AI-safety researcher, not addressed

- **Section:** 5–9 as a whole.
- **Doc text:** "The model's two irreducible jobs, reading a messy situation and resolving what precedent leaves open, get their own blocks."
- **Objection:** Under v7 the trained model supplies tags and a probability. The deployer's catalog and the harness decide who acts; the catalog supplies direction labels, tiers, floors and prohibitions. Every safety property the doc claims holds in the harness whatever the model learned:
  - no autonomous act above role;
  - computed escalation;
  - "nothing that arrives as data confers authority".

  So: what does training change in the model's own dispositions, and how would anyone know? v6 named "the real test of transfer" as prose exemplars with no catalog (`src/proposal/benchbook-sections-v6.md` L241). The doc never says what happens to that condition under v7. v7 makes it harder to define, because routing now depends on catalog authority tables that a prose-only condition lacks.

  Items 1–2 show the concern is live: on AUT-101 and the six Hard Calls, the gate plus π reproduce most of the gold without precedent. The model's own PLAN block is never read by the reward (item 10). Only 9 of 21 flips pass without π (item 7). The doc's closing line ("routing can't be farmed") gestures at this but does not quantify or test it.
- **Fix:** add a short subsection "What the model contributes" with the ablation from item 2. Add a falsifier row: "A2 with the harness removed (the model's own PLAN, scored atom by atom against gold) is no better than A1 → the reasoning lives in the harness, not the model." Score the model's PLAN block against the harness plan. Keep a no-catalog prose condition and say how its gold is routed.

## 4. Strongest objection from the formal AI & Law side (Horty, Prakken, Bench-Capon), not addressed

- **Section:** 6, design rule 3 ("Precedent binds per issue"); section 8, rules 3.3 and 3.5.
- **Doc text:** "Holdings attach to binary issues, not option bundles."
- **Objection 1, separability.** v7 assumes issues are separable: each issue is compared, supported and composed alone. In the reason model a precedent's priority ordering is derived from its whole fact situation.
  - v7's issues are carved out of 3–4 prose options by one converter, not taken from a domain theory. In IBP or ANGELIC-style issue models, the Restatement or statute fixes both the issues and the rule that combines them.
  - The schema has a `coupling` field, but only one rule exists in any catalog (catalog-REL L75–76, REL→TEAR). The solver only *reports* violations (`solver_v3.py` 924–931). The lint "one issue and one side per factor" forces factors that bear on two issues to be assigned to one.
  - AUT-101 shows the cost. The preparations "shorten his run", so PREP bears on whether holding is safe, yet PREP and DEP are solved independently.
- **Objection 2, what constrains.** In Horty's model every decided case contributes a priority ordering. v7's `permitted` holdings "only license" and never constrain, which discards constraint the model would derive. Meanwhile compiled flips, which are authored counterfactuals and not decisions, enter the case base as near-miss cards at rank −0.5. Their conflicts end "bounded at equal rank" (r2-results issue 10).
- **Fix:** add a limitations paragraph that states the separability assumption. Require catalogs to declare `coupling` and enforce it as a compose constraint, not a report. Define what a permitted holding constrains, for instance through Horty's consistency test on the case base. Keep near-miss cards out of the case base until an ablation shows they help. That matches the doc's own "v7.1, run it as an ablation first".

## 5. "Closes every red-team solver counterexample" and "Fixed" overclaim

- **Section:** 8 lead; section 5 table; section 9 lead; section 3 row M8.
- **Doc text:**
  - "Solver v3 passes 84 tests, closes every red-team solver counterexample"
  - "Reward exploits (C1, C3, M5–M7) | Fixed | Fixed"
  - "The reward keeps v6's shape and closes its exploits."
- **Problem:**
  - RT-6 is still open. `tests/test_redteam.py` L99–103 reads: "CHANGED / STILL OPEN … the two readings still give opposite actions … 'which rung sufficed' is an author judgment no lint can check".
  - RH-4 (M6) is "partly STILL OPEN". Flagging still beats acting whenever P(own tags right) < 0.80, down from 0.855 (L213–217).
  - RT-7b's answer changed from escalate to hold (L131–136).
  - The v6.1 column's "Fixed" is a projection for code that does not exist.
- **Fix:**
  - Section 8: "…resolves every red-team solver counterexample except RT-6 (the rung convention is stated and linted, but which rung sufficed stays an author judgment, and the two readings still give opposite actions)".
  - Section 5 row: "C1, C3, M5, M7 addressed; M6 narrowed (flag break-even 0.855 → 0.80)" in the v7 column, and "would be addressed (not built)" in the v6.1 column.
  - Section 9: "…closes C1, C3, M5 and M7 and narrows M6".

## 6. Decision 3's number is wrong

- **Section:** 11, decision 3; section 8, "Holding force".
- **Doc text:** "13 vs 27 of 33 gold atoms computable without π".
- **Problem:** 27/33 is *with* π = hidden resolution, not without π. I re-ran the no-π reading with every holding set to `required`: it reproduces **20/33**, not 27. INT-109 falls from 2/6 to 0/6, REL-105 rises to 5/5 and ANL-107 to 4/5. Holding force is therefore not the whole story, and the causal "because" in section 8 is overstated.
- **Evidence:** a probe on `hc_eval.load` records with every `force` set to `required`, `compose_record(..., pi=None)`. Totals: 13 as-is, 20 all-required, of 33.
- **Fix, decision 3 "What depends on it":** "Without π: 13/33 atoms as converted; 20/33 if every holding were `required` (probe). With the author's π: 27/33."
- **Fix, section 8:** "Without π, only 13/33 atoms reproduce. Most holdings are marked `permitted`, which never forces; marking all `required` raises this to 20/33 but breaks INT-109."

## 7. "16/21 flips met" hides that most outcome flips pass only when π is set to the answer

- **Section:** 8, the Six Hard Calls table and totals.
- **Doc text:** "Totals: 27/33 atoms and 16/21 flips."
- **Problem:**
  - For outcome clauses, hc_eval judges a flip with π set to the clause's own outcome (`hc_eval.py` L49–55, L77–78). Without π, only **9/21** flips are met. r2-results reports this (L57: "16/21 (9 without π)"), but the doc drops it.
  - Six of the 16 "met" flips have the wrong addressee, and addressees are not counted (r2-results L77).
  - Two failures are converter readings, not spec gaps (AUT-102 x3 hand trace; ANL-107 x1 flag clause, r2-results L69–74). So "Every mismatch traces to a named spec gap" holds for atoms only.
- **Fix:** "Totals: 27/33 atoms; 16/21 flips with π set to each flip's expected outcome (9/21 without π; 6 of the 16 name a different addressee). Every missing *atom* traces to a named spec gap; two flip failures are the converter's hand-trace errors."

## 8. The DOHA headline credits v3 with a one-line patch's result, under a disabled gate

- **Section:** 8 lead and DOHA table; section 1 ("Recommendation").
- **Doc text:** "halves wrong autonomous acts on real DOHA data".
- **Problems:**
  - The run uses a study delegation that switches the authority gate off. Under the records' real role (`recommend`), every item routes to the judge (`results/doha-v3.md` L7–8). The doc never says this.
  - v3-r2's SEAD 4 row (3/10, 28/200, 2/200) is identical to the red team's one-line per-equity patch of solver_v2 (REDTEAM L160–163). So the gain belongs equally to v6.1.
  - The counts are tiny: 4 → 2 events, and both remaining events are the same over-tag in two cases.
  - The table compares v2 on SEAD 4 only with v3 "with the doctrine factors". It omits v2 + doctrine (5/10 · 5/5, 40/230, 3/230) and v3-r1 + doctrine (3/10, 32/230, 1/230).
- **Fix, section 8 lead:** "On the DOHA pilot (10 cases, authority gate switched off by a study delegation), v3 gives 2 wrong autonomous acts in 200 one-tag perturbations against v2's 4, and decides one fewer case. That is exactly what the red team's one-line per-equity patch achieves, so the gain is available to v6.1 too."
- **Fix, table:** add the two doctrine rows for v2 and v3-r1.

## 9. The "authority as a gate" headline over-reads the data

- **Section:** 1 ("Authority"); 2 ("Two parties", "Authority as a weight"); 3 (M10); 5 ("Escalation").
- **Problems:**
  - **49%.** It counts reason factors whose *drafter-assigned equity label* is authority- **or process**-type (strand 27 L42). That includes `record_integrity`, `classification_integrity`, `due_process` and `vendor_constraint`. When the six cases were converted by hand, only 8 of 36 factors (22%) turned out to be gates. The doc reports both numbers and never reconciles them.
  - **"In practice authority works as a gate computed from stakes."** This comes from the command literature (CDE, ROE), not from the Hard Calls.
  - **"Route atoms in 83 winners" and "Still an option letter in 83 winners."** A route-to-named-human atom is in 52 winners; 83 is route **or** notify/flag (strand 27 L34).
  - **"The compromise usually wins: C in 49, B in 43, A in 2."** Letters are not compromises. Strand 27 finds only 20 textbook compromises (L204) and treats the 55 C and D winners as the compromise set.
  - **Hand coding.** 3.3, 85, "A tempting in 80" and 28% are one agent's hand coding, and 28% is a 100-flip sample (95% CI 20–38). The atom vocabulary was built from the same texts (strand 27 L11, L209). The doc presents all of them as measured.
- **Fix, section 1:** "About half of reason factors (144/293) carry an authority- or process-type equity label. When six cases were converted, 8 of 36 factors turned out to be gates rather than weights. Command doctrine treats authority as a gate; v7 follows it."
- **Fix, sections 3 and 5:** "83 winners contain a route or notify atom (52 a route to a named person)".
- **Fix, section 2:** "The first-listed option almost never wins (A in 2 of 100)". Tag the hand-coded figures "(one coder)".

## 10. The core premise "the yes/no questions inside a bundle do recur" has thin support

- **Section:** 2, "Two parties"; section 6, rule 3; section 11, decision 1.
- **Doc text:** "a whole bundle almost never recurs. The yes/no questions inside a bundle do recur."
- **Problem:** No measurement backs this for domain issues.
  - In the six conversions, 12 distinct issues fill 16 slots. Ten appear once; only TELL (4 cases) and HDC (2) recur (round-2 log §9.2).
  - The CORE regex finds "tell/report" options in 58 cases, but halt and preserve-vs-destroy in only 7 each (round-2 log L39, lower bounds).
  - Per-issue precedent is only worth its cost if issues recur.
- **Fix:** "Some do: a 'tell the owner plainly' option appears in at least 58 of 100 cases, halt and preserve-vs-destroy in at least 7 each. In the six conversions, 10 of 12 issues appeared once. Whether domain issues recur is the first thing the AUT pilot (order of work, step 2) must show."

## 11. The reward and mapping sections disagree with the code

- **Section:** 7 (mapping table, "every scored line"); 9 (formula, "Isomorphic permutation"); 6 (rule 5).
- **Problems:**
  1. **Formula.** The doc's r omits two terms the code uses: `flag_cost` and an A7 plan-atom F1 term `w_plan = 0.25` (`reward_v2.py` L3, L16, L298–320). The section 9 table also has no plan row.
  2. **PLAN block.** The model's PLAN block is never read: `reward_v2.py` has no `m["plan"]`, and r_plan uses the harness plan. A model-written block with no consumer breaks the doc's own rule 5 ("Every field has a named consumer, or it goes").
  3. **SETTLE's question.** "The question left" in SETTLE is not scored anywhere (`reward_v2.py` has no `question` or U*). Yet the mapping table lists "U* from the solver" as its check.
  4. **Permutation scope.** The doc says permutation covers "option letters, side letters, factor IDs, entity names, and the order of facts and cards". `permute_v7.py` L1–3 does side letters, factor IDs and order only. Condition IDs pass through (L24–26); there are no entity names or option letters. So "gap exactly 0" was measured on a narrower permutation. It is also expected by construction for a symbolic solver.
- **Fix:**
  - Section 9: r = G(w_read r_read + w_who r_who + w_cmp r_cmp + r_act + w_cal r_cal + w_plan r_plan + r_flag) + (1−G) r_fail, and add a table row "r_plan | — | F1 of plan atoms, harness plan vs gold (w 0.25, prototype choice) | A7".
  - Section 7: either score PLAN against the harness plan or drop it from what the model writes. Say "SETTLE: π only; the question is not yet scored."
  - Section 9: "The prototype relabels side letters, factor IDs and the order of facts and cards; entity names, option letters and condition IDs are not yet permuted."

## 12. The labeling budget does not add up, and "derived" and "Done" overstate

- **Section:** 10 lead and table; 5 table; 1 ("Most of what v6 asks the labeler to write is derived instead").
- **Problems:**
  1. **"Estimate about 6–10 days of your time."** The table sums to about 9.75–14.75 working days at 8 h/day:
     - CORE ½ day plus catalogs 4–7 days;
     - Hard Calls review 16–24 h, options 3–5 h, DOHA 20–25 h, retest 3–4 h.

     Without the DOHA scale-up it is 7.25–11.6 days.
  2. **Review hours.** Section 5 says Hard Calls review is "about 20–25 h for 100 cases"; section 10 says "16–24 h".
  3. **Catalogs.** "½–1 day each, 4–7 days in all" for seven sub-areas is 3.5–7.
  4. **"Derived instead."** The conversion log shows v7 records carry *more* labeler judgment: `[JUDGMENT]` notes went from 27 to 33 and `[SILENT]` from 27 to 29 (round-2 log L202). Nine catalog entries exist only to serve flips (round-1 log L315). The doc itself says "more fields" and "a few more minutes per case".
  5. **"Done."** "DOHA pilot (10) and FISC (3) | Done" is not accurate: all 13 records still carry `found` facts in `situation`. `validate_v7.py` warns on every one: "status `found` in the situation layer (leaks the decision; P1)".
- **Fix:**
  - Section 10 lead: "Estimate about 10–15 working days of your time (7–12 without the DOHA scale-up)". Make section 5 read 16–24 h.
  - Section 1: "v7 derives watch_for, escalation and flip coverage, but each record carries more judgment calls (channels, holders, interim sides), not fewer."
  - Migration row status: "Converted to v7 shape; still tagged from the judge's findings (13 of 13 fail the decision-point rule)".

## 13. Section 3's severity count and attribution are inconsistent

- **Section:** 3 lead.
- **Doc text:** "Three critical, nine major and several minor problems. Every number comes from scripts run on your artifacts as delivered … The scripts are in review/redteam/".
- **Problem:** The table has eleven majors (M1–M11), and the red team found eight (REDTEAM L19–34; README "3 critical, 8 major, 8 minor"). M9–M11 were added from strand 27, and their numbers come from strand 27's counts and hand coding, not from `review/redteam/`:
  - 83 winners [H];
  - 210/318 [F];
  - 28% [H, sample].
- **Fix:** "Three critical, eleven major and eight minor problems. C1–C3, M1–M8 and the minors come from the red-team scripts (review/redteam/); M9–M11 come from the seed-data counts in strand 27, some hand-coded by one coder."

## 14. Sections 1, 8 and 11 disagree with each other

- **Section:** 1, 8, 11.
- **Problems:**
  1. **Which four decisions matter most.** Section 1's "biggest four" are decisions 1, 2, 4 and 10. Section 11 says "the first four decide the shape of v1", which is 1, 2, 3 and 4.
  2. **C2 filed as a reward exploit.** Section 1 lists "the longest option wins 96/100" under "Reward. Three critical exploits". It is a data leak (C2), not a reward exploit.
  3. **Laundering.** Section 8 says "Laundering … v7 now enforces it", and its 3.1 row states "Live orders authorize only if their issuer's level reaches the tier" as a rule. That is a prototype switch (`ORDER_LEVEL_CHECK`, a CHOICE). The spec v2 text says the opposite: "A live order from a holder … makes that side within_role", `SPEC-v7-v2.md` L140. Decision 5 is still open. Read literally, the spec re-opens laundering (r2-results issue 1).
  4. **Near-miss.** Section 5 defers "near-miss pair serving" to v7.1. Section 8 rule 3.3 already applies near-miss cards. These are two different things with one name.
- **Fix:**
  - Pick one set of four and use it in both places. Decision 3 (holding force) belongs in section 1, given item 6.
  - Move the 96/100 line under "Facts" or "Data".
  - "The prototype enforces this by default (a switch not yet in the spec text; decision 5)."
  - Rename the solver's version "compiled flip cards".

## 15. Literature claims that go beyond the strands or the fact-check

- **Section:** 2 and 4.
- **Items:**
  - **"Qiyās refuses to rule on the ḥikma alone … a thousand-year argument for that split".** The source is itself a review of scholars *disagreeing* on al-taʿlīl bi-al-ḥikmah, and al-Āmidī allows ḥikma when it is manifest and measurable (FACTCHECK 22.25). Say "the mainstream view refuses to rule on the ḥikma unless it is manifest and measurable".
  - **"pre-delegations fire only on stated triggers (NATO AJP-3.9)".** AJP-3.9 says targets outside delegated authority are referred back, and that proportionality is re-checked at final authorization (FACTCHECK 23.26). Say "pre-approvals cover a stated envelope and are re-checked before execution".
  - **"any level may restrict, but only the holder may permit (rules of engagement)".** For ROE supplemental measures this is right. As a general rule it is tagged [OURS] in strand 23 L103, and decision 6 shows it fails for adverse actions. Say "(ROE supplemental measures; v7 generalizes it, see decision 6)".
  - **"Mistral-7B 75.70 vs 53.27".** Add that at 13B the gain over a plain-case prompt is 2.81 points (FACTCHECK 25.10).
  - **"Knowing the outcome changes what seems relevant … (Fischhoff 1975)".** The "relevance" wording is PARTIAL/UNVERIFIED verbatim (24.30). Keep "raises judged likelihood, and people are largely unaware".
  - **"every formal model of precedential constraint we found is two-sided".** Fine, but van Woerkom 2026 is UNVERIFIED (26.3). Note that Gould & Toni's AA-CBR is multi-class but not a deterministic constraint model (strand 26 L60).
  - **"Qing bifu".** The fact-check could not attest "bifu" in any source it opened; the pages use 比照 (22.30). The term is likely right (the Qing Code's no-precise-article provision reads 引律比附), but cite that article.
  - **Raz plus Rome Statute art. 33.** These are two different things. One is exclusionary reasons; the other is the limit of the superior-orders *defence* in criminal liability. Say "the law marks its outer limit at orders that are 'manifestly unlawful' (Rome Statute art. 33)".
  - **"Plain fine-tuning is the known-weak baseline (Lampinen et al. 2025)".** The abstract says ICL "can generalize several types of inferences more flexibly", with exceptions (25.22). Say "a weaker baseline on several inference types".
  - **"on DOHA a 1-NN baseline tied the solver".** It tied only on the pilot's 4-item split. Leave-one-out gives 1-NN 8/10 against the solver's 4/10 decided.
  - **"A fact-check pass corrected nine errors".** No list of nine exists. FACTCHECK has 221 rows: about 177 confirmed, 16 corrected, 4 wrong and 15 unverifiable or unverified; the rest are partial or split verdicts. It did not cover strand 27. The strand files still carry the uncorrected text (README), for example "F.4.a" and "R. Tarfon rejects". Replace with the tallies and add "read the strands next to FACTCHECK.md".

## 16. Two claims about the DOHA fix and SEAD 4 overreach

- **Section:** 8 (after the DOHA table); 10 (order of work, step 5).
- **Doc text:**
  - "No solver change can fix that. Only tags taken from the neutralized pre-decision record can".
  - "SEAD 4 ¶2(b) and ¶2(e) suggest that any unmitigated allegation means deny."
- **Problem 1:** The count baseline's 10/10 may be a *real* regularity of Guideline F, not leakage. If it survives neutralized tags, precedent reasoning adds nothing on this guideline.
- **Problem 2:** ¶2(e) cuts both ways. It opens "adverse information concerning a single criterion may not be sufficient" (FACTCHECK 26.34).
- **Fix 1:** "Tags from the neutralized record will show whether the count's 10/10 is leakage or a real regularity of Guideline F. If it survives, Guideline F is too simple to show value from precedent."
- **Fix 2:** "¶2(b) (doubt resolved for national security) points toward deny-if-any-unmitigated; ¶2(e) cuts both ways."

## 17. Stale numbers, paths and examples

- **Section:** 8, 10, 12, byline, 6.
- **Problems:**
  1. **"750 lines of Python".** That is the round-1 solver (`code_r1/solver_v3.py`). The current `solver_v3.py` has 1,094 lines (1,748 with the reward and validator).
  2. **As-of chip.** It says 2026-09-29; round-2 results and the package are dated 2026-09-30.
  3. **CORE path.** "Drafted in `hc-v7-v2/catalog-CORE.yaml`" is a container working path. In the package the file is `hard-calls-v7/round2/catalog-CORE.yaml` (also `code/catalogs/hc/`).
  4. **Mac location.** "Everything is in `benchbook-labs/ideas/…` on your Mac" could not be checked from this container. Confirm it before sending.
  5. **AUT-101 YAML in section 6.** The abridgement drops `confidence`/`channel` on f4 and `channel` on f5, all of which the spec requires. It also shortens f2's text to "4-10 min", so the section 7 READ quote "…4-10 minutes" no longer matches the displayed text.
  6. **"Escalation … a computed route to a named person" (section 1).** Five flips name addressees no rule derives, and `flag_to` is outside the spec (r2-results L77).
- **Fix:**
  - "a prototype: about 1,100 lines for the solver".
  - Set the chip to 2026-09-30.
  - Use the package paths.
  - Keep f2's full text and f4/f5's required fields in the excerpt.
  - "…a computed route to the holders of the action (flag and inform addressees are not yet derived)".

## 18. Clarity for Peter

- **Section:** throughout.
- **Problems:**
  1. **Section numbers.** The doc cites "section 3/5/8/9/10/11/12", but the headings are unnumbered.
  2. **Undefined terms.** These appear without definition:
     - the Chow threshold, p*, π, U* and ρ;
     - L/k and tiers T0–T4;
     - "extreme completions", "near-miss cards", "residue", "interim", "knockouts", "tier floors" and "laundering";
     - "determination", "channel", "naqḍ", "ʿilla/ḥikma" and "Zhang's Tasks 1–3".
  3. **The diagram.** It names the three questions "Who may decide / What precedent settles / What is still uncertain", while the text says "Who may decide / What is known / What to do on each issue".
  4. **Section 4.** Its 12×5 table carries less decision value than its length. The four agreement points above it carry the message.
  5. **Sources.** The 26 main sources have no links, although FACTCHECK has the URLs.
  6. **Overclaiming words.** "fixes", "closes", "halves", "exactly", "v7 now enforces it", "Fixed | Fixed".
- **Fix:**
  - Number the headings.
  - Add a 12-line glossary after the bottom line.
  - Align the diagram labels with the text.
  - Move the section 4 table to a second tab.
  - Link each source to the URL FACTCHECK opened.
  - Replace the overclaiming words with the measured statements in items 1, 5, 7 and 8.

---

*Method note.* The ablations in items 2 and 6 are my own probes on a scratch copy. They use only functions the prototype exposes (`compose_record`, `plan_diff`, `cards_from_record`, `hidden_pi`) and are reproducible in about 20 lines of Python.
