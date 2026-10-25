"""(f) Permutation invariance (spec 6): consistently relabelling side letters per issue and factor IDs,
and shuffling fact and card order, leaves every composed action unchanged (mapped back), and leaves the
reward of the oracle mapping unchanged (the isomorphic-perturbation gap is exactly 0)."""
import copy
import pytest
import solver_v3 as S
import reward_v2 as RW
import permute_v7 as PV
from conftest import path, rec, vep_record, VEP_STUDY

DOHA = [f"DOHA-F-{i:02d}" for i in range(1, 11)]
DOHA_STUDY = {"deciders": [{"holder": "DOHA administrative judge", "holds": ["GRANT_ELIGIBILITY", "DENY_ELIGIBILITY"]}],
              "delegations": [{"to": "agent", "holds": ["GRANT_ELIGIBILITY", "DENY_ELIGIBILITY"], "when": []}]}


def scenarios():
    """(catalog file, flags, situation record, served records, extra tag changes, pi, authority override)"""
    yield "AUT", (), rec("AUT-101"), [rec("AUT-101")], [], None, None
    yield "AUT", (), rec("AUT-101"), [rec("AUT-101")], ["+cond.threat_confirmed", "+cond.master_unreachable"], None, None
    yield "AUT", (), rec("AUT-101"), [rec("AUT-101"), rec("AUT-001")], [], None, None
    yield "AUT", (), rec("AUT-001"), [rec("AUT-001")], ["-DEP-A3", "+DEP-B2@likely"], None, None
    for tags, pi in [({"D1", "D2@high", "D3", "D4", "R1", "R2", "R3"}, {"DISC": {"A": 0.9, "B": 0.1}}),
                     ({"D1", "D2@high", "D3", "D4", "R1", "R2", "R3"}, {"DISC": {"A": 0.3, "B": 0.7}}),
                     ({"D1", "D2@high", "D3", "R1", "R3"}, None), ({"D1", "D2@moderate", "R1", "R6", "R3"}, None)]:
        yield "VEP", (), vep_record(tags), [rec("VEP-001"), rec("VEP-004")], [], pi, None
    for h in DOHA:
        yield "SEC-F", (), rec(h), [rec(i) for i in DOHA if i != h], [], None, DOHA_STUDY
    yield "FISC", (), rec("FISC-02"), [rec("FISC-01"), rec("FISC-02"), rec("FISC-03")], [], None, None


def run(cat_doc, flags, situation_rec, served, changes, pi, auth):
    c = S.Catalog(cat_doc, flags)
    cards = [cd for r in served for cd in S.cards_from_record(c, r)]
    out = {}
    r = situation_rec["record"]
    for u in [x["id"] for x in r.get("units") or []] or [None]:
        s = S.situation_from_record(c, r, u)
        if auth:
            s["authority"] = auth
        s["tags"] = S.apply_change(c, s["tags"], changes)
        for I, a in S.compose(c, cards, s, pi)["actions"].items():
            out[(I, u)] = a
    return out, c, cards


def key(a):
    return (a["act"], a.get("side"), a.get("to"), a.get("because"), a.get("recommend"))


@pytest.mark.parametrize("seed", range(6))
def test_f_permutation_invariance(seed):
    n = 0
    for name, flags, srec, served, changes, pi, auth in scenarios():
        cat_doc = S.load_yaml(path("catalogs", f"{name}.yaml"))
        base, c0, _ = run(cat_doc, flags, srec, served, changes, pi, auth)
        P = PV.make_perm(cat_doc, seed)
        pc = PV.catalog(P, cat_doc)
        pch = [ch[0] + PV.tag(P, ch[1:]) for ch in changes]
        perm, c1, _ = run(pc, flags, PV.record(P, srec), [PV.record(P, r) for r in served], pch, PV.pi(P, pi), auth)
        assert set(perm) == set(base), name
        for k in base:
            assert key(PV.unpermute_action(P, perm[k])) == key(base[k]), (name, seed, k, base[k], perm[k])
            n += 1
    assert n >= 20


@pytest.mark.parametrize("seed", range(3))
def test_f_reward_gap_is_zero(seed):
    doc = S.load_yaml(path("catalogs", "VEP.yaml"))
    P = PV.make_perm(doc, seed)
    for tags, pi in [({"D1", "D2@high", "D3", "D4", "R1", "R2", "R3"}, {"DISC": {"A": 0.7, "B": 0.3}}),
                     ({"D1", "D2@high", "D3", "R1", "R3"}, None)]:
        totals = []
        for d, recs, p, hid in [(doc, [rec("VEP-001"), rec("VEP-004")], pi, {"DISC": "A"}),
                                (PV.catalog(P, doc), [PV.record(P, rec("VEP-001")), PV.record(P, rec("VEP-004"))],
                                 PV.pi(P, pi), {"DISC": PV.side(P, "DISC", "A")})]:
            c = S.Catalog(d)
            srec = vep_record({PV.tag(P, t) for t in tags} if d is not doc else tags, cvep=c)
            item = RW.item_from_record(c, srec, served_records=recs, hidden=hid)
            totals.append(RW.reward(item, RW.oracle_mapping(item, p))[0])
        assert abs(totals[0] - totals[1]) < 1e-12
