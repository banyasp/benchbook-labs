"""perturb operators, offline (a scripted stand-in replaces the models)."""
import json
import random

import pytest

from bench.schema.pipeline import PairRecord, Scenario
from pipeline.perturb import OperatorError, add_fact, flip, restyle, set_complete
from pipeline.perturb.common import check_gold
from pipeline.perturb.add_fact import solver_messages
from pipeline.perturb.overlap import overlap
from pipeline.store import Store

from .fakes import Fake, pilot

REAL = {"technique": "magnitude", "touched_consideration": "C3", "how": "a purge takes longer than the time left",
        "edits": [{"action": "replace", "fact": "F10", "kind": "capability", "status": "confirmed",
                   "text": "A purge routine on the module needs about nine minutes to finish, and the watch puts boarding about fourteen minutes out."}]}
PARA = {**REAL, "edits": [{"action": "replace", "fact": "F10", "text": "The module can be wiped or destroyed before capture.", "kind": "capability", "status": "confirmed"}]}


@pytest.fixture(autouse=True)
def _reset():
    yield
    set_complete(None)


def setup(tmp_path, fake):
    set_complete(fake)
    return Store(tmp_path), pilot("DR-AUT-001@v1")


def pair_of(X, T, partial):
    return PairRecord(id="P-test", **{k: v for k, v in partial.items() if k not in ("case_scenario", "trace_scenario")},
                      case_scenario=X.id, trace_scenario=T.id, split=X.split)


def test_restyle_gold_complete(tmp_path):
    f = Fake()
    st, X = setup(tmp_path, f)
    T, p = restyle(X, st, random.Random(1))
    assert T.id == "DR-AUT-001-restyle1@v1" and T.family == X.family and T.split == X.split and T.status == "derived"
    assert T.lineage.parent == X.id and T.lineage.operator == "restyle"
    check_gold(X, T, p)
    assert len(p["fact_map"].matched) == len(X.case.facts) and not (p["fact_map"].corresponding or p["fact_map"].live_only)
    assert len(p["consideration_map"].matched) == len(X.case.considerations)
    assert all(v is not None for v in p["options_map"].values()) and p["relation"] == "follows" and p["gold_tier"] == "by-construction"
    assert T.case.verdict.choice == X.case.verdict.choice and T.case.facts[0].fact != X.case.facts[0].fact
    assert [c.facts for c in T.case.considerations] == [c.facts for c in X.case.considerations]
    pair_of(X, T, p)
    Scenario.model_validate(T.dump())


def test_flip_via_and_choice_and_indirectness(tmp_path):
    f = Fake(realize=[REAL])
    st, X = setup(tmp_path, f)
    T, p = flip(X, st, random.Random(1), item="flip1")
    check_gold(X, T, p)
    assert p["relation"] == "flips" and p["via"] == ["DR-AUT-001@v1/flip1"] and p["gold_tier"] == "by-construction"
    assert p["choice"] == T.case.global_id("O2") and p["options_map"][p["choice"]] == X.case.global_id("O2")
    assert T.case.verdict.choice == "O2"
    # F10 replaced -> corresponding; touched consideration corresponding; everything else matched
    assert [g.case for g in p["fact_map"].corresponding] == ["DR-AUT-001@v1/F10"]
    assert X.case.global_id("C3") in [g.case for g in p["consideration_map"].corresponding]
    assert p["touched"].item == "DR-AUT-001@v1/flip1" and "wiped" in p["touched"].condition
    ind = T.lineage.detail["indirectness"]
    assert ind["pass"] and ind["recall"] <= 0.5
    # not C plus one sentence: the unchanged facts were restyled
    assert sum(1 for a, b in zip(X.case.facts, T.case.facts) if a.fact != b.fact) == len(X.case.facts)
    # the fired flip now reads as the reversal and points back to C's choice
    w = {x.id: x for x in T.case.flip_conditions.would_change}
    assert w["flip1"].then == "O1"
    assert all(x.then != "O2" for x in T.case.flip_conditions.would_change)
    pair_of(X, T, p)


def test_flip_overlap_rejects_paraphrase_then_retries(tmp_path):
    f = Fake(realize=[PARA, REAL])
    st, X = setup(tmp_path, f)
    T, p = flip(X, st, random.Random(1), item="flip1")
    realize_calls = [m for r, m in f.calls if "make ONE listed condition true" in m[0]["content"]]
    assert len(realize_calls) == 2 and "paraphrase" in realize_calls[1][-1]["content"]
    assert "wiped" not in T.case.facts[-1].fact + " ".join(x.fact for x in T.case.facts)


def test_flip_all_paraphrases_fail(tmp_path):
    st, X = setup(tmp_path, Fake(realize=[PARA]))
    with pytest.raises(OperatorError):
        flip(X, st, random.Random(1), item="flip1")


def test_overlap_metric():
    iff = "the module can be wiped or destroyed before capture"
    assert not overlap("The module could be wiped or destroyed prior to capture.", iff)["pass"]
    assert overlap(REAL["edits"][0]["text"], iff)["pass"]


def test_flip_unverified_condition_rejected(tmp_path):
    st, X = setup(tmp_path, Fake(realize=[REAL], verify=False))
    with pytest.raises(OperatorError):
        flip(X, st, random.Random(1), item="flip1")


@pytest.mark.parametrize("choice,rel", [("O1", "follows"), ("O2", "distinguished")])
def test_add_fact_independent_solve(tmp_path, choice, rel):
    f = Fake(solver_choice=choice)
    st, X = setup(tmp_path, f)
    T, p = add_fact(X, st, random.Random(3))
    check_gold(X, T, p)
    assert p["relation"] == rel and p["gold_tier"] == "model-solved" and T.verdict_tier == "model-solved"
    assert T.case.verdict.choice == choice and p["via"] is None
    assert len(p["fact_map"].live_only) == 1 and len(T.case.facts) == len(X.case.facts) + 1
    # the solver saw only T's F and Q: build the same messages from the final T and compare, then check for C content
    solve_calls = [m for r, m in f.calls if r == "independent_solver"]
    assert len(solve_calls) == 1
    assert solve_calls[0] == solver_messages(T.case.dump())
    text = json.dumps(solve_calls[0])
    c = X.case
    leaked = [s for s in ([x.why for x in c.considerations] + [c.lesson, c.limits, c.reasoning.weighing, c.reasoning.read]
                          + [w.if_ for w in c.flip_conditions.would_change] + [c.id, T.id, "addfact", "add_fact", "MODE",
                                                                              "would_change", "PARENT", "propose"]) if s in text]
    assert not leaked, leaked
    pair_of(X, T, p)
    if rel == "distinguished":
        assert any(w.then == X.case.verdict.choice for w in T.case.flip_conditions.would_change)


def test_provenance_recorded(tmp_path):
    st, X = setup(tmp_path, Fake(solver_choice="O1"))
    T, p = add_fact(X, st, random.Random(3))
    ids = [s.id for s in T.provenance.steps]
    assert "add_fact.solve" in ids and "perturb.construct" in ids
    solve = next(s for s in T.provenance.steps if s.id == "add_fact.solve")
    assert solve.role == "independent_solver"
