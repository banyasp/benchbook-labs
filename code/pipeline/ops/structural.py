"""structural_edit: F changes and K changes (OPERATORS-SPEC-v1 §3). v1 builds the modes that need no solver:

    flip      make one Φ would_change item true; V := its `then` (by construction), via = the item.
              realization plain    -> writer prompt pipeline/transfer/prompts/flip.v1.md (<= max_facts facts edited)
              realization indirect -> wraps pipeline.perturb.flip (indirect realization + light restyle, full gold maps)
    target_f  realize one Φ would_not_change item; V held by construction (relation follows, via = the item). Skipped
              when the item already holds in X (a no-op; checked by the condition verifier).

Gates: structure (code), condition_realized (the strict condition verifier on X''s facts: a check of the edit, not a
verdict solver), leak, technique. Annotation (optional): verdict_shift (does a blind solver reach the expected V?).
target_k, general target_f and lookalike beyond Φ need a solver: not built (v1 scope).
"""
from __future__ import annotations

import json
from pathlib import Path

from bench.schema.pipeline import Lineage, Scenario

from . import checks as CK
from .record import OpResult, dump_delta, llm_writer, new_id

PROMPTS = Path(__file__).resolve().parent / "prompts"
FLIP_PROMPT = Path(__file__).resolve().parents[1] / "transfer" / "prompts" / "flip.v1.md"


def facts_text(case: dict) -> str:
    return "\n".join(f"{f['id']}: {f['fact']}" for f in case["facts"])


def _phi_item(case: dict, kind: str, item_id: str) -> dict | None:
    return next((w for w in case["flip_conditions"].get(kind, []) if w["id"] == item_id), None)


def _same_frame_errors(old: dict, new: dict) -> list[str]:
    errs = []
    if new.get("question") != old["question"]:
        errs.append("keep `question` exactly as it is")
    if {k: v.get("do") for k, v in new.get("options", {}).items()} != {k: v["do"] for k, v in old["options"].items()}:
        errs.append("keep every option exactly as it is (same ids and `do` text)")
    return errs


def _fact_budget_errors(old: dict, new: dict, max_facts: int) -> list[str]:
    ch = CK.changed_facts(old, new)
    n = len(ch["edited"]) + len(ch["added"])
    errs = [f"edit or add at most {max_facts} facts; you changed {ch}"] if n > max_facts else []
    if ch["removed"]:
        errs.append(f"do not remove facts ({ch['removed']})")
    if n == 0:
        errs.append("no fact changed: the condition must hold as a fact")
    return errs


def _delta_facts(sid: str, xid: str, old: dict, new: dict) -> dict:
    ch = CK.changed_facts(old, new)
    g, gx = (lambda i: f"{sid}/{i}"), (lambda i: f"{xid}/{i}")
    return {"matched": [{"live": g(f["id"]), "case": gx(f["id"])} for f in new["facts"]
                        if f["id"] not in ch["edited"] and f["id"] not in ch["added"]],
            "corresponding": [{"live": g(i), "case": gx(i)} for i in ch["edited"]],
            "live_only": [g(i) for i in ch["added"]], "case_only": [gx(i) for i in ch["removed"]]}


def _delta_k(sid: str, xid: str, old: dict, new: dict) -> dict:
    g, gx = (lambda i: f"{sid}/{i}"), (lambda i: f"{xid}/{i}")
    o = {k["id"]: k for k in old["considerations"]}
    n = {k["id"]: k for k in new["considerations"]}
    same = lambda a, b: (a["equity"], sorted(a["favors"]), a["weight"], sorted(a["facts"])) == (b["equity"], sorted(b["favors"]), b["weight"], sorted(b["facts"]))
    return {"matched": [{"live": g(i), "case": gx(i)} for i in n if i in o and same(o[i], n[i])],
            "corresponding": [{"live": g(i), "case": gx(i)} for i in n if i in o and not same(o[i], n[i])],
            "live_only": [g(i) for i in n if i not in o], "case_only": [gx(i) for i in o if i not in n]}


def _scenario(X: Scenario, sid: str, obj: dict, op_label: str, basis: str) -> Scenario:
    from pipeline.transfer.build import to_scenario
    S = to_scenario(obj, sid, family=X.family, parent=X.id, operator=op_label, detail={}, domain=X.domain, anchor=X)
    S.split = X.split
    S.basis = basis
    S.tags = sorted(set(S.tags) - {"transfer", "transfer-flip"} | {op_label, "synthetic"})
    S.lineage = Lineage(parent=X.id, operator=op_label)
    S.fact_spans = {k: v for k, v in X.fact_spans.items() if k in {f.id for f in S.case.facts}}
    return S


def structural_edit(X: Scenario, store, *, mode: str, phi: str, realization: str = "plain", max_facts: int = 2,
                    role: str = "transfer_writer", tries: int = 3, annotate: bool = False, seed: int = 0) -> OpResult:
    if mode == "flip":
        if realization == "indirect":
            return _flip_indirect(X, store, phi, max_facts, annotate, seed)
        return _flip_plain(X, store, phi, max_facts, role, tries, annotate)
    if mode == "target_f":
        return _target_f_noflip(X, store, phi, max_facts, role, tries, annotate)
    raise ValueError(f"structural_edit mode {mode!r} is not built in v1 (needs a solver)")


def _flip_plain(X, store, phi, max_facts, role, tries, annotate) -> OpResult:
    from pipeline.transfer.build import llm_json, structure_errors
    args = {"mode": "flip", "target": {"phi": phi}, "realization": "plain", "max_facts": max_facts, "annotate": annotate}
    case = CK.case_dict(X)
    item = _phi_item(case, "would_change", phi)
    if item is None:
        return OpResult("structural_edit", "flip", args, None, skipped=f"no would_change item {phi}")
    if item["then"] == case["verdict"]["choice"]:
        return OpResult("structural_edit", "flip", args, None, skipped=f"{phi}.then is already the verdict")

    def check(o):
        errs = structure_errors(o, case, same_k=False, verdict=item["then"])
        errs += _same_frame_errors(case, o)
        errs += _fact_budget_errors(case, o, max_facts)
        if {k["id"]: k["equity"] for k in o.get("considerations", [])} != {k["id"]: k["equity"] for k in case["considerations"]}:
            errs.append("keep every consideration id with its equity")
        return errs

    user = ("CASE (JSON):\n" + json.dumps(case, ensure_ascii=False, indent=1)
            + "\n\nFLIP CONDITION TO MAKE TRUE:\n" + json.dumps(item, ensure_ascii=False))
    obj, log = llm_json(role, FLIP_PROMPT.read_text(), user, check, tries=tries)
    writer = llm_writer(role, FLIP_PROMPT, tries=len(log))
    if obj is None:
        return OpResult("structural_edit", "flip", args, None, writer=writer, log=log)
    sid = new_id(store, X.family, "structural_edit", "flip")
    S = _scenario(X, sid, obj, "flip", f"flip of {X.id}: {phi} made true, verdict = its then (by construction)")
    nc = CK.case_dict(S)
    delta = {"relation": "flips", "via": [f"{X.id}/{phi}"], "choice": f"{sid}/{item['then']}", "gold_tier": "by-construction",
             "options_map": {f"{sid}/{o}": f"{X.id}/{o}" for o in nc["options"]},
             "fact_map": _delta_facts(sid, X.id, case, nc), "consideration_map": _delta_k(sid, X.id, case, nc),
             "touched": {"item": f"{X.id}/{phi}", "condition": item["if"], "how": "realized plainly by editing or adding facts"}}
    r = OpResult("structural_edit", "flip", args, S, delta=delta, writer=writer, log=log)
    r.gates["structure"] = {"pass": True}
    r.annotations["fact_edit"] = CK.fact_edit_size(case, nc)
    _realized_gate(r, item["if"], nc)
    r.gates["leak"] = CK.leak_gate(S)
    r.gates["technique"] = CK.technique_gate(S)
    if annotate:
        r.annotations["verdict_shift"] = CK.verdict_shift(X, S, expected=item["then"])
        r.solver = {"backend": "llm", "role": "transfer_checker", "used_for": "annotation"}
    return r


def _realized_gate(r: OpResult, if_text: str, new_case: dict):
    from .solver import solve
    try:
        v = solve("condition_holds", {"if": if_text, "facts_text": facts_text(new_case)})["answer"]
        r.gates["condition_realized"] = {"pass": bool(v.get("holds")), "why": v.get("why", "")[:300]}
    except Exception as e:                                                # noqa: BLE001
        r.gates["condition_realized"] = {"pass": False, "error": str(e)[:200]}


def _flip_indirect(X, store, phi, max_facts, annotate, seed) -> OpResult:
    from pipeline.perturb.common import seed_rng
    from pipeline.perturb.flip import flip
    args = {"mode": "flip", "target": {"phi": phi}, "realization": "indirect", "max_facts": max_facts, "annotate": annotate,
            "seed": seed, "note": "pipeline.perturb.flip also restyles the whole scenario lightly"}
    T, partial = flip(X, store, seed_rng(X.id, "flip", phi, seed), item=phi, realization="indirect")
    writer = llm_writer("perturber", Path(__file__).resolve().parents[1] / "perturb" / "prompts" / "realize_flip.md")
    r = OpResult("structural_edit", "flip", args, T, delta=dump_delta(partial), writer=writer)
    r.gates["structure"] = {"pass": True}
    r.gates["leak"] = CK.leak_gate(T)
    r.gates["technique"] = CK.technique_gate(T)
    if annotate:
        r.annotations["verdict_shift"] = CK.verdict_shift(X, T, expected=T.case.verdict.choice)
        r.solver = {"backend": "llm", "role": "transfer_checker", "used_for": "annotation"}
    return r


def _target_f_noflip(X, store, phi, max_facts, role, tries, annotate) -> OpResult:
    from pipeline.transfer.build import llm_json, structure_errors
    from .solver import solve
    args = {"mode": "target_f", "target": {"phi": phi}, "realization": "plain", "max_facts": max_facts, "annotate": annotate}
    case = CK.case_dict(X)
    item = _phi_item(case, "would_not_change", phi)
    if item is None:
        return OpResult("structural_edit", "target_f", args, None, skipped=f"no would_not_change item {phi}")
    pre = solve("condition_holds", {"if": item["if"], "facts_text": facts_text(case)})["answer"]
    if pre.get("holds"):
        return OpResult("structural_edit", "target_f", args, None,
                        skipped=f"no-op: {phi} already holds in X ({pre.get('why', '')[:160]})")

    def check(o):
        errs = structure_errors(o, case, same_k=True)                  # K exact + same verdict
        errs += _same_frame_errors(case, o)
        errs += _fact_budget_errors(case, o, max_facts)
        if _phi_item(o, "would_not_change", phi) is not None:
            errs.append(f"remove the realized would_not_change item {phi}")
        return errs

    prompt = PROMPTS / "noflip.v1.md"
    user = ("CASE (JSON):\n" + json.dumps(case, ensure_ascii=False, indent=1)
            + "\n\nWOULD_NOT_CHANGE ITEM TO MAKE TRUE:\n" + json.dumps(item, ensure_ascii=False))
    obj, log = llm_json(role, prompt.read_text(), user, check, tries=tries)
    writer = llm_writer(role, prompt, tries=len(log))
    if obj is None:
        return OpResult("structural_edit", "target_f", args, None, writer=writer, log=log)
    sid = new_id(store, X.family, "structural_edit", "target_f")
    S = _scenario(X, sid, obj, "noflip", f"target_f of {X.id}: would_not_change {phi} made true, verdict held (by construction)")
    nc = CK.case_dict(S)
    delta = {"relation": "follows", "via": [f"{X.id}/{phi}"], "choice": f"{sid}/{nc['verdict']['choice']}",
             "gold_tier": X.verdict_tier, "options_map": {f"{sid}/{o}": f"{X.id}/{o}" for o in nc["options"]},
             "fact_map": _delta_facts(sid, X.id, case, nc), "consideration_map": _delta_k(sid, X.id, case, nc),
             "touched": {"item": f"{X.id}/{phi}", "condition": item["if"], "how": "would_not_change realized by editing or adding facts"}}
    r = OpResult("structural_edit", "target_f", args, S, delta=delta, writer=writer, log=log,
                 intended={"phi": phi, "precheck": {"holds": False, "why": pre.get("why", "")[:300]}})
    r.gates["structure"] = {"pass": True}
    r.annotations["fact_edit"] = CK.fact_edit_size(case, nc)
    _realized_gate(r, item["if"], nc)
    r.gates["leak"] = CK.leak_gate(S)
    r.gates["technique"] = CK.technique_gate(S)
    if annotate:
        r.annotations["verdict_shift"] = CK.verdict_shift(X, S, expected=nc["verdict"]["choice"])
        r.solver = {"backend": "llm", "role": "transfer_checker", "used_for": "annotation"}
    return r
