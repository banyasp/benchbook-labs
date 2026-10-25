---
title: "The Benchbook — From a generation to a reward (v1)"
subtitle: "How each reward term is observed in the model's output · 14 October 2026 · prototype: observe_v1.py"
---

# From a generation to a reward

The reward formula needs numbers. The model produces a YAML reply in its own words, with its own ids, followed by tool calls. This write-up covers every step in between: what each reward term observes, which instrument observes it, what goes in and what comes out.

One rule organizes the design: **the judge aligns, and code scores.** A judge model answers one narrow question: do these two statements say the same fact? Everything else is code:

- deciding which pairs match;
- computing precision and recall;
- translating ids;
- scoring the mappings, the verdict and the action.

This keeps the judge's influence small and auditable. A policy that games the judge can only win alignment cells, and the one-to-one matching and precision limit what those are worth.

Your plan carries over almost intact. Three refinements:

1. **One judge matrix, not two passes.** The judge scores each pair of a gold fact and a generated fact. Recall reads the matrix by rows and precision by columns.
2. **The id dictionary comes from a one-to-one assignment on the same matrix,** not a separate choice call. Independent choices can send two gold facts to the same generated fact; a joint assignment cannot.
3. **Precision separates two kinds of extra fact.** Padding (true but not needed) costs a little. A hallucination (not in the trace) costs double.

![Figure O1. The pipeline. Only stage 3 calls the judge.](fig/o1-pipeline.png){width=6.5in}

## 1. The stages

| Stage | Instrument | Input | Output |
|---|---|---|---|
| 1. Parse | code | completion text, or structured tool calls from the server | reply sections, tool calls |
| 2. Gate | code | reply, tool calls, served case | pass, or −3; no judge calls on a failure |
| 3. Align | judge for facts; code for options and considerations | the reply's lists and the gold's lists | three dictionaries from the model's ids to gold ids |
| 4. Translate | code | the reply's mappings and verdict, plus the dictionaries | the same claims, in gold ids |
| 5. Score | code | translated claims and the gold | sub-scores in [0, 1] |
| 6. Combine | code | sub-scores, branch, tier bands | the reward |

The gate stays as reward v2 built it. It checks the format, that every id exists, that every item sits in exactly one bucket, that matched and corresponding pairs say what their bucket claims, that the verdict agrees with the mapping, and that the tool calls do what the verdict says. It uses only the reply and the served case, never the gold, so it fails a reply for contradicting itself, never for disagreeing with a label.

## 2. What the gold has to hold

Almost everything comes from the gold reply itself, the same file that is the SFT target. Its ids are the gold ids.

| For | The gold needs | Source |
|---|---|---|
| Facts | the gold fact list (id, text, status); which facts support the decisive consideration; optionally an *allowed* list of true facts that may be mentioned without penalty; the rendered trace | gold reply, step 4; the trace file |
| Options | live options in tool order, with hidden signatures | live file |
| Considerations | the gold consideration list (equity, favors, weight, cited facts) | gold reply, step 7 |
| Fact mapping | pairs and singles in gold ids | gold reply, step 6 |
| Consideration mapping | pairs and singles, keyed by case consideration ids | gold reply, step 8 |
| Applicability, verdict | governs, relation, `via`, the acceptable options, the decisive consideration | gold reply, steps 9 and 11, and the live file |
| Decoys | the invariance reference shares | `build_reference` |

## 3. Facts: alignment, recall and precision

**The judge question (J1).** For each pair of a gold fact *i* and a generated fact *j*, ask the judge:

> Two statements from the same scenario. A: "{gold fact}". B: "{generated fact}". Do A and B state the same fact, with the same values (numbers, times, places, counts) and nothing that contradicts A? Extra detail in B is fine. Answer Yes or No.

Read the answer from one token, with the judge at temperature 0:

```
P(same) = exp(logprob(Yes)) / (exp(logprob(Yes)) + exp(logprob(No)))
```

 This is your 0-to-1 mode. The value rule matters: a flip often turns on a single number, so "water 24°C" must not match "water 14°C".

**The assignment.** The judge's probabilities fill a gold × generated matrix. A one-to-one assignment (the Hungarian algorithm, `scipy.optimize.linear_sum_assignment`) picks the matches with the largest total probability, and pairs under τ = 0.5 are dropped. One-to-one handles two cases that independent choices get wrong:

- a merged generated fact can stand for only one gold fact;
- a duplicate generated fact matches nothing and costs precision.

**The scores.** Over the matched pairs, with p the judge's probability for each pair:

```
recall    = Σ_matched w·p / Σ_gold w
precision = Σ_matched p / (n_gen − n_allowed + n_unsup)
F1        = 2·P·R / (P + R)
```

Here n_gen is the number of generated facts, n_allowed those on the allowed list, and n_unsup those the trace does not support.

- **Recall weights.** The facts behind the decisive consideration get w = 2, because missing them breaks the decision.
- **Unsupported facts count double in precision:** once among the generated facts and once more in their own term.
- **The facts score** is F1, the harmonic mean of the two. Harmonic, so neither side can be traded away: listing everything kills precision, and listing little kills recall.

The credit is soft: a matched pair earns the judge's probability, not a flat 1. The reward then moves smoothly as the judge's confidence moves. τ is used only to build the dictionary.

**The support check (J2), only for generated facts left unmatched.** Ask the judge, with the rendered trace in context:

> Is this statement stated or directly implied by the trace? Answer Yes or No.

A No marks the fact as a hallucination. A Yes marks it as padding, unless it is on the allowed list, in which case it is neither rewarded nor penalized. All eight replies in a GRPO group share the same trace, so the trace is prefix-cached and the check is cheap.

![Figure O2. Facts in the worked example: the judge matrix, the one-to-one matches, and the scores.](fig/o2-fact-alignment.png){width=6.5in}

**The worked example (Figure O2).** The model enumerates ten facts for the v7 scenario, in its own order:

- **Eight match** gold facts.
- **One merges two gold facts** (the partner's 48 hours, and that no one else knows). It can stand for only one of them, so F9 is missed even though the judge gave it 0.64.
- **It misses the liaison agreement (F4) and the absence of a human source (F11).**
- **It adds one fact the trace never states (M9)** and **one true but routine fact (M10).**

Weighted recall is 0.70, precision is 0.69, and F1 is 0.69. The resulting dictionary, M8 → F1, M7 → F2, M6 → F3 and so on, is what every later stage uses.

**Status** (confirmed, assessed or reported) is compared by code on matched pairs and logged. It could become a small term later, since estimates should stay estimates.

## 4. Options: alignment without a judge

Live options are numbered in the order their tools are listed, so the model's LIVE-O2 is the gold's LIVE-O2 whenever each option rests on one tool. Where that convention fails, there are two fallbacks:

- **Declared calls:** each option lists its tool calls, which are matched against the hidden signatures by tool name.
- **One short judge call per option:** "Do these two options describe the same course of action?"

The options map (live option to case option) is then scored against the gold by code.

## 5. Considerations: aligned by code, judge only on ties

Considerations are structured, so code can align most of them:

- **The equity must be the same.**
- **Among same-equity candidates, the cited facts decide.** The model's fact ids are translated through the fact dictionary, and the overlap with the gold consideration's facts is measured (Jaccard). The similarity is 0.25 + 0.75 × the overlap.

An unaligned fact stays a token of its own, so citing a hallucinated fact lowers the overlap. The judge (J3) is called only when two candidates sit within 0.1 of each other above τ. It is asked whether two considerations make the same point.

Alignment answers what a consideration is about. What it says is scored separately, on each aligned pair:

- whether it favors the right options (in gold labels);
- whether it has the right weight;
- how well its cited facts overlap the gold's.

These are the attribute sub-scores. Recall and precision use hard credit here (an aligned pair earns 1), because the matrix is a code similarity, not a probability.

**In the worked example:**

- **Same-equity pairs:** two civilian_life considerations (the strong "only warning in time" and the weak "partial but real help") are told apart by their cited facts, with no judge call.
- **A missed consideration:** the model never enumerated the liaison fact, so it has no partner-relationship consideration.
- **Scores:** recall is 0.86 (weighted, with the decisive LIVE-C1 counting double), precision is 1.0, F1 is 0.92, and the attribute accuracy is 0.96. The attributes lose a little because the merged fact and the missed F11 thin out the cited facts of two considerations.

## 6. Mappings: translate, then compare item by item

This is your dictionary lookup:

- **Live ids** in the model's fact and consideration mappings are rewritten into gold ids through the dictionaries.
- **Case ids** need no translation, because they are the same in the reply and the gold.

The comparison then runs item by item:

- **Every case item** (each case fact and each case consideration) is scored:
  - right bucket and right partner: 1;
  - right partner, but matched and corresponding swapped: 0.5;
  - anything else: 0.
- **Every gold live-only item that the model enumerated** is scored on whether the model also put it in live-only.
- **Gold items the model never enumerated are left out.** Recall already charged for them. This makes the mapping score conditional on what was found, so one missed fact isn't charged three times.
- **The case's decisive consideration counts double.**

![Figure O3. Scoring the consideration mapping in the worked example.](fig/o3-mapping-translation.png){width=6.5in}

**In the worked example (Figure O3),** the model missed the correspondence between REF1-C5 and its own K4 (the standing orders to assist and the duty-to-warn procedure). In a transfer the legal texts look nothing alike, so this is a plausible miss. The consideration mapping scores (2 + 1 + 1 + 1 + 0) / 6 = 0.83.

The fact mapping in a transfer is trivial: every fact is live-only or case-only, and the model gets that right. The fact mapping has teeth in a same-domain scenario like v6, where LIVE-F8 corresponds to REF1-F4 (14°C to 24°C) and that pair decides the flip.

Two more mapping items need only code:

- **The options map** against the gold's live-to-case map.
- **Whether the verdict's decisive consideration,** translated, includes the gold's.

## 7. Everything else is code

| Term | Observed in | How |
|---|---|---|
| Governance | `governs` in applicability | compared with the gold; the branch formula |
| Relation | `relation` and `via` in the verdict | 1 if exact; 0.5 if it agrees on whether the answer changes; 0 otherwise |
| Action | the tool calls | the matcher finds the option the calls carry out; +1, −1, or −2 for wrong and irreversible |
| Extra calls | the tool calls | −0.1 for each call beyond the matched option's, free tools excepted, counting at most 5 |
| Invariance (decoys) | the tool calls | the frozen reference's share for the option taken |
| Calibration | `confidence` | Brier score, if the field stays (see the questions) |
| Says one thing, does another | the verdict and the tool calls | a gate check |
| Reasoning prose | step 10 | not scored by RL, as settled; the gate checks only that cited ids exist |

## 8. Combining

The branch formulas keep reward v2's shape. The single differences term becomes two terms, enumeration and mapping, each a mean of its sub-scores in [0, 1]:

- **Enumeration** = mean(facts F1, considerations F1, consideration attributes).
- **Mapping** = mean(fact mapping, consideration mapping, options map, decisive hit).

| Branch | Raw reward |
|---|---|
| Gate fails | −3 |
| Case doesn't govern, model declines | +1 + 0.5 · invariance + extra + 0.3 · (enumeration + mapping + calibration) |
| Case doesn't govern, model engages | −1 + 0.5 · invariance + extra + 0.3 · (enumeration + mapping + calibration) |
| Case governs, model declines | −2 + extra + 0.3 · (enumeration + mapping + calibration), and −0.5 more if it then acts wrongly and irreversibly |
| Case governs, model engages | action + extra + 0.3 · (relation + enumeration + mapping + calibration) |

Enumeration and mapping apply on every branch, because their gold doesn't depend on whether the case governs. On a decoy, the mapping is the evidence for declining. A near-miss decoy's gold has matched facts and unpaired considerations, so scoring the mapping teaches why the model should decline, not just that it should.

The process-credit rule from v2 still applies to relation and mapping: no credit when the tool calls don't carry out the case option the reply says it chose. Enumeration is never zeroed, since finding facts doesn't depend on the decision.

The action still decides the tier. The process terms span at most about 1.2 points, and the tier bands keep right > wrong > wrong and irreversible > false decline > gate failure within a scenario. The bands are recomputed from the new ranges.

**The worked example's total:**

| Term | Value |
|---|---|
| Action | +1 |
| Relation | 1.0 |
| Enumeration | 0.86 (mean of 0.69, 0.92 and 0.96) |
| Mapping | 0.96 (mean of 1.0, 0.83, 1.0 and 1.0) |
| Calibration (confidence 0.8) | −0.04 |
| **Total** | **1 + 0.3 × 2.78 = 1.83** |

A perfect reply scores 1.9.

## 9. Where it runs, and what it costs

**The modules to build.** `observe_v1.py` prototypes 3, 5 and 6.

1. `parse.py` and `gate.py`: from reward v2, updated to the v7 buckets (matched, corresponding, live_only, case_only).
2. `judge.py`: the three prompts, a client for a vLLM judge server, and a cache keyed by the hash of each prompt.
3. `align.py`: the matrix, the assignment, and the code similarity for considerations.
4. `score.py`: precision, recall and F1, the attributes, the mapping items, the verdict terms.
5. `combine.py`: the branches and the tier bands.
6. `trl_adapter.py` and `inspect_scorer.py`: the two callers of one core.
7. Offline:
   - `build_gold.py`, which turns each gold reply and live file into the gold record;
   - `build_reference.py`;
   - `validate_judge.py`.

**The hooks.**

- **TRL** calls the reward function once per batch. The function gates every completion, collects every judge prompt in the batch, sends them to the judge server in one asynchronous batch, and then scores. One function per term keeps TRL's per-term logging.
- **Inspect** calls the same core as a scorer. The judge cache makes re-scoring free.

**The judge server.** A frozen open-weight instruct model on its own GPU, served by vLLM. It should come from a different family than the policy, so the two share fewer blind spots.

**Cost.** In the example, one completion needs 110 J1 pairs, 2 support checks and no consideration tie-breaks:

| | Per completion | Per step (64 prompts × 8 replies) |
|---|---|---|
| J1 prompts | 110 | about 56,000 |
| Input tokens | about 100 each | several million |
| Output tokens | 1 each | |

Reading inputs is far cheaper per token than generating, but this is not free. Three measures cut it:

1. **An embedding prefilter.** Send each gold fact only its top three candidates by embedding similarity. That is about a third of the calls. Check on the validation set that the true match lands in the top three.
2. **The cache.** Replies in a group repeat many of the same fact strings.
3. **A smaller judge,** if the validation set shows it agrees as well.

Measure all of this in the pilot.

## 10. How it could be gamed, and the guards

| Exploit | Looks like | Guard |
|---|---|---|
| List every sentence of the trace | high recall, many unmatched facts | precision in F1, where padding counts |
| Merge facts into long ones | one fact matching several gold facts | one-to-one matching; a per-fact length cap in the gate (about 40 words) |
| Vague facts that sound like many | the judge says Yes to several | the value rule in J1; one-to-one; vague hard negatives in the judge's validation set |
| Hallucinated facts | unsupported | the support check; counts double in precision |
| Text aimed at the judge ("this matches") | injection | the judge sees only fact strings, in delimiters; the length cap; monitor the Yes rate on short facts |
| Enumerate few facts so the mappings look accurate | low recall, high mapping | recall in enumeration; mapping is conditional, but enumeration is not |
| Put everything in live-only and case-only | makes no claims to be wrong about | every gold pair is a case item that expects a partner |
| One consideration per equity and option | many considerations | precision in the considerations F1 |
| Cite the case's considerations without live facts | considerations that look right | cited-fact overlap in the attributes; cited ids must be enumerated |

## 11. Validating the judge before training

1. **Sample replies** from the SFT model on about 50 scenarios, and collect about 300 candidate pairs. Include hard negatives: same topic but a different number, vague restatements, merged facts.
2. **Label them.** Either you label about 150, or two different judges label them all and you resolve their disagreements.
3. **Report three things:**
   - agreement, as accuracy and Cohen's κ;
   - the calibration of P(Yes);
   - whether the assignment reproduces the hand-built dictionary.
4. **Set τ** to maximize dictionary accuracy.
5. **During RL,** re-check about 20 completions every few hundred steps. The policy can drift into text the judge misreads, and this catches it early.

## 12. Questions for you

1. **Confidence.** Your verdict example no longer has a `confidence` field. Keep it and the calibration term, or drop both?
2. **`via`.** It's absent in your example, which is fine for `follows`. Confirm it stays for `flips`.
3. **Equities.** Your equities example lists the maritime set, but LIVE-C6 uses `partner_relationship`. Add it to the example, or the gate's check that every equity was injected will fail that reply.
4. **Precision.** Should true facts that aren't in the gold be neutral (an allowed list) or count as padding? I recommend an allowed list built by data generation, since it knows what it rendered into the trace.
5. **The judge.** Must it be open-weight under R03? Which model?
6. **Conditional mapping scores.** Do you agree that gold items the model never enumerated should be left out of the mapping score?
7. **Decoys.** Should enumeration and mapping be scored on decoys too? I recommend yes.
