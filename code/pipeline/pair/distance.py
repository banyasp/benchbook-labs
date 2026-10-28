"""Structural distance d(C, T) (design §7.5): computed from G, never served.

d = 1 - sum(w*s)/sum(w) over the union of fact and consideration items, s = 1 matched, 0.5 corresponding, 0 live_only /
case_only, w = 2 for items behind decisive considerations (a decisive consideration, or a fact one cites; on either
side), else 1; + 0.1 per frame field that is not `same`; capped at 1. Raw counts are returned so any other weighting
can be recomputed (Peter sets the weights).
"""
from __future__ import annotations

from bench.schema.pipeline import GoldMap, PairRecord, Scenario

S = {"matched": 1.0, "corresponding": 0.5, "live_only": 0.0, "case_only": 0.0}
FRAME_PENALTY = 0.1
FORMULA = "design-7.5-default-v1"


def decisive_items(S_: Scenario) -> set[str]:
    """Global ids of decisive considerations and of the facts they cite."""
    c = S_.case
    dec = set(c.verdict.decisive)
    out = {c.global_id(x) for x in dec}
    for k in c.considerations:
        if k.id in dec:
            out |= {c.global_id(f) for f in k.facts}
    return out


def distance(fact_map: GoldMap, cons_map: GoldMap, frame, C: Scenario | None, T: Scenario) -> tuple[float, dict]:
    dt = decisive_items(T)
    dc = decisive_items(C) if C is not None else set()
    cnt = {k: {"n": 0, "w": 0.0} for k in S}
    num = den = 0.0
    kinds = {"fact": fact_map, "consideration": cons_map}
    for m in kinds.values():
        for b in ("matched", "corresponding"):
            for p in getattr(m, b):
                w = 2.0 if (p.live in dt or p.case in dc) else 1.0
                num += w * S[b]
                den += w
                cnt[b]["n"] += 1
                cnt[b]["w"] += w
        for g in m.live_only:
            w = 2.0 if g in dt else 1.0
            den += w
            cnt["live_only"]["n"] += 1
            cnt["live_only"]["w"] += w
        for g in m.case_only:
            w = 2.0 if g in dc else 1.0
            den += w
            cnt["case_only"]["n"] += 1
            cnt["case_only"]["w"] += w
    fr = {k: getattr(frame, k) for k in ("question", "decider", "role")}
    pen = FRAME_PENALTY * sum(v != "same" for v in fr.values())
    base = 1.0 - (num / den if den else 1.0)
    d = round(min(1.0, base + pen), 4)
    return d, {"formula": FORMULA, "sum_ws": num, "sum_w": den, "base": round(base, 4), "frame": fr, "frame_penalty": round(pen, 3),
               "buckets": cnt}


def for_pair(rec: PairRecord, C: Scenario | None, T: Scenario) -> PairRecord:
    """Return rec with d and distance_features['d'] set (existing features kept)."""
    d, feats = distance(rec.fact_map, rec.consideration_map, rec.frame, C, T)
    return rec.model_copy(update={"d": d, "distance_features": {**rec.distance_features, "d": feats}})
