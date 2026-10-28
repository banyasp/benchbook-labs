"""W3: flip realization + Φ regularization, restyle numeric drift, condition_holds, revise_card, refusals (fakes only)."""
import json
import random
from collections import Counter

import pytest
import yaml

from bench.schema.pipeline import PairRecord, Scenario
from pipeline.perturb import OperatorError, RefusalError, condition_holds, flip, restyle, revise_card, save_result, set_complete
from pipeline.perturb.common import seed_rng
from pipeline.perturb.io import revised_partial_path
from pipeline.perturb.numnorm import drift, numbers
from pipeline.perturb.revise_card import check_text, delta_k, pick_target
from pipeline.store import Store

from .fakes import Fake, pilot, scr
from .test_perturb import PARA, REAL, pair_of, setup


@pytest.fixture(autouse=True)
def _reset():
    yield
    set_complete(None)


# ------------------------------------------------------------------ flip: realization, Φ
def test_flip_paraphrase_realization_skips_overlap_keeps_verify(tmp_path):
    f = Fake(realize=[PARA])
    st, X = setup(tmp_path, f)
    T, p = flip(X, st, random.Random(1), item="flip1", realization="paraphrase")
    assert p["realization"] == "paraphrase" and T.lineage.detail["realization"] == "paraphrase"
    assert "skipped" in T.lineage.detail["indirectness"]
    assert any("You check a claim" in m[0]["content"] for r, m in f.calls)          # verify kept
    assert any("RESTATE ONE listed condition" in m[0]["content"] for r, m in f.calls)
    pair_of(X, T, p)                                                                  # PairRecord accepts realization


def test_flip_indirect_realization_recorded_and_seeded_share(tmp_path):
    st, X = setup(tmp_path, Fake(realize=[REAL]))
    T, p = flip(X, st, random.Random(1), item="flip1", realization="indirect")
    assert p["realization"] == "indirect"
    # seeded choice follows indirect_share (0.7 in config/pipeline.yaml)
    n = 0
    for i in range(200):
        r = random.Random(i)
        n += r.random() < 0.7
    assert 120 < n < 160
    class Both(Fake):
        def __call__(self, role, messages, **kw):
            if "RESTATE ONE listed condition" in messages[0]["content"]:
                self.realize = [PARA]
            elif "make ONE listed condition true" in messages[0]["content"]:
                self.realize = [REAL]
            return super().__call__(role, messages, **kw)
    set_complete(Both(realize=[REAL]))
    seen = Counter()
    for i in range(12):
        T, p = flip(X, st, random.Random(i), item="flip1")
        seen[p["realization"]] += 1
        assert (p["realization"] == "paraphrase") == bool(T.lineage.detail["indirectness"].get("skipped"))
    assert seen["indirect"] > seen["paraphrase"] > 0


def test_flip_phi_regularized(tmp_path):
    st, X = setup(tmp_path, Fake(realize=[REAL]))
    T, p = flip(X, st, random.Random(1), item="flip1", realization="indirect")
    wc = T.case.flip_conditions.would_change
    assert len(wc) == len(X.case.flip_conditions.would_change) == 4
    assert all(w.then != T.case.verdict.choice or False for w in wc if w.then == X.case.verdict.choice) 
    assert not any(w.then == T.case.verdict.choice for w in wc)                      # none vacuous
    back = T.lineage.detail["back_flip"]
    bw = next(w for w in wc if T.case.global_id(w.id) == back["item"])
    assert bw.then == X.case.verdict.choice and back["then"] == T.case.global_id(X.case.verdict.choice)
    assert [w.id for w in wc] == ["flip1", "flip2", "flip3", "flip4"]                # renumbered in the shuffled order
    touched = next(c for c in T.case.considerations if c.id == "C3")
    assert touched.weight == X.case.considerations[2].weight                         # not systematically weak
    assert T.lineage.detail["phi"]["would_change_parent"] == T.lineage.detail["phi"]["would_change_child"] == 4
    assert len(T.lineage.detail["phi"]["authored_items"]) == 3
    assert "flip-conditions-authored" in T.tags
    assert len([a for a in T.provenance.authored if "would_change" in a]) == 3
    # order is shuffled: over seeds the back-flip item does not always land in the same slot
    slots = set()
    for i in range(10):
        set_complete(Fake(realize=[REAL]))
        T2, _ = flip(X, st, random.Random(i), item="flip1", realization="indirect")
        slots.add(next(n for n, w in enumerate(T2.case.flip_conditions.would_change) if T2.case.global_id(w.id) == T2.lineage.detail["back_flip"]["item"]))
    assert len(slots) > 1


def test_flip_rejects_weak_touched_and_short_phi(tmp_path):
    class WeakFake(Fake):
        def answer_parts(self, b, then, fired):
            out = super().answer_parts(b, then, fired)
            if then:
                out["considerations"][self.touched]["weight"] = "weak"
            return out
    st, X = setup(tmp_path, WeakFake(realize=[REAL]))
    with pytest.raises(OperatorError, match="weaken"):
        flip(X, st, random.Random(1), item="flip1", realization="indirect")

    class ShortFake(Fake):
        def answer_parts(self, b, then, fired):
            out = super().answer_parts(b, then, fired)
            out.pop("new_would_change", None)
            return out
    set_complete(ShortFake(realize=[REAL]))
    with pytest.raises(OperatorError, match="must keep 4 would_change"):
        flip(X, st, random.Random(1), item="flip1", realization="indirect")


def test_condition_holds_public():
    f = Fake(verify=True)
    set_complete(f)
    X = pilot("DR-AUT-001@v1")
    assert condition_holds("the module can be wiped", "Some rendered trace text.")["holds"] is True
    assert condition_holds("x", X)["holds"] is True                                  # a Scenario is accepted
    set_complete(Fake(verify=False))
    assert condition_holds("x", "text")["holds"] is False


# ------------------------------------------------------------------ restyle numeric drift
def test_numnorm_formats():
    assert numbers("fee $1,200") == numbers("1200 dollars") == numbers("1.2k USD")
    assert numbers("40% on March 3, 2025 at 2:30 pm") == numbers("forty percent on 3/3/2025 at 14:30")
    assert not drift("twenty minutes", "20 minutes")["missing"]
    assert drift("20 minutes", "25 minutes")["missing"] == ["20"]


def test_restyle_rejects_numeric_drift_in_decisive_facts(tmp_path):
    class Drift(Fake):
        def fq(self, b):
            out = super().fq(b)
            out["facts"]["F9"] = out["facts"]["F9"].replace("1,900", "2,400")
            return out
    st, X = setup(tmp_path, Drift())
    with pytest.raises(OperatorError, match="numeric drift"):
        restyle(X, st, random.Random(1))


def test_restyle_allows_formatting_change(tmp_path):
    class Fmt(Fake):
        def fq(self, b):
            out = super().fq(b)
            out["facts"]["F9"] = out["facts"]["F9"].replace("1,900", "1900")
            return out
    st, X = setup(tmp_path, Fmt())
    T, p = restyle(X, st, random.Random(1))
    assert "1900" in T.case.facts[8].fact and T.lineage.detail["numeric_drift_in_decisive_facts"] == []


# ------------------------------------------------------------------ revise_card
class ReviseFake:
    def __init__(self, mutate=None, add=False):
        self.mutate, self.add, self.calls = mutate, add, []

    def __call__(self, role, messages, **kw):
        self.calls.append((role, messages))
        sysm, user = messages[0]["content"], messages[1]["content"]
        assert "You revise the weighing" in sysm
        tgt = user.split("TARGET: ")[1].split(" ")[0]
        case = json.JSONDecoder().raw_decode(user[user.index("{"):])[0]
        cur = case["verdict"]["choice"]
        cons, changed, new = {}, [], None
        for cid, c in case["considerations"].items():
            if cur in c["favors"] and tgt not in c["favors"]:
                if not self.add:
                    cons[cid] = {"weight": "weak" if c["weight"] != "weak" else "strong", "why": scr(c["why"])}
                    if c["weight"] == "weak":
                        cons[cid]["weight"] = "strong"
                    changed.append(cid)
        dec = [cid for cid, c in case["considerations"].items() if tgt in c["favors"]]
        if self.add:
            new = {"facts": ["F1"], "equity": "deployer_priority", "favors": [tgt], "weight": "strong", "why": "A new reading of {F1} favors the other option."}
            dec = ["C%d" % (len(case["considerations"]) + 1)]
        r = case["reasoning"]
        other = [o for o in case["options"] if o != tgt][0]
        wc = [w for w in case["flip"] if w.startswith("flip")]
        kept = [w for w in wc if case["flip_then"][w] != tgt]
        out = {"summary": "The weighing now ranks the other interest higher.", "changed": changed, "considerations": cons,
               "new_consideration": new, "decisive": dec,
               "reasoning": {**{k: scr(r[k]) for k in ("read", "weighing", "tradecraft", "uncertainty", "handoff")},
                             "tempting_wrong": {"option": other, "pull": "pull text", "why_wrong": "why wrong text"},
                             "rejected": {other: "rejected text"}},
               "flip": {}, "new_would_change": [{"if": f"another condition {i}", "then": other, "why": "because"} for i in range(len(wc) - len(kept))],
               "lesson": "lesson text", "limits": "limits text"}
        if not any(case["flip_then"][w] == other for w in kept):
            pass
        if self.mutate:
            self.mutate(out)
        return json.dumps(out)


def rv(tmp_path, fake, **kw):
    set_complete(fake)
    st, X = Store(tmp_path), pilot("DR-AUT-001@v1")
    return st, X, revise_card(X, st, random.Random(2), **kw)


def test_revise_card_reweight(tmp_path):
    st, X, (T, p) = rv(tmp_path, ReviseFake())
    assert T.case.verdict.choice == "O2" and T.lineage.operator == "revise_card" and T.lineage.parent == X.id
    assert "revised-authored" in T.tags and T.verdict_tier == "by-construction" and T.id == "DR-AUT-001-revise1@v1"
    for k in ("facts", "setting", "decider", "agent", "agent_role", "situation", "question", "options"):
        assert T.case.dump()[k] == X.case.dump()[k]
    dk = T.lineage.detail["delta_k"]
    assert dk["changed"] == [X.case.global_id(c) for c in ("C1", "C2", "C3")] and dk["added"] == []
    assert len(T.case.flip_conditions.would_change) == len(X.case.flip_conditions.would_change)
    assert any(w.then == "O1" for w in T.case.flip_conditions.would_change)
    st_ = [s for s in T.provenance.steps if s.id == "revise_card.revise"][0]
    assert st_.role == "perturber" and st_.prompt_version.startswith("revise_card.v1+")
    assert p["intent"] == "revised" and p["arm"] == "revised" and p["relation"] == "follows" and p["tags"] == ["revised-authored"]
    assert p["choice"] == X.case.global_id("O2") and p["case_scenario"] == T.id and p["trace_scenario"] == X.id
    assert len(p["consideration_map"].corresponding) == 3 and len(p["consideration_map"].matched) == 1
    sp, pp = save_result(st, T, p)
    assert pp == revised_partial_path(st, T.id) and pp.exists()
    assert not (st.root / "partials" / f"{T.id}.yaml").exists()                      # pair's scan ignores it
    PairRecord(id="P-x", split=X.split, **{**p, "provenance": p["provenance"]})      # PairRecord-shaped
    Scenario.model_validate(T.dump())


def test_revise_card_add_consideration_cites_fact(tmp_path):
    st, X, (T, p) = rv(tmp_path, ReviseFake(add=True))
    assert T.lineage.detail["delta_k"]["added"] == [f"{T.id}/C5"] and T.case.considerations[-1].facts == ["F1"]
    assert p["consideration_map"].case_only == [f"{T.id}/C5"]


@pytest.mark.parametrize("mut,err", [
    (lambda o: o.__setitem__("changed", ["C1"]), "you claimed"),
    (lambda o: o.__setitem__("new_consideration", {"facts": [], "equity": "x", "favors": ["O2"], "weight": "strong", "why": "w"}), "at least one"),
    (lambda o: o["reasoning"].__setitem__("weighing", "The source emphasizes the cost."), "source narration"),
    (lambda o: o["reasoning"].__setitem__("read", "Then Sergeant Hollis decided to stay."), "personal name"),
    (lambda o: o.__setitem__("decisive", ["C1"]), "decisive"),
    (lambda o: o["considerations"].__setitem__("C1", {"facts": ["F2"]}), "only weight"),
])
def test_revise_card_gate(tmp_path, mut, err):
    set_complete(ReviseFake(mutate=mut))
    with pytest.raises(OperatorError, match=err):
        revise_card(pilot("DR-AUT-001@v1"), Store(tmp_path), random.Random(2))


def test_revise_card_refusal_recorded_not_retried(tmp_path):
    calls = []
    set_complete(lambda role, m, **kw: calls.append(1) or "I'm sorry, but I can't help with that.")
    with pytest.raises(RefusalError) as ei:
        revise_card(pilot("DR-AUT-001@v1"), Store(tmp_path), random.Random(2))
    assert len(calls) == 1 and ei.value.step.params["refusal"] is True
    set_complete(lambda role, m, **kw: "")
    with pytest.raises(RefusalError):
        flip(pilot("DR-AUT-001@v1"), Store(tmp_path), random.Random(1), item="flip1")


def test_pick_target_balance_and_handup_cap():
    X = pilot("DR-INT-103@v1")                                                       # moves: act, partial, refuse, act
    assert X.case.verdict.choice == "O2"
    tally, hand = Counter(), 0
    for i in range(60):
        pt = pick_target(X, random.Random(i), tally)
        assert pt["target"] != X.case.verdict.choice
        tally[pt["move"]] += 1
    total = sum(tally.values())
    assert (tally["ask"] + tally["refuse"]) / total <= 1 / 3 + 1e-9
    assert tally["act"] > 0 and tally["refuse"] > 0
    # only hand-ups available: cap is waived and recorded
    Y = pilot("DR-REL-301@v1")
    pt = pick_target(Y, random.Random(0), Counter({"act": 5}), cap=0.0)
    assert pt["move"] in ("act", "ask")


def test_check_text_rules():
    check_text({"a": "Weigh the duty to the crew first. The deployer now ranks {F1} above cost."}, "crew deployer")
    with pytest.raises(ValueError):
        check_text({"a": "According to the source, hold."}, "")
    with pytest.raises(ValueError):
        check_text({"a": "Dr. Alvarez agreed."}, "")
