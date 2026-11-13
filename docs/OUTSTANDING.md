# Outstanding work

*Maintained list of what is not done yet, grouped by why. Started 2026-11-11 from `context/OPERATORS-SPEC-v1.md` (v1 scope,
build status, deferred), `docs/V2-PRIORITIES.md` and Peter's rulings of 2026-11-11. Shown in the console at
`/outstanding`. Update it when an item is done (move it to "Done", with the commit) or when Peter rules on one.*

## 1. Needs a solver

These operator modes cannot set the new gold by construction: an independent solver must decide V′. They wait on the
**solver-fidelity decision** (section 4): a blind GPT-6 Luna solve agrees with the corpus verdict on only 42 of 57
anchors (74%), so a model-solved gold may depart from what a practitioner would do.

| Mode | What it is | What it would take |
|---|---|---|
| `structural_edit` `target_k` | Directly add or remove a consideration, or change its `favors` or weight. | Solver for V′; the K-drift handling below; tier `model-solved` (or `human-solved` through the queue). |
| `structural_edit` general `target_f` | Any fact edit (add, edit, remove). Only "make a `would_not_change` condition true" is built, because there V is held by construction. | Solver for K′ then V′; retry and `k_drift` annotation when K′ differs from the intent. |
| `structural_edit` `lookalike` beyond Φ | Same domain and surface, enough change in K that V changes. Today a lookalike can only be a same-domain flip through an existing `would_change` item. | Solver; accept only if V′ ≠ V, else keep as a `target_k` result. |
| `frame_edit` remove the gold option | The new gold is whatever is next best. | Solver for V′. |
| `frame_edit` add an invented option | A plausible wrong option not in the source. | Solver to confirm V holds; option-texture checks (R6, R70). |
| `frame_edit` change the decider | Q changes, so V may change. | Solver for V′. |
| K-drift handling | What to do when the solver's K′ differs from the writer's intended change (retry with feedback, annotate `k_drift`, or send to hard). Specified, not built: no built mode produces it. | Build with the first solver-dependent mode. |

## 2. Not built (in scope, not done)

| Item | What it is | Why not done | What it would take |
|---|---|---|---|
| Solver `panel` backend | Several independent Bedrock-hosted solvers combined by a rule (unanimous / majority); a split goes to the next backend. | Nothing in v1 needs a solver to set a gold. | ~half a day once a fidelity approach is chosen. Catches one model's quirks, not a bias all LLMs share. |
| Operator resume from human answers | The `human` solver backend now queues tasks (`data/store/queue/`) and the console records answers (`data/labels/labels.jsonl`), but an operator chain does not yet pause in a `pending_solve` state and resume when the answer arrives. | Operators are not yet resumable and idempotent. | Make operator steps resumable by task id; a `python -m pipeline.ops resume` that reads answers and finishes the pending outputs. |
| Semantic no-op check for `target_f` | The smoke run produced a near-restatement ("concerns" → "continued to have concerns") that the strict pre-check passed; word-overlap distance cannot catch it. | Found in the smoke run; not yet built. | A cheap LLM check, "does the edited fact assert anything the original did not?", as an annotation. |
| Console: run-over-run trend charts | The console shows each run and batch; it has no charts of a metric across runs or batches over time. | First version is tables only. | Add when there are enough batches to trend. |
| SFT: full-scale target generation | Run the chosen pipeline (Luna writes; Granite writes W+V with notes + guidance; gates) over pairs-v1 full. | **Running** (2026-11-13): `results/sft/gen1`, 2,217 train cells, no revised arm (Peter). | `pipeline.sft.generate` write -> wv -> assemble; then M15. |
| pairs-v1 evals on format v3 | SFT targets use `format.v3` (reasoning after not_governed, no case_approach there); evals of trained models must use the same prompt. | Decided 2026-11-13. | Pass `format_spec v3` in eval.allpairs runs on pairs-v1. |
| `surface_edit` `match_options` | Rewrite all options as a matched set (similar length and texture) with K and V held, so option form carries no cue (R6, R70). | Being built (2026-11-11). | — |

## 3. Deferred (later, by decision)

| Item | What it is | When |
|---|---|---|
| **Distance metric (important)** | How far a derived scenario is from its anchor. Undecided. Every transformation is recorded losslessly (lineage steps), so distance can be computed afterwards for everything already generated. Related: R56 (distance confounded with operator family). | Before the headline distance curves. |
| Render parameters | Realization (stated → indirect → multi-hop), distractor density, channel mix, filler register. Listing facts plainly is acceptable for now (Peter), so the study measures reasoning, not fact extraction (R4, R5). | **Must be ready before SFT**, because SFT targets demonstrate fact extraction. |
| Duplicate checks | X′ nearly duplicating an existing store scenario (mainly in `neighbor` mode). | Later; hard to do well. |
| Epistemic edits | confirmed → assessed, or removing a decisive fact: an F-change subtype. Undecided how they interact with the hand-up rules. | Later. |
| Two-scenario operators | Merge or split cases. | Out of scope. |
| Deployer equity variation | Swapping the deployer's equities. Would happen upstream, at scenario writing, into a partitioned store. | Out of scope. |

## 4. Waiting on Peter

| Decision | Options | Notes |
|---|---|---|
| Solver fidelity approach | (1) keep model-solved golds out of the headline; (2) a practitioner-conditioned solver; (3) measure each solver's fidelity on flips, where the answer is known; (4) human review of disagreements only (the console queue). Combinable; which first? | Unblocks all of section 1 and the `panel` backend. |

## 5. Decided against / parked

| Item | Ruling | Reason (Peter, 2026-11-11) |
|---|---|---|
| SFT: would_change consistency gate (a Jev check that case_approach states each cited would_change item correctly; M13 found one slip, cell 00427) and a "3-5 sentences" cap on case_approach | **Not to be built.** | (Peter, 2026-11-13) Too specific a failure mode; checking it would open a long list of other checks; no length limit. |
| `frame_edit` decide ↔ advise | **Not to be built for now.** | "Causes some quirks, I don't want to engage those yet." (The quirks: option wording changes from "approve" to "recommend approval", and a hand-up option such as "refer it to the minister" is a real choice for a decider but close to a non-answer for an advisor.) |
| `frame_edit` add an option the source considered and rejected | **Dropped.** | Options the source considered and rejected would already be in the option set; a rejected preceding decision is a different question, not another option for this one. |
| `frame_edit` drop_option as a pairs-v1 arm | **Removed from the dataset** (the operator code stays; 51 pilot outputs kept in the store, not used in cells). | "That just reduces the choice set and almost certainly increases the probability of correct guesses." |

## Done

- Five operators with v1 modes, code-built lineage, gates and annotations, recipes, analytics, Φ grounding sidecar
  (commit 7d9f1e1a); lineage migration applied to 470 derived scenarios (0acd8e5b).
- Solver `human` backend, the review queue (`python -m pipeline.ops enqueue-review`), sign-off records, and the research
  console (`code/console/`, 2026-11-11).
