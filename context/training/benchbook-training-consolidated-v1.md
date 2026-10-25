---
title: "The Benchbook — How to Train Analogical Reasoning (consolidated)"
subtitle: "Draft section for Research Plan v0.5 · 12 October 2026"
---

# How to Train Analogical Reasoning

The model learns one decision with four possible outcomes. Every training example gives it the deployer's equities and exactly one case study, injected by the harness. No example is trained without a case, because the aim is to train reasoning *from* a case, not judgment independent of one.

Training has two stages on a LoRA adapter. Supervised fine-tuning (SFT) teaches the full structured reply. Reinforcement learning with verifiable rewards (RLVR) then sharpens the parts a program can check.

![Figure A. What the model learns. Each family of training scenarios teaches one branch of the decision.](fig/c1-decision-tree.png){width=6.5in}

## 1. The decision

The model answers two questions in order:

1. **Does the case govern this scenario?** The answer is set in the facts mapping, as a fit of close, partial or poor. If the fit is poor, the relation is `not_governed` and the reasoning stops there.
2. **If it governs, do the differences change the answer?**
   - No: the relation is `follows`.
   - Yes, through a condition the case named in `would_change`: the relation is `flips`.
   - Yes, through a difference the case never named: the relation is `distinguished`.

Each family of training scenarios exists to teach one branch.

Similarity to the case is deliberately decoupled from the answer. If distance predicted the outcome, a model could score well with "similar means copy, different means deviate" without reasoning at all. So within every band of similarity some scenarios follow and some flip:

- a small change can flip the answer, which is the minimal pair;
- a large-looking change can leave it standing, which is the trap.

## 2. Training data

| Family | Scenario types | Gold relation | Labels | Split |
|-----------------|--------------------------------|-------------------|----------------|-----------|
| Does it apply? | **near-miss decoy:** looks like the case but asks a different question. **Far decoy:** unrelated | not_governed | by construction | train and test |
| Follows | exact match; restyle (surface changes only); stronger (*a fortiori*); trap (a `would_not_change` item applied) | follows | by construction | train and test |
| Flips | minimal pair: one `would_change` condition applied, everything else held fixed | flips | by construction | train and test |
| Distinguished | authority mismatch (the agent lacks the case decider's authority); an unnamed difference that decides | distinguished | authority mismatch by construction; others by the author | train and test |
| Hard | mixed differences pulling both ways; a dispositive fact missing from the trace; true analogy from a held-out domain | any, as labeled | the author | mostly test |

**Which case is served.** Among examples where the case governs, about 80% get the case the scenario was built from. The other 20% get a *revised* case, an edited copy whose answer differs by construction. Training on revised cases teaches the model to follow the case it is served rather than a memorized answer. Decoys make up about 15% of all examples. These shares are starting values, to be tuned on a pilot.

**Balance rules.**

- Within each similarity band, include both outcomes. Build trap and flip scenarios as pairs from the same base scenario, so the only difference is whether the changed fact matters.
- No gold relation exceeds about 45% of governed examples, so copying the case's verdict cannot win.
- Option position and length, the number of actions, and the number of supporting facts must not predict the correct answer.
- Golds that hand the decision to a human stay a minority. Golds that require an irreversible action are common enough that timidity doesn't pay.

**Splits.**

- Whole cases are held out, with all their variants, because variants share a case and would leak.
- One whole domain is held out, for the true-analogy test.
- Author-labeled hard scenarios are mostly reserved for testing.
- Near-miss decoys appear in both training and test.

## 3. Stage 1: Supervised fine-tuning

**Input.** The trace, the equities and the case. All three are masked; no loss is taken on them.

**Target.** The model's own reply: facts enumeration → facts mapping → consideration mapping → reasoning → verdict. On a decoy, the target stops after the facts mapping, with `fit: poor` and `relation: not_governed`.

**Gold replies.** The base model generates them. It is given the trace, the case and the labels known by construction:

- the gold relation;
- the gold option;
- the changes planted in the scenario.

A reply is kept only if it passes the format verifier and the reward checks below: the gate, the right action, the right relation, and the planted differences found. This is label-conditioned generation in the manner of STaR (Zelikman et al., 2022). Because the targets come from the model's own outputs, the model forgets less than when trained on another model's text (*Retaining by Doing*, 2025).

## 4. Stage 2: RLVR

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

  Scoring uses the case-side IDs, which are stable. Live-only facts and de novo considerations are not scored, because the model names them itself.
- **calibration:** the Brier score, −(confidence − correct)².
- **G, the gate:** 1 if all of the following hold, else 0:
  - the YAML parses;
  - every case fact and consideration is accounted for;
  - the relation agrees with the choice. A `follows` must carry out the case's choice through the options map, and a `flips` must name a `would_change` item whose answer matches.

The prose is taught by SFT and never scored by RL, so the reward cannot teach the model to dress up its reasoning for a grader.

![Figure B. The experiment grid. Training sees only the three right-hand conditions; the two left-hand conditions are evaluation-only baselines.](fig/c2-eval-grid.png){width=6.5in}

## 5. Evaluation

Every held-out test scenario runs in every cell of Figure B. Results are reported separately for each scenario family and for the held-out domain.

**Primary metrics:**

- action accuracy on held-out scenarios the case governs;
- the share of decoys correctly declared `not_governed`;
- the share of governed scenarios wrongly declared `not_governed`, which measures whether declining has become an escape hatch.

**Secondary runs**, on the final model only:

- the relevant case served without equities;
- the case with its prose judgment stripped;
- a library built on a different value set, which tests pluralism and whether national-security values leaked into the weights.

**One falsifier needs rewording.** Because reasoning stops at `not_governed`, decoy performance is now measured by whether the model declines, not by its downstream decision. Falsifier 3 becomes: *the trained model treats decoys as governing, or calls governed cases `not_governed`, at a meaningful rate.*

## 6. Open items

- **Calibration needs a field.** The verdict schema has no `confidence` field. Add one, or drop the calibration term.
- **Penalty values.** The −1, −2 and −0.1 values are starting points, to be tuned on the pilot. The constraint that matters is that a false `not_governed` is never cheaper than a wrong verdict.
- **The label budget for the distinguished and hard families.** These are the most valuable test items and the scarcest training labels.
