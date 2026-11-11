"""Scenario operators (context/OPERATORS-SPEC-v1.md, Peter 2026-11-11).

Five primitives, each X -> (X', delta) with a code-built lineage step:
    permute          reorder options / facts / considerations (code)
    surface_edit     reword | neighbor | transfer      (F changes; K and V held)
    structural_edit  flip | target_f (would_not_change)  (F and K change; V by construction)
    frame_edit       drop_option                       (Q changes; V held)
    judgment_edit    weights / W / V / Φ               (F, Q, K's equity and favors fixed)
v1 scope: no independent solver sets a verdict. Arms are recipes (recipes.py); render() and serve() are projections,
not operators. CLI: python -m pipeline.ops --help
"""
from .frame import drop_option
from .judgment import judgment_edit
from .permute import permute
from .record import OpResult, finish
from .structural import structural_edit
from .surface import surface_edit


def frame_edit(X, store, *, target: str = "drop_option", **kw):
    if target != "drop_option":
        raise ValueError(f"frame_edit target {target!r} is not built in v1")
    return drop_option(X, store, **kw)


__all__ = ["permute", "surface_edit", "structural_edit", "frame_edit", "judgment_edit", "OpResult", "finish"]
