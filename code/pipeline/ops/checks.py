"""Gates and annotations shared by the operators (OPERATORS-SPEC-v1).

Gates decide the bucket (hard failures only): structure (code), leak (LLM checker), technique (code screen),
setting_adds (LLM probe; failing it makes the output `hard`, not `rejected`).
Annotations never decide anything: verdict_shift (blind solve on X and X'), k_support (the blind solver's
considerations against X''s K). They exist for the pipeline dashboard.
"""
from __future__ import annotations

import json

from bench.schema.pipeline import Scenario

from .solver import SolverSpec, solve


def case_dict(S: Scenario) -> dict:
    c = S.case.model_dump(mode="json", by_alias=True, exclude_none=True)
    c.pop("library", None)
    return c


# ------------------------------------------------------------------ structure helpers (code)
def k_signature(case: dict) -> dict:
    """K-equivalence (Peter, 2026-11-11): same equity ids, favors and weight per consideration."""
    return {k["id"]: (k["equity"], tuple(sorted(k.get("favors") or [])), k["weight"]) for k in case["considerations"]}


def k_equivalent(a: dict, b: dict, option_map: dict[str, str] | None = None) -> tuple[bool, dict]:
    """a, b case dicts. option_map: a-option -> b-option (for permuted options)."""
    om = option_map or {}
    sa = {k: (e, tuple(sorted(om.get(o, o) for o in f)), w) for k, (e, f, w) in k_signature(a).items()}
    sb = k_signature(b)
    diff = {k: {"before": sa.get(k), "after": sb.get(k)} for k in set(sa) | set(sb) if sa.get(k) != sb.get(k)}
    return not diff, diff


def changed_facts(a: dict, b: dict) -> dict:
    fa = {f["id"]: f["fact"] for f in a["facts"]}
    fb = {f["id"]: f["fact"] for f in b["facts"]}
    return {"edited": sorted(k for k in fa if k in fb and fa[k] != fb[k]), "added": sorted(k for k in fb if k not in fa),
            "removed": sorted(k for k in fa if k not in fb)}


def fact_edit_size(a: dict, b: dict) -> dict:
    """Annotation: surface distance (1 - word Jaccard) of each edited fact. Surface only: a one-word negation that flips
    the meaning scores low and a reworded restatement scores high (smoke 2026-11-11), so this is NOT a no-op detector."""
    from pipeline.perturb.overlap import jaccard
    fa = {f["id"]: f["fact"] for f in a["facts"]}
    ch = changed_facts(a, b)
    fb = {f["id"]: f["fact"] for f in b["facts"]}
    return {"surface_distance": {i: round(1 - jaccard(fa[i], fb[i]), 3) for i in ch["edited"]}, "added": ch["added"]}


# ------------------------------------------------------------------ LLM gates
def leak_gate(S: Scenario) -> dict:
    from pipeline.render import answer_leak as AL
    try:
        lk = AL.check(S, None)
        bad = (lk.get("frame") or []) + (lk.get("facts") or [])
        return {"pass": not bad, "items": bad[:5]}
    except Exception as e:                                            # noqa: BLE001
        return {"pass": False, "error": str(e)[:200]}


def technique_gate(S: Scenario) -> dict:
    from pipeline.ingest import technique_check as TC
    txt = json.dumps(case_dict(S), ensure_ascii=False)
    hits = [f.match for f in TC.check(txt) if f.severity == "strip"]
    return {"pass": not hits, "hits": hits[:5]}


def setting_adds_gate(S: Scenario, anchor: Scenario) -> dict:
    """The new setting must not add a strong consideration of its own (Peter: it would change the weighing). Compared
    with the same probe on the anchor, so considerations the probe also finds in the anchor do not count."""
    from pipeline.transfer.build import _against, adds_probe, anchor_baseline
    base = anchor_baseline(anchor)
    anchor_eq = {m.get("equity") for m in base["adds_strong"]}
    c = case_dict(S)
    probe = adds_probe(c)
    strong = [m for m in probe.get("missing", []) if str(m.get("weight", "")).lower() in ("strong", "bar")]
    new = _against(strong, anchor_eq, c["verdict"]["choice"])
    return {"pass": not new, "new_strong": new[:5], "probe_error": probe.get("error")}


# ------------------------------------------------------------------ annotations
def verdict_shift(X: Scenario, Xp: Scenario, expected: str, option_map: dict[str, str] | None = None,
                  spec: SolverSpec | None = None) -> dict:
    """Blind solve on X and X'. flag = the solver agrees with X's verdict on X but does not reach `expected` on X'.
    option_map maps X option ids -> X' ids (permutations)."""
    om = option_map or {}
    sx = solve("verdict", {"case": case_dict(X)}, spec)["answer"]
    sp = solve("verdict", {"case": case_dict(Xp)}, spec)["answer"]
    on_x, on_xp = sx.get("choice"), sp.get("choice")
    agrees_x = on_x == X.case.verdict.choice
    reaches = on_xp == expected
    out = {"solver_on_X": on_x, "solver_on_X_prime": on_xp, "expected_on_X_prime": expected,
           "solver_agrees_on_X": agrees_x, "solver_reaches_expected": reaches,
           "flag": bool(agrees_x and not reaches), "informative": agrees_x}
    out["k_support"] = k_support(case_dict(Xp), sp)
    return out


def k_support(case: dict, solved: dict) -> dict:
    gold = [(k["equity"], set(k["favors"]), k["weight"]) for k in case["considerations"]]
    got = [(k.get("equity"), set(k.get("favors") or []), k.get("weight")) for k in solved.get("considerations") or []]
    return {"n": len(gold),
            "equity_found": sum(1 for e, _, _ in gold if any(e == g for g, _, _ in got)),
            "equity_and_direction": sum(1 for e, f, _ in gold if any(e == g and (f & h) for g, h, _ in got)),
            "exact_weight": sum(1 for e, f, w in gold if any(e == g and (f & h) and w == x for g, h, x in got))}
