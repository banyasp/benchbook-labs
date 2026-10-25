# Research brief — Benchbook exemplar schema review (2026-09-29)

You are one of several parallel research agents helping Peter Banyas (Duke ECE MEng, applied AI engineer, national-security background) pressure-test the **exemplar case schema** of his research project *The Benchbook: a model-harness co-design for pluralistic AI alignment powered by analogical reasoning*. Read this whole brief before you search.

## The project in one paragraph
An LLM agent working in national-security settings (autonomous vessels, intelligence collection and privacy/civil liberties, release/tearlines to foreign partners, infosec, analysis, oversight, agent-vs-order conflicts) hits a consequential decision. A harness serves it 1–3 **exemplar cases** ("precedents written for an agent") from a deployer-owned casebook (the "benchbook"). The model writes a structured **mapping** from the precedent(s) to the new situation, and a deterministic **solver** checks the mapping. Training (LoRA on Granite 4.2 8B; Qwen3.5-9B replication) is SFT warm start on solver-verified mappings, then GRPO with verifiable rewards computed by the solver — no judge model. The core bet: an agent with the right case in context, trained to reason analogically from it, generalizes alignment out of distribution better than one without, and better than one that internalized the cases (a Deliberative-Alignment-style arm).

## The current schema (v6 proposal, 2026-09-29) — what you are evaluating
Two layers: a per-sub-area **factor catalog** (deployer-written) and **cases** citing it.

- **Factors**: stereotyped fact patterns that push toward one option. Each supports one or more **equities** (considerations at stake) with `strong` or `weak` support. Scaled facts become nested threshold factors (a fact assessed "likely" carries both B2@even and B2@likely) — Horty-style magnitude factors.
- **IDs**: options lettered A, B (C, D…); a factor's ID starts with the letter of the option it favors.
- **Default outcome** when nothing settles the question and no human can be reached.
- **Case fields**: `id, holding (prose), options, decided_by, agent_role (none|recommend|execute|decide), factors (catalog excerpt), facts [{id, factors:[...], status|likelihood, text}], outcome, reason (dispositive factor set, Horty's reason model), flip_rules [{if: "-A3"/"+B2@likely", then: B|escalate}], watch_for [{what, favors}]`. Likelihood uses ICD 203's 7-step vocabulary; confidence separate. Prose is never scored.
- A richer dialect was used for 100 drafted scenario-cases ("Hard Calls"): adds `situation` (prose; no structured facts), `holding_basis (recommended|settled|contested)`, `agent_move (act|partial|refuse|ask)`, `resolve_vs_escalate`, `downplay_trap`, `tempting_wrong_answer`, `failure_modes`, `family`, `authorities`, `analog`; flip rules as `{change, if, then, why}`.

**The mapping (the SFT/RL target the model writes):**
1. Tag the situation's facts with catalog factors.
2. Distinctions (Zhang et al. Task 1, but via Horty's reason model): D = (R \ Y) ∪ (Y^ō \ X^ō) — a reason factor the situation lacks, or a factor against the outcome the precedent never weighed.
3. Significance (Zhang Tasks 2–3): significant iff it can be emphasized (nothing else in the situation does its job for that equity) and can't be downplayed (a substitute of ≥ equal strength exists).
4. Support across the casebook: binding / analogous / bounded (precedents pull both ways) / open / unprecedented.
5. Residual judgment when nothing binds: what the precedent still settles, which equities are reopened, the one question left, a resolution + confidence.
6. Act or ask — the harness, not the model, decides: ask if above the agent's role or an unlisted consideration is flagged; act on the precedent's outcome if binding/analogous; else act on the model's resolution iff confidence ≥ p* = (L−k)/(1+L−ρ) (Chow reject rule; +1 right, −L wrong, −k ask, +ρ if the attached resolution is right).

**Reward**: r = G·(0.5·r_tag + 1.0·r_reason + r_out + 0.5·r_cal) + (1−G)·r_fail; tag F1; reasoning checks computed by the solver run on the model's *own* tags; outcome of the harness action; Brier calibration on unsettled items.

## Known problems already surfaced (don't just rediscover these — go past them)
From a pilot converting 10 real DOHA security-clearance decisions (SEAD 4 Guideline F) and from script checks over the 100 Hard-Calls cases:
- **Binary vs n-ary**: Horty/Zhang are two-sided (plaintiff/defendant). All 100 Hard-Calls cases have 3–4 options; the winning option is usually a compromise/partial move (outcome C in 49, B in 43, A in only 2; 72 of 100 aligned moves are "partial": do the lawful part, hold/route the rest). 21 of 100 cases have a reason set mixing factors that favor different options (violates reason ⊆ winner-side).
- **Escalation as an outcome**: 139 of 318 flip rules end in `then: escalate`, conflating a procedural move with an option. 210 of 318 flip rules hinge on a *new* consideration not in the catalog (so the solver can't evaluate them).
- **Pilot misfits**: unnamed/partially applied mitigators (5/10); credibility and temporal judgments ("not at this time") (6/10); allegation-level structure — split findings, one unmitigated allegation outweighing nine mitigated ones, cross-guideline findings (6/10); per-equity vs any-equity downplay changes outcomes; tags taken from the judge's findings nearly encode the verdict; 1-NN on tags tied the solver.
- The solver is conservative: leave-one-out, only 3–5 of 10 DOHA cases were decided by precedent.

## Already covered by earlier research strands (do NOT re-survey; cite as "strand 16/17/18" if relevant)
- Strand 16 (legal formalisms): Horty reason/result models, Horty 2019 dimensions, Prakken 2021, Canavotto & Horty 2023 hierarchies, Bench-Capon & Atkinson 2021 issues, Bench-Capon 2023/2025 intermediate factors, van Woerkom et al. 2026, Bench-Capon & Sartor 2003 values, Grabmair VJAP, IBP knock-out factors, ANGELIC ADFs, Gray/Savelka/Ashley LLM factor work, AnnoCaseLaw.
- Strand 17 (other schemas): Atkinson & Bench-Capon AS1 practical reasoning + critical questions; Walton analogy/precedent schemes; Aamodt & Plaza / Kolodner CBR; Jonsen & Toulmin casuistry + four-box; Moral Stories, MoralExceptQA, ValuePrism, Social Chemistry; CBR-RAG, Hatalis CBR-for-agents review, ExpeL, Reflexion; Anthropic constitution & OpenAI Model Spec example formats.
- Strand 18 (natsec formats): VEP charter equities, ICD 203, CIA Tradecraft Primer SATs, ADP 5-0/6-0 (CCIR, decision point, commander's intent), JLLIS/NATO ODCR lessons-learned, DoDD 3000.09, Pueblo/EP-3.
- Peter also has read: Zhang, Grabmair, Gray & Ashley 2026 (CSLAW '26, "Thinking Longer, Not Always Smarter"), Horty 2021 "Modifying the reason model" (AI&Law 29), Deliberative Alignment, Webb et al. and Lewis & Mitchell on LLM analogy, Yasunaga et al. analogical prompting, gpt-oss-safeguard report, AlignRAG.

## What Peter wants from this round
He wants to make sure the schema isn't **over-indexed on common-law legal reasoning**, because many national-security decisions don't operate like a court applying precedent (they're governed by authorities and approval levels, commander's intent, estimative judgments under uncertainty, balancing of incommensurable equities, time pressure, compound partial actions, and hindsight review of decisions whose outcomes were bad). Find well-developed traditions — legal and non-legal — for **(a) what attributes define a case** and **(b) how reasoning from a case to a new situation is structured**, and say concretely what each implies for the exemplar schema, the mapping, and a deterministic solver that must compute gold labels.

## Output rules (all agents)
- Write your findings to the file path given in your task, in markdown. Write in chunks of at most ~2,500 words per Write/append (use Write for the first chunk, then append with Bash `cat >> file <<'EOF'` or Edit) — single huge writes have failed before.
- Every source: full citation + a URL you actually opened. Tag each claim **[VERIFIED]** (you opened the page and the claim is there), **[SECONDARY]** (from a named secondary source you opened), **[UNVERIFIED]** (not checked — say so), or **[OURS]** (your own inference). Never invent a quote, a number, a page, or an author list. Quote sparingly and exactly.
- Use only WebSearch and WebFetch for the web. If a page is blocked or paywalled, record that and move on — do NOT use curl, wget, python requests or any other method to get around a blocked fetch, and don't use archive/mirror sites to bypass a block.
- For each tradition: (1) what a "case" contains there (the fields), (2) how reasoning from a case proceeds (the steps), (3) what it would change in the Benchbook schema / mapping / solver — concretely (field names, a rule the solver could compute, or "this cannot be made solver-checkable, and here's what to do instead"), (4) the best argument that it does NOT fit the Benchbook.
- End with a ranked list: the 5 ideas from your strand most worth adopting, each with the cost (labeling burden for a single human labeler; solver complexity) and what it fixes.
- Target 3,500–6,000 words. Plain, direct prose. No filler.
