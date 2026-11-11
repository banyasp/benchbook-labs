# Scenario operators — spec v1 (draft for Peter's mark-up)

*2026-11-11. From Peter's rulings in session 4e83879d (2026-11-10/11). Replaces the operator list of design v2.4.1
§6-7 (perturb, revise_card, pair/reorder, transfer) once Peter approves it. Nothing in the code has moved yet.
Revision 2 (same day): Peter's second round (k_tolerance exact; lookalike = V changes; the blind solve is an
annotation, not a gate; `resolve` dropped; `author` → `writer`; lineage written by code). First draft:
`versions/OPERATORS-SPEC.v1-first-draft.md`.*

## v1 build scope: no independent solver (Peter, 2026-11-11)

Build only the modes whose V′ needs no independent solver. The solver module is specified below, but its LLM and human
backends are not built yet (solver fidelity to practitioners is unresolved: a blind Luna solve agrees with the corpus
verdict on 42 of 57 anchors).

| Operator · mode | In v1 | V′ from |
|---|---|---|
| `permute` (all) | yes | code |
| `surface_edit` reword / neighbor / transfer | yes | held |
| `structural_edit` flip (incl. a same-domain flip used as a lookalike) | yes | the Φ `would_change` item's `then` |
| `structural_edit` target_f **realizing a `would_not_change` item** | yes (Peter: "interesting and cool") | held |
| `frame_edit` remove a non-gold option / add an option the source considered and rejected | yes | held |
| `frame_edit` decide ↔ advise | pending Peter's ruling | held (proposed) |
| `judgment_edit` | yes | the planner's target |
| `structural_edit` target_k, general target_f, lookalike beyond Φ; `frame_edit` remove gold / add an invented option / change decider | **later** (needs a solver) | — |

- **Capacity** (1,072 extracted scenarios):
  - 1,493 `would_change` items, at least one per scenario;
  - about 1,100 `would_not_change` items, but many restate a fact already present, so only the counterfactual ones
    give a real edit.
- **Φ grounding is an annotation, not a gate** (Peter). No Φ item records whether its `if` and `then` are stated or
  implied in the source spans, or were authored by the extractor. A grounding check records this per item
  (`phi_grounding: stated | implied | authored`) for the dashboard. It never removes items.
- The blind-solve annotations (`verdict_shift`, `k_support`) are optional in v1: they are an LLM call per output
  and serve observability only.

## Build status (2026-11-11)

Built in `code/pipeline/ops/` (README there), with the v1 scope above:
- all five operators;
- code-built lineage steps (`lineage.anchor`, `lineage.steps` added to the schema);
- gates and annotations; the solver interface (LLM backend for annotations and checks only);
- recipes and the planner (`recipes/`: same_domain_flip, transfer_flip, neighbor_control, lookalike_flip, noflip,
  drop_option, revised);
- batch analytics;
- the Φ grounding sidecar (`python -m pipeline.ops grounding`);
- the legacy lineage migration (dry run only so far: 470 legacy derived scenarios, 253 with a gold partial).

Not built:
- `frame_edit` add-a-source-rejected-option (needs the source text) and decide ↔ advise (awaiting Peter);
- the solver's panel and human backends;
- the dashboard page.

Live smoke (every v1 mode once, on pilot-2 X1s, written to a scratch store):
- 8 accepted;
- the neighbor and transfer outputs went to hard on setting_adds, and both were also flagged by verdict_shift.

## Principles (Peter)

- **Few primitive operators, each with parameters. No near-duplicates.** An experimental arm is a *recipe* (a
  composition of operators with arguments), not a new operator.
- **Every application is recorded without loss**: operator, mode, every argument, the writer and solver used, the
  check results and the output Δ. Anything we later want to know about a transformation (e.g. its distance) must be
  computable from that record. **Code writes the record**; models only ever write the language content.
- **Observability.** Batch analytics and per-scenario annotations make drift and doubtful outputs visible on a
  pipeline dashboard. They are for awareness and for improving the system. They do not automatically delete data.
  Gates are reserved for hard failures (leak, technique, structure, a setting that adds a strong consideration).
- **Modularity.** Writers, solvers and checks are swappable backends (LLM ↔ human, one model ↔ another).

## Layers

| Layer | What it does | Examples |
|---|---|---|
| Scenario store | X = (F, Q, A), A = K, W, V, Φ (+ lesson, limits, basis) | `data/store/scenarios/` |
| **Operators** | X → (X′, Δ). One scenario in, one out. | the five below |
| Planner (batch policies) | Picks scenarios and operator arguments for a whole set; orchestrates recipes; runs batch analytics | gold-position balance, hand-up cap, which flip condition per anchor, "go fish" decoys |
| Projections | Turn a scenario into what a model sees. Not edits. | `render(X) → T`, `serve(X) → C` |
| Pairing / cells | Join a projected T(X1) with a served C(X2) per arm | `eval.transfer_cells`, all-pairs grid |

## Shared arguments and definitions

- **K** = considerations, each `facts → equity → favors → weight → why`. K is not split (Peter): weights belong to K,
  and `judgment_edit` may edit them.
- **K-equivalence** (`k_tolerance`, Peter, 2026-11-11): the same equity ids, the same `favors` and the same `weight`
  for every consideration. A one-step weight change could plausibly change the outcome, so it is not tolerated.
  It is checked two ways:
  1. **Structure (gate, code):** X′'s K has exactly X's equity ids, favors and weights. It is deterministic and
     cheap.
  2. **Support (annotation, LLM):** a blind re-extraction of K from X′'s F and Q, compared with X′'s K. This is noisy:
     re-extraction does not always reproduce the weights even on an unedited X. So it stays an annotation until its
     noise floor on unedited scenarios is measured.
- **`writer`** (every operator that writes language): an LLM role (`transfer_writer`, ...) or `human` (an SME or the
  deployer editing the casebook). The backend is swappable, like the solver's.
- **`solver`** (operators whose V cannot be set by construction): the solver spec (see Solver module).

## The five operators

### 1. `permute`
Reorders the items of one list: options (the main use), facts or considerations. Code only. The ids are renumbered so
that the id number equals the position.
- Args: `target = options | facts | considerations`, `order = [explicit] | random(seed)`.
- Balancing (e.g. the gold position across a batch) is a planner policy that supplies `order`.
- Δ: the id map. The gold follows by construction.

### 2. `surface_edit`: F changes, K held (K-equivalence), V held
- Modes and the `setting` argument (`setting = {subdomain, sketch}`; the sketch is given, e.g. written by a
  sketching step, or proposed by the writer):

  | Mode | `setting` | Example (anchor: in 1981 the Deputy Secretary of Defense decides whether the new computer-security evaluation center sits at NSA or at a civilian federal center; the sponsor prefers NSA's expertise; NSA would house it outside its chain with its own budget; components fear interference) |
  |---|---|---|
  | `reword` | none (same world) | The same 1981 decision with new wording: same actors, same facts. |
  | `neighbor` | same sub-domain (cyber policy), a new situation | Where a government vulnerability-disclosure clearinghouse sits: the signals-intelligence agency (its expertise) or a civilian cyber agency (a government-wide problem); the agency would host it outside its chain; departments fear it will sit on vulnerabilities. |
  | `transfer` | another sub-domain | Personnel security: where the department's clearance-adjudication facility sits, at the counterintelligence agency (investigative expertise) or at the civilian personnel agency (reciprocity is government-wide). Or space policy: whether the satellite collision-warning center goes to space command's squadron or to a civil space-traffic office. (Both are batch-2 sketches for this anchor, `results/domain-transfer/SISTER-SCENARIOS-NATSEC-batch2a.md` §1.) |

- Gates:
  - K-equivalence (structure);
  - **the new setting must not add a strong consideration of its own** (it would change the weighing and the
    verdict);
  - leak;
  - technique.

  A failure goes to hard or rejected and is never relabelled with a new V.
- **Annotations** (not gates; Peter: the corpus V comes from the practitioner, and a solver may disagree with it or
  draw a line elsewhere):
  - `verdict_shift`: a blind solve on X and on X′. The signal is the conditional case: the solver agrees with V on X
    but not on X′. That suggests the edit itself moved the decision. If the solver already disagrees on X, the
    annotation says so and carries no signal.
  - `k_support`: the blind re-extraction of K (see K-equivalence).
- Δ:
  - `reword`: a full 1:1 fact map, options 1:1, K matched.
  - `neighbor` and `transfer`: the K map by id and the option map. There is no fact-level map by construction.
  - Relation: `follows`.
- Replaces `perturb.restyle` (reword) and transfer `write_sister` (transfer). `neighbor` is new.

### 3. `structural_edit`: F changes and K changes
- Modes (each mode fixes where the new V comes from; there is no separate `resolve` argument):

  | Mode | Input | V′ comes from |
  |---|---|---|
  | `flip` | a Φ `would_change` item id | by construction: the item's `then`; `via` = the item |
  | `target_k` | a K change (add or remove a consideration, change `favors`, change a weight) | the solver, from the new F and Q |
  | `target_f` | an F change (add, edit or remove a fact) | the solver: K′, then V′. **Except** when the change makes a Φ `would_not_change` item true: then V is held by construction, `via` = that item, and the relation is `follows` (v1) |
  | `lookalike` | same domain and surface; change K **enough that V changes** (Peter) | the solver; accepted only if V′ ≠ V |

- Args:
  - `mode`, `target`;
  - `max_facts` (default 2);
  - `realization = plain | indirect` (default `plain`):
    - `plain`: the changed fact states the new situation directly ("the partner government has formally asked the
      team to leave").
    - `indirect`: the condition holds only by implication, through facts that do not paraphrase the Φ item's `if`
      text (an overlap check enforces it). Its purpose: when X′ becomes a live trace and the served card carries the
      original Φ wording, the model cannot match the flip condition by string matching.
    - `indirect` matters only for that pairing direction. Peter's "obvious facts for now" makes `plain` the
      default; the 64 existing `perturb.flip` scenarios migrate as `indirect`.
  - `writer`, `solver`.
- **When the solver's K′ differs from the intended change** (`target_k`, `target_f`, `lookalike`):
  - **The gold follows what the solver found, never the writer's intent.** Δ is computed from the solver's K′ and
    V′; the intended change and the difference from it are recorded in the lineage step.
  - **Slightly different** (the intended change happened, plus other differences, e.g. a weight elsewhere moved):
    the writer retries with the difference as feedback (up to `tries`). If it is still off, the scenario is kept,
    annotated `k_drift` with the difference, and the planner decides whether it still fits the recipe.
  - **Substantially different** (the intended change did not happen, or the decisive set or V moved unexpectedly):
    retry, then hard. If a human solver is configured, the task goes to the queue.
  - **Arms accept on the actual Δ.** A `lookalike` whose V′ = V is not a lookalike; it is kept as a `target_k`
    result with relation `follows` or `distinguished`.
  - `flip` also runs the blind solver, as an annotation only (`verdict_shift`: does the solver reach `then`?). V is
    set by construction from the Φ item.
- Δ: the fact map buckets (matched / corresponding / live_only / case_only), the K map, the relation (`flips` /
  `distinguished` / `follows`), `via`.
- Φ is maintained by a shared step: the new item reverses back to the original V.
- Replaces `perturb.flip`, transfer `write_flip` and `perturb.add_fact` (`target_f`). `target_k` and `lookalike` are
  new.

### 4. `frame_edit`: Q changes (Peter, 2026-11-11)
- Targets:
  - the option set (remove an option, e.g. the gold one; add a plausible wrong one);
  - `agent_role` (decide / advise / execute);
  - the decider.
- V′: by construction where it is certain (e.g. removing a non-gold option keeps V; adding an option the source
  considered and rejected keeps V). Otherwise the solver.
- Δ: the option map (with removed and added options), the relation.

### 5. `judgment_edit`: F, Q and K's equity/favors untouched; edits weights, W, V and Φ
- Args:
  - `target = option Oj | weights {k_id: w}` (the planner picks the target);
  - `writer`: who writes the new weighing to reach it. An LLM role, or `human`: a deployer or SME editing their
    casebook, which is the online-edit use case (H4).
- No new consideration drawn from existing facts (Peter: not needed now).
- Δ: relation `revised` (R54: following C′ is the online-edit test).
- Replaces `perturb.revise_card` (which must stop adding considerations).

### What is *not* an operator
- **Decoy** (different surface, different K): "go fish". The planner draws another scenario from the store.
- **Deployer equity variation**: out of scope (Peter). The deployer's equities are fixed. Swapping equities would
  happen upstream, at scenario writing, into a partitioned store.
- **Two-scenario operators** (merge or split cases): out of scope.

## Output contract

Every operator returns `(X′, Δ)`. **Code** (not a model) appends one lineage step to X′, built from the call's
arguments, the backends' metadata, the check results and the computed Δ. Models return only language content, as
JSON validated by a callback, the pattern of `perturb/common.py` ("structural facts are built in Python; models only
write language").

```yaml
lineage:
  parent: <X id>
  steps:                     # the full recipe, in order; composition = several steps
    - op: structural_edit
      mode: flip
      args: {target: {phi: W2}, realization: plain, max_facts: 2}
      writer: {backend: llm, role: transfer_writer, model: ..., prompt: flip.v1.md@<sha>, temperature: ..., tries: 1}
      solver: {backend: llm, role: ..., used_for: annotation}
      gates: {structure: pass, leak: pass, technique: pass, setting_adds: pass}
      annotations: {verdict_shift: {solver_on_X: O1, solver_on_X_prime: O2, then: O2, flag: false}}
      intended: {...}        # target_k / target_f / lookalike: the requested change
      delta: {fact_map: ..., k_map: ..., option_map: ..., relation: flips, via: W2}
      ts: ...
  anchor: <root X id>        # the extracted corpus scenario at the root of the chain
  family: <root family>      # inherited unchanged; see Splits
```

Δ composes along the chain, so a pair (C = Xᵢ, T = Xⱼ) with a common ancestor has a gold mapping by composition.

## Solver module

```
solve(task, solver_spec) -> Solved(answer, by, provenance) | Pending(task_id)
```
- **Task types** carry only their inputs, so blindness is enforced by the type, not by each caller's prompt:
  - `verdict(F, Q, E)`;
  - `considerations(F, Q, E)`;
  - `weighing(F, Q, K)`;
  - `condition_holds(F, if)`.
- **Backends:**
  - `llm(role)`: one model.
  - `panel([roles], rule)`: several independent solvers (different models, e.g. GPT-6 Luna and Claude on Bedrock,
    or several samples of one model), combined by a rule (unanimous / majority). A split goes to the next backend.
    It catches one model's idiosyncrasies, but not a bias that all LLMs share. Natsec text stays on Bedrock, so the
    members must be Bedrock-hosted.
  - `human`: a pending task.
  - A chain, e.g. `panel → human` on disagreement or a failed check.
- **Human loop**:
  - A pending task goes to `data/store/queue/<task_id>.yaml`, and the scenario waits in a `pending_solve` state.
  - A labelling page shows each task with its context (to be designed; possibly an artifact with a shared database).
  - The answer resumes the operator chain by task id. For that, operators must be resumable and idempotent.
- **Who solved it** sets the gold tier: source-endorsed / by-construction / model-solved / human-solved. Reports split
  by tier.
- Replaces add_fact's independent solver, transfer's `blind_solve` and perturb's `condition_holds`.

### Solver fidelity to the practitioner (open; Peter's concern)

- A model solver may disagree with the practitioner, or draw the line somewhere else. Measured: a blind GPT-6 Luna
  solve agrees with the corpus verdict on **42 of 57 unedited transfer anchors (74%)**
  (`results/transfer/build-{pilot,batch2}-20261109.jsonl`, `checks.equivalence.anchor_blind_agrees_with_source`).
  So roughly a quarter of model-solved golds could depart from what a practitioner would do.
- Options, combinable:
  1. **Prefer by-construction routes.** surface_edit, flip and judgment_edit need no solver for V. Keep
     solver-dependent outputs (`target_f`, `target_k`, `lookalike`, part of `frame_edit`) tier `model-solved` and
     report them apart from the headline until validated.
  2. **A practitioner-conditioned solver.** The solver sees the original X's full A (the practitioner's K, W, V, Φ,
     lesson, limits) and is asked how *that* reasoning resolves the changed facts, not what it would do itself.
     It is closer to the practitioner's line. The cost is circularity: it is an analogical-reasoning model setting
     the gold for an analogical-reasoning test. Mitigation: run both the conditioned and the blind solver; where
     they disagree, flag the scenario or send it to the human queue.
  3. **Measure each solver's fidelity on edits with a known answer.** Flips have a by-construction V (Φ's `then`).
     A solver run on flips measures how often it reaches the practitioner's own counterfactual. Where Φ is
     source-grounded rather than extractor-authored, that is a direct fidelity estimate on edited scenarios.
  4. **Human review of the disagreements only**, through the queue (within Peter's audit budget).

## Splits and families

- Every operator output inherits its anchor's `family` and split; this is enforced in code, in one place.
- The full chain (`lineage.anchor`, `parent`, steps) is kept, so the train/test strata can be redefined later and
  every scenario derived from an anchor or family found again (Peter: we may re-stratify).

## Batch analytics and the pipeline dashboard (observability)

- Per batch and per arm:
  - gold option position;
  - option count and length;
  - supporting facts per option;
  - hand-up share;
  - fact and consideration counts;
  - gate-failure rates per operator;
  - annotation rates (`verdict_shift`, `k_support`, `k_drift`);
  - writer and solver mix;
  - gold-tier mix.
- These flag drift (R4-R7, R50-R58) and doubtful outputs. They never delete data.

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

- Old modules go to `versions/` when replaced.
- The lineage of existing store scenarios (operators `restyle`, `flip`, `add_fact`, `revise_card`, `reorder`,
  `transfer`, `transfer-flip`) is mapped onto the new names and arguments by a migration that adds fields and never
  deletes any.
- Note: the current transfer builder already treats blind-solve equivalence as information, not a gate. Its "hard"
  bucket comes only from the setting-adds check, plus flips demoted because their sister was hard: 37 of 104
  sisters and 52 of 100 flips (pilot 1 + batch 2).

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

- Solver fidelity: which of options 1-4 above, and in what order.
