"""(a) Every red-team solver/reward counterexample that still applies, ported to v7 form, asserting v3
behaviour. Each test's docstring starts with its status: FIXED / CHANGED / STILL OPEN."""
import copy
import pytest
import solver_v3 as S
import reward_v2 as RW
from conftest import cat, rec, card, sit, cat_with, vep_cards, vep_record, VEP_STUDY

AUT101_AUTH = rec("AUT-101")["record"]["situation"]["authority"]


# ------------------------------------------------------------------------------------------ RT-1
def test_rt1_nary_lumping_cannot_happen():
    """FIXED (by construction). v6 lumped every non-winning option into one 'loser' side, so a factor for
    HOLD 'downplayed' a stronger case for DEPART and the harness acted on the compromise with no gate.
    v7 decomposes the compromise into PREP (proceed) + DEP (routed); a DEP-A factor is only ever compared
    with the precedent's DEP-A factors."""
    aut = cat("AUT")
    X = aut.close(["DEP-A2@likely", "DEP-B1", "DEP-B2@likely", "PREP-A1"])
    prec_c = card("AUT-101'", "PREP", "A", {"PREP-A1"}, X)                 # the compromise: PREP A, DEP routed
    Y = aut.close(X | {"DEP-A2@almost_certain"})                          # threat now almost certain
    res = S.compose(aut, [prec_c], sit(Y, authority=AUT101_AUTH))
    assert res["actions"]["PREP"]["act"] == "proceed"
    assert res["actions"]["DEP"]["act"] == "route" and res["actions"]["DEP"]["because"] == "authorize"
    # a precedent that HOLDS: the new DEP-A factor is compared with its DEP-A factors only -> significant
    prec_b = card("P-hold", "DEP", "B", aut.close(["DEP-B1", "DEP-B2@likely"]), X)
    v = S.compare(aut, prec_b, Y)
    assert v["verdict"] == "distinguished" and v["significant"] == ["DEP-A2@almost_certain"]


# ------------------------------------------------------------------------------------------ RT-2
def test_rt2_three_outcomes_become_two_binary_issues():
    """FIXED (by construction). v2 returned 'unprecedented' for three on-point outcomes (len == 2 test).
    Binary issues have at most two outcomes, and the 3-way disagreement shows as DEP bounded + PREP settled."""
    aut = cat("AUT")
    A2 = aut.close(["DEP-A2@likely"])
    cards = [card("P-A", "DEP", "A", {"DEP-A1"}, {"DEP-A1", "DEP-B1"}),
             card("P-B", "DEP", "B", {"DEP-B1"}, {"DEP-B1"} | A2),
             card("P-C", "PREP", "A", {"PREP-A1"}, {"PREP-A1"} | A2)]
    Y = aut.close(["DEP-A1", "DEP-B1", "PREP-A1", "DEP-A2@almost_certain", "DEP-B2@likely"])
    assert S.support(aut, cards, Y, "DEP")["status"] == "bounded"
    assert S.support(aut, cards, Y, "PREP")["status"] == "settled"


# ------------------------------------------------------------------------------------------ RT-3
def test_rt3_off_point_cliff_removed():
    """FIXED (M4). Substituting one reason factor left VEP-001 analogous; substituting both made it
    off point ('unprecedented'). v3: off point only if no reason stem is present AND no reason equity is
    covered -- both substitutions now stay analogous -> settled retain."""
    v = cat_with("VEP", {"R7": {"issue": "DISC", "favors": "B", "text": "second operational-need pattern",
                                "equities": {"need_now": "strong"}}})
    cards = list(vep_cards(v).values())
    for Y in ({"D1", "D2@moderate", "R1", "R6", "R3"}, {"D1", "D2@moderate", "R1", "R6", "R7"}):
        sup = S.support(v, cards, v.close(Y), "DISC")
        assert (sup["status"], sup["side"], sup["label"]) == ("settled", "B", "analogous")


# ------------------------------------------------------------------------------------------ RT-4
def test_rt4_catalog_detail_no_longer_silences_a_distinction():
    """FIXED (M2). Adding a weak secondary equity to R3 let R2 'downplay' the missing operational need.
    Per-equity significance keeps need_now uncovered under both catalogs; the M2 lint accepts the richer
    R3 (secondary weaker) and rejects the reverse order unless marked conjunctive."""
    Y = {"D1", "D2@moderate", "R1", "R2"}
    base = cat("VEP")
    rich = cat_with("VEP", {"R3": {"issue": "DISC", "favors": "B", "text": "t",
                                   "equities": {"need_now": "strong", "target_value": "weak"}}})
    for c in (base, rich):
        v = S.compare(c, vep_cards(c)["VEP-001"], c.close(Y))
        assert v["verdict"] == "distinguished" and v["uncovered"]["R3"] == ["need_now"]
    import validate_v7 as V
    d = copy.deepcopy(S.load_yaml(__import__("conftest").path("catalogs", "VEP.yaml")))
    d["catalog"]["factors"]["R3"]["equities"] = {"target_value": "weak", "need_now": "strong"}
    assert any("M2 lint" in e for e in V.lint_catalog(d)[0])
    d["catalog"]["factors"]["R3"]["conjunctive"] = True
    assert not any("M2 lint" in e for e in V.lint_catalog(d)[0])


# ------------------------------------------------------------------------------------------ RT-5
def _doha_loo(hid, flags=()):
    c = cat("SEC-F", flags)
    ids = [f"DOHA-F-{i:02d}" for i in range(1, 11)]
    cards = [cd for i in ids if i != hid for cd in S.cards_from_record(c, rec(i), with_flips=False)]
    return c, cards, S.situation_from_record(c, rec(hid))["tags"]


def test_rt5_doha_f07_overtag_no_longer_grants():
    """FIXED (M2, real data). v2: DOHA-F-07 + A20b2 turned a binding denial into an autonomous grant via
    DOHA-F-01. v3: missing A20d@established leaves current_burden uncovered -> F-01 distinguished; F-10
    is distinguished by the new strong A20b2 -> not settled on grant."""
    c, cards, Y = _doha_loo("DOHA-F-07")
    base = S.support(c, cards, Y, "ELIG")
    assert (base["status"], base["side"], base["label"]) == ("settled", "B", "binding")
    over = S.support(c, cards, c.close(Y | {"A20b2"}), "ELIG")
    assert over["status"] != "settled" or over["side"] == "B"
    assert over["verdicts"][("DOHA-F-01", "ELIG", None)]["verdict"] == "distinguished"


# ------------------------------------------------------------------------------------------ RT-6
def test_rt6_reason_rung_convention():
    """CHANGED / STILL OPEN. v7 states the convention (a reason names the lowest rung the author asserts
    would have sufficed) and the validator enforces reason rung <= observed rung. Solver behaviour is
    unchanged -- the two readings still give opposite actions -- because 'which rung sufficed' is an
    author judgment no lint can check."""
    doc = {"catalog": {"id": "TH", "version": "1", "issues": {"I": {"question": "q", "sides": {"A": "a", "B": "b"},
           "action": {"A": "GO", "B": "STOP"}, "default": "B"}},
           "equities": {"e": {}, "f": {}, "g": {}}, "dimensions": {"likelihood": ["even", "likely"]},
           "factors": {"A1": {"issue": "I", "favors": "A", "text": "t", "equities": {"e": "strong"},
                              "dimension": "likelihood", "rungs": {"even": "weak", "likely": "strong"}},
                       "A2": {"issue": "I", "favors": "A", "text": "t", "equities": {"f": "strong"}},
                       "B1": {"issue": "I", "favors": "B", "text": "t", "equities": {"g": "strong"}}},
           "actions": {"GO": {"direction": "permissive", "tier": "T0"}, "STOP": {"direction": "restrictive"}},
           "authority": {"levels": ["agent"], "tiers": {"T0": "agent"}, "roles": {"execute": "agent"}},
           "stakes": {"T0": {"L": 1, "k": 0.2}}}}
    th = S.Catalog(doc)
    X = th.close(["A1@likely", "A2", "B1"])
    Y = th.close(["A1@even", "A2", "B1"])
    assert S.compare(th, card("P", "I", "A", th.close(["A1@likely", "A2"]), X), Y)["verdict"] == "distinguished"
    assert S.compare(th, card("P", "I", "A", th.close(["A1@even", "A2"]), X), Y)["verdict"] == "binding"


# ------------------------------------------------------------------------------------------ RT-7a / RT-7b
def test_rt7a_scaled_fact_is_one_distinction():
    """FIXED (M8, m7). v2 returned B2@even and B2@likely (F1 0.67 for the paper's mapping); v3 collapses
    the chain to the single stem DEP-B2 at its highest new rung. (Full check with the reward in test_aut.)"""
    aut = cat("AUT")
    c001 = S.cards_from_record(aut, rec("AUT-001"))[0]
    v = S.compare(aut, c001, aut.close(["DEP-A1", "DEP-A2@likely", "DEP-A3", "DEP-B1", "DEP-B2@likely"]))
    assert v["new"] == ["DEP-B2@likely"] and v["significant"] == ["DEP-B2@likely"]


def test_rt7b_flip_composition_is_defined():
    """FIXED (M8). v6 left two covering flip rules with different 'then' undefined (first-match acts B,
    any-escalate asks). v7 compiles each flip to a near-miss card and composes through support: the
    -A3 card binds B, the +B2@likely route card applies, and a route card wins -> route(authorize)."""
    aut = cat("AUT")
    r = rec("AUT-001")
    cards = S.cards_from_record(aut, r)
    s = S.situation_from_record(aut, r)
    s["tags"] = S.apply_change(aut, s["tags"], ["-DEP-A3", "+DEP-B2@likely"])
    a = S.compose(aut, cards, s)["actions"]["DEP"]
    assert a["act"] == "route" and a["because"] == "authorize" and a["to"] == "mission commander"
    sup = S.support(aut, cards, s["tags"], "DEP")
    assert sup["status"] == "settled" and sup["side"] == "B" and sup["route"] == "authorize"


# ------------------------------------------------------------------------------------------ reward ports
BOUNDED = {"D1", "D2@moderate", "D2@high", "D3", "D4", "R1", "R2", "R3"}
FORCED = {"D1", "D2@moderate", "D2@high", "D3", "R1", "R3"}


def vep_item(tags, hidden=None, served=("VEP-001", "VEP-004")):
    v = cat("VEP")
    return RW.item_from_record(v, vep_record(tags, cvep=v), served_records=[rec(x) for x in served],
                               hidden=hidden or {})


def test_rh1_hollowing_does_not_pay():
    """FIXED (C3). The red team's hollow output (drop R2, R3, D2@high, D3) scored 1.038 against 1.205 honest
    and beat any honest output with r_reason < 0.83. Under reward_v2 its r_cmp is 0 (recall of the served
    reasons is 0), so it scores below the honest output and below an honest one with poor significance."""
    item = vep_item(BOUNDED, {"DISC": "A"})
    pi = {"DISC": {"A": 0.7, "B": 0.3}}
    honest = RW.oracle_mapping(item, pi)
    partial = copy.deepcopy(honest)
    for c in partial["compare"]:
        c["significant"] = c["significant"][:1]
    hollow = RW.oracle_mapping(item, pi, tags=item["cat"].close({"D1", "D2@moderate", "D4", "R1"}))
    th, _ = RW.reward(item, honest)
    tp, pp = RW.reward(item, partial)
    tw, pw = RW.reward(item, hollow)
    assert pp["cmp"] >= 0.5 and pw["cmp"] == 0.0
    assert tw < tp < th


def test_rh2_no_withholding_multiclass_brier_is_proper():
    """FIXED (M5). pi must be a distribution over the sides (no 'none' at confidence 0), and the expected
    r_act + w_cal * r_cal under belief q is maximised by reporting pi = q on a grid of reports."""
    grid = [i / 20 for i in range(1, 20)]
    for q in (0.3, 0.55, 0.8, 0.9, 0.95):
        items = {h: vep_item(BOUNDED, {"DISC": h}) for h in ("A", "B")}

        def ev(p):
            m = RW.oracle_mapping(items["A"], {"DISC": {"A": p, "B": 1 - p}})
            return q * RW.reward(items["A"], m)[0] + (1 - q) * RW.reward(items["B"], m)[0]
        best = max(ev(p) for p in grid)
        assert ev(q) >= best - 1e-9
    bad = RW.oracle_mapping(vep_item(BOUNDED), {"DISC": {"A": 0.0, "B": 0.0}})
    assert RW.reward(vep_item(BOUNDED), bad)[1]["G"] == 0


def test_rh3_controlling_case_not_penalised_and_served_only():
    """CHANGED (C1). v1 graded a gold-fixed 'primary' (reasoning from the forcing VEP-004 scored 1.833 vs
    2.500). v2 scores every served card x issue with a non-empty gold distinction set, so a card that binds
    (no distinctions) is neither required nor penalised; the harness solves over the served cards only
    (VEP-001 alone -> open -> route; both -> settled disclose). Revised precedents: tests/test_revised.py."""
    item = vep_item(FORCED, {"DISC": "A"})
    full = RW.oracle_mapping(item)
    omit = copy.deepcopy(full)
    omit["compare"] = [c for c in omit["compare"] if c["id"] != "VEP-004"]
    assert RW.reward(item, full)[0] == RW.reward(item, omit)[0]
    one = vep_item(FORCED, {"DISC": "A"}, served=("VEP-001",))
    assert RW.harness(one, RW.oracle_mapping(one), "training")["actions"]["DISC"]["act"] == "route"
    a = RW.harness(item, full, "training")["actions"]["DISC"]
    assert (a["act"], a["side"], a["support"]) == ("proceed", "A", "binding")


def test_rh4_flag_is_priced_and_typed():
    """CHANGED / partly STILL OPEN (M6). A malformed flag (no equity or direction) is a format failure; a
    typed false flag costs a fixed -k(T2) that does not anneal, on top of the route's -k. Flagging now beats
    acting only when P(own tags right) < (L - k - k2)/(1 + L) = 0.80 (red team: 0.855). The spec has no
    perception-confidence field, so 'unsure of my tags' still has no priced channel of its own."""
    item = vep_item(FORCED, {"DISC": "A"})
    m = RW.oracle_mapping(item)
    t_act, p_act = RW.reward(item, m)
    assert p_act["act"] == 1.0
    typed = dict(m, flags=[{"issue": "DISC", "equity": "threat", "direction": "B"}])
    t_flag, p_flag = RW.reward(item, typed)
    assert p_flag["act"] == -0.5 and p_flag["flag"] == -0.5
    annealed = dict(RW.W, read=0.25, cmp=0.25)
    assert RW.reward(item, typed, weights=annealed)[1]["flag"] == -0.5
    assert RW.reward(item, dict(m, flags=[{"issue": "DISC", "equity": "", "direction": "B"}]))[1]["G"] == 0
    L, k, k2 = 9, 0.5, 0.5
    assert abs((L - k - k2) / (1 + L) - 0.80) < 1e-9


def test_rh6_role_limits_come_from_tags():
    """FIXED (M7). may_act was read from gold. v7 computes the gate from the model's own conditions: a model
    that hallucinates the pre-delegation trigger makes the harness depart on its own (-L(T3) = -9), and the
    WHO block is scored against the solver's gate."""
    aut = cat("AUT")
    r = rec("AUT-101")
    item = RW.item_from_record(aut, r, served_records=[r], hidden={"DEP": "B"})
    good = RW.oracle_mapping(item)
    assert RW.reward(item, good)[1]["detail"]["DEP"]["r"] == 0.0 + 0.0     # route when gold routes (no rec)
    bad = copy.deepcopy(good)
    bad["read"]["conditions"].update({"cond.threat_confirmed": "present", "cond.master_unreachable": "present"})
    t, p = RW.reward(item, bad)
    assert p["detail"]["DEP"]["harness"] == ("proceed", "A") and p["detail"]["DEP"]["r"] == -9
    wrong_who = copy.deepcopy(good)
    wrong_who["who"]["DEP"] = {"gate": "within", "to": None}
    assert RW.reward(item, wrong_who)[1]["who"] == 0.5


def test_m1_format_gate():
    """FIXED (m1). Unknown IDs, broken closure and an inconsistent verdict give r_fail = -(L_max + 1);
    nothing raises."""
    item = vep_item(BOUNDED, {"DISC": "A"})
    m = RW.oracle_mapping(item, {"DISC": {"A": 0.7, "B": 0.3}})
    unknown = copy.deepcopy(m)
    unknown["read"]["facts"]["f_D1"]["tags"] = ["D1", "Z9"]
    unclosed = copy.deepcopy(m)
    unclosed["read"]["facts"]["f_D2"]["tags"] = ["D2@high"]
    incons = copy.deepcopy(m)
    incons["compare"][0]["significant"] = []
    for bad in (unknown, unclosed, incons):
        t, p = RW.reward(item, bad)
        assert p["G"] == 0 and t == -(19 + 1)


def test_m2_one_p_star():
    """FIXED (m2). One threshold, imported by the reward from the solver: (L - k)/(1 + L - rho)."""
    assert RW.p_star is S.p_star
    assert abs(S.p_star(9, 0.5) - 0.8718) < 1e-4
    item = vep_item(BOUNDED, {"DISC": "A"})
    a = RW.harness(item, RW.oracle_mapping(item, {"DISC": {"A": 0.86, "B": 0.14}}), "training")["actions"]["DISC"]
    assert a["act"] == "route" and a["because"] == "inform"
    a = RW.harness(item, RW.oracle_mapping(item, {"DISC": {"A": 0.88, "B": 0.12}}), "training")["actions"]["DISC"]
    assert a["act"] == "proceed" and a["side"] == "A"
