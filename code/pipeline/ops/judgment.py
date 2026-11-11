"""judgment_edit: F, Q and K's equity/favors untouched; the weights, W, V and Φ change (OPERATORS-SPEC-v1 §5).

Wraps pipeline.perturb.revise_card with weights_only=True (no favors / rules_out change, no new consideration).
target = an option id, or "auto" (revise_card's seeded pick, balanced by move with the hand-up cap). The writer is an LLM
role (`perturber`) in v1; a human writer (a deployer editing the casebook) is the H4 online-edit case, later.
Gold: relation `revised`; the new judgment is stipulated, not an oracle's (R54).
"""
from __future__ import annotations

from pathlib import Path

from bench.schema.pipeline import Scenario

from . import checks as CK
from .record import OpResult, dump_delta, llm_writer


def judgment_edit(X: Scenario, store, *, target: str = "auto", seed: int = 0, tally=None) -> OpResult:
    from pipeline.perturb.common import OperatorError, seed_rng
    from pipeline.perturb.revise_card import revise_card
    args = {"target": target, "seed": seed, "weights_only": True}
    try:
        T, partial = revise_card(X, store, seed_rng(X.id, "judgment_edit", target, seed), tally=tally,
                                 target=None if target == "auto" else target, weights_only=True)
    except OperatorError as e:
        msg = str(e)
        if "cannot reach" in msg or "must be an option" in msg:
            return OpResult("judgment_edit", None, args, None, skipped=msg[:200])
        return OpResult("judgment_edit", None, args, None, log=[{"error": msg[:300]}])
    writer = llm_writer("perturber", Path(__file__).resolve().parents[1] / "perturb" / "prompts" / "revise_card.v1.md")
    r = OpResult("judgment_edit", None, args, T, delta=dump_delta(partial), writer=writer)
    a, b = CK.case_dict(X), CK.case_dict(T)
    sig = lambda c: {k["id"]: (k["equity"], tuple(sorted(k["favors"]))) for k in c["considerations"]}
    r.gates["structure"] = {"pass": sig(a) == sig(b) and all(a[k] == b[k] for k in ("question", "options", "facts"))}
    r.delta["target"] = T.lineage.detail.get("target")
    return r
