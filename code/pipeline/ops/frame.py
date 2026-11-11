"""frame_edit: Q changes (OPERATORS-SPEC-v1 §4). v1 builds `drop_option` only (remove a non-gold option; V held by
construction). Adding an option the source considered and rejected needs the source text and is not built yet;
decide <-> advise awaits Peter's ruling; the other targets need a solver (later).

drop_option, in code: the option leaves `options`; considerations lose it from `favors` / `rules_out` (a consideration
left favoring nothing, or a bar left ruling out nothing, is dropped: K changes, recorded in the delta); would_change
items whose `then` is the option are dropped; watch_for items lose it; `rejected` loses it. An LLM then rewrites only
the prose fields that still mention the removed course (and a new tempting_wrong if needed). Options are renumbered
O1..On-1 (permute's renaming).
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from bench.schema import Case
from bench.schema.pipeline import Scenario

from . import checks as CK
from .permute import apply_order
from .record import OpResult, llm_writer, new_id

PROMPTS = Path(__file__).resolve().parent / "prompts"
SKIP_KEYS = {"id", "equity", "weight", "favors", "rules_out", "move", "irreversible", "to", "kind", "status", "choice",
             "then", "option", "decisive", "facts", "basis", "agent_role", "library", "title"}


def text_fields(d, path=""):
    """(path, text) for every prose string leaf of a case dict."""
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            if k in SKIP_KEYS and not (path.endswith("reasoning.rejected") or path == "options"):
                continue
            out += text_fields(v, f"{path}.{k}" if path else k)
    elif isinstance(d, list):
        for x in d:
            key = x.get("id") if isinstance(x, dict) and "id" in x else str(d.index(x))
            out += text_fields(x, f"{path}[{key}]")
    elif isinstance(d, str):
        out.append((path, d))
    return out


def set_path(d: dict, path: str, value: str):
    parts = re.findall(r"[^.\[\]]+|\[[^\]]+\]", path)
    cur = d
    for i, p in enumerate(parts):
        last = i == len(parts) - 1
        if p.startswith("["):
            key = p[1:-1]
            nxt = next((x for x in cur if isinstance(x, dict) and x.get("id") == key), None)
            if nxt is None:
                nxt = cur[int(key)]
            if last:
                raise ValueError(f"path {path} ends in a list item")
            cur = nxt
        else:
            if last:
                if p not in cur or not isinstance(cur[p], str):
                    raise ValueError(f"unknown text field {path}")
                cur[p] = value
            else:
                cur = cur[p]


def remove_structurally(case: dict, k: str) -> tuple[dict, dict]:
    d = copy.deepcopy(case)
    info = {"removed_option": k, "removed_do": d["options"][k]["do"], "dropped_considerations": [],
            "dropped_would_change": [], "dropped_watch_for": [], "tempting_wrong_needs_new": False}
    del d["options"][k]
    keep = []
    for c in d["considerations"]:
        c["favors"] = [o for o in c.get("favors", []) if o != k]
        if c.get("rules_out"):
            c["rules_out"] = [o for o in c["rules_out"] if o != k]
            if not c["rules_out"]:
                c.pop("rules_out")
        bar_empty = c.get("weight") == "bar" and not c.get("rules_out")
        if not c["favors"] or bar_empty:
            info["dropped_considerations"].append(c["id"])
        else:
            keep.append(c)
    d["considerations"] = keep
    d["verdict"]["decisive"] = [x for x in d["verdict"]["decisive"] if x not in info["dropped_considerations"]]
    d["reasoning"]["rejected"] = {o: v for o, v in d["reasoning"]["rejected"].items() if o != k}
    if d["reasoning"]["tempting_wrong"]["option"] == k:
        info["tempting_wrong_needs_new"] = True
    fc = d["flip_conditions"]
    info["dropped_would_change"] = [w["id"] for w in fc["would_change"] if w["then"] == k]
    fc["would_change"] = [w for w in fc["would_change"] if w["then"] != k]
    for w in fc.get("watch_for", []):
        w["favors"] = [o for o in w.get("favors", []) if o != k]
    info["dropped_watch_for"] = [w["id"] for w in fc.get("watch_for", []) if not w["favors"]]
    fc["watch_for"] = [w for w in fc.get("watch_for", []) if w["favors"]]
    # prose references to dropped items must go too
    info["dropped_refs"] = [k] + info["dropped_considerations"] + info["dropped_would_change"] + info["dropped_watch_for"]
    return d, info


def mentions(text: str, refs: list[str]) -> bool:
    return any(re.search(rf"(?<![A-Za-z0-9]){re.escape(r)}(?![0-9])", text) for r in refs)


def drop_option(X: Scenario, store, *, option: str, role: str = "transfer_writer", tries: int = 3) -> OpResult:
    args = {"target": "drop_option", "option": option}
    case = CK.case_dict(X)
    gold = case["verdict"]["choice"]
    if option not in case["options"]:
        return OpResult("frame_edit", "drop_option", args, None, skipped=f"no option {option}")
    if option == gold:
        return OpResult("frame_edit", "drop_option", args, None, skipped="the gold option cannot be dropped without a solver (v1)")
    if len(case["options"]) < 3:
        return OpResult("frame_edit", "drop_option", args, None, skipped="needs at least 3 options")
    d, info = remove_structurally(case, option)
    from pipeline.transfer.build import llm_json
    fields = [(p, t) for p, t in text_fields(d) if not p.startswith("options")]
    refs = info["dropped_refs"]

    def check(o):
        errs = []
        if not isinstance(o, dict) or not isinstance(o.get("fields", {}), dict):
            return ["reply must be {\"fields\": {...}, \"tempting_wrong\": ...}"]
        trial = copy.deepcopy(d)
        for p, t in (o.get("fields") or {}).items():
            try:
                set_path(trial, p, t)
            except Exception as e:                                       # noqa: BLE001
                errs.append(str(e))
        if info["tempting_wrong_needs_new"]:
            tw = o.get("tempting_wrong") or {}
            if tw.get("option") not in trial["options"] or tw.get("option") == gold:
                errs.append(f"tempting_wrong.option must be a remaining non-verdict option: {sorted(set(trial['options']) - {gold})}")
            else:
                trial["reasoning"]["tempting_wrong"] = {"option": tw["option"], "pull": tw.get("pull", ""), "why_wrong": tw.get("why_wrong", "")}
        left = [p for p, t in text_fields(trial) if mentions(t, refs)]
        if left:
            errs.append(f"these fields still mention a removed item ({', '.join(refs)}): {left[:8]}")
        if not errs:
            o["_trial"] = trial
        return errs

    user = (f"REMOVED COURSE: {option}: {info['removed_do']}\n"
            f"Also removed with it (no longer exist; drop any reference): {', '.join(refs[1:]) or 'none'}\n"
            f"tempting_wrong must be replaced: {'yes' if info['tempting_wrong_needs_new'] else 'no'}\n\n"
            "SCENARIO (JSON, without the removed option):\n" + json.dumps(d, ensure_ascii=False, indent=1)
            + "\n\nTEXT FIELDS (path: text):\n" + "\n".join(f"{p}: {t}" for p, t in fields))
    prompt = PROMPTS / "drop_option.v1.md"
    obj, log = llm_json(role, prompt.read_text(), user, check, tries=tries)
    writer = llm_writer(role, prompt, tries=len(log))
    if obj is None:
        return OpResult("frame_edit", "drop_option", args, None, writer=writer, log=log)
    trial = obj["_trial"]
    order = [o for o in case["options"] if o != option]
    trial, mp = apply_order(trial, "options", order)
    sid = new_id(store, X.family, "frame_edit", "drop_option")
    trial["id"] = sid
    S = Scenario(id=sid, family=X.family, split=X.split, domain=X.domain, status="derived", case=Case.model_validate(trial),
                 verdict_tier=X.verdict_tier, basis=X.basis, source=X.source, fact_spans=dict(X.fact_spans),
                 tags=sorted(set(X.tags)), provenance=copy.deepcopy(X.provenance))
    S.lineage.operator = "frame_edit"
    g, gx = (lambda i: f"{sid}/{i}"), (lambda i: f"{X.id}/{i}")
    kept_k = [c["id"] for c in trial["considerations"]]
    delta = {"relation": "follows", "choice": g(trial["verdict"]["choice"]), "gold_tier": X.verdict_tier,
             "options_map": {g(mp[o]): gx(o) for o in order}, "removed_options": [gx(option)],
             "fact_map": {"matched": [{"live": g(f["id"]), "case": gx(f["id"])} for f in trial["facts"]]},
             "consideration_map": {"matched": [{"live": g(c), "case": gx(c)} for c in kept_k],
                                   "case_only": [gx(c) for c in info["dropped_considerations"]]},
             "dropped": {k: v for k, v in info.items() if k.startswith("dropped_") and k != "dropped_refs"},
             "frame": {"question": "same", "decider": "same", "role": "same", "options": "subset"}}
    r = OpResult("frame_edit", "drop_option", args, S, delta=delta, writer=writer, log=log)
    r.gates["structure"] = {"pass": S.case.verdict.choice == mp[gold] and len(S.case.options) == len(case["options"]) - 1}
    r.gates["leak"] = CK.leak_gate(S)
    r.gates["technique"] = CK.technique_gate(S)
    return r
