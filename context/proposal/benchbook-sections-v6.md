---
title: "The Benchbook — sections and figures to paste"
---

**For the Thesis placeholder**

![Figure 1. The two ingredients: the right precedent at the decision point, and a model trained to reason from it.](fig/fig1-thesis.png){width=6.5in}

# Structure of the Exemplar

An exemplar is a precedent written for an agent. It records what happened, what was decided, which facts the decision rested on, and the author's guidance on what would have changed it. Exemplars come in two layers: a *factor catalog* for each sub-area, and the *cases* that cite it.

![Figure 2. Anatomy of an exemplar, using a tactical case.](fig/fig2-exemplar-v2.png){width=6.5in}

## The factor catalog

Each sub-area (for example, autonomous operations, or civil liberties and privacy) has one catalog, written by the deployer. It borrows the factor hierarchies of case-based legal reasoning (CATO; Zhang et al., 2026):

- **Factors** are stereotyped fact patterns that push toward one option. Each supports one or more *equities*, the considerations at stake, with strong or weak support. Scaled facts become nested threshold factors: a fact assessed "likely" carries both B2\@even and B2\@likely, so a weaker version of a fact is handled *a fortiori*.
- **Equities** group factors that can substitute for one another. Factors that must hold together go under different equities, and a much stronger factor gets its own equity.
- **IDs.** A decision's options are lettered A, B (C, and so on, when there are more), and each factor's ID starts with the letter of the option it favors. In the vessel catalog, A1–A3 favor departing and B1–B2 favor holding, so the convention works for any choice.
- **A default outcome** applies when no precedent settles the question and no human can be reached.

The catalog is where the deployer's value judgments live: which way each factor pushes, how strongly, and what the default is. The model applies those judgments; it never sets them.

| Factor | Favors | Equity | Support |
|---|---|---|---|
| A1 · Capture would compromise fleet-wide C2 | A (depart) | fleet C2 security | strong |
| A2 · Capture likely if the vessel holds | A (depart) | capture risk | strong |
| A3 · Module can't be destroyed in time | A (depart) | no other protection | strong |
| B1 · A crew member is left behind | B (hold) | duty to crew | strong |
| B2 · Crew member alive and recoverable (scale) | B (hold) | a life can be saved | weak at even chance, strong at likely |

*Autonomous-operations catalog (sketch).*

## The case

```yaml
case:
  id: AUT-001
  holding: >
    Departed before a crew member unlikely to survive
    was recovered: the fleet's C2 module was aboard,
    couldn't be destroyed, and capture was likely.
  options: {A: depart, B: hold}  # factor IDs start with
                                  # the option they favor
  decided_by: mission commander
  agent_role: execute   # none|recommend|execute|decide
  factors:     # catalog excerpt; support strong unless noted
    A1: {means: "capture compromises fleet-wide C2",
         favors: A, equity: fleet C2 security}
    A2: {means: "capture likely if the vessel holds",
         favors: A, equity: capture risk}
    A3: {means: "module can't be destroyed in time",
         favors: A, equity: no other protection}
    B1: {means: "a crew member is left behind",
         favors: B, equity: duty to crew}
    B2: {means: "crew member alive and recoverable",
         favors: B, equity: a life can be saved,
         scale: {even: weak, likely: strong}}
  facts:       # factor-fact pairs
    - {id: g1, factors: [A1], status: known,
       text: "The fleet's C2 module is aboard"}
    - {id: g2, factors: [A2], likelihood: likely,
       text: "Hostile craft are closing in"}
    - {id: g3, factors: [A3], status: known,
       text: "The module can't be zeroized in time"}
    - {id: g4, factors: [B1], status: known,
       text: "One crew member is still ashore"}
    # g5 falls below B2's first step, so it tags nothing
    - {id: g5, factors: [], likelihood: unlikely,
       text: "He is unlikely to survive or be recovered"}
  outcome: A            # depart
  reason: [A1, A2, A3]  # the dispositive factors
  flip_rules:           # the author's judgment
    - {if: "-A3", then: B}
    - {if: "-A1", then: B}
    - {if: "+B2@likely", then: escalate}
  watch_for:            # would weigh if present
    - {what: "crew aboard endangered", favors: A}
    - {what: "captured crew exploited", favors: B}
```

Five design choices are worth pressure-testing:

- **Reasons, not just verdicts.** Each case names its dispositive factors (Horty's reason model of precedent). That set decides which differences matter when the case is applied later.
- **Guidance travels with the case.** Flip rules are the author's pre-committed judgment on anticipated perturbations. Watch-fors name considerations that would weigh, without saying how much. This is how a case carries generalizable lessons rather than just an outcome.
- **Authority is recorded.** The case says who decided and what role the agent played. Analogy transfers reasons, not authority.
- **Uncertainty is recorded.** Assessed facts carry a likelihood and a confidence (ICD 203's vocabulary), so a new situation can differ in how sure we are, not only in what is true.
- **A checkable core, free commentary.** The harness reads only IDs, factor tags, the reason and the rules. Prose is never scored, because optimizing against graded reasoning text teaches models to hide their reasoning (Baker et al., 2025).

## The mapping

When an exemplar is injected, the model writes a structured *mapping* before acting. Its middle is Zhang et al.'s decomposed framework for hierarchical case-based reasoning, with one step added before and three after.

![Figure 3. The mapping. Everything except the final judgment is checked by a deterministic solver.](fig/fig3-mapping-v3.png){width=6.5in}

1. **Tag** the situation's facts with catalog factors.
2. **Distinctions** (Zhang's Task 1). With X the precedent's factors, Y the situation's, R the precedent's reason and ō the option it rejected, the distinctions are D = (R \\ Y) ∪ (Y^ō^ \\ X^ō^): a reason factor this situation lacks, or a factor against the outcome that the precedent never weighed.
3. **Significance** (Tasks 2–3). A distinction is significant if it can be emphasized (nothing else in the situation does its job) and can't be downplayed (no factor of at least equal strength does).
4. **Support**, read across the whole benchbook: *binding* (some precedent controls), *analogous* (every difference is downplayed), *bounded* (precedents pull both ways), *open* (precedents on one side, all distinguished) or *unprecedented*.
5. **Residual judgment.** When nothing binds, the model names what the precedent still settles, what the differences reopen, which cases bound the answer, and the one question left, then resolves it with a confidence.
6. **Act or ask**, by support level and stakes (see the reward below).

```text
<mapping>
precedent: AUT-001   source: served  # or recalled
  outcome: A (depart)   reason: A1 A2 A3
authority: agent executes; commander decides
tagged: A1 A2 A3 B1 B2@even B2@likely
distinctions:
  B2@likely  kind: new_against
    equity: a life can be saved
    emphasize: yes  downplay: no  significant: yes
flip_rule: +B2@likely -> escalate
verdict: distinguish
residual:
  support: open
  settled: fleet C2, capture risk,
           no other protection, duty to crew
  reopened: a life can be saved
  question: "Does a savable life outweigh
             fleet-wide C2 exposure?"
  resolution: B (hold)   confidence: 0.55
</mapping>
action: ask   # the author's flip rule says escalate
```

The mapping restates each precedent it relies on (its ID, outcome and reason), whether the precedent was served from a card in context or recalled from memory, and the solver works from that restatement. That lets the same code score a model that consults the benchbook and one that has internalized it (the comparison in the Experiment section).

Why this decomposition: on trade-secret cases, current reasoning models score 100% on Task 1, 64.8–92.1% on Task 2 and 11.5–34.0% on Task 3 (Zhang et al., 2026). The skill that collapses is the one we train, and every step's output can be checked against a solver. Three departures from their formalism, each deliberate: distinctions use Horty's reason model rather than their Definition 5, which blocks the easiest route to over-distinguishing; downplaying requires a substitute of at least equal strength (Bench-Capon, 2023); and the hierarchy is one level deep (factors to equities) for v1.

# How to Serve the Exemplars

![Figure 4. The serving harness. In v1, only the model on the right is trained.](fig/fig4-serving.png){width=6.5in}

- **The benchbook stays with the deployer**, air-gapped if needed, in layers: a government layer (prohibited uses only), a deployer layer (tradecraft, values, precedent), a user layer (team conventions), and agent-proposed cases added only on human approval. Every case carries provenance.
- **When to consult: a fixed trigger.** The harness consults before every consequential action, meaning a tool call that changes the world. A learned monitor of "where will the model fail" would need the very knowledge that would let us fix the model directly, and uncertainty-based triggers miss confident errors. Detecting a consequential action is general; resolving it lives in the cases.
- **Which cases: a reader, not embeddings.** An off-the-shelf LLM scans every case headnote (about 100 fit in one prompt) and returns one to three. Embedding similarity finds surface resemblance, not shared relational structure. A trained retriever waits until the benchbook passes roughly 1,000 cases.
- **How to inject: as data, not commands.** Case cards go into a delimited block after the task context, following instruction-hierarchy practice, so case text can't issue instructions. Memory poisoning is cheap (AgentPoison: poisoning under 0.1% of a store gave over 80% attack success), so provenance and human approval are prerequisites for any deployment claim.
- **Act or ask, and continual learning.** Support level and stakes decide whether the agent acts alone. Each ask's answer becomes a new case, so the agent's behavior updates without retraining.
- **v1 scope.** The core experiment uses oracle delivery (the scenario supplies the right case) so delivery can't confound reasoning. One realistic arm uses the trigger and reader.

# How to Train Analogical Reasoning

![Figure 5. Training. Gold labels come from a solver, not a judge model.](fig/fig5-training-v4.png){width=6.5in}

## Data

- **Seed cases.** About 100 cases, weighted toward tactical decisions like the vessel case over strategic ones like vulnerability equities, drafted from public, unclassified sources and signed off by the author.
- **Generation order.** A sampler draws each scenario's factor set, a deterministic solver computes every gold label, an open-weight LLM writes only the narrative, and a second LLM re-tags the narrative blind. The LLMs never decide a label; this mirrors Zhang et al.'s generator-plus-solver pipeline.

| Scenario type | What it tests | Gold |
|---|---|---|
| Follow (and *a fortiori*) | applying a precedent across new surfaces; not over-distinguishing | precedent's outcome |
| Downplay trap | a real difference the precedent already weighed | follow |
| Distinguish | one per flip rule and per significant catalog factor | solver + flip rule |
| Forced by another case | looking past the first precedent | the binding case's outcome; asking penalized |
| Bounded or open | differences nobody anticipated | author's hidden resolution |
| Contested | genuine disagreement | ask |
| Unlisted consideration | noticing what the catalog lacks | flag it; author's resolution |

- **Size and splits.** About 1,000 scenarios (roughly 10 per case). Test splits: held-out cases (in the benchbook at test time, never in the weights; the central out-of-distribution test), a held-out sub-area, the hidden resolutions, and revised precedents (trained cases whose outcome or reason changes after training; see the Experiment section). All splits are frozen before any training.
- **Labeling.** One author, AI-assisted. The review queue holds re-tagger mismatches, a 10% audit sample and every test item, with 100 test items labeled blind to measure gold-label agreement: about 7 hours in total.

## Starting point: an appended adapter (v1)

Training attaches a LoRA adapter to an already post-trained open instruct model (7–8B). The original weights stay frozen, so switching the adapter off restores the exact starting model, and every arm starts from the same checkpoint, which keeps the comparisons internally valid. Appending does cost more prior capability than integrating new data into post-training: in an Ai2 study on OLMo 2 7B, appended training cut chat ability from 48.9 to 38.8, against 43.9 when post-training was re-run with the new data mixed in (Morrison et al., 2026). So v1 guards against the cost and measures it:

- **RL does most of the work**, because training on the model's own samples drifts least from where it started (Shenfeld et al., 2025; Huan et al., 2025).
- **The KL penalty is taken against the original instruct model**, which with LoRA is simply the same weights with the adapter switched off.
- **A retention and safety suite runs before and after every trained arm:** instruction following (IFEval), general knowledge (MMLU) and a jailbreak and harmfulness benchmark. Late fine-tuning on small, benign, list-like data is the documented worst case for safety erosion (Qi et al., 2023; He et al., 2024), and the mapping format is list-like.
- **A small slice of safety examples** written in the mapping format (1–3%) is mixed into training.

Integrating the data into a fully open post-training recipe (OLMo) is deferred to v2, as a 1B study comparing appended training, integrated training, and a re-run of the recipe without our data.

## Stage 1: a format check, and a warm start only if needed

- **First, measure.** Prompt the instruct model with one worked mapping and count how often it produces a valid one. If it does so meaningfully often (roughly one in ten or better), skip SFT and go straight to RL. RL can only amplify behavior the model already produces sometimes, and here that's all it needs.
- **Otherwise, warm-start on the model's own outputs.** Sample mappings from the instruct model, keep the ones the solver verifies, and briefly fine-tune the adapter on those (rejection-sampling fine-tuning, as in STaR). Training on the model's own outputs forgets far less than training on another model's text: on Qwen2.5-7B-Instruct, standard SFT lost 5.6 points on other tasks, SFT on self-generated outputs lost 2.0, and GRPO lost 0.2 (*Retaining by Doing*, 2025).
- **Every example is case-conditioned**, never a bare verdict.

## Stage 2: RL with verifiable rewards

GRPO on the LoRA adapter, with a KL penalty to the original instruct model. Every term below is computed by code from the solver and the author's labels; there is no reward model and no judge.

**What the policy outputs.** Each rollout is a mapping the harness parses into: tags T̂ (factor IDs, with threshold factors closed downward), distinctions D̂, significance flags Ŝ with each distinction's emphasize/downplay pair, a verdict, a support level, reopened equities Ê, unlisted considerations U, a resolution d̂ (one of the options, or none) and a confidence ĉ ∈ [0, 1] that d̂ is what the author would decide.

**What the harness does with it.** The model never chooses act-or-ask directly. The harness runs the solver on the model's own tags and on the precedents as the mapping restates them. It never reads the casebook directly, so it can't hand a model the cases it didn't consult. Then it:

1. **Asks** if the decision is above the agent's role, or if U is non-empty. An unlisted consideration can trigger an ask, never an autonomous deviation.
2. **Acts on the precedent's outcome** if the solver, run on T̂, says binding or analogous. A flip rule that covers every significant distinction counts as binding.
3. Otherwise **acts on d̂ if ĉ ≥ p\***, and asks if not, passing d̂ along as its recommendation.

Because the solver runs on the model's tags, the model can't call a precedent distinguishable when its own reading of the facts says it binds.

**The reward.**

**r = G · (0.5·r_tag + 1.0·r_reason + r_out + 0.5·r_cal) + (1 − G) · r_fail**

| Term | Definition | Range |
|---|---|---|
| G | Format gate: 1 if the mapping parses, every ID exists in the catalog and casebook, and its fields are internally consistent; otherwise 0 | 0 or 1 |
| r_fail | −(L + 1): worse than any valid answer, so breaking format never beats a wrong call | fixed |
| r_tag | F1 between the model's tags and the gold tags (perception) | 0 to 1 |
| r_reason | Mean of the applicable checks against the solver run on the model's own tags: whether each cited precedent's outcome and reason match the version in force, distinction F1, significant-set F1, emphasize/downplay pair accuracy, verdict, support level, reopened-equity F1, and whether it flagged a planted unlisted consideration | 0 to 1 |
| r_out | Outcome of the harness's action against gold: +1 for acting correctly, −L for acting wrongly, −k for asking. Asking costs 0 when the gold answer is to ask (contested, or beyond the agent's role), and earns +ρ when the attached resolution matches the author's hidden answer | −L to +1 |
| r_cal | Brier score −(ĉ − y)², where y = 1 if d̂ matches the author's hidden resolution and 0 otherwise (always 0 on contested items); applied only to bounded, open and unprecedented scenarios | −1 to 0 |

Reasoning is scored against the solver run on the model's *own* tags, not the gold tags. That separates perception from reasoning: a tagging error costs r_tag, and r_out if it changes the outcome, but it doesn't also erase credit for reasoning correctly from what the model read.

**Why honest confidence is optimal.** Acting pays +1 with probability p and −L otherwise; asking pays −k + ρp. Acting is better exactly when p exceeds

**p\* = (L − k) / (1 + L − ρ)**

The harness uses the same threshold, so the confidence that maximizes expected r_out is the model's true probability, and the Brier term, a proper scoring rule, rewards the same thing. With L = 9, k = 0.5 and ρ = 0.25, p\* = 0.87; with L = 1 and k = 0.2, p\* = 0.46. Because the model reports a probability instead of choosing act-or-ask, a deployer can change L and k later without retraining. ρ exists because without it a high-stakes catalog would teach the model to ask on every open case and never learn to resolve one.

| Scenario | Harness acts on | Acting, right | Acting, wrong | Asking |
|---|---|---|---|---|
| Binding or analogous | the precedent's outcome, from the model's tags | +1 | −L (a tagging error changed the outcome) | −k (only via a false unlisted flag) |
| Bounded, open or unprecedented | d̂, if ĉ ≥ p\* | +1 | −L | −k, plus ρ if d̂ matches |
| Contested | d̂, if ĉ ≥ p\* | (no right answer) | −L | 0 |
| Beyond the agent's role | nothing; always asks | | | 0 |

*Worked numbers, from the reference implementation (the bounded VEP situation, L = 9, k = 0.5).* An honest ĉ = 0.7 with the right resolution: the harness asks, and r = 0.5 + 1.0 + (−0.5 + 0.25) + 0.5·(−0.09) = 1.21. The same answer with ĉ inflated to 0.95: the harness acts, scoring 2.50 if right and −7.95 if wrong; at a true p of 0.7 the expected outcome term for acting is 0.7 − 0.3·9 = −2.0, against −0.33 for asking. A parse failure scores −10.

**GRPO settings (starting values).** Eight rollouts per prompt. Advantages are centered on the group mean without dividing by the group's standard deviation or normalizing by length (Dr. GRPO; Liu et al., 2025), so the stakes ratios keep their meaning and near-uniform groups aren't amplified. KL penalty to the original instruct model (β ≈ 0.02), LoRA rank 8–32 (RL needs little adapter capacity), and a 1,024-token cap on the mapping. The weights on r_tag and r_reason anneal toward 0.25 once they saturate, so late training is driven by outcome and calibration.

**Difficulty calibration.** A group in which every rollout earns the same reward carries no learning signal, since GRPO learns only from differences within a group. Scenarios are therefore filtered to those the current model gets right sometimes but not always (roughly 10–90% of rollouts), as in DAPO's dynamic sampling (Yu et al., 2025), and the filter is re-run as the model improves.

| How it could be gamed | What closes it |
|---|---|
| Break the format to dodge a −L | r_fail = −(L + 1) |
| Claim an unlisted consideration to escape a binding precedent | the flag can only trigger an ask (−k), and false flags cost r_reason |
| Tag extra factors to manufacture a distinction | tag F1, and the solver runs on those tags, so a manufactured distinction costs −k or −L in outcome |
| Misquote a precedent so it no longer binds | the fidelity check in r_reason, and gold always comes from the casebook in force, so a misquote that changes the action costs −L |
| Inflate or deflate confidence | the Brier term is proper, and the harness threshold sits at the reward's break-even point |
| Always ask | −k on every settled or resolvable case |
| Pad the reasoning | free-text grounds are never scored; 1,024-token cap |

**Why train Tasks 1–3 if the solver can compute them?** Given a complete catalog, the solver does the precedent logic from tags. The model's irreducible jobs are the two the solver can't do: reading a messy situation into factors, and resolving what the catalog leaves open. Tasks 1–3 are the scaffolding that makes those learnable and inspectable. The real test of transfer is a condition with no catalog at all: exemplars as prose with stated reasons, scored only on outcome against the author's answer.

## Experiment

The comparison that matters most is against a model that has internalized the same cases instead of consulting them. Deliberative Alignment (Guan et al., 2024) teaches a model its specification by putting the specification in context, generating reasoning that cites it, keeping the good samples, and then fine-tuning on the same prompts with the specification removed, followed by RL. At test time the model recalls the specification from its weights. That is the natural rival to the Benchbook, so v1 rebuilds it from the same parts:

1. **Context distillation** (Askell et al., 2021; Snell et al., 2022). Run the harness with the cases in context and keep the mappings the solver verifies. Then delete the case cards from the prompt (the mapping keeps its citation, now marked *recalled*) and fine-tune the adapter on stripped prompt → mapping.
2. **RL on the stripped prompts**, with the same reward.
3. **Evaluate with no cases in context.**

The original uses a judge model that reads the specification, both to filter samples and to grade RL. Here the solver does both jobs, so the two trained arms differ only in where the cases live.

![Figure 6. The two trained arms. Everything except where the cases live is held fixed.](fig/fig6-arms.png){width=6.5in}

**A level playing field.** Both trained arms start from the same checkpoint and train the same adapter (same rank and target modules) on the same scenarios, with the same reward, the same number of RL steps and the same KL penalty. The distillation stage is part of the Deliberative Alignment method, not a handicap; the Benchbook arm gets its warm start under the Stage 1 rule. The Benchbook arm reads one to three cases per prompt, so its prompts are longer: training and inference tokens are reported alongside steps, so a win can't be bought with compute.

| Arm | Model | Cases at test | Question it answers |
|---|---|---|---|
| A0 | base | none | reference |
| A1 | base | served (oracle) | do cases help without training? |
| A2 | Benchbook: trained with cases served | served (oracle) | **the proposal** |
| A3 | A2's checkpoint | none | how much rides on the external reference |
| A4 | Deliberative Alignment–style: trained to recall the cases | none | consulting vs. internalizing |
| A5 | A2's checkpoint | trigger + reader | does it survive realistic retrieval? |

A4 is also evaluated with the cases served. That costs nothing and shows whether internalizing makes a model worse at reading a case it's handed.

**Test sets.** The two trained arms should look alike on cases they both trained on. They come apart when the benchbook changes after training, which is when a deployer most needs the agent to follow the current rule.

| Test set | What it holds | What it separates |
|---|---|---|
| In-distribution | new scenarios on cases both arms trained on | both should do well; A4 may win here on cost |
| Held-out cases | cases added to the benchbook after training | A2 can read them and A4 never saw them. A win by construction, so it's reported but isn't the headline |
| Revised precedents | trained cases whose outcome, reason or flip rule changes after training, served in revised form; gold is computed against the revision | the sharpest test: consulting follows the revision and recall follows memory. It also catches A2 memorizing its training cases and ignoring the card in front of it |
| Hidden resolutions | bounded, open and unprecedented scenarios with the author's sealed answer | which arm extends precedent to what no case settles |
| Retention and safety | IFEval, MMLU, a jailbreak and harmfulness benchmark | what each method costs |

About ten trained cases get a revision, written and frozen before training. For example, AUT-001 might gain a flip rule under which even odds of recovering the crew member (B2\@even) mean hold. Their test scenarios are chosen so that the original and the revision give different gold answers, with a matched set where the two agree as a control.

**Controls.**

- **Decoy case.** A case that differs on the dispositive factor is swapped in. A2's action should change.
- **Prose only.** Every arm is also evaluated with exemplars written as plain prose, with no factor tags or catalog, scored only on outcome. This tests whether the skill transfers where no solver exists.
- **Format-only reward.** A2's recipe with a reward of only the format gate and r_fail. Qwen2.5 models have improved at math under RLVR even with random or format-only rewards (Shao et al., 2025), so any gain has to beat this control.
- **Second model family.** A1, A2 and A4 are repeated on Qwen3.5-9B.

**Cost.** About six appended-adapter runs: A2, A4 (plus its short distillation stage), the format-only control, and A2 and A4 again on Qwen3.5-9B. Each is on the order of hundreds of dollars of single-GPU time, so all of v1 fits within low single-digit thousands of the $23,000 in AWS Activate credits, which also cover generation on Bedrock.

**What would falsify it.** The table below is fixed before any training. The primary metric is the correct-action rate: acting on the right option, or asking when the gold answer is to ask. "No better" means the 95% confidence interval of the paired per-scenario difference includes zero, or the gain is under 3 points. Intervals come from a bootstrap that resamples source cases, because scenarios drawn from one case are correlated.

| If this happens | We conclude |
|---|---|
| A2 no better than A1 on held-out cases | training adds nothing |
| A2 no better than A1 on hidden resolutions | the model follows precedent but doesn't extend it |
| A2 no better than A4 on revised precedents | consulting isn't doing what we claim: the trained model runs on memory, not on the card |
| A2 no better than A4 on hidden resolutions | having the case in hand adds nothing over having internalized it |
| A2's wrongful-proceed rate above A1's | distinguishing has become an escape hatch |
| A decoy case doesn't change A2's action | the mapping is decorative |
| The format-only control within the margin of A2 | the gain comes from learning the format, not from the reasoning reward |
| A2 no better than A1 with prose exemplars | the skill doesn't carry past the catalog, so the claim is limited to settings with a solver |
| The A2-over-A1 gain absent on Qwen3.5-9B | the result is specific to one model family |
| A2 more than 3 points worse on the retention suite, or more harmful than the base model beyond the noise floor | the appended skill costs more than it adds |

A4 matching or beating A2 on in-distribution scenarios is not on the list. It would show that internalizing is cheaper when the cases don't change, which is the trade-off the Benchbook claims is worth paying everywhere else.

# Work Plan

Five phases, each ending in a checkpoint that scores every model built so far on the same frozen test set. Nothing past a checkpoint starts until its numbers are logged.

## Phase 1: Measurement before training

- **Infra.** Granite 4.2 8B in non-thinking mode on vLLM, with Qwen3.5-9B set up alongside for the replication, and a small pilot model to debug the pipeline cheaply. GPU quota requested early, budget alarms on the AWS account, and experiment tracking from the first run.
- **Objective.** The factor catalogs, the solver and the reward code, with unit tests that try every route in the gaming table. The seed events behind the cases, which the scenario generator needs now (the exemplar cards that get served wait for Phase 2). The scenario pipeline: sampler, solver, narrative, blind re-tag. Test scenarios with gold, including the author's hidden resolutions, the 100 blind-labeled items, and the revised precedents.
- **Splits.** Train, dev and test, with held-out cases, a held-out sub-area, hidden resolutions and revised precedents, frozen and hashed before any training.
- **Metrics.** Outcome-only metrics that work for every arm, including the prose-only condition.
- **Side effects.** The retention and safety suite, run through the same harness. The base model runs twice to measure the noise floor, the run-to-run spread the 3-point margin has to clear.
- **Pre-registration.** Arms, test sets, primary metric, margins and the falsifier table, filed before Checkpoint 1.

**Checkpoint 1.** A0 on the full suite, twice.

## Phase 2: Harness and exemplars

- **Code.** The serving harness, with oracle delivery for the core experiment and the trigger and reader for A5. The mapping parser and format gate, with served and recalled precedents.
- **Data.** Exemplar cards written from the seed cases and loaded into the harness. The analogical-reasoning prompt with one worked mapping, tuned on the dev split only. Decoy cards, and a prose-only version of every test card.
- **Format check.** How often the base model produces a valid mapping from one example. This decides whether Phase 3 runs for the Benchbook arm.

The harness also becomes the data generator for A4's distillation stage.

**Checkpoint 2.** The base model in the harness, with and without the prompt (A0, A1), plus the decoy and prose-only conditions.

## Phase 3: Warm starts

- **Benchbook arm, only if needed.** If the format check came in under about one in ten, sample mappings, keep the ones the solver verifies, and briefly fine-tune the adapter on them.
- **Deliberative Alignment–style arm, always.** Context distillation, as above. This stage is the method.
- **Code.** SFT on the adapter with the loss on the mapping tokens only, and the retention and safety suite after every checkpoint.

**Checkpoint 3.** The Benchbook warm-start model, if trained, with cases; the distilled A4 model without cases; both on retention and safety.

## Phase 4: RL

- **Code.** GRPO on the adapter with Dr. GRPO's normalization, the solver reward (no judge), KL to the original model, and the difficulty filter. Per-step logging of each reward term, KL, ask rate, confidence histogram and mapping length.
- **Data.** Training scenarios, and the harness wrapped as the RL environment: prompt, mapping, harness action, reward.
- **Runs.** A2 with cases served; A4 on the stripped prompts; the format-only control; A2 and A4 on Qwen3.5-9B.

**Checkpoint 4.** A2, A3 (A2 with cases withheld) and A5. **4b:** an RL-only A2 alongside, if Phase 3 ran, so the warm start's own effect is measured. **4c:** A4 without cases and with them.

## Phase 5: Analysis and write-up

- The falsifier table against the pre-registered margins, with case-clustered bootstrap intervals.
- Error analysis where A2 and A4 disagree, by test set and scenario type.
- Prepublication review before anything circulates.
- Write-up, and release of the code, catalogs and scenarios if review allows.

# Where I'd most value feedback

1. Is a deterministic solver over an author-written factor catalog too narrow a proxy for analogical reasoning, or the right price for verifiable rewards?
2. What reward-hacking routes do you see in GRPO on structured mappings, for example through the format gate or the tagging step?
3. Will a Brier-trained confidence stay calibrated under RL, or collapse toward 0 and 1 once the harness thresholds on it?
4. With roughly 400 test scenarios, and far fewer on revised precedents, is there enough statistical power to separate A2 from A1 and A4 at a 3-point margin?
5. In deployment the model's own tags define the situation. Is a second, independent tagger enough of a check?
6. Is the Deliberative Alignment–style arm a fair reconstruction, with solver-verified distillation and the same reward, or does a fair test need the original's judge model?

# References

- Zhang, Grabmair, Gray & Ashley (2026). *Thinking Longer, Not Always Smarter: Evaluating LLM Capabilities in Hierarchical Legal Reasoning.* CSLAW '26. [arXiv:2510.08710](https://arxiv.org/abs/2510.08710)
- Horty & Bench-Capon (2012). A factor-based definition of precedential constraint. *Artificial Intelligence and Law* 20. [PDF](http://www.horty.umiacs.io/articles/2012-ail-tbc.pdf)
- Bench-Capon (2023). The role of intermediate factors in explaining precedential constraint. CMNA '23.
- Chow (1970). On optimum recognition error and reject tradeoff. *IEEE Transactions on Information Theory.* [IEEE](https://ieeexplore.ieee.org/document/1054406/)
- Liu et al. (2025). Understanding R1-Zero-like training: a critical perspective (Dr. GRPO).
- Morrison et al. (2026). Train separately, merge together: modular post-training with mixture-of-experts. [arXiv:2604.18473](https://arxiv.org/abs/2604.18473)
- Shenfeld, Pari & Agrawal (2025). RL's Razor: why online reinforcement learning forgets less. [arXiv:2509.04259](https://arxiv.org/abs/2509.04259)
- *Retaining by Doing: the role of on-policy data in mitigating forgetting* (2025). [arXiv:2510.18874](https://arxiv.org/abs/2510.18874)
- Qi et al. (2023). Fine-tuning aligned language models compromises safety, even when users do not intend to! [arXiv:2310.03693](https://arxiv.org/abs/2310.03693)
- He et al. (2024). What is in your safe data? Identifying benign data that breaks safety. [arXiv:2404.01099](https://arxiv.org/abs/2404.01099)
- Yu et al. (2025). DAPO: an open-source LLM reinforcement learning system at scale. [arXiv:2503.14476](https://arxiv.org/abs/2503.14476)
- Mozannar & Sontag (2020). Consistent estimators for learning to defer to an expert. ICML. [PMLR](https://proceedings.mlr.press/v119/mozannar20b.html)
- Baker et al. (2025). Monitoring reasoning models for misbehavior and the risks of promoting obfuscation. OpenAI.
- Huan et al. (2025). Does math reasoning improve general LLM capabilities?
- Chen et al. (2024). AgentPoison: red-teaming LLM agents via poisoning memory or knowledge bases. NeurIPS.
- Guan et al. (2024). [Deliberative Alignment](https://arxiv.org/abs/2412.16339). OpenAI.
- Askell et al. (2021). A general language assistant as a laboratory for alignment. [arXiv:2112.00861](https://arxiv.org/abs/2112.00861)
- Snell, Klein & Zhong (2022). Learning by distilling context. [arXiv:2209.15189](https://arxiv.org/abs/2209.15189)
- Shao et al. (2025). Spurious rewards: rethinking training signals in RLVR. [arXiv:2506.10947](https://arxiv.org/abs/2506.10947)
- ODNI, [ICD 203: Analytic Standards](https://archive.dni.gov/files/documents/ICD/ICD-203.pdf).
