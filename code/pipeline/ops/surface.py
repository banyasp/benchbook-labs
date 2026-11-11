"""surface_edit: F changes, K held exactly (equity ids, favors, weights), V held (OPERATORS-SPEC-v1 §2).

    reword    same world, new wording (wraps pipeline.perturb.restyle; gold by construction incl. a 1:1 fact map)
    neighbor  same sub-domain, a different situation, new facts (writer prompt neighbor.v1.md)
    transfer  another sub-domain, new facts (writer prompt = pipeline/transfer/prompts/write.v1.md, unchanged)
    match_options  only the option texts change: rewritten as a matched set so the gold does not stand out by length,
              detail or tone (2026-11-11, Peter: fix the gold-is-longest cue at the anchors before deriving pairs; M12).
              F, Q apart from option wording, K, V and the gold tier held. Gates: structure (code), option_form (code:
              word-count spread), option_equivalence (LLM checker: each option still the same course of action), leak,
              technique.

setting = {"subdomain", "title", "sketch"} given by the caller (e.g. parsed from a sketch file), or "propose": a writer
proposes one (propose_setting.v1.md) and the proposal is recorded in the step's args.

Gates: structure (code: K-equivalence + verdict, enforced on the writer's reply), leak, technique, setting_adds
(neighbor / transfer; failing it makes the output `hard`). Annotation (optional, `annotate=True`): verdict_shift
(blind solve on X and X'), never a gate (Peter, 2026-11-11).
"""
from __future__ import annotations

import json
from pathlib import Path

from bench.schema.pipeline import Lineage, Scenario

from . import checks as CK
from .record import OpResult, dump_delta, llm_writer, new_id

PROMPTS = Path(__file__).resolve().parent / "prompts"
TRANSFER_PROMPTS = Path(__file__).resolve().parents[1] / "transfer" / "prompts"
WRITER_PROMPT = {"neighbor": PROMPTS / "neighbor.v1.md", "transfer": TRANSFER_PROMPTS / "write.v1.md"}


def propose_setting(X: Scenario, mode: str, subdomain: str | None, role: str) -> tuple[dict | None, list]:
    from pipeline.transfer.build import anchor_case, llm_json
    need = ("subdomain", "title", "sketch")
    user = (f"MODE: {mode}\nANCHOR SUB-DOMAIN: {X.case.library.get('domain') if isinstance(X.case.library, dict) else X.domain}"
            + (f"\nREQUESTED SUB-DOMAIN: {subdomain}" if subdomain else "")
            + "\n\nANCHOR CASE (JSON):\n" + json.dumps(anchor_case(X), ensure_ascii=False, indent=1))
    return llm_json(role, (PROMPTS / "propose_setting.v1.md").read_text(), user,
                    lambda o: [f"missing {k}" for k in need if not o.get(k)])


def rewrite_world(X: Scenario, mode: str, setting: dict, role: str, tries: int) -> tuple[dict | None, list]:
    from pipeline.transfer.build import anchor_case, llm_json, structure_errors
    ref = anchor_case(X)
    user = ("ANCHOR CASE (JSON):\n" + json.dumps(ref, ensure_ascii=False, indent=1)
            + f"\n\nSKETCH OF THE SISTER (sub-domain: {setting['subdomain']}; title: {setting['title']}):\n{setting['sketch']}")
    if setting.get("anchor_sketch"):
        user += f"\n\nANCHOR SUMMARY FROM THE SKETCH FILE:\n{setting['anchor_sketch'][:3000]}"
    return llm_json(role, WRITER_PROMPT[mode].read_text(), user, lambda o: structure_errors(o, ref), tries=tries)


def surface_edit(X: Scenario, store, *, mode: str, setting=None, role: str = "transfer_writer", tries: int = 3,
                 annotate: bool = False, seed: int = 0) -> OpResult:
    args = {"mode": mode, "setting": setting, "annotate": annotate, "seed": seed}
    if mode == "reword":
        return _reword(X, store, args, seed, annotate)
    if mode == "match_options":
        return _match_options(X, store, args, role, tries)
    if mode not in ("neighbor", "transfer"):
        raise ValueError(f"unknown surface_edit mode {mode!r}")
    log_all = []
    if setting is None or setting == "propose" or (isinstance(setting, dict) and setting.get("propose")):
        sub = setting.get("subdomain") if isinstance(setting, dict) else None
        prop, plog = propose_setting(X, mode, sub, role)
        log_all += [{"stage": "propose", **x} for x in plog]
        if prop is None:
            return OpResult("surface_edit", mode, args, None, writer=llm_writer(role, PROMPTS / "propose_setting.v1.md"), log=log_all)
        setting = {**prop, "proposed": True}
        args["setting"] = setting
    obj, wlog = rewrite_world(X, mode, setting, role, tries)
    log_all += [{"stage": "write", **x} for x in wlog]
    writer = llm_writer(role, WRITER_PROMPT[mode], tries=len(wlog),
                        **({"setting_prompt": f"propose_setting.v1.md@{_sha(PROMPTS / 'propose_setting.v1.md')}"} if setting.get("proposed") else {}))
    if obj is None:
        return OpResult("surface_edit", mode, args, None, writer=writer, log=log_all)
    sid = new_id(store, X.family, "surface_edit", mode)
    from pipeline.transfer.build import to_scenario
    S = to_scenario(obj, sid, family=X.family, parent=X.id, operator="transfer" if mode == "transfer" else "neighbor",
                    detail={"subdomain": setting["subdomain"], "title": setting["title"]},
                    domain=setting["subdomain"] if mode == "transfer" else X.domain, anchor=X)
    S.split = X.split
    S.basis = f"{mode} of {X.id}: considerations, weighing and verdict carried over"
    S.tags = sorted(set(S.tags) - {"transfer"} | {mode, "synthetic"})
    S.lineage = Lineage(parent=X.id, operator=mode)
    g, gx = (lambda i: f"{sid}/{i}"), (lambda i: f"{X.id}/{i}")
    delta = {"relation": "follows", "choice": g(S.case.verdict.choice), "gold_tier": "by-construction",
             "options_map": {g(o): gx(o) for o in S.case.options},
             "consideration_map": {"matched": [{"live": g(c.id), "case": gx(c.id)} for c in S.case.considerations]},
             "fact_map": None, "fact_map_note": "new facts: they correspond to X's facts only through the considerations that cite them"}
    r = OpResult("surface_edit", mode, args, S, delta=delta, writer=writer, log=log_all)
    ok, diff = CK.k_equivalent(CK.case_dict(X), CK.case_dict(S))
    r.gates["structure"] = {"pass": ok and S.case.verdict.choice == X.case.verdict.choice, "k_diff": diff}
    r.gates["leak"] = CK.leak_gate(S)
    r.gates["technique"] = CK.technique_gate(S)
    r.gates["setting_adds"] = CK.setting_adds_gate(S, X)
    if annotate:
        r.annotations["verdict_shift"] = CK.verdict_shift(X, S, expected=S.case.verdict.choice)
        r.solver = {"backend": "llm", "role": "transfer_checker", "used_for": "annotation"}
    return r


def _sha(p: Path) -> str:
    from .record import file_sha
    return file_sha(p)


def _reword(X: Scenario, store, args: dict, seed: int, annotate: bool) -> OpResult:
    from pipeline.perturb.common import seed_rng
    from pipeline.perturb.restyle import restyle
    T, partial = restyle(X, store, seed_rng(X.id, "restyle", seed))
    writer = llm_writer("perturber", Path(__file__).resolve().parents[1] / "perturb" / "prompts" / "rewrite.md")
    r = OpResult("surface_edit", "reword", args, T, delta=dump_delta(partial), writer=writer)
    ok, diff = CK.k_equivalent(CK.case_dict(X), CK.case_dict(T))
    r.gates["structure"] = {"pass": ok and T.case.verdict.choice == X.case.verdict.choice, "k_diff": diff}
    r.gates["leak"] = CK.leak_gate(T)
    r.gates["technique"] = CK.technique_gate(T)
    if annotate:
        r.annotations["verdict_shift"] = CK.verdict_shift(X, T, expected=T.case.verdict.choice)
        r.solver = {"backend": "llm", "role": "transfer_checker", "used_for": "annotation"}
    return r


# ------------------------------------------------------------------ match_options
def frame_of(case: dict) -> dict:
    return {k: case.get(k) for k in ("title", "setting", "decider", "agent", "agent_role", "situation", "question")}


MAX_SPREAD = 1.3          # longest / shortest option, in words


def option_words(texts: dict[str, str]) -> dict[str, int]:
    return {k: len(v.split()) for k, v in texts.items()}


def option_form(texts: dict[str, str], gold: str) -> dict:
    w = option_words(texts)
    spread = max(w.values()) / max(1, min(w.values()))
    rank = sorted(w.values(), reverse=True).index(w[gold]) + 1
    return {"pass": spread <= MAX_SPREAD, "words": w, "spread": round(spread, 2), "gold_rank": rank,
            "gold_uniquely_longest": rank == 1 and list(w.values()).count(w[gold]) == 1}


def _match_options(X: Scenario, store, args: dict, role: str, tries: int) -> OpResult:
    import copy
    from pipeline.transfer.build import llm_json
    case = CK.case_dict(X)
    gold = case["verdict"]["choice"]
    old = {k: o["do"] for k, o in case["options"].items()}
    before = option_form(old, gold)
    if before["spread"] <= 1.1 and not before["gold_uniquely_longest"]:
        return OpResult("surface_edit", "match_options", args, None, skipped=f"already matched (spread {before['spread']})")
    view = {"frame": frame_of(case), "facts": case["facts"], "options": old, "chosen": gold}
    user = "SCENARIO (JSON):\n" + json.dumps(view, ensure_ascii=False, indent=1)

    def check(o):
        new = o.get("options") or {}
        errs = [f"missing option {k}" for k in old if not str(new.get(k, "")).strip()]
        errs += [f"unknown option {k}" for k in new if k not in old]
        if not errs:
            f = option_form({k: str(new[k]) for k in old}, gold)
            if not f["pass"]:
                errs.append(f"options differ too much in length (word counts {f['words']}); bring every option within "
                            f"about 15% of the median")
        return errs

    obj, log = llm_json(role, (PROMPTS / "match_options.v1.md").read_text(), user, check, tries=tries)
    writer = llm_writer(role, PROMPTS / "match_options.v1.md", tries=len(log))
    if obj is None:
        return OpResult("surface_edit", "match_options", args, None, writer=writer, log=log)
    new = {k: str(obj["options"][k]).strip() for k in old}
    trial = copy.deepcopy(case)
    for k in old:
        trial["options"][k]["do"] = new[k]
    sid = new_id(store, X.family, "surface_edit", "match_options")
    trial["id"] = sid
    from bench.schema.case import Case
    S = Scenario(id=sid, family=X.family, split=X.split, domain=X.domain, status="derived", case=Case.model_validate(trial),
                 verdict_tier=X.verdict_tier, basis=X.basis, source=X.source, fact_spans=dict(X.fact_spans),
                 tags=sorted(set(X.tags) | {"options-matched"}), provenance=copy.deepcopy(X.provenance))
    S.lineage.operator = "surface_edit"
    g, gx = (lambda i: f"{sid}/{i}"), (lambda i: f"{X.id}/{i}")
    after = option_form(new, gold)
    delta = {"relation": "follows", "choice": g(gold), "gold_tier": X.verdict_tier,
             "options_map": {g(k): gx(k) for k in old},
             "option_text": {k: {"before": old[k], "after": new[k]} for k in old},
             "option_form": {"before": before, "after": after},
             "fact_map": {"matched": [{"live": g(f["id"]), "case": gx(f["id"])} for f in case["facts"]]},
             "consideration_map": {"matched": [{"live": g(c["id"]), "case": gx(c["id"])} for c in case["considerations"]]},
             "frame": {"question": "same", "decider": "same", "role": "same", "options": "reworded"},
             "writer_notes": obj.get("notes")}
    r = OpResult("surface_edit", "match_options", args, S, delta=delta, writer=writer, log=log)
    sc = CK.case_dict(S)
    ok, diff = CK.k_equivalent(case, sc)
    same_rest = all(sc[k] == case[k] for k in case if k not in ("id", "options"))
    same_moves = all(sc["options"][k]["move"] == case["options"][k]["move"] for k in old)
    r.gates["structure"] = {"pass": ok and same_rest and same_moves and sc["verdict"]["choice"] == gold, "k_diff": diff,
                            "other_fields_unchanged": same_rest, "moves_unchanged": same_moves}
    r.gates["option_form"] = after
    r.gates["option_equivalence"] = option_equivalence(case, old, new)
    r.gates["leak"] = CK.leak_gate(S)
    r.gates["technique"] = CK.technique_gate(S)
    return r


def option_equivalence(case: dict, old: dict, new: dict, role: str = "transfer_checker") -> dict:
    from pipeline.transfer.build import llm_json
    view = {"frame": frame_of(case), "facts": case["facts"],
            "options": {k: {"original": old[k], "rewritten": new[k]} for k in old}}
    obj, log = llm_json(role, (PROMPTS / "option_equivalence.v1.md").read_text(),
                        "SCENARIO (JSON):\n" + json.dumps(view, ensure_ascii=False, indent=1),
                        lambda o: [f"missing {k}" for k in old if k not in (o.get("options") or {})])
    if obj is None:
        return {"pass": False, "error": "checker failed", "log": log}
    per = obj["options"]
    return {"pass": all(bool(per[k].get("same")) for k in old), "per_option": per,
            "checker": llm_writer(role, PROMPTS / "option_equivalence.v1.md")}
