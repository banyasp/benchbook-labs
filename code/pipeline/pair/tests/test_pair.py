"""pair: derived pairs + decoys, split rule, hand-up cap, gold-position balance (offline)."""
import random
from collections import Counter

import pytest

from bench.schema.pipeline import PairRecord
from pipeline.pair import build, reorder
from pipeline.pair.build import is_handup
from pipeline.pair.reorder import gold_position
from pipeline.perturb import restyle, save_result, set_complete
from pipeline.perturb.common import check_gold
from pipeline.perturb.tests.fakes import CASES, Fake, pilot
from pipeline.store import Store

IDS = ["DR-AUT-001@v1", "DR-AGT-201@v1", "DR-INT-103@v1", "DR-INT-301@v1", "DR-OVS-301@v1", "DR-REL-301@v1",
       "DR-INT-301-r1@v1", "DR-OVS-301-r1@v1"]
SPLIT = {"AUT-001": "train", "INT-301": "train", "OVS-301": "train"}


@pytest.fixture
def store(tmp_path):
    set_complete(Fake())
    st = Store(tmp_path)
    for i in IDS:
        s = pilot(i)
        s = s.model_copy(update={"split": SPLIT.get(s.family, "eval-only")})
        st.save_scenario(s)
    for s in st.scenarios():
        T, p = restyle(s, st, random.Random(1))
        save_result(st, T, p)
    yield st
    set_complete(None)


def test_build_rules(store):
    rep = build(store, decoys=2, seed=0)
    scen = {s.id: s for s in store.scenarios()}
    recs = store.pairs()
    assert recs and len(recs) == rep["pairs"]
    assert {r.intent for r in recs} == {"restyle", "decoy"}
    for r in recs:
        C, T = scen[r.case_scenario], scen[r.trace_scenario]
        assert C.split == T.split == r.split                                   # never crosses splits
        assert r.id.startswith("P-") and len(r.id) == 12
        if r.intent == "decoy":
            assert r.relation == "not_governed" and not r.governs and C.family != T.family
            assert all(v is None for v in r.options_map.values())
            assert not r.fact_map.matched and not r.fact_map.corresponding
            assert len(r.fact_map.live_only) == len(T.case.facts) and len(r.fact_map.case_only) == len(C.case.facts)
            assert len(r.consideration_map.live_only) == len(T.case.considerations)
            assert r.choice == T.case.global_id(T.case.verdict.choice) and r.gold_tier == T.verdict_tier
        else:
            assert r.relation == "follows"
            assert r.options_map[r.choice] == C.case.global_id(C.case.verdict.choice)   # survives re-ordering
            assert len(r.fact_map.matched) == len(C.case.facts)


def test_hand_up_cap_and_position_balance(store):
    rep = build(store, decoys=3, seed=1)
    scen = {s.id: s for s in store.scenarios()}
    by = {}
    for r in store.pairs():
        by.setdefault(r.intent, []).append(r)
    for intent, rs in by.items():
        hu = sum(is_handup(scen[r.trace_scenario]) for r in rs)
        assert hu * 3 <= len(rs), (intent, hu, len(rs))
    for key, cnt in rep["after"]["gold_position"].items():
        assert max(cnt.values()) - min(cnt.values() if len(cnt) == int(key.split("n=")[1]) else [0]) <= 1, (key, cnt)
    # report before/after exists
    assert "before" in rep and "after" in rep


def test_reorder_roundtrip():
    T = pilot("DR-INT-301@v1")                      # three options, gold O3? -> move it
    for target in range(1, len(T.case.options) + 1):
        S, m = reorder(T, target)
        assert gold_position(S) == target
        assert sorted(m.values()) == sorted(T.case.options) and S.case.verdict.choice == f"O{target}"
        # the gold option text is the same text
        assert S.case.options[S.case.verdict.choice].do == T.case.options[T.case.verdict.choice].do
        assert [o.move for o in S.case.options.values()].count("ask") == [o.move for o in T.case.options.values()].count("ask")


def test_hand_up_cap_drops_surplus(store, monkeypatch):
    import importlib
    B = importlib.import_module("pipeline.pair.build")
    scen = {s.id: s for s in store.scenarios()}
    hot = {s.id for s in scen.values() if s.family in ("AUT-001", "INT-301", "OVS-301")}      # pretend their golds are hand-ups
    monkeypatch.setattr(B, "is_handup", lambda T: T.id in hot or T.lineage.parent in hot)
    rep = B.build(store, decoys=3, seed=2, write=False)
    assert rep["dropped_for_handup_cap"]
    for intent, c in rep["after"]["handup"].items():
        assert c.get("handup", 0) * 3 <= sum(c.values()), (intent, c)
