# Strand 22 — How analogy works in minds, what a "reason" is, and how non-common-law traditions reason from a case

Research agent, 2026-09-29. Tags: **[VERIFIED]** I opened the page and the claim is there; **[SECONDARY]** from a named secondary source I opened; **[UNVERIFIED]** not checked; **[OURS]** my inference. Strand 16/17/18 material is cited, not re-surveyed.

## Bottom line

1. **Fixed polarity breaks.** Dancy's holism, the Mohist warning about parallel inference, and the qiyās objection *qalb* all say a feature's direction depends on context. Horty's fix keeps the solver generalist: reversal = **undercut + a second default**, plus **modifier** facts (enable/disable/intensify/attenuate) that act on factors, not options. [OURS on VERIFIED sources]
2. **Authority is not a heavy factor.** A Razian order is a *protected* reason: a reason to comply plus an **exclusionary** reason that removes some other reasons from the comparison, up to a limit ("manifestly unlawful," Rome Statute Art. 33). Horty formalizes exclusion as a default that pushes others below threshold. This computes as a solver filter pass. [OURS on VERIFIED sources]
3. **N-ary outcomes get a semantics.** Qing analogical sentencing = anchor statute ± **degrees**. Talmudic *dayo* caps an a fortiori conclusion at the source's ruling. Together, a precedent gives a **bound** on an ordered outcome ladder, not a point. That fits 72/100 partial moves. [OURS on VERIFIED sources]
4. **Serve two cases; retrieve in two stages.** Comparing two cases raised transfer from 19% to 48% (Gentner et al. 2003). Surface-similarity retrieval is what humans default to and what fails on far analogies, for people and for LLMs. [VERIFIED results; OURS implications]
5. **Cross-tradition surprises.**
   - Qing law and the Talmud both **allocate the power to analogize by authority**. That grounds "the harness, not the model, decides act or ask."
   - Qiyās's *ʿilla* (manifest, determinable ratio) vs *ḥikma* (unmeasurable purpose) is almost exactly factor vs equity. It is a doctrinal argument for scoring factors, not equities.

---

## Part A — Cognitive science of analogy

### A1. Structure-mapping theory (Gentner 1983)

**Source.** Dedre Gentner, "Structure-Mapping: A Theoretical Framework for Analogy," *Cognitive Science* 7(2): 155–170 (1983). https://groups.psych.northwestern.edu/gentner/papers/Gentner83.2b.pdf

**What a case is.** A case is a structured description made of objects plus predicates. Attributes are one-place predicates; relations take two or more arguments. Gentner's example: "COLLIDE (x,y) is a relation, while LARGE (x) is an attribute" (p. 157) [VERIFIED]. Higher-order relations take propositions as arguments, as in CAUSE [COLLIDE (x,y), STRIKE (y,z)] (p. 158) [VERIFIED].

**How reasoning proceeds.**
- An analogy maps relations, not attributes: "Relations between objects, rather than attributes of objects, are mapped from base to target" (p. 155) [VERIFIED].
- Which relations get mapped is governed by the **systematicity principle**: "A predicate that belongs to a mappable system of mutually interconnecting relationships is more likely to be imported into the target than is an isolated predicate" (p. 162) [VERIFIED].
- Gentner types comparisons by what they share [VERIFIED, pp. 159–160]:
  - literal similarity: many attributes and many relations;
  - analogy: few attributes, many relations;
  - abstraction: relations with generalized objects;
  - mere appearance: attributes only.

**What it implies for the Benchbook.**
- A catalog factor is, formally, an attribute of the situation: "B3 is present." A case's reason set is therefore a set of attributes. On Gentner's terms, the Benchbook compares cases by something closer to literal similarity over pre-abstracted attributes than by analogy. [OURS]
- The catalog is not naive. Each factor is already an abstraction that hides a relation. "Partner has operational need" is really NEEDS(partner, info, for-operation). What is lost is the **connections between factors**: which fact causes which risk to which equity, for whom, and what goal the decision served. [OURS]
- The DOHA pilot shows the cost. Allegation-level structure broke 6 of 10 pilot cases:
  - split findings;
  - one unmitigated allegation outweighing nine mitigated ones;
  - findings that cross guidelines.

  These are all structure among facts, where mitigator M applies to allegation 3 and not to allegation 7. A flat bag cannot say that. [OURS on the brief's pilot data]

**Concrete change (minimal relational layer).** Add two optional fields per fact [OURS]:
- `about`: a small closed vocabulary of role slots per sub-area. For release decisions that could be `partner`, `source`, `originator`, `requester`, `affected_person`.
- `bears_on`: the fact id or allegation id that a modifier or mitigator attaches to.

Solver checks this makes computable:
- **(a) One-to-one role alignment.** If the model maps precedent role *p* to situation role *s*, every mapped factor pair must have matching `about` slots. This is Gentner's one-to-one plus parallel-connectivity constraint, cut down to role labels.
- **(b) Grouped evaluation.** Facts can be grouped by `bears_on`, so the solver evaluates each allegation as a sub-case and then applies a combination rule, such as "any unmitigated disqualifying allegation → deny."

This is still a set computation, just over a partition of facts instead of one bag.

**Best argument against.** Full SME-style predicate calculus per case is beyond one labeler. The factors are already the abstraction a structure-mapper would produce after alignment. If sub-areas rarely have several allegations or parties per case, the role layer earns little. [OURS]

### A2. MAC/FAC: cheap surface retrieval, then structural evaluation (Forbus, Gentner & Law 1995)

**Source.** Kenneth D. Forbus, Dedre Gentner & Keith Law, "MAC/FAC: A Model of Similarity-Based Retrieval," *Cognitive Science* 19(2): 141–205 (1995); the lab PDF header reads 1994. https://groups.psych.northwestern.edu/gentner/papers/ForbusGentnerLaw94.2b.pdf

**Mechanism.**
- **MAC** ("many are called") reduces each structured description to a flat **content vector** of functor counts and scores candidates by dot product (pp. 162–163) [VERIFIED]. MAC is, in effect, a flat bag of factors.
- **FAC** ("few are chosen") runs SME on the survivors to get structural alignments, soundness scores, and candidate inferences (pp. 148–150) [VERIFIED].
- The rationale for two stages is a cost trade-off. Many stored cases and fast human access imply a cheap process, while judging soundness implies an expensive one (p. 147) [VERIFIED].
- The key empirical dissociation: "Surface similarity was the best predictor of memory access, and structural similarity was the best predictor of subjective soundness" (p. 145) [VERIFIED].
- Human retrieval rates in their Table 2 were literal similarity .73, surface-only .53, true analogy .12 (p. 165) [VERIFIED]. True analogies are rarely retrieved spontaneously.

**What it implies for the harness's reader.** [OURS]
1. **Build the reader as MAC then FAC, not embeddings alone.** An embedding retriever over case prose is a MAC stage. It will preferentially return surface matches from the same sub-area vocabulary. The FAC stage should be the solver itself:
   - the model first tags the situation;
   - the solver then re-ranks the top k retrieved cases by structural fit:
     - (i) reason-set coverage, i.e., is R ⊆ situation factors;
     - (ii) number of Horty distinctions, D = (R \ Y) ∪ (Y^ō \ X^ō), fewer is better;
     - (iii) overlap of the equities served.

   This fits the existing pipeline: tag, then retrieve by tags, then serve 1–3 cases. It also answers the chicken-and-egg problem of retrieving by tags that do not exist yet.
2. **Put lures in the training mixture on purpose.** Serve some "mere-appearance" cases: same sub-area and vocabulary, different reason structure, so the right answer is "not analogous." Serve some cross-sub-area true analogies: different surface, same equity structure. Without both, the model can learn "the served case is always relevant," which is a MAC shortcut.
3. **The 1-NN tie is predicted.** On literal-similarity test items a flat content vector suffices. The solver's advantage can only show on a far or cross-sub-area split, so the evaluation needs one.

**Best argument against.** A casebook of tens to hundreds of cases per sub-area is small enough to run the solver on everything, which removes the cost rationale (p. 147). The lure and far-analogy lesson still holds, because it is about what the model learns. [OURS]

### A3. Analogical encoding and schema induction: serve two cases, and include a near miss

**Sources.**
- Dedre Gentner, Jeffrey Loewenstein & Leigh Thompson, "Learning and Transfer: A General Role for Analogical Encoding," *Journal of Educational Psychology* 95(2): 393–408 (2003). https://groups.psych.northwestern.edu/gentner/papers/GentnerLoewensteinThompson03.pdf
- Mary L. Gick & Keith J. Holyoak, "Schema Induction and Analogical Transfer," *Cognitive Psychology* 15: 1–38 (1983), abstract at https://www.sciencedirect.com/science/article/abs/pii/0010028583900026 (the full-text PDF I tried was not machine-readable).
- Dedre Gentner & Arthur B. Markman, "Structural Alignment in Comparison: No Difference Without Similarity," *Psychological Science* (1994; volume not checked). https://journals.sagepub.com/doi/10.1111/j.1467-9280.1994.tb00652.x
- Dedre Gentner & Kenneth Kurtz, "Learning and using relational categories," in Ahn et al. (eds.), *Categorization inside and outside the laboratory*, pp. 151–175 (APA, 2005). https://groups.psych.northwestern.edu/gentner/papers/GentnerKurtz05.pdf

**Findings.**
- **Gentner, Loewenstein & Thompson (2003).** Novices learned negotiation principles from two cases, either compared side by side or studied separately.
  - Experiment 2: 48% of the comparison group transferred the principle vs 19% of the separate-study group (p. 399) [VERIFIED].
  - Participants whose written comparison scored 0 for schema quality transferred at about 20%. Those scoring 1 or 2 were about twice as likely to transfer (p. 400) [VERIFIED].
  - Their account: comparison "can lead learners to focus on structural commonalities rather than on idiosyncratic surface features" (p. 394) [VERIFIED].
- **Gick & Holyoak (1983)** [VERIFIED, abstract]:
  - with one analog, summarization instructions, a verbal principle, or a diagram did not reliably produce transfer;
  - with two analogs, subjects "often derived a problem schema as an incidental product of describing the similarities of the analogs";
  - schema quality predicted transfer;
  - aids that failed with one analog helped when paired with two.
- **Gentner & Markman (1994).** Comparison yields "commonalities, differences related to the commonalities, and differences unrelated to the commonalities." Differences are easier to find between *similar* pairs, especially **alignable differences**, those tied to the shared structure [VERIFIED, abstract].
- **Gentner & Kurtz (2005)** on **progressive alignment**: learning improves through juxtapositions "that progress from highly similar pairs to pairs with less surface similarity and eventually to pairs that differ strongly in their entity characteristics but share relational patterns" (p. 163) [VERIFIED].

**What it implies.** [OURS]
1. **Serve pairs, and add a mapping step 0: `schema`.**
   - When two served precedents share an outcome, the model first writes their common reason, and the solver checks it. The gold common reason is the intersection R₁ ∩ R₂, or the smallest set that makes both precedents consistent under Horty's a fortiori constraint.
   - This is the Gick & Holyoak manipulation turned into a verifiable target, with schema quality as a reward term. It is cheap: the solver derives gold from existing reason sets.
2. **Make the second case a near miss when one exists.** A near miss shares most factors with the primary precedent but has the opposite, or an adjacent, outcome. Its alignable difference is the **pivot**:
   - `pivot = (R_primary Δ R_nearmiss) restricted to reason factors`, which is solver-computable;
   - the model then states which side of the pivot the situation falls on, which is also solver-checkable.

   Gentner & Markman predict that similar pairs make this difference easy to find. That makes the pivot a well-posed training signal rather than a search problem.
3. **The flip rules are near misses waiting to be used.** Each in-catalog flip rule (`if: "-A3", then: B`) describes a variant case with a known outcome. By the brief's count, 108 of 318 flip rules hinge on catalog factors, since 210 do not. Those 108 can be expanded mechanically into synthetic near-miss cases with no new labeling. The 210 off-catalog flip rules cannot, which is another reason to fold recurring new considerations back into the catalog.
4. **Curriculum.** Progressive alignment suggests ordering the SFT and GRPO data:
   - start with pairs from the same sub-area;
   - then pairs across sub-areas that share an equity structure, such as a release decision and an intelligence-sharing decision that both turn on source protection versus partner need.

**Best argument against.** These results concern *encoding for later transfer*. The Benchbook model uses cases in context, which is closer to mapping, and two cases double the surface it can latch onto. Run 1-case vs 2-case (same outcome) vs 2-case (near miss) as an ablation before adopting. [OURS]

### A4. Multiconstraint theory: the purpose the analogy serves (Holyoak & Thagard 1989)

**Source.** Keith J. Holyoak & Paul Thagard, "Analogical Mapping by Constraint Satisfaction," *Cognitive Science* 13(3) (1989; pages not checked), abstract at https://www.sciencedirect.com/science/article/abs/pii/0364021389900165. The Waterloo PDF failed TLS verification, so I did not use it.

**Claim.** Three interacting constraints govern mapping [VERIFIED, abstract]:
- structural: maximize "the consistency of relational correspondences";
- semantic: support mappings "to the degree that mapped predicates have similar meanings";
- pragmatic: favor "mappings involving elements the analogist believes to be important in order to achieve the purpose for which the analogy is being used."

**What it implies.** [OURS] The mapping is purpose-blind. Add a `served` field on the holding: the equities the decision actually protected, a subset of those its reason factors support. In step 3, a distinction is significant only if it touches a `served` equity or introduces a new one. This is close to Bench-Capon & Sartor's values (strand 16). The cognitive point is that purpose belongs **in the case**, because one catalog factor can be central in one precedent and incidental in another.

**Best argument against.** It invites post-hoc rationalization by the labeler. It adds information only when a reason factor supports several equities and the precedent relied on one. [OURS]

### A5. LLM analogical reasoning, 2023–2025 (brief)

- **Webb, Holyoak & Lu**, "Emergent analogical reasoning in large language models," *Nature Human Behaviour* 7: 1526–1541 (2023), https://www.nature.com/articles/s41562-023-01659-w. GPT-3 matched or exceeded humans on several analogy formats [VERIFIED].
- **Lewis & Mitchell** (arXiv 2402.08955, 2024), https://arxiv.org/abs/2402.08955. On counterfactual variants, "the GPT models' performance declines sharply" while humans stay high [VERIFIED].
- **Lewis & Mitchell** (arXiv 2411.14215), https://arxiv.org/abs/2411.14215. On story analogies, GPT models showed answer-order effects and more sensitivity to paraphrase than humans [VERIFIED]. A search-result listing says it appeared in TMLR 2025 [UNVERIFIED].
- **Sourati et al.**, "ARN: Analogical Reasoning on Narratives" (TACL 2024; arXiv 2310.00996), https://arxiv.org/abs/2310.00996. Built on structure-mapping, with separate surface and system mappings. Finding: LLMs "can largely recognize near analogies," but even the largest "struggle with far analogies in a zero-shot setting, with GPT4.0 scoring below random." Solved examples and chain of thought help [VERIFIED].
- **Yuan et al.**, "Beneath Surface Similarity: Large Language Models Make Reasonable Scientific Analogies after Structure Abduction" (Findings of EMNLP 2023; arXiv 2305.12660), https://arxiv.org/abs/2305.12660. LLMs "often overlook the structures that underpin these analogies," and struggle to explicitly abduce the relational structure linking two systems [VERIFIED].

**Implication.** [OURS] ARN's far-analogy failure is the MAC/FAC lure condition (A2). It argues for keeping the solver as the FAC stage rather than letting the model pick the analogue. SCAR supports the core bet that an explicit written mapping is a trainable target the model does not produce unprompted.

---

## Part B — What a reason is (where the fixed-polarity factor breaks)

### B1. Dancy's holism of reasons and Horty's formal treatment

**Sources.**
- Sean McKeever, "Moral Particularism and Moral Generalism," *SEP* (revised 2023). https://plato.stanford.edu/entries/moral-particularism-generalism/
- Chris Tucker, "Weighing Reasons," *SEP* (2025). https://plato.stanford.edu/entries/weighing-reasons/
- John F. Horty, "Reasons as Defaults," *Philosophers' Imprint* 7(3) (2007). http://www.horty.umiacs.io/articles/007003.pdf
- John F. Horty, *Reasons as Defaults* (OUP 2012; paperback 2014). TOC at https://global.oup.com/academic/product/reasons-as-defaults-9780199396443; final draft at http://www.horty.umiacs.io/courses/readings/rd-root.pdf
- Andrew Kernohan, "How to modify the strength of a reason," *Philosophical Studies* 179: 1205–1220 (2022). https://link.springer.com/article/10.1007/s11098-021-01703-3
- Jonathan Dancy, *Ethics Without Principles* (OUP 2004). I did not open it; claims about it here come via the SEP entries.

**The claim.** Holism: "a consideration that counts as a reason in one case may not count as a reason in another case, or may count as a reason, but in a different direction." Example: a remark's being funny can be a reason for making it, a reason against, or no reason at all [VERIFIED, McKeever SEP].

The SEP entries describe the context factors [VERIFIED, McKeever; Tucker]:
- **Defeaters**: offensiveness defeats humor's force.
- **Enablers**: the audience will appreciate the joke, which enables humor to be a reason.
- **Intensifiers**: the joke will break an unduly somber mood.
- Tucker's summary: conditions (enablers/disablers) are "on/off switches"; modifiers (amplifiers/attenuators) "determine only how bright it is." His example: coercion disables a promise; "you are the only person around" amplifies the reason to help.

Dancy's own labels "favourer/disfavourer" for the reasons themselves are standard [UNVERIFIED: I did not open Dancy 2004].

**Formal treatment.** Horty (2007) identifies reasons with "the premises of triggered defaults" (§2.2) [VERIFIED].
- **Undercutting** is modelled as a default whose conclusion puts another default below a threshold: "a default is undercut when our reasoning forces us to conclude that its priority falls below threshold" (§3.2) [VERIFIED].
- **Dancy's reversal cases** are handled as a defeated reason plus a new one: under the drug, "L is still classified as a reason for R, but simply as a defeated reason" (§4.2) [VERIFIED].
- **Holism does not force particularism.** Horty argues that defaults can be general principles that are holistic in operation (2012, ch. 6, "moderate particularism") [VERIFIED via draft].
- **Enablers vs reasons.** The 2012 book treats enablers as distinct from reasons (§2.2.2) [VERIFIED].
- **Intensifiers and attenuators are left largely open.** A section titled "Excluders, intensifiers, and attenuators" (§5.3.3) raises them without a worked formalism [VERIFIED]. The 2007 paper's fn. 16 reads a disabler as an attenuator that pushes a default "below threshold" [VERIFIED].
- **A quantitative alternative.** Kernohan (2022) models modifiers probabilistically: a modifier R* scales a reason R's support for Φ by the ratio Pr(R*|R&Φ)/Pr(R*|R) [VERIFIED].

**What it means for the Benchbook.** [OURS] The factor ID encodes polarity: A-factors favor A. Holism says polarity belongs to a factor *in a context*. Horty's move preserves fixed polarity: never flip a factor. Instead:
- a context fact **disables** the factor;
- the same raw fact may **also** trigger a different catalog factor with the opposite letter.

Proposal: add a fourth catalog object, the **modifier**, which targets a factor rather than an option:

```yaml
modifiers:
  - id: M1
    target: A2            # "partner has operational need" (favors release)
    role: disable         # enable | disable | intensify | attenuate
    text: request arrived through an unauthenticated channel
  - id: M2
    target: A2
    role: attenuate
    text: partner already holds the information via another channel
  - id: M3
    target: A2
    role: intensify
    text: imminent threat to partner forces
```

Solver pre-pass, before any reason-model step:
1. A tagged factor is **active** iff all of its `requires_enabler` modifiers are present (if the catalog declares any) and no `disable` modifier targeting it is present.
2. `intensify` / `attenuate` move an active factor one step on its existing ladder, `weak↔strong` or `B2@even↔B2@likely`.
3. Distinctions, significance, and support are then computed over active factors only.
4. A situation that shares a precedent's reason factor but has a disabler for it counts as lacking that reason. Horty's D formula then produces the distinction automatically.

**Polarity reversal** becomes "disable + second tag." Example:
- "The subject is a U.S. person" normally tags A5 (favors minimizing collection).
- With the person's documented consent to monitoring of their own compromised system, a consent modifier disables A5.
- The same fact also tags B4 (protect the victim).

**What it fixes.**
- "Unnamed or partially applied mitigators" (5 of 10 DOHA cases). Many adjudicative mitigating conditions are really enablers or attenuators of a disqualifying factor, not independent pro-applicant factors.
- The threshold-nesting machinery generalizes cleanly as intensify/attenuate on the ladder.

**Best argument against.** Real holism is open-ended: unlisted disablers will surface as off-catalog flip rules (already 210). Modifiers also make tagging relational, so tag F1 stops measuring the hard part. Dancy rejects Horty's undercut reading [VERIFIED, Horty §4.2], but the Benchbook needs a solver-friendly approximation, not the right metaphysics. Keep the modifier list to the switches practitioners actually cite. [OURS]

### B2. Raz: exclusionary reasons and the authority of orders

**Sources.**
- Stefan Sciaraffa, "Authority," *SEP* (revised 2025). https://plato.stanford.edu/entries/authority/
- Michael S. Moore, "Requiem for a Concept: Exclusionary Reasons" (KCL lecture). https://www.kcl.ac.uk/c-ppl/assets/inaugural-lecture-series/michael-s-moore-requiem-for-a-concept-exclusionary-reasons.pdf
- Horty 2007 §3.2 (above).
- Rome Statute Art. 33. https://www.public.law/world/rome_statute/article_33_superior_orders_and_prescription_of_law

**The account.**
- An exclusionary reason is "a second order reason to refrain from acting for some reason." Raz, *Mind* 85 (1975) p. 487, quoted by Moore [SECONDARY].
- A preemptive (protected) reason "comprises a content-independent reason to phi and a second-order reason (an exclusionary reason) not to act for reasons for or against phi-ing" [VERIFIED, SEP Authority, citing Raz].
- The Normal Justification Thesis grounds authority in the subject's being "likely better to comply with reasons which apply to him ... if he accepts the directives ... rather than by trying to follow the reasons which apply to him directly" (Raz 1986: 53) [VERIFIED, SEP].
- Raz's own paradigm is military. Jeremy "was ordered by his commanding officer to appropriate a van belonging to a civilian," and reads the order as meaning "it is not for him to act on a complete assessment of the pros and cons" (*Practical Reason and Norms*, pp. 41–42, quoted by Moore) [SECONDARY].
- Exclusion can have limited scope, excluding some reasons and not others [SECONDARY, Moore].
- Tucker's SEP entry: exclusionary reasons "do not affect the balance of reasons," so one may be required to act against the balance [VERIFIED].

**Formalization.** Horty models Raz's Colin case with an exclusionary default, ¬Welfare(d) → d ≺ t: any default not bearing on the son's welfare falls below threshold and "does not provide any reason" (§3.2) [VERIFIED]. The scope of the exclusion is a predicate on reasons. That is precisely what the Benchbook needs.

**The limit.** Rome Statute Art. 33 relieves responsibility for obeying an order only if (a) there was a legal obligation to obey, (b) the person "did not know that the order was unlawful," and (c) "the order was not manifestly unlawful." Orders to commit genocide or crimes against humanity are deemed manifestly unlawful [VERIFIED]. Read as reason structure [OURS]:
- (a) is an enabler of the exclusion;
- (b) and (c) are its disablers.

**What it means for the Benchbook.** [OURS] Authority should be its own case (and catalog) object, not a factor:

```yaml
authorities:
  - id: X1
    source: watch officer            # who issued it
    directs: C                       # option or action directed
    level: 2                         # ordinal approval level of the source
    scope: {excludes_equities: [E_efficiency, E_optics]}   # or excludes_all_except: [...]
    enabled_by: [X1-auth]            # e.g. order authenticated via proper channel
    disabled_by: [L1, L2]            # L1 manifestly unlawful; L2 outside delegated scope / conditions changed
```

Solver step 0, run before tagging-based comparison:
1. **X1 is active** iff its enablers are present and no disabler is present at or above its threshold likelihood.
2. **If active**: drop every situation factor whose equities all fall in `scope.excludes`. Then add a protected reason for `directs` that other factors can override only if they (i) support a non-excluded equity **and** (ii) come with precedent in the casebook that lets them prevail against an order. Otherwise the directed option wins.
3. **Disabler likelihood between thresholds** (the agent cannot tell whether the order is manifestly unlawful): output `ask`, as a procedure, not an option.
4. **Approval levels.** "Above the agent's role" becomes computable: if the chosen action's `required_level` exceeds the level delegated to the agent, output `ask`.
5. **Graded authority is real in non-common-law practice too.** A Qing Board of Punishments ruling reasoned that "committing homicide at a father's behest is less of a transgression than homicide at an uncle's behest because an uncle is a more distant relative" (Wang 2005, p. 335; see C2) [VERIFIED]. The authority's proximity works as a magnitude, which `level` captures.

**Worked example.** An operator orders an autonomous vessel's agent to hold course through a zone with a fishing vessel nearby.
- The agent's own views on transit efficiency or diplomatic optics are excluded.
- Safety-of-life and collision-regulation equities are not excluded.
- An order to close on the fishing vessel would trigger L1.

**What it fixes.**
- Gives agent-vs-order cases a semantics that is neither "obey = heavy weight" nor "obey unless outweighed."
- Pulls part of the 139 escalate-ending flip rules out of the option space into a computed `ask`.
- Makes `decided_by` and `agent_role` do solver work rather than sit as metadata.

**Best argument against.** Mission command *invites* subordinates to weigh intent (strand 18), so real exclusion scopes are narrow and contested. For AI agents, exclusion is a security hazard: a prompt injection claiming authority buys exclusion of the agent's objections. The authentication enabler is therefore mandatory, and an unverifiable authority must be treated as inactive. Moore's critique [SECONDARY] matters for philosophy, not for a solver.

### B3. Ross: prima facie duties, no fixed ranking, and residue

**Source.** Anthony Skelton, "William David Ross," *SEP* (revised 2022). https://plato.stanford.edu/entries/william-david-ross/

**The account** [VERIFIED].
- Duties of fidelity, reparation, gratitude, beneficence, non-maleficence (among others).
- "It is always possible for any one duty to outweigh any other," with defeasible general orderings. "Do evil to no one" is "more pressing than" "do good to every one," except when the evil is "very substantially outweighed."
- Conflicts are settled by judgment: "the decision rests with perception."
- The SEP's exposition says a responsibility's valence "persists even when a responsibility is outweighed," so a broken promise still leaves compensation owed.

**What it means.** [OURS]
- **Residue.** This is the missing semantics of *partial* moves. "Do the lawful part, hold/route the rest" (72 of 100 Hard Calls) is the chosen option plus actions that discharge the overridden duty: notify oversight, log, minimize, seek retroactive approval.
- Proposal: each catalog equity gets a short `residue` menu, e.g. privacy → minimize + log + notify oversight. An outcome is then `{option: C, residue: [..]}`.
- Solver check (set coverage): every equity supported by a present, *strong*, losing-side active factor must have a residue act in the model's plan.
- Ross's defeasible orderings suggest an equity-level partial order used only in step 5 (residual judgment), never to decide a bound case.

**Best argument against.** Ross gives no decision procedure. "Perception" is exactly what a deterministic solver cannot compute. Residue coverage also rewards padding the plan with notifications, so it needs a cap (acts drawn only from the menu of equities that actually lost).

### B4. Richardson: specifying norms instead of weighing them

**Source.** Henry S. Richardson, "Specifying Norms as a Way to Resolve Concrete Ethical Problems," *Philosophy & Public Affairs* 19(4): 279–310 (1990). http://www.horty.umiacs.io/courses/readings/richardson-1990-specifying.pdf

**The account** [VERIFIED].
- Norm p specifies q iff:
  - (a) same normative type;
  - (b) every instance of p's absolute counterpart is an instance of q's;
  - (c) p qualifies q "by adding clauses indicating what, where, when, why, how, by what means, by whom, or to whom";
  - (d) no added clause is irrelevant to q (pp. 295–296).
- Specification is an alternative to deductive application and to intuitive balancing. For the latter, Richardson says of taking the balance as primitive: "we cannot give it a rational grounding" (p. 288).
- A specification is defensible if it "enhances the mutual support among the set of norms found acceptable on reflection" (p. 302).
- Worked example (the Baby Doe case): the killing prohibition is narrowed by added conditions (p. 304).

**What it means.** [OURS] Specification gives step 5 (residual judgment) a *checkable* output format. Replace "a resolution + confidence" with "a specified rule + confidence":

`rule: {base: <equity or option-norm>, when: [catalog factor ids], unless: [catalog factor ids], then: <option>}`

The solver checks:
- (i) every clause is a catalog factor. This is Richardson's (d) as "no irrelevant clauses," and anything off-catalog forces `ask`;
- (ii) consistency with the casebook: no precedent satisfies `when` without `unless` but has a different outcome. This is coherence operationalized as non-contradiction;
- (iii) the rule covers the situation.

Flip rules are already specifications in miniature.

**Best argument against.** Richardson's coherence is richer than non-contradiction, and a consistency check will accept many silly rules that happen not to clash with a small casebook. Require minimality (the fewest clauses that still separate the relevant precedents) to limit overfitting.

---

## Part C — Non-common-law traditions of reasoning from a case

### C1. Islamic jurisprudence: qiyās

**Sources.**
- Wael B. Hallaq, "The Logic of Legal Reasoning in Religious and Non-Religious Cultures: The Case of Islamic Law and the Common Law," *Cleveland State Law Review* 34 (1985–86). https://engagedscholarship.csuohio.edu/cgi/viewcontent.cgi?article=1958&context=clevstlrev
- Federal Territory Mufti's Office (Malaysia), *Irsyad Uṣūl al-Fiqh* Series 14 (tanqīḥ/takhrīj/taḥqīq al-manāṭ). https://muftiwp.gov.my/en/artikel/irsyad-usul-fiqh/1392-irsyad-usul-al-fiqh-series-14-tanqih-al-manath-takhrij-al-manath-dan-tahqiq-al-manath
- Same, Series 15 (al-sabr wa al-taqsīm). https://muftiwp.gov.my/en/artikel/irsyad-usul-fiqh/1393-irsyad-usul-al-fiqh-15-al-sabru-wa-al-taqsim-its-definition-and-application
- "A Review of Classical and Contemporary Uṣūl Fiqh Scholars' Perspectives on the Method of al-Taʿlīl bi al-Ḥikmah," *IJRISS* 9 (2025). https://rsisinternational.org/journals/ijriss/articles/a-review-of-classical-and-contemporary-usul-fiqh-scholars-perspectives-on-the-method-of-al-talil-bi-al-hikmah/
- Muhammad Iqbal, "Dialectical System of Qiyās al-ʿilla," in *Arsyad al-Banjari's Insights on Parallel Reasoning and Dialectic in Law* (Springer LARI 25, 2022). https://link.springer.com/chapter/10.1007/978-3-030-91676-3_2
- Shahid Rahman, Muhammad Iqbal & Youcef Soufi, *Inferences by Parallel Reasoning in Islamic Jurisprudence* (Springer LARI 19, 2019). https://link.springer.com/book/10.1007/978-3-030-22382-3

**What a case is.** Four pillars: "the asl, the precedent ...; (2) the far', the new case requiring a solution; (3) the 'illa, the similarity common to the asl and the far'; and (4) the hukm, the rule which is transferred" (Hallaq p. 94, transliteration normalized) [VERIFIED].

The ʿilla must be manifest and determinable. Rulings based on the ḥikma (underlying wisdom) lack "the requisite consistency (inḍibāṭ)." The standard example is travel: a traveler's hardship varies with train, motorcycle, or airplane, so the operative cause is travel defined by distance, not hardship itself [VERIFIED, IJRISS]. Al-Āmidī allowed reasoning from the ḥikma only when it is itself manifest and measurable [VERIFIED, IJRISS].

**How reasoning proceeds: three operations on the ratio (manāṭ)** [VERIFIED, Series 14]:
- **Takhrīj al-manāṭ: extract** an unstated ʿilla. Example: wine is prohibited, the text gives no ratio, and jurists extract *intoxication*.
- **Tanqīḥ al-manāṭ: refine** it by stripping features that "seemingly related to the 'illah" but are not. Example: the Bedouin who broke his Ramadan fast by intercourse. Being a Bedouin, the particular day, and the wife's status are dropped.
  - The schools then **disagreed on the level of the ratio**: Shāfiʿī and Aḥmad kept "intercourse," while Ḥanafīs held the ratio to be violating Ramadan itself.
- **Taḥqīq al-manāṭ: verify** that the established ʿilla is present in the new case, e.g., whether the cat-purity ratio ("living among humans") applies to rats.

**Methods for establishing the ʿilla (masālik).**
- **Sabr wa-taqsīm**: list candidate attributes, then eliminate the unfit. For wine: grape-derived, liquid, intoxicating, impure, leaving intoxication [VERIFIED, Series 15].
- Hallaq's account of **co-extensiveness and co-exclusiveness**: "the presence of the cilla when the judgment is present ... the absence ... when the judgment is absent" (p. 88), i.e., ṭard wa-ʿaks / dawarān [VERIFIED].
- **Efficacy**: the property "must bring about a judgment" (p. 88) [VERIFIED].
- Munāsaba (suitability) is the standard name for efficacy-style reasoning [UNVERIFIED, not in a page I opened].
- Qiyās yields only probable (ẓannī) knowledge (p. 86) [VERIFIED].
- Al-Shīrāzī ranks three kinds of qiyās: by the occasioning factor (*ʿilla*), by indication (*dalāla*), and by resemblance (*shabah*) [VERIFIED as chapter titles in Rahman et al.; the ranking detail is UNVERIFIED].

**Dialectical objections** tested a qiyās [VERIFIED as a list, Iqbal 2022]:
- *naqḍ* (inconsistency);
- *ʿadam al-taʾthīr* (inefficacy);
- *muʿāraḍa* (counter-analogy);
- *qalb* (reversal);
- *fasād al-waḍʿ* (corruption of the premises).

**Mapping onto the Benchbook.** [OURS]

| Qiyās | Benchbook | Solver-checkable? |
|---|---|---|
| aṣl / farʿ / ḥukm | precedent / situation / outcome | — |
| ʿilla | reason set R | yes |
| ḥikma | equity | no, and qiyās says *don't score it* |
| taḥqīq al-manāṭ | step 1 tagging (+ likelihood) | yes (tag F1) |
| takhrīj al-manāṭ | labeler writes R; model's "reason extraction" | yes, against gold R |
| tanqīḥ al-manāṭ | minimality of R; downplaying | yes: drop-one test (below) |
| sabr wa-taqsīm | significance step: enumerate, eliminate | partly |
| dawarān (ṭard wa-ʿaks) | casebook consistency across cases | yes |
| naqḍ | a case with R active but the other outcome | yes (Horty inconsistency) |
| ʿadam al-taʾthīr | a factor in R that is not necessary | yes (drop-one) |
| muʿāraḍa | "bounded" support (precedents pull both ways) | yes |
| qalb | same fact supports the opposite outcome in context | via B1 modifiers |
| qiyās al-shabah | 1-NN tag resemblance | yes, but it should rank *below* ʿilla-based support |

Concrete additions:
1. **ʿIlla/ḥikma is the doctrinal case for Peter's factor/equity split.** It also sets a rule for substitutes in step 3: a substitute may stand in for a missing reason factor only if it is itself a catalog factor serving the same equity. The ḥikma alone (the equity being at stake) never binds.
   - When only the ḥikma is present, support is at most "analogous by purpose." Label it that way.
2. **Casebook lints** the solver runs whenever a case is added:
   - *naqḍ*: any case where a precedent's R is active and uncountered but the outcome differs;
   - *tanqīḥ / ʿadam al-taʾthīr*: for each r ∈ R, is there a case or flip rule showing the outcome changes without r? If not, flag r as unrefined.
3. **Level-of-ratio disagreements become `holding_basis: contested`**, carrying *two* candidate reason sets, as in the Ḥanafī vs Shāfiʿī reading of the Bedouin case.
   - The solver computes support under both. If they diverge, the situation is "bounded," and the model must say which ratio it adopted.
4. **Support ladder**: rename 1-NN-only support "resemblance" (shabah) and rank it below "analogous."
5. **Taḥqīq is separate from qiyās.** The DOHA finding that tags taken from the judge's findings "nearly encode the verdict" happens because those findings have already done the taḥqīq.
   - Tag from the raw record (allegations and evidence), with likelihoods, not from findings.

**Best argument against.** In qiyās the aṣl's ruling is revealed, not decided, so the tradition never faces a precedent that might itself be wrong. Its objections presuppose a live adversary (jadal), not one model and a solver. The structural lessons (ratio vs purpose, the three manāṭ operations, objections as lints) stand without the vocabulary.

### C2. Qing China: sentencing by analogy (bifu), case compilations, and Mohist *tui*

**Sources.**
- Mary Buck, "Justice for All: The Application of Law by Analogy in the Case of Zhou Fuqing," *Journal of Chinese Law* 7(2) (1993). https://journals.library.columbia.edu/index.php/cjal/article/download/3134/6758/37698
- Zhiqiang Wang, "Case Precedent in Qing China: Rethinking Traditional Case Law," *Columbia Journal of Asian Law* 19(1) (2005). https://journals.library.columbia.edu/index.php/cjal/article/download/3246/6966/38039
- Robert L. Birmingham, review of Bodde & Morris, *Law in Imperial China* (1967), *Stanford Law Review* (1968). https://www.repository.law.indiana.edu/cgi/viewcontent.cgi?article=3705&context=facpub
- Hiroaki Terada, "Conviction and Sentencing," in *China's Traditional Legal Order* (Springer 2025). https://link.springer.com/chapter/10.1007/978-981-96-5941-8_7
- Marshall D. Willman, "Logic and Language in Early Chinese Philosophy," *SEP* (revised 2022). https://plato.stanford.edu/entries/chinese-logic-language/

**What a case is.**
- The *Xing'an huilan* (Conspectus of Penal Cases) collected case summaries with the Board of Punishments' reasoning, from the first third of the 19th century [VERIFIED, Birmingham]. Wang calls it "a monumental and comprehensive sixty-volume corpus of precedents" (p. 326) [VERIFIED].
- An entry records the provincial facts, the proposed sentence and the statute it cites, and the Board's reasoning. Facts compared included:
  - circumstances and gravity;
  - the means used;
  - kinship and status relations (father's vs uncle's behest);
  - intent, e.g., reliable evidence of a victim's suicidal intent in a mercy-killing case (pp. 335–337) [VERIFIED, Wang].

**How reasoning proceeds.**
- **The statute.** Buck translates it: "If, in deciding on a punishment, there is no precise article, (choose) cite (another) law and decide the case by analogy," and then "The imperial rescript will then be awaited" (p. 114) [VERIFIED].
- **Wrongful analogy was punishable** as intentionally or mistakenly imposing an excessive or deficient penalty (Art. 409) (p. 114) [VERIFIED].
- **Anchor plus degrees.** Judgment was pronounced "'by analogy to' the statute or substatute with a one-degree increase or reduction in the punishment" (p. 114) [VERIFIED].
- **Authority tiers.** The hierarchy of authority was "statute, sub-statute, general circular, and then prior cases," and invoking case law was prohibited "unless a prior case was circulated or enacted as a sub-statute" (Wang pp. 340–341) [VERIFIED].
- **Review.** Terada describes the determination of the applicable article (*nizui*) as a proposal reviewed by superiors, with the emperor holding final authority in capital cases [VERIFIED, chapter abstract/summary].

**What it means for the Benchbook.** [OURS]
1. **Anchor + degree semantics for n-ary outcomes.** Order a case's options on a ladder where one exists: full act > partial act > hold > refuse. The precedent's outcome is the anchor; each significant distinction moves the outcome one degree in the direction of its polarity. Factors then favor a *direction* on the ladder, not a letter.
   - This makes the 21 of 100 "mixed" reason sets legitimate: a C outcome between A and B is exactly where A-ward and B-ward factors balance.
2. **Precedent rank.** Add `authority_rank: policy | approved_exemplar | circulated | prior_case`. "Binding" requires rank ≥ `approved_exemplar`; a raw prior case can support at most "analogous."
3. **Analogy needs licence.** A Qing magistrate could propose an analogy but not finalize it. That is the Benchbook's act-or-ask rule with a historical pedigree. The agent's output in unprecedented cases is a *proposal for review*: a structured memorial citing the anchor and the degree shift. The +ρ term for a correct attached resolution already rewards it.

**Mohist tui: what is structurally new beyond Mengzian extension** [VERIFIED definitions via Willman SEP, §3.4]:
- *Tui* (pushing) is: "On the grounds that what they don't accept is the same as what they do accept, propose it." It is a consistency challenge built on the *interlocutor's own* accepted case.
- The Mohists warned that parallel inference depends on the terms' combined semantics, not their form: "Robbers are people ... but killing robbers is not killing people" (§3.5).

Lessons [OURS]: (i) the deployer's own casebook can be *pushed* against a new instruction from the deployer, and the solver can check that consistency; (ii) the robber example is holism again, so handle it with B1 modifiers.

**Best argument against.** Qing analogy served a penal code whose outcome is a scalar punishment on a legally given ladder. Benchbook options are often qualitatively different (tearline vs liaison vs deny) or two-dimensional (what to do × whom to tell). Use the ladder only where the labeler marks `ordinal: true`.

### C3. Talmudic *kal va-chomer*, *dayo*, and the two-source *binyan av*

**Sources.**
- Mishnah Bava Kamma 2:5 (William Davidson English ed., Sefaria API). https://www.sefaria.org/api/texts/Mishnah_Bava_Kamma.2.5?context=0
- W. Bacher & J. Z. Lauterbach, "Talmud Hermeneutics," *Jewish Encyclopedia* (1906). https://www.jewishencyclopedia.com/articles/14215-talmud-hermeneutics
- M. Abraham, D. M. Gabbay & U. Schild, "Analysis of the Talmudic Argumentum A Fortiori Inference Rule (Kal Vachomer) using Matrix Abduction," *Studia Logica* 92(3): 281–364 (2009). https://link.springer.com/article/10.1007/s11225-009-9202-5

**The pieces.**
- **Kal va-chomer and dayo.** R. Tarfon: "If in a place where the Torah was lenient with regard to Eating and Trampling, in the public domain, is it not right that we be strict with regard to Goring on the property of the injured party?" That is, goring there should pay in full. The Sages: "It is sufficient for the conclusion that emerges from an a fortiori inference to be like its source," so half damages, as in the public domain [VERIFIED, Mishnah BK 2:5].
- **Refutation (*pirka*).** A kal va-chomer is refuted by showing the premise does not actually establish the claimed ordering [VERIFIED, JE summary].
- **Binyan av from two passages.** Two laws sharing a "common feature" (*ha-tzad ha-shaveh*) ground a rule for others with that feature. The argument fails if the shared element does not really establish the equivalence [VERIFIED, JE summary].
- **Gezerah shavah** (verbal analogy): "No one may draw a conclusion from analogy upon his own authority" [VERIFIED, JE].
- **Formalization.** Abraham, Gabbay & Schild formalize kal va-chomer as "Matrix Abduction" over partial binary matrices [VERIFIED, abstract].

**What it means.** [OURS]
- Kal va-chomer *is* Horty's a fortiori constraint (strand 16). The new element is **dayo**: an a fortiori argument from a precedent yields at most the precedent's outcome.
- On an ordinal ladder (C2), a stronger situation gets a **lower bound** equal to the precedent's degree, not a licence for a more extreme move. Example: a precedent granted partial release on weaker pro-release facts, and the situation has stronger ones. The situation is guaranteed *at least* partial release. Full release is "open" and goes to residual judgment.
- The solver outputs `[lo, hi]` on the ladder: binding when lo = hi, bounded otherwise. This gives Horty's model an n-ary reading without changing its core.
- **Binyan av from two sources** is a 2,000-year-old version of Gick & Holyoak's two-analog schema induction, *with a built-in check*. The rule is R₁ ∩ R₂. It is refuted if R₁ ∩ R₂ contains a factor the new case lacks, which is solver-computable and matches A3's `schema` step.
- **Gezerah shavah's authority limit** parallels the Qing rescript: both traditions allocate the *power to analogize* by role.

**Best argument against.** These are rules for *reading* a fixed text, not for deciding under uncertainty, and the outcomes (half vs full damages) are naturally scalar. Dayo is contested inside the tradition (R. Tarfon rejects it), so treat it as a design choice.

---

## Ranked: the five ideas most worth adopting

1. **Ordinal outcome ladder with bounded a fortiori (Qing degrees + dayo) and Ross residue.**
   - *Fixes*: n-ary/partial outcomes (72 of 100 partial); the 21 mixed-polarity reason sets, since factors become directional; and "route the rest" through residue coverage.
   - *Cost*: labeler marks `ordinal: true` and orders options, about 1 minute per case, plus a per-equity residue menu, about 5–8 lines per sub-area. Solver: moderate. Interval propagation replaces point outcomes, and residue coverage is a set check.
2. **Authority as an exclusionary object** (`authorities` with scope, enablers, disablers, level; Raz/Horty; Rome Statute Art. 33 limit).
   - *Fixes*: agent-vs-order cases; computes "above role"; moves part of `escalate` out of the option space; treats unauthenticated authority as inactive, which blocks the injection hazard.
   - *Cost*: one block per case that involves an order or delegation, plus a short list of limit disablers per sub-area. Solver: a filter pass before comparison, low complexity.
3. **Modifier catalog entries** (enable, disable, intensify, attenuate; Dancy/Horty; qiyās *qalb*).
   - *Fixes*: fixed-polarity breakage handled as "disable + second tag"; partially applied mitigators (5 of 10 DOHA); generalizes threshold nesting.
   - *Cost*: roughly 5–15 modifiers per sub-area catalog, and the model must tag modifier–target links. Solver: a linear pre-pass.
4. **Serve a primary plus a near miss, with a `schema`/`pivot` mapping step** (Gentner et al. 2003; Gick & Holyoak 1983; Gentner & Markman 1994; binyan av).
   - *Fixes*: transfer (48% vs 19% in humans); gives a precise, checkable target for "which side of the line is this"; puts the flip rules to work.
   - *Cost*: near-zero labeling for the 108 in-catalog flip rules, which the solver expands into synthetic near misses. Solver: set intersection and symmetric difference. Validate by ablation before adopting.
5. **Solver as FAC stage and casebook linter** (MAC/FAC; qiyās naqḍ / tanqīḥ; Qing precedent rank).
   - Embedding retrieval → model tags → solver re-rank by reason coverage and distinctions.
   - Add mere-appearance lures and cross-sub-area true analogies to training.
   - Lint every case for naqḍ and drop-one necessity.
   - Rank support: binding (rank ≥ approved exemplar) > analogous > resemblance.
   - *Fixes*: surface-bias retrieval; untested far-analogy generalization (the 1-NN tie); labeler errors in reason sets.
   - *Cost*: no per-case labeling beyond `authority_rank`. Solver: reuses existing checks.

**Runners-up.**
- Richardson specification as the step-5 output format (a rule of catalog factors checked for casebook consistency).
- Role slots / `bears_on` for allegation-level structure (Gentner systematicity).
- A `served` equity field on holdings (Holyoak & Thagard pragmatic centrality).
