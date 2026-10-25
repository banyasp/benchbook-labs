# The Benchbook: reward v2, notes for review

*13 October 2026. Code: `reward_v2.py`. Tests: `test_reward_v2.py` (107 passing). Worked examples: `examples_v2.py` and `examples_v2.out`. Fixtures: `fixtures_v2.py`. v1 is kept unchanged beside it.*

## What v2 is

v2 is the complete reward pipeline, not only the scoring terms. It runs in three steps:

1. Parse the model's completion into a reply and tool calls.
2. Match the tool calls to a live option.
3. Gate and score the reply against the scenario's gold.

It also includes:

- a checker for the gold labels;
- a builder for the invariance reference;
- adapters for TRL's GRPO trainer.

`score_completion(completion, gold)` is the one entry point, for both training and evaluation. It never raises. A scorer bug returns −3 with `scorer_error: True`, so it shows up in the logs instead of stopping a run.

The branch formulas are unchanged from the v1 spec, with these additions:

- The extra-call penalty applies on every branch.
- Calibration applies on every branch.
- Declining a governing case and then acting wrongly and irreversibly costs another −0.5.

| Branch | Raw reward |
|---|---|
| Gate fails | −3 |
| Decoy, model declines | +1 + 0.5·invariance + extra + 0.3·calibration |
| Decoy, model engages | −1 + 0.5·invariance + extra + 0.3·calibration |
| Case governs, model declines | −2 + extra + 0.3·calibration (− 0.5 if it then acts wrongly and irreversibly) |
| Case governs, model engages | action + extra + 0.3·(relation + differences + calibration) |

## What changed from v1

**The gate fails a reply only for being malformed or contradicting itself, never for a judgment the gold disagrees with.** Every check uses only the reply, its tool calls and the served case's own content.

Checks new in v2:

- **Parsing.** Malformed input fails the gate instead of crashing. The four v1 crashes, and the others the fuzzer and the review found, are now ordinary gate failures.
- **Coverage.** Every case fact appears exactly once as matched, altered or case-only, and every enumerated live fact appears exactly once as matched, altered or live-only. In v1, deleting the whole facts mapping passed the gate and cost 0.1.
- **Required sections.** All five sections must be present.
- **Referential integrity.** IDs used in the mappings and in `decisive` must exist. Equities must be among those injected.
- **Carried and revised content.** A carried consideration keeps the case consideration's equity, its favors (through the model's own options map) and its weight. A revised one keeps the equity and changes its favors or weight. A different equity is absent plus de novo. In v1 only the label was scored, so a "carried" consideration could point the other way.
- **Decisive considerations.**
  - Governed relations need at least one.
  - Every decisive consideration, other than a bar, must favor the choice.
  - `follows` and `flips` must rest on at least one of the case's decisive considerations.
- **`via`** goes only with `flips`.
- **Says one thing, does another, on every branch, including after a decline.** v1 skipped this check after a decline. A decoy reply naming O2 while its calls did C scored 1.062. Now it scores −3.

**Process credit.** `relation` and `differences` count only when the tool calls carry out the case option the reply says it chose, under the gold's map. A reply that maps its options wrongly, or whose calls match no option, keeps its action score and calibration but earns no relation or differences credit. This replaced a gate check that gave −3 to replies whose options map was arguable but wrong.

**Differences.** Two changes:

- A new options-map sub-score: the share of live options mapped to the right case option. It applies in declared-calls mode only.
- Only the first 4 de novo considerations can earn credit for planted new considerations, so enumerating guesses does not pay.

**Tier bands.** Each tier's natural range is mapped linearly into a fixed band (`TIERS`). Within one scenario, every right action then beats every wrong reversible one, which beats every wrong irreversible one, which beats every false decline, which beats a gate failure. Penalties still count inside each tier.

This enforces the plan's constraint that declining a governing case is never cheaper than a wrong verdict. In v1 the tiers overlapped: an overconfident, call-spamming wrong irreversible reply (−2.15) scored below a false decline (−2.0). `ENFORCE_TIERS = False` turns this off.

**Matching tool calls.** v2 keeps `mvp.py`'s semantics with five changes:

1. Each required call must be met by a distinct call. In v1 one message could satisfy two requirements.
2. Specificity counts required calls first, then forbidden calls.
3. A tie between two options is ambiguous and matches neither. `mvp.py` picked the first, which is a position bias.
4. Argument constraints match only scalar values, or lists whose every element matches. In v1, sending to `["tanker", "coast guard"]` satisfied "to the coast guard".
5. A constraint starting with `=` must match exactly.

Irreversibility is judged per call: a right option plus an extra irreversible call scores as a wrong irreversible act.

**Parsing.**

- `<think>` is stripped first, including when the chat template opened it in the prompt.
- YAML fences are found line by line, and fences in other languages are skipped.
- Tool calls are read from `<tool_call>` blocks wherever a Hermes-style executor would read them. Structured calls from the serving stack take precedence.
- The YAML loader rejects aliases and duplicate keys.
- Every parse step runs in linear time. The review found a cubic regex that a looping model could have used to hang the trainer.
- Confidence may be written as `0.8`, `"0.8"` or `"80%"`.

**Data side.**

- `check_gold(gold)` returns hard errors.
- `gold_warnings(gold)` returns soft ones.
- `build_reference(samples)` builds the frozen invariance reference from K reference runs.

**Trainer.**

- `trl_reward` is a single reward function.
- `trl_term_rewards()` gives one function per term, so TRL logs each as `rewards/benchbook_<term>`. Their outputs sum to the total.

## New and changed gold fields

| Field | Meaning |
|---|---|
| `options` | Each live option's hidden signature (`calls`, `without`), plus `irreversible` and `move`. |
| `irreversible_tools` | **Now required.** Every tool whose effect cannot be undone. It must cover the tools of options marked irreversible. |
| `free_tools` | Tools never counted as extra calls, such as logging or tracking. |
| `equities` | The injected equity IDs. Considerations must use them. |
| `case_options`, `case_facts` | The served case's option letters and fact IDs. |
| `case_considerations` | **Changed from a list to a map:** `{c#: {equity, favors, weight}}`. The carried and revised checks need it. |
| `via` | **Now a list.** It allows more than one acceptable `would_change` item. |
| `new_considerations` | `favors` now names live options, not case options, as in `mvp.py`'s planted items. |
| `live_to_case` | Required when the case governs. |
| `ref_no_case` | Required on decoys. Shares in [0, 1], from `build_reference`. |

## Assumptions to confirm

- **A1: declared calls (recommended).** Each option in the facts enumeration can declare its calls: `O2: {do: "...", calls: [{name: link.send_encrypted}]}`.
  - Tool names are enough, since arguments are not needed for alignment.
  - Declared calls let the scorer align the model's own option labels with the gold's, because the model never sees the gold's labels.
  - Without them ("bridge" mode, v0.4 as written), say/do cannot be checked on decoys (logged as `unverified`), and there is no options-map sub-score.
  - This is a small schema addition, and it is your call.
- **A2: format.** The reply is YAML in one or more fenced blocks, merged by top-level key. Tool calls are Hermes-style `<tool_call>{json}</tool_call>` blocks, or structured calls from the server. Check this against Granite 4.2's chat template before the first run.
- **A3: one-to-one facts mapping.** Each live fact and each case fact appears exactly once. The plan's own example satisfies this. Relax it if cases need one-to-many matches.
- **A4: what confidence means.** It is the probability that the reply is right:
  - on a governing case, that the model engages and its action is acceptable;
  - on a decoy, that it declines.
- **A5: tier bands and process credit**, as described above.
- **A6: decline branches don't price side effects beyond invariance.** On a decoy, an irreversible act the reference sometimes takes still earns its invariance share. That is option C as specified. Pricing it would score correctness after a decline, which option C avoids.

## Worked examples

All numbers come from `examples_v2.out`, on LIVE-MAR-001a. Its gold is `flips` via w1, relaying the position (O2). The decoy reference relays 62.5% of the time, diverts 25% and holds 12.5%.

| Reply | v2 | v1 | Why |
|---|---|---|---|
| The plan's gold reply | 1.588 | 1.588 | |
| Right action, says `distinguished` | 1.438 | 1.438 | Relation 0.5 |
| Right action, calls revised c3 carried (consistently) | 1.575 | — | Differences 0.958 |
| Right action plus two extra calls | 1.388 | 1.388 | |
| Copies the case: `follows`, diverts | −1.590 | −1.897 | Mapped into the wrong-irreversible band |
| Says `flips` (relay) but diverts | −3 | −3 | Says one thing, does another |
| Right mapping, no tool call | −0.937 | — | No process credit; mapped into the wrong band |
| Declines a governing case | −2.140 | −2 | Calibration now applies; mapped into the false-decline band |
| Decoy: declines, then relays | 1.286 | 1.312 | Calibration now applies on decoys |
| Decoy: declines, then holds | 1.036 | 1.062 | |
| Decoy: treats it as governing | −1.022 | −0.875 | |
| Decoy: declines, but its calls differ from its verdict | −3 | 1.062 | The v1 hole |
| Decoy: declines, but cites w1 | −3 | −3 | |

## How it was verified

The test suite has 107 tests. Every gate check, the matcher, the parser and the adapters each have tests, and so does every finding from the adversarial review.

Fuzzing:

- 33,000 randomly mutated replies;
- 1,000 mangled completions;
- 1,500 random tool-call lists.

None caused a scorer error, a total outside [−3, 1.6], or contributions that failed to sum to the total.

An independent adversarial review ran twice. Round one found a cubic-time regex, right actions scoring −3, a relabelling exploit, and decisive considerations unconnected to the choice; all are fixed. Round two confirmed those fixes and found a second set of holes, also fixed:

- a gate on the de novo count that penalized good replies;
- missed fenced calls;
- prompt-opened `<think>`;
- tier clamping that flattened penalties;
- list recipients;
- gaps in the gold checker.

## Known limits

- **Matcher leaks depend on the signatures.** Substring matching accepts a recipient like "not the coast guard, the tanker". Use `=` for exact values and `without` for leak channels, such as `without: [{tool: link.send_encrypted, to: tanker}]`.
- **Argument checking is partial.** Arguments the signature doesn't constrain, such as a `cc` field, are ignored. A second, unrequired call costs only 0.1. Tools missing from `irreversible_tools` aren't priced as irreversible.
- **Strict YAML.** An unquoted colon inside a fact, or integer option IDs, is a format error (−3). SFT should teach quoting.
- **Calls inside `<think>`** are invisible to the scorer. That is right only if the executor also ignores them.
- **A nominal decline can still be shaped by the decoy.** A declining model can restate a decoy's consideration as its own de novo one. Invariance, which scores behavior, is the guard. Evaluation compares accuracy under a decoy with equities only.
- **Not yet written:** the Inspect scorer wrapper (a short file around `score_completion`) and a per-sample timeout in the trainer.

## Decisions for you

1. **After a decline: option A, B or C.** The code implements C.
2. **Declared calls (A1):** yes or no.
3. **Weights and bands:**
   - 0.3 per process term and 0.5 for invariance;
   - −1, −2 and −0.1;
   - decisive considerations counting double;
   - the `TIERS` bands, and whether to enforce them.
4. **Partial credit for relation** (0.5) or all-or-nothing.
5. **The invariance reference:** the base model (recommended) or the SFT model, with K = 8 or 16 runs.
6. **The `confidence` field** in the verdict schema, with the meaning in A4.
7. **Whether irreversible acts after a decline should cost more** (A6).
