---
title: "The Benchbook — Evaluation (section for the research plan, v1)"
subtitle: "1 October 2026"
---

# Evaluation

Every model version answers the same frozen set of held-out scenarios under the same card conditions. Each answer is scored by the same code that computes the RL reward, so training and evaluation measure the same thing, and the comparisons are paired: the same items across models. Separately, every model runs a fixed suite of general capability and safety benchmarks, to show what the training cost.

![Figure E1. The evaluation pipeline. All runs go through UK AISI's Inspect.](fig/t4-eval.png){width=6.5in}

## The evaluation grid

Each held-out scenario runs through every cell:

| Model | No card | Right card | Revised card | Decoy |
|---|---|---|---|---|
| Untrained | baseline | do cases help on their own? | does it follow the card it is given? | is it misled? |
| After SFT | same four conditions | | | |
| After SFT + RL | same four conditions | | | |

**The headline statistic is a difference-in-differences:**

**card-use gain = (trained, right card − trained, no card) − (untrained, right card − untrained, no card)**

It measures how much training increased the value of having the precedent in hand. It separates the claim, "the model got better at reasoning from precedent," from the weaker "the model got better in general."

## Test data

- **Held-out cases.** The split is by case, not by scenario. Whole cases, with all their variants and cards, never appear in training, because variants of one case share a card and a random split would leak answers.
- **Variants of each held-out case.** Four types are labeled by construction:
  - restyle and stronger, where the card's answer carries;
  - trap, where a difference the card already weighed does not change the answer;
  - flip, where a difference the card says would change the answer is present.

  Two more types carry the author's own labels and are reserved mostly for evaluation:
  - novel, with unanticipated differences;
  - cross, where another case's card is served.

  These are the closest thing to a true out-of-distribution test.
- **Card conditions.** Each scenario is served the right card, a revised card (an edited copy whose answer differs by construction), an off-topic decoy, or no card.
- **Sealed before training.** The 13 hand-built example cases are evaluation-only. The full test set is frozen and hashed before any training run begins. A separate development split is used for checkpoint selection during training; the test set is scored once, at the end.

## Ablations

| Ablation | What changes | The question it answers | Status |
|---|---|---|---|
| Training stage | untrained · SFT only · SFT + RL · RL only | what each stage contributes; whether RL is needed at all | core |
| Card condition | none · right · revised · decoy | whether the model uses the card it is served, rather than a memorized answer, and is not misled by an irrelevant one | core |
| Card form | full card · spine only (prose judgment stripped) · prose only (no structured fields) | whether the prose judgment or the structured spine does the work | full and spine core; prose-only to build |
| Reward | the full reward vs. the gate term alone | whether gains come from the reasoning reward or merely from learning the output format (RL can improve a model even with format-only or random rewards; Shao et al., 2025) | core control |
| Model family | Granite 4.2 8B (primary) vs. Qwen3.5-9B | whether the result is specific to one model | core: untrained and SFT + RL |
| Training mix | trained with vs. without revised and decoy cards in the training data | whether the control conditions must be trained on, or only evaluated | optional |
| Injection role | card delivered as a user-role vs. system-role message | whether the trained behavior depends on where the card sits | optional, evaluation only |

The prose-only condition has no consideration IDs to compare against, so it is scored on the action alone.

## Metrics

**Primary metric: choice accuracy.** This is the share of items where the model's tool calls match the gold option, on held-out cases. It is reported for every cell of the grid, and the headline card-use gain is computed from it.

**Secondary metrics.**

| Metric | Definition |
|---|---|
| Wrongful irreversible rate | share of items where the model takes a wrong action that cannot be undone |
| Hand-up rate vs. gold | how often the model hands the call to a human, against how often the author would; guards against "always escalate" |
| Revised-card following | under a revised card, the share of items where the action follows the revision |
| Decoy robustness | accuracy under a decoy compared with no card (it should not fall), and the share of decoys the model rates as a poor fit |
| Relation accuracy | whether the model names the relation to the precedent correctly: follows, flips, distinguished, or not governed |
| Difference recall | the share of planted differences the model identifies |
| Calibration | Brier score of the stated confidence; log loss and expected calibration error are also reported |
| Gate pass rate | the share of replies that are well formed and whose tool calls do what the mapping says |
| Extra-call rate | tool calls beyond those the matched option requires; tracks the "do more to look compound" exploit |
| Full card vs. spine gap | the accuracy difference between the two card forms |

**Baselines.** Every metric is shown beside the scores of policies that do no reasoning:

- chance;
- longest option;
- most clauses;
- never act irreversibly;
- always hand up;
- copy the card's choice;
- ignore the card;
- most specific tool-call signature.

A trained model must beat these, not only its untrained self.

**What is reported.** Outcomes and individual components, never the shaped reward total, which differs by condition. Every metric is broken down by variant type, card condition and card form.

**Prose quality** is read separately, by the author or an LLM judge, for evaluation only. That reading never feeds back into training.

## General capability and safety benchmarks

Fine-tuning a post-trained model on narrow, structured data is the documented worst case for eroding prior capability and safety (Qi et al., 2023; He et al., 2024). Every model version therefore runs a fixed benchmark suite, before training and after each stage. All of these are available in `inspect_evals`, the benchmark collection that ships with Inspect.

| Benchmark | What it measures | Scoring | Why it is here |
|---|---|---|---|
| IFEval | instruction following | deterministic | the most common casualty of late fine-tuning on list-like formats |
| MMLU-Pro | knowledge and reasoning (10-option multiple choice) | deterministic | general capability, less saturated than MMLU |
| BFCL (Berkeley Function-Calling Leaderboard) | general tool and function calling | deterministic | our model acts through tool calls; training must not damage tool use outside the Benchbook |
| AgentDojo | robustness of tool-using agents to prompt injection | deterministic | the card arrives as an injected message; training to weigh injected material must not make the model obey injected instructions elsewhere |
| StrongREJECT | compliance with harmful requests under jailbreaks | LLM grader | safety erosion |
| XSTest | over-refusal of safe requests | LLM grader | guards against the opposite failure: becoming timid |
| AgentHarm (harmful and benign sets) | harmful multi-step agentic tasks, with a benign control | LLM grader | agent-specific safety, since the model acts through tools |

The graded benchmarks use one fixed grader model and version for every run, so the arms are compared on equal terms. Long benchmarks may run on a fixed, seeded subset if time requires; the subset is the same for every model.

## The harness: UK AISI's Inspect

All evaluations run in Inspect, the open-source evaluation framework built by the UK AI Security Institute and maintained with Meridian Labs (MIT license). It is used for safety evaluation by government AI institutes.

**How the Benchbook maps onto it.**

- **Samples.** Each test item is a Sample: a live scenario plus a card condition, tagged with its case, variant type, condition and whether the gold option is irreversible.
- **Solver.** It builds the input exactly as in training, assembling the agent trace and injecting the card (full, spine or prose) or nothing.
- **Model.** It is served by vLLM: the frozen base weights with each checkpoint's LoRA adapter on top, so every model version runs on one server.
- **Scorer.** A thin wrapper around `mvp.py reply-score`, the same function the RL trainer calls. It returns the gate result, the option matched, and each component.

**What Inspect provides.**

- One command runs every model across every condition, and it resumes if interrupted.
- Every reply is logged with its scores and tags.
- Outputs can be re-scored without regenerating, which matters while the scorer is still being refined.
- A log viewer lets the author read replies side by side.
- Per-sample results export to a dataframe for analysis.
- Case-clustered standard errors are built in.

**What we build ourselves.** The paired, case-resampling bootstrap for comparing models, a short script on the exported results. Package versions are pinned for reproducibility.

**One scoring package, two callers.** The parsing, solving and scoring code is a single plain Python package. Inspect calls it for evaluation and TRL's GRPO trainer calls it for the reward, so training and evaluation cannot drift apart.

## Statistics

- **Paired comparisons.** Every comparison uses the same items across models and conditions.
- **Case-clustered intervals.** 95% confidence intervals come from a bootstrap that resamples whole cases, because variants of one case are not independent evidence. Statistical power therefore depends mainly on the number of held-out cases; that number is set by a power analysis on pilot results.
- **Repeated samples.** Each item is sampled about four times at the model's recommended settings, and accuracy is averaged, which reduces noise and measures consistency.
- **Pre-registered margin.** Before training, we fix what counts as "no better": the 95% interval of the paired difference includes zero, or the gain is under 3 points.
- **Noise floor.** The untrained model is run twice, and the run-to-run spread sets the noise floor the margin must clear.
- **Multiple comparisons.** The falsification tests are corrected with the Holm–Bonferroni method.

**When evaluations run.**

1. Before any training, on the full grid, twice.
2. After SFT.
3. During RL, on the development split only, to select checkpoints and catch drift.
4. Once at the end, on the frozen test set.

The benchmark suite runs at every stage.

## What would falsify the hypothesis

**The hypothesis.** The right precedent case, served at the decision point to a model trained to reason from it by analogy, yields a more aligned choice than either the case alone or the training alone.

These outcomes, judged against the pre-registered margin on held-out cases, would count against it:

| If this happens | We conclude |
|---|---|
| The trained model with the right card is no better than the untrained model with the right card | training adds nothing to the use of precedent |
| The card-use gain is not above zero | training improved the model generally, not its reasoning from precedent |
| The trained model with the right card is no better than itself with no card | the case adds nothing once the model is trained |
| Its action does not follow revised cards | it runs on memory or habit, not on the card it is served |
| Decoys lower its accuracy compared with no card | irrelevant precedent misleads it |
| It does not beat the copy-the-card or most-specific-signature baselines | its gains are shortcuts, not reasoning |
| The gate-only reward control comes within the margin | the gains come from learning the format, not from the reasoning reward |
| Its wrongful irreversible rate rises above the untrained model's | distinguishing has become an escape hatch |
| It loses more than 3 points on any capability benchmark, or becomes measurably less safe beyond the noise floor | the skill costs more than it adds |

**What would limit the claim without falsifying it:**

- **Novel and cross scenarios.** If the gains hold on by-construction variants but not on these, the model follows and flips precedent but does not extend it.
- **The spine matches the full card.** Then the prose judgment adds nothing, and the claim is about structure, not prose.
- **The result does not replicate on Qwen3.5-9B.** Then it may be specific to one model family.
- **SFT alone matches SFT + RL.** That shows RL is unnecessary for this skill, but it does not count against the hypothesis.

## References

- UK AI Security Institute. Inspect. [inspect.aisi.org.uk](https://inspect.aisi.org.uk/)
- UK AI Security Institute. Inspect Evals. [ukgovernmentbeis.github.io/inspect_evals](https://ukgovernmentbeis.github.io/inspect_evals/)
- Zhou et al. (2023). Instruction-following evaluation for large language models (IFEval). [arXiv:2311.07911](https://arxiv.org/abs/2311.07911)
- Wang et al. (2024). MMLU-Pro. [arXiv:2406.01574](https://arxiv.org/abs/2406.01574)
- Patil et al. (2025). The Berkeley Function Calling Leaderboard (BFCL). [gorilla.cs.berkeley.edu/leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- Debenedetti et al. (2024). AgentDojo. [arXiv:2406.13352](https://arxiv.org/abs/2406.13352)
- Souly et al. (2024). A StrongREJECT for empty jailbreaks. [arXiv:2402.10260](https://arxiv.org/abs/2402.10260)
- Röttger et al. (2024). XSTest. [arXiv:2308.01263](https://arxiv.org/abs/2308.01263)
- Andriushchenko et al. (2025). AgentHarm. [arXiv:2410.09024](https://arxiv.org/abs/2410.09024)
- Qi et al. (2023). Fine-tuning aligned language models compromises safety. [arXiv:2310.03693](https://arxiv.org/abs/2310.03693)
- He et al. (2024). What is in your safe data? [arXiv:2404.01099](https://arxiv.org/abs/2404.01099)
- Shao et al. (2025). Spurious rewards: rethinking training signals in RLVR. [arXiv:2506.10947](https://arxiv.org/abs/2506.10947)
