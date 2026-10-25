"""(g) Revised precedent (red-team C1 / RH-3). VEP-004's pre-revision card required allied exposure (D4 in
its reason); the revision drops it. On the forced-by-VEP-004 situation (no D4):
  served revised card          -> the harness acts on it (disclose);
  mapping restates the stale card (A4-style) -> evaluation acts on the stale restatement (route, -k);
                                  training scores G = 0 (r_fail);
  recall arms (nothing served) act on whatever they restate.
Plus the decoy control: swapping the served card changes the harness action on a binding item."""
import copy
import solver_v3 as S
import reward_v2 as RW
from conftest import cat, rec, vep_record

FORCED = {"D1", "D2@high", "D3", "R1", "R3"}


def cards():
    v = cat("VEP")
    revised = S.cards_from_record(v, rec("VEP-004"))[0]
    stale = dict(revised, reason=frozenset(v.close(["D2@high", "D3", "D4"])), X=revised["X"] | {"D4"})
    c001 = S.cards_from_record(v, rec("VEP-001"))[0]
    return v, revised, stale, c001


def item(served, in_force=None):
    v = cat("VEP")
    it = RW.item_from_record(v, vep_record(FORCED, cvep=v), served_cards=served, hidden={"DISC": "A"})
    if in_force is not None:
        it["in_force"] = in_force
    return it


def restate(m, card):
    m = copy.deepcopy(m)
    m["cite"] = [c for c in m["cite"] if c["id"] != card["id"]] + [
        {"id": card["id"], "issue": card["issue"], "unit": None, "outcome": card["outcome"],
         "reason": sorted(card["reason"]), "X": sorted(card["X"])}]
    return m


def test_g_served_revised_card_is_acted_on():
    v, revised, stale, c001 = cards()
    it = item([c001, revised])
    a = RW.harness(it, RW.oracle_mapping(it), "evaluation")["actions"]["DISC"]
    assert (a["act"], a["side"]) == ("proceed", "A")
    st = item([c001, stale])
    a = RW.harness(st, RW.oracle_mapping(st), "evaluation")["actions"]["DISC"]
    assert a["act"] == "route"


def test_g_stale_restatement_evaluation_vs_training():
    v, revised, stale, c001 = cards()
    it = item([c001, revised])
    fresh = RW.oracle_mapping(it)                       # A2: restates what it was served
    stale_m = restate(fresh, stale)                     # A4-style: restates the pre-revision card
    t, p = RW.reward(it, fresh, "evaluation")
    assert p["act"] == 1.0
    t, p = RW.reward(it, stale_m, "evaluation")
    assert p["detail"]["DISC"]["harness"][0] == "route" and p["act"] == -0.5      # red team's spec value
    t, p = RW.reward(it, stale_m, "training")
    assert p["G"] == 0 and t == -(19 + 1)
    assert RW.reward(it, fresh, "training")[1]["G"] == 1


def test_g_recall_arms_act_on_their_restatement():
    v, revised, stale, c001 = cards()
    it = item([], in_force=[c001, revised])             # A3/A4: nothing served; gold from the version in force
    base = RW.oracle_mapping(item([c001, revised]))
    a4 = restate(base, stale)
    a3 = restate(base, revised)
    assert RW.reward(it, a4, "evaluation")[1]["detail"]["DISC"]["harness"][0] == "route"
    assert RW.reward(it, a3, "evaluation")[1]["detail"]["DISC"]["harness"] == ("proceed", "A")
    assert RW.reward(it, a3, "evaluation")[1]["act"] == 1.0


def test_g_decoy_changes_the_action_on_a_binding_item():
    """Red-team C1 fix 5: the harness has a served-card input, so a decoy swap moves the action."""
    v, revised, stale, c001 = cards()
    real, decoy = item([revised]), item([c001])
    m_real, m_decoy = RW.oracle_mapping(real), RW.oracle_mapping(decoy)
    a = RW.harness(real, m_real, "training")["actions"]["DISC"]
    b = RW.harness(decoy, m_decoy, "training")["actions"]["DISC"]
    assert (a["act"], a.get("side")) == ("proceed", "A") and b["act"] == "route"
