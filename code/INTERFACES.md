# Step 2 interfaces (2026-10-25)

The contract between the Step 2 packages. `code/bench/` (2a) is done and frozen for today; change it only through
the coordinator. Everything below imports `bench.schema` and gets models only through `bench.models.role(...)`.
Run from the repo root with `PYTHONPATH=code` (pytest picks this up from `conftest.py`).

## bench (2a, done)
- `bench.schema`: `Case` (+ `.serve("REF1") -> ServedCase` with `.doc`, `.yaml()`, `.table` served id → global id),
  `EquitySet`, `parse_reply(content, reasoning=None) -> ParsedReply`, `AnswerKey`, `LiveScenario`, `STEPS`.
- `bench.models`: `role(name) -> RoleConfig`, `complete(role, messages, **overrides) -> str`. Roles in
  `config/models.yaml`: `policy`, `judge_choice`, `judge_noul`, `converter`, `query_extractor`.
- Id namespaces: canonical case items are local (`F1`, `C1`, `O1`, `flip1`) inside `DR-<family>@v<k>`; global id
  `DR-INT-301@v1/F1`; served `REF1-F1`; live `LIVE-F1`. Answer keys use LIVE ids + global case ids.

## library (2b) — `code/library/`
```python
from library import Library
lib = Library(root="data")                    # data/cases, data/registry, data/scenarios
lib.case("DR-INT-301@v1") -> Case             # latest version if "@v" omitted: lib.case("DR-INT-301")
lib.equities("pilot") -> EquitySet
lib.scenarios(family=None, split=None) -> list[LiveScenario]
lib.scenario("INT-301-v01") -> LiveScenario   # .answer_key(arm) -> AnswerKey
from library.retrieval import OracleRetriever, StructuralRetriever   # Structural = stub (NotImplementedError)
OracleRetriever(lib).retrieve(scenario, arm) -> list[Case]          # what the arm serves, in order
```

## harness (2c) — `code/harness/`
```python
from harness import HarnessSettings, build_episode, run_episode, continue_episode
s = HarnessSettings(mode="B", analogical_prompt=True, injection_role="user", injection_name="benchbook",
                    tool_messages="flattened" | "native", max_tokens=None, seed=None)
ep = build_episode(scenario, arm, s, lib)      # Episode: .messages, .prompt_text (rendered, chat template applied),
                                              #          .served: list[ServedCase], .prefill: str, .meta: dict
out = run_episode(ep, s, role="policy")      # Completion: .content, .reasoning, .raw_text, .usage, .seconds, .finish_reason
out2 = continue_episode(ep, s, partial="<assistant text so far, possibly edited>")   # faithfulness interventions
```
Modes (DECISIONS 2026-10-25): **A** thinking on, structure after `</think>`; **B** thinking off; **C** structure
inside `<think>` (prefill `<think>\nkind: fact_enumeration\n`), verdict after; **C′** like C, prose allowed between docs.
`raw_text` is the full assistant text including any prefill, so `parse_reply(raw_text)` works for every mode.

## scorers (2d) — `code/scorers/`
```python
from scorers import score_reply, Judge
from scorers.judge import JevJudge, StubJudge, CachedJudge
judge = CachedJudge(JevJudge(), path="results/judge_cache.sqlite")   # or StubJudge() offline
scores = score_reply(parsed, key, served, judge) -> dict[str, float | int | None]   # one entry per PDF table row
```
None = not scored (gold absent or after `not_governed`). No weights, no combination (reward TBD, Peter).
Adapters: `scorers.inspect_adapter` (an Inspect `@scorer`), `scorers.trl_adapter` (reward funcs, one per scorer).

## eval + training (2e) — `code/eval/`, `code/training/`
- `eval/checkpoint2.py`: Inspect task over scenarios × arms × {prompt, no prompt} × modes × samples; solver calls
  the harness, scorer calls `score_reply`; also writes per-sample JSONL to `results/checkpoint2/<run>/samples.jsonl`.
- `eval/faithfulness.py`, `eval/stats.py` (bootstrap CIs resampling whole families), `eval/report.py` (RESULTS tables).
- `training/`: SFT data builder (loss masks), LoRA SFT, GRPO skeleton. CPU-checked only today.
