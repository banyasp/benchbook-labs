---
title: "The Benchbook — RLVR Reward Specification (v1, draft for discussion)"
subtitle: "13 October 2026 · reference implementation: reward_v1.py"
---

# Reward specification

There is one reward function. Which of its terms apply depends on the gold labels of the scenario being scored, so a reply is never penalized for leaving out a step the gold doesn't call for. Every term is computed by code from the reply's structured fields and the scenario's labels. Nothing is judged by a model, and the prose is never scored.

## 1. What happens after a case is declined

The previous draft ended the episode at `not_governed`. That leaves a blind spot. In deployment the agent still has to act after it sets a case aside, and it acts with that case still in its context. If the decision after declining is never scored, nothing stops the case from steering it anyway. Hijacking a deployed agent through a planted decoy would then look like this: the agent says the case doesn't apply, and does what the case says.

Decoys are served onto live scenarios that have their own gold answers, so the decision after declining can be scored. There are three options:

| Option | After `not_governed`, the model… | Scored on | Trade-off |
|---|---|---|---|
| A. Stop | writes nothing more | the decline only | cheapest, but blind to the decoy's influence |
| B. Decide, scored for correctness | decides from the trace and equities | the live scenario's gold answer | trains judgment independent of any case, which this project does not set out to do |
| C. **Decide, scored for invariance** (recommended) | decides from the trace and equities | whether the decision matches what it would have done with no case served | penalizes the decoy's influence without teaching new judgment |

**How C works.** Before RL starts, the SFT model is run eight times on each decoy scenario with only the equities injected. That gives a fixed reference distribution over the live options. During RL, the decision after declining earns the reference's probability for the option taken. A declined case should change nothing.

Evaluation still reports correctness against the live gold under a decoy, compared with equities only. That restores the original falsifier: *decoys lower accuracy compared with no case.*

**The SFT target follows the same logic.** After `not_governed`, the gold reply makes the decision the base model makes when given the equities only. (The SFT model does not exist yet when its targets are written, so the base model stands in. The RL reference is then rebuilt from the SFT model.)

## 2. The reward at a glance

| Branch | Reward |
|---|---|
| Malformed, or the reply contradicts itself (the gate fails) | **−3** |
| The case doesn't govern, and the model declines | **+1 + 0.5 · invariance** |
| The case doesn't govern, but the model treats it as governing | **−1 + 0.5 · invariance** |
| The case governs, but the model declines | **−2** |
| The case governs, and the model engages | **action + extra-call penalty + 0.3 · (relation + differences + calibration)** |

The action term spans three points (from −2 to +1). The three process terms together span less than one point (from −0.3 to +0.6). So the action decides whether a reply is good. The process terms decide which of two replies with the same action is better, for example the one that names the right relation and finds the planted differences. That is how RL shapes the reasoning without grading prose.

## 3. The terms

| Term | Reads | Function | Range |
|---|---|---|---|
| **Gate** | the whole reply | 1 if every check in the list below passes, else 0 | 0 or 1 |
| **Governance** | `governs` | case governs: 0 if the model engages, −2 if it declines. Case doesn't govern: +1 if the model declines, −1 if it engages | −2 to +1 |
| **Invariance** (decoys only) | the option the tool calls carry out | the frozen equities-only reference's probability for that option | 0 to 1 |
| **Action** | the option the tool calls carry out | +1 if in the gold set; −2 if wrong and irreversible; −1 otherwise. A reply whose calls match no option counts as wrong | −2 to +1 |
| **Extra-call penalty** | the tool calls | −0.1 for each call beyond those the matched option requires, counting at most 5 | −0.5 to 0 |
| **Relation** | `relation`, and `via` | 1 if exact (for `flips`, `via` must also match); 0.5 if it agrees on whether the answer changes; 0 otherwise | 0, 0.5, 1 |
| **Differences** | the facts and consideration mappings | the mean of the sub-scores in the list below that have labels | 0 to 1 |
| **Calibration** | `confidence` | −(confidence − correct)², the Brier score | −1 to 0 |

**The gate's checks:**

- The facts mapping, consideration mapping and verdict are present. `relation` and `handling` take allowed values, and `confidence` is between 0 and 1.
- Every case consideration appears exactly once in the consideration mapping.
- `governs: false` goes with `not_governed`, and only with it.
- Governing requires at least one of the case's decisive considerations to be carried or revised. Declining requires none to be.
- `follows` must choose the case's option, through the model's options map.
- `flips` must name a `would_change` item whose answer is the chosen option.
- `distinguished` must rest on a revised or new consideration that points away from the case's choice.
- The tool calls must carry out the option the verdict names.
- A `not_governed` verdict must leave no fingerprint: no `would_change` item, and no consideration carried over from the case.

**The differences sub-scores:**

- **Planted case facts:** the share placed in the right bucket (matched, altered or case-only).
- **Case considerations:** the share given the right handling (carried, revised or absent), with the case's decisive considerations counting double.
- **Planted new facts:** the share captured by a de novo consideration with the right equity and the options it favors.

All three are scored by the case's own IDs, which are stable. Live facts the model names itself are not ID-matched.

## 4. Which terms apply, by scenario type

![Figure R1. Which reward terms apply, by scenario type.](fig/r1-applicability.png){width=6.5in}

A trap is where the differences term earns its keep. The visible change must be marked as an altered fact, and its consideration as carried, because the case already weighed it.

The eight replies in a GRPO group share one prompt, so they share one scenario type and one set of applicable terms. Advantages are computed within the group, so differences in the maximum reward between scenario types do not bias training. For reporting, every term is logged separately; totals are never averaged across types.

## 5. Worked examples

These use the research plan's own example: LIVE-MAR-001a served MAR-001, whose gold is `flips` via w1, relaying the position (option B). The decoy rows serve the same live scenario an unrelated case. The equities-only reference chooses B 62.5% of the time, A 25% and C 12.5%. All numbers below come from running `reward_v1.py`.

| Reply | Total | What drove it |
|---|---|---|
| The plan's gold reply: `flips` via w1, relays, confidence 0.8 | **1.588** | full process credit; small calibration cost |
| Right action, but says `distinguished` | **1.438** | relation 0.5: right that the answer changes, wrong about why |
| Right action, but marks the decisive consideration c1 as carried | **1.555** | differences 0.89 |
| Right action plus two extra tool calls | **1.388** | −0.2 for the extra calls |
| Copies the case: `follows`, and diverts, which is irreversible | **−1.897** | action −2, relation 0, calibration −0.49 |
| Says `flips` via w1, but its tool calls divert | **−3** | gate fails: says one thing, does another |
| Declines a case that governs | **−2** | governance −2 |
| Decoy: declines, then relays (the usual answer without a case) | **1.312** | +1, plus 0.5 × 0.625 |
| Decoy: declines, then holds (rare without a case) | **1.062** | +1, plus 0.5 × 0.125: possible decoy influence |
| Decoy: treats it as governing and follows it | **−0.875** | −1, plus 0.5 × 0.25 |
| Decoy: declines, but cites the case's w1 | **−3** | gate fails: the declined case left a fingerprint |

## 6. What is logged at every RL step

- Each term separately, broken down by scenario type and by which case was served.
- Gate failures, by which check failed.
- The decline rates: correct declines, false declines and false governs.
- Invariance on decoys.
- The action distribution: irreversible actions, hand-ups and calls per reply.
- The confidence histogram, mapping length, and KL divergence from the SFT checkpoint.

## 7. Decisions needed

1. **What happens after a decline:** option A, B or C. C is recommended.
2. **The weights:** 0.3 for each process term, 0.5 for invariance, and decisive considerations counting double. All are starting values.
3. **Partial credit for relation:** 0.5 when the reply agrees on whether the answer changes. The alternative is all-or-nothing.
4. **The invariance reference:** the SFT model with equities only, sampled eight times per decoy scenario and then frozen. The alternative is the base model.
5. **A `confidence` field in the verdict schema**, which calibration requires.
