"""Offline tests for the code-only parts of pipeline.ops (no model calls)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bench.schema.pipeline import Scenario
from pipeline.store import Store
from pipeline.ops import checks as CK
from pipeline.ops.frame import mentions, remove_structurally, set_path, text_fields
from pipeline.ops.permute import apply_order, permute
from pipeline.ops.record import OpResult, finish, new_id

REAL = Store()
SID = "DR-CORPUS-NX-7b45b55b-E2@v1"


def three_option_scenario() -> Scenario:
    for p in sorted((REAL.root / "scenarios").glob("CORPUS*/*.yaml")):
        S = Scenario.load(p)
        if len(S.case.options) >= 3 and not S.lineage.parent:
            return S
    pytest.skip("no 3-option corpus scenario")


@pytest.fixture
def tmp_store(tmp_path):
    s = Store(tmp_path / "data")
    (s.root / "scenarios").mkdir(parents=True)
    return s


def test_permute_options_gold_to_every_position(tmp_store):
    X = three_option_scenario()
    n = len(X.case.options)
    for k in range(1, n + 1):
        r = permute(X, tmp_store, target="options", order={"gold_to": k})
        if r.skipped:
            assert list(X.case.options).index(X.case.verdict.choice) + 1 == k
            continue
        S = r.scenario
        assert list(S.case.options).index(S.case.verdict.choice) + 1 == k
        mp = r.delta["id_map"]
        assert [S.case.options[mp[o]].do for o in X.case.options] == [X.case.options[o].do for o in X.case.options]
        for a, b in zip(X.case.considerations, S.case.considerations):
            assert sorted(mp[o] for o in a.favors) == sorted(b.favors)
        assert set(S.case.options) == {f"O{i}" for i in range(1, n + 1)}


def test_permute_facts_renames_citations_and_spans(tmp_store):
    X = REAL.scenario(SID)
    ids = [f.id for f in X.case.facts]
    r = permute(X, tmp_store, target="facts", order=list(reversed(ids)))
    S, mp = r.scenario, r.delta["id_map"]
    text = {f.id: f.fact for f in X.case.facts}
    assert {f.id: f.fact for f in S.case.facts} == {mp[k]: v for k, v in text.items()}
    for a, b in zip(X.case.considerations, S.case.considerations):
        assert sorted(mp[f] for f in a.facts) == sorted(b.facts)
    assert set(S.fact_spans) == {mp[k] for k in X.fact_spans}


def test_k_equivalence_is_exact_on_weight():
    a = CK.case_dict(REAL.scenario(SID))
    b = CK.case_dict(REAL.scenario(SID))
    assert CK.k_equivalent(a, b)[0]
    b["considerations"][0]["weight"] = "weak" if b["considerations"][0]["weight"] != "weak" else "strong"
    ok, diff = CK.k_equivalent(a, b)
    assert not ok and a["considerations"][0]["id"] in diff


def test_drop_option_structure_and_paths():
    X = three_option_scenario()
    case = CK.case_dict(X)
    k = [o for o in case["options"] if o != case["verdict"]["choice"]][-1]
    d, info = remove_structurally(case, k)
    assert k not in d["options"] and all(k not in c["favors"] for c in d["considerations"])
    assert all(w["then"] != k for w in d["flip_conditions"]["would_change"])
    fields = dict(text_fields(d))
    path = next(iter(fields))
    set_path(d, path, "edited")
    assert dict(text_fields(d))[path] == "edited"
    assert mentions("see {O3} and O3.", ["O3"]) and not mentions("O31", ["O3"]) and not mentions("C10", ["C1"])
    order = [o for o in case["options"] if o != k]
    c2, mp = apply_order(d, "options", order)
    assert set(c2["options"]) == {f"O{i}" for i in range(1, len(order) + 1)}


def test_finish_records_lineage_and_inherits(tmp_store):
    X = REAL.scenario(SID)
    r = permute(X, tmp_store, target="options", order={"gold_to": 2 if list(X.case.options).index(X.case.verdict.choice) == 0 else 1})
    row = finish(tmp_store, X, r)
    S = tmp_store.scenario(row["id"])
    assert S.family == X.family and S.split == X.split and S.held_out == X.held_out
    assert S.lineage.anchor == X.id and S.lineage.parent == X.id
    st = S.lineage.steps[-1]
    assert st["op"] == "permute" and st["bucket"] == "accepted" and st["writer"]["backend"] == "code" and st["delta"]["id_map"]
    # a second application chains: anchor stays the root, steps accumulate
    r2 = permute(S, tmp_store, target="options", order="random", seed=3)
    if not r2.skipped:
        row2 = finish(tmp_store, S, r2)
        S2 = tmp_store.scenario(row2["id"])
        assert S2.lineage.anchor == X.id and len(S2.lineage.steps) == 2


def test_new_id_unique_under_reservation(tmp_store):
    ids = {new_id(tmp_store, "CORPUS-X", "permute", None) for _ in range(5)}
    assert len(ids) == 5


def test_bucket_rules():
    r = OpResult("surface_edit", "transfer", {}, scenario=object())       # type: ignore[arg-type]
    r.gates = {"structure": {"pass": True}, "setting_adds": {"pass": False}}
    assert r.bucket[0] == "hard"
    r.gates["leak"] = {"pass": False}
    assert r.bucket[0] == "rejected"
    assert OpResult("x", None, {}, None, skipped="no-op").bucket[0] == "skipped"


def test_recipe_expand_planner():
    from pipeline.ops.recipes import expand
    X = REAL.scenario(SID)
    T3 = three_option_scenario()
    jobs = expand({"op": "structural_edit", "args": {"mode": "flip", "phi": "each"}}, [X])
    assert [kw["phi"] for _, kw in jobs] == [w.id for w in X.case.flip_conditions.would_change if w.then != X.case.verdict.choice]
    jobs = expand({"op": "permute", "args": {"target": "options", "order": "balance"}}, [X, T3])
    assert all("gold_to" in kw["order"] for _, kw in jobs)
    jobs = expand({"op": "frame_edit", "args": {"option": "each_nongold"}}, [T3])
    assert len(jobs) == len(T3.case.options) - 1
