"""Augmented-pair gate (design §7.2): X''s back-flip `if` must hold on X's RENDERED trace.

Runs as its own step after render:  python -m pipeline.pair gate-augmented
The condition-holds verifier is W3's (pipeline.perturb); this module calls it and does not reimplement it. The verifier
is `pipeline.perturb.flip.condition_holds(text, condition, store=None) -> (bool, why)` when W3 exposes it; until then the
fallback drives W3's own machinery (Ctx.ask with the `verify_condition` prompt and the same user layout as flip's stage A).
"""
from __future__ import annotations

import random
import time

from bench.schema.pipeline import PairRecord
from pipeline.store import Store, write_yaml

from .arms import local, now


def trace_text(tj: dict) -> str:
    """The rendered trace as plain text (every message's content, tool calls included)."""
    parts = []
    for m in tj.get("messages", []):
        c = m.get("content")
        if isinstance(c, list):
            c = "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
        parts.append(f"[{m.get('role', '?')}] {c or ''}")
        for tc in m.get("tool_calls") or []:
            parts.append(f"[tool_call] {tc}")
    return "\n\n".join(parts)


def default_verifier(store: Store):
    """-> fn(text, condition, scenario) -> (holds: bool, why: str), W3's verifier."""
    try:
        from pipeline.perturb.flip import condition_holds                  # preferred public hook (requested from W3)

        def v(text, cond, X):
            return condition_holds(text, cond, store=store)
        return v
    except ImportError:
        pass
    from pipeline.perturb.common import Ctx

    def v(text, cond, X):
        ctx = Ctx("flip", X, store, random.Random(0))
        out, _ = ctx.ask("perturber", "verify", "verify_condition", f"FACTS:\n{text}\n\nCONDITION: {cond}", lambda o: o, tries=2,
                         step_id="pair.gate")
        return out.get("holds") is True, str(out.get("why"))
    return v


def gate_augmented(store: Store, verifier=None, limit: int | None = None, regate: bool = False) -> dict:
    """For every augmented pair still tagged gate-pending whose trace X is rendered: verify the back-flip item's `if`
    on X's trace. Pass -> tag gate-passed. Fail -> tags rejected + gate-failed with the reason in provenance (nothing is
    deleted; exports skip `rejected`). Missing trace -> stays pending. Log: data/store/augmented_gate.yaml."""
    verifier = verifier or default_verifier(store)
    res = {"passed": [], "failed": [], "pending_no_trace": [], "skipped": []}
    n = 0
    for p in store.pairs():
        if p.arm != "augmented":
            continue
        tags = set(p.tags)
        if not regate and ({"gate-passed", "gate-failed"} & tags):
            res["skipped"].append(p.id)
            continue
        if not store.has_trace(p.trace_ref or p.trace_scenario):
            res["pending_no_trace"].append(p.id)
            continue
        if limit is not None and n >= limit:
            break
        n += 1
        Xp = store.scenario(p.case_scenario)
        X = store.scenario(p.trace_scenario)
        item = next((w for w in Xp.case.flip_conditions.would_change if Xp.case.global_id(w.id) == (p.via or [None])[0]), None)
        assert item is not None and item.then == X.case.verdict.choice, f"{p.id}: back-flip item missing or wrong `then`"
        text = trace_text(store.trace_json(p.trace_ref or p.trace_scenario))
        ok, why = verifier(text, item.if_, X)
        tags -= {"gate-pending", "gate-passed", "gate-failed", "rejected"} if regate else {"gate-pending"}
        p.provenance.step(id=f"pair.gate.{len(p.provenance.steps)}", operator="pair", ts=now(), params={"holds": bool(ok)},
                          notes=f"back-flip `if` {'holds' if ok else 'does NOT hold'} on X's rendered trace: {why}")
        if ok:
            tags.add("gate-passed")
            res["passed"].append(p.id)
        else:
            tags |= {"gate-failed", "rejected"}
            res["failed"].append({"pair": p.id, "if": item.if_, "why": why})
        store.save_pair(p.model_copy(update={"tags": sorted(tags)}))
    write_yaml(store.root / "augmented_gate.yaml", {"ts": now(), **res})
    return {k: (len(v) if k != "failed" else v) for k, v in res.items()} | {"n_failed": len(res["failed"])}
