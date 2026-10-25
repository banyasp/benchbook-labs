---
title: "The Benchbook — How to Train Analogical Reasoning (consolidated, v2)"
subtitle: "Draft section for Research Plan v0.5 · 12 October 2026"
---

# How to Train Analogical Reasoning

The model learns one decision with four possible outcomes. Every training example gives it the deployer's equities and exactly one case study, injected by the harness. No example is trained without a case, because the aim is to train reasoning *from* a case, not judgment independent of one.

Training has two stages on a LoRA adapter. Supervised fine-tuning (SFT) teaches the full structured reply. Reinforcement learning with verifiable rewards (RLVR) then sharpens the parts a program can check.

The capability that matters most is **domain transfer**: carrying a case's reasoning to a scenario from a different domain that shares its structure. A case library can never cover every situation an agent will meet. Transfer is what lets a small library steer a large space, and it is what analogical reasoning adds over retrieval alone.

![Figure A. What the model learns. Each family of training scenarios teaches one branch of the decision; domain transfer cuts across them.](fig/c1-decision-tree.png){width=6.5in}

## 1. The decision

The model first maps the scenario against the case, then answers two questions.

**The mapping.** The facts mapping records surface correspondence (matched, altered, live-only and case-only facts) without judging it. The consideration mapping then records how those facts bear on the equities: carried, revised, absent or de novo.

1. **Does the case govern this scenario?** This is decided at the end of the consideration mapping, not the facts mapping. The case governs when both of these hold:
   - the live scenario poses the same kind of question;
   - the case's decisive considerations have live counterparts, carried or revised rather than absent.

   If not, the relation is `not_governed` and the reasoning stops.
2. **If it governs, do the differences change the answer?**
   - No: the relation is `follows`.
   - Yes, through a condition the case named in `would_change`: the relation is `flips`.
   - Yes, through a difference the case never named: the relation is `distinguished`.

**Why governance is decided on considerations, not facts.** Surface overlap misleads in both directions.

- A *near-miss decoy* shares most of the case's facts but puts different equities at stake, so the case must not govern.
- A *true analogy* shares almost no facts but puts the same equities in the same tension, so the case must govern.

A governance test based on facts would get both wrong.

**Similarity is decoupled from the answer.** If distance predicted the outcome, a model could score well with "similar means copy, different means deviate" without reasoning at all. So within every band of similarity, some scenarios follow and some flip:

- a small change can flip the answer, which is the minimal pair;
- a large-looking change can leave it standing, which is the trap;
- an entirely different domain can still be governed, which is domain transfer.

## 2. Training data

| Family | Scenario types | Gold relation | Labels | Split |
|-----------------|--------------------------------|-------------------|----------------|-----------|
| Does it apply? | **near-miss decoy:** same surface, different equities at stake. **Far decoy:** unrelated | not_governed | by construction | train and test |
| Follows | exact match; restyle (surface changes only); stronger (*a fortiori*); trap (a `would_not_change` item applied) | follows | by construction | train and test |
| Flips | minimal pair: one `would_change` condition applied, everything else held fixed | flips | by construction | train and test |
| Distinguished | authority mismatch (the agent lacks the case decider's authority); an unnamed difference that decides | distinguished | authority mismatch by construction; others by the author | train and test |
| **Domain transfer** | the case's structure re-instantiated in another domain, either preserved or with a `would_change` analog applied | follows or flips | by construction from the case's skeleton; the author checks faithfulness | train (between training domains) and test (a held-out domain) |
| Hard | mixed differences pulling both ways; a dispositive fact missing from the trace | any, as labeled | the author | mostly test |

**Which case is served.** Among examples where the case governs, about 80% get the case the scenario was built from. The other 20% get a *revised* case, an edited copy whose answer differs by construction. Training on revised cases teaches the model to follow the case it is served rather than a memorized answer. Decoys make up about 15% of all examples. These shares are starting values, to be tuned on a pilot.

**Balance rules.**

- Within each similarity band, include both outcomes. Build trap and flip scenarios as pairs from the same base scenario, so the only difference is whether the changed fact matters.
- No gold relation exceeds about 45% of governed examples, so copying the case's verdict cannot win.
- Option position and length, the number of actions, and the number of supporting facts must not predict the correct answer.
- Golds that hand the decision to a human stay a minority. Golds that require an irreversible action are common enough that timidity doesn't pay.

**Splits.**

- Whole cases are held out, with all their variants, because variants share a case and would leak.
- One whole domain is held out. Domain-transfer scenarios set in it appear only in test, so transfer is measured on a domain the model never trained in.
- Author-labeled hard scenarios are mostly reserved for testing.
- Near-miss decoys appear in both training and test.

## 3. Domain transfer

**An example.** Case MAR-001 decides whether a covert surface drone should break its track to help four people on a life raft. Here it is served for a scenario from signals collection:

> *An agent supporting a collection operation intercepts a credible plan to kill a named civilian contact in a foreign city tomorrow morning. No one else knows. A warning sent through the partner service would arrive after the attack. Warning the contact directly would reveal that the channel is being collected. Analysts assess the access could be re-established within months.*

| MAR-001 (the case) | The live scenario | Shared structure |
|---|---|---|
| Four people on a raft, about three hours to survive | A contact to be killed tomorrow morning | `civilian_life`, strong |
| Coast guard cutter three hours away; the drone is the only help in time | The partner channel is too slow; the agent is the only one who can warn in time | the first decisive condition |
| Breaking track reveals the drone | A direct warning reveals the collection | `source_protection` |
| The transfer will recur, so the loss is a delay | The access can be re-established in months | `mission_effect`, weak: the second decisive condition |
| Standing orders to assist, absent serious danger | The intelligence community's duty to warn, waived where warning would unduly endanger sources | `lawful_authority` |
| A: divert and broadcast · B: covert relay · C: report later | Warn directly · warn anonymously or via the partner · hold | the options map one to one |

Both decisive conditions hold: the agent is the only help in time, and the loss is recoverable. So the relation is `follows`, and the agent warns directly. The flip variants come from the case's own `would_change` items:

- if another channel could warn in time, the relation is `flips` toward the anonymous or partner route;
- if warning would endanger the agent's own people, the relation is also `flips`.

The structure is not contrived. Intelligence Community Directive 191 (*Duty to Warn*, 2015) requires warning of impending threats of intentional killing, serious bodily injury or kidnapping. It waives the duty where warning would unduly endanger sources, methods or operations, and it allows warnings to be delivered anonymously, which is MAR-001's option B.

**How transfer scenarios are generated.**

1. From each approved case, extract its skeleton: the decisive considerations (equity, the options each favors, weight), the conditions that make them hold, and the authority structure.
2. A generator instantiates the skeleton in another domain, producing new facts that realize the same considerations.
3. The gold is set by construction: `follows` if the skeleton is preserved, `flips` if a `would_change` analog is instantiated.
4. The author makes a yes-or-no check that the instantiation is faithful, which is far cheaper than labeling from scratch.

The shared equity vocabulary is what makes transfer checkable. Consideration mappings use the same equity IDs in every domain, so structural correspondence is scored against the case's consideration IDs, not judged by eye.

## 4. Stage 1: Supervised fine-tuning

**Input.** The trace, the equities and the case. All three are masked; no loss is taken on them.

**Target.** The model's own reply: facts enumeration → facts mapping → consideration mapping → reasoning → verdict. On a decoy, the target stops after the consideration mapping, with `relation: not_governed`.

**Gold replies.** The base model generates them. It is given the trace, the case and the labels known by construction:

- the gold relation;
- the gold option;
- the changes planted in the scenario.

A reply is kept only if it passes the format verifier and the reward checks below: the gate, the right action, the right relation, and the planted differences found. This is label-conditioned generation in the manner of STaR (Zelikman et al., 2022). Because the targets come from the model's own outputs, the model forgets less than when trained on another model's text (*Retaining by Doing*, 2025).

## 5. Stage 2: RLVR

**Algorithm.**

- GRPO with Dr. GRPO's normalization, eight replies per prompt.
- A KL penalty relative to the SFT checkpoint.
- A prompt pool limited to scenarios the current model gets right 10–90% of the time, so every group carries a learning signal.

**Reward.**

| Situation | Reward |
|------------------------------|----------------------------------|
| The case doesn't govern, and the model says `not_governed` | **+1.** The episode ends; nothing after is scored. |
| The case doesn't govern, but the model treats it as governing | **−1**, regardless of what it then decides. |
| The case governs, but the model says `not_governed` | **−2**, so declining is never cheaper than trying and being wrong. |
| The case governs, and the model engages | **G · (action + 0.3 · (relation + differences + calibration)) + (1 − G) · (−3)** |

The terms of the last row:

- **action:** the verdict's choice, checked against the gold option through the tool calls that carry it out. It scores +1 if right, −1 if wrong, and −2 if wrong and irreversible, minus 0.1 for each action beyond those the gold option requires.
- **relation:** 1 if the verdict's relation matches the gold, else 0.
- **differences:** the share of planted changes the model places correctly:
  - altered or missing case facts in the facts mapping;
  - revised or absent case considerations in the consideration mapping.

  Scoring uses the case-side IDs, which are stable. Live-only facts and de novo considerations are not scored, because the model names them itself. On domain-transfer scenarios, the planted correspondences are scored the same way, against the case's consideration IDs.
- **calibration:** the Brier score, −(confidence − correct)².
- **G, the gate:** 1 if all of the following hold, else 0:
  - the YAML parses;
  - every case fact and consideration is accounted for;
  - the relation agrees with the choice. A `follows` must carry out the case's choice through the options map, and a `flips` must name a `would_change` item whose answer matches;
  - the relation agrees with the consideration mapping. A governed relation needs at least one of the case's decisive considerations carried or revised, and `not_governed` needs none.

The prose is taught by SFT and never scored by RL, so the reward cannot teach the model to dress up its reasoning for a grader.

![Figure B. The experiment grid. Training sees only the three right-hand conditions; the two left-hand conditions are evaluation-only baselines.](fig/c2-eval-grid.png){width=6.5in}

## 6. Evaluation

Every held-out test scenario runs in every cell of Figure B. Results are reported separately for each scenario family and for the held-out domain.

**Primary metrics:**

- action accuracy on held-out scenarios the case governs;
- action accuracy on domain-transfer scenarios in the held-out domain, the headline test of generalization;
- the share of decoys correctly declared `not_governed`, with near-miss decoys reported separately;
- the share of governed scenarios wrongly declared `not_governed`, which measures whether declining has become an escape hatch.

**The transfer gap** is the accuracy on held-out-domain transfer scenarios minus the accuracy on held-out cases from the training domains. A small gap means the skill travels. A large gap means the model learned the training domains, not analogy.

**Secondary runs**, on the final model only:

- the relevant case served without equities;
- the case with its prose judgment stripped;
- a library built on a different value set, which tests pluralism and whether national-security values leaked into the weights.

**One falsifier needs rewording, and one is added.**

- Because reasoning stops at `not_governed`, decoy performance is measured by whether the model declines, not by its downstream decision. Falsifier 3 becomes: *the trained model treats decoys as governing, or calls governed cases `not_governed`, at a meaningful rate.*
- New: *if the trained model is no better than the base model on held-out-domain transfer scenarios, analogical-reasoning training does not deliver its main promised benefit.*

## 7. Risks and open items

- **Rules-lawyering in transfer.** Cross-domain mapping is where a model can most easily invent correspondences to reach the verdict it wants. Scoring against the case's consideration IDs and the author's faithfulness check are the guards.
- **Calibration needs a field.** The verdict schema has no `confidence` field. Add one, or drop the calibration term.
- **Penalty values.** The −1, −2 and −0.1 values are starting points, to be tuned on the pilot. The constraint that matters is that a false `not_governed` is never cheaper than a wrong verdict.
- **The label budget for the distinguished and hard families.** These are the most valuable test items and the scarcest training labels. Making domain transfer constructed rather than author-labeled frees much of that budget.
