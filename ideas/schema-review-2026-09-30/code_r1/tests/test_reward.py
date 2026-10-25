"""(e) Hollowing: a hollow mapping (drop the served precedents' reason factors so they fall off point and
every comparison is trivially 'right') scores strictly below every honest mapping with r_cmp >= 0.5,
at the starting and at the annealed weights, on three unsettled items. Plus reward bookkeeping checks."""
import copy, itertools, random
import pytest
import solver_v3 as S
import reward_v2 as RW
from conftest import cat, rec, vep_record, VEP_STUDY

DOHA = [f"DOHA-F-{i:02d}" for i in range(1, 11)]


def items():
    v = cat("VEP")
    yield "VEP bounded", RW.item_from_record(
        v, vep_record({"D1", "D2@high", "D3", "D4", "R1", "R2", "R3"}, cvep=v),
        served_records=[rec("VEP-001"), rec("VEP-004")], hidden={"DISC": "A"}), {"DISC": {"A": 0.7, "B": 0.3}}
    c = cat("SEC-F")
    served = [cd for i in DOHA if i != "DOHA-F-03" for cd in S.cards_from_record(c, rec(i), with_flips=False)]
    yield "DOHA-F-03 LOO", RW.item_from_record(c, rec("DOHA-F-03"), served_cards=served, hidden={"ELIG": "A"},
                                               authority=VEP_STUDY | {"delegations": [{"to": "agent",
                                               "holds": ["GRANT_ELIGIBILITY", "DENY_ELIGIBILITY"], "when": []}]}), \
        {"ELIG": {"A": 0.6, "B": 0.4}}
    a = cat("AUT")
    r = copy.deepcopy(rec("AUT-001"))
    r["record"]["situation"]["facts"][-1] = {"id": "g5", "text": "He is likely recoverable inside the window",
                                              "status": "assessed", "likelihood": "likely", "confidence": "moderate",
                                              "tags": ["DEP-B2@even", "DEP-B2@likely"]}
    yield "AUT-001 +B2@likely", RW.item_from_record(a, r, served_cards=S.cards_from_record(a, rec("AUT-001"),
                                                    with_flips=False), hidden={"DEP": "B"}), {"DEP": {"A": 0.4, "B": 0.6}}


def honest_variants(item, pi):
    """Honest tags; COMPARE degraded pair by pair (verdict kept or wrong; significant set full, halved or empty)."""
    base = RW.oracle_mapping(item, pi)
    opts = []
    for c in base["compare"]:
        sig = c["significant"]
        opts.append([(c["verdict"], sig), (c["verdict"], sig[: max(1, len(sig) // 2)]),
                     ("analogous" if c["verdict"] == "distinguished" else "distinguished",
                      [] if c["verdict"] == "distinguished" else ["X-bogus"])])
    combos = list(itertools.product(*opts))
    if len(combos) > 200:                                # seeded sample; the all-correct combo stays first
        combos = combos[:1] + random.Random(0).sample(combos[1:], 199)
    for combo in combos:
        m = copy.deepcopy(base)
        for c, (v, sig) in zip(m["compare"], combo):
            c["verdict"], c["significant"] = v, [s for s in sig if s != "X-bogus"] or (
                sorted(item["cat"].tag)[:1] if v == "distinguished" else [])
        yield m


def hollow_variants(item, pi):
    """Drop every served reason stem (and optionally one more stem); report the solver's own verdicts."""
    cat, gold = item["cat"], item["situation"]["tags"]
    stems = {cat.stem(t) for c in item["served"] if c.get("outcome") for t in c["reason"]}
    core = {t for t in gold if cat.is_cond(t) or cat.stem(t) not in stems}
    yield RW.oracle_mapping(item, pi, tags=core)
    for t in sorted(core):
        if not cat.is_cond(t):
            yield RW.oracle_mapping(item, pi, tags=cat.close(core - set(cat.ladder[cat.stem(t)])))


def acts(res):
    return {I: (a["act"], a.get("side"), a.get("to"), a.get("because"), a.get("recommend"))
            for I, a in res["actions"].items()}


@pytest.mark.parametrize("weights", [RW.W, dict(RW.W, read=0.25, cmp=0.25)])
def test_e_hollowing_never_pays(weights):
    for name, item, pi in items():
        honest = [RW.reward(item, m, weights=weights) for m in honest_variants(item, pi)]
        honest = [(t, p) for t, p in honest if p["G"] and p["cmp"] >= 0.5]
        assert honest, name
        act0 = acts(RW.harness(item, RW.oracle_mapping(item, pi), "training"))
        compared = 0
        for m in hollow_variants(item, pi):
            t, p = RW.reward(item, m, weights=weights)
            if acts(RW.harness(item, m, "training")) != act0:
                continue          # a hollow that changes the action is scored by r_act, not by this test
            compared += 1
            assert p["cmp"] == 0.0, name
            assert t < min(h for h, _ in honest), (name, t, min(h for h, _ in honest))
        assert compared, name


def test_vacuous_pairs_are_dropped_not_scored_one():
    v = cat("VEP")
    item = RW.item_from_record(v, vep_record({"D1", "D2@high", "D3", "R1", "R3"}, cvep=v),
                               served_records=[rec("VEP-004")], hidden={"DISC": "A"})
    assert RW.r_cmp(item, RW.oracle_mapping(item), "training") == 0.0     # binding: nothing to score


def test_r_act_table():
    v = cat("VEP")
    item = RW.item_from_record(v, vep_record({"D1", "D2@high", "D3", "D4", "R1", "R2", "R3"}, cvep=v),
                               served_records=[rec("VEP-001"), rec("VEP-004")], hidden={"DISC": "A"})
    r = lambda p: RW.r_act(item, RW.oracle_mapping(item, {"DISC": p}), "training")
    assert r({"A": 0.9, "B": 0.1}) == 1.0                  # acts, right
    assert r({"A": 0.1, "B": 0.9}) == -9.0                 # acts, wrong: -L(T2)
    assert r({"A": 0.6, "B": 0.4}) == -0.5 + 0.25          # routes, recommends the hidden side
    assert r({"A": 0.4, "B": 0.6}) == -0.5                 # routes, wrong recommendation
    contested = dict(item, contested={"DISC"})
    assert RW.r_act(contested, RW.oracle_mapping(item, {"DISC": {"A": 0.6, "B": 0.4}}), "training") == 0.0
    assert RW.r_cal(contested, RW.oracle_mapping(item, {"DISC": {"A": 0.5, "B": 0.5}})) == 0.0
