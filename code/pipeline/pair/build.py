"""pair: store -> PairRecords (derived + decoys), then balance (hand-up cap, gold option positions).

Rules
- Derived pairs come from the gold partials the perturb operators wrote (C = parent, T = X').
- Decoys: C = an unrelated source scenario (different family, preferably a different domain), T = an existing source
  scenario; relation not_governed, governs false, choice = T's own gold choice, tier = T's verdict tier, every fact and
  consideration live_only / case_only, options_map all None.
- Pairs never cross splits (C.split == T.split; eval-only pairs only with eval-only).
- Hand-up cap (R7): per intent, hand-up golds (gold option move ask/refuse) <= 1/3 of the group. With k non-hand-up
  pairs at most floor(k/2) hand-ups survive; the surplus is dropped (deterministic order) and reported.
- Option positions (R6): per (intent, number of options) the gold position is made as uniform as possible by writing
  a re-ordered COPY of T (`reorder.py`) for the pairs that need it; nothing is dropped for position.
- Pair id = P-<sha10 of (C, T, intent)> computed after re-ordering.
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict

import yaml

from bench.schema.pipeline import FrameCmp, GoldMap, PairRecord, Provenance, Scenario, sha256_text
from bench.schema.pipeline import pair_id as _pair_id
from pipeline.perturb.io import partial_path
from pipeline.store import Store, write_yaml

from .reorder import gold_position, reorder

HANDUP = ("ask", "refuse")


def pair_id(c: str, t: str, intent: str, arm: str | None = None, card_view: str = "full") -> str:
    """v2.4 id (design §7.1). Legacy 2f ids (hash of C|T|intent) are kept on existing records."""
    return _pair_id(c, t, intent, arm or ("decoy" if intent == "decoy" else "relevant"), card_view)


def h(*parts) -> str:
    return sha256_text("|".join(map(str, parts)))


def is_handup(T: Scenario) -> bool:
    return T.case.options[T.case.verdict.choice].move in HANDUP


# ------------------------------------------------------------------ candidates
def derived_records(store: Store, scen: dict[str, Scenario]) -> list[PairRecord]:
    out = []
    for p in sorted((store.root / "partials").glob("*.yaml")):
        d = yaml.safe_load(p.read_text())
        c, t = scen.get(d["case_scenario"]), scen.get(d["trace_scenario"])
        if not c or not t or c.split != t.split:
            continue
        out.append(PairRecord(id="P-pending", split=c.split, **d))
    return out


def decoy_records(scen: dict[str, Scenario], per_target: int, seed: int) -> list[PairRecord]:
    sources = sorted((s for s in scen.values() if not s.lineage.parent), key=lambda s: s.id)
    out = []
    for T in sources:
        cands = [C for C in sources if C.split == T.split and C.family != T.family]
        cands.sort(key=lambda C: (C.domain == T.domain, h(seed, T.id, C.id)))     # different domain first
        for C in cands[:per_target]:
            tc, cc = T.case, C.case
            fm = GoldMap(live_only=[tc.global_id(f.id) for f in tc.facts], case_only=[cc.global_id(f.id) for f in cc.facts])
            cm = GoldMap(live_only=[tc.global_id(c.id) for c in tc.considerations], case_only=[cc.global_id(c.id) for c in cc.considerations])
            eq_t, eq_c = {c.equity for c in tc.considerations}, {c.equity for c in cc.considerations}
            prov = Provenance()
            prov.step(id="pair.decoy", operator="pair", notes="decoy: unrelated C; gold = T's own verdict", params={"seed": seed},
                      ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            out.append(PairRecord(
                id="P-pending", intent="decoy", case_scenario=C.id, trace_scenario=T.id, split=T.split,
                frame=FrameCmp(question="different", decider="same" if tc.decider == cc.decider else "different",
                               role="same" if tc.agent_role == cc.agent_role else "different"),
                options_map={tc.global_id(o): None for o in tc.options}, fact_map=fm, consideration_map=cm, governs=False,
                relation="not_governed", choice=tc.global_id(tc.verdict.choice), gold_tier=T.verdict_tier,
                distance_features={"operator": "decoy", "same_domain": C.domain == T.domain,
                                   "equity_jaccard": round(len(eq_t & eq_c) / max(1, len(eq_t | eq_c)), 3)},
                provenance=prov))
    return out


# ------------------------------------------------------------------ retargeting a record to a re-ordered T
def retarget(rec: PairRecord, old: str, new: str, perm: dict[str, str]) -> PairRecord:
    d = rec.dump()

    def g(x):
        if x is None:
            return None
        s, _, loc = x.partition("/")
        return f"{new}/{perm.get(loc, loc)}" if s == old else x

    d["trace_scenario"] = new
    d["options_map"] = {g(k): v for k, v in d["options_map"].items()}
    d["choice"] = g(d["choice"])
    d["acceptable"] = [g(a) for a in d.get("acceptable", [])]
    for key in ("fact_map", "consideration_map"):
        m = d[key]
        for b in ("matched", "corresponding"):
            m[b] = [{**p, "live": g(p["live"])} for p in m.get(b, [])]
        m["live_only"] = [g(x) for x in m.get("live_only", [])]
    return PairRecord.model_validate(d)


# ------------------------------------------------------------------ balance
def distributions(recs: list[PairRecord], scen: dict[str, Scenario]) -> dict:
    hand, pos = defaultdict(Counter), defaultdict(Counter)
    for r in recs:
        T = scen[r.trace_scenario]
        hand[r.intent][("handup" if is_handup(T) else "other")] += 1
        pos[f"{r.intent}/n={len(T.case.options)}"][gold_position(T)] += 1
    return {"handup": {k: dict(v) for k, v in sorted(hand.items())},
            "gold_position": {k: dict(sorted(v.items())) for k, v in sorted(pos.items())}}


def cap_handups(recs: list[PairRecord], scen: dict[str, Scenario], seed: int) -> tuple[list[PairRecord], list[str]]:
    keep, dropped = [], []
    by = defaultdict(list)
    for r in recs:
        by[r.intent].append(r)
    for intent, rs in by.items():
        hu = [r for r in rs if is_handup(scen[r.trace_scenario])]
        other = [r for r in rs if r not in hu]
        allowed = len(other) // 2
        hu.sort(key=lambda r: h(seed, r.case_scenario, r.trace_scenario, intent))
        keep += other + hu[:allowed]
        dropped += [f"{r.case_scenario} -> {r.trace_scenario} ({intent})" for r in hu[allowed:]]
    return keep, dropped


def balance_positions(recs: list[PairRecord], scen: dict[str, Scenario], seed: int, store: Store | None):
    """Assign gold positions as uniformly as possible per (intent, n); write re-ordered T copies where needed."""
    groups = defaultdict(list)
    for r in recs:
        groups[(r.intent, len(scen[r.trace_scenario].case.options))].append(r)
    out, reordered = [], 0
    for (intent, n), rs in sorted(groups.items()):
        N = len(rs)
        quota = {p: N // n + (1 if p <= N % n else 0) for p in range(1, n + 1)}
        # rotate which positions get the extra one, deterministically, so n=2 groups of odd size do not always favor 1
        extra = [p for p in range(1, n + 1) if quota[p] > N // n]
        if extra:
            shift = int(h(seed, intent, n)[:6], 16) % n
            quota = {p: N // n + (1 if ((p - 1 - shift) % n) < N % n else 0) for p in range(1, n + 1)}
        rs = sorted(rs, key=lambda r: h(seed, r.case_scenario, r.trace_scenario, intent))
        target, left = {}, dict(quota)
        for r in rs:                                         # first keep current positions where quota allows
            cur = gold_position(scen[r.trace_scenario])
            if left.get(cur, 0) > 0:
                target[id(r)] = cur
                left[cur] -= 1
        for r in rs:
            if id(r) not in target:
                p = max(left, key=lambda q: (left[q], -q))
                target[id(r)] = p
                left[p] -= 1
        for r in rs:
            T = scen[r.trace_scenario]
            S, perm = reorder(T, target[id(r)])
            if S is not T:
                scen[S.id] = S
                if store is not None:
                    store.save_scenario(S)
                r = retarget(r, T.id, S.id, perm)
                reordered += 1
            out.append(r)
    return out, reordered


def build(store: Store, decoys: int = 2, seed: int = 0, write: bool = True) -> dict:
    scen = {s.id: s for s in store.scenarios()}
    recs = derived_records(store, scen) + decoy_records(scen, decoys, seed)
    before = distributions(recs, scen)
    kept, dropped = cap_handups(recs, scen, seed)
    final, reordered = balance_positions(kept, scen, seed, store if write else None)
    final = [PairRecord.model_validate({**r.dump(), "id": pair_id(r.case_scenario, r.trace_scenario, r.intent, r.arm, r.card_view)}) for r in final]
    for r in final:
        assert scen[r.case_scenario].split == scen[r.trace_scenario].split == r.split, "pair crosses splits"
    if write:
        for r in final:
            if not (store.pair_dir(r.id) / "pair.yaml").exists():          # keep P3's trace/solve on existing pairs
                store.save_pair(r)
    report = {"pairs": len(final), "candidates": len(recs), "by_intent": dict(Counter(r.intent for r in final)),
              "by_relation": dict(Counter(r.relation for r in final)), "by_tier": dict(Counter(r.gold_tier for r in final)),
              "by_split": dict(Counter(r.split for r in final)), "dropped_for_handup_cap": dropped,
              "reordered_trace_copies": reordered, "before": before, "after": distributions(final, scen)}
    if write:
        write_yaml(store.root / "pair_build_report.yaml", report)
    return report


def stats(store: Store) -> dict:
    scen = {s.id: s for s in store.scenarios()}
    recs = store.pairs()
    return {"pairs": len(recs), "by_intent": dict(Counter(r.intent for r in recs)), "by_relation": dict(Counter(r.relation for r in recs)),
            "by_tier": dict(Counter(r.gold_tier for r in recs)), "by_split": dict(Counter(r.split for r in recs)),
            **distributions(recs, scen)}
