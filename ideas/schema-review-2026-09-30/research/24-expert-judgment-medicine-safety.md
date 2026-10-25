# Strand 24 — How expert-judgment and safety-critical fields represent a case and reason from it (the non-court traditions)

Research date: 2026-09-29. Scope: naturalistic decision making, decision-forcing cases, medicine, structured professional judgment, safety engineering, hindsight review, intelligence analysis.

## Read this first

**How I verified.** Every page was opened with WebFetch, which returns a model-written digest of the page, not raw text. Where I write "quote," it is a string the tool returned as a quotation. Web search ran out of budget partway through, and several sources were blocked (PMC/PubMed reCAPTCHA, Wiley/Taylor & Francis/Sage 403, robots.txt on the HCR-20 rating sheet and an NHS formulation PDF). Nothing was fetched by any other route. Tags: **[VERIFIED Sn]** = the opened page says it; **[SECONDARY Sn]** = the opened page reports someone else's work; **[UNVERIFIED]** = not checked; **[OURS]** = my inference. Source IDs (S1…) are listed at the end with the URLs I opened.

**Not opened, so treat as gaps:** the HCR-20 V3 manual itself (Douglas, Hart, Webster & Belfrage 2013), the SAPROF manual, Reason's 1997 book text of Figure 9.4, Leveson & Thomas's STPA Handbook, the GRADE Evidence-to-Decision paper, and Klein, Calderwood & MacGregor 1989 (bibliographic listing only).

**Bottom line.**
1. These fields treat a case as a *record cut at a decision point*, with what the decider knew kept apart from what happened after. That cut fixes the pilot's "tags nearly encode the verdict" leak and is the precondition for negative exemplars.
2. HCR-20's "presence × relevance" does **not** by itself fix the partially-applied-mitigator misfit: its middle category ("Possibly or Partially") merges uncertainty with extent, and a real DOE clearance decision shows two kinds of partial (§4). Relevance and the non-summative chain are the useful parts.
3. RPD expectancies, data/frame anomalies and ACH milestones all say "record what you would expect to see next." Medicine adds red flags, which trigger inquiry rather than push a verdict. That is a better home for most of the 139 `then: escalate` flip rules than an "escalate" option.
4. ACH's diagnosticity and disconfirmation-first rule, plus bow-tie barriers, give an n-ary way for a compromise option to win without being labeled special.
5. STPA is strong for knock-outs and perturbations, weak for weighing.

---

## 1. Naturalistic decision making: RPD, CDM, data/frame, situation awareness

**Case fields.** Klein's unit is the incident, elicited by the Critical Decision Method (CDM) as a timeline with marked decision points, defined as "a point in time when alternative decisions or courses of action could have been chosen" [VERIFIED S1]. CDM runs in four sweeps: incident selection, timeline verification and decision-point identification, deepening, "what-if" queries [VERIFIED S5]. The 1988 ARI report's probes include decision-point options; cues ("What information relevant to the decision was available and how was it obtained?"); causal factors; goal shifts; analogues ("Pick the most similar/helpful case. Describe the differences."); errors; hypotheticals ("What might have happened if an action had not been taken?"); desired data; and add-ons for confidence, decision basis ("What rule was being followed?"), novice contrast ("How might a less experienced officer have behaved differently?"), time pressure and decision duration [VERIFIED S1]. A later clinical protocol adds "Is this case a typical scenario?" and a hand-over-style situation summary [VERIFIED S6]. A recognized situation in RPD is a bundle: relevant cues, plausible goals, expectancies, typical action [SECONDARY S3]. Expectancies "prepare decision makers for action" and "provide clues for testing whether the situation is correctly understood" [SECONDARY S2]. Typical actions form an ordered queue; a rejected option is replaced by "the next most typical option ... from the action queue" or modified [VERIFIED S1].

**Reasoning steps.** Recognize typicality; generate expectancies and check them (if violated, re-diagnose or seek information); mentally simulate the typical action; accept, modify, or move down the queue [VERIFIED S1; SECONDARY S2, S3]. In Klein, Moon & Hoffman's data/frame theory a frame "functions as a hypothesis about the connections among data," and may be a story, map or script. Two cycles operate: *elaboration* (fill slots, explain away inconsistencies) and *reframing* (question, compare, replace). Expectancies "can be violated by anomalies, permitting adjustment and reframing" [VERIFIED S7]. Endsley's situation awareness has three levels — perception, comprehension, projection — and is "the primary basis for subsequent decision making" without guaranteeing a good decision [SECONDARY S8].

**What it changes in the Benchbook.**

*(a) The mapping already does half of this.* [OURS] D = (R \ Y) ∪ (Y^ō \ X^ō) is factor-level expectancy checking: a reason factor the situation lacks is an unmet expectancy; a new opposing factor is an anomaly. What is missing is (i) presuppositions that are not weighed factors (authority in force, the agent's role, the time window, who the counterparty is) and (ii) a *typed response* to a broken presupposition. RPD and data/frame supply three responses: re-diagnose (ask for information), fall to the next typical action, reframe (treat as unprecedented). None of these is "option B."

*(b) Proposed fields* [OURS]: `frame_conditions: [{id, kind: authority|role|time|info_state|counterparty, text}]` (what the outcome presupposes) and `anomaly_cues: [{what, then: ask|next_option|unprecedented}]`. The mapping gains a step 0: for each frame condition, tag `holds | fails | unknown`. Solver rule: any `fails` caps support at `bounded`; any `unknown` on an authority-kind condition routes to `ask`. This is computable from tags alone.

*(c) It has a target already sitting in the data.* 210 of 318 flip rules hinge on a consideration not in the catalog (brief). In data/frame terms these are data the frame has no slot for. They should be `anomaly_cues` with a reframing response, not flip rules the solver cannot evaluate. The harness's existing "ask if an unlisted consideration is flagged" rule then has a gold label.

*(d) CDM as an authoring checklist for Peter, not a model behavior.* The probes map onto the schema with these gaps:

| CDM probe | Benchbook field | Status |
|---|---|---|
| Cues; desired data | facts; watch_for; ask trigger | have |
| Options; basis of choice | options; reason; authorities | have |
| Analogues ("describe the differences") | analog; distinctions | Hard-Calls dialect only |
| Errors; novice contrast | tempting_wrong_answer, downplay_trap, failure_modes | Hard-Calls dialect only |
| Hypotheticals | flip_rules | have |
| Typical scenario? | `typicality: prototype\|variant\|edge` | **missing** |
| Time pressure; duration | `time_available`, `human_reachable_within` | **missing** |

The Hard-Calls fields `tempting_wrong_answer` and `failure_modes` reinvent CDM's error and novice probes. That is mild evidence they are worth keeping and promoting into the v6 dialect.

*(e) Do not add expected consequences (Endsley level 3) as a scored field.* A solver cannot check a projection without an environment.

**Best argument it doesn't fit.** Kahneman & Klein say skilled intuition needs an environment that "must provide adequately valid cues" and "prolonged practice and feedback that is both rapid and unequivocal" [VERIFIED S9]. National-security value conflicts are rare, slow, committee-mediated and get little unequivocal feedback. RPD describes a competence the agent does not have and the Benchbook does not try to build. Retrieval-plus-mapping *replaces* recognition. CDM also elicits retrospective accounts from deciders who know the outcome (§6). And expectancies double-count reason factors unless restricted to non-factor presuppositions.

---

## 2. Decision-forcing cases and tactical decision games (USMC)

**Case fields.** A decision-forcing case has two essential elements: "a description of the protagonist and the problem that he faced" and "a Socratic conversation, led by an able facilitator"; most add "the reveal," also "the historical solution" and "the rest of the story" — what the real decider chose and what followed [VERIFIED S11a]. Bruce Gudmundsson held the Case Method Chair at Marine Corps University 2007–2017 [VERIFIED S11a]. A student template has four parts: big-picture background; protagonist ("You are Captain..."); scope-narrowing facts; decision point ("What now, captain?") [VERIFIED S11d]. The distinguishing feature is perspective: conventional case studies give "a retrospective point of view," decision-forcing cases "a prospective point of view," so players lack hindsight advantage [VERIFIED S11b]. A game built wholly on real events is a "decision-forcing case study"; one with at least one imaginary element is a "speculative decision game" [VERIFIED S11e]. Formats run from "Harvard-style" (heavy pre-reading) to "Quantico-style" (none) [VERIFIED S11a].

**Reasoning steps.** Facilitator prompts: "what is going on here?", "what is your plan?", "what are you going to do?" [VERIFIED S11a]. The student commits, then compares her solution and others' with the historical solution [VERIFIED S11c]. I found no scoring rule. Whether a doctrinal "school solution" exists is [UNVERIFIED].

**What it changes.**

*(a) One record, two cuts* [OURS]. The Benchbook's "exemplar card" and "live scenario" are the same underlying record cut at different places. Scenario = everything up to the decision point. Card = scenario + decision + reveal. The v6 card and the Hard-Calls scenario are separate dialects with no shared structured facts (the scenario's `situation` is prose). Give both one fact list with `known_at_decision: true|false`, plus an `after` block (consequences, later review). The harness serves the card; the training prompt for a *new* situation is built from the `known_at_decision` subset only.

*(b) This is the fix for the pilot's leakage.* [OURS] "Tags taken from the judge's findings nearly encode the verdict" arises because findings are the adjudicator's after-the-fact output. A decision-forcing build tags from what was before the decider (the statement of reasons, the record) and holds the findings back as "the rest of the story." The precedent side still uses findings as legitimate content. The *test-item* side must not.

*(c) The reveal is not gold.* Gudmundsson's own framing compares students with the historical solution, not with a verified-correct one. Using the reveal as a label would import outcome bias (§6). The scored cousin is Klein & Borders's ShadowBox: trainees rank "typically three to six" options per decision point, are scored by matching the top rank of an SME panel, panel minority views are retained, and the "real learning comes from ... the rationale" [VERIFIED S10]. Gold as a *ranking with retained dissent* fits `holding_basis: contested` and n-ary outcomes better than a single winner. ShadowBox also asks "which cues to monitor" and "what type of information to seek" as decision types [VERIFIED S10], which are the `watch_for` and `ask` outputs.

*(c′) Medicine runs the same loop.* Vanderbilt's restructured M&M asks participants to "consider which management decisions they would have made at key points" before outcome disclosure [VERIFIED S18a]; the emergency-medicine template is case, poll, outcome disclosure, classification [VERIFIED S18b].

**Best argument it doesn't fit.** These are teaching devices for human judgment. They produce discussion, not a computable answer, and the "historical solution" is one choice that may have been lucky or wrong. The value of a Benchbook exemplar comes from an authority-endorsed or reviewed holding, not from history having gone one way. Decision-forcing cases are narrative and single-decision; the Benchbook needs structured factors to be solver-checkable.

---

## 3. Medicine

### 3.1 Illness scripts and the script concordance test

**Case fields.** An illness script has three components: enabling conditions (past history and causes), fault (pathophysiology), consequences (signs and symptoms) [VERIFIED S12c]. Scripts have slots holding "acceptable and unacceptable values" and "default values"; the case with every slot at default is the prototype; remembered patients are "instance scripts" [VERIFIED S12a, Charlin et al. 2007, pp. 1180–81]. Clinicians stress features that "significantly alter the likelihood of the diagnosis" and separate it from mimics [VERIFIED S12b].

**Reasoning steps.** Activate a script (fast recognition of an instance, or deliberate induction), then "search for evidence, to confirm hypotheses or to rule them out"; accumulated acceptable values raise activation until the diagnosis closes [VERIFIED S12a].

**Script concordance test (SCT).** Item = vignette; "if you were thinking of [option]"; "and then you find [new datum]"; "this option becomes" on a −2…+2 scale. Scoring: the panel's modal answer earns 1 point, other answers earn credit proportional to how many panelists chose them [VERIFIED S19, describing Lambert et al. 2009].

**Implications.**
- The SCT item *is* a flip rule with a scoring method: `{option, added_fact, effect: −2..+2}`. For catalog-expressible facts the solver computes the effect by re-running the decision with the fact added and reading the change in margin; a panel or Peter supplies it only for non-catalog facts. Partial credit for dissent fits `contested` holdings. [OURS]
- Mimics and discriminating features are the `bounded` support level. The solver already finds them (nearest neighbor with a different outcome); store the pair as `contrast_case` rather than labeling it. [OURS]

### 3.2 Absolute vs relative contraindication

An absolute contraindication has "no reasonable circumstances for undertaking a course of action"; a relative one raises the risk of complications "but these risks may be outweighed by other considerations" [VERIFIED S13a]. The NIH-OAR glossary: a relative contraindication "should be used with caution," the risk being "acceptable because the benefits outweigh the risks" [VERIFIED S13b]. The structural point: status attaches to an **(action, condition) pair**, not to the condition. Recipient-uncleared is absolute against full release and only relative against a redacted summary. Replace the global strong/weak marker on a factor with `knock_out_for: [option ids]`; IBP knock-outs (strand 16) cover the two-sided case, this is the n-ary extension. [OURS]

### 3.3 GRADE: two axes, not one

GRADE separates certainty of evidence (high, moderate, low, very low) from strength of recommendation (strong or weak, "also known as conditional"), with direction for or against, plus "only in research" and "no recommendation" [VERIFIED S14a]. Handbook: "high confidence in effect estimates does not necessarily imply strong recommendations, and strong recommendations can result from low or even very low confidence" [VERIFIED S14a]. Strength has four determinants: balance of desirable and undesirable consequences; confidence in estimates; values and preferences ("the greater the variability ... the more likely a weak recommendation"); resource use [VERIFIED S14b]. The five paradigmatic situations where strong-with-low-certainty is warranted: low-quality evidence of benefit in a life-threatening situation; low-quality benefit with high-quality harm or cost; low-quality equivalence with high-quality less harm for one option; high-quality equivalence with low-quality harm in one; high-quality modest benefit with low-quality possibility of catastrophic harm [VERIFIED S14b, S14c].

**Implications** [OURS].
- `holding_basis` (recommended | settled | contested) merges *strength of the ruling* with *certainty of the facts under it*. Split it: `holding: {direction, strength: strong|conditional, conditional_on: [equity or deployer-value axis]}`; certainty already lives in fact likelihood and confidence. GRADE defines "conditional" by variability in values and preferences, which is deployer pluralism; a conditional holding should name the axis it depends on.
- Stakes override. Three of the five situations are low-certainty *harm* driving a strong call. Add `stakes: irreversible|catastrophic` to a factor; solver rule: a stakes-flagged factor at ≥ "unlikely" is weighed as if "likely." The Chow loss L could be tied to the same flag instead of being one constant.
- GRADE's "only in research" and "no recommendation" parallel `unprecedented` and `open`.

### 3.4 Red flags

Red flags are "important historical and physical features that may be associated with potentially dangerous conditions"; presence "warrants close attention and potentially diagnostic testing" [VERIFIED S17b]. They are poor verdict evidence: "upwards of 64% of patients with a spinal malignancy had no associated red flags," and "over 80% had at least one red flag but less than 1% were diagnosed with serious pathologies" [VERIFIED S17a, quoting Sikina & Kiel]. So a red flag acts on the *work-up decision*, not on the diagnosis.

**Implication** [OURS]: give factors `kind: support | trigger`. A trigger never enters the reason set; its effect is on the harness's act-or-ask branch (ask or escalate if information can be had within `time_available`). Much of the 139/318 `then: escalate` flip rules are really "this cue is a red flag." An absent trigger licenses nothing, so `-trigger` flip rules should be disallowed.

### 3.5 Morbidity & mortality format

Vanderbilt's restructured conference: patient timeline with decision points; contributing factors classed as procedure, environment, equipment, people, policy, other; action items with completion targets [VERIFIED S18a]. The emergency-medicine template classes errors as system/process, non-remediable or cognitive [VERIFIED S18b]; another uses narrative, process map, six-P fishbone, teaching point, action items [VERIFIED S18c]. "Non-remediable" is medicine's name for a good decision with a bad outcome. The action item is the lesson; in a benchbook it becomes a changed factor or rule. Fields are in §6.

### 3.6 Clinical decision rules (Ottawa ankle)

X-ray if pain in the malleolar zone **and** (bone tenderness along the distal 6 cm of the posterior tibia or fibula edge, or inability to bear weight for four steps); reported "100% sensitive" and 36% fewer X-rays in the original study; a rule-out tool [SECONDARY S15]. Development has six stages — need, derivation, prospective validation, implementation, cost-effectiveness, dissemination — and derived rules often fail in new populations [VERIFIED S16]. Two lessons for flip rules [OURS]: decision rules are tuned for an *asymmetric* error (miss nothing), which is the p* logic already in the harness; and they carry a validation tier. Add `basis: authority|precedent|deployer_policy|author_judgment` to each flip rule; leave-one-out on the casebook is the "validation," and unvalidated author-judgment rules should be visibly marked.

**Best argument medicine doesn't fit.** Its machinery assumes measurable ground truth (a fracture on film, a diagnosis at autopsy) that lets scripts be tested, rules derived and sensitivity computed. National-security value conflicts have no film. Benchbook uncertainty is mostly normative (which equity dominates), not diagnostic. GRADE's certainty describes bodies of effect estimates; there are none here. A 4×2 strength/certainty grid may be finer than one labeler can calibrate.

---

## 4. Structured professional judgment: HCR-20 V3 and SAPROF

**Case fields.** HCR-20 V3 follows seven steps: case information; presence; relevance; risk formulation; scenarios; management; conclusory opinions [VERIFIED S20a]. Presence is "No, Possibly or Partially, and Yes"; evaluators "should document evidence both for and against"; items may be omitted when there is no information [VERIFIED S20a]. Relevance is low, moderate or high. A factor counts as relevant if it materially contributed to past violence, is likely to influence a future decision to act violently, may impair non-violent problem solving, or is crucial to manage [VERIFIED S20a]. It is separate because a population-level factor may matter differently to this individual: evaluators "need to investigate the role that it has played in past violence, or may play in future violence" [VERIFIED S20a]. Formulation integrates the case into an explanation, casting factors as motivators (raise perceived benefit), disinhibitors (lower perceived cost) or destabilizers (impair decision making). Scenarios are repeat, twist, escalation and optimistic, driven by "what am I trying to prevent?" [VERIFIED S20a]. Conclusions are low/moderate/high (routine/elevated/urgent) [VERIFIED S20a]. No cut score: the manual is quoted as saying more items with higher relevance "suggests a higher level of current risk" [SECONDARY S20c]. Its stated reasons against purely actuarial use: sample dependence, exclusion of potentially important factors, instability across samples, and the difficulty of applying group estimates to individuals [VERIFIED S20a]. SAPROF rates 17 protective factors 0 ("clearly absent or there is no evidence"), 1 ("may be present or is present to some extent") or 2 ("clearly present"), in three subscales, with a five-point final protection judgment; it also yields a 0–34 total, so it sits nearer the actuarial end [VERIFIED S21].

**Checking the "partially applied mitigator" fix.** The middle rating is "Possibly or Partially" in V3 [VERIFIED S20a], "possibly/partially present (score of 1)" in V2 [VERIFIED S20d], and "may be present or is present to some extent" in SAPROF [VERIFIED S21]. It merges *uncertainty about whether* with *extent to which*. The digest of the V3 overview article I opened reports no definition of partial, and I could not open the manual, so what the manual itself says is [UNVERIFIED]. A real clearance decision shows the Benchbook's case is wider than either. In DOE OHA PSH-23-0088, applying Guideline F, mitigating condition (d) ("initiated and is adhering to a good-faith effort to repay overdue creditors or otherwise resolve debts") was "only partially met": payment plans existed but $513 of more than $25,000 had been paid, under 2%. Condition (b) ("largely beyond the person's control ... and the individual acted responsibly") was met on its first limb and not fully on the second: events beyond his control, but he "did not always respond responsibly" [VERIFIED S22a]. That is partial-by-*extent* and partial-by-*conjunct*. One P label does not tell a solver which, and neither is "possibly."

**Implications** [OURS].
1. Do not import a tri-valued P. Decompose instead. A conjunctive mitigator becomes sub-factors (b1 beyond control, b2 acted responsibly), the intermediate-factor pattern in strand 16; extent-partial uses the existing nested threshold factors; "possibly" stays in the likelihood field. "Partial" is then derived (some children met), not labeled.
2. Keep relevance, cheaply. HCR relevance is Horty's reason membership, graded. Record only exceptions: `set_aside: [{factor, why: not_causal|stale|substituted|outweighed}]`; every present factor in `reason` defaults to high. Solver check: the outcome must follow from the non-set-aside factors, and `set_aside` must not contradict the model's own significance results.
3. Repeat, twist, escalation and optimistic describe the *direction of a new situation's departure from a precedent*, which the five support levels (a property of the casebook) do not. Use them to stratify out-of-distribution test items.
4. Formulation → scenarios → management → judgment matches step 5 (residual judgment). Require the model's residual judgment to name driver factors from the catalog, so the formulation is checkable.

**Best argument it doesn't fit.** SPJ keeps the final call non-mechanical on purpose; a verifiable-reward pipeline wants the opposite, so the solver only checks inputs and the model may free-associate on the last step. HCR-20's 20 generic items are rated by trained raters for individuals, whereas the catalog is per sub-area and richer. Its output is an ordinal risk level, not a choice among actions. And its own P category is the ambiguity Peter wants to remove.

---

## 5. Safety engineering: STPA and bow-tie

**STPA case fields.** Losses, hazards, a control structure, then unsafe control actions (UCAs). A UCA is one that "in a particular context and worst-case environment, will lead to a hazard," written as source controller, type, control action, context, hazard link [VERIFIED S23b]. Four types: not providing the action causes a hazard; providing it causes a hazard; a potentially safe action "too early, too late, or in the wrong order"; an action that "lasts too long or is stopped too soon" (continuous actions) [VERIFIED S23b]. Controllers act on a process model, and "accidents often occur when the process model is incorrect" (inconsistent, incomplete or incorrect) [VERIFIED S23a]. In a UCA *context table*, each control action is crossed with process-model variable states and each cell is flagged hazardous if provided any time, too early or too late [SECONDARY S23d]. Thomas's MIT report formalized STPA and automated the analysis [VERIFIED S23c]. STPA has already been applied to LLM agents: Mylius models an untrusted agent, trusted monitor and human auditor, with UCAs such as a team delaying shutdown after an exfiltration attempt [VERIFIED S23e]; Doshi et al. derive requirements and formalize them as information-flow and temporal-logic specifications [VERIFIED S23f].

**Assessment as a perturbation generator** [OURS]. The fit is good structurally. `agent_role` is a position in a control structure, the approver is another controller, "no human reachable, use the default" is a broken feedback path, and the agent's beliefs about U.S.-person status or the authority in force are process-model variables (the `status|likelihood` on facts). That yields typed perturbation operators for synthetic variants and flip rules:
1. **Process-model flip**: a belief the agent holds is wrong (flip a fact's status).
2. **Timing**: act before approval, after the window closes, or out of order. Options then need a `timing` attribute.
3. **Duration**: continue or stop a continuous action (collection, retention, monitoring). This is "applied too long / stopped too soon."
4. **Lost feedback**: approver unreachable or approval stale, which routes to the default outcome.
5. **Role shift**: recommend becomes execute.
Operators 2 and 3 give typed language for the pilot's "not at this time" judgments. As a *decision table*, (option, context conjunction) → unsafe is a pure solver lookup, and a machine can prefill cells: unsafe if the context contains a `knock_out_for` factor for that option; Peter labels only the exceptions.

**Best argument it doesn't fit.** STPA defines unsafe by a hazard, so it outputs constraints (knock-outs), not weighings. It can say A is unsafe; it cannot say whether B or C is better, and the winners here are usually partial moves. Full tables blow up (3 options × 4 types × 4 binary variables = 192 cells per sub-area), so it works as a checklist and prefilled generator, not a hand-labeled field. Its agent-safety precedents produce specifications, not case-based reasoning.

**Bow-tie case fields.** Hazard; top event ("the loss of control of the hazard"); threats on the prevention side; consequences on the mitigation side; prevention barriers ("stop threats from resulting in the top event"); mitigation barriers (reduce "the scale of ... undesired consequences"); degradation factors (formerly escalation factors) and degradation controls; barriers must be "effective, independent and auditable" [VERIFIED S24a]. Practice advice: name specific threats, not "human error"; name specific consequences [VERIFIED S24b]. Reasoning is barrier adequacy along each path; there is no weighting.

**Implication** [OURS]. 72 of 100 Hard-Calls aligned moves are partial ("do the lawful part, hold/route the rest"). A partial move is a barrier insertion. Model an option as `base_action` plus `barriers: [{type: preventive|mitigative, addresses: equity, actor}]`. Solver checks: (i) coverage: every equity that the base action burdens (because a present factor on another option's side supports it) has at least one barrier addressing it; (ii) independence: two barriers with the same actor and mechanism count once; (iii) a "partial" option whose barriers address nothing is just the base action. The compromise is then *derived* from coverage rather than labeled. Cost: about 1–2 minutes per case to re-encode a partial move; the solver check is easy.

**Best argument it doesn't fit.** Bow-tie presupposes one hazard to keep under control; a release-versus-retain equity conflict is two goods. It has no weights, and the sources I opened give no validation evidence for barrier-adequacy judgments.

---

## 6. Evaluating decisions in hindsight

**Case fields, by tradition.**
- *Reason's culpability tree* (as reproduced in a 2008–09 Baines Simmons deck; the book's Figure 9.4 was not opened): "Did they follow all procedures and best practices?"; "Did they think they were following correct procedures and practices?"; "Were the consequences as intended?", ending in categories such as normal compliance, routine, situational, optimizing and exceptional violation, unintentional violation [SECONDARY S25c].
- *NPSA Incident Decision Tree* (Meadows, Baker & Butler 2005): deliberate-harm, incapacity, foresight (did protocols exist, were they poor, conflicting, ignored) and substitution tests; it separates action from result: "In the majority of cases, the actions will be as intended, but the outcome will not" [VERIFIED S25a].
- *Substitution test*, verbatim as attributed to Johnston 1995: "Substitute for the person concerned someone coming from the same work area and possessing comparable qualifications and experience. Then ask: 'In the light of how the events unfolded and were perceived by those involved in real time, is it likely that this new individual would have behaved any differently?'" [VERIFIED S25b].
- *Just Culture algorithm*: human error, at-risk behavior, reckless behavior ("a conscious disregard of a substantial and unjustifiable risk") map to console, coach, discipline [VERIFIED S25d].
- *HFACS*: a decision error is "intentional behavior that proceeds as intended, yet the plan proves inadequate or inappropriate for the situation," split into procedural errors, poor choices and problem-solving errors; other unsafe acts are skill-based errors, perceptual errors, routine and exceptional violations [VERIFIED S28].
- *Air Force accident boards* (C-130J, 19 May 2013): Part 1 Summary of Facts, Part 2 Statement of Opinion; causes found by "clear and convincing evidence," substantially contributing factors by "the preponderance of evidence"; named factors include channelized attention, risk assessment, delayed necessary action, response set, procedural error [VERIFIED S29a].
- *AR 15-6*: a finding is "a clear and concise statement of a fact that can be readily deduced from evidence in the record"; standard is preponderance, "the greater weight of credible evidence"; recommendations must be "consistent with and logically based on the findings" [VERIFIED S29b; the digest's title for the 2025 edition looked wrong, check]. The investigator's guide requires each finding to cite exhibits, each recommendation to cite its findings, and, for conflicting witnesses, that "you must decide who you believe and explain in your findings why" [VERIFIED S29c].

**The bias evidence.** Baron & Hershey: the same medical decisions were rated better when they succeeded; a recent replication (N = 692) found the effect even among participants who said outcomes should not matter (d = 0.64) [VERIFIED S26a]. Fischhoff 1975: outcome knowledge raised postdicted likelihood *and* changed "the perceived relevance of event-descriptive data," and subjects were "largely unaware" of it [VERIFIED S26b]. Dekker: "People do what makes sense to them at any given moment, given their goals, attentional focus, and knowledge"; "if only" counterfactuals describe "a reality that did not happen" [SECONDARY S27, blog digests of his book].

**What it changes** [OURS].
1. *Hindsight reweights factor salience, not only probabilities.* A factor that "caused" the bad result looks more relevant afterward, and the person tagging cannot feel it. Negative-exemplar tags must come from `known_at_decision` facts, ideally by a second pass that never sees the outcome or the findings.
2. *Three separate judgments.* `decision_assessment` (acceptable | unacceptable, or an `acceptable_range` of options, judged ex ante), `result` (good | bad | mixed | unknown), and `failure_mode` (HFACS-derived vocabulary; culpability only if wanted). The 2×2 gives four exemplar types, including good decision/bad outcome (a positive exemplar with a bad result) and bad decision/good outcome (a negative exemplar that worked). v6's single `outcome` cannot hold that.
3. *A `review` block* for reviewed cases: `{body, standard: preponderance|clear_and_convincing, findings: [{id, text, evidence_refs}], recommendations: [{text, cites}], substitution_test: {result, basis}}`. AR 15-6's finding-to-exhibit and recommendation-to-finding links are the provenance chain; the board's two evidence tiers act like ICD 203 confidence per finding.
4. *Credibility as a finding that gates facts.* The pilot's credibility misfit (6 of 10) is what AR 15-6 tells investigators to write out. Represent it as `fact.depends_on: finding_id`.
5. *A computable check.* Run the solver on the `known_at_decision` facts against the casebook as it stood at the time. If it says precedent supported Y and the decider did X, flag `deviation_from_precedent`, and compare with the board's finding. This needs a dated casebook, so it is ambitious.
6. *Flip rules for negative exemplars* should read "what fact would have made the chosen option right," not "what the decider should have done," to stay inside the decider's information (Dekker).

**Best argument it doesn't fit.** Reason's tree and Just Culture allocate blame among people; the Benchbook teaches an agent what to do, so culpability fields cost labeling and add little. Boards are themselves after-the-fact and written for command action, not for training data. Seed reports may be redacted. And Peter, reading the outcome, is subject to the same bias; Fischhoff found people do not notice it.

---

## 7. Intelligence analysis: Analysis of Competing Hypotheses (ACH)

**Case fields.** Hypotheses; evidence and arguments, each rated for credibility and relevance in the PARC tool [SECONDARY S30c]; a matrix of hypotheses against evidence with consistent/inconsistent cells. The eight steps: identify hypotheses; list evidence for and against; build the matrix and "analyze the 'diagnosticity' of the evidence"; refine, deleting evidence "that have no diagnostic value"; draw tentative conclusions "by trying to disprove hypotheses rather than prove them"; test sensitivity to a few critical items ("consider the consequences if that evidence were wrong"); report all hypotheses' relative likelihood; "identify milestones for future observation" [VERIFIED S30a].

**Reasoning.** "Evidence is diagnostic when it influences your judgment on the *relative* likelihood of the various hypotheses"; "If an item of evidence seems consistent with all the hypotheses, it may have no diagnostic value at all" [VERIFIED S30b]. Work across the matrix one evidence item at a time; "A single item of evidence inconsistent with a hypothesis may be sufficient grounds for rejecting that hypothesis" [VERIFIED S30a]. Heuer adds that there is "no guarantee that ACH will produce a correct answer" [VERIFIED S30a]. Evidence that it reduces bias is thin [SECONDARY S30c].

**What it changes** [OURS].
1. *Diagnosticity is factor salience in the n-ary case.* Zhang's significance already asks whether a factor can be emphasized and cannot be downplayed. ACH says more: a factor matters only if it *discriminates among the options*. v6 ties each factor to one favored letter. With 3–4 options and a compromise usually winning, a factor "favoring B" may be *consistent with C*, because C honors that equity in part. My hypothesis (untested): this is one source of the 21 of 100 reason sets that mix sides.
2. *Derive the matrix; don't label it.* Give options `protects: {equity: full|partial|none}` (templated per sub-area; roughly 15–20 cells per case). Factor-to-equity edges already exist, so consistency(option, factor) is derived. Solver rule: eliminate options inconsistent with a knock-out; among survivors, minimize weighted inconsistency (ACH's "least evidence against"). The compromise wins when it covers the most equities. Combine with the barrier structure in §5. Before adopting, test whether the rule reproduces the labeled winners on the 100 Hard-Calls cases.
3. *Compute ACH step 6.* `critical_facts` = the minimal fact set whose removal or falsity flips the outcome. The solver computes it; the model names it; overlap is the reward. This replaces hand-authored flip rules for catalog facts and handles credibility (a critical fact resting on a low-credibility source is flagged).
4. *Step 8 is the third independent statement* of "record what you would expect to see next" (with RPD and data/frame). It supports `anomaly_cues`.

**Best argument it doesn't fit.** ACH ranks hypotheses about what is *true*; options are actions judged by *values*. "Inconsistent" for an option means "fails to protect an equity," a value judgment ACH does not supply. Inconsistency counting ignores weights. Diagnosticity filtering could delete factors that matter for *how* to act rather than *which* option.

---

## Ranked: the five ideas from this strand most worth adopting

**1. Cut every case at the decision point and keep two layers.** Fields: `known_at_decision` on each fact; an `after` block; a `review` block for reviewed cases; `decision_assessment`, `result` and `failure_mode` as three separate fields (§2, §6).
- *Fixes:* the pilot's "tags nearly encode the verdict" leak; makes negative, lucky and unlucky exemplars expressible; unifies exemplar cards and live scenarios; makes credibility findings explicit.
- *Cost:* labeling is one boolean per fact (about 2 minutes per case) plus a `review` block only where a review exists. The real cost is an outcome-blind second pass for negative exemplars. Solver: trivial (partition facts, reward tags from the as-of set only, script a leakage check).

**2. Decompose "partial"; record relevance as exceptions.** Conjunctive mitigators become sub-factors, extent uses threshold factors, "possibly" stays in likelihood, and `set_aside: [{factor, why}]` marks present-but-immaterial factors (§4).
- *Fixes:* partially applied mitigators (5 of 10 in the pilot), which HCR-20's P label would not.
- *Cost:* one-time catalog splitting per sub-area; per case 0–2 `set_aside` entries. Solver: moderate (derive parents from children; check `set_aside` against the model's own significance results).

**3. A frame-validity channel.** `frame_conditions`, `anomaly_cues` with a typed response (ask, next option, unprecedented), and `kind: trigger` factors that never enter the reason set (§1, §3.4, §7).
- *Fixes:* the 210 of 318 flip rules on non-catalog considerations; most of the 139 `then: escalate` rules; gives the harness's "ask on an unlisted consideration" rule a gold label.
- *Cost:* 1–3 short items per case. Solver: simple rules (a failed condition caps support at `bounded`; a trigger routes to ask).

**4. Options as base action plus barriers, scored by derived equity coverage.** Adds ACH-style diagnosticity, a least-inconsistency rule after knock-outs, `knock_out_for` per (action, condition), and solver-computed `critical_facts` (§5, §7, §3.2).
- *Fixes:* n-ary outcomes, compromise moves (72 of 100), mixed-side reason sets (21 of 100), and most hand-written flip rules.
- *Cost:* `protects` per option (templated per sub-area), 1–2 minutes per case to re-encode partial moves. Solver: a new scoring rule and a critical-fact search; **test first against the 100 labeled Hard-Calls winners**, since it may not reproduce them.

**5. Split the holding's strength from its certainty, and add stakes.** `holding: {direction, strength: strong|conditional, conditional_on}`; `stakes: irreversible|catastrophic` on a few factors (§3.3).
- *Fixes:* the `holding_basis` conflation; principled behavior at low certainty and high stakes; makes deployer-value dependence explicit.
- *Cost:* one enum, one `conditional_on`, one flag on a handful of factors. Solver: small (threshold shift; optionally derive L from stakes).

**Next tier.** STPA's four UCA types as an authoring checklist and offline perturbation operators (timing, duration, lost feedback); SCT-style `{option, added_fact, effect}` items scored against a panel (Peter and the solver's computed effect as two panelists); ShadowBox-style ranked gold with retained minority; flip-rule `basis` tiers; `typicality` and `time_available` from CDM.

---

## Sources (S-numbers as used above; every URL was opened unless marked)

- S1 Klein & MacGregor (1988), *Knowledge Elicitation of Recognition-Primed Decision Making*, ARI Tech. Rep. 799. https://apps.dtic.mil/sti/pdfs/ADA199076.pdf
- S2 Athens (1992), *Unravelling the Mystery of Battlefield Coup d'oeil*, SAMS monograph. https://apps.dtic.mil/sti/tr/pdf/ADA264507.pdf
- S3 ShadowBox, primer on RPD (2025). https://www.shadowboxtraining.com/news/2025/06/17/a-primer-on-recognition-primed-decision-making-rpd/
- S5 Hoffman, *Protocols for Cognitive Task Analysis* (IHMC). https://www.ihmc.us/wp-content/uploads/2025/06/Protocols-for-Cognitive-Task-Analysis.pdf
- S6 Assadi et al. (2022), Frontiers in Digital Health, and its CDM probe table. https://www.frontiersin.org/articles/1016522 ; https://public-pages-files-2025.frontiersin.org/articles/1016522/file/table_1.pdf/1016522_supplementary-materials_tables_1_pdf/1
- S7 Klein, Moon & Hoffman (2006), "Making Sense of Sensemaking 2," *IEEE Intelligent Systems* 21(5):88–92. https://perigeantechnologies.com/publications/MakingSenseofSensemaking2-AMacrocognitiveModel.pdf
- S8 Situation awareness (Endsley 1995 as summarized). https://en.wikipedia.org/wiki/Situation_awareness
- S9 Kahneman & Klein (2009), "Conditions for intuitive expertise," *Am. Psychologist*. http://bear.warrington.ufl.edu/brenner/mar7588/Papers/kahneman-klein-2009.pdf
- S10 Klein & Borders (2016), ShadowBox, *J. Cognitive Engineering and Decision Making*. https://www.shadowboxtraining.com/wp-content/uploads/2021/05/The_ShadowBox_Approach_to_Cognitive_Skills_Trainin.pdf ; https://www.gary-klein.com/sb
- S11 Gudmundsson: (a) Canadian Army Line of Sight, https://www.canada.ca/en/army/services/line-sight/articles/2021/09/decision-forcing-cases.html ; (b) https://tacticalnotebook.substack.com/p/decision-forcing-cases ; (c) https://tacticalnotebook.substack.com/p/how-to-play-decision-forcing-cases ; (e) https://tacticalnotebook.substack.com/p/the-two-types-of-decision-games . (d) Hoffman (2023), https://www.themaneuverist.org/post/developing-a-decision-forcing-case-by-captain-madeline-hoffman-usmc
- S12 (a) Charlin, Boshuizen, Custers & Feltovich (2007), "Scripts and clinical reasoning," *Med Educ* 41(12):1178–84. https://eoa.umontreal.ca/wp-content/uploads/sites/70/2015/07/Charlin_2007-2.pdf ; https://pubmed.ncbi.nlm.nih.gov/18045370/ (b) https://clinicalreasoning.org/illness-scripts/ (c) https://link.springer.com/chapter/10.1007/978-3-319-64828-6_3
- S13 (a) https://en.wikipedia.org/wiki/Contraindication (b) https://clinicalinfo.hiv.gov/en/glossary/relative-contraindication
- S14 (a) GRADE Handbook, https://gdt.gradepro.org/app/handbook/handbook.html (b) Andrews et al. (2013), "GRADE guidelines: 15," *J Clin Epidemiol* 66(7):726–735, https://www.jclinepi.com/article/S0895-4356(13)00054-1/fulltext (citation: https://www.sciencedirect.com/science/article/abs/pii/S0895435613000541) (c) PDF copy https://www.societaitalianatrapiantidiorgano.com/wp-content/uploads/2018/06/GRADE-Guidelines-15-Determinants-of-a-recommendation-direction-and-strength.pdf
- S15 Ottawa ankle rules (Stiell et al. 1992 as summarized). https://en.wikipedia.org/wiki/Ottawa_ankle_rules
- S16 Stiell & Wells (1999), *Ann Emerg Med* 33(4):437–447. https://www.sciencedirect.com/science/article/abs/pii/S0196064499703094
- S17 (a) Sikina & Kiel (2022), ACEP. https://www.acep.org/sportsmedicine/newsroom/newsroom-articles/august2022/re-evaluating-red-flags-for-back-pain (b) Della-Giustina & Osborne (2025), Consultant360. https://www.consultant360.com/peer-reviewed/revisiting-red-flags-acute-low-back-pain
- S18 (a) Deis et al., AHRQ *Advances in Patient Safety* vol. 2. https://www.ncbi.nlm.nih.gov/books/NBK43710/ (b) Council of EM Residency Directors, WestJEM (2020). https://westjem.com/articles/evolving-from-morbidity-and-mortality-to-a-case-based-error-reduction-conference-evidence-based-best-practices-from-the-council-of-emergency-medicine-residency-directors.html (c) Walker et al. (2016), MedEdPORTAL. https://www.mededportal.org/doi/10.15766/mep_2374-8265.10475
- S19 Lambert et al. (2009), SCT in radiation oncology, *Radiat Oncol* 4:7. https://link.springer.com/doi/10.1186/1748-717X-4-7
- S20 (a) Douglas et al. (2014), "HCR-20V3: Development and Overview," *Int J Forensic Ment Health* 13(2):93–108. https://www.antoniocasella.eu/archipsy/Douglas_2014.pdf (c) https://www.academia.edu/36370705/The_Interrater_Reliability_and_Predictive_Validity_of_the_HCR_20V3_in_Common_Workplace_Environments (d) https://psychology.iresearchnet.com/forensic-psychology/violence-risk-assessment/hcr-20-violence-risk-assessment-scheme/
- S21 Kashiwagi et al. (2018), SAPROF Japanese version, *Ann Gen Psychiatry*. https://link.springer.com/10.1186/s12991-018-0175-5
- S22 (a) DOE OHA, PSH-23-0088 (2023). https://www.energy.gov/sites/default/files/2023-09/PSH-23-0088.pdf
- S23 (a) STPA tutorial (Thomas, MIT). https://www.flighttestsafety.org/images/Systems-Theoretic-Process-Analysis-STPA-v9-v2-san.pdf (b) https://ptolemy.berkeley.edu/projects/cps/Unsafe_Control_Actions.html (c) Thomas, MIT report (2012). https://www.osti.gov/biblio/1044959 (d) Petzold, ESWC 2022. https://cdn.files.pg.edu.pl/wimio/10th%20European%20STAMP%20Workshop%20and%20Conference%202022/Petzold_ESWC%202022.pdf (e) Mylius, arXiv:2506.01782. https://arxiv.org/pdf/2506.01782v1 (f) Doshi et al., arXiv:2601.08012. https://arxiv.org/html/2601.08012v1
- S24 (a) Johnson et al. (2018), Hazards 28. https://www.icheme.org/media/16937/hazards-28-paper-31.pdf (b) https://www.wolterskluwer.com/en/solutions/enablon/bowtie/expert-insights/barrier-based-risk-management-knowledge-base/the-bowtie-method
- S25 (a) Meadows, Baker & Butler (2005), Incident Decision Tree. https://www.ncbi.nlm.nih.gov/books/NBK20586/ (b) http://www.nickmilton.com/2017/02/the-substitution-test-for-learning-from.html (c) Baines Simmons deck. https://www.raes-hfg.com/reports/21may09-Potential/21may09-baines.pdf (d) https://casrai.org/guides/just-culture-algorithm
- S26 (a) Replication of Baron & Hershey (1988), *Int Rev Soc Psychol*. https://rips-irsp.com/articles/10.5334/irsp.751 (b) Fischhoff (1975), *JEP:HPP* 1(3):288, abstract. https://www.researchgate.net/publication/10631443_Hindsight_is_not_equal_to_foresight_The_effect_of_outcome_knowledge_on_judgment_under_uncertainty
- S27 Dekker, *Field Guide* (2006), via https://roblog.co.uk/2021/10/the-field-guide-to-understanding-human-error/ and https://www.kitchensoap.com/2013/10/29/counterfactuals-knight-capital/
- S28 Shappell & Wiegmann (2000), HFACS. https://commons.erau.edu/cgi/viewcontent.cgi?article=1777&context=publication ; https://skybrary.aero/articles/human-factors-analysis-and-classification-system-hfacs
- S29 (a) USAF AIB report, C-130J, 19 May 2013. https://www.airandspaceforces.com/PDF/AircraftAccidentReports/Documents/2013/051913_C-130J-30_FOBShank_full.pdf (b) AR 15-6, 2025 ed. copy. https://www.defendyourservice.com/wp-content/uploads/2026/01/AR-15-6-2025ed.pdf (c) AR 15-6 investigator guide. https://home.army.mil/carson/9616/5089/9449/ar-15-6.pdf
- S30 Heuer, *Psychology of Intelligence Analysis*: (a) ch. 8, http://all.net/journal/deception/ciabook2/www.cia.gov/csi/books/19104/art11.html (b) ch. 4, http://all.net/journal/deception/ciabook2/www.cia.gov/csi/books/19104/art7.html. The all.net pages copy the CIA book; I used them because the CIA PDF excerpt I opened stopped before chapter 8 (nothing was blocked). (c) https://en.wikipedia.org/wiki/Analysis_of_competing_hypotheses
- Also opened: 32 CFR 147.8 (older Guideline F text), https://www.law.cornell.edu/cfr/text/32/147.8
