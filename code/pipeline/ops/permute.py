"""permute: reorder the items of one list (options, facts or considerations) and renumber ids so that id number ==
position. Code only; the gold follows by construction (OPERATORS-SPEC-v1 §1).

    order: explicit list of the old ids in their new order | "random" (seeded) | {"gold_to": k} (options only)

Ids are renamed in every structured field and in braced prose references ({O2}, {F3}, {C1}); option ids are also
renamed as bare tokens (O2), as balance_options does, because extracted prose names options that way.
"""
from __future__ import annotations

import copy
import random
import re

from bench.schema import Case
from bench.schema.pipeline import Scenario

from .record import OpResult, code_writer, new_id

PREFIX = {"options": "O", "facts": "F", "considerations": "C"}


def current_ids(case: dict, target: str) -> list[str]:
    if target == "options":
        return list(case["options"])
    return [x["id"] for x in case[target]]


def resolve_order(ids: list[str], order, case: dict, seed: int) -> list[str]:
    if order == "random":
        new = ids[:]
        random.Random(seed).shuffle(new)
        return new
    if isinstance(order, dict) and "gold_to" in order:
        gold = case["verdict"]["choice"]
        others = [o for o in ids if o != gold]
        k = int(order["gold_to"])
        if not 1 <= k <= len(ids):
            raise ValueError(f"gold_to {k} outside 1..{len(ids)}")
        return others[:k - 1] + [gold] + others[k - 1:]
    if sorted(order) != sorted(ids):
        raise ValueError(f"order {order} must be a permutation of {ids}")
    return list(order)


def rename(obj, mp: dict[str, str], prefix: str, bare: bool):
    """Two-phase rename of ids (old -> new) in keys and strings."""
    tok = re.compile(rf"\b{prefix}(\d+)\b") if bare else re.compile(rf"(?<=\{{){prefix}(\d+)(?=\}})")
    exact = re.compile(rf"^{prefix}\d+$")
    tmp = {k: f"\x00{prefix}{v[len(prefix):]}\x00" for k, v in mp.items()}
    back = {v: mp[k] for k, v in tmp.items()}

    def sub(s: str, table) -> str:
        if exact.match(s):
            return table.get(s, s)
        return tok.sub(lambda m: table.get(m.group(0), m.group(0)), s)

    def walk(o, table):
        if isinstance(o, dict):
            return {(sub(k, table) if isinstance(k, str) else k): walk(v, table) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(x, table) for x in o]
        if isinstance(o, str):
            return sub(o, table)
        return o

    once = walk(obj, tmp)
    restore = re.compile(f"\x00{prefix}\\d+\x00")

    def walk2(o):
        if isinstance(o, dict):
            return {(restore.sub(lambda m: back[m.group(0)], k) if isinstance(k, str) else k): walk2(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk2(x) for x in o]
        if isinstance(o, str):
            return restore.sub(lambda m: back[m.group(0)], o)
        return o

    return walk2(once)


def apply_order(case: dict, target: str, new_order: list[str]) -> tuple[dict, dict[str, str]]:
    p = PREFIX[target]
    mp = {old: f"{p}{i}" for i, old in enumerate(new_order, 1)}
    c = rename(copy.deepcopy(case), mp, p, bare=(target == "options"))
    if target == "options":
        c["options"] = {k: c["options"][k] for k in sorted(c["options"], key=lambda k: int(k[1:]))}
    else:
        c[target] = sorted(c[target], key=lambda x: int(x["id"][1:]))
    return c, mp


def permute(X: Scenario, store, *, target: str = "options", order="random", seed: int = 0) -> OpResult:
    args = {"target": target, "order": order, "seed": seed}
    case = X.case.model_dump(mode="json", by_alias=True, exclude_none=True)
    ids = current_ids(case, target)
    new_order = resolve_order(ids, order, case, seed)
    if new_order == ids:
        return OpResult("permute", None, args, None, skipped="identity permutation")
    c, mp = apply_order(case, target, new_order)
    sid = new_id(store, X.family, "permute", None)
    c["id"] = sid
    spans = dict(X.fact_spans)
    if target == "facts":
        spans = {mp.get(k, k): v for k, v in spans.items()}
    S = Scenario(id=sid, family=X.family, split=X.split, domain=X.domain, status="derived", case=Case.model_validate(c),
                 verdict_tier=X.verdict_tier, basis=X.basis, source=X.source, fact_spans=spans,
                 tags=sorted(set(X.tags)), provenance=copy.deepcopy(X.provenance))
    S.lineage.operator = "permute"
    g = lambda i: f"{sid}/{i}"
    gx = lambda i: f"{X.id}/{i}"
    om = {g(mp.get(o, o) if target == "options" else o): gx(o) for o in case["options"]}
    delta = {"relation": "follows", "choice": g(c["verdict"]["choice"]), "id_map": mp,
             "options_map": om if target == "options" else {g(o): gx(o) for o in case["options"]}, "gold_tier": X.verdict_tier}
    r = OpResult("permute", None, args, S, delta=delta, writer=code_writer("ids renumbered in code"))
    r.gates["structure"] = {"pass": True}
    return r
