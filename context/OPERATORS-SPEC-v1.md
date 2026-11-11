# Scenario operators — spec v1 (draft for Peter's mark-up)

*2026-11-11. From Peter's rulings in session 4e83879d (2026-11-10/11). Replaces the operator list of design v2.4.1
§6-7 (perturb, revise_card, pair/reorder, transfer) once Peter approves it. Nothing in the code has moved yet.*

## Principles (Peter)

- **Few primitive operators, each with parameters. No near-duplicates.** An experimental arm is a *recipe* (a
  composition of operators with arguments), not a new operator.
- **Every application is recorded without loss**: operator, mode, every argument, the writer and solver used, the
  check results and the output Δ. Anything we later want to know about a transformation (e.g. its distance) must be
  computable from that record.
- **Observability.** Batch analytics make drift visible (gold position, option length, supporting-fact counts,
  hand-up share, etc.). They are for awareness. They do not automatically delete or rewrite data.
- **Modularity.** Writers, solvers and checks can be swapped (LLM ↔ human, one model ↔ another) without touching the
  operators.

## Layers

| Layer | What it does | Examples |
|---|---|---|
| Scenario store | X = (F, Q, A), A = K, W, V, Φ (+ lesson, limits, basis) | `data/store/scenarios/` |
| **Operators** | X → (X′, Δ). One scenario in, one out. | the five below |
| Planner (batch policies) | Picks scenarios and operator arguments for a whole set; orchestrates recipes; runs batch analytics | gold-position balance, hand-up cap, which flip condition per anchor, "go fish" decoys |
| Projections | Turn a scenario into what a model sees. Not edits. | `render(X) → T`, `serve(X) → C` |
| Pairing / cells | Join a projected T(X1) with a served C(X2) per arm | `eval.transfer_cells`, all-pairs grid |

## The five operators

Notation: K = considerations, each `facts → equity → favors → weight → why`. **K is not split** (Peter, 2026-11-11):
weights belong to K, and `judgment_edit` may edit them.

### 1. `permute`
Reorders the items of one list: options (the main use), facts or considerations. Code only. The ids are renumbered so
that the id number equals the position.
- Args: `target = options | facts | considerations`, `order = [explicit] | random(seed)`.
- Balancing (e.g. the gold position across a batch) is a planner policy that supplies `order`.
- Δ: the id map. The gold follows by construction.

### 2. `surface_edit`: F changes, K is held (approximately), V is held
- Modes:
  - `reword`: same meaning, new wording.
  - `neighbor`: a different but similar situation in the same domain; new facts, K approximately equivalent.
  - `transfer`: a different domain with entirely new facts; K approximately equivalent because the implications for the
    equities are the same.
- Args: `mode`, `setting` (`neighbor`: optional; `transfer`: required: the sub-domain plus a sketch, given or
  proposed by a writer), `k_tolerance` (what "approximately equivalent" allows: same equity ids and favors, same
  decisive set, weight within ±1 step; to be confirmed), `writer` role.
- **The V invariant is checked, never assumed.**
  - Checks:
    - a blind re-extraction of K from the new F and Q must match the old K within `k_tolerance`;
    - a blind solve must reach the same V;
    - the new setting must not add a strong consideration of its own;
    - leak and technique checks.
  - A failure goes to hard or rejected. It is never relabelled with a new V (that would let a verdict change escape
    as "follows").
- Δ:
  - `reword`: a full 1:1 fact map, options 1:1, K matched.
  - `neighbor` and `transfer`: the K map by id and the option map. There is no fact-level map by construction, since
    the facts correspond only through the considerations that cite them.
  - Relation: `follows`.
- Replaces `perturb.restyle` (reword) and transfer `write_sister` (transfer). `neighbor` is new.

### 3. `structural_edit`: F changes and K changes
- Modes:
  - `flip`: make one Φ `would_change` item true by editing F, and the K it touches. V := that item's `then`, by
    construction; `via` = the item id.
  - `target_k`: name a change in K (add or remove a consideration, change its `favors`, change a weight). A writer
    alters F (in-domain) so the change follows. A solver then re-derives K and V from the new F and Q (blind). The
    writer's claim is never trusted.
  - `target_f`: name a change in F (add, edit or remove a fact). The solver derives K′, then V′.
  - `lookalike` (Peter: fold "same surface, different K" in here): keep the surface on purpose (same domain, same
    kinds of actors and facts) while changing K enough that V should not carry over. It is the mere-appearance cell
    of the surface × structure grid. It may be built from `target_k` plus a surface-similarity constraint.
- Args:
  - `mode`, `target` (a Φ id, a K change or an F change);
  - `realization = plain | indirect`, `max_facts` (default 2);
  - `resolve = by_construction | solver(spec)`: `flip` defaults to by construction, the others to the solver.
- Δ: the fact map buckets (matched / corresponding / live_only / case_only), the K map, the relation (`flips` /
  `distinguished` / `follows`), `via`.
- Φ is maintained by a shared step: the new item reverses back to the original V.
- Replaces `perturb.flip` (indirect, with a light restyle composed on top), transfer `write_flip` (plain) and
  `perturb.add_fact` (`target_f`). `target_k` and `lookalike` are new.

### 4. `frame_edit`: Q changes (Peter, 2026-11-11)
- Targets:
  - the option set (remove an option, e.g. the gold one; add a plausible wrong one);
  - `agent_role` (decide / advise / execute);
  - the decider.
- Resolution: the solver. Some cases can be set by construction, e.g. removing a non-gold option keeps V.
- Δ: the option map (with removed and added options), the relation.

### 5. `judgment_edit`: F, Q and K-structure untouched; edits the weights, W, V and Φ
- Args:
  - `target = option Oj | weights {k_id: w}`;
  - `author = LLM role | human`.
- No new consideration drawn from existing facts (the grey case; Peter: not needed now).
- Δ: relation `revised` (the served C′ carries an edited judgment; following it is the H4 online-edit test, R54).
- Replaces `perturb.revise_card` (which must stop adding considerations).

### What is *not* an operator
- **Decoy** (different surface, different K): "go fish". The planner draws another scenario from the store.
- **Deployer equity variation**: out of scope (Peter). The deployer's equities are fixed. Swapping equities would
  happen upstream, at scenario writing, into a partitioned store.
- **Two-scenario operators** (merge or split cases): out of scope.

## Output contract

Every operator returns `(X′, Δ)` and appends one lineage step to X′:

```yaml
lineage:
  parent: <X id>
  steps:                     # the full recipe, in order; composition = several steps
    - op: structural_edit
      mode: flip
      args: {target: {phi: W2}, realization: plain, max_facts: 2, resolve: by_construction}
      writer: {role: transfer_writer, model: ..., prompt: flip.v1.md@<sha>, temperature: ...}
      solver: null
      checks: {leak: pass, technique: pass, blind_reaches_then: true, ...}
      delta: {fact_map: ..., k_map: ..., option_map: ..., relation: flips, via: W2}
  anchor: <root X id>        # the extracted corpus scenario at the root of the chain
  family: <root family>      # inherited unchanged; see Splits
```

Δ composes along the chain, so a pair (C = Xᵢ, T = Xⱼ) with a common ancestor has a gold mapping by composition.

## Solver module

```
solve(task) -> Solved(answer, by, provenance) | Pending(task_id)
```
- **Task types** carry only their inputs, so blindness is enforced by the type, not by each caller's prompt:
  - `verdict(F, Q, E)`;
  - `considerations(F, Q, E)`;
  - `weighing(F, Q, K)`;
  - `condition_holds(F, if)`.
- **Backends**: one LLM role; a panel that must agree; human; and the escalation chain (panel → human queue on
  disagreement or a failed check).
- **Human loop**:
  - A pending task goes to `data/store/queue/<task_id>.yaml`, and the scenario waits in a `pending_solve` state.
  - A labelling page shows each task with its context (to be designed; possibly an artifact with a shared database).
  - The answer resumes the operator chain by task id. For that, operators must be resumable and idempotent.
- **Who solved it** sets the gold tier: by-construction / model-solved / human-solved.
- The 28 `needs_review` pilot-2 answer keys could be reviewed through the same queue.
- Replaces add_fact's independent solver, transfer's `blind_solve` and perturb's `condition_holds`.

## Splits and families

- Every operator output inherits its anchor's `family` and split; this is enforced in the writer, in one place.
- The full chain (`lineage.anchor`, `parent`, steps) is kept, so the train/test strata can be redefined later and
  every scenario derived from an anchor or family found again (Peter: we may re-stratify).

## Batch analytics (observability)

The planner reports per batch and per arm:
- gold option position;
- option count and length;
- supporting facts per option;
- hand-up share;
- fact and consideration counts;
- check-failure rates per operator;
- writer and solver mix.

These flag drift (R4-R7, R50-R58). They never delete data by themselves.

## Mapping from existing code

| Spec | Current code |
|---|---|
| `permute` | `pipeline/pair/reorder.py`, transfer `permute_options`, `pipeline/ingest/balance_options.py` |
| `surface_edit` reword / transfer | `pipeline/perturb/restyle.py` / `pipeline/transfer/build.py` `write_sister` |
| `structural_edit` flip | `pipeline/perturb/flip.py` (indirect + restyle), transfer `write_flip` (plain); repair: `perturb/backflip.py` |
| `structural_edit` target_f | `pipeline/perturb/add_fact.py` |
| `judgment_edit` | `pipeline/perturb/revise_card.py` |
| solver | add_fact's solver, transfer `blind_solve`, `perturb/condition.py` |
| checks | transfer `run_checks`, `pipeline/render/answer_leak.py`, `pipeline/ingest/technique_check.py` |

Old modules go to `versions/` when replaced. The lineage of existing store scenarios (operators `restyle`, `flip`,
`add_fact`, `revise_card`, `reorder`, `transfer`, `transfer-flip`) is mapped onto the new names and arguments by a
migration that adds fields and never deletes any.

## Deferred (TODO; come back to these)

1. **Distance metric (important).** The metric is undecided. For now, every transformation is recorded without loss
   (above), so distance labels can be computed retroactively for all completed transformations once the metric
   exists. Related: R56 (distance confounded with operator family). Also in `docs/V2-PRIORITIES.md`.
2. **Render parameters, after the pair operators.**
   - Realization (stated → indirect → multi-hop), distractor density, channel mix, filler register.
   - Peter, 2026-11-11: listing facts obviously is acceptable *for now*, so the study measures reasoning, not fact
     extraction (R4, R5).
   - **Must be ready before SFT**, because SFT targets demonstrate fact extraction.
3. **Duplicate checks** (X′ nearly duplicating an existing store scenario, especially in `neighbor` mode). Hard to
   do; later.
4. **Epistemic edits** (confirmed → assessed, removing a decisive fact): an F-change subtype. Decide later how they
   interact with the hand-up rules.

## Open for Peter

- The default `k_tolerance` for `surface_edit` (what counts as "approximately equivalent" K).
- `lookalike`: how much K change is required, and how surface similarity is held and checked.
