"""pair v2.4: arms, balance, distance, channels, gate, housekeeping (offline; fakes and fixtures only)."""
import json
import random
from collections import Counter

import pytest

from bench.schema import Case
from bench.schema.pipeline import (CHANNELS, Lineage, OptionSpan, PairRecord, Provenance, Scenario, SpanEntry, SpanMap,
                                   TraceRecord)
from pipeline.ingest.splits import check_no_leak
from pipeline.pair import assign_channels, assign_recommended, build, gate_augmented, reorder
from pipeline.pair import balance as B
from pipeline.pair.build import housekeeping_2f, pair_id, stats, sync_traces
from pipeline.pair.distance import distance
from pipeline.perturb import flip, restyle, save_result, set_complete
from pipeline.perturb.tests.fakes import Fake, pilot
from pipeline.perturb.tests.test_perturb import REAL
from pipeline.solve.structure import GoldStructure
from pipeline.store import Store

IDS = ["DR-AUT-001@v1", "DR-AGT-201@v1", "DR-INT-103@v1", "DR-INT-301@v1", "DR-OVS-301@v1", "DR-REL-301@v1"]
TRAIN = {"AUT-001", "INT-301", "OVS-301", "AGT-201"}
SPLIT = {f: "train" for f in TRAIN} | {"INT-103": "test", "REL-301": "test"}


def revise(C: Scenario) -> Scenario:
    """Stand-in for W3's revise_card result: same F and Q, a different verdict."""
    d = C.case.dump()
    d["id"] = C.id.replace("@v1", "-rc1@v1")
    d["verdict"]["choice"] = [o for o in d["options"] if o != C.case.verdict.choice][0]
    return Scenario(id=d["id"], family=C.family, split=C.split, domain=C.domain, status="derived", case=Case.model_validate(d),
                    verdict_tier="by-construction", lineage=Lineage(parent=C.id, operator="revise_card"))


@pytest.fixture
def store(tmp_path):
    set_complete(Fake(realize=[REAL]))
    st = Store(tmp_path)
    for i in IDS:
        s = pilot(i)
        st.save_scenario(s.model_copy(update={"split": SPLIT.get(s.family, "eval-only")}))
    for s in st.scenarios():
        T, p = restyle(s, st, random.Random(1))
        save_result(st, T, p)
    X = st.scenario("DR-AUT-001@v1")
    T, p = flip(X, st, random.Random(1), item="flip1")
    save_result(st, T, p)
    for cid in ("DR-AUT-001@v1", "DR-INT-301@v1"):
        st.save_scenario(revise(st.scenario(cid)))
    yield st
    set_complete(None)


def test_channels_deterministic_gold_blind():
    opts = [f"S@v1/O{i}" for i in range(1, 5)]
    a = assign_channels("S@v1", opts, 3)
    assert a == assign_channels("S@v1", list(reversed(opts)), 3) and set(a.values()) <= set(CHANNELS) and len(set(a.values())) == 4
    assert a != assign_channels("S@v1", opts, 4) or a != assign_channels("T@v1", opts, 3)
    assert len(set(assign_channels("S@v1", [f"S@v1/O{i}" for i in range(1, 8)], 0).values())) == 5      # > 5 options cycle
    rec = [assign_recommended(f"S{i}@v1", opts, 0) for i in range(400)]
    assert 0.4 < sum(r is not None for r in rec) / 400 < 0.6 and {r for r in rec if r} == set(opts)
    assert assign_recommended("S@v1", opts, 9) == assign_recommended("S@v1", list(reversed(opts)), 9)


def test_build_arms_and_invariants(store):
    rep = build(store, decoys=2, seed=0)
    scen = {s.id: s for s in store.scenarios()}
    recs = store.pairs()
    assert len(recs) == rep["pairs"] and not rep["leak_violations"] and check_no_leak(store) == []
    arms = Counter(r.arm for r in recs)
    assert {"relevant", "augmented", "revised", "decoy", "self", "none"} <= set(arms), arms
    assert {"restyle", "flip", "reverse_restyle"} <= {r.intent for r in recs if r.arm == "relevant"}
    assert all(r.id == pair_id(r.case_scenario, r.trace_scenario, r.intent, r.arm, r.card_view) for r in recs)
    assert not any(scen[r.trace_scenario].lineage.operator == "reorder" for r in recs)
    for r in recs:
        T = scen[r.trace_scenario]
        C = scen.get(r.case_scenario)
        assert r.trace_ref == T.id and r.d is None if r.arm == "none" else r.d is not None
        assert r.split == T.split and (C is None or C.split == T.split)
        if r.arm in ("self", "none"):
            assert r.split in ("test", "eval-only") and r.ar_prompt is True
        if r.split == "train":
            assert r.arm not in ("self", "none")
        if r.arm == "relevant" and r.intent == "reverse_restyle":
            assert r.split == "train" and r.relation == "follows" and C.lineage.operator == "restyle" and C.lineage.parent == T.id
            assert r.choice == T.case.global_id(T.case.verdict.choice) and not r.fact_map.live_only and not r.fact_map.case_only
            assert r.d < 0.05
        if r.arm == "augmented":
            assert r.intent == "augmented" and r.relation == "flips" and r.realization == "direct" and r.card_view == "full"
            (v,) = r.via
            item = {C.case.global_id(w.id): w for w in C.case.flip_conditions.would_change}[v]
            assert item.then == T.case.verdict.choice and r.options_map[r.choice] == C.case.global_id(item.then)
            assert r.gold_tier == T.verdict_tier and {"composed-with-C", "gate-pending"} <= set(r.tags)
            assert r.fact_map.corresponding[0].case == C.case.global_id("F10")       # Delta inverted: X' is the card
            assert r.fact_map.corresponding[0].live == T.case.global_id("F10")
        if r.arm == "revised":
            Rr = T
            assert r.relation == "follows" and r.tags == ["revised-authored"] and r.gold_tier == "by-construction"
            assert r.options_map[r.choice] == C.case.global_id(C.case.verdict.choice)
            assert r.choice != Rr.case.global_id(Rr.case.verdict.choice) and Rr.lineage.operator == "restyle"
            assert len(r.consideration_map.matched) == len(C.case.considerations)
        if r.arm == "decoy":
            assert r.relation == "not_governed" and C.family != T.family and r.d == 1.0
            assert r.distance_features["equity_jaccard"] <= 0.2
            assert r.choice == T.case.global_id(T.case.verdict.choice)
        if r.arm == "self":
            assert r.d == 0 and r.case_scenario == r.trace_scenario
        if r.intent in ("flip", "add_fact"):
            assert "composed-with-C" in r.tags
    for arm in set(arms):
        for g in ("train", "eval"):
            rs = [r for r in recs if r.arm == arm and B.group(r) == g]
            assert sum(B.is_handup(r, scen) for r in rs) * 3 <= len(rs), (arm, g)
    uses = Counter(r.case_scenario for r in recs if r.arm == "decoy" and r.split == "train")
    assert not uses or max(uses.values()) <= 3
    assert "after_balance" in rep and "before_balance" in rep and rep["skipped"]["counts"] is not None
    # re-running is stable (same ids) and keeps one file per pair
    ids = {r.id for r in recs}
    build(store, decoys=2, seed=0)
    assert {r.id for r in store.pairs()} == ids


def test_view_and_ar_assignment(store):
    build(store, seed=1, thin_share=0.0)
    assert all(r.card_view == "full" for r in store.pairs())
    rep = build(store, seed=1, thin_share=1.0, position_tolerance=None)
    scen = {s.id: s for s in store.scenarios()}
    new = [r for r in store.pairs() if pair_id(r.case_scenario, r.trace_scenario, r.intent, r.arm, r.card_view) == r.id]
    thin = [r for r in new if r.card_view == "thin"]
    assert thin and all(r.split == "train" and r.arm in ("relevant", "revised") and r.relation in ("follows", "distinguished") for r in thin)
    assert not [r for r in new if r.card_view == "thin" and r.relation in ("flips", "not_governed")]
    assert all(r.ar_prompt in (True, False) for r in new if r.split == "train")
    assert all(r.ar_prompt and r.card_view == "full" for r in new if r.split != "train")
    assert rep["thin_share"] == 1.0 and scen


def test_handup_cap_per_arm_reports_drops(store):
    rep = build(store, decoys=3, seed=2, write=False)
    assert "handup" in rep["dropped"] and "position" in rep["dropped"]
    for key, v in rep["after_balance"].items():
        assert v["handup"]["share"] <= 1 / 3 + 1e-9, key
        assert "position_card_order" in v and "recommended_is_gold" in v


def test_distance_formula():
    from bench.schema.pipeline import FrameCmp, GoldMap, GPair
    C, T = pilot("DR-AUT-001@v1"), pilot("DR-AUT-001@v1")
    g = lambda i: C.case.global_id(i)
    same = FrameCmp(question="same", decider="same", role="same")
    fm = GoldMap(matched=[GPair(live=g("F1"), case=g("F1"))], corresponding=[GPair(live=g("F2"), case=g("F2"))])
    d, feats = distance(fm, GoldMap(), same, C, T)
    assert 0 < d < 0.5 and feats["buckets"]["corresponding"]["n"] == 1
    d2, f2 = distance(GoldMap(live_only=[g("F1")], case_only=[g("F2")]), GoldMap(), FrameCmp(question="different", decider="same_kind", role="same"), C, T)
    assert d2 == 1.0 and f2["frame_penalty"] == 0.2
    assert distance(GoldMap(matched=[GPair(live=g("F1"), case=g("F1"))]), GoldMap(), same, C, T)[0] == 0.0


def _trace(store, tid, scen, text="the module can be wiped", rec=None):
    T = scen[tid]
    opts = [T.case.global_id(o) for o in T.case.options]
    sm = SpanMap(entries=[SpanEntry(fact=T.case.global_id("F1"), message=1, start=0, end=5, realization="stated")],
                 options=[OptionSpan(option=o, message=1, start=10 * (len(opts) - i), end=10 * (len(opts) - i) + 5,
                                     channel=CHANNELS[i % 5]) for i, o in enumerate(opts)])
    store.save_trace(TraceRecord(trace_scenario=tid, split=T.split, span_map=sm, channels={o: CHANNELS[i % 5] for i, o in enumerate(opts)},
                                 recommended_option=rec or opts[0]),
                     {"messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": text}]})


def test_gate_augmented_and_sync(store):
    build(store, seed=0)
    scen = {s.id: s for s in store.scenarios()}
    aug = [r for r in store.pairs() if r.arm == "augmented"]
    assert aug
    out = gate_augmented(store, verifier=lambda *a: (True, "x"))
    assert out["pending_no_trace"] == len(aug) and out["passed"] == 0
    for r in aug:
        _trace(store, r.trace_scenario, scen)
    seen = []
    out = gate_augmented(store, verifier=lambda text, cond, X: (seen.append((text, cond)) or False, "no"))
    assert out["n_failed"] == len(aug) and "wiped" in seen[0][0] and seen[0][1]
    after = store.pair(aug[0].id)
    assert {"rejected", "gate-failed"} <= set(after.tags) and "gate-pending" not in after.tags
    assert (store.pair_dir(aug[0].id) / "pair.yaml").exists()                      # nothing deleted
    build(store, seed=0)                                                           # rebuild keeps the rejection
    assert "rejected" in store.pair(aug[0].id).tags
    assert gate_augmented(store, verifier=lambda *a: (True, ""))["skipped"] == len(aug)
    assert gate_augmented(store, verifier=lambda *a: (True, ""), regate=True)["passed"] == len(aug)
    p = store.pair(aug[0].id)
    assert "gate-passed" in p.tags and "rejected" not in p.tags
    s = stats(store)
    assert s["augmented_gate"] == {"passed": len(aug)}
    # rendered traces feed position / recommendation reports
    r = sync_traces(store)
    assert r["pairs_with_trace"] >= len(aug)
    assert store.pair(aug[0].id).recommended_option == store.trace(aug[0].trace_scenario).recommended_option
    rk = s["per_arm"]
    assert any(isinstance(v["position_first_mention_rank"], dict) for v in rk.values())


def test_gold_structure_from_store_revised_and_none(store):
    build(store, seed=0)
    scen = {s.id: s for s in store.scenarios()}
    seen = set()
    for r in store.pairs():
        if r.arm in seen or r.arm not in ("revised", "none", "augmented"):
            continue
        seen.add(r.arm)
        g = GoldStructure.from_store(store, r)
        k = g.answer_key()
        assert k.arm == r.arm and k.choice == g.glob2live[r.choice] and k.provenance["arm"] == r.arm
        if r.arm == "revised":
            C = scen[r.case_scenario]
            assert g.T.case.verdict.choice == C.case.verdict.choice != scen[r.trace_scenario].case.verdict.choice
            assert len(g.cons_ids) == len(C.case.considerations)
        if r.arm == "none":
            assert k.served is None and k.relation is None
    assert seen == {"revised", "none", "augmented"}


def test_housekeeping_2f(tmp_path):
    st = Store(tmp_path)
    from bench.schema.pipeline import FrameCmp, GoldMap
    X = pilot("DR-AUT-001@v1")
    st.save_scenario(X)
    for pid, intent in (("P-1217d16660", "add_fact"), ("P-7b3fe9966f", "flip"), ("P-2c6540bbdd", "flip")):
        flipc = intent == "flip"
        st.save_pair(PairRecord(id=pid, intent=intent, case_scenario=X.id, trace_scenario=X.id, split="eval-only",
                                frame=FrameCmp(question="same", decider="same", role="same"), options_map={}, fact_map=GoldMap(),
                                consideration_map=GoldMap(), governs=True, relation="flips" if flipc else "follows",
                                via=[X.case.global_id("flip1")] if flipc else None, choice=X.case.global_id("O1"),
                                gold_tier="by-construction", realization="indirect" if flipc else None))
    out = housekeeping_2f(st)
    assert "rejected" in st.pair("P-1217d16660").tags and "T2" in st.pair("P-2c6540bbdd").tags
    assert st.pair("P-7b3fe9966f").realization == "paraphrase" and st.pair("P-2c6540bbdd").realization == "indirect"
    assert any("2f" in (s.notes or "") for s in st.pair("P-1217d16660").provenance.steps)
    assert set(housekeeping_2f(st).values()) == {"already done"} and out


def test_reorder_still_importable():
    T = pilot("DR-INT-301@v1")
    S, m = reorder(T, 1)
    assert S.case.verdict.choice == "O1"
