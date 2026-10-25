"""(b) AUT-101 end to end, (c) AUT-001 against the v6 worked mapping, plus the 3.1/3.4/3.5 mechanics
(unreachable default, orders, stability and U*, knockout, mirror) and the derived guidance of 3.6."""
import copy
import solver_v3 as S
import reward_v2 as RW
from conftest import cat, rec, card, sit, cat_with, vep_cards, VEP_STUDY


def _aut101():
    aut, r = cat("AUT"), rec("AUT-101")
    return aut, r, S.cards_from_record(aut, r), S.situation_from_record(aut, r)


# ------------------------------------------------------------------------------------------ (b)
def test_b_aut101_gold_plan_from_gold_tags():
    """r2 CHANGED (shape): v2 routes carry side, a `to` list and an interim restrictive side (P4, A2)."""
    aut, r, cards, s = _aut101()
    gold = r["record"]["resolution"]["plan"]
    res = S.compose(aut, cards, s)
    assert S.plan_matches(gold, res["plan"])
    assert (res["actions"]["PREP"]["act"], res["actions"]["PREP"]["side"]) == ("proceed", "A")
    dep = res["actions"]["DEP"]
    assert (dep["act"], dep["side"], dep["because"], dep["to"], dep["recommend"], dep["interim"]) == \
        ("route", "A", "authorize", ["vessel master"], None, "B")
    assert {"act": "proceed", "issue": "DEP", "side": "B", "interim": True} in res["plan"]
    # serving AUT-001's holding as well changes nothing (it is distinguished on DEP)
    c001 = S.cards_from_record(aut, rec("AUT-001"), with_flips=False)
    assert S.plan_matches(gold, S.compose(aut, cards + c001, s)["plan"])


def test_b_aut101_flip_x1_makes_departure_autonomous():
    aut, r, cards, s = _aut101()
    s1 = dict(s, tags=S.apply_change(aut, s["tags"], ["+cond.threat_confirmed", "+cond.master_unreachable"]))
    res = S.compose(aut, cards, s1)
    dep = res["actions"]["DEP"]
    assert (dep["act"], dep["side"], dep["support"]) == ("proceed", "A", "binding")
    assert not [a for a in res["plan"] if a["act"] == "contingent"]
    s2 = dict(s, tags=S.apply_change(aut, s["tags"], ["+DEP-B2@likely"]))             # flip x2
    dep2 = S.compose(aut, cards, s2)["actions"]["DEP"]
    assert (dep2["act"], dep2["because"], dep2["to"]) == ("route", "authorize", ["vessel master"])


def test_b_finding_cross_record_near_miss_conflict():
    """r2 FIXED (A4). Round 1: AUT-001's compiled flips (-A3 -> B, -A1 -> B, reason {DEP-B1}) bound a fortiori
    on AUT-101 and settled DEP on hold. v2 ranks near-miss cards a half-step below their base and applies them
    only ceteris paribus (AUT-001's other A-side tags DEP-A1/A3 must be present), so AUT-101 keeps its gold.
    The naqd lint still flags the pair on the union situation (module aboard + trigger met): a real conflict
    between the two records' counterfactuals, resolved as bounded (equal rank)."""
    aut, r, cards, s = _aut101()
    c001 = S.cards_from_record(aut, rec("AUT-001"))
    res = S.compose(aut, cards + c001, s)
    assert S.plan_matches(r["record"]["resolution"]["plan"], res["plan"])
    v = res["assessed"]["DEP"]["verdicts"]
    assert v[("AUT-001/x1", "DEP", None)]["verdict"] == "off_point" and "scope" in v[("AUT-001/x1", "DEP", None)]["note"]
    assert {c["rank"] for c in c001 if c["kind"] == "flip"} == {2.5}
    pairs = {(b["p"][0], b["q"][0]) for b in S.lint_horty(aut, cards + c001)}
    assert ("AUT-101/x1", "AUT-001/x1") in pairs


def test_b_derived_guidance_and_lints():
    aut, r, cards, s = _aut101()
    # r2 CHANGED (A5 on): PREP-B1's weak own_force_life is blocked by PREP-A1 (strong, same equity), so it no
    # longer distinguishes the PREP card and drops out of watch_for.
    assert S.watch_for(aut, cards, s) == [("cond.master_unreachable", ["DEP"])]
    assert ("+cond.master_unreachable", ("proceed", "B")) in S.flip_set(aut, cards, s, "DEP")
    assert S.lint_horty(aut, cards) == []
    for I in ("DEP", "PREP"):
        assert S.lint_monotone(aut, cards, s["tags"], I) == []


# ------------------------------------------------------------------------------------------ (c)
def test_c_aut001_v6_mapping_collapses_to_one_stem():
    aut, r = cat("AUT"), copy.deepcopy(rec("AUT-001"))
    facts = r["record"]["situation"]["facts"]
    facts[-1] = {"id": "g5", "text": "He is likely alive and recoverable inside the window", "status": "assessed",
                 "likelihood": "likely", "confidence": "moderate", "tags": ["DEP-B2@even", "DEP-B2@likely"]}
    item = RW.item_from_record(aut, r, served_cards=S.cards_from_record(aut, rec("AUT-001"), with_flips=False))
    gold = item["situation"]["tags"]
    assert gold == aut.close(["DEP-A1", "DEP-A2@likely", "DEP-A3", "DEP-B1", "DEP-B2@likely"])
    v = S.compare(aut, item["served"][0], gold)
    assert v["verdict"] == "distinguished" and v["new"] == ["DEP-B2@likely"]          # one stem, rung: likely
    assert v["significant"] == ["DEP-B2@likely"] and v["uncovered"]["DEP-B2@likely"] == ["own_force_life"]
    v6 = RW.oracle_mapping(item)          # the v6 mapping: distinctions [B2@likely], verdict distinguish
    v6["compare"] = [{"id": "AUT-001", "issue": "DEP", "unit": None, "verdict": "distinguished",
                      "significant": ["DEP-B2@likely"]}]
    assert RW.f1(v6["compare"][0]["significant"], v["significant"]) == 1.0
    assert RW.r_cmp(item, v6, "training") == 1.0


# ------------------------------------------------------------------------------------------ 3.5 / 3.1 mechanics
def test_no_human_reachable_takes_the_default_and_keeps_the_contingency():
    aut, r, cards, s = _aut101()
    s1 = dict(s, tags=S.apply_change(aut, s["tags"], ["+cond.master_unreachable"]))
    res = S.compose(aut, cards, s1)
    dep = res["actions"]["DEP"]
    assert (dep["act"], dep["side"]) == ("proceed", "B") and dep["basis"].startswith("default")
    assert any(a["act"] == "contingent" for a in res["plan"])


def test_orders_exclude_active_and_disabled():
    aut = cat("AUT")
    X = aut.close(["DEP-A1", "DEP-A2@likely", "DEP-A3"])
    c = card("P", "DEP", "A", aut.close(["DEP-A1", "DEP-A2@likely", "DEP-A3"]), X)
    order = {"from": "fleet commander", "directs": {"issue": "DEP", "side": "A"}, "excludes": ["duty_to_crew"],
             "active_when": ["cond.order_authenticated"], "disabled_by": ["cond.order_unlawful"]}
    auth = {"deciders": [], "delegations": [], "orders": [order]}
    Y = X | {"DEP-B1"}
    assert S.assess(aut, [c], sit(Y, authority=auth), "DEP")["status"] == "open"          # not authenticated
    a = S.assess(aut, [c], sit(Y | {"cond.order_authenticated"}, authority=auth), "DEP")
    assert (a["status"], a["side"]) == ("settled", "A")                                  # B1 excluded
    s3 = sit(Y | {"cond.order_authenticated", "cond.order_unlawful"}, authority=auth)
    act = S.compose(aut, [c], s3)["actions"]["DEP"]
    assert act["act"] == "route" and act["because"] == "flag"


def test_stability_and_one_question_left():
    v = cat("VEP")
    c004 = vep_cards(v)["VEP-004"]
    Y = v.close({"D1", "D2@high", "D3", "R1", "R3"})           # VEP-004 binds unless R2 (NC3 access) holds
    s = sit(Y, authority=VEP_STUDY, uncertain={"R2": ["absent", "present"]})
    a = S.assess(v, [c004], s, "DISC")
    assert a["status"] == "unstable" and a["ustar"] == ["R2"]
    act = S.compose(v, [c004], s)["actions"]["DISC"]
    assert act["act"] == "route" and act["because"] == "inform" and act["question"] == ["R2"]
    s["uncertain"] = {}
    assert S.compose(v, [c004], s)["actions"]["DISC"]["act"] == "proceed"
    # an uncertain delegation condition never activates the delegation (3.1)
    aut, r, cards, s1 = _aut101()
    s1 = dict(s1, tags=s1["tags"] | {"cond.threat_confirmed"}, uncertain={"cond.master_unreachable": ["absent", "present"]})
    assert S.compose(aut, cards, s1)["actions"]["DEP"]["because"] == "authorize"


def test_knockout_is_never_downplayed():
    Y = {"D1", "D2@moderate", "D6", "R1", "R2", "R3"}
    plain = cat("VEP")
    ko = cat_with("VEP", patch=lambda c: c["factors"]["D6"].update(knockout=True))
    assert S.compare(plain, vep_cards(plain)["VEP-001"], plain.close(Y))["verdict"] == "analogous"
    assert S.compare(ko, vep_cards(ko)["VEP-001"], ko.close(Y))["verdict"] == "distinguished"


def test_mirror_faces_of_one_dimension():
    doc = {"catalog": {"id": "M", "version": "1", "issues": {"I": {"question": "q", "sides": {"A": "a", "B": "b"},
           "action": {"A": "GO", "B": "STOP"}, "default": "B"}}, "equities": {"e": {}},
           "dimensions": {"d": {"rungs": ["lo", "mid", "hi"], "mirror": False}},
           "factors": {"A1": {"issue": "I", "favors": "A", "text": "value at least r", "equities": {"e": "strong"},
                              "dimension": "d", "rungs": {"lo": "weak", "mid": "strong", "hi": "strong"}},
                       "B1": {"issue": "I", "favors": "B", "text": "value at most r", "equities": {"e": "strong"},
                              "dimension": "d", "rungs": {"lo": "strong", "mid": "strong", "hi": "weak"},
                              "mirror_of": "A1"}},
           "actions": {"GO": {"direction": "permissive", "tier": "T0"}, "STOP": {"direction": "restrictive"}},
           "authority": {"levels": ["agent"], "tiers": {"T0": "agent"}, "roles": {"execute": "agent"}},
           "stakes": {"T0": {"L": 1, "k": 0.2}}}}
    off = S.Catalog(doc)
    assert off.close(["B1@mid"]) == {"B1@mid", "B1@hi"}                 # a mirror face closes upward
    X = off.close(["A1@hi", "B1@hi"])
    c = card("P", "I", "A", off.close(["A1@mid"]), X)
    Y = off.close(["A1@mid", "B1@mid"])
    assert S.compare(off, c, Y)["verdict"] == "distinguished"
    doc["catalog"]["dimensions"]["d"]["mirror"] = True
    assert S.compare(S.Catalog(doc), c, Y)["verdict"] == "binding"
