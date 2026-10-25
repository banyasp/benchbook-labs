# Strand 26 — Formal legal-reasoning work aimed at the Benchbook's gaps

*Research agent, 2026-09-29. Scope: the six gaps listed in the brief (n-ary outcomes, scaled factors, balancing under uncertainty, inconsistent/non-binding precedent, fact-finding and tagging, per-allegation records). This is not a re-survey of strand 16. Where strand 16 already covered a paper (Horty 2019 dimensions, Canavotto & Horty 2023 hierarchies, Bench-Capon & Atkinson 2021 issues, Bench-Capon 2023/2025 intermediate factors, IBP knock-out factors, ANGELIC), I cite it only for the specific point needed.*

**Tag key:** [VERIFIED] = I opened the page and the claim is there. [SECONDARY] = from a named secondary source I opened. [UNVERIFIED] = not checked. [OURS] = my inference.

**Access problems (recorded as the brief requires):**
- Rigoni 2018 on Springer: the fetch proxy rate-limited it (HTTP 429) and told me not to retry. Everything below about Rigoni is [SECONDARY], via Horty 2021 and Prakken 2021.
- Mullins 2025 full text on Taylor & Francis: 403. I read the SSRN abstract.
- Bench-Capon & Atkinson's JURIX 2017 and 2018 dimension papers: the PDF returned 403 and IOS Press is blocked by robots.txt. I verified only the titles and pages, from Bench-Capon's bibliography page.
- Branting 1991 PDF: failed on SSL and robots.txt.
- ACM DL pages: 403.
- Horty 2019 on Springer is paywalled, but its abstract page gave Observation 3 and Definition 11. Horty 2021 on Springer is paywalled; I read the author's PDF.
- The shared web-search budget ran out partway through this strand. The last few items were checked with direct fetches only.

**One caveat on Horty 2021 Definition 9.** The PDF text extraction loses where the mirror bar sits. The tool read clause (2b) as "Premise(r) ⊩ W̄". That reading fails on Horty's own worked example (≥12 months does not entail ≥24 months). The reading that fits the example is "the mirror of Premise(r) entails W" (≤12 months entails ≤24 months). I use that reading below and label it [OURS]. Peter should check p. 281 of the PDF directly.

---

## Bottom line

1. **No precedential-constraint model I could open handles more than two outcomes.** Horty's book draft, van Woerkom et al. (JAIR 2024; AI&Law 2026), Odekerken et al., Canavotto 2025 and Fungwacharakorn et al. 2025 are all two-sided. Di Florio et al. add only a "no decision" value.
   - The fix is a reduction.
   - Give every factor a **favors-set** (the options it pushes toward) instead of one letter.
   - Record the holding as **pairwise holdings**: winner over each loser, each with its own reason.
   - When the options sit on one scale, this collapses to **threshold binaries** ("at least C?", "at least A?").
   - This makes the 21/100 "mixed" reason sets legal, and it turns flip rules into solver-checkable holdings between the losing options.
2. **The collapse bites Peter's likelihood ladders only when the catalog has rungs favoring the losing side.** More precisely: when the losing side has a rung between the precedent's actual value and the reason's threshold.
   - Horty's 2021 mirror fix becomes a one-line change to the distinction formula.
   - That change: a counter-factor on the same dimension that is entailed by the mirror of the reason does not count as a distinction.
3. **Balancing can be recorded as ordinal intensity × reliability per equity**, and a solver can run a dominance (a-fortiori) test on it without numbers. The bigger win is a `holding_force` field (required / permitted / forbidden). IHL's "reasonable military commander" standard, like IG reviews, mostly produces *permission*, not obligation.
4. **Inconsistent, mixed-authority casebooks are now formally tractable.**
   - Canavotto's "no new inconsistency" test handles contradictory precedents.
   - Broughton and Di Florio et al. add court hierarchy, recency, overruled precedents and per incuriam precedents (ones decided in ignorance of a binding authority).
   - Mullins argues for ordinal, not cardinal, precedent weight.
   - The Benchbook needs an **authority lattice** in the casebook header, plus per-case `authority` metadata.
5. **Incomplete-information precedent reasoning (Odekerken, Bex & Prakken 2023/2026) is the single most useful find for the tagging step.**
   - Facts get sets of possible values.
   - The solver computes whether the verdict is *stable* across all completions of the unknowns.
   - It also computes which unknown is *relevant*. That is a solver-computable version of Peter's "the one question left" and `watch_for`.
6. **Per-allegation records should be issue-level holdings plus a declared rollup rule** (IBP's logical model; SEAD 4's single-criterion rule). This avoids treating "one unmitigated allegation outweighs nine mitigated ones" as a balance.

---

## 1. More than two outcomes

### 1.1 What the formalisms say

Every model I opened is two-sided:

- **Horty's book draft** [VERIFIED]: "we can suppose that the outcome of a case is a decision directly either in favor of the plaintiff or in favor of the defendant."
  - It also assumes that "all factors are like this, favoring one particular side."
  - It does not discuss generalizing to more than two outcomes.
- **van Woerkom et al., JAIR 2024** [VERIFIED]: "A fact situation can be decided for either of two outcomes, also called sides, 0 or 1."
  - Their 2026 hierarchical/dimensional models are also two-outcome [VERIFIED].
- **Odekerken, Bex & Prakken** [VERIFIED]: the outcome "can be either PRO or CONTRA."
- **Canavotto 2025** [VERIFIED], and **Fungwacharakorn, Bourgne & Satoh 2025** [VERIFIED], who formalize arguments over her model: plaintiff/defendant only.
- **Di Florio, Dong & Rotolo, "When Precedents Clash"** [VERIFIED]: classifier outputs in {1, 0, ?}. The "?" is the absence of a decision, not a third option.

The only multi-class argumentation-CBR model I found is **Gould & Toni's Gradual AA-CBR** (NeSy 2025) [VERIFIED]. It "enabl[es] multi-class classification". But argument strengths are learned by gradient descent, so it is not a deterministic a-fortiori constraint and cannot produce solver gold labels.

I cannot prove a negative. The search budget ran out before I could rule out a stray workshop paper. But none of the main lines of this literature models n-ary, ordered or compound outcomes [OURS].

### 1.2 What goes wrong with "one winner vs everything else"

Take a Hard-Calls-style case, an autonomous vessel [OURS]. Options:
- **A** = engage the contact.
- **B** = keep shadowing.
- **C** = prepare both an engagement course and an evasive course, and hand the choice to the commander.

Factors:
- A1: the contact is on an intercept course.
- B1: engagement authority is above the agent's role.
- C1: the commander is reachable before the closest point of approach.
- A3: hull markings match a known hostile unit.

**Precedent P:** facts {A1, B1, C1}, outcome C. The real justification has two halves:
- A1 rules out B (a threat on an intercept course needs a ready response).
- B1 rules out A (the agent may not engage on its own authority).
- C1 makes C feasible.

**Under one-vs-rest:** pro-C = {C1} and con-C = {A1, B1}. Horty's reason must be a subset of pro-C, so R = {C1}. That is why 21 of 100 Hard-Calls reason sets "violate" the rule: the true reason is {A1, B1}, which mixes letters. Both directions of the test then fail:

- **False distinction.** New situation S = {A1, A3, B1, C1}. A3 favors A, so it counts as a new con-C factor the precedent never weighed. Result: distinguished, not binding. But A3 only strengthens the case against B. B1 still blocks A, so C should follow.
- **False a fortiori.** New situation S′ = {B1, C1}. Con-C shrank, so the precedent binds and C is forced. But without A1 there is no threat, and B (keep shadowing) is plausibly right. A1 was part of C's justification against B, and deleting it was wrongly read as removing an obstacle to C.

**The root cause** [OURS]: relative to a compromise, a factor pushes in both directions. A1 helps C against B and hurts C relative to A. A single polarity cannot express that.

### 1.3 Candidate reductions

**(a) Pairwise holdings over favors-sets (recommended general form)** [OURS]

*Catalog change.* Replace "the ID's first letter is the favored option" with `favors: [options]`, the set the factor pushes toward (against all the rest). For the example:
- A1 favors {A, C}.
- B1 favors {B, C}.
- C1 favors {C}.
- A3 favors {A, C}.

For any pair (o, o′), the factors favoring o over o′ are those whose favors-set contains o but not o′. The ID letter can stay as a mnemonic.

*Case change.* Replace the single `reason` with `pairwise: [{win, lose, reason}]`, one entry per losing option (k−1 entries for k options):
- P: `{win: C, lose: A, reason: [B1]}` and `{win: C, lose: B, reason: [A1]}`.
- The union {A1, B1} is the "mixed" reason. It is now legal, because each part lives in its own pair.

*Solver rule.*
- `forced(o ≻ o′ | S)` holds iff some precedent carries a pairwise holding (o ≻ o′, R) where:
  - R ⊆ S, and
  - every factor in S that favors o′ over o was already in that precedent's facts. This is Horty's reason model run on the pair, plus the §2 mirror clause if dimensions are involved.
- `Perm(S)` = the options that no other option is forced to beat.
- **binding** iff |Perm| = 1. **bounded/open** otherwise.

Checking the example:
- **S** = {A1, A3, B1, C1}. Pair C–A: R = {B1} holds, and nothing in S favors A over C (A3's favors-set includes C). Pair C–B: R = {A1} holds. So C is forced.
- **S′** = {B1, C1}. Pair C–B: R = {A1} is missing, so that pair is unconstrained. Pair C–A is still forced. Perm = {B, C}. That is the right answer: autonomous engagement is excluded, and the harness decides act-or-ask on B vs C.

*Bonus: flip rules become holdings between the losing options.* "−C1 → B" says that with C infeasible, B beats A. Record it as `pairwise {win: B, lose: A, reason: [B1], condition: −C1}`. The solver can check it whenever its `if` uses catalog factors.

*Escalation.* `then: escalate` should become one of two things:
- A real option, if it is a substantive move ("prepare both and refer"). Such options usually have enabling conditions (C1), which belong in an option-level `requires: [C1]` field, not in the factor set.
- `unconstrained` (|Perm| > 1), leaving *ask* to the harness.

This separates the procedural move from the options, as the brief's diagnosis asks.

**(b) Ordered outcomes as threshold binaries (special case)** [OURS]

When options form a chain (shadow < prepare-and-refer < engage; warn < disable < destroy; sentencing bands) and every favors-set is an up-set or a down-set of the chain, pairwise holdings reduce to k−1 nested binary questions:
- t1 = "at least C?"
- t2 = "at least A?"

An outcome C answers **yes** to t1 (reason drawn from upward factors: {A1}) and **no** to t2 (reason drawn from downward factors: {B1}).

This is the output-side twin of Peter's nested threshold factors on the input side. An ordinal outcome is a ladder of binary cases. Two precedents can bracket a new situation into an interval (a lower bound from one, an upper bound from another), which is exactly what sentencing-style reasoning needs.

This is the standard ordinal-to-binary decomposition from machine learning (Frank & Hall 2001, "A simple approach to ordinal classification"). [UNVERIFIED: I did not open it; the search budget was exhausted.]

A middle-favoring factor like C1 is not monotone on the chain. It is the tell-tale sign of a compromise, which is why C1 is better treated as an enabling condition.

**(c) Compound decisions as component vectors** [OURS]

"Do the lawful part, hold or route the rest" (72/100 partial moves) is best represented as a vector of component decisions, each binary or ordinal:
- release tearline: yes/no
- release full product: yes/no
- route to IG: yes/no

Constraint is then per component (§6). Add a `coupling` rule only where components interact (e.g., "full release implies tearline release").

**(d) Per-issue resolutions (ANGELIC / Canavotto & Horty, strand 16)** decompose *reasons*, not *options*. They help with (c) but do not by themselves fix the compromise problem in 1.2.

### 1.4 What it fixes, cost, and the best argument against

**Fixes:**
- the binary-vs-n-ary mismatch;
- the 21/100 mixed reasons;
- the conflation of escalation with an option;
- about 139 flip rules. Those whose `then` is `escalate` become either options or `unconstrained`.

**Cost:**
- One reason per losing option. Hard-Calls has 3–4 options, so 2–3 short reason sets per case instead of 1.
- One favors-set per catalog factor.
- The solver is k−1 runs of the existing binary check.

**Best argument against.** Pairwise holdings fragment a holistic judgment. The commander-referral option exists because of the mutual blocking, and a labeler may not be able to say which factors defeat which alternative. Pairwise constraints from different precedents can also form cycles (A ≻ B, B ≻ C, C ≻ A), leaving Perm empty.

Answers:
- (i) The labeler already has to do this: the 21 mixed reasons show the pairwise structure is already in Peter's head.
- (ii) A cycle signals an inconsistent casebook. §4's machinery (Canavotto) handles it. Perm can be defined as the Smith set, "the smallest set such that every candidate inside the set S pairwise defeats every candidate outside S" (Wikipedia, "Smith set") [VERIFIED], and it is never empty. Because forced relations are partial (many pairs are undecided), the Schwartz variant, which "ignores tied votes" (same page) [VERIFIED], fits better. [OURS]

---
## 2. Scaled factors and the collapse

### 2.1 What the formalisms say

**Horty 2019, "Reasoning with dimensions and magnitudes"** (AI&Law 27:309–345).
- Definition 11 introduces magnitude factors M^s_{d,v}. Such a factor holds when "the value of that situation along the dimension d favors the side s at least as strongly as v" [VERIFIED, abstract page].
- Observation 3 shows the reason model then yields exactly the result model's constraint. The reason: "any respect in which a situation is weaker for a side than a situation from a background case already settled for that side can consistently be used as the basis of a rule supporting a decision for the opposite side" [VERIFIED].
- Mechanism [OURS]: when the new case slips on dimension d, a magnitude factor for the other side at the new value becomes true. It was false in the precedent, so the precedent never ranked anything above it.

**Horty 2021, "Modifying the reason model"** (AI&Law 29:271–285) [VERIFIED from the author PDF].
- Mirror: for a reason V favoring s, V̄ is "built from magnitude factors addressing the same dimensions as those in V and using the same reference values, but favoring the opposite side."
- Example: if Premise(r1) = {M^δ_{d1,12}} ("a year or more abroad", favoring the defendant), then its mirror {M^π_{d1,12}} is "a year or less abroad", favoring the plaintiff.
- Definition 9 (modified priority): W <_c Z iff (1) Z ⊩ Premise(r), and either (2a) X ⊩ W, or (2b) the mirror clause. (Bar placement: see the caveat at the top. The reading consistent with the example is "the mirror of Premise(r) ⊩ W" [OURS].)
- Justification: "By appealing Premise(r) to justify its decision for s, the court is implicitly asserting that Premise(r) is a stronger reason for s than Premise(r)̄ is for s̄."
- Worked result: in precedent c1, a 30-month stay was decided for the defendant on the ≥12-month rule. A later 15-month case decided for the plaintiff on a "<24 months" rule is consistent under the original model but *inconsistent* under the modified one. In Horty's words, "spending a year or more abroad must have higher priority as a reason for the defendant than spending two years or less abroad does for the plaintiff."
- Second example (c5–c7): a two-dimension premise stops binding when the new case falls below the premise on the other dimension.

**Rigoni 2018** (AI&Law 26:1–22) [SECONDARY; Springer page rate-limited].
- Horty 2021 reports that Rigoni builds dimensions as "sets of reasons", "limits consideration to a single dimension", and uses **switching points**: regions of a dimension where the favored side changes.
- Horty rejects switching points: reasons "favoring each side … vary only in strength."

**Prakken 2021, "A formal analysis of some factor- and precedent-based accounts of precedential constraint"** (AI&Law 29:559–585) [VERIFIED].
- He accepts that Horty's revision "does not collapse into his result model." But he warns it shares a feature, "even more strongly present in Rigoni's model", that raises "concerns about practical applicability": "it may in practice be hard for knowledge engineers to identify the side favoured by a particular value assignment, since often this will be context-dependent."
- His alternative, Definition 15: deciding F for s is forced iff some precedent c = (F′, R, s) has R ≤_s F^|R|. Here R is a "possibly incomplete rule" (value assignments to a subset of dimensions), and the new case is compared only on R's dimensions.
- As the fetched text reads, Definition 15 does not itself block on new opponent-side dimensions [VERIFIED as summarized]. So R must list the counter-dimensions that were weighed, at their precedent values, or the model becomes rule-like [OURS].

**Bench-Capon & Atkinson.** "Dimensions and Values for Legal CBR" (JURIX 2017, pp. 27–32) and "Lessons from Implementing Factors with Magnitude" (JURIX 2018, pp. 11–20). Also Atkinson, Bench-Capon, Prakken & Wyner, "Argumentation Schemes for Reasoning about Factors with Dimensions" (JURIX 2013, pp. 39–48). I verified titles and pages only, via Bench-Capon's bibliography page. Their content is [UNVERIFIED]. My unverified recollection: they treat ascribing a factor from a dimension value as its own argued step, driven by values/purpose, which is the same "where is the threshold?" problem.

### 2.2 How this bears on Peter's ladders (B2@even, B2@likely) [OURS]

Peter's rung B2@v means "likelihood ≥ v, favoring B". That is exactly Horty's M^B_{d,v}. Whether the collapse bites depends on the catalog.

**Case 1: one-sided ladders only (no A-favoring rungs on that dimension).**
- No collapse. A drop in likelihood removes B-rungs; it never adds an A-factor.
  - The first clause of D, (R \ Y), catches a drop below the reason's rung.
  - The second clause, (Y^ō \ X^ō), catches a rise when the precedent went against B.
- The price: the catalog cannot express "civilian presence at most unlikely" as a *positive* reason for A. An A-precedent's reason can only cite other factors.
- Peter's ladder, starting at "even", is an implicit **catalog-level switching point**. It declares that movement within bins 1–3 never matters. That is Rigoni's modeling choice, and it inherits Prakken's objection: whether "unlikely" civilian presence favors holding depends on the context (strike vs. collection vs. release).

**Case 2: two-sided ladders (A2@≤v mirrors exist).** Peter's current D collapses exactly when the catalog has an ō-favoring rung u on a dimension such that:
- the precedent's actual value is below u, and
- u is still within the tolerance set by R's rung on that dimension.

The fix, from Definition 9:

> D = (R \ Y) ∪ (Y^ō \ (X^ō ∪ ↓mirror(R)))

Here ↓mirror(R) is the set of catalog factors entailed by the mirror of R's magnitude factors. A plain boolean factor's mirror is trivially true, so it contributes nothing. On a single dimension this reduces to: **the precedent binds iff the new case still satisfies R's rung, whatever the precedent's actual value was.**

Two companion rules for Zhang-style significance:
- **Closure.** A fact tagged B2@likely must also carry B2@even. The solver should enforce this rather than trust the tagger.
- **No same-dimension substitutes.** B2@even can never "downplay" the absence of B2@likely, because they are one fact at two resolutions. The current per-equity substitute test would otherwise find a spurious equal-strength substitute whenever both rungs support the same equity with the same strength.

### 2.3 Worked example with ICD 203 bins [OURS; bins VERIFIED]

ICD 203's seven likelihood terms map to 01–05, 05–20, 20–45, 45–55, 55–80, 80–95 and 95–99% [VERIFIED, ICD 203 PDF]. Number the bins 1–7 (1 = almost no chance … 4 = roughly even … 7 = almost certain). ICD 203 also says a confidence level must not be combined with "a degree of likelihood … in the same sentence" [VERIFIED]. That fits keeping confidence separate (see §3).

**Setup.**
- Dimension L2 = likelihood that the contact is a civilian vessel.
- B-rungs ("hold"): B2@≥unlikely (bin ≥3), B2@≥even (≥4), B2@≥likely (≥5).
- A-rungs ("engage"): A2@≤unlikely (≤3), A2@≤vunlikely (≤2).

**Precedent P.** A1 (hostile act observed); L2 = very unlikely (bin 2); outcome A.
- Tags: {A1, A2@≤unlikely, A2@≤vunlikely}. X^B = ∅.
- The deciding official relied on "at most unlikely", so R = {A1, A2@≤unlikely}.

| New situation | L2 | Current D | Mirror-fixed D | Correct? |
|---|---|---|---|---|
| S1 | bin 2 | ∅ → binds | ∅ → binds | yes |
| S2 | bin 3 (unlikely) | Y^B \ X^B = {B2@≥unlikely} → **distinguished** | B2@≥unlikely is the mirror of A2@≤unlikely, so it is excluded → **binds** | fixed: still inside the stated tolerance |
| S3 | bin 4 (even) | R \ Y = {A2@≤unlikely} → distinguished | same | yes: past the tolerance |
| S4 | bin 3, R = {A1} only (the official said nothing about L2) | {B2@≥unlikely} → distinguished | not in the mirror of R → distinguished | yes: only bin 2 was weighed |

Row S2 is the collapse. A one-bin move that the official's own stated reason tolerates defeats the precedent. Row S4 shows the fix stays principled: if the reason does not mention the dimension, the precedent weighed only the actual value.

**Labeling consequence.** The reason's rung is the load-bearing labeling decision: did the official rely on "at most unlikely" or on "very unlikely"? This is Horty's "30 months, rule ≥12" choice. It should be a required, explicit field (`reason` lists the rung), never inferred from the fact's bin.

### 2.4 What it fixes, cost, and the best argument against

**Fixes:**
- Spurious distinctions on graded facts: likelihood, recency ("not at this time"), quantity, and partially applied mitigators once those become 2-rung ladders (§5).
- The downplay bug on nested factors.
- It makes Peter's scaled-fact design sound in either catalog style.

**Cost:**
- Catalog: declare the dimension, its direction and its rungs (once per factor family).
- Labeler: choose the rung in R.
- Solver: one closure step plus a set difference.

**Best argument against.** Definition 9 extends a precedent's reach past anything the official said. "≥12 beats ≤12" is stretched to "≥12 beats ≤24" by assuming that reasons on a dimension vary monotonically in strength. Prakken's objection generalizes: in natsec, where a dimension switches sides is context-dependent, and ICD bins are coarse (54% vs 56% crosses a bin boundary).

Mitigations:
- Keep the mirror inference within one sub-area's catalog.
- Let a catalog mark a dimension `non_monotone: true` (no mirror inference).
- Accept that the collapse is only as bad as the ladder is fine. Coarse ladders are a legitimate deployer choice, but they should be a *declared* switching point, not an accident.

---
## 3. Balancing incommensurable equities under uncertainty

### 3.1 What the formalisms say

**Alexy's Weight Formula**, as presented by Klatt & Schmidt (2012) [VERIFIED]:

> W_{i,j} = (W_i · I_i · R_i) / (W_j · I_j · R_j)

- W = abstract weight; I = intensity of interference; R = reliability of the empirical assumptions.
- Intensity uses a triadic scale: light = 2⁰, moderate = 2¹, serious = 2².
- Reliability: reliable/certain = 2⁰, plausible = 2⁻¹, not evidently false = 2⁻².
- The epistemic "second law of balancing": "The more heavily an interference with a constitutional right weighs, the greater must be the certainty of its underlying premisses."

**Sartor.** "The Logic of Proportionality: Reasoning with Non-Numerical Magnitudes" (German Law Journal 14(8):1419–1456, 2013; earlier in Rivista di filosofia del diritto 2012) [VERIFIED].
- It models proportionality "based on quantitative reasoning, even when no numbers are given."
- Utility impact on value v is the proportional impact times the weight of v.
- The key non-numerical inference is **dominance**: better on some value and no worse on the others.
- In the text the fetch tool could read, I found no probability or reliability term. Uncertainty enters only through Alexy.

Sartor's "Consistency in Balancing: From Value Assessments to Factor-Based Rules" (in Duarte & Sampaio (eds.), *Proportionality in Law*, Springer 2018, pp. 121–136) connects "outcomes' impacts on values and factors influencing such impacts" and proposes "a formal analysis of the connection between balancing assessments and factor-based case-rules" [VERIFIED, abstract]. That is the same bridge as Peter's factor → equity (strong/weak) links.

**IHL.**
- AP I art. 51(5)(b) and art. 57(2)(a)(iii) forbid attacks expected to cause incidental civilian harm "which would be excessive in relation to the concrete and direct military advantage anticipated."
- Art. 57(2)(b) requires cancelling or suspending an attack when this "becomes apparent" [VERIFIED, OHCHR text].
- The ICTY committee's NATO report, ¶50 [VERIFIED]: "the answers may differ depending on the background and values of the decision maker … the determination of relative values must be that of the 'reasonable military commander'. Although there will be room for argument in close cases, there will be many cases where reasonable military commanders will agree that the injury to noncombatants … was clearly disproportionate."

### 3.2 Fields and solver rule [OURS]

**Case field:**

```
balance: [{equity, favors: <option>, intensity: light|moderate|serious,
           reliability: certain|plausible|not_evidently_false}]
```

- Abstract weight belongs in the **catalog**: it is the deployer's equity priority, not a per-case judgment.
- For risk-type equities, intensity combines magnitude with ICD likelihood ("may be expected to cause").
- Reliability is the ICD **confidence** in the premise. ICD 203 already separates the two, so this maps cleanly.
- Peter's strong/weak is already a 2-point intensity scale, so this is an extension, not a new layer.

**A-fortiori test (dominance, no numbers).** Precedent P chose o over o′. In new situation S, o ≻ o′ is forced if both hold:
- (i) every equity favoring o in P's *decisive set* has, in S, intensity ≥ and reliability ≥ its values in P; and
- (ii) every equity favoring o′ in S appeared in P with intensity ≤ and reliability ≤.

Condition (i) uses the decisive subset rather than all pro-o equities. That keeps reason-model narrowness, and §2's mirror logic applies per equity.

An optional **Alexy-exchange** mode compares per-equity scores i + r (log₂ scale). It assumes one intensity step equals one reliability step, but never sums *across* equities, so incommensurability is respected. The solver should report which mode produced a label.

**The more important field: `holding_force: required | permitted | forbidden`.**
- A "reasonable commander" approval, an IG finding of "not unreasonable", or a DOHA Appeal Board affirmance on a deferential standard establishes that the chosen option was *permitted*, not that the others were forbidden.
- Solver rules:
  - From a `permitted` precedent, infer permission for any S at least as favorable.
  - From `forbidden` ("clearly disproportionate"), infer prohibition for any S at least as unfavorable.
  - Only `required` yields `forced`.
- This lines up with Canavotto's deontic reading (§4). It turns many current "contested" holdings into sound but weaker constraints.

### 3.3 What it fixes, and the best argument against

**Fixes:**
- Records how *much* each equity was at stake, and how sure the decider was, without faking numbers.
- Gives the "second law" a checkable form: heavier interference requires higher reliability, as a flip rule on reliability.
- Stops treating permissive hindsight rulings as mandates.

**Cost:**
- Two ordinal labels per equity per case (about 3–5 equities).
- A dominance check in the solver.

**Best argument against.**
- Intensity grading *is* the balancing. Moving judgment from "which option" into "moderate or serious?" relocates the irreducible step without removing it.
- Reviewers widely criticize Alexy's formula as false precision.
- For training: the model learns to game ordinal grades to reach the outcome it prefers.

Answer: score the grades like tags (F1 against gold), not as free choices. Keep the reward on the solver's verdict computed from the model's *own* grades, exactly as Peter does for tags.

---

## 4. Inconsistent and non-binding precedent

### 4.1 What the formalisms say

**Canavotto, "Reasoning with inconsistent precedents"** (AI&Law 33(1):137–166, 2025; online 2023) [VERIFIED].
- The requirement "keep the case base consistent" becomes "introduce no *new* inconsistency".
- Fungwacharakorn et al. [SECONDARY] state it as: decide X for s on rule r iff inc(Γ ∪ {⟨X,r,s⟩}) ⊆ inc(Γ).
- Observation 5.5: a potential decision introduces a new inconsistency iff it has a conflicting case and no supporting case.
- "Inconsistent case bases do not make verification that a decision is permissible substantially more complex than consistent case bases."
- Footnote 10 flags the limitation: the conclusion is "reasonable under the assumption that different precedent cases are equally important."

**Broughton, "Vertical precedents in formal models of precedential constraint"** (AI&Law 27(3):253–307, 2019) [VERIFIED, PhilPapers]: "no model can capture the U.S. doctrine of precedent without making that distinction" between vertical and horizontal precedent.

**Di Florio, Dong & Rotolo, "When Precedents Clash"** (arXiv 2410.10567) [VERIFIED].
- Adds a court hierarchy, a binding relation and a temporal order.
- Formalizes "overruled cases and cases decided per incuriam", which are "not to be considered binding."
- Decides by the latest binding precedents of the highest court. That is unambiguous only when the temporal order is total.

**Mullins, "Weight and Authority in Formal Models of Precedential Constraint"** (Jurisprudence, 2025, doi 10.1080/20403313.2025.2486422; SSRN 5201392) [VERIFIED, abstract].
- Precedents carry "varying levels of priority or strength", but the framework "does not allow us to use cardinal weights."
- Argues against "interpreting strictly authoritative precedent in terms of prioritising or reweighting reasons."

**Non-common-law authority** [VERIFIED]:
- *Jurisprudence constante*: "a long series of previous decisions … is highly persuasive but not controlling"; a single decision can ground stare decisis, while "a series of adjudicated cases, all in accord" forms jurisprudence constante (Louisiana Supreme Court, via Wikipedia).
- ICJ Statute art. 59: "The decision of the Court has no binding force except between the parties and in respect of that particular case."
- ICJ Statute art. 38(1)(d): judicial decisions are "subsidiary means for the determination of rules of law."

### 4.2 Fields and solver rule [OURS]

**Casebook header:** an authority lattice (a partial order) over sources such as FISC/court, DOJ/OLC, agency GC, IG, PCLOB, policy board, deployer ruling and after-action review. It also declares:
- which sources bind which `agent_role` or sub-area; and
- whether later-in-time overrides at equal rank.

**Case field:**

```
authority: {source, rank, date, force: binding|persuasive, status: good|overruled|superseded|per_incuriam}
```

**Solver steps:**
1. Filter out overruled and superseded cases.
2. Split the rest into a binding pool and a persuasive pool, for this agent and context.
3. In the binding pool, resolve conflicts:
   - higher rank wins;
   - at equal rank, the later case wins if declared;
   - otherwise apply Canavotto: option o is permissible iff no binding precedent conflicts with o, or some binding precedent supports o.

   Only ordinal ranks are used, following Mullins.
4. The persuasive pool never forces. It supports the **analogous** label only as jurisprudence constante: at least k consistent persuasive precedents and none conflicting (k set by the deployer).

Peter's "bounded" label then becomes computable as a permissible *set* rather than "pulls both ways".

### 4.3 What it fixes, and the best argument against

**Fixes:**
- Mixed-authority natsec casebooks.
- Stale precedents.
- A computable "bounded" label.
- IG-style findings recorded as persuasive rather than binding.

**Cost:**
- One metadata block per case.
- A one-time lattice per deployer.
- Linear-time filtering.

**Best argument against.** Natsec authority is not a clean lattice. IG reports are recommendations; policies are silently superseded; classified opinions may be uncitable to the agent; and the deployer's own rulings may conflict with a higher legal authority the deployer cannot overrule.

Answer: the lattice is deployer-declared and can be partial. Where two sources are incomparable, Canavotto's permissive rule applies, and the harness asks.

---
## 5. Fact-finding, credibility and the tagging step

### 5.1 What the formalisms say

**Bex, van Koppen, Prakken & Verheij, "A hybrid formal theory of arguments, stories and criminal evidence"** (AI&Law 18(2):123–152, 2010) [VERIFIED, citation and abstract].
- Evidential arguments support or attack the elements of competing *stories* (causal scenarios).
- It focuses on "the process of proof, in which the facts of the case are determined."
- The story-comparison criteria (evidential coverage, contradiction, gaps, plausibility) were paraphrased by the fetch tool and are [UNVERIFIED] as stated.

**Verheij, "Proof with and without probabilities"** (AI&Law 25(1):127–154, 2017) [VERIFIED].
- A *case model* is a set of logically consistent, mutually incompatible "cases" (full accounts of what happened) with a total preorder.
- An argument (φ, ψ) is:
  - *coherent* if some case satisfies φ ∧ ψ;
  - *conclusive* if every case satisfying φ satisfies φ ∧ ψ;
  - *presumptively valid* if a case satisfying φ ∧ ψ is ≥ every case satisfying φ.

**Odekerken, Bex & Prakken, "Justification, stability and relevance for case-based reasoning with incomplete focus cases"** (ICAIL 2023) [VERIFIED].
- Each dimension of the new case gets a *set of possible values*.
- The status is Stable-PRO / Stable-CONTRA / Stable-UNDECIDED if every completion gets that status, and "Unstable otherwise."
- Removing a possible value is *relevant* if it leads to a minimal stable partial completion.
- Complexity: Stable-PRO/CONTRA is coNP-complete in general, but "extreme completions" (only the most-PRO and most-CONTRA values per dimension) make it polynomial when each possible-value set has a single min and max.

**The journal version**, "Precedent-based reasoning with incomplete information for human-in-the-loop decision support" (AI&Law 34, 2026; online 2024) [VERIFIED].
- Stresses identifying "cases for which the same outcome is enforced regardless of how the uncertainties … are resolved."
- Reports a deployment with the Dutch police for classifying mala fide web shops.
- Notes that "a user can assign an outcome to an unstable focus case without making the case base of precedents inconsistent."

**SEAD 4**, whole-person factors (App. A ¶2(d)) [VERIFIED]: these include "the frequency and recency of the conduct", "the presence or absence of rehabilitation" and "the likelihood of continuation or recurrence". That is the source of the pilot's temporal and "not at this time" judgments.

**Wigmore charts.** I verified only a generic description (Wikipedia: lines for "reasoning, explanations, refutations, and conclusions"). They add no field that Bex/Verheij do not.

### 5.2 Fields and solver rule [OURS]

**Facts** get `status: established | admitted | alleged | assessed | disputed`. For `assessed`, add `likelihood` (ICD bin) and `confidence`. For testimonial facts, add `credibility: credited | discredited | not_assessed`.

In the **new situation**, any fact that is not established carries a **possible-value set**:
- a boolean factor → {present, absent};
- a ladder dimension → an interval of bins (e.g., [unlikely, even] when analysts split).

**"Partially applies"** becomes a 2-rung ladder in the catalog (F@partial ⊂ F@full, F@partial weaker). §2's machinery then handles it. That covers the 5/10 pilot misfits where a mitigator applied in part.

**Stability (solver).** The reason model is monotone: adding o-favoring factors and removing ō-favoring ones can only help o. So Odekerken-style extreme completions work here as well. The solver runs twice per option (or per pair from §1):
- once on the most-o completion;
- once on the least-o completion.

If they agree, the verdict is stable, and the harness can act on it.

**Relevance (solver).** If the verdict is unstable, try resolving each uncertain fact to each extreme on its own. The facts whose resolution stabilizes the verdict are the gold `question_left`, and they seed `watch_for`.
- This is a greedy under-approximation of Odekerken's relevance, which is NP-complete in general. With ≤5 uncertain facts per situation it is cheap.
- This makes step 5 of the mapping ("the one question left") partly solver-checkable instead of prose.

**Competing readings (Verheij/Bex).** When a situation admits rival accounts (a genuine fishing boat vs. a militia vessel spoofing AIS), the mapping lists 2–3 alternative taggings, each with an ICD likelihood. The solver runs on each. Agreement means the decision is robust to the fact dispute; disagreement means the decision turns on it, which feeds act-or-ask.

**Stop tags from encoding the verdict.** Build new-situation inputs from the *pre-decision* record (SOR allegations plus the applicant's evidence; the Hard-Calls `situation`), with statuses `alleged`/`assessed`. Keep the fact-finder's `established` statuses only in the *precedent* record. This directly addresses "tags taken from the judge's findings nearly encode the verdict."

**Temporal holdings.** "Not at this time" is a reason containing a recency rung (e.g., A@≥24mo since last incident). The flip rule "+A@≥24mo → A" is then solver-checkable.

### 5.3 What it fixes, and the best argument against

**Fixes:**
- Partially applied mitigators.
- Credibility, and alleged vs found.
- Verdict leakage through tags.
- A computable "one question left".
- A principled basis for act-or-ask: unstable plus a resolvable relevant fact → ask/gather.

**Cost:**
- A status on every fact (cheap).
- Possible-value sets only on disputed facts.
- Solver: 2 runs per option plus a per-fact relevance loop.

**Best argument against.** None of this checks fact-finding itself. Credibility calls remain unscored judgment, and possible-value sets may teach the model to widen every interval, go "unstable" and ask by default.

Answer: score interval width against gold (a too-wide interval costs tag-F1), and let Peter's Chow threshold, not the model, set the ask rate.

---

## 6. Per-allegation / multi-issue records

### 6.1 What the formalisms and practice say

**SEAD 4** [VERIFIED]:
- "Any doubt concerning personnel being considered for national security eligibility will be resolved in favor of the national security" (¶2(b)).
- "a single criterion may be sufficient to make an unfavorable eligibility determination even in the absence of a recent occurrence or a recurring pattern," while a "recent or recurring pattern of questionable judgment" can ground ineligibility even when no single criterion suffices (¶2(e)).

**DOHA decisions record formal findings per paragraph and subparagraph.** ISCR Case No. 24-00337 (Apr. 10, 2025) [VERIFIED]:
- "Paragraph 1, Guideline H: FOR APPLICANT … Paragraph 2, Guideline E: AGAINST APPLICANT."
- The conclusion: "not clearly consistent with the national interest to grant." The applicant mitigated one guideline, was not mitigated on another, and was denied.

**IBP** (Brüninghaus & Ashley 2003; described in Bench-Capon, "HYPO's legacy", AI&Law 25(2):205–250, 2017) [SECONDARY]:
- A logical model from the Restatement splits the claim into issues.
- Factors resolve each leaf issue, with knock-out factors.
- Issue outcomes "feed into the hierarchical logical model, which combines them."

**Bench-Capon's 2025 intermediate-factors paper** (strand 16) holds that constraint should run on base-level factors, with intermediate factors serving explanation. [OURS] DOHA allegations are *not* intermediate factors of one outcome. They are separately adjudicated questions with a regulation-supplied aggregation rule, so issue-level constraint is legitimate here.

**Branting 1991, "Reasoning with portions of precedents"** (reuse of sub-justifications): I could not open it [UNVERIFIED].

### 6.2 Fields and solver rule [OURS]

```
issues: [{id, question, catalog, facts, factors, outcome, reason, holding_force}]
rollup: {rule: any_against | all_for | conjunctive | vector, basis: rule|judgment,
         override: [{pattern_finding, then}]}
```

**Solver:**
1. Constrain each issue separately. An issue-level holding from *any* precedent can bind the matching issue in the new case (Branting's "portions" idea).
2. Apply the rollup.

**For SEAD 4:**
- `any_against` → deny is `required`. Reading ¶2(b) with ¶2(e), an unmitigated concern is a doubt [OURS interpretation; Peter should check it against the Appeal Board's language].
- `all_for` → grant is only `permitted`: a deny remains lawful if the record has an explicit "pattern" finding (¶2(e)).

"One unmitigated allegation outweighs nine mitigated ones" stops being a balance. The nine mitigated allegations never enter the rollup.

**For natsec compound moves:** issues are the components of a partial action (§1.3(c)), and the rollup is `vector` plus any declared couplings.

### 6.3 What it fixes, and the best argument against

**Fixes:**
- Split findings, cross-guideline cases and compound partial moves.
- Makes 1-NN vs solver comparisons fairer: per-issue retrieval is finer-grained than whole-case tags.

**Cost:**
- DOHA: one small record per SOR subparagraph (often 5–15). That is the heaviest labeling item in this strand.
- Hard-Calls: 2–3 components per case.
- Solver: per-issue runs plus a lookup.

**Best argument against.** The whole-person concept is expressly holistic. Recency, pattern and interaction across allegations are exactly what per-issue decomposition discards, and Bench-Capon's point stands that issue structure often explains rather than constrains.

Answer: keep a `pattern` override at the rollup level. It is recorded as a whole-case factor, so holism enters through one declared channel instead of leaking into every issue.

---
## Ranked top 5 to adopt

**1. Favors-sets plus pairwise holdings, with the ordinal threshold form when options form a chain (§1).**
- *Fixes:* binary vs n-ary; the 21/100 mixed reason sets; compromise outcomes; escalation-as-option; flip rules between losing options become checkable.
- *Cost:* labeler writes k−1 short reasons per case plus one favors-set per catalog factor. Solver is k−1 runs of the existing binary check, plus a Schwartz-set step.
- *Why first:* every other fix assumes it, and the Hard-Calls data (outcome C in 49, 72 partial moves) shows the current structure is wrong for most cases.

**2. Mirror-aware distinction for ladders (§2).**
- The formula: D = (R \ Y) ∪ (Y^ō \ (X^ō ∪ ↓mirror(R))), plus closure and "no same-dimension substitutes".
- *Fixes:* the dimensional collapse, spurious distinctions on ICD likelihood, recency and partial mitigators, and the nested-factor downplay bug.
- *Cost:* catalog declares dimension, direction and rungs; the labeler must name the rung in R. Solver cost is trivial.

**3. Fact status plus possible-value sets, with stability and relevance (§5).**
- *Fixes:* alleged vs found; credibility; partial application; verdict leakage through tags. It also gives a solver-computed "one question left", `watch_for` and a principled ask trigger.
- *Cost:* one status per fact (cheap); intervals only on disputed facts. Solver: 2 runs per option plus a per-fact loop, polynomial via extreme completions.

**4. `holding_force` (required / permitted / forbidden) plus an authority lattice with Canavotto's no-new-inconsistency test (§3–4).**
- *Fixes:* permissive hindsight rulings (reasonable-commander, IG, deferential appeals) being read as mandates; mixed-authority casebooks; stale precedents; a computable "bounded".
- *Cost:* one enum and one metadata block per case; one lattice per deployer. Solver: filter plus the supporting/conflicting check (Observation 5.5).

**5. Issue-level records with a declared rollup (§6).**
- *Fixes:* DOHA split and cross-guideline findings, "one outweighs nine", and compound partial moves as vectors.
- *Cost:* highest labeling cost for DOHA (one record per SOR subparagraph). Solver is modest.
- Adopt it for the clearance sub-area and for compound Hard-Calls moves. It is not needed for single-question cases.

**Runner-up: the ordinal balance table** (intensity × reliability per equity, §3). Worth adding only after #1–#4. It moves judgment into grading rather than removing it, and Peter's strong/weak support plus ICD likelihood and confidence already carry most of the signal.

---

## Sources (all opened unless marked)

- Horty, J., *The Logic of Precedent: Constraint and Freedom in Common Law Reasoning*, draft (2022) — http://www.horty.umiacs.io/articles/2022-7-15-logic-precedent.pdf
- Horty, J., "Reasoning with dimensions and magnitudes," *AI&Law* 27:309–345 (2019) — https://link.springer.com/article/10.1007/s10506-019-09245-0 (paywalled; abstract and snippets)
- Horty, J., "Modifying the reason model," *AI&Law* 29(2):271–285 (2021) — http://www.horty.umiacs.io/articles/2021-modifying-reason-model.pdf ; https://link.springer.com/article/10.1007/s10506-020-09275-z
- Rigoni, A., "Representing dimensions within the reason model of precedent," *AI&Law* 26 (2018) — https://link.springer.com/article/10.1007/s10506-017-9216-7 (**not read: HTTP 429**)
- Prakken, H., "A formal analysis of some factor- and precedent-based accounts of precedential constraint," *AI&Law* 29(4):559–585 (2021) — https://link.springer.com/article/10.1007/s10506-021-09284-6
- Bench-Capon, T. bibliography (titles/pages for Bench-Capon & Atkinson JURIX 2017/2018; Atkinson et al. JURIX 2013) — https://www.csc.liv.ac.uk/~tbc/W2bib.htm ; the JURIX 2018 PDF (403): https://intranet.csc.liv.ac.uk/~katie/jurix18a.pdf
- van Woerkom, W., Grossi, D., Prakken, H., Verheij, B., "A Fortiori Case-Based Reasoning: From Theory to Data," *JAIR* 81:401–441 (2024) — https://www.jair.org/index.php/jair/article/download/15178/27092
- van Woerkom, W., Grossi, D., Prakken, H., Verheij, B., "Hierarchical models of precedential constraint," *AI&Law* (2026) — https://link.springer.com/article/10.1007/s10506-025-09461-x
- van Woerkom, W. K., *A Fortiori Case-Based Reasoning* (PhD thesis, Utrecht, 2025) — https://research-portal.uu.nl/en/publications/a-fortiori-case-based-reasoning-formal-studies-with-applications-/
- Gould, A., Toni, F., "Neuro-Argumentative Learning with Case-Based Reasoning," PMLR 284:1090–1106 (2025) — https://proceedings.mlr.press/v284/gould25a.html
- Wikipedia, "Smith set" — https://en.wikipedia.org/wiki/Smith_set
- Frank, E., Hall, M., "A simple approach to ordinal classification" (2001) — **[UNVERIFIED], not opened**
- Klatt, M., Schmidt, J., "Epistemic discretion in constitutional law," *I•CON* 10(1):69–105 (2012) — https://academic.oup.com/icon/article/10/1/69/689866
- Sartor, G., "The Logic of Proportionality: Reasoning with Non-Numerical Magnitudes," *German Law Journal* 14(8):1419–1456 (2013) — https://www.cambridge.org/core/journals/german-law-journal/article/logic-of-proportionality-reasoning-with-nonnumerical-magnitudes/FB1F106A1A817D3073DAF6849A9E2DB6 ; also *Riv. filosofia del diritto* 1(2):337–374 (2012) — https://www.rivisteweb.it/doi/10.4477/38866
- Sartor, G., "Consistency in Balancing: From Value Assessments to Factor-Based Rules," in Duarte & Sampaio (eds.), *Proportionality in Law*, Springer, 121–136 (2018) — https://link.springer.com/chapter/10.1007/978-3-319-89647-2_6
- Additional Protocol I, arts. 51, 57 — https://www.ohchr.org/en/instruments-mechanisms/instruments/protocol-additional-geneva-conventions-12-august-1949-and
- ICTY, Final Report to the Prosecutor … NATO Bombing Campaign (2000), ¶¶48–50 — https://www.icty.org/en/press/final-report-prosecutor-committee-established-review-nato-bombing-campaign-against-federal
- Henderson, I., Reece, K., "Proportionality under IHL: The 'Reasonable Military Commander' Standard and Reverberating Effects," 51 *Vand. J. Transnat'l L.* 835 (2018) — https://scholarship.law.vanderbilt.edu/vjtl/vol51/iss3/12/ (abstract only)
- Canavotto, I., "Reasoning with inconsistent precedents," *AI&Law* 33(1):137–166 (2025) — https://link.springer.com/article/10.1007/s10506-023-09382-7
- Fungwacharakorn, W., Bourgne, G., Satoh, K., "An Argumentative Explanation Framework for Generalized Reason Model with Inconsistent Precedents" (arXiv, 2025) — https://arxiv.org/html/2510.19263v1
- Broughton, G., "Vertical precedents in formal models of precedential constraint," *AI&Law* 27(3):253–307 (2019) — https://philpapers.org/rec/BROVPI-2 ; https://link.springer.com/article/10.1007/s10506-019-09244-1
- Di Florio, C., Dong, H., Rotolo, A., "When Precedents Clash" (arXiv 2410.10567) — https://arxiv.org/html/2410.10567 (venue not confirmed)
- Mullins, R., "Weight and Authority in Formal Models of Precedential Constraint," *Jurisprudence* (2025) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5201392 (T&F full text 403: https://www.tandfonline.com/doi/full/10.1080/20403313.2025.2486422)
- Wikipedia, "Jurisprudence constante" — https://en.wikipedia.org/wiki/Jurisprudence_constante
- ICJ Statute, arts. 38, 59 — https://www.icj-cij.org/statute
- Bex, F., van Koppen, P., Prakken, H., Verheij, B., "A hybrid formal theory of arguments, stories and criminal evidence," *AI&Law* 18(2):123–152 (2010) — https://www.ai.rug.nl/~verheij/publications/ail2010.htm
- Verheij, B., "Proof with and without probabilities," *AI&Law* 25(1):127–154 (2017) — https://link.springer.com/article/10.1007/s10506-017-9199-4
- Odekerken, D., Bex, F., Prakken, H., "Justification, stability and relevance for case-based reasoning with incomplete focus cases," ICAIL 2023 — https://webspace.science.uu.nl/~prakk101/papers/icail23obp.pdf
- Odekerken, D., Bex, F., Prakken, H., "Precedent-based reasoning with incomplete information for human-in-the-loop decision support," *AI&Law* 34 (2026) — https://link.springer.com/article/10.1007/s10506-024-09421-x
- Wikipedia, "Wigmore chart" — https://en.wikipedia.org/wiki/Wigmore_chart
- ODNI, ICD 203 *Analytic Standards* — https://archive.dni.gov/files/documents/ICD/ICD-203.pdf
- SEAD 4, *National Security Adjudicative Guidelines* (2017) — https://www.energy.gov/sites/prod/files/2018/02/f48/SEAD4_20170608.pdf
- DOHA, ISCR Case No. 24-00337 (Apr. 10, 2025) — https://doha.ogc.osd.mil/Industrial-Security-Program/Industrial-Security-Clearance-Decisions/ISCR-Hearing-Decisions/2025-ISCR-Hearing-Decisions/FileId/233769/
- Bench-Capon, T., "HYPO's legacy: introduction to the virtual special issue," *AI&Law* 25(2):205–250 (2017) — https://d-nb.info/1139534831/34
- Bench-Capon, T., "Intermediate factors and precedential constraint," *AI&Law* 33(3):827–846 (2025) — https://link.springer.com/article/10.1007/s10506-024-09405-x
- Branting, L. K., "Reasoning with portions of precedents," ICAIL 1991 — **[UNVERIFIED], fetch failed**
