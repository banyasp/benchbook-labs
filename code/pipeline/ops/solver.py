"""Solver module (OPERATORS-SPEC-v1 §Solver module). v1 scope: no independent solver sets a verdict (Peter, 2026-11-11);
the LLM backend is used for annotations and realization checks only. `panel` is specified, not built. `human` writes a
task to the queue (`pipeline.ops.queue`, answered in the console) and returns a pending result (2026-11-11).

    solve(task, spec) -> {"answer": ..., "by": {...}}                     llm
    solve(task, spec) -> {"pending": task_id, "answer": None, "by": {...}} human; read back with answer_for(task_id)

Task types carry only their inputs, so blindness is enforced here, not by each caller:
    verdict        F, Q, equities                -> choice (+ the considerations the solver sees)
    condition_holds F, the `if` text             -> holds, why
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SolverSpec:
    backend: str = "llm"            # llm | human | panel (panel: later)
    role: str = "transfer_checker"

    def meta(self, used_for: str) -> dict:
        return {"backend": self.backend, "role": self.role, "used_for": used_for}


def _blind_case(case: dict) -> dict:
    """Only F and Q (and the agent frame); never considerations, reasoning, verdict or flip conditions."""
    keep = ("setting", "decider", "agent", "agent_role", "situation", "question", "facts")
    shown = {k: case[k] for k in keep if k in case}
    shown["options"] = {k: {"do": v["do"]} for k, v in case["options"].items()}
    return shown


def solve(task: str, payload: dict, spec: SolverSpec | None = None) -> dict:
    spec = spec or SolverSpec()
    if spec.backend == "human":
        return _human(task, payload, spec)
    if spec.backend != "llm":
        raise NotImplementedError(f"solver backend {spec.backend!r} is specified but not built (v1 scope)")
    if task == "verdict":
        from pipeline.transfer.build import blind_solve
        case = payload["case"]
        blind = _blind_case(case)
        out = blind_solve({**blind, "options": {k: {"do": v["do"]} for k, v in case["options"].items()}})
        return {"answer": out, "by": spec.meta("annotation")}
    if task == "condition_holds":
        from pipeline.perturb.condition import condition_holds
        return {"answer": condition_holds(payload["if"], payload["facts_text"], role="perturber"),
                "by": {"backend": "llm", "role": "perturber", "used_for": "check"}}
    raise ValueError(f"unknown solver task {task!r}")


def _human(task: str, payload: dict, spec: SolverSpec) -> dict:
    """Queue the task for a person (console /queue). Blindness: a verdict task carries only blind_case(case)."""
    from . import queue as Q
    if task == "verdict":
        tid = Q.enqueue("verdict", {"case": Q.blind_case(payload["case"])}, ref=payload.get("ref"), source="solver")
    elif task == "condition_holds":
        tid = Q.enqueue("condition_holds", {"if": payload["if"], "facts_text": payload["facts_text"]},
                        ref=payload.get("ref"), source="solver")
    else:
        raise ValueError(f"unknown solver task {task!r}")
    return {"pending": tid, "answer": None, "by": {"backend": "human", "role": spec.role, "used_for": "solve"}}


def answer_for(task_id: str) -> dict | None:
    """The person's latest answer to a queued task, or None while it is pending. (Resuming the operator chain from
    the answer is not built yet: docs/OUTSTANDING.md.)"""
    from . import queue as Q
    return Q.answer_of(task_id)
