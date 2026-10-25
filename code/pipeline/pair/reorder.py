"""Re-order a T scenario's options (option order is free in a T scenario) by writing a *copy* with remapped ids.

The copy gets id `<T id without @v>-ro<k>@v1` where k is the gold option's new 1-based position; option ids are
renumbered O1..On in the new order so id number == position everywhere (case, prose refs {O2}, verdict, flips).
The original scenario is untouched, so other pairs that use it are unaffected.
"""
from __future__ import annotations

import copy
import re
import time

from bench.schema import Case
from bench.schema.pipeline import Lineage, Scenario

REF_O = re.compile(r"\{(O\d+)\}")


def gold_position(T: Scenario) -> int:
    return list(T.case.options).index(T.case.verdict.choice) + 1


def option_perm(T: Scenario, target: int) -> dict[str, str]:
    """old option id -> new id, gold moved to position `target`, the others keep their relative order."""
    ids = list(T.case.options)
    gold = T.case.verdict.choice
    others = [o for o in ids if o != gold]
    order = others[: target - 1] + [gold] + others[target - 1:]
    return {old: f"O{i + 1}" for i, old in enumerate(order)}


def _walk(o, fn):
    if isinstance(o, dict):
        return {k: _walk(v, fn) for k, v in o.items()}
    if isinstance(o, list):
        return [_walk(v, fn) for v in o]
    return fn(o) if isinstance(o, str) else o


def reorder(T: Scenario, target: int) -> tuple[Scenario, dict[str, str]]:
    """Return (scenario with the gold option at `target`, old->new option id map). Same scenario if already there."""
    if gold_position(T) == target:
        return T, {o: o for o in T.case.options}
    m = option_perm(T, target)
    d = T.case.dump()
    ren = lambda s: REF_O.sub(lambda mm: "{" + m[mm.group(1)] + "}" if mm.group(1) in m else mm.group(0), s)
    opts = d["options"]
    d["options"] = {m[k]: opts[k] for k in sorted(opts, key=lambda k: int(m[k][1:]))}
    for c in d["considerations"]:
        c["favors"] = [m[o] for o in c["favors"]]
        if c.get("rules_out"):
            c["rules_out"] = [m[o] for o in c["rules_out"]]
    d["verdict"]["choice"] = m[d["verdict"]["choice"]]
    r = d["reasoning"]
    r["tempting_wrong"]["option"] = m[r["tempting_wrong"]["option"]]
    r["rejected"] = {m[k]: v for k, v in r["rejected"].items()}
    for w in d["flip_conditions"]["would_change"]:
        w["then"] = m[w["then"]]
    for w in d["flip_conditions"].get("watch_for", []):
        w["favors"] = [m[o] for o in w["favors"]]
    for k in ("situation", "lesson", "limits", "reasoning", "considerations", "flip_conditions"):
        d[k] = _walk(d[k], ren)
    base = T.id.split("@")[0]
    nid = f"{base}-ro{target}@v1"
    d["id"] = nid
    case = Case.model_validate(d)
    prov = copy.deepcopy(T.provenance)
    prov.step(id="pair.reorder", operator="pair", notes=f"options re-ordered so the gold option is at position {target}",
              params={"perm": m}, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    S = Scenario(id=nid, family=T.family, split=T.split, domain=T.domain, status="derived", case=case,
                 verdict_tier=T.verdict_tier, basis=T.basis, source=T.source, fact_spans=dict(T.fact_spans),
                 tags=sorted(set(T.tags) | {"reorder"}), lineage=Lineage(parent=T.id, operator="reorder", detail={"perm": m, "gold_position": target}),
                 provenance=prov)
    return S, m
