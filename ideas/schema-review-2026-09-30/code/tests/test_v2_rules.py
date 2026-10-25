"""Round 2: tests for the spec v2 rules, on the converter's six Hard-Calls records (records/hc/, verbatim
copies of drafts/hc-v7-v2/) and on this prototype's own records."""
import copy, os
import solver_v3 as S
import validate_v7 as V
from conftest import path, cat, rec, card, sit


def hc(rid):
    r = S.load_yaml(path("records", "hc", f"{rid}.yaml"))
    cid = r["record"]["catalog"].split("@")[0]
    return S.load_catalog(path("catalogs", "hc", f"catalog-{cid}.yaml")), r


def units_sit(c, r, u):
    return S.situation_from_record(c, r, u)


def dep(a):
    return (a["act"], a.get("side"), a.get("because"))


# ------------------------------------------------------------------------------------------ H1
def test_h1_delegation_cannot_launder_past_a_tier_floor():
    """AGT-106: d3 lets this agent package nominees. NOM-B1 (protected activity only) puts a T3 floor on N7;
    the delegation does not list it in covers_floors, so it no longer covers N7 (H1). The six stay within role."""
    c, r = hc("AGT-106")
    n7, six = units_sit(c, r, "N7"), units_sit(c, r, "nominees_foreign")
    assert S.gate(c, six, "NOM", six["tags"])["A"]["via"] == "delegation"
    g = S.gate(c, n7, "NOM", n7["tags"])["A"]
    assert not g["within"] and g["via"] is None
    r2 = copy.deepcopy(r)
    next(d for d in r2["record"]["situation"]["authority"]["delegations"] if d["id"] == "d3")["covers_floors"] = ["NOM-B1"]
    n7b = units_sit(c, r2, "N7")
    assert S.gate(c, n7b, "NOM", n7b["tags"])["A"]["via"] == "delegation"          # an explicit cover is honoured
    got = S.compose_record(c, r, S.cards_from_record(c, r), V.hidden_pi(c, r["record"]))
    assert S.plan_matches(r["record"]["resolution"]["plan"], got["plan"])


def test_h1_the_order_path_needs_the_level_check():
    """Converter g1: the analyst's live order (level operator) would re-open the laundering on N7 if an order
    authorized regardless of level. With ORDER_LEVEL_CHECK (this prototype's reading) N7 routes; literally it
    is packaged whenever the model leans to include."""
    c, r = hc("AGT-106")
    cards = S.cards_from_record(c, r)
    lean_in = dict(V.hidden_pi(c, r["record"]), **{"NOM[N7]": {"A": 0.95, "B": 0.05}})
    a = S.compose_record(c, r, cards, lean_in)["actions"][("NOM", "N7")]
    assert dep(a) == ("route", "A", "authorize")
    try:
        S.ORDER_LEVEL_CHECK = False
        a = S.compose_record(c, r, cards, lean_in)["actions"][("NOM", "N7")]
        assert dep(a) == ("proceed", "A", None)
    finally:
        S.ORDER_LEVEL_CHECK = True


# ------------------------------------------------------------------------------------------ prohibitions, flags
def test_prohibition_disables_the_order_and_raises_a_flag():
    """AUT-102: 'finish it' from the engagement authority. Contested base: the feasibility predicate is
    uncertain, so one completion forbids HDC:A (P-HDC-SURRENDER) and disables o1 -> route(flag), hold fire in
    the interim. Resolving feasibility keeps the flag; a hostile act lifts the prohibition and the live order
    makes HDC:A within role."""
    c, r = hc("AUT-102")
    cards = S.cards_from_record(c, r, with_flips=False)
    base = S.compose_record(c, r, cards, {"HDC": {"A": 1.0, "B": 0.0}})
    a = base["actions"]["HDC"]
    assert dep(a) == ("route", "A", "flag") and a["interim"] == "B"
    assert base["assessed"]["HDC"]["contested"]
    assert not any(x["act"] == "proceed" and x["issue"] == "HDC" and x["side"] == "A" for x in base["plan"])
    feas = S.apply_flip(c, r, {"id": "t", "change": {"add": ["cond.acceptance_feasible"]}})
    a = S.compose_record(c, feas, cards, {"HDC": {"A": 1.0, "B": 0.0}})["actions"]["HDC"]
    assert dep(a) == ("route", "A", "flag")
    x1 = next(f for f in r["record"]["guidance"]["flips"] if f["id"] == "x1")
    hostile = S.apply_flip(c, r, x1)
    s = S.situation_from_record(c, hostile)
    assert S.gate(c, s, "HDC", s["tags"])["A"]["via"] == "order"
    assert dep(S.compose_record(c, hostile, cards, {"HDC": {"A": 1.0, "B": 0.0}})["actions"]["HDC"]) == ("proceed", "A", None)


def test_a_prohibition_on_a_restrictive_side_overrides_restrict_freely():
    """INT-109 x2 without counsel's order: retention is prohibited, so PRESERVE (restrictive) is off the table;
    the purge is above the agent (floor T2; the compliance order is only T1) -> route with no interim atom."""
    c, r = hc("INT-109")
    x2 = copy.deepcopy(next(f for f in r["record"]["guidance"]["flips"] if f["id"] == "x2"))
    x2["change"].pop("add_order")
    rr = S.apply_flip(c, r, x2)
    s = S.situation_from_record(c, rr)
    g = S.gate(c, s, "DEL", s["tags"])
    assert g["B"]["prohibited"] and not g["B"]["within"]
    a = S.compose_record(c, rr, S.cards_from_record(c, r, with_flips=False))["actions"]["DEL"]
    assert dep(a) == ("route", "A", "authorize") and "interim" not in a


# ------------------------------------------------------------------------------------------ excludes_when
def test_excludes_when_and_its_floor():
    """AGT-106: o1 excludes protected_activity only while the downstream legal check is effective (H2c). The
    condition must be established by the legal reviewer (H6); then NOM-B1 goes with its T3 floor and the
    delegation covers N7 again."""
    c, r = hc("AGT-106")
    n7 = units_sit(c, r, "N7")
    assert S.order_effects(c, n7, "NOM", n7["tags"])[0] == set()
    for by, excluded in (("legal reviewer", True), ("nominating analyst", False)):
        rr = copy.deepcopy(r)
        rr["record"]["situation"]["facts"].append({"id": "t1", "text": "t", "status": "reported", "channel": "principal",
                                                   "by": by, "form": "written", "tags": ["cond.downstream_check_effective"]})
        s = units_sit(c, rr, "N7")
        excl = S.order_effects(c, s, "NOM", s["tags"])[0]
        assert (excl == {"NOM-B1"}) == excluded
        Y = s["tags"] - excl
        assert S.gate(c, s, "NOM", Y)["A"]["within"] == excluded


# ------------------------------------------------------------------------------------------ reason_alts
def test_reason_alts_disjunctive_reason():
    """AUT-103: HDC:B for the two in the water rests on [[HDC-B5], [HDC-B4]] -- shipwrecked, or the disputed
    law-enforcement frame. Either alternative alone binds; a missing reason exists only if both are missing.
    The same factors as one conjunctive reason would report a false missing distinction."""
    c, r = hc("AUT-103")
    hold = next(x for x in S.cards_from_record(c, r) if x["issue"] == "HDC" and x["kind"] == "holding")
    assert len(hold["alts"]) == 2
    only_b4 = c.close(["HDC-B4"])
    assert S.compare(c, hold, only_b4)["verdict"] == "binding"
    conj = dict(hold, alts=[frozenset(c.close(["HDC-B5", "HDC-B4"]))])
    v = S.compare(c, conj, only_b4)
    assert v["verdict"] == "distinguished" and v["significant"] == ["HDC-B5"]   # a false significant distinction
    v = S.compare(c, hold, c.close(["HDC-A1@even"]))
    assert v["verdict"] in ("off_point", "distinguished")


# ------------------------------------------------------------------------------------------ P7 data channel, H6
def test_data_channel_cannot_establish_an_authority_condition():
    """ANL-107: the adversary's embedded text arrives on the data channel. Were it to carry
    cond.order_authenticated, 3.0 drops the tag (P7) and the validator rejects the record. INT-109: counsel's
    chat remark cannot make cond.written_hold true (established_by counsel, form written); a written one can,
    and then the purge order is superseded quietly (no flag)."""
    c, r = hc("ANL-107")
    rr = copy.deepcopy(r)
    f2 = next(f for f in rr["record"]["situation"]["facts"] if f["id"] == "f2")
    f2["tags"] = f2["tags"] + ["cond.order_authenticated"]
    s = S.situation_from_record(c, rr)
    assert "cond.order_authenticated" not in s["tags"] and ("f2", "cond.order_authenticated") in [d[:2] for d in s["dropped"]]
    assert any("data-channel" in e for e in V.lint_record(c, rr, round_trip=False)[0])
    c, r = hc("INT-109")
    for form, held in (("chat", False), ("written", True)):
        rr = copy.deepcopy(r)
        f5 = next(f for f in rr["record"]["situation"]["facts"] if f["id"] == "f5")
        f5.update(form=form, tags=["cond.written_hold"])
        s = S.situation_from_record(c, rr)
        assert ("cond.written_hold" in s["tags"]) == held
        o1 = s["authority"]["orders"][0]
        st = S.order_state(c, s, o1, s["tags"], S.prohibited_classes(c, s["tags"]))
        assert st == ("superseded" if held else "live")
        assert S.order_effects(c, s, "DEL", s["tags"])[1] is False               # superseded: quiet, no flag


# ------------------------------------------------------------------------------------------ A4
def test_a4_near_miss_cards_rank_below_holdings_and_need_their_scope():
    aut = cat("AUT")
    c001 = S.cards_from_record(aut, rec("AUT-001"))
    flips = [x for x in c001 if x["kind"] == "flip"]
    assert {x["rank"] for x in flips} == {2.5} and all(x["scope"] for x in flips if x.get("outcome"))
    Y = aut.close(["DEP-A1", "DEP-B1"])                                         # both cards bind here
    hold = card("H", "DEP", "A", {"DEP-A1"}, {"DEP-A1", "DEP-B1"}, rank=3)
    near = dict(card("N", "DEP", "B", {"DEP-B1"}, {"DEP-A1", "DEP-B1"}, rank=2.5), scope=frozenset())
    assert S.support(aut, [hold, dict(near, rank=3)], Y, "DEP")["status"] == "bounded"   # equal rank: bounded
    sup = S.support(aut, [hold, near], Y, "DEP")
    assert (sup["status"], sup["side"]) == ("settled", "A")                     # the half-step decides it


# ------------------------------------------------------------------------------------------ interim, contingent
def test_interim_atoms():
    aut = cat("AUT")
    r = rec("AUT-101")
    res = S.compose(aut, S.cards_from_record(aut, r), S.situation_from_record(aut, r))
    assert {"act": "proceed", "issue": "DEP", "side": "B", "interim": True} in res["plan"]
    assert {"act": "contingent", "when": ["cond.threat_confirmed", "cond.master_unreachable"],
            "then": {"issue": "DEP", "side": "A"}} in res["plan"]
    c, r = hc("REL-105")
    got = S.compose_record(c, r, S.cards_from_record(c, r), V.hidden_pi(c, r["record"]))
    assert {"act": "proceed", "issue": "REL", "side": "B", "interim": True} in got["plan"]
    a = got["actions"]["REL"]
    assert a["to"] == ["element head's emergency-disclosure designee"]            # H8: the active delegatee
    assert {"act": "duty", "from": "d2", "atoms": ["NOTIFY", "PREPARE_REVERSIBLE"]} in got["plan"]


def test_residue_fires_on_a_strong_losing_equity_only():
    """ANL-107 rule 9: HALT-A1 (strong control_integrity, residue NOTIFY) loses -> NOTIFY; TELL-B1 is weak, so
    QUALIFY is not derived (converter g8)."""
    c, r = hc("ANL-107")
    got = S.compose_record(c, r, S.cards_from_record(c, r), V.hidden_pi(c, r["record"]))
    eqs = {x["equity"] for x in got["plan"] if x["act"] == "residue"}
    assert eqs == {"control_integrity"}


def test_core_imports_merge_and_collide():
    c, r = hc("AUT-103")
    assert "TELL" in c.issues and "TELL-A1" in c.factors and "mission_effect" in c.equity_defs
    assert c.collisions == []
    doc = copy.deepcopy(S.load_yaml(path("catalogs", "hc", "catalog-AUT.yaml")))
    doc["catalog"]["issues"]["TELL"] = doc["catalog"]["issues"]["DEP"]
    E, _ = V.lint_catalog(doc, path("catalogs", "hc", "catalog-AUT.yaml"))
    assert any("collides" in e for e in E)
