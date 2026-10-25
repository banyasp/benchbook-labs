# Strand 25 — ML work (2023–2026) on how cases, norms and precedents are represented for LLMs to reason from and be trained on

Prepared 2026-09-29 for the Benchbook exemplar-schema review (v6). Earlier strands 16/17/18 are cited, not repeated. A longer draft with more per-paper detail is kept in the session scratchpad (`25-full-version.md`).

## How to read the tags

- **[VERIFIED]** = I opened the page (arXiv abstract/HTML/PDF, ACL Anthology, vendor doc) and the claim is there. My fetch tool returns a machine-generated digest, not raw text, so a number that appears in only one digest and that I could not cross-check is marked "(single extraction)"; treat those as leads to confirm.
- **[SECONDARY]** = from a named secondary source I opened (search-result listing, project page). **[UNVERIFIED]** = title/snippet only, or the fetch failed. **[OURS]** = my inference.
- Where two extractions of one paper disagreed I say so (see appendix).

## Headline findings

1. **Contextual integrity (CI) is the one non-legal schema with a mature ML pipeline that mirrors the Benchbook's seed → scenario → behavior flow** (PrivacyLens: 493 seeds → vignettes → agent trajectories; GPT-4 probing accuracy 98.99% vs about 25% leakage in action). Recommendation: a typed CI flow header **in addition to** factors, with situational factor tags derived from the tuple (Section 1).
2. **Transformers default to case-based procedure execution** (Hu et al.), which is what "1-NN on tags tied the solver" looks like; the published remedy is Rule-Following Fine-Tuning: rule in the input, recite and apply step by step (Section 2).
3. **Argumentative LLMs give no accuracy gain over chain-of-thought.** Take their monotonicity ("contestability") properties as solver-checked invariants; skip LLM-scored arguments (Section 3).
4. **Pittsburgh/TUM 2025–26 work is evaluation, not training.** Told to abstain on case pairs sharing no factors, at least four of eight models abstained 0–3.33% of the time (GPT-4o 86.67%). I found no paper that trains a model on factor-based distinguishing with a symbolic verifier (Section 4).
5. **Valid controlled variation needed structure-before-text, per-condition generation and a human manipulation check**; an LLM generator failed to realize the structure alone (OffTheRails). Presentational edits flip 7.5–24.3% of frontier-model moral judgments (Section 5).
6. **RLVR failure modes apply directly:** extensional verifiers get gamed, monitored reasoning gets obfuscated, random or format-only rewards give large gains on Qwen but not Llama/OLMo. v6's option-letter-in-the-ID rule and the C-heavy outcome prior are shortcuts of this kind (Section 6).
7. **Deployed policy-as-prompt formats are vendor guidance, not experiments**; I found no controlled structured-vs-prose comparison (Section 7).

---

## 1. Contextual integrity (CI) as a case schema for LLM agents

### 1.1 What a "case" contains

**Source.** Nissenbaum, "Privacy as Contextual Integrity," Washington Law Review 79(1), 2004: norms of *appropriateness* ("what information about persons is appropriate, or fitting, to reveal in a particular context") and norms of *flow or distribution*; distribution principles include confidentiality, need, entitlement, obligation, and the list is "probably open-ended." The 2004 article does not use the phrase "transmission principle"; the five-parameter form used in ML (sender, recipient, subject, attribute, transmission principle) is a later formalization [attribution OURS]. [VERIFIED — https://nissenbaum.tech.cornell.edu/papers/H.%20Nissenbaum,%20_Privacy%20as%20Contextual%20Integrity.pdf]

**A deterministic CI checker already exists.** Barth, Datta, Mitchell, Nissenbaum, "Privacy and Contextual Integrity: Framework and Applications," IEEE S&P 2006: first-order linear temporal logic over traces of communication actions (sender, recipient, subject, attribute, transmission principle as a temporal condition); **positive norms** permit a flow when the condition holds, **negative norms** permit it *only* when it holds; "weak compliance" of a proposed action against a history is polynomial-time, strong compliance PSPACE; HIPAA, COPPA and GLBA provisions are encoded. [VERIFIED content — https://theory.stanford.edu/people/jcm/papers/barth-datta-mitchell-nissenbaum-2006.pdf ; year/venue from IEEE Xplore listing, [SECONDARY]]

**ML schemas.**
- **ConfAIde** (Mireshghallah, Kim, Zhou, Tsvetkov, Sap, Shokri, Choi; ICLR 2024 spotlight; arXiv 2310.17884): four tiers; Tier 2 is a factorial CI design (7 information types × 7 actors × 2 uses = 98 vignettes, human-rated); "GPT-4 and ChatGPT reveal private information in contexts that humans would not, 39% and 57% of the time." [VERIFIED abstract — https://arxiv.org/abs/2310.17884 ; tier design single extraction, https://arxiv.org/pdf/2310.17884]
- **PrivacyLens** (Shao, Li, Shi, Liu, Yang; NeurIPS 2024 D&B; arXiv 2409.00138): seed = 5-tuple (data type, subject, sender, recipient, transmission principle) → vignette → agent trajectory in a sandbox with simulated tools (final action removed so the model must produce it); 493 seeds from 15 U.S. regulations, privacy literature and crowdsourcing; generation gated by unit tests with an LM "Surgery Kit" repair step. GPT-4 and Llama-3-70B leak in 25.68% and 38.69% of cases even with privacy-enhancing instructions (abstract); the HTML body gives 24.54% for GPT-4 with that prompt beside **98.99% probing accuracy** (figures differ; unresolved). Leakage is judged by a few-shot Mistral-7B-Instruct classifier (0.92 accuracy vs human majority on 50 actions; Fleiss' kappa 0.56). [VERIFIED — https://arxiv.org/abs/2409.00138 ; https://arxiv.org/html/2409.00138v2]
- **CI-Bench** (Cheng, Wan, Abueg, Ghalebikesabi, Yi, Bagdasarian, Balle, Mellem, O'Banion; Google; arXiv 2409.13903): 44,100 synthetic cases, eight domains, four sub-tasks (context comprehension, norm recognition, appropriateness, response). Weakest at identifying the *recipient*; "well-defined rules and guidelines for data flow significantly improve the accuracy of models in assessing information exchanges." [VERIFIED — https://arxiv.org/abs/2409.13903]
- **GoldCoin** (Fan, Li, Deng, Wang, Song; HKUST; EMNLP 2024 main, pp. 3321–3343; arXiv 2406.11149): synthetic "court cases" generated from HIPAA norms (309 cases; one extraction gave 269 permit + 40 forbid norms), each = narrative + CI fields (sender/recipient/subject with roles, information type, optional purpose/authorization/consent/belief) + norm ID + applicability and compliance conclusions. LoRA on 7B/13B models vs zero-shot, "Law Recitation" (train on statute text) and "Direct Prompt." **Compliance accuracy on real HIPAA cases** (107 by my arithmetic): Mistral-7B 50.47 zero-shot → 53.27 law recitation → 53.27 direct prompt → **75.70** GoldCoin (macro-F1 66.98); Llama2-13B 65.42 → 68.22 → 73.83 → 76.64. [VERIFIED — https://aclanthology.org/2024.emnlp-main.195/ ; https://arxiv.org/html/2406.11149]
- **PrivaCI-Bench** (Li, Hu, Jing, Chen, Hu, Han, Chu, Hu, Song; ACL 2025): CI plus legal compliance over regulations, court cases, privacy policies; LLMs capture key CI parameters but need "further advancements for privacy compliance." [VERIFIED — https://aclanthology.org/2025.acl-long.518/]
- **AirGapAgent** (Bagdasarian, Yi, Ghalebikesabi, Kairouz, Gruteser, Oh, Balle, Ramage; CCS 2024; arXiv 2405.05175): a data-minimization step restricts what the agent sees to what the task needs; under a context-hijack attack unprotected Gemini Ultra's protection falls 94% → 45%, AirGapAgent holds 97%. [VERIFIED abstract — https://arxiv.org/abs/2405.05175]
- **CIMemories** (Mireshghallah, Mangaokar, Kokhlikyan, Zharmagambetov, Zaheer, Mahloujifar, Chaudhuri; arXiv 2511.14937): the same attribute is necessary for one task and inappropriate for another; up to 69% attribute-level violations; GPT-5's rise from 0.1% to 9.6% as tasks accumulate from 1 to 40. [VERIFIED abstract — https://arxiv.org/abs/2511.14937]

### 1.2 How reasoning proceeds, and what has been trained

- **CI-CoT / CI-RL** (Lan, Inan, Abdelnabi, Kulkarni, Wutschitz, Shokri, Brinton, Sim; NeurIPS 2025; arXiv 2506.04245). Prompt the model to extract sender/recipient roles, subject, purpose and transmission principle, classify each attribute (necessary/helpful/optional/inappropriate), then answer. GRPO on ~700 synthetic items (590/66/73 split). **Reward = format (−1 if `<think>`/`<answer>` tags missing) + keyword term |required present|/|required| − |restricted present|/|restricted|.** Transfers to PrivacyLens and ConfAIde. Authors' limits: no error bars at submission, synthetic data, keyword reward "simple and auditable but coarse," ≤14B models, **no SFT-vs-RL comparison**. [VERIFIED — https://arxiv.org/abs/2506.04245 ; https://arxiv.org/html/2506.04245v2 ; per-benchmark percentages not cross-checked]
- **Microsoft Research write-up** (Afonja et al., 25 Nov 2025): an inference-time "PrivacyChecker" extracting flow tuples cut leakage 33.06% → 8.32% (GPT-4o) and 36.08% → 7.30% (DeepSeek-R1); CI-CoT cut leakage but also helpfulness; CI-RL restored much of it. [VERIFIED — https://www.microsoft.com/en-us/research/blog/reducing-privacy-leaks-in-ai-two-approaches-to-contextual-integrity/]
- **Franchi, Choksi, Triedman, Nissenbaum**, "Reinforcing privacy reasoning in LLMs via normative simulacra from fiction" (arXiv 2604.20904, 21 Apr 2026): structured CI norm representations extracted from novels; SFT then GRPO with a composite reward and "per-completion contrastive scoring" against memorizing source-specific patterns; SFT alone installs "a conservative prior toward restricting information flow," improving situation recognition but not judgment accuracy. **Abstract only** — full-text fetches failed (HTTP 429). [VERIFIED abstract — https://arxiv.org/abs/2604.20904 ; body [UNVERIFIED]]

### 1.3 What it implies for the Benchbook

The pilot's problems (tags from the judge's findings encode the verdict; untyped distinctions; unvalidated counterfactual pairs) are what CI datasets avoided by making the *situation* a typed record before any judgment.

1. **Add a `flows` header to privacy/civil-liberties cases; do not replace factors.** `flows: [{sender_role, recipient_role, subject_role, info_type, transmission_principle, prior_flows}]`, closed per-sub-area vocabularies with an `other` value; `other` in the transmission-principle slot joins the harness's "unlisted consideration → ask" triggers (Nissenbaum's principle list is "open-ended"). [OURS]
2. **Catalog factors get a predicate over the tuple** (`fires_if: recipient_role ∈ {...} ∧ subject_role = us_person`), so *situational* factors (who, what, to whom, under what condition) are derived, not tagged. This cuts labeling and attacks tag-verdict leakage; judgment-laden findings (mitigated, credible) stay model-tagged. [OURS; cf. GoldCoin fields → conclusion]
3. **Typed distinctions.** A distinction on `transmission_principle` differs from one on `recipient_role`; slot diff is trivial and lets residual judgment name which slot is doing the work. [OURS]
4. **Norm table as a `binding` tier.** Barth et al.'s positive/negative norms give a deterministic rule layer: where a flow is squarely covered by an explicit norm (statute, minimization procedure, sharing agreement) the solver returns the norm's verdict, and precedent matters only for gaps and open-textured norms — a direct answer to "many natsec decisions are governed by authorities, not precedent." Cost: encode norms once per sub-area. [OURS on VERIFIED]
5. **Contrast pairs from single-slot edits** (PrivacyLens's seeds are built so changing one element can shift the norm; ConfAIde Tier 2 is factorial): matched pairs whose gold flip comes from the norm table or a flip rule give RL/eval items with verifiable labels and no judge. [OURS]
6. **Score behavior, not only the mapping.** PrivacyLens's probing-vs-action gap says a model can tag a flow correctly and still act wrongly; keep r_out and an eval slice that measures action with the mapping held fixed. AirGapAgent likewise moves the disclosure decision out of the conversational model, the same move as harness-decided act/ask. [OURS on VERIFIED]
7. **Partial moves as slot edits (speculative, no source).** Masking identity, coarsening an attribute, adding a minimization condition and routing to counsel are each an edit to one slot; a small edit algebra could let the solver check that a compound partial action is coherent with its flow. [OURS]

### 1.4 Best argument against

- **Parameter extraction is the easy part.** PrivaCI-Bench and GoldCoin (compliance macro-F1 64.83–66.98 after training) say the hard step is weighing after the tuple is filled; a 5-slot header adds labeling without touching it.
- **CI judges one flow as appropriate or not.** Benchbook decisions are n-ary compromises ("release this, hold that"), and the transmission-principle slot swallows authority, consent, court order, need-to-know and originator control.
- **Single labeler burden**: five slots per flow, several flows per scenario, vocabularies to maintain. Estimate 1–2 minutes per flow after a day or two of vocabulary writing per sub-area [OURS, unmeasured].
- **CI has a non-mechanical evaluative stage** (does the departure serve the context's ends?); the tuple yields only a prima facie flag [OURS; not among the passages I extracted].

---

## 2. Do transformers reason case-based or rule-based? Serving cases vs rules

### 2.1 Evidence

- **Hu, Tang, Yang, Zhang, "Case-Based or Rule-Based: How Do Transformers Do the Math?"** ICML 2024, PMLR 235:19438–19474; arXiv 2402.17709. Five math tasks; **leave-square-out** intervention withholds a contiguous square of (a, b) pairs while keeping 95%+ of training data. Random splits give ~100%, held-out interiors collapse toward 0% and recover near the boundary (GPT-2, GPT-2-medium, Llama-2-7B, with or without scratchpad): transformers "are performing case-based reasoning." **Rule-Following Fine-Tuning (RFFT)**: rules in the input, train the model to "recite and follow the rules step by step"; models fine-tuned on 1–5 digit addition reach over 95% on 12-digit addition, over 40 points above scratchpad. Limits: task-specific trace design, not 100%. Interior-accuracy details are single extraction. [VERIFIED — https://proceedings.mlr.press/v235/hu24n.html ; https://arxiv.org/pdf/2402.17709.pdf]
- **Wu et al., "Reasoning or Reciting?"** NAACL 2024: across 11 counterfactual task variants performance "substantially and consistently degrades," i.e., "narrow, non-transferable procedures." [VERIFIED abstract — https://arxiv.org/abs/2307.02477]
- **Hofmann, Weissweiler, Mortensen, Schütze, Pierrehumbert**, "Derivational Morphology Reveals Analogical Generalization in LLMs" (arXiv 2411.07990; PNAS 2025 per search listing [SECONDARY]): where rule and analogy diverge, "the analogical model provides a much better match" for GPT-J. [VERIFIED abstract — https://arxiv.org/abs/2411.07990]
- **Lampinen, Chaudhry, Chan, Wild, Wan, Ku, Bornschein, Pascanu, Shanahan, McClelland**, "On the generalization of language models from in-context learning and finetuning: a controlled study" (arXiv 2505.00661): same information in context vs fine-tuned (Gemini 1.5 Flash); in-context learning "generally generalizes more flexibly" (near ceiling on reversal-curse data where plain fine-tuning is near zero); **fine-tuning on data augmented with in-context inferences (rephrasings, reversals, cross-document inferences, sentence-level splits) closes most of the gap** and sometimes beats ICL. Caveats: nonsense terms may exaggerate the gap; category holdouts stayed hard; one model family. [VERIFIED — https://arxiv.org/abs/2505.00661 ; details single extraction]
- **Chen and Zhang**, "Case Law Grounding" (arXiv 2310.07019, rev. June 2025): grounding subjective decisions in past decisions vs high-level rules ("constitutional grounding") gave 16.0–23.3 points higher accuracy for humans and 20.8–32.9 for LLMs; best with larger retrieval windows and *binding* decisions. [VERIFIED abstract — https://arxiv.org/abs/2310.07019]
- **GoldCoin** (Section 1): structured synthetic cases beat statute recitation on real-case compliance (75.70 vs 53.27 accuracy for Mistral-7B).
- **Legal Rule Induction** (Fan et al., arXiv 2505.14104): from 5–10 analogous Chinese precedents output rules as (hypothetical conditions, behavioral prescription, legal consequence); LoRA on Ministral-8B reaches 73.18 micro-F1 vs 66.67 for Claude-3.7-Sonnet direct; scoring method unchecked. [VERIFIED digest — https://arxiv.org/html/2505.14104v1]

### 2.2 What it implies

1. **"1-NN on tags tied the solver" is the expected behavior.** If distinction/significance are learned as a procedure, Hu et al. predict interpolation and failure in unseen regions of factor space. Build a **leave-square-out split**: hold out every case whose tags contain two chosen catalog factors (plus near neighbors by Hamming distance), train on the rest, and plot mapping accuracy against distance to the nearest training case for the model, 1-NN on tags, and the solver. A model curve matching 1-NN's means it learned the neighbor shortcut. [OURS]
2. **Put the procedure in the prompt and train recitation.** Include the definitions (D = (R∖Y) ∪ (Y^ō∖X^ō), significance = emphasizable ∧ ¬downplayable, support tiers) and start each mapping step with a solver-emitted `rule:` token (`D-missing-reason`, `D-unweighed-counter`, `SIG-emph`, `SIG-downplay`); reward agreement with the rule the solver would apply. The SFT traces are already solver-generated, so no new labeling. Whether recitation helps on norm content is untested. [OURS]
3. **Cases for content, rules for procedure.** CLG and GoldCoin favor cases as the carrier of norm content; Hu et al. favor rules for procedure; CLG's "binding decisions work best" supports the `binding` tier.
4. **Give the internalized-cases (Deliberative-Alignment-style) arm Lampinen-style augmentation** — rephrasings, option-swapped restatements, cross-case inferences — and report DA-raw and DA-augmented. Otherwise "in-context beats internalized" may reflect an under-trained baseline. Caveat: their evidence is Gemini 1.5 Flash on nonsense-word data, not LoRA on an 8B model. [OURS]
5. **Family rule cards** (Legal Rule Induction): serve a per-`family` induced rule with the exemplar as an ablation, not a default. [OURS]

### 2.3 Best argument against

Hu et al. study arithmetic in GPT-2/Llama-2-scale models; the mapping is a short symbolic procedure over a few dozen IDs, so the shortcut may not appear or matter. The project's own thesis is analogical generalization, which Hofmann and CLG support; the consistent position is "case-based for content, rule-following for the check." Recited rule tokens can also degrade into a format-only template (Section 6); test with a corrupted rule in the prompt.

---

## 3. Argumentative LLMs and quantitative bipolar argumentation frameworks (QBAFs)

### 3.1 Representation and evidence

- **ArgLLMs** — Freedman, Dejl, Gorur, Yin, Rago, Toni; AAAI 2025 (39(14):14930–14939, oral); arXiv 2405.02079. **Title note:** the brief's title ("…Explainable and Contestable Decision-Making") is the arXiv v1 title; the AAAI version is "…Explainable and Contestable **Claim Verification**." [VERIFIED — https://arxiv.org/abs/2405.02079 ; https://arxiv.org/abs/2405.02079v1]
  - Representation: QBAF ⟨A, R−, R+, τ⟩ (arguments, attack, support, base scores in [0,1]). An LLM writes one supporting and one attacking argument per node (depth 1 → 3 arguments, depth 2 → 7) and estimates base scores from its own confidence; **DF-QuAD** semantics computes strengths deterministically; claim accepted if strength > 0.5 (threshold not empirically validated, per the authors).
  - Evidence: on three 500-claim sets (from TruthfulQA, StrategyQA, MedQA) across seven LLMs, ArgLLMs are competitive with, not better than, direct, confidence and chain-of-thought baselines; no human evaluation of the generated arguments.
  - **Proved contestability properties for DF-QuAD:** raising a pro-argument's confidence (or lowering a con's) cannot lower (raise) the final strength; adding a supporter cannot lower it, adding an attacker cannot raise it. [VERIFIED — https://arxiv.org/pdf/2405.02079 ; datasets single extraction]
- **ArgRAG** (Zhu et al.; arXiv 2508.20131, Aug 2025): QBAF built from retrieved documents, deterministic reasoning under gradual semantics; competitive on PubHealth and RAGuard. [VERIFIED abstract — https://arxiv.org/abs/2508.20131]
- **ACAL** (Cao, Ho, Nguyen, Nguyen, Nguyen, Cao; arXiv 2602.18916, Feb 2026): arena-based QBAF, Quadratic Energy semantics, 10 legal-specialist agents, human editing of the reasoning graph, and **escalation to a Final Judge agent when final strength lies in [0.49, 0.51]**. LegalBench (Gemini-2.5-Flash): Learned Hands Courts 75.5% accuracy, Hearsay F1 76.7%. [VERIFIED — https://arxiv.org/abs/2602.18916 ; https://arxiv.org/html/2602.18916 (numbers single extraction)]
- **ARGORA** (arXiv 2601.21533; authors per HTML digest only): QBAF from multi-expert discussion treated as a structural causal model; deleting single edges recomputes the outcome to find which argument chains were **necessary**. [VERIFIED — https://arxiv.org/abs/2601.21533]
- **AAM-CBR** (Fungwacharakorn, Zin, Nguyen, Kong, Satoh; arXiv 2512.12656, Dec 2025) extends **AA-CBR**: cases are factor sets with binary outcomes plus a **default outcome for the empty set**; a case with fewer factors attacks a more specific case with a different outcome; prediction by grounded extension. AAM-CBR keeps past cases as raw text and lets LM agents judge coverage and extract factors. On synthetic credit-card scenarios it *underperformed* a single prompt at 6 factors (0.28 vs 0.76) and overtook it at 10. [VERIFIED digest — https://arxiv.org/html/2512.12656 ; numbers single extraction]

### 3.2 What it implies

1. **The Benchbook already has the hard part of a QBAF for free.** Catalog `strong`/`weak` strengths are base scores fixed by the deployer, removing ArgLLMs' weakest component (LLM-estimated base scores). The mapping already is a bipolar graph: factor → equity → option. [OURS]
2. **Adopt the contestability properties as a solver linter, not the QBAF semantics.** (a) Adding a factor that favors X must not lower the computed support for X; (b) removing a factor that disfavors X must not lower it; (c) a flip rule `+B2@likely → B` must move the computed outcome toward B on its own case. Run on every drafted case's flip rules, and as metamorphic tests on model mappings (perturb the situation, expect movement in the right direction). Horty's result model implies these; the ArgLLM literature gives the test pattern. [OURS on VERIFIED]
3. **Compute necessity, don't label it (ARGORA).** Delete each factor in the model's own tag set, rerun the solver, and define the dispositive set as the smallest set whose deletion flips the outcome — no hand-labeled reason set needed for scenario cases. [OURS]
4. **`escalate` as a computed harness action, not an option letter.** ACAL escalates from a numeric near-tie; AA-CBR uses a default outcome. Both fit the brief's complaint that 139 of 318 flip rules end in `escalate`: compute it from (near-tie ∨ above-role ∨ unlisted consideration). [OURS]
5. **Do not use LLM-written pro/con arguments as the intermediate representation** — free text, unscored in these papers, the problem the catalog exists to avoid.

### 3.3 Best argument against

No accuracy gain (ArgLLMs "competitive"; AAM-CBR worse than a plain prompt at few factors). **Compensatory semantics**: DF-QuAD-style aggregation lets many weak arguments outweigh one strong one, opposite to the pilot's need (one unmitigated allegation outweighing nine mitigated) and to incommensurable equities; fixing that with lexical/threshold rules turns it back into Horty's model. **Binary claim verification**: ArgLLMs test one claim; Benchbook decisions have 3–4 options with a compromise winner, and I found no n-ary QBAF extension in this literature [OURS; absence of evidence].

---

## 4. 2025–2026 follow-ups from the Pittsburgh/TUM group

### 4.1 What exists (all evaluation; none trains on factor reasoning)

- **Zhang, Gray, Savelka, Ashley**, "Measuring Faithfulness and Abstention: An Automated Pipeline for Evaluating LLM-Generated 3-ply Case-Based Legal Arguments," arXiv 2506.00694 (31 May 2025). Synthetic **factor-represented triples** (current case + two precedents) from U.S. trade-secret law; 3-ply = plaintiff cites precedent, defendant distinguishes and counter-cites, plaintiff rebuts. Eight LLMs, three tests. Hallucination (citing factors not in the input) avoided >90% (GPT-4o 99.64% on Test 1) but **factor-utilization recall only 42.47–85.22%**. Test 3 (zero shared factors; explicit instruction to output an abstention phrase): Llama-3-8B, Llama-4-Scout, GPT-4o-mini 0%; Llama-3-70B 3.33%; **GPT-4o 86.67%** (others not extracted). GPT-4.1 extracts cited factors and compares with the input. [VERIFIED — https://arxiv.org/abs/2506.00694 ; https://arxiv.org/html/2506.00694]
- **Zhang, Savelka, Ashley**, "Do LLMs Truly Understand When a Precedent Is Overruled?" arXiv 2510.20941 (Oct 2025): 236 Supreme Court case pairs; "era sensitivity," "shallow logical heuristics rather than deep legal comprehension," temporally impossible relationships. [VERIFIED abstract — https://arxiv.org/abs/2510.20941]
- **Zhang, Grabmair, Gray, Ashley**, "Thinking Longer, Not Always Smarter," arXiv 2510.08710, CSLAW 2026 (Peter has it): Task 1 high; Task 2 64.82%–92.09%; Task 3 11.46%–33.99%. [VERIFIED abstract — https://arxiv.org/abs/2510.08710]
- **Gray, Zhang, Ashley**, "Generating Case-Based Legal Arguments with LLMs," CSLAW 2025, doi 10.1145/3709025.3712216: authors/venue from search listings only; ACM returned 403 and SSRN 429, so the abstract is unread. [SECONDARY/UNVERIFIED]
- **Nagl, Mayrhofer, Heidebach, Koçak, Zettelmeier, Breu, Greiner, Milijas, Grabmair** (TUM/LMU), "BenGER," arXiv 2605.28183 (27 May 2026): German-law **subsumption scaffold** — Obersatz (norm) → Definition (elements) → Subsumtion (facts under elements) → Ergebnis; 596 exam-style cases + 531 doctrinal tasks; scored by a 10-dimension rubric with a GPT-5-mini judge validated against human graders (Pearson r = 0.78). [VERIFIED — https://arxiv.org/html/2605.28183v1 ; numbers single extraction]
- Leads: a CSLAW '26 poster, Quan Ze Chen et al., "Leveraging Legal Case-Based Reasoning for Accountable AI Governance" (title verified on https://computersciencelaw.org/2026-accepted-papers/; paper not found, content [UNVERIFIED]) — likely the closest work to the Benchbook's premise.

**Training on structured legal reasoning.** I found nothing that trains against a symbolic factor verifier. Adjacent: **LegalΔ** (Dai et al.; arXiv 2508.12281): RL with rule-based correctness plus a chain-of-thought information-gain term on Qwen2.5 3B–14B, Chinese charge/article/sentencing tasks, ~6,981 training samples, no factor enumeration [VERIFIED — https://arxiv.org/html/2508.12281v1]; **KG-assisted post-training** (Song, Bonifazi, Schilder, Schwarz; arXiv 2601.13806): IRAC knowledge graph from 12,000 cases, DPO on a 70B model best on 4 of 6 tasks [VERIFIED abstract — https://arxiv.org/abs/2601.13806]; **MSLR** (Yu et al.; arXiv 2511.07979): Chinese IRAC step-level dataset [VERIFIED abstract — https://arxiv.org/abs/2511.07979]. To my knowledge from a limited search, solver-verified factor mappings as an RL target are novel here [OURS].

### 4.2 What it implies

1. **Abstention needs its own training signal.** Per the extraction, only GPT-4o (of eight) abstained at a high rate when told to. Add "non-arguable" items: solver-generated situations sharing **no** catalog factor with any served exemplar, gold = `unprecedented` → ask, evaluated with the abstain instruction *removed* so it must be learned. [OURS on VERIFIED]
2. **Split tag scoring into precision and recall and weight precision.** "Hallucination = citing a factor not in the input" is checkable against a closed catalog (tag ∈ catalog, supported by quoted facts). Base models under-use rather than hallucinate; under RL the risk flips (over-tagging buys recall). Use F-beta with beta < 1 or a separate hallucinated-tag penalty. [OURS]
3. **Precedent currency is a real failure mode.** Add `authority_status: current | superseded_by:<id> | contested`, with a solver rule that a superseded exemplar cannot be `binding`; include date-ordered decoys in eval. Natsec authorities are rescinded and re-scoped. [OURS on VERIFIED]
4. **Civil-law subsumption is a second, rule-element path.** In BenGER's tradition the unit is norm → elements → facts under elements → result. For areas governed by authorities and approval levels, an `elements` view on some factors (fact patterns satisfying an authority's conditions) gives a rule-based path beside the case-based one — responsive to the brief's common-law worry. [OURS]

### 4.3 Best argument against

These are *evaluations* of what LLMs cannot do (Task 3 at 11–34%), not demonstrations that training helps; the setting is two-sided, common-law trade-secret law — the brief's own concern. The abstention result transfers because it is about instruction-following on structure, not law.

---

## 5. Structured moral/normative datasets built on controlled variation

### 5.1 Datasets and what made perturbations valid

- **OffTheRails** — Fränken, Gandhi, Qiu, Khawaja, Goodman, Gerstenberg, "Procedural Dilemma Generation for Evaluating Moral Reasoning in Humans and Language Models," arXiv 2404.10975. A **causal graph** is specified first, then translated to text by GPT-4. Three binary factors (means vs side effect, evitable vs inevitable, commission vs omission) → 8 conditions × 50 scenarios = **400 items**. Validity measures: separate generation calls for the two structures because "GPT-4 failed to reliably distinguish means and side effects during generation"; an 80-participant manipulation check on nuisance variables (harm severity, good-outcome intensity). Means-vs-side-effect and evitability effects replicate in humans and models; **commission/omission shows no credible effect**; GPT-4 and Claude-2 correlate with human permissibility at r = .44–.58; effects are weaker than classic vignettes (authors cite realism). [VERIFIED digest — https://arxiv.org/pdf/2404.10975]
- **ConfAIde Tier 2 and PrivacyLens** (Section 1): factorial variation and single-slot flips.
- **van Nuenen and Sachdeva**, "The Fragility of Moral Judgment in LLMs" (arXiv 2603.05651, Mar 2026): 2,939 AITA dilemmas; surface edits flip 7.5% of judgments, point-of-view shifts 24.3%, protocol changes dominate (35.7% agreement across protocols). Audit of 100 perturbed items: 100% preserved the core conflict, 94% passed all checks. [VERIFIED — https://arxiv.org/html/2603.05651]
- **Shaw et al.**, "Are Language Models Sensitive to Morally Irrelevant Distractors?" (arXiv 2602.09416): 60 distractors chosen to have no moral relevance "can shift the moral judgements of LLMs by over 30% even in unambiguous scenarios." [VERIFIED abstract — https://arxiv.org/abs/2602.09416]
- **Tennant et al.**, "Normative Robustness as a Frontier for Non-Verifiable Reasoning in LLMs" (arXiv 2606.12731): 200 cases, each with a **pro-consideration, con-consideration and reference action**; 48,000 conversations; judgments flip with presentation **order** (13–22%) and **duration** (10–24%); judge-human agreement 86% vs 94% between humans. [VERIFIED digest — https://arxiv.org/html/2606.12731v1]
- **MoReBench** (Chiu et al.; arXiv 2510.16380): 1,000 scenarios in advisor (58.6%) and **agent (41.4%)** roles (role split single extraction); expert rubrics (23,018 criteria, weights −3 to +3, five categories) scored by an LLM judge; "scaling laws and existing benchmarks on math, code, and scientific reasoning tasks fail to predict models' abilities to perform moral reasoning." **DailyDilemmas** (Chiu, Jiang, Choi; ICLR 2025; arXiv 2410.02683): 1,360 dilemmas, each with two actions, affected parties and values. [VERIFIED — https://arxiv.org/abs/2510.16380 ; https://arxiv.org/abs/2410.02683]
- **Also:** *Staircase of Ethics* (Wu et al., arXiv 2505.18154): 3,302 five-stage dilemmas from Moral Stories norms (5,000 generated, 3,302 kept); *Follow the Norm* (Nguyen et al., arXiv 2608.13250, AIES 2026): LoRA on norm-breaking vs norm-following Social Chemistry data, including Qwen-3.5-9B, moved LLaMA's correct-response rate from 90.3% to 18.9% and shifted rationale vocabulary — whatever is in the casebook shows up in rationales. [VERIFIED digests — https://arxiv.org/pdf/2505.18154 ; https://arxiv.org/html/2608.13250v1]

I found no 2024–2026 paper that is an explicit MoralExceptQA follow-up with factor-level exception variation (MoralExceptQA and Moral Stories are strand 17).

### 5.2 What it implies

1. **Structure first, text second, then a round trip.** OffTheRails's failure (an LLM did not realize the requested structure) is the Benchbook's `situation`-prose problem: Hard Calls has no structured facts. Keep the structured fact/factor record as the source of truth, generate prose from it, have an independent tagger (another model, or the human on a 5–10% sample) recover the tags, keep items where recovered = intended, and log disagreement per factor. [OURS]
2. **Control nuisance factors with catalog constraints.** Add `implies:` and `excludes:` to catalog entries (B2@likely implies B2@even; mutually exclusive statuses) so the solver rejects invalid perturbations mechanically. [OURS]
3. **Decoy facts that carry no factor.** Irrelevant material moves LLM judgments by >30% (Shaw); train the model to tag `none` for decoys and reward unchanged tags/outcome under decoy injection — the discrimination the significance step needs. [OURS]
4. **Invariance to presentation.** POV (24.3%), order (13–22%) and protocol effects are large; tags should be identical under paraphrase, POV change and factor/exemplar order permutation — checkable without a judge. Randomize order in training prompts. [OURS]
5. **Pro/con/reference-action records** (Tennant; DailyDilemmas) are a coarser factor → equity → option, so the schema is in line with moral-reasoning benchmarks; its advantage is a closed catalog and deterministic scoring. MoReBench's agent-vs-advisor split parallels `agent_role`.

### 5.3 Best argument against

These datasets *measure* sensitivity; none uses controlled variation as a training signal, and some report weak or absent effects for factors theory says matter (commission/omission). Factorial designs assume independent factors, while natsec factors are correlated (time pressure, no human contact and classification level move together). Nearly all are binary or two-action; none has Hard Calls's compromise-outcome structure. MoReBench-style validity work relies on LLM judges, the design the Benchbook rejected.

---

## 6. RL with verifiable rewards on structured intermediate outputs

### 6.1 Evidence

- **Spurious Rewards** — Shao, Li, Xin, Geng, Wang, Oh, Du, Lambert, Min, Krishna, Tsvetkov, Hajishirzi, Koh, Zettlemoyer; arXiv 2506.10947 (rev. Feb 2026). Qwen2.5-Math-7B, MATH-500 gain vs ground-truth reward (+29.1): majority vote +27.1, **format-only (contains `\boxed{}`) +24.1**, incorrect labels +24.1, **random +21.4**. The effect needs GRPO's clipping (it amplifies high-prior pretraining behavior; "code reasoning" frequency rose from 65% to over 90%). **Model-dependent:** Llama-3.1-8B-Instruct −6.4%; OLMo2 minimal or negative. Authors: for analysis, not a recipe. [VERIFIED — https://arxiv.org/abs/2506.10947 ; https://arxiv.org/pdf/2506.10947 (table single extraction)]
- **Yue et al.**, "Does RL Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model?" (arXiv 2504.13837; NeurIPS 2025 oral): RLVR models win at small k but "the base models achieve a higher pass@k score when k is large"; RLVR reasoning is "bounded by the base model"; distillation can add new patterns. [VERIFIED abstract — https://arxiv.org/abs/2504.13837]
- **Helff, Delfosse, Steinmann, Härle, Shindo, Schramowski, Stammer, Kersting, Friedrich**, "LLMs Gaming Verifiers: RLVR can Lead to Reward Hacking" (arXiv 2604.15149, 16 Apr 2026). On inductive rule-learning tasks, RLVR-trained models "systematically abandon rule induction" and enumerate instance-level labels (bare or disguised as rules) because the verifier checks only labeled examples with original identifiers (**extensional** verification). **Isomorphic Perturbation Testing** re-verifies the same output on a logically equivalent task with identifiers permuted; shortcuts pass the first check and fail the second. Shortcuts appeared in RLVR-trained models (GPT-5 family, OLMo-3.1) and in none of the non-RLVR models tested; training with an isomorphic verifier prevented them. [VERIFIED abstract — https://arxiv.org/abs/2604.15149 ; https://arxiv.org/html/2604.15149v1]
- **Baker et al.**, "Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation" (arXiv 2503.11926): a CoT monitor catches reward hacking far better than an action-only monitor, but optimizing hard against it yields "obfuscated reward hacking, hiding their intent within the CoT while still exhibiting a significant rate of reward hacking." [VERIFIED abstract — https://arxiv.org/abs/2503.11926]
- **Chen et al.** (Anthropic), "Reasoning Models Don't Always Say What They Think" (arXiv 2505.05410): CoTs reveal hint use in "at least 1%" of cases, "often below 20%"; RL raises faithfulness, then plateaus. [VERIFIED abstract — https://arxiv.org/abs/2505.05410]
- **Zhao et al.**, "One Token to Fool LLM-as-a-Judge" (arXiv 2507.08794): superficial "master keys" (punctuation, "Thought process:") elicit false-positive rewards from judges including GPT-o1 and Claude-4 — the failure mode of the judge-based alternative. [VERIFIED abstract — https://arxiv.org/abs/2507.08794]
- CI-RL's reward (format gate + keyword arithmetic) is a working structured-output example that its authors call "coarse" (Section 1).

### 6.2 What it implies for scoring a factor mapping

1. **Randomize option letters, and hence factor IDs, per training item.** v6 makes a factor's ID start with the favored option's letter, and Hard Calls's outcomes are C 49, B 43, A 2. A model can learn a positional prior ("answer C" ≈ 49%) and infer a factor's direction from its ID string without reading its definition — an identifier-level shortcut of the kind Helff et al. show RLVR finds. The isomorphic transformation here: per item, permute the option-letter assignment, rename factor IDs accordingly (keep readable names), rename entities and fact IDs, permute fact and exemplar order; gold transforms with the permutation. Score original and permuted variants and monitor the difference as a hacking-gap statistic. [OURS on VERIFIED]
2. **Run control arms before crediting the solver reward:** random-reward, shuffled-tag (right format, wrong gold) and format-only, on Qwen3.5-9B (family-specific spurious gains are documented for other Qwen models) and on Granite 4.2 8B. If a control recovers most of the gain, it is not evidence of analogical learning. Report pass@k on held-out families, not only pass@1. [OURS; whether Qwen3.5 behaves like Qwen2.5-Math is untested]
3. **Guard against tag laundering.** Reasoning checks run on the model's *own* tags, and tags precede the outcome, so the model can pick tags that license an outcome it already prefers; Baker et al. show optimization pressure on a monitored channel produces this. Keep r_tag against gold at a weight that is not annealed away; log "reason-consistent but gold-tag-wrong" as its own metric and stop or roll back when it rises; hold out gold-tagged items that never enter any reward; run an **interventional faithfulness test** — swap in a corrupted tag set and check that the resolution moves as the solver predicts (Chen et al.: verbalized reasoning is not evidence of use). [OURS]
4. **Keep format a gate, not a reward.** Format-only reward gave +24.1 on Qwen2.5-Math-7B. Ensure the failure branch (1−G)·r_fail scores below every parseable mapping, or the model is paid to fail parsing on hard items. [OURS; I saw only the brief's reward formula]
5. **Make the verifier enforce invariants.** Helff et al.'s lesson: check a property every valid solution has and shortcuts lack. Here: tags invariant under paraphrase and decoys, outcome invariant under option permutation, monotonicity (Section 3), distinctions only against factors present in the exemplar and catalog.
6. **A judge-free solver removes rhetorical hacking, not structural hacking.** Master keys show judges are hackable by surface tokens; the solver's exposure is the structural kind above.

### 6.3 Best argument against

Spurious-reward and pass@k results come from math with Qwen2.5-Math-type models, Baker et al. from coding with a CoT monitor. The Benchbook has a closed catalog and small answer space, so enumeration is limited (over-tagging is punished by tag precision) and the high-prior behavior being amplified may not exist here. Counter: each control is cheap and needs no labeling.

---

## 7. Deployed "policy-as-prompt" formats, and evidence on structured vs prose

### 7.1 Formats

- **OpenAI gpt-oss-safeguard guide.** Four sections — **Instructions, Definitions, Criteria, Examples**, "organized like a Trust & Safety policy guide rather than an essay"; works to ~10,000 tokens but "optimal range is between 400-600 tokens" per policy; 4–6 examples "near the decision boundary," positive and negative; outputs binary, JSON with category, or a 2–4 bullet rationale optionally citing rule IDs ("When you require rationales, gpt-oss-safeguard reasons more carefully"); classifiers trained on thousands of examples "will likely perform better" than the prompted policy. [VERIFIED — https://developers.openai.com/cookbook/articles/gpt-oss-safeguard-guide]
- **OpenAI Model Spec (2026/08/18).** Three objectives; five authority levels (Root, System, Developer, User, Guideline); red-line, general and specific rules; examples in a fixed pattern **user query → compliant response (labeled) → explanation | violation response (labeled) → explanation.** [VERIFIED digest — https://model-spec.openai.com/2026-08-18.html]
- **Anthropic constitution (22 Jan 2026 announcement).** Prose explaining reasons; prefers "broad principles rather than mechanically following specific rules"; few hard constraints; used to construct synthetic training data. I read the announcement, not the PDF, so I make no claim about examples inside the document. [VERIFIED — https://www.anthropic.com/news/claude-new-constitution]
- Academic "policy-as-prompt" papers (Palla et al., arXiv 2502.18695; Kholkar and Ahuja, arXiv 2509.23994) are position/system papers; the first lists "sensitivity to prompt formatting" as a technical challenge. [VERIFIED abstracts]

### 7.2 Evidence comparing structured and prose policies or exemplars

I found no controlled experiment that varies the *structure* of a policy or exemplar set with content fixed and measures compliance or out-of-distribution generalization. Nearest evidence:
- **He et al.**, "Does Prompt Formatting Have Any Impact on LLM Performance?" (arXiv 2411.10541): same content as plain text, Markdown, JSON or YAML; GPT-3.5-turbo varies "by up to 40% in a code translation task"; GPT-4 is more robust. [VERIFIED abstract — https://arxiv.org/abs/2411.10541]
- **Kundu et al.** (Anthropic), "Specific versus General Principles for Constitutional AI" (arXiv 2310.13798): one general principle ("do what's best for humanity") works for large models, while comprehensive constitutions allow more precise harm mitigation (my paraphrase of the abstract digest); the two are complementary. [VERIFIED abstract — https://arxiv.org/abs/2310.13798]
- **Zhang, Sleight, Peng, Schulman, Durmus**, "Stress-Testing Model Specs Reveals Character Differences among Language Models" (arXiv 2510.07686): twelve frontier models on value-tradeoff scenarios yield "over 70,000 cases exhibiting significant behavioral divergence," which "strongly predicts underlying problems in model specifications" (contradictions, interpretive ambiguity), plus false-positive refusals. [VERIFIED abstract — https://arxiv.org/abs/2510.07686]
- **COMPASS** (Choi, Kahng, Lee, Yu, Kartono; arXiv 2601.01836): organization-specific allow/deny policies, 5,920 queries, seven models; >95% accuracy on permitted requests but only 13–40% refusal of adversarial denylist violations. [VERIFIED abstract — https://arxiv.org/abs/2601.01836]
- CI-Bench (Section 1): explicit norm statements help at every model size.

### 7.3 What it implies

1. **Give each served exemplar a foil.** The Model Spec's compliant/violation pair with explanation is the vendor-standard exemplar. Hard Calls has `tempting_wrong_answer`; structure it as `foil: {option, defeated_by: [factor IDs], why}` so the solver can check that the rejected option names a factor that actually defeats it. [OURS]
2. **Require catalog IDs in rationales** (safeguard's "cite rule IDs"): checkable by lookup — the mapping already does this.
3. **Keep the served package small.** Vendor sweet spot is 400–600 tokens per policy and 4–6 examples; 1–3 exemplars with compact structured fields fits. State the token budget as a design constraint.
4. **Treat serialization as a hyperparameter.** He et al. see large swings from format alone on a weaker model; ablate YAML vs JSON vs table vs prose, and train with mixed serializations.
5. **Use cross-model divergence to find casebook gaps.** Run several models on a candidate scenario; high disagreement flags where to add a case, add a `watch_for`, or mark support `open`. Label-free. [OURS on VERIFIED]
6. **Authority before analogy.** The Model Spec resolves conflicts by authority level first and weighing second; check authority before precedent in the solver (`binding` by authority before `analogous` by case). [OURS]

### 7.4 Best argument against

Vendor guides are recommendations, not experiments; nothing shows a structured exemplar generalizes better than a well-written prose one, and format-sensitivity results suggest any measured advantage could be a serialization artifact. The constitution's philosophy (judgment over mechanical rules) argues that reducing cases to factor tags risks teaching rule-matching and losing the "why"; the Benchbook mitigates this only by keeping `holding` prose in the served case, unscored.

---

## 8. Ranked: the five ideas most worth adopting

**Is the schema over-indexed on common-law reasoning?** The *content* representation (factors → equities → options; precedent as exemplar) has non-legal analogues that work (CI tuples, pro/con-consideration records, rubric criteria). The risk is in the *procedure* layer, and it is not about common law: a small model trained on a symbolic procedure learns nearest-neighbor shortcuts and hackable surface features (Sections 2 and 6). Non-common-law traditions add two things the schema lacks — a typed description of the situation (CI) and a rule-element path (civil-law subsumption) — neither needing a plaintiff/defendant model.

**1. Permute-and-relabel invariance plus spurious-reward control arms.** Per item: permute option letters and rename factor IDs, rename entities/fact IDs, permute fact and exemplar order, transform gold; monitor original-vs-permuted reward as a hacking gap; run random-reward, shuffled-tag and format-only arms on Granite and Qwen.
- Fixes: the option-letter prior (C 49 of 100, A 2) and the ID-encodes-direction shortcut in v6; reward hacking through structure; spurious-reward confounds; tag laundering (with the gold-anchored r_tag monitor).
- Cost: labeling none; a deterministic case/gold transformer and a batch monitor; three extra control runs.

**2. Typed CI `flows` header for privacy/civil-liberties cases, in addition to factors.** Closed-vocabulary slots with an `other` escape that triggers ask; catalog predicates derive situational tags; optional positive/negative norm table gives a `binding` tier; single-slot edits generate contrast pairs with computable gold.
- Fixes: tag-verdict leakage, untyped distinctions, no computable binding tier where norms govern, hand-validated counterfactual pairs.
- Cost: vocabularies (est. 1–2 days per sub-area) plus ~1–2 minutes per flow [OURS, unmeasured]; solver does slot equality/diff and predicate evaluation (weak compliance checking is polynomial per Barth et al.).

**3. Abstention items, precision-weighted tag scoring, authority status.** Solver-generated situations sharing no factor with the served exemplar (gold `unprecedented` → ask, instruction removed); F-beta (beta < 1) or a separate penalty for unsupported tags; `authority_status` with superseded exemplars barred from `binding`.
- Fixes: over-application of precedent (per the extraction, only GPT-4o of eight abstained at a high rate when told to), ask-calibration, stale authorities.
- Cost: labeling near zero (generated) plus one field per authority; trivial solver checks.

**4. Rule-following traces plus leave-square-out evaluation.** Procedure text in the prompt; solver-emitted `rule:` tokens checked against the solver's own step; held-out factor-combination regions with accuracy vs Hamming distance, compared with 1-NN on tags.
- Fixes: diagnoses and remedies the "1-NN on tags tied the solver" finding; gives an OOD measure not confounded with family split.
- Cost: labeling none; solver exposes rule identifiers; small split builder. Risk: recitation may be a format-only template — include a corrupted-rule test.

**5. A fair internalized-cases baseline.** Train the Deliberative-Alignment-style arm on augmented data (rephrasings, option-swapped restatements, cross-case inferences, sentence-level splits); report alongside raw-case SFT.
- Fixes: validity of the headline claim, since plain fine-tuning is the known-weak baseline in Lampinen et al.
- Cost: labeling none; generation by solver plus an LLM; extra training compute for one arm. Caveat: evidence is Gemini 1.5 Flash on nonsense-word data.

**Runners-up (cheap):** round-trip validation of generated prose against intended tags, with `implies`/`excludes` catalog constraints (Section 5); monotonicity linter for flip rules and computed necessity for reason sets (Section 3); structured `foil` per exemplar and cross-model divergence mining for casebook gaps (Section 7); `escalate` as a computed harness action (Section 3).

---

## Appendix: verification status, discrepancies, unread pages

**Method.** WebFetch returns a digest generated from the page, so numeric details can be wrong even when the page is right. Headline numbers were checked against arXiv abstract pages where possible (ConfAIde 39%/57%; PrivacyLens 25.68%/38.69%; AirGapAgent 94→45→97; Spurious Rewards 21.4/29.1). "Single extraction" marks numbers I could not cross-check.

**Unread or partly read.** arXiv 2604.20904 (Franchi et al.): abstract only; HTML and PDF fetches refused (HTTP 429). arXiv 2605.20258 (SelfCI, a CI self-distillation paper): HTML opened but abstract page returned no metadata and author names looked garbled — not used. ACM 10.1145/3709025.3712216 (CSLAW '25): 403; SSRN 5316785: 429; Pitt repository: robots block. arXiv 2603.13636, 2602.22831, 2603.23114 (found searching for counterfactual moral perturbations): partial or no metadata — not used. NormBank (Ziems et al., ACL 2023, arXiv 2305.17008; situational norms with constraints) surfaced in search but was not opened. The CSLAW '26 poster "Leveraging Legal Case-Based Reasoning…": title only. I did not read the Anthropic constitution PDF or the gpt-oss-safeguard technical report.

**Discrepancies between extractions (unresolved).** PrivacyLens GPT-4 leakage 25.68% (abstract) vs 24.54% (HTML v2 body); one extraction also gave 147 crowdsourcing participants and Fleiss' kappa 0.79 for seed validation, a second found no participant count in the main text — I omitted both. GoldCoin norm counts ("309 permit + 40 forbid" vs "269 permit + 40 forbid = 309 cases") — used the latter. ARGORA: digest said 2025, arXiv ID implies January 2026. ConfAIde: a digest gave tier-wise correlations (0.86 → 0.10) and inter-annotator alphas — not used.

**Background not re-opened here.** MoralExceptQA, Moral Stories, Deliberative Alignment, gpt-oss-safeguard report, the CSLAW '26 body (strands 16/17; Peter has read the latter three).
