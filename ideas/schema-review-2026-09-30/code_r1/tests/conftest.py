"""Shared fixtures for the v7 prototype tests. Run from code/: ./run_tests.sh (or python3 -m pytest tests)."""
import copy, os, sys
import pytest

CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, CODE)
import solver_v3 as S  # noqa: E402


def path(*p):
    return os.path.join(CODE, *p)


def cat(name, flags=()):
    return S.load_catalog(path("catalogs", f"{name}.yaml"), flags)


def rec(rid):
    return S.load_yaml(path("records", f"{rid}.yaml"))


def cat_with(name, extra_factors=None, patch=None):
    """A catalog variant: add or replace factors (RT-3, RT-4) without touching the files."""
    d = copy.deepcopy(S.load_yaml(path("catalogs", f"{name}.yaml")))
    d["catalog"]["factors"].update(extra_factors or {})
    if patch:
        patch(d["catalog"])
    return S.Catalog(d)


def card(cid, issue, outcome, reason, X, force="required", rank=0, status="current"):
    return {"id": cid, "issue": issue, "unit": None, "outcome": outcome, "reason": frozenset(reason),
            "X": frozenset(X), "force": force, "status": status, "rank": rank, "requires": frozenset(),
            "forbids": frozenset(), "route": None, "kind": "holding"}


def sit(tags, role="execute", serves="principal", authority=None, uncertain=None):
    return {"tags": set(tags), "uncertain": dict(uncertain or {}), "agent": {"role": role, "serves": serves},
            "authority": authority or {"deciders": [], "delegations": [], "orders": []}, "unit": None,
            "record_id": None}


# Study authority: an unconditional delegation of both classes, so the gate never intervenes and the
# comparison isolates precedent logic (as the red-team scripts did). Labelled as a study device.
VEP_STUDY = {"deciders": [{"holder": "Equities Review Board", "holds": ["DISCLOSE_TO_VENDOR"]}],
             "delegations": [{"to": "agent", "holds": ["DISCLOSE_TO_VENDOR", "RETAIN"], "when": [],
                              "source": "study device"}], "orders": []}


@pytest.fixture
def vep():
    return cat("VEP")


@pytest.fixture
def aut():
    return cat("AUT")


def vep_cards(cvep):
    return {r: S.cards_from_record(cvep, rec(r))[0] for r in ("VEP-001", "VEP-004")}


def vep_record(tags, rid="VEP-X", authority=None, hidden=None, cvep=None):
    """A VEP record whose situation holds `tags` (one fact per factor stem), for reward tests."""
    c = cvep or cat("VEP")
    facts = []
    for stem, top in sorted(c.top(c.close(tags)).items()):
        facts.append({"id": f"f_{stem}", "text": c.factors[stem]["text"] + ".", "status": "observed",
                      "tags": c.ladder[stem][: c.tag[top][2] + 1]})
    return {"record": {
        "id": rid, "catalog": "VEP@2026-10", "provenance": {"kind": "authored", "gold_kind": "teaching"},
        "units": [], "situation": {"agent": {"role": "execute", "serves": "Equities Review Board"}, "facts": facts,
                                   "authority": copy.deepcopy(authority or VEP_STUDY)},
        "resolution": {"holdings": [], "plan": [], "status": "settled", "hidden_resolution": hidden or {}},
        "guidance": {"flips": [], "anomaly_cues": []}}}
