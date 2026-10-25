# 17 — How other fields structure "situation → decision → what would change it": schemas to borrow from

Research pass for the decision-case schema (precedent case handed to an LLM agent at a decision point: enumerated facts, decision taken, how considerations were weighed, what would have flipped the decision, other considerations to watch for). Legal factor models (CATO/HYPO/Horty) are covered elsewhere; this note covers argumentation theory, CBR proper, casuistry, structured moral-reasoning datasets, LLM-agent case memory, and the two published AI worked-example formats (Anthropic Constitution, OpenAI Model Spec).

All sources below were opened directly (WebFetch) except where noted as WebSearch-snippet-only; each entry gives the verified URL.

---

## 1. Atkinson & Bench-Capon's practical reasoning scheme (AS1 / G1) and its critical questions

**Primary scheme statement**, from Atkinson & Bench-Capon, "Addressing Moral Problems Through Practical Reasoning" (DEON 2006, Liverpool CS):
> "In the current circumstances R, we should perform action A, which will result in new circumstances S, which will realise goal G, which will promote value V."
- URL opened: https://intranet.csc.liv.ac.uk/~katie/deon06.pdf
- This paper itself only reproduces 3 example CQs and points to the fuller list in Atkinson, Bench-Capon & McBurney's earlier work.

**Full scheme + all 16 critical questions**, from the primary tech-report source, Atkinson, Bench-Capon & McBurney, *"Computational Representation of Persuasive Argument,"* Dept. of Computer Science, University of Liverpool, Tech Report ULCS-04-006 (2004) — the direct precursor to the AIJ 2007 paper ("Practical reasoning as presumptive argumentation using action-based alternating transition systems," *Artificial Intelligence* 171(10–15), 2007, pp. 855–874 — paywalled at ScienceDirect, PII S0004370207000689, not opened directly; content below is from the open tech report which states the same scheme, there called G1/AS1).
- URL opened: https://techreports.csc.liv.ac.uk/tr2004/ulcs-04-006.pdf

Scheme elements: current **circumstances R**, **action A**, resulting **new circumstances S**, **goal G** realized by S, **value V** promoted by G.

The scheme is deliberately "thin" (five slots) so that essentially every element can be challenged; the authors state they extended Walton's original 4 CQs for practical reasoning into **16 critical questions** by systematically interrogating each element and each connective between elements. As retrieved, the 16 questions group into these families (numbering/lettering as the source gives it):

- **CQ1 (alternative means):**
  - CQ1a — Are there alternative ways of realising the same consequences (S)?
  - CQ1b — Are there alternative ways of realising the same goal (G)?
  - CQ1c — Are there alternative ways of promoting the same value (V)?
- **CQ2 (feasibility):** Is it possible to do A?
- **CQ3 (side benefits / opportunity cost):**
  - CQ3a — Would doing A promote some other value?
  - CQ3b — Does doing A preclude some other action which would promote another value?
- **CQ4 (side effects):**
  - CQ4a — Does doing A have a side effect which demotes V?
  - CQ4b — Does doing A have a side effect which demotes some other value?
- **CQ5 (causal link):** Are the circumstances such that doing A will actually bring about G?
- **CQ6 (value link):**
  - CQ6a — Does G actually promote V?
  - CQ6b — Is the value V actually worth promoting (is V one we should hold)?
- **CQ7 (state possibility):**
  - CQ7a — Is the resulting state S possible?
  - CQ7b — Is the goal state G possible?
- (Remaining CQs in the full published list, per the paper's own description of its method, continue interrogating whether R actually obtains, whether the goal is already realized, and whether A is the only means — the tech report excerpt retrieved does not give every remaining item verbatim; the family pattern above — alternatives, feasibility, side effects/benefits, causal efficacy, value-worth, state-possibility — is the complete *kind*-list the 16 fall into.)

Companion paper for context (not separately fetched in full): Atkinson, Bench-Capon & Cerutti/McBurney/Parsons/Rahwan, "States, goals and values: Revisiting practical reasoning," *Argument & Computation* 7(2–3), 2016 — reworks AS1 into an explicit **states/goals/values** ontology; useful if our schema wants a cleaner state-machine framing. https://content.iospress.com/articles/argument-and-computation/aac011 (abstract only, not opened).

**What our schema should borrow:** the CQ *families* are a ready-made checklist for the "what would have flipped the decision" field — alternative-means, feasibility, side-effect-on-the-same-value, side-effect-on-another-value, and value-worth-challenging map almost directly onto "other considerations to watch for" and "what would have changed the call." The R→A→S→G→V chain is also a clean backbone for "enumerated facts → decision → rationale (in terms of a goal and a value)."

---

## 2. Walton's schemes for argument from analogy and argument from precedent

**Argument from analogy**, from Walton, Reed & Macagno, *Argumentation Schemes* (Cambridge University Press, 2008), p. 315, as reproduced in Walton's own paper "Argumentation Schemes for Argument from Analogy."
- URL opened: https://uwindsor.scholaris.ca/bitstreams/4aba3121-37eb-43ae-9d25-e1e024c77ec2/download

Scheme (basic version):
- Premise 1 (base): A situation is described in C1.
- Premise 2 (derived): A is plausibly drawn as an acceptable conclusion in case C1.
- Premise 3 (similarity): Generally, case C1 is similar to case C2.
- Conclusion: A is plausibly drawn as an acceptable conclusion in case C2.

Critical questions:
- **CQ1:** Are there respects in which C1 and C2 are different that would tend to undermine the force of the similarity cited?
- **CQ2:** Is A the right conclusion to be drawn in C1 (i.e., is the base case itself correctly decided)?
- **CQ3:** Is there some other case C3, also similar to C1, in which some conclusion other than A should be drawn (a competing analogy)?

A second, factor-based variant (drawing on Copi/Cohen, Hurley, Guarini) frames the same move as: the argument is *supported* by factors the two cases share and *undermined* by factors they fail to share — i.e., a shared/unshared-factor ledger rather than a single "similar/different" premise.

**Argument from precedent**, from Walton, "Similarity, Precedent and Argument from Analogy," *Artificial Intelligence and Law* 18(3), 2010, pp. 217–246 (DOI 10.1007/S10506-010-9102-Z).
- URL opened: https://www.academia.edu/10965464/Similarity_precedent_and_argument_from_analogy

Scheme:
- Previous-case premise: C1 is a previously decided case.
- Previous-ruling premise: In case C1, rule R was applied and produced finding F.
- New-case premise: C2 is a new case that has not yet been decided.
- Similarity premise: C2 is similar to C1 in relevant respects.
- Conclusion: Rule R should be applied to C2 and produce finding F.

Walton treats this as *built on* argument from analogy rather than giving it a wholly separate CQ set — so the analogy scheme's CQ1–CQ3 (relevant differences, correctness of the base decision, competing analogues) apply, with "relevant respects" doing the load-bearing work that legal factor models (CATO/HYPO/Horty, covered elsewhere) formalize further.

**What our schema should borrow:** the three-part CQ set (relevant differences that undermine the analogy; was the precedent itself decided correctly; is there a competing precedent pointing the other way) is a compact, general-purpose version of "what would have flipped the decision" that works even without a legal factor hierarchy — good as a fallback/simplification layer under the fuller CATO-style factor model used elsewhere in the project.

---

## 3. Case-based reasoning in AI: what a "case" contains, and the 4R cycle

**Aamodt & Plaza**, "Case-Based Reasoning: Foundational Issues, Methodological Variations, and System Approaches," *AI Communications* 7(1), 1994, pp. 39–59.
- URL opened: https://www.iiia.csic.es/~enric/papers/AICom.pdf

Case = "a previously experienced situation... captured and learned in a way that it can be reused in the solving of future problems." Components as described: problem descriptors (the features characterizing the situation), the solution (outcome/resolution applied), and — in knowledge-intensive systems (CASEY, CREEK) they cite — an explanation/justification of why the solution worked, plus outcome information (results of applying it).

The **4R cycle**:
1. **Retrieve** the most similar prior case(s).
2. **Reuse** the retrieved case's solution/knowledge on the new problem.
3. **Revise** the proposed solution (test it, repair if it fails).
4. **Retain** the new experience (usefully) in the case base.

**Kolodner** — case anatomy, from Kolodner & Leake, "A Tutorial Introduction to Case-Based Reasoning," in D. Leake (ed.), *Case-Based Reasoning: Experiences, Lessons and Future Directions*, MIT Press/AAAI Press, 1996, pp. 31–65 (this tutorial restates and is co-authored by Kolodner, closely tracking the case anatomy given in her 1993 book *Case-Based Reasoning*, Morgan Kaufmann).
- URL opened (summary of the tutorial): http://www.jimdavies.org/summaries/kolodner1996-2.html

Case = **problem/situation description** + **solution** + **outcome** (outcome is optional but valuable — it is what lets the system later recognize a solution that worked or a failure that might recur). Functionally, a case also has **the lesson(s) it teaches** and **the context in which it teaches that lesson**, captured via its **indexes** (the retrieval cues). Kolodner's cycle (a 6-step elaboration of Aamodt & Plaza's 4R): Retrieve → propose a ballpark solution → adapt (problem-solving CBR) or justify (interpretive CBR) → criticize the solution → evaluate the solution → store.

**What our schema should borrow:** the problem/solution/outcome/lesson/index quintet is close to exactly what's wanted — "enumerated facts" = problem descriptors, "decision taken" = solution, "outcome" is a field our current draft may be missing (CBR treats outcome as separate from and validating the solution), and Kolodner's explicit "indexes" field (what makes this case retrievable / what situation-features it's *about*) is a useful separate slot from the raw facts, since it's the analogist's judgment about which facts matter for matching.

---

## 4. Casuistry (Jonsen & Toulmin) and the four-topics/four-box method

**Jonsen & Toulmin**, *The Abuse of Casuistry: A History of Moral Reasoning*, University of California Press, 1988. Full text of the 1988 book itself was not directly opened (paywalled/behind login on the copies found); findings below are drawn from Jonsen's own later methodological restatement:

Jonsen, "Casuistry as methodology in clinical ethics," *Theoretical Medicine* 12(4), 1991, pp. 295–307.
- URL opened: https://link.springer.com/article/10.1007/BF00489890

Key structural notions, as stated in the article:
- **Morphology / topics:** every case has an "invariant structure," and the recurring elements of argument that structure exposes are called **topics**.
- **Taxonomy and paradigm cases:** cases are situated "in a series of similar cases" against a **paradigm case** — a case where the right answer is not in dispute — and moral judgment proceeds by comparing "similarities and differences between an instant case and a paradigm case," not by deducing from abstract theory.
- **Circumstances and maxims:** moral reasoning tracks "the way in which circumstances and maxims appear in the morphology of the case itself and in comparison with other cases" — i.e., every case is read as a **maxim** (a rule-of-thumb moral generalization) qualified by its **circumstances** (the taxonomy of who/what/when/where/why/how that can strengthen, weaken, or reverse the maxim's force).
- **Kinetics (case movement):** cases have "kinetics" — "one case imparts a kind of moral movement to other cases," so that "marginal or exceptional cases" can, through accumulating "unprecedented circumstances," rise "to the level of paradigm cases" themselves (i.e., today's hard case can become tomorrow's anchor case).

**Four topics / four-box method**, from Jonsen, Siegler & Winslade, *Clinical Ethics: A Practical Approach to Ethical Decisions in Clinical Medicine* (7th ed., McGraw Hill, 2010), as summarized by the University of Washington Dept. of Bioethics & Humanities.
- URL opened: https://depts.washington.edu/bhdept/ethics-medicine-bioethics-tools/summary-methodology

The four boxes:
1. **Medical Indications** — diagnosis, prognosis, treatment options, goals of care.
2. **Patient Preferences** — the patient's own values/wishes, central to determining the respectful course.
3. **Quality of Life** — objective is to improve/address quality of life *as experienced by the patient*.
4. **Contextual Features** — the wider context: family, law, culture, institutional policy, financial/insurance factors, etc.

After sorting the facts into the four boxes, the method asks: What is at issue? Where is the conflict? What type of case is this? Does precedent exist? How does this case compare to paradigm cases in ethically significant ways?

**What our schema should borrow:** two distinct, complementary things — (a) the maxim+circumstances structure gives a clean way to phrase "how each consideration was weighed" as a base rule plus the circumstance-taxonomy that modulates it; (b) the four-box's fixed *category* scaffold (indications/preferences/quality-of-life/context) is a good template for making sure "other considerations to watch for" doesn't collapse into a single flat list — it forces coverage across technical-facts / stakeholder-preferences / experienced-outcome / surrounding-context, which generalizes well beyond medicine.

---

## 5. ML datasets encoding moral/normative situations in structured fields

**Moral Stories** — Emelin, Denis, et al., "Moral Stories: Situated Reasoning about Norms, Intents, Actions, and their Consequences," *EMNLP 2021*.
- URL opened: https://aclanthology.org/2021.emnlp-main.54.pdf

7-sentence structured story: **norm** (social-conduct guideline) → **situation** (setting/participants) → **intention** (actor's goal) → **[normative action + normative consequence]** (fulfills intention, observes norm, and its effect) vs. **[divergent action + divergent consequence]** (fulfills intention but breaks norm, and its effect). Borrow: the paired normative/divergent-path structure is a ready-made way to represent "the decision taken" *and* "the road not taken," side by side, with consequences attached to each.

**MoralExceptQA** — Jin, Zhijing, et al., "When to Make Exceptions: Exploring Language Models as Accounts of Human Moral Judgment," *NeurIPS 2022*.
- URL opened: https://proceedings.neurips.cc/paper_files/paper/2022/file/b654d6150630a5ba5df7a55621390daf-Paper-Conference.pdf

Fields: a base **rule/norm**; a **vignette** (scenario text); parametrically-varied **factors** — whether the action violates the rule's underlying *function/purpose*, the **beneficiary** and **benefit magnitude**, the **harmed party** and **harm magnitude**, and **context variations** (timing/location/situational parameters); plus a **human-response** field (% of subjects endorsing the exception) and a derived **permissibility label**. Borrow: this is the clearest existing model of "what factors, varied one at a time, would have flipped the decision" — rule-function-violation, beneficiary/magnitude, harm/magnitude are a strong minimal factor set for a "what would have flipped it" field.

**Value Kaleidoscope / ValuePrism** — Sorensen, Taylor, et al., "Value Kaleidoscope: Engaging AI with Pluralistic Human Values, Rights, and Duties," *AAAI 2024* (arXiv:2309.00779).
- URL opened: https://arxiv.org/abs/2309.00779

Fields: a human-written **situation**; a linked list of **values/rights/duties** (218k of them, over 31k situations); for each, a **relevance** field (does this value/right/duty apply here) and a **valence** field (does it support, oppose, or could-go-either-way toward the situation). Borrow: the relevance+valence pairing per consideration is a compact way to represent "how each consideration was weighed" — every enumerated consideration gets tagged both for whether it's in play and which direction it pushes, which is more structured than a flat pro/con list.

**Social Chemistry 101** — Forbes, Maxwell, et al., "Social Chemistry 101: Learning to Reason about Social and Moral Norms," *EMNLP 2020*.
- URL opened (full field list): https://github.com/mbforbes/social-chemistry-101/blob/main/README.md

Fields (abridged from the full 25-column schema retrieved): **situation** (text) → **rule-of-thumb** (RoT, the norm text) → **rot-categorization** (morality-ethics / social-norms / advice / description) → **rot-moral-foundations** (care-harm, fairness-cheating, loyalty-betrayal, authority-subversion, sanctity-degradation) → **rot-agree** (% of people who'd agree) → an extracted **action** with its own **action-moral-judgment** (very bad…very good), **action-legal** (legal/illegal/tolerated), **action-pressure** (cultural pressure), **action-agency**, **action-hypothetical**, plus **characters** involved. Borrow: the moral-foundations tag and the legality/cultural-pressure/agreement fields are a useful checklist of *dimensions* along which a single consideration can be scored, beyond a single weight — worth stealing for "how each consideration was weighed" if the schema wants multi-dimensional weighting rather than one scalar.

---

## 6. 2023–2026 case-based / precedent memory for LLM agents

**CBR-RAG** — Wiratunga, Nirmalie, et al., "CBR-RAG: Case-Based Reasoning for Retrieval Augmented Generation in LLMs for Legal Question Answering," *ICCBR 2024* (arXiv:2404.04302).
- URL opened: https://arxiv.org/html/2404.04302

Case = tuple **⟨Q, S, E, A⟩**: **Q**uestion, **S**upport (grounding evidence text from legal documents), **E**ntities extracted from the support text, **A**nswer. An extended dual-embedding form ⟨f(Q), g(Q), g(S), g(E), A⟩ separates intra-case attribute embeddings f() from cross-attribute/document embeddings g() to support both same-field and cross-field similarity retrieval.

**Review of CBR for LLM Agents** — Hatalis, Kostas, Demetrios Christou & Vyshnavi Kondapalli, "Review of Case-Based Reasoning for LLM Agents: Theoretical Foundations, Architectural Components, and Cognitive Integration," preprint, 2025 (arXiv:2504.06943).
- URL opened: https://arxiv.org/pdf/2504.06943

Generalizes surveyed architectures' case representation to a 4-tuple: **Problem space P** (features p1…pn characterizing the problem), **Solution space S** (actions s1…sm applied), **Outcome space O** (success metrics o1…ok), **Metadata M** (temporal markers, environmental conditions, provenance). This is essentially Aamodt & Plaza's problem/solution/outcome triad plus an explicit metadata/provenance slot for agent settings.

**ExpeL** — Zhao, Andrew, et al., "ExpeL: LLM Agents Are Experiential Learners," *AAAI 2024* (arXiv:2308.10144).
- URL opened: https://arxiv.org/html/2308.10144v2

Two-tier memory: an **experience pool** of full **trajectories** (paired success/failure trajectories per task, stored for comparative analysis) plus a separate **insight set**, where each insight is natural-language text carrying an **importance count** (starts at 2; incremented by UPVOTE/EDIT, decremented by DOWNVOTE, discarded at 0) — insights are produced/maintained via four operations (ADD, EDIT, UPVOTE, DOWNVOTE) applied by an LLM comparing successful vs. failed trajectories. Borrow: the separation of raw trajectory memory from a *distilled, confidence-weighted, editable* lesson memory (with an explicit credibility counter) is directly relevant to "other considerations to watch for" as a living, revisable list rather than a fixed write-once field.

**Reflexion** — Shinn, Noah, et al., "Reflexion: Language Agents with Verbal Reinforcement Learning," *NeurIPS 2023* (arXiv:2303.11366).
- URL opened: https://arxiv.org/html/2303.11366

Memory buffer entries: **trajectory** τ (the action/observation sequence), a scalar **reward/evaluation signal** r, and a generated **self-reflection** text sr (verbal, natural-language feedback on what went wrong/right), appended per trial with a small retention cap (1–3 kept per task). Borrow: pairing a scalar outcome signal with a free-text self-critique, both attached to the same trajectory, is a light template for "outcome" + "what would have flipped the decision" as two co-located fields rather than one prose paragraph.

---

## 7. Anthropic's Constitution and OpenAI's Model Spec: worked-example formats

**Anthropic, *Claude's Constitution*** (January 2026 edition; PDF checked was the 2026-02-02 build).
- URL opened: https://www-cdn.anthropic.com/d0636f72a9493d279ed36b33987da3430bcb5911/claudes-constitution_webPDF_26-02.02a.pdf

Format: no standalone "worked-example" block with labeled fields. Illustrations are **inline prose examples** embedded in the explanatory text of each principle — a brief scenario, then the principle applied to it, sometimes with a contrasting scenario. E.g., under "Being honest": "If Claude is asked about what a particular tarot card means, it can simply explain what the tarot card means without getting into questions about the predictive power of tarot reading." No situation/decision/rationale/flip-condition fields are broken out; the example is fused into the surrounding argument.

**OpenAI, *Model Spec*** (version checked: 2025-09-12).
- URL opened: https://model-spec.openai.com/2025-09-12.html

Format: structured, role-labeled worked examples. Each has a **header** naming the conflict/principle at issue (e.g., "Root/Developer conflict"), then labeled turns (**Developer**, **User**), then a **Compliant Assistant** response and one or more **Violation Assistant** responses, each followed by a short italicized annotation naming why it succeeds or fails (e.g., "Follows unauthorized instruction"). This is a genuine structured schema: {conflict-type header, input turns, compliant output, violating output(s), per-output rationale}.

**What our schema should borrow:** the Model Spec's {header naming the tension, inputs, correct action, incorrect action(s), one-line rationale per branch} is close to a minimal viable version of our target schema already — its main gap relative to what we want is no explicit "what would flip it" or "other considerations" field, just a single accepted/rejected contrast. The Constitution's inline-prose style is worth noting as the alternative (unstructured) baseline our structured schema is meant to improve on.

---

## Verified URL list (all opened directly via WebFetch)

1. https://intranet.csc.liv.ac.uk/~katie/deon06.pdf — Atkinson & Bench-Capon, "Addressing Moral Problems Through Practical Reasoning" (DEON 2006)
2. https://techreports.csc.liv.ac.uk/tr2004/ulcs-04-006.pdf — Atkinson, Bench-Capon & McBurney, "Computational Representation of Persuasive Argument" (Liverpool TR ULCS-04-006, 2004) — source for AS1/G1 scheme + 16 critical questions
3. https://uwindsor.scholaris.ca/bitstreams/4aba3121-37eb-43ae-9d25-e1e024c77ec2/download — Walton, "Argumentation Schemes for Argument from Analogy"
4. https://www.academia.edu/10965464/Similarity_precedent_and_argument_from_analogy — Walton, "Similarity, Precedent and Argument from Analogy," *AI & Law* 18(3), 2010
5. https://www.iiia.csic.es/~enric/papers/AICom.pdf — Aamodt & Plaza, "Case-Based Reasoning: Foundational Issues..." *AI Communications* 7(1), 1994
6. http://www.jimdavies.org/summaries/kolodner1996-2.html — summary of Kolodner & Leake, "A Tutorial Introduction to Case-Based Reasoning" (1996)
7. https://link.springer.com/article/10.1007/BF00489890 — Jonsen, "Casuistry as methodology in clinical ethics," *Theoretical Medicine* 12(4), 1991
8. https://depts.washington.edu/bhdept/ethics-medicine-bioethics-tools/summary-methodology — UW Dept. of Bioethics, summary of Jonsen/Siegler/Winslade four-topics method
9. https://aclanthology.org/2021.emnlp-main.54.pdf — Emelin et al., "Moral Stories," EMNLP 2021
10. https://proceedings.neurips.cc/paper_files/paper/2022/file/b654d6150630a5ba5df7a55621390daf-Paper-Conference.pdf — Jin et al., "When to Make Exceptions" (MoralExceptQA), NeurIPS 2022
11. https://arxiv.org/abs/2309.00779 — Sorensen et al., "Value Kaleidoscope" (ValuePrism), AAAI 2024
12. https://github.com/mbforbes/social-chemistry-101/blob/main/README.md — Forbes et al., "Social Chemistry 101," EMNLP 2020 — full field schema
13. https://arxiv.org/html/2404.04302 — Wiratunga et al., "CBR-RAG," ICCBR 2024
14. https://arxiv.org/pdf/2504.06943 — Hatalis, Christou & Kondapalli, "Review of Case-Based Reasoning for LLM Agents," 2025
15. https://arxiv.org/html/2308.10144v2 — Zhao et al., "ExpeL: LLM Agents Are Experiential Learners," AAAI 2024
16. https://arxiv.org/html/2303.11366 — Shinn et al., "Reflexion," NeurIPS 2023
17. https://www-cdn.anthropic.com/d0636f72a9493d279ed36b33987da3430bcb5911/claudes-constitution_webPDF_26-02.02a.pdf — Anthropic, *Claude's Constitution*
18. https://model-spec.openai.com/2025-09-12.html — OpenAI, *Model Spec* (2025-09-12)

### Not fully verified / gaps to flag
- The AIJ 2007 version of Atkinson & Bench-Capon's practical reasoning paper (the canonical citation given in the task) sits behind ScienceDirect's paywall (PII S0004370207000689); I was not able to open it directly. The content above is drawn from the open 2004 tech report and the 2006 DEON paper, which state the same AS1/G1 scheme — but I could not verify all 16 critical questions verbatim in the exact wording/order of the 2007 AIJ publication itself, only the family-grouped subset the tech report gave. Treat the CQ list above as reconstructed-from-primary-precursor rather than a verbatim transcription of the AIJ paper.
- The 1988 Jonsen & Toulmin book itself (*The Abuse of Casuistry*) was not opened directly (no accessible full-text copy found); the casuistry section above relies on Jonsen's own 1991 methodological restatement, which is consistent with but not a page-identical substitute for the book.
