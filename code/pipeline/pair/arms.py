"""Candidate pairs per arm (design §7.2). Pure functions over scenarios and the perturb partials; no store writes.

    relevant   derived pairs (restyle / flip / add_fact: partial as written by perturb) + reverse_restyle (train only)
    augmented  flip pairs reversed: card X' = flip(X), trace X's own, gold X's answer, relation flips via X''s back item
    revised    card C' = revise_card(C), trace = restyle(C)'s, gold C''s choice, relation follows (K_T = C''s)
    decoy      card from another family: equity Jaccard <= 0.2, no shared decisive equity; <= 3 uses per card in train
    self       card X on X's own trace (eval splits)
    none       no card (eval splits)

Everything returns `Cand` (a PairRecord with id P-pending plus a log of what was skipped and why).
"""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field

import yaml

from bench.schema.pipeline import EVAL_SPLITS, FrameCmp, GoldMap, GPair, PairRecord, Provenance, Scenario, Touched, sha256_text
from pipeline.store import Store

HANDUP = ("ask", "refuse")
COMPOSED = "composed-with-C"
DECOY_MAX_JACCARD = 0.2
DECOY_MAX_USES_TRAIN = 3


def h(*parts) -> str:
    return sha256_text("|".join(map(str, parts)))


def local(gid: str) -> str:
    return gid.rpartition("/")[2]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class Skips:
    items: list[dict] = field(default_factory=list)

    def add(self, arm: str, what: str, why: str):
        self.items.append({"arm": arm, "item": what, "why": why})

    def count(self) -> dict:
        return dict(Counter(f"{i['arm']}: {i['why']}" for i in self.items))


def is_retired_copy(s: Scenario) -> bool:
    """Reordered T copies (2f) are retired in v2.4: never paired again; existing ones stay on disk."""
    return s.lineage.operator == "reorder"


def load_partials(store: Store) -> list[dict]:
    out = []
    for p in sorted((store.root / "partials").glob("*.yaml")):
        d = yaml.safe_load(p.read_text())
        d["_file"] = p.name
        out.append(d)
    return out


def _step(rec_prov: Provenance, id_: str, notes: str, **params):
    rec_prov.step(id=id_, operator="pair", notes=notes, params=params, ts=now())


def _prov(d: dict) -> Provenance:
    return Provenance.model_validate(d) if isinstance(d, dict) else (d or Provenance())


# ------------------------------------------------------------------ inversion (Delta inverted)
def invert_gold(gm: GoldMap) -> GoldMap:
    return GoldMap(matched=[GPair(live=p.case, case=p.live, note=p.note) for p in gm.matched],
                   corresponding=[GPair(live=p.case, case=p.live, note=p.note) for p in gm.corresponding],
                   live_only=list(gm.case_only), case_only=list(gm.live_only))


def invert_options(om: dict[str, str | None], T_new: Scenario) -> dict[str, str | None]:
    inv = {v: k for k, v in om.items() if v}
    return {T_new.case.global_id(o): inv.get(T_new.case.global_id(o)) for o in T_new.case.options}


def _frame(d) -> FrameCmp:
    return d if isinstance(d, FrameCmp) else FrameCmp.model_validate(d)


def _gm(d) -> GoldMap:
    return d if isinstance(d, GoldMap) else GoldMap.model_validate(d)


def _from_partial(d: dict, C: Scenario) -> dict:
    keep = {k: v for k, v in d.items() if not k.startswith("_")}
    return keep


# ------------------------------------------------------------------ relevant (derived)
def derived(partials: list[dict], scen: dict[str, Scenario], skips: Skips) -> list[PairRecord]:
    out = []
    for d in partials:
        C, T = scen.get(d["case_scenario"]), scen.get(d["trace_scenario"])
        if not C or not T:
            skips.add("relevant", d["_file"], "scenario missing")
            continue
        if is_retired_copy(C) or is_retired_copy(T):
            skips.add("relevant", d["_file"], "reordered copy (retired)")
            continue
        if C.split != T.split:
            skips.add("relevant", d["_file"], "crosses splits")
            continue
        rec = PairRecord(id="P-pending", split=C.split, arm="relevant", trace_ref=T.id, **_from_partial(d, C))
        if rec.intent in ("flip", "add_fact"):
            rec = rec.model_copy(update={"tags": sorted(set(rec.tags) | {COMPOSED})})
        out.append(rec)
    return out


def reverse_restyle(partials: list[dict], scen: dict[str, Scenario], skips: Skips) -> list[PairRecord]:
    out = []
    for d in partials:
        if d.get("intent") != "restyle":
            continue
        X, R = scen.get(d["case_scenario"]), scen.get(d["trace_scenario"])
        if not X or not R or is_retired_copy(X) or is_retired_copy(R):
            continue
        if X.split != "train" or R.split != "train":
            continue                                    # train only (eval uses `self`)
        prov = Provenance()
        _step(prov, "pair.reverse_restyle", f"card = restyle(X) {R.id}, trace = X's own; gold = X's answer", source_partial=d["_file"])
        out.append(PairRecord(
            id="P-pending", intent="reverse_restyle", arm="relevant", case_scenario=R.id, trace_scenario=X.id, split="train",
            frame=_frame(d["frame"]), options_map=invert_options(d["options_map"], X),
            fact_map=invert_gold(_gm(d["fact_map"])), consideration_map=invert_gold(_gm(d["consideration_map"])),
            governs=True, relation="follows", choice=X.case.global_id(X.case.verdict.choice), gold_tier=X.verdict_tier,
            distance_features={"operator": "reverse_restyle", "of": d["_file"]}, trace_ref=X.id, provenance=prov))
    return out


# ------------------------------------------------------------------ augmented
def back_item(Xp: Scenario, X: Scenario, prefer: str | None = None):
    """X''s would_change item whose `then` is X's choice (the back-flip item). None if absent."""
    c = X.case.verdict.choice
    items = [w for w in Xp.case.flip_conditions.would_change if w.then == c]
    if prefer:
        items.sort(key=lambda w: w.id != prefer)
    return items[0] if items else None


def augmented(partials: list[dict], scen: dict[str, Scenario], skips: Skips) -> list[PairRecord]:
    out = []
    for d in partials:
        if d.get("intent") != "flip":
            continue
        X, Xp = scen.get(d["case_scenario"]), scen.get(d["trace_scenario"])
        if not X or not Xp or is_retired_copy(X) or is_retired_copy(Xp):
            continue
        if Xp.lineage.operator != "flip":
            skips.add("augmented", d["_file"], "trace scenario is not a flip result")
            continue
        fired = local((d.get("via") or [""])[0] if isinstance(d.get("via"), list) else d.get("via") or "")
        item = back_item(Xp, X, prefer=fired)
        if item is None:
            skips.add("augmented", Xp.id, "no back-flip item (no would_change with then = X's choice)")
            continue
        om = invert_options(d["options_map"], X)
        choice = X.case.global_id(X.case.verdict.choice)
        if om.get(choice) != Xp.case.global_id(item.then):
            skips.add("augmented", Xp.id, "Delta inverted does not map X's choice to the back item's `then`")
            continue
        prov = Provenance()
        _step(prov, "pair.augmented", "card = X' (flip of X), trace = X's own; Delta inverted; gold = X's answer via X''s back-flip item",
              source_partial=d["_file"], back_item=Xp.case.global_id(item.id))
        out.append(PairRecord(
            id="P-pending", intent="augmented", arm="augmented", case_scenario=Xp.id, trace_scenario=X.id, split=X.split,
            frame=_frame(d["frame"]), options_map=om, fact_map=invert_gold(_gm(d["fact_map"])),
            consideration_map=invert_gold(_gm(d["consideration_map"])), governs=True, relation="flips",
            via=[Xp.case.global_id(item.id)], choice=choice, gold_tier=X.verdict_tier, realization="direct",
            touched=Touched(item=Xp.case.global_id(item.id), condition=item.if_,
                            how="back-flip item of X'; X's own trace states the condition directly"),
            tags=sorted({COMPOSED, "gate-pending"}), distance_features={"operator": "augmented", "of": d["_file"]},
            trace_ref=X.id, provenance=prov))
    return out


# ------------------------------------------------------------------ revised
def revised(partials: list[dict], scen: dict[str, Scenario], skips: Skips) -> list[PairRecord]:
    """C' scenarios (lineage.operator revise_card) paired with restyle(C)'s trace. W3 supplies C'; the restyle
    scenario and its partial (C -> R) supply M^F and the options map."""
    restyles = {}
    for d in partials:
        if d.get("intent") == "restyle":
            restyles.setdefault(d["case_scenario"], []).append(d)
    out = []
    for Cp in sorted((s for s in scen.values() if s.lineage.operator == "revise_card"), key=lambda s: s.id):
        C = scen.get(Cp.lineage.parent or "")
        if not C:
            skips.add("revised", Cp.id, "parent card missing")
            continue
        cands = sorted((d for d in restyles.get(C.id, []) if d["trace_scenario"] in scen), key=lambda d: d["trace_scenario"])
        if not cands:
            skips.add("revised", Cp.id, f"no restyle(C) trace scenario for {C.id}")
            continue
        d = cands[0]
        R = scen[d["trace_scenario"]]
        if Cp.split != R.split or is_retired_copy(R):
            skips.add("revised", Cp.id, "split mismatch or retired restyle copy")
            continue
        if Cp.case.verdict.choice == C.case.verdict.choice:
            skips.add("revised", Cp.id, "C' choice equals C's choice")
            continue
        if [f.id for f in Cp.case.facts] != [f.id for f in R.case.facts] or set(Cp.case.options) != set(R.case.options):
            skips.add("revised", Cp.id, "restyle trace fact/option ids differ from the card's")
            continue
        sw = lambda g: Cp.case.global_id(local(g)) if g and g.startswith(C.id + "/") else g          # noqa: E731
        om = {t: sw(c) for t, c in d["options_map"].items()}
        want = Cp.case.global_id(Cp.case.verdict.choice)
        t_choice = next((t for t, c in om.items() if c == want), None)
        if t_choice is None:
            skips.add("revised", Cp.id, "C' choice has no counterpart in the options map")
            continue

        def rebase(gm: GoldMap) -> GoldMap:
            f = lambda ps: [GPair(live=p.live, case=sw(p.case)) for p in ps]                              # noqa: E731
            return GoldMap(matched=f(gm.matched), corresponding=f(gm.corresponding), live_only=list(gm.live_only),
                           case_only=[sw(x) for x in gm.case_only])
        # K_T = C''s considerations carried onto T's facts: the same ids on both sides, all matched
        km = GoldMap(matched=[GPair(live=R.case.global_id(c.id), case=Cp.case.global_id(c.id)) for c in Cp.case.considerations])
        prov = Provenance()
        _step(prov, "pair.revised", "card = C' (revise_card), trace = restyle(C)'s; K_T = C''s considerations; gold = C''s choice",
              restyle_partial=d["_file"], parent=C.id, trace_of=R.id)
        out.append(PairRecord(
            id="P-pending", intent="revised", arm="revised", case_scenario=Cp.id, trace_scenario=R.id, split=Cp.split,
            frame=_frame(d["frame"]), options_map=om, fact_map=rebase(_gm(d["fact_map"])), consideration_map=km, governs=True,
            relation="follows", choice=t_choice, gold_tier="by-construction", tags=["revised-authored"],
            distance_features={"operator": "revised", "parent": C.id, "restyle": R.id}, trace_ref=R.id, provenance=prov))
    return out


# ------------------------------------------------------------------ decoy
def equities(S: Scenario) -> set[str]:
    return {c.equity for c in S.case.considerations}


def decisive_equities(S: Scenario) -> set[str]:
    dec = set(S.case.verdict.decisive)
    return {c.equity for c in S.case.considerations if c.id in dec}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def decoy_ok(C: Scenario, T: Scenario) -> tuple[bool, float]:
    j = jaccard(equities(C), equities(T))
    return (C.family != T.family and j <= DECOY_MAX_JACCARD and not (decisive_equities(C) & decisive_equities(T))), j


def decoys(scen: dict[str, Scenario], per_target: int, seed: int, skips: Skips) -> list[PairRecord]:
    sources = sorted((s for s in scen.values() if not s.lineage.parent and not is_retired_copy(s)), key=lambda s: s.id)
    uses: Counter = Counter()
    out = []
    for T in sources:
        cands = []
        for C in sources:
            if C.split != T.split:
                continue
            ok, j = decoy_ok(C, T)
            if ok:
                cands.append((C, j))
        cands.sort(key=lambda cj: (uses[cj[0].id] if T.split == "train" else 0, h(seed, "decoy", T.id, cj[0].id)))
        n = 0
        for C, j in cands:
            if n >= per_target:
                break
            if T.split == "train" and uses[C.id] >= DECOY_MAX_USES_TRAIN:
                continue
            uses[C.id] += 1
            n += 1
            tc, cc = T.case, C.case
            fm = GoldMap(live_only=[tc.global_id(f.id) for f in tc.facts], case_only=[cc.global_id(f.id) for f in cc.facts])
            cm = GoldMap(live_only=[tc.global_id(c.id) for c in tc.considerations], case_only=[cc.global_id(c.id) for c in cc.considerations])
            prov = Provenance()
            _step(prov, "pair.decoy", "decoy: card of another family, equity Jaccard <= 0.2, no shared decisive equity; gold = T's own verdict",
                  seed=seed, jaccard=round(j, 3))
            out.append(PairRecord(
                id="P-pending", intent="decoy", arm="decoy", case_scenario=C.id, trace_scenario=T.id, split=T.split,
                frame=FrameCmp(question="different", decider="same" if tc.decider == cc.decider else "different",
                               role="same" if tc.agent_role == cc.agent_role else "different"),
                options_map={tc.global_id(o): None for o in tc.options}, fact_map=fm, consideration_map=cm, governs=False,
                relation="not_governed", choice=tc.global_id(tc.verdict.choice), gold_tier=T.verdict_tier,
                distance_features={"operator": "decoy", "same_domain": C.domain == T.domain, "equity_jaccard": round(j, 3)},
                trace_ref=T.id, provenance=prov))
        if n < per_target:
            skips.add("decoy", T.id, f"only {n}/{per_target} eligible decoy cards")
    return out


# ------------------------------------------------------------------ self / none (eval only)
def self_pairs(scen: dict[str, Scenario], skips: Skips) -> list[PairRecord]:
    out = []
    for X in sorted(scen.values(), key=lambda s: s.id):
        if X.lineage.parent or X.split not in EVAL_SPLITS or is_retired_copy(X):
            continue
        c = X.case
        pairs = lambda ids: [GPair(live=c.global_id(i), case=c.global_id(i)) for i in ids]               # noqa: E731
        prov = Provenance()
        _step(prov, "pair.self", "card(X) on X's own trace; all matched; d = 0")
        out.append(PairRecord(
            id="P-pending", intent="self", arm="self", case_scenario=X.id, trace_scenario=X.id, split=X.split,
            frame=FrameCmp(question="same", decider="same", role="same"), options_map={c.global_id(o): c.global_id(o) for o in c.options},
            fact_map=GoldMap(matched=pairs([f.id for f in c.facts])),
            consideration_map=GoldMap(matched=pairs([k.id for k in c.considerations])), governs=True, relation="follows",
            choice=c.global_id(c.verdict.choice), gold_tier=X.verdict_tier, distance_features={"operator": "self"},
            trace_ref=X.id, provenance=prov))
    return out


def none_pairs(scen: dict[str, Scenario], trace_ids: set[str]) -> list[PairRecord]:
    """trace_ids: scenarios that serve as traces in eval-split pairs (plus eval sources, added by the caller)."""
    out = []
    for sid in sorted(trace_ids):
        T = scen.get(sid)
        if not T or T.split not in EVAL_SPLITS or is_retired_copy(T):
            continue
        c = T.case
        prov = Provenance()
        _step(prov, "pair.none", "no card; gold = T's own answer (relation not_governed: no case governs)")
        out.append(PairRecord(
            id="P-pending", intent="none", arm="none", case_scenario="", trace_scenario=T.id, split=T.split,
            frame=FrameCmp(question="different", decider="different", role="different"),
            options_map={c.global_id(o): None for o in c.options},
            fact_map=GoldMap(live_only=[c.global_id(f.id) for f in c.facts]),
            consideration_map=GoldMap(live_only=[c.global_id(k.id) for k in c.considerations]), governs=False,
            relation="not_governed", choice=c.global_id(c.verdict.choice), gold_tier=T.verdict_tier,
            distance_features={"operator": "none"}, trace_ref=T.id, provenance=prov))
    return out
