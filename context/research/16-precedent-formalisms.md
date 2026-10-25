# Strand 16 — Formal models of precedential constraint, for the case and mapping schemas

Written 2026-09-28. Purpose: pin down the definitions the harness needs so it can compute follow / distinguish / no-precedent mechanically from structured fields. Builds on what we already use: Zhang, Grabmair, Gray, Ashley et al. (CSLAW '26) for the factor → concern → issue DAG, blocking, downplay/emphasize, significance; and Bench-Capon (CMNA'23), which says to compute constraint on base-level factors and keep intermediate factors for explanation.

Verification tags: **[VERIFIED]** means I opened the page and the claim is on it. **[SECONDARY]** means I couldn't open the primary source, and the claim comes from a named secondary source that I did open. **[UNVERIFIED]** means it isn't checked; don't cite it yet. **[OURS]** marks our own inference or proposal, which no source makes.

Notation used throughout, in plain text:
- `s` is an outcome (side). `~s` is the other side.
- `X^s` means the factors in fact situation X that favour s. `X^~s` means the factors in X that favour ~s.
- `R` is the reason (rule premise) of a precedent: the set of winning-side factors the court treated as sufficient.

---

## 1. Horty's reason model (Horty 2011 ICAIL; Horty & Bench-Capon 2012 AI&Law)

**Citations**
- Horty, J. F. "Reasons and precedent." *Proceedings of the Thirteenth International Conference on Artificial Intelligence and Law (ICAIL 2011)*, ACM Press, 2011, pp. 41–50. [VERIFIED: venue and pages from Horty's publications page. The DOI isn't checked, so I've left it out.]
  - PDF opened: http://www.horty.umiacs.io/articles/2011-icail.pdf (the old umd.edu URL 302-redirects here).
  - Publications page opened: http://www.horty.umiacs.io/publications.html
- Horty, J. F. & Bench-Capon, T. J. M. "A factor-based definition of precedential constraint." *Artificial Intelligence and Law* 20(2), 2012, pp. 181–214. DOI 10.1007/s10506-012-9125-8. [VERIFIED]
  - Preprint opened: http://www.horty.umiacs.io/articles/2012-ail-tbc.pdf
- Cross-check source: Prakken 2021 (see §2) restates both of Horty's models in clean notation and proves the direct test. I used it to recover the over-bars that the PDF-to-text conversion dropped.

**Representation** [VERIFIED, 2012 preprint and 2011 PDF]
- Factors: `F = F^π ∪ F^δ`, split into plaintiff-favouring and defendant-favouring factors.
- Fact situation: `X ⊆ F`.
- Reason: "a set of factors uniformly favoring one side or the other" (2011).
- Rule: `r = Y → s`, "where Y is some set of factors supporting s as an outcome". `Premise(r) = Y` and `Conclusion(r) = s`.
- Case: "c = ⟨X, r, s⟩, where X is a fact situation containing the legal factors present in the case, r is the rule of the case, and s is its outcome". The outcome s is p or d.
- The rule must be applicable in its own case, so `Premise(r) ⊆ X^s`.

**Key definitions** [VERIFIED as text. The over-bars come from Prakken 2021's restatement, which uses `con(c)`.]
- **Def. 2, preference derived from a case:** `W <_c Z` iff `W ⊆ X^~s` and `Premise(r) ⊆ Z`.
  - In words: any reason for the loser that the precedent's losing-side factors contain is weaker than any reason for the winner that contains the precedent's rule premise.
  - The PDF text prints this as "W ⊆ Xs", because the over-bar was lost. Prakken 2021 writes the same condition as "Y ⊆ con(c) and X ⊇ pro(c)", which confirms that the bar belongs there.
- **Def. 3:** `W <_C Z` iff `W <_c Z` for some case c in the case base C.
- **Def. 4, applicable rule:** "a rule r … is applicable in the fact situation X if and only if Premise(r) ⊆ X".
- **Def. 7, consistency:** "C is inconsistent if and only if there are reasons X and Y such that X <_C Y and Y <_C X."
- **Def. 8, precedential constraint:** the court must "base its decision on some rule r leading to an outcome s such that the new case base C ∪ {⟨X, r, s⟩} is itself consistent."
- "At least as strong" (2011): "Y is at least as strong as X whenever … X ⊆ Y."

**Direct test: when a precedent forces an outcome.** This is the "R ⊆ … and … ⊆ …" form.
- Take a precedent `c = ⟨X, r, s⟩` with `R = Premise(r)`, and a new fact situation `Y`. Then c forces outcome s in Y iff both hold:
  - `R ⊆ Y` (equivalently `R ⊆ Y^s`): the precedent's reason is present in the new case.
  - `Y^~s ⊆ X^~s`: every factor in the new case that favours the loser was already present in the precedent and was overridden there.
- [VERIFIED via Prakken 2021, Def. 6 and Prop. 1.] The relevant differences in the reason model, for same-outcome comparison, are `D(c, f) = pro(c) \ pro(f) ∪ con(f) \ con(c)`, where `pro(c)` is the reason and `con(c)` is the precedent's losing-side factors. "Deciding F for s is forced iff there exists c with outcome s and D(c, f) = ∅" (Prop. 1, for consistent case bases).
- Why it follows from Defs. 2, 7 and 8 [OURS, a one-line check]:
  - Suppose the court decided Y for ~s on some rule with premise `R' ⊆ Y^~s`.
  - That decision would add `Y^s <_c' R'`. Since `R ⊆ Y^s`, this gives `R <_C R'`.
  - The precedent already gives `R' <_c R`, because `R' ⊆ Y^~s ⊆ X^~s`.
  - That is a cycle, so the case base would be inconsistent. So the ~s decision is blocked.
- **Result model, for contrast** [VERIFIED, Prakken 2021]: forced iff `X^s ⊆ Y^s` and `Y^~s ⊆ X^~s`. This is the reason model with `R = X^s`. Prakken 2021 §5.2: the reason model "includes Horty's result model as the special case where for all cases the rule equals the case's fact situation."
- 2012 paper, quoted [VERIFIED]: following a binding rule is sufficient for constraint but not necessary (Observation 3). The paper's stated motivation is "to move beyond simple a fortiori reasoning". The court distinguishes when it "formulates another rule r′ supporting the opposite outcome", and that is allowed exactly when the new case base stays consistent.
- Def. 5 (trumped rules) is quoted in the preprint text, but the over-bar on the conclusion was lost in extraction. [UNVERIFIED exact form.]

**Implication for our schema** [OURS]
- A precedent needs three separate fields: `reason` (R, the factors the court said were sufficient), `winner_factors` (X^s, a superset of R), and `loser_factors` (X^~s, everything the court overrode).
- With those fields, the harness can compute the distinction set as `D = (R \ Y^s) ∪ (Y^~s \ X^~s)`.
- Winner-side factors that the precedent had outside R and the new case lacks are **not** distinctions under the reason model. That is the model's whole point, and it is where an LLM is most likely to over-distinguish.

---

## 2. Dimensions and magnitudes (Horty 2019; Prakken 2021)

**Citations**
- Horty, J. F. "Reasoning with dimensions and magnitudes." *Artificial Intelligence and Law* 27(3), 2019, pp. 309–345. DOI 10.1007/s10506-019-09245-0. [VERIFIED]
  - Journal page opened: https://link.springer.com/article/10.1007/s10506-019-09245-0
  - Earlier ICAIL 2017 version opened, for exact definitions: http://www.horty.umiacs.io/articles/2017-icail.pdf
- Prakken, H. "A formal analysis of some factor- and precedent-based accounts of precedential constraint." *Artificial Intelligence and Law* 29(4), 2021, pp. 559–585. DOI 10.1007/s10506-021-09284-6. [VERIFIED; open access]
  - Opened: https://link.springer.com/article/10.1007/s10506-021-09284-6

**Representation** [VERIFIED, Horty 2017/2019 and Prakken 2021]
- A dimension is "an ordered set of legally significant values, where the ordering among values reflects the extent to which the fact that the dimension takes on that particular value favors one side or the other."
  - Prakken's form: `d = (V, ≤_o, ≤_o')` with "v ≤_o v′ iff v′ ≤_o′ v".
  - Horty's form: "p ⪯_s q if and only if q ⪯_~s p". In words, the order for one side is the reverse of the order for the other.
- A dimensional fact situation "is a function mapping each dimension to a value along that dimension": `X = {⟨d, X(d)⟩ : d ∈ D}`.
- **Magnitude factor** (Horty 2017 Def. 3.1): `X ⊨ M^s_{d,p}` iff `p ⪯_s X(d)`. That is, the situation's value on d favours s at least as strongly as the threshold p.
  - Reasons and rules are sets of magnitude factors.
  - A reason is at least as strong as another when "for every factor in the second there is a factor in the first at least as strong".
- **Ordering over whole situations** (Horty 2017 Def. 3.2): "Y is at least as strong as X for the side s … iff X(d) ⪯_s Y(d) for each dimension d."
- The factor model is the special case where each dimension has two values, present or absent. [VERIFIED as a summary of Horty 2019; not quoted verbatim]

**How a fortiori works**
- Dimensional result model [VERIFIED]: the court must decide Y for s iff there is a case c with `Outcome(c) = s` and `Facts(c) ≤_s Y`. That is, on every dimension, the new case is at least as favourable to s as the precedent was.
- Horty 2019 abstract [VERIFIED]: with dimensions, the result and reason models "converge, yielding identical constraint patterns". The paper then proposes two refinements of the reason model to keep them apart:
  - "separated" rules;
  - "acceptable" rules only.
- Prakken 2021 Def. 7 [VERIFIED]: `F ≤_s F'` iff "for all (d,v) ∈ F and all (d,v′) ∈ F′ it holds that v ≤_s v′".
- Prakken 2021 Def. 10 [VERIFIED]: Horty's dimensional reason model with complete rules is forced iff there is `c = (F', R, s)` in CB with `R ≤_s F`.
- **Prakken §5.4, Def. 15** [VERIFIED as summarised]: a less demanding variant, with partial rules. Forced iff there is `c = (F', R, s)` with `R ≤_s F|_R`, i.e. compare only on the dimensions that R mentions.

**Simplest usable definition** [OURS, built on the verified definitions]
1. Give each dimension an ordinal scale and a direction: which side higher values favour.
2. The precedent stores its values and a reason R, which is a partial assignment of thresholds.
3. The precedent **forces** s iff:
   - on every dimension in R, the new value is at least as favourable to s as R's threshold; and
   - on every dimension the court weighed *against* s, the new value is no more favourable to ~s than the precedent's value.

This is the factor test `R ⊆ Y^s` and `Y^~s ⊆ X^~s`, lifted to ordered values.

Caveat: I couldn't read Prakken's full §5.4 text. It is my reading that the second clause is needed so that Def. 15's partial rules don't ignore new, stronger opposing values. **Check this against the paper before relying on it.**

**Implication for our schema** [OURS]
- For balancing variables (severity, imminence, reversibility, degree of intrusion, number affected), use `dimensions: {id, scale: [ordered labels], favours_high: side}`.
- Case fields become value assignments rather than booleans.
- The harness computes componentwise dominance. It needs no weights.
- Alternatively, following Bench-Capon's ascription view, convert dimension values to factors at fixed thresholds when the case is authored. Either way, the verdict stays mechanical.

---

## 3. Hierarchical constraint

### 3a. Canavotto & Horty (ICAIL 2023)

**Citation:** Canavotto, I. & Horty, J. "Reasoning with hierarchies of open-textured predicates." *ICAIL 2023*, ACM, 2023, pp. 52–61. DOI 10.1145/3594536.3595148.
- [VERIFIED: pages from Horty's publications page; abstract from the Semantic Scholar API record]
- Opened: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3594536.3595148?fields=title,authors,abstract,openAccessPdf,venue,year
- The ACM full text (https://dl.acm.org/doi/pdf/10.1145/3594536.3595148) returned **403**, so I couldn't read the body.

**Gist**
- Abstract [VERIFIED]: they develop the reason model over a hierarchy of intermediate legal concepts, "based on the idea that constraint depends, not just on the ultimate decision reached in a case, but on the variety of intermediate decisions that may constitute judicial opinions."
- Each precedent therefore carries a decision, with its own reason, at each intermediate node it resolved, and constraint is computed node by node.
- They then flatten hierarchies, cases and case bases into the standard reason model. They show that hierarchical constraint "may be lost in the flattened setting" and, "more surprisingly, that new patterns of constraint might appear in the flattened setting that were not present in the full hierarchical setting."
- [SECONDARY: Bench-Capon 2024/25 (below)] Bench-Capon calls the hierarchical version H-constraint and the base-level version F-constraint.
  - His "Emma" example: home factors F1, F2, F4 → intermediate Q (behaviour at home); school factors F5, F6 → intermediate R (behaviour at school); then the outcome.
  - Here the flattening yields `F1 ≻ F6`. Bench-Capon argues the right base-level constraint is `F1 ∧ F4 ≻ F6`, because "F1 was never tested against F6 … since F6 had been neutralised by F4."

### 3b. Bench-Capon & Atkinson (ICAIL 2021)

**Citation:** Bench-Capon, T. & Atkinson, K. "Precedential constraint: the role of issues." *ICAIL '21*, São Paulo, ACM, 2021, 10 pp. DOI 10.1145/3462757.3466062. [VERIFIED]
- Opened (author PDF): https://www.csc.liv.ac.uk/~katie/icail21b.pdf

**Gist** [VERIFIED as summarised]
- Horty's whole-case comparison treats a case as an unstructured bag of factors, so a distinction relevant to one issue blocks a precedent on a different issue.
- They restore CATO/IBP-style issues (trade secrets: InfoValuable, SecrecyMaintained, ImproperMeans, InfoUsed, ConfidentialRelationship). Issues are combined by non-defeasible logic, e.g. TradeSecret ∧ Misappropriated ↔ plaintiff.
- They argue: "Comparison (for both the results and the reason models) should be at the level of issues, to ignore irrelevant distinctions, and to reflect legal practice better."
- Their Example 2 is a new case {F6p, F12p, F10d, F16d}.
  - Whole-case: two pro-plaintiff precedents are each blocked by a cross-issue distinction.
  - Issue by issue: each issue is constrained. More cases become constrained, and the results match practice.
- Their conclusion: constraint should be in terms of factors "even if we wish to represent cases in terms of dimensional facts."

### 3c. Related sources opened while checking 3a

- Bench-Capon, T. "Intermediate factors and precedential constraint." *Artificial Intelligence and Law* 33(3), 2025, pp. 827–846 (online 17 May 2024). DOI 10.1007/s10506-024-09405-x. [VERIFIED]
  - Opened: https://link.springer.com/article/10.1007/s10506-024-09405-x
  - Conclusion [VERIFIED]: "intermediate factors do play an important role, but only in explanation, not in constraint." This is the journal-length form of the CMNA'23 argument we already have.
- van Woerkom, W., Grossi, D., Prakken, H. & Verheij, B. "Hierarchical models of precedential constraint." *Artificial Intelligence and Law*, 2026, pp. 1–45. DOI 10.1007/s10506-025-09461-x. [VERIFIED abstract]
  - Opened: https://link.springer.com/article/10.1007/s10506-025-09461-x
  - Four a fortiori models (binary or dimensional × flat or hierarchical), all monotonic; some are conservative extensions of others. The worked example uses penitentiary law.
- Prakken & van Woerkom, "Defending the Hierarchical Result Models of Precedential Constraint," arXiv 2512.13505 (Dec 2025). Abstract read via https://arxiv.org/abs/2512.13505.
  - It argues that some of Bench-Capon's examples treat intermediate factors as dimensions, and that the dimensional hierarchical result model avoids his criticisms.
  - **The HTML full text (https://arxiv.org/html/2512.13505) was refused by the fetch proxy (HTTP 429, rate-limited). I did not read the body.**
- Not opened: Bench-Capon, "A Note on Hierarchical Constraints" (JURIX 2023). https://intranet.csc.liv.ac.uk/~tbc/publications/Jurix23tbc.pdf returned **403**.

**Implication for our schema** [OURS]
- Store per-issue (per-concern) partitions of every case's factors, plus a per-issue resolution with its own reason.
- The harness can then compute the verdict in two modes, and the experiment should say which one it uses:
  - (i) flat base-level constraint, as Bench-Capon argues;
  - (ii) issue-local constraint, as in Bench-Capon & Atkinson 2021 and Canavotto & Horty.
- Mode (ii) is effectively Zhang et al.'s "downplay": a cross-issue distinction isn't significant.

---

## 4. Values

### 4a. Bench-Capon & Sartor 2003

**Citation:** Bench-Capon, T. & Sartor, G. "A model of legal reasoning with cases incorporating theories and values." *Artificial Intelligence* 150(1–2), 2003, pp. 97–143. DOI 10.1016/S0004-3702(03)00108-5. [VERIFIED]
- Opened, abstract only: https://www.sciencedirect.com/science/article/pii/S0004370203001085
- Opened, author copy used for the definitions: https://www.csc.liv.ac.uk/~tbc/publications/aijsartor.pdf

**Representation** [VERIFIED]
- **Def. 1, factor description:** "a three tuple ⟨f, o, v⟩". A factor, the outcome it favours, and the value it promotes.
- **Def. 2, case:** ⟨c, F, o⟩, a case name, a set of factors, and an outcome.
- **Def. 3, rule:** ⟨F, o⟩.
- **Def. 6:** `rval(⟨F, o⟩)` is the set of values promoted by the rule's factors.
- **Def. 8:** rule preference `rpref(r1, r2)`. **Def. 10:** value-set preference `vpref(V1, V2)`.
- **Axiom 1:** "rpref(r1, r2) if and only if vpref(rval(r1), rval(r2))".
- **Theory constructors:**
  - include-case (Def. 13) and include-factor (Def. 14);
  - factors-merging (Def. 15) and rule-broadening (Def. 16);
  - preferences-from-case (Def. 17), which abduces rule and value preferences from a precedent's outcome;
  - rule-preference-from-value-preference (Def. 18);
  - arbitrary rule and value preferences (Defs. 19–20).
- **Explaining a case (Def. 21):** a rule in the theory supports the outcome, and no applicable rule defeats it.
- **Theory evaluation:** coherence, explanatory power, simplicity (fewer factor descriptions), no preference cycles, and few arbitrary preferences.

**How tradeoffs transfer**
- A precedent decided for o, with pro factors P and con factors C, yields `rpref(⟨P,o⟩, ⟨C,~o⟩)` and hence `vpref(rval(P), rval(C))`.
- Through Axiom 1 and Def. 18, that value preference then orders *other* rules, with different factors, that promote the same value sets.
- This is how a decision about one set of facts constrains a case with different facts. [VERIFIED as the mechanism. The phrasing "regardless of differing factor antecedents" is the summariser's, not a quote.]

### 4b. Grabmair's VJAP (2016 thesis; 2017 ICAIL)

**Citations**
- Grabmair, M. *Modeling Purposive Legal Argumentation and Case Outcome Prediction using Argument Schemes in the Value Judgment Formalism.* PhD dissertation, Intelligent Systems Program, University of Pittsburgh, 2016. [VERIFIED]
  - Record opened: http://d-scholarship.pitt.edu/27608/
  - PDF opened: https://d-scholarship.pitt.edu/27608/7/MGrabmair-ETD-v2.pdf
  - The alternative download link returned 403.
- Grabmair, M. "Predicting trade secret case outcomes using argument schemes and learned quantitative value effect tradeoffs." *ICAIL 2017*, ACM. DOI 10.1145/3086512.3086521.
  - **Not read.** ACM returned 403, and Semantic Scholar says the abstract is elided by the publisher.
  - Everything below comes from the thesis.

**Representation** [VERIFIED from the thesis, via summariser]
- Four trade-secret values: property interest, confidentiality interest, fair competition, and usability of public information.
- Factor → value **effects** come in three complementary pairs: "more vs. less legitimate interests, waived vs. protected interests, as well as interference vs non-interference with interests."
  - For example, F15π unique-product has a more-legitimate effect on the property interest.
  - F27δ disclosure-in-public-forum has a waiver effect on the confidentiality interest.
- Effects are **scoped to issues** (leaf legal concepts).
- **Def. 7:** qualitative value effects on a seven-point scale (+++ … −−−).
- **Def. 8:** adversarial value effects θ+ ∈ [0,1] and θ− ∈ [−1,0].
- **Def. 9, value judgment:** "E+oπ(V, s, Fπ) > E−oπ(V, s, Fδ)". In words, the positive effects of the plaintiff's facts on values outweigh the negative effects of the defendant's facts.
- **Def. 10, scoped value judgment:** a value judgment "whose scope is not the global decision outcome but the fulfillment of some intermediate legal concept."

**How tradeoffs transfer** [VERIFIED as scheme names; premises are paraphrased by the summariser]
- The argument scheme "For Local Tradeoff Precedent Analogy" (§4.9.3.1) applies when a precedent resolved a local, issue-scoped tradeoff and the current case shows a similar constellation on that issue. The precedent's balance then carries over.
- Counter-schemes ("Against … from Surplus Factor", §4.9.3.2–4) distinguish on surplus factors present in one case and not the other. A surplus factor that favours the precedent's winner strengthens the analogy.
- Weights for effects are learned by simulated annealing. Confidence then propagates through the argument graph.
- VJAP "does not use such manually chosen knockout factors" and instead uses "generic inter-issue tradeoff argument schemes."

**Could not verify:** the VJAP evaluation's dataset size and accuracy. The summariser said "13 cases", but that is almost certainly a misread. **[UNVERIFIED — do not cite a number.]**

**Implication for our schema** [OURS]
- Balancing cases (national-security equities) are VJAP-shaped, not elements-shaped. Every factor should carry `effects: [{value, direction, kind}]`.
  - `kind` uses VJAP's six types: more-legitimate, less-legitimate, waived, protected, interferes, does-not-interfere.
- Every precedent resolution should record its tradeoff as `winner_values > loser_values` at the issue where the balancing happened.
- The harness can then add a value-level a fortiori test, lifting §1 to values. The precedent's tradeoff transfers when both hold:
  - the new case's winner-side effects include the precedent's winner-side effects;
  - the new case's loser-side effects are contained in the precedent's.
- Don't use learned weights for ground truth. Keep effects ordinal.

---

## 5. IBP knock-out factors (Brüninghaus & Ashley 2003)

**Citations**
- Brüninghaus, S. & Ashley, K. D. "Predicting outcomes of case based legal arguments." *ICAIL 2003*, ACM. DOI 10.1145/1047788.1047838. [Bibliographic record VERIFIED via the Semantic Scholar API: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/1047788.1047838?fields=title,authors,abstract,openAccessPdf,venue,year]
  - **I couldn't read the paper itself.** ACM returned 403 and ResearchGate returned 429, and no open PDF was found.
- Ashley, K. D. & Brüninghaus, S. "Automatically classifying case texts and predicting outcomes." *Artificial Intelligence and Law* 17, 2009, pp. 125–165. DOI 10.1007/s10506-009-9077-9. [VERIFIED]
  - Opened: https://link.springer.com/article/10.1007/s10506-009-9077-9
- Definition taken from Grabmair 2016 (above), p. 35. [SECONDARY]

**What a KO factor is** [SECONDARY + VERIFIED]
- Grabmair 2016, p. 35: "In IBP, knockout factors are used in the explain-away functionality of the algorithm to discard cases that are counterexamples to the hypothesis that, when deciding a contested leaf issue, a set of plaintiff factors trumps a set of defendant factors."
- Also from p. 35: they "are deemed to be so strongly in favor of the defendant that they prevent cases from always being considered useful counterexamples regarding any specific issue with which they are not associated." The factors named there are F20δ, F23δ, F19δ and F27δ.
- Ashley & Brüninghaus 2009 (note 8) lists IBP's KO-Factors as F8 Competitive-Advantage (P), F17 Info-Independently-Generated (D), F19 No-Security-Measures (D), F20 Info-Known-to-Competitors (D), F26 Deception (P), and F27 Disclosure-In-Public-Forum (D). [VERIFIED]
- **The two lists differ, for example on F23 versus F8/F17/F26.** The 2003 original wasn't read, so the canonical list and any selection criterion are [UNVERIFIED].
- In short, a KO factor is a factor strong enough to decide an issue by itself. A precedent that contains a KO factor the new case lacks can be explained away as a counterexample.

**Implication for our schema** [OURS]
- Add `knockout: bool` to factor definitions. The harness rule would be:
  - a KO factor for ~s that is present in the new case and absent from the precedent is always a significant distinction, and can't be downplayed;
  - a precedent that won on a KO factor the new case lacks can't be followed.
- This is Zhang et al.'s "blocking", made explicit per factor.

---

## 6. ANGELIC (Al-Abdulkarim, Atkinson, Bench-Capon)

**Citations**
- Al-Abdulkarim, L., Atkinson, K. & Bench-Capon, T. "A methodology for designing systems to reason with legal cases using Abstract Dialectical Frameworks." *Artificial Intelligence and Law* 24(1), 2016, pp. 1–49. DOI 10.1007/s10506-016-9178-1. [VERIFIED citation and abstract]
  - Opened: https://link.springer.com/article/10.1007/s10506-016-9178-1
  - The PDF body could not be extracted.
- Definitions and example taken from the same authors' technical report, "Evaluating an Approach to Reasoning with Cases Using Abstract Dialectical Frameworks," University of Liverpool ULCS-15-002, 13 Aug 2015. [VERIFIED]
  - Opened: https://wiki.csc.liv.ac.uk/research/techreports/tr2015/ulcs-15-002.pdf
- Follow-up: Atkinson & Bench-Capon, "ANGELIC II: An Improved Methodology for Representing Legal Domain Knowledge," *ICAIL 2023*. DOI 10.1145/3594536.3595137. [Abstract VERIFIED via Semantic Scholar API]

**Representation, in one paragraph** [VERIFIED]
- An ADF is "a tuple ADF = ⟨S, L, C⟩ where S is the set of statements (positions, nodes), L is a subset of S × S, a set of links and C = {C_s∈S} is a set of total functions C_s: 2^par(s) → {t, f}."
- In ANGELIC, the nodes form a tree: the outcome, then issues, then intermediate factors, then base-level (CATO) factors.
- Each non-leaf node's acceptance condition is written "as a set of tests for acceptance and rejection, to be applied in the order given", ending in a default. For example: "Accept F112 if F18. Accept F112 if F8. Accept F112 if F7. Reject F112 if F17. Accept F112."
- The order of the tests encodes the priorities learned from precedents.
- The Prolog program is built "by ascending the ADF, rewriting the acceptance conditions as groups of Prolog clauses."
- Reported result: 78.1% (25/32 cases), which the authors describe as "remarkably close to the 77.8% reported for the version of CATO".

**Implication for our schema** [OURS]
- Our concern/issue DAG can carry an ANGELIC-style ordered acceptance list per node. That gives the harness a deterministic oracle for every intermediate node and for the outcome.
- But an ADF is a *theory*: it already encodes the domain's precedents. Use it to generate or check ground truth in domains we author. Don't use it as a substitute for the precedent-constraint test that the agent is being scored on.

---

## 7. LLMs with factor-based precedent reasoning, 2024–2026 (four items)

1. **Gray, M., Savelka, J., Oliver, W. & Ashley, K.** "Using LLMs to Discover Legal Factors." arXiv:2410.07504 (Oct 2024); JURIX 2024, DOI 10.3233/FAIA241234.
   - The LLM pipeline turns raw opinions into factor lists with definitions. Semi-automated factors predict outcomes "with moderate success, if not yet as well as expert-defined factors."
   - Opened: https://arxiv.org/abs/2410.07504 [VERIFIED abstract]
   - The IOS Press page is robots-blocked, so the JURIX venue comes from the search-result title and DOI only.
2. **Gray, M. A., Zhang, L. & Ashley, K. D.** "Generating Case-Based Legal Arguments with LLMs." *CSLAW '25*, ACM. DOI 10.1145/3709025.3712216.
   - Prompt engineering gets LLMs to produce case-based arguments that follow established argument schemes.
   - [Abstract VERIFIED via https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3709025.3712216?fields=title,authors,abstract,venue,year. The ACM page wasn't opened.]
3. **Savelka, J., Ashley, K. D., Zhang, L. & Gray, M.** "Measuring Faithfulness and Abstention: An Automated Pipeline for Evaluating LLM-Generated 3-ply Case-Based Legal Arguments." arXiv:2506.00694 (May 2025).
   - Setup: 26 trade-secret factors.
   - Findings: models avoid hallucinated factors over 90% of the time; factor utilisation is about 40–85%; most models "failed to follow instructions to stop" when no factors are shared.
   - Opened: https://pith.science/paper/2506.00694 [VERIFIED as summarised; arXiv abs not opened]
4. **Sesodia, M., Petrova, A., Armour, J., Lukasiewicz, T., Camburu, O.-M., Dokania, P. K., Torr, P. & Schroeder de Witt, C.** "AnnoCaseLaw: A Richly-Annotated Dataset For Benchmarking Explainable Legal Judgment Prediction." arXiv:2503.00128 (Feb 2025).
   - 471 US appellate negligence cases with expert annotations. Tasks: judgment prediction, concept identification, and automated annotation.
   - Finding: "application of legal precedent proving particularly difficult."
   - Opened: https://arxiv.org/abs/2503.00128 [VERIFIED]

Seen in search but not opened: "Weight and authority in formal models of precedential constraint" (Taylor & Francis, 2025), https://www.tandfonline.com/doi/full/10.1080/20403313.2025.2486422, returned **403**. It may matter for balancing; worth a manual look.

---

## 8. Putting it together: what the case and mapping schemas need [OURS]

**Case fields**
- `factors[]`: `{id, side, issue, knockout?, effects:[{value, direction, kind}]}`
- `dimensions[]`: `{id, scale, favours_high, issue}`
- `facts`: present factors and dimension values
- `outcome`
- per-issue `resolutions[]`: `{issue, outcome, reason: [factor ids or (dim, threshold)], overridden: [loser-side factors/values], value_tradeoff: {winner_values, loser_values}}`
- `reasons_text` (for explanation only)

**Mapping fields the agent must produce**
- For each difference: `{factor_or_dim, kind: missing_reason | new_opposing | weaker_value | other, issue, significant: bool, why}`
- `verdict`

**Harness computation (per issue, or on the whole case in flat mode)**
- `D = (R \ Y^s) ∪ (Y^~s \ X^~s)`, plus the dimensional analogues:
  - dimensions in R where the new value is below the threshold;
  - opposing dimensions where the new value is stronger for ~s.
- Rules for KO factors:
  - an unmatched KO factor for ~s forces a distinction;
  - a precedent that won on a KO factor absent from the new case yields "no follow".
- Verdicts:
  - **follow** iff the precedent is on point on this issue and D = ∅;
  - **distinguish** iff it is on point and D ≠ ∅;
  - **no precedent** iff it is not on point. Proposed test: R shares no factor or dimension with the new case on any issue the precedent resolved. This follows HYPO's "shares at least one factor" convention; I haven't checked that convention in this session.
- **Significance:** a difference is significant iff it is in D, or is a KO factor. Differences outside D are insignificant; this includes the precedent's non-reason winner-side factors that the new case lacks.
- In issue-local mode, differences that fall in issues the precedent didn't resolve on its reason are insignificant. That is the downplay.
- **Value mode** (balancing): replace the factor sets with value-effect sets and run the same a fortiori test (Bench-Capon & Sartor Axiom 1, VJAP local tradeoff).
- **Consistency guard:** before any run, the harness should check that the case base is consistent in Horty's Def. 7 sense (no `W <_C Z` and `Z <_C W`). Otherwise ground truth is ill-defined. See Canavotto, "Reasoning with inconsistent precedents," *AI&Law* 33 (2025) 137–166, DOI 10.1007/s10506-023-09382-7, listed on her homepage https://sites.google.com/view/ilariacanavotto/home; the paper itself was not opened.

---

## Verification log: pages that could not be read

- https://arxiv.org/html/2512.13505 — fetch proxy HTTP 429 (rate limit). Only the abstract was read, from arxiv.org/abs.
- https://dl.acm.org/doi/pdf/10.1145/3594536.3595148 (Canavotto & Horty 2023) — 403.
- https://dl.acm.org/doi/10.1145/3594536.3595154 — 403.
- https://intranet.csc.liv.ac.uk/~tbc/publications/Jurix23tbc.pdf — 403.
- https://d-scholarship.pitt.edu/downloads/9a277503-2609-4491-9969-1ce0fcfdb8b5 — 403. The alternative thesis PDF worked.
- Grabmair ICAIL 2017 — ACM 403, abstract elided.
- Brüninghaus & Ashley ICAIL 2003 — no open copy. ResearchGate 429.
- https://link.springer.com/content/pdf/10.1007/s10506-016-9178-1.pdf — body not extractable. The 2015 tech report was used instead.
- https://ebooks.iospress.nl/doi/10.3233/FAIA241234 — robots-disallowed.
- https://www.tandfonline.com/doi/full/10.1080/20403313.2025.2486422 — 403.
- https://dblp.org/db/conf/icail/icail2023.html — robots-disallowed.
- Horty PDFs (2011, 2012): the text converter dropped the over-bars. Side assignments were recovered from Prakken 2021's restatement.
