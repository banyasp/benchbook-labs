"""Validator, JSON Schema and lints: every shipped catalog and record passes; each lint fires on a
seeded defect; the DOHA casebook is Horty-consistent; the pilot's '+B19a' flip is caught by the naqd lint."""
import copy, glob
import pytest
import solver_v3 as S
import validate_v7 as V
from conftest import path, cat, rec

FILES = sorted(glob.glob(path("catalogs", "*.yaml"))) + sorted(glob.glob(path("records", "*.yaml")))


def test_all_files_validate(capsys):
    assert V.main(FILES) == 0


@pytest.mark.parametrize("f", FILES, ids=lambda p: p.split("/")[-1])
def test_schema(f):
    assert V.schema_errors(S.load_yaml(f)) == []


def aut_doc():
    return copy.deepcopy(S.load_yaml(path("catalogs", "AUT.yaml")))


def test_catalog_lints_fire():
    d = aut_doc()
    d["catalog"]["factors"]["DEP-A1"]["equities"] = {"nonexistent": "strong"}
    d["catalog"]["factors"]["DEP-A2"]["rungs"] = {"likely": "strong", "even": "weak"}
    d["catalog"]["authority"]["non_delegable_to_agent"] = ["HOLD_AT_PIER"]
    d["catalog"]["authority"]["tier_floors"] = {"cond.threat_confirmed": "T3"}
    E, _ = V.lint_catalog(d)
    text = " | ".join(E)
    for needle in ("unknown equity", "dimension's order", "restrictive classes", "tier_floors"):
        assert needle in text, needle


def test_record_lints_fire():
    aut = cat("AUT")
    r = copy.deepcopy(rec("AUT-001"))
    rr = r["record"]
    rr["resolution"]["holdings"][0]["reason"] = ["DEP-A1", "DEP-A2@almost_certain", "cond.threat_confirmed"]
    rr["situation"]["facts"][0]["tags"] = ["DEP-A2@likely"]                       # not closed downward
    rr["situation"]["facts"].append({"id": "g9", "text": "t", "status": "found", "tags": []})
    E, _ = V.lint_record(aut, r)
    text = " | ".join(E)
    for needle in ("conditions never appear", "not present at or above its rung", "not closed", "`found`"):
        assert needle in text, needle
    bad = copy.deepcopy(rec("AUT-101"))
    bad["record"]["situation"]["facts"][3].pop("confidence")                    # assessed needs confidence
    assert V.schema_errors(bad)


def test_gold_plan_round_trip_is_checked():
    r = copy.deepcopy(rec("AUT-101"))
    r["record"]["resolution"]["plan"][1]["recommend"] = "A"
    E, _ = V.lint_record(cat("AUT"), r)
    assert any("gold plan not reproduced" in e for e in E)


def test_doha_casebook_is_horty_consistent():
    for flags in ((), ("doctrine",)):
        c = cat("SEC-F", flags)
        cards = [cd for i in range(1, 11) for cd in S.cards_from_record(c, rec(f"DOHA-F-{i:02d}"), with_flips=False)]
        assert S.lint_horty(c, cards) == []


def test_naqd_lint_catches_the_pilot_no_op_flip():
    c = cat("SEC-F")
    r = copy.deepcopy(rec("DOHA-F-05"))
    r["record"]["guidance"]["flips"] = [{"id": "x1", "event": "world", "change": ["+B19a"],
                                         "then": {"issue": "ELIG", "outcome": "B", "force": "required"}}]
    bad = S.lint_horty(c, S.cards_from_record(c, r))
    assert [(b["p"][0], b["q"][0]) for b in bad] == [("DOHA-F-05", "DOHA-F-05/x1")]
    E, W = V.lint_record(c, r)
    assert any("no-op" in w for w in W) and any("naqd" in w for w in W)
