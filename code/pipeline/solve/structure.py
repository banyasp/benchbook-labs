"""The gold structure of one (C, T) pair in the ids the student sees (P3: shared by render, solve and project).

    g = GoldStructure.build(pair, C, T)             # C, T: Scenario (PairRecord holds only ids)
    g.live            LIVE-id -> global T id  (facts in TRACE order from the span map; options in T's order;
                      considerations ordered by where their facts first appear in the trace)
    g.served          ServedCase for C, prefix REF1   (table: REF1-x -> global C id)
    g.fact_map ...    the gold maps with LIVE-* on the live side and REF1-* on the case side
    g.answer_key()    2a AnswerKey (LIVE ids for T items, *global* ids for C items)

Facts of T that the span map could not locate in the trace are dropped from the gold (the gold must be supported by
the trace; R3); their case counterparts move to case_only. Items the pair's maps leave out are put in live_only /
case_only so every item is in exactly one bucket. Both repairs are listed in `.warnings`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from bench.schema.answer_key import (AnswerKey, GoldConsideration, GoldFact, GoldFlip, GoldFrame, GoldFrameMap,
                                     GoldMapping, GoldOption, GoldPair)
from bench.schema.case import ServedCase
from bench.schema.common import PROSE_REF
from bench.schema.pipeline import PairRecord, Scenario

LIVE = "LIVE-"
BUCKETS = ("matched", "corresponding", "live_only", "case_only")


def local(gid: str) -> str:
    return gid.rpartition("/")[2]


def _num(s: str) -> int:
    return int(re.sub(r"\D", "", s) or 0)


def effective_trace(pair: PairRecord, C: Scenario, T: Scenario) -> Scenario:
    """Arm `revised` (design §7.3): the trace is restyle(C), but K_T, the verdict and Phi are C'-s (the served card's A)
    carried onto T's facts. F and Q are unchanged by revise_card and restyle keeps ids 1:1, so the A part is copied
    as is; any other id layout is an error (pair build checks it). Other arms: T unchanged."""
    if pair.arm != "revised":
        return T
    d = T.case.dump()
    a = C.case.dump()
    for k in ("considerations", "reasoning", "verdict", "flip_conditions", "lesson", "limits"):
        d[k] = a[k]
    if set(d["options"]) != set(a["options"]) or [f["id"] for f in d["facts"]] != [f["id"] for f in a["facts"]]:
        raise ValueError(f"{pair.id}: revised pair needs the trace's fact and option ids to equal the card's")
    from bench.schema import Case
    return T.model_copy(update={"case": Case.model_validate(d)})


@dataclass
class GoldStructure:
    pair: PairRecord
    C: Scenario
    T: Scenario
    served: ServedCase
    live: dict[str, str]                       # LIVE-id -> global T id
    glob2live: dict[str, str]
    case2served: dict[str, str]                # global C id -> REF1-id
    fact_order: list[str]                      # LIVE fact ids in trace order
    option_ids: list[str]
    cons_ids: list[str]
    dropped_facts: list[str] = field(default_factory=list)       # global T fact ids not located in the trace
    warnings: list[str] = field(default_factory=list)
    fact_map: dict = field(default_factory=dict)                 # bucket -> [(LIVE, REF1)] | [LIVE] | [REF1]
    cons_map: dict = field(default_factory=dict)
    options_map: dict[str, str | None] = field(default_factory=dict)   # LIVE-O -> REF1-O | None

    # ------------------------------------------------------------ build
    @classmethod
    def from_store(cls, store, pair: PairRecord, prefix: str = "REF1") -> "GoldStructure":
        """v2.4: G for a stored pair. C and T come from the scenario store, the span map from the trace store
        (pairs reference traces by `trace_ref`; the legacy `pair.span_map` is the fallback)."""
        C = store.scenario(pair.case_scenario) if pair.case_scenario else None
        T = store.scenario(pair.trace_scenario)
        sm = None
        ref = pair.trace_ref or pair.trace_scenario
        if store.has_trace(ref):
            sm = store.trace(ref).span_map
        return cls.build(pair, C, T, prefix, span_map=sm)

    @classmethod
    def build(cls, pair: PairRecord, C: Scenario, T: Scenario, prefix: str = "REF1", span_map=None) -> "GoldStructure":
        """`span_map` (a SpanMap, e.g. from the trace store) overrides `pair.span_map`. For arm `revised` the
        trace scenario is restyle(C), whose A is C's; the gold K_T / verdict is C'-s, so T is replaced by
        `effective_trace` (T's F and Q, the served card's A)."""
        T = effective_trace(pair, C, T)
        sm = span_map if span_map is not None else pair.span_map
        served = C.case.serve(prefix, pair.card_view) if C is not None else None      # arm none: no card
        case2served = {g: s for s, g in served.table.items()} if served else {}
        tc = T.case
        warn: list[str] = []

        # facts in trace order
        pos: dict[str, tuple[int, int]] = {}
        if sm:
            for e in sm.entries:
                k = (e.message, e.start)
                if e.fact not in pos or k < pos[e.fact]:
                    pos[e.fact] = k
        all_f = [tc.global_id(f.id) for f in tc.facts]
        if sm:
            kept = sorted([g for g in all_f if g in pos], key=lambda g: pos[g])
            dropped = [g for g in all_f if g not in pos]
            if dropped:
                warn.append(f"{len(dropped)} T fact(s) not located in the trace, dropped from the gold: "
                            f"{[local(g) for g in dropped]}")
        else:
            kept, dropped = all_f, []
            warn.append("no span map: facts numbered in scenario order")
        live: dict[str, str] = {}
        for i, g in enumerate(kept, 1):
            live[f"{LIVE}F{i}"] = g
        fact_order = list(live)

        option_ids = []
        for i, o in enumerate(tc.options, 1):
            live[f"{LIVE}O{i}"] = tc.global_id(o)
            option_ids.append(f"{LIVE}O{i}")

        def cpos(c):
            ps = [pos[tc.global_id(f)] for f in c.facts if tc.global_id(f) in pos]
            return (min(ps) if ps else (10 ** 9, 0), _num(c.id))
        cons_ids = []
        for i, c in enumerate(sorted(tc.considerations, key=cpos), 1):
            live[f"{LIVE}C{i}"] = tc.global_id(c.id)
            cons_ids.append(f"{LIVE}C{i}")
        fc = tc.flip_conditions
        for w in [*fc.would_change, *fc.would_not_change, *fc.watch_for]:
            live[f"{LIVE}{w.id}"] = tc.global_id(w.id)
        g2l = {g: l for l, g in live.items()}

        self = cls(pair=pair, C=C, T=T, served=served, live=live, glob2live=g2l, case2served=case2served,
                   fact_order=fact_order, option_ids=option_ids, cons_ids=cons_ids, dropped_facts=dropped,
                   warnings=warn)
        self.fact_map = self._map(pair.fact_map, [g for g in all_f if g not in dropped],
                                  [C.case.global_id(f.id) for f in C.case.facts] if C else [], "fact")
        self.cons_map = self._map(pair.consideration_map, [tc.global_id(c.id) for c in tc.considerations],
                                  [C.case.global_id(c.id) for c in C.case.considerations] if C else [], "consideration")
        for o in option_ids:
            tgt = pair.options_map.get(live[o])
            self.options_map[o] = case2served.get(tgt) if tgt else None
        return self

    def _map(self, gm, t_all: list[str], c_all: list[str], what: str) -> dict:
        t_ok, c_ok = set(t_all), set(c_all)
        out = {b: [] for b in BUCKETS}
        seen_t, seen_c = set(), set()
        for b in ("matched", "corresponding"):
            for p in getattr(gm, b):
                if p.live not in t_ok:
                    if p.live not in self.dropped_facts:
                        self.warnings.append(f"{what} map: unknown T item {p.live}")
                    continue                    # dropped T fact: its case partner falls to case_only below
                if p.case not in c_ok:
                    self.warnings.append(f"{what} map: unknown C item {p.case}")
                    continue
                out[b].append((self.glob2live[p.live], self.case2served[p.case]))
                seen_t.add(p.live)
                seen_c.add(p.case)
        for g in gm.live_only:
            if g in t_ok and g not in seen_t:
                out["live_only"].append(self.glob2live[g])
                seen_t.add(g)
        for g in gm.case_only:
            if g in c_ok and g not in seen_c:
                out["case_only"].append(self.case2served[g])
                seen_c.add(g)
        for g in t_all:
            if g not in seen_t:
                self.warnings.append(f"{what} map left out T item {local(g)}: put in live_only")
                out["live_only"].append(self.glob2live[g])
        for g in c_all:
            if g not in seen_c:
                self.warnings.append(f"{what} map left out C item {local(g)}: put in case_only")
                out["case_only"].append(self.case2served[g])

        def key(x):
            return _num(x[0] if isinstance(x, tuple) else x.rpartition("-")[2])
        return {b: sorted(v, key=key) for b, v in out.items()}

    # ------------------------------------------------------------ text with ids renumbered
    def live_text(self, s):
        """T's canonical local ids ({F1}, O2 ...) -> LIVE ids in a prose string or a bare id."""
        if not isinstance(s, str):
            return s
        tl = {local(g): l for l, g in self.live.items()}
        if s in tl:
            return tl[s]
        return PROSE_REF.sub(lambda m: tl.get(m.group(1), m.group(0)), s)

    def lid(self, local_id: str) -> str:
        return self.glob2live[self.T.case.global_id(local_id)]

    # ------------------------------------------------------------ gold in student ids
    @property
    def choice(self) -> str:
        return self.glob2live[self.pair.choice]

    @property
    def acceptable(self) -> list[str]:
        return [self.glob2live[a] for a in self.pair.acceptable if a in self.glob2live]

    @property
    def via(self) -> list[str]:
        return [self.case2served[v] for v in (self.pair.via or []) if v in self.case2served]

    @property
    def decisive(self) -> list[str]:
        return [self.lid(d) for d in self.T.case.verdict.decisive]

    def weights(self) -> dict[str, float]:
        """Facts behind decisive considerations count double (design section 6)."""
        dec = set(self.decisive)
        w = {f: 1.0 for f in self.fact_order}
        for c in self.T.case.considerations:
            if self.lid(c.id) in dec:
                for f in c.facts:
                    g = self.T.case.global_id(f)
                    if g in self.glob2live:
                        w[self.glob2live[g]] = 2.0
        return w

    def fact(self, live_id: str):
        return next(x for x in self.T.case.facts if self.T.case.global_id(x.id) == self.live[live_id])

    def consideration(self, live_id: str):
        return next(c for c in self.T.case.considerations if self.T.case.global_id(c.id) == self.live[live_id])

    def considerations_live(self) -> list[dict]:
        """Considerations in LIVE order with ids and fact lists renumbered (dropped facts removed)."""
        out = []
        for cid in self.cons_ids:
            c = self.consideration(cid)
            facts = [self.glob2live[self.T.case.global_id(f)] for f in c.facts
                     if self.T.case.global_id(f) in self.glob2live]
            out.append({"id": cid, "facts": facts, "equity": c.equity, "favors": [self.lid(o) for o in c.favors],
                        "weight": c.weight, "why": self.live_text(c.why)})
        return out

    def flips_live(self) -> dict:
        fc = self.T.case.flip_conditions
        return {
            "would_change": [{"id": f"{LIVE}{w.id}", "if": self.live_text(w.if_), "then": self.lid(w.then),
                              "why": self.live_text(w.why)} for w in fc.would_change],
            "would_not_change": [{"id": f"{LIVE}{w.id}", "if": self.live_text(w.if_), "why": self.live_text(w.why)}
                                 for w in fc.would_not_change],
            "watch_for": [{"id": f"{LIVE}{w.id}", "what": self.live_text(w.what),
                           "favors": [self.lid(o) for o in w.favors], "why": self.live_text(w.why)}
                          for w in fc.watch_for]}

    # ------------------------------------------------------------ the 2a answer key
    def answer_key(self, arm: str | None = None) -> AnswerKey:
        tc, p = self.T.case, self.pair
        w = self.weights()
        facts = []
        for lid_ in self.fact_order:
            f = self.fact(lid_)
            facts.append(GoldFact(id=lid_, kind=f.kind, status=f.status, fact=f.fact, weight=w[lid_]))
        options = {}
        for o in self.option_ids:
            co = tc.options[local(self.live[o])]
            options[o] = GoldOption(do=co.do, move=co.move, irreversible=co.irreversible, to=co.to)
        tb = self.served.table if self.served else {}

        def gm(m):
            return GoldMapping(
                matched=[GoldPair(live=a, case=tb[b]) for a, b in m["matched"]],
                corresponding=[GoldPair(live=a, case=tb[b]) for a, b in m["corresponding"]],
                live_only=list(m["live_only"]), case_only=[tb[x] for x in m["case_only"]])

        flips = [GoldFlip(id=f"{LIVE}{x.id}", **{"if": self.live_text(x.if_)}, then=self.lid(x.then),
                          why=self.live_text(x.why)) for x in tc.flip_conditions.would_change]
        return AnswerKey(
            scenario=self.T.id, arm=arm or self.pair.arm, served=self.C.id if self.C else None, options=options, choice=self.choice,
            acceptable=self.acceptable, relation=None if (arm or p.arm) == 'none' else p.relation, via=list(p.via) if p.via else None,
            frame=GoldFrame(question=tc.question, decider=tc.decider, my_role=tc.agent),
            facts=facts, frame_map=GoldFrameMap(**p.frame.model_dump()),
            option_map={o: (tb[s] if s else None) for o, s in self.options_map.items()},
            fact_mapping=gm(self.fact_map),
            considerations=[GoldConsideration(**c) for c in self.considerations_live()],
            consideration_mapping=gm(self.cons_map), governs=p.governs, decisive=self.decisive, flip_conditions=flips,
            provenance={"pair": p.id, "arm": p.arm, "card_view": p.card_view, "gold_tier": p.gold_tier, "operator": "project",
                        "d": p.d, "recommended_option": p.recommended_option, "tags": list(p.tags),
                        "course": "absent: the teacher's course is not gold", "dropped_facts": self.dropped_facts})

    def tables(self) -> dict:
        return {"live": self.live, "served": self.served.table if self.served else {}}
