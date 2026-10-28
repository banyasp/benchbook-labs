import pytest

from pipeline.ingest.technique_check import check, is_clean, scan_scenario

DECISION_OK = [
    "The commander authorized the strike on the two tankers after concluding an imminent threat existed.",
    "The pilots offered a show of force; the commander declined.",
    "The strike cell assessed that civilians were likely present, and civilian casualties were later confirmed.",
    "Approval authority had been delegated to the brigade commander under the rules of engagement.",
    "The inquiry applied distinction, proportionality and precautions in attack, and found the decision lawful.",
    "Whether to fire on the radar track before positive identification, given the ROE self-defense condition.",
    "The ship's commanding officer had no time to seek authorization from higher headquarters.",
    "The controller refused the flight's requests to employ weapons while higher authority was consulted.",
    "Force protection, mission and legitimacy were weighed against the risk of harm to civilians.",
    "The convening authority disagreed with the investigating officer and approved the findings.",
    "The air strike killed civilians; the coalition acknowledged the casualties and paid condolence.",
    "The brigade received new guidance over the course of 12 months and the new commander acted.",
    "The committee reviewed the bombing of the television station as a military objective.",
]

TECHNIQUE = [
    ("The aircraft dropped a GBU-12 on the building.", "munition"),
    ("They selected a 500-lb bomb with a delayed fuze.", "munition"),
    ("A Hellfire missile was used.", "munition"),
    ("The strike used a 2,000 pound JDAM.", "munition"),
    ("The CDE was run at tier 2 using the collateral damage estimation methodology.", "cde"),
    ("The non-combatant casualty cut-off value was exceeded.", "cde"),
    ("The blast radius and hazard distance were computed.", "cde"),
    ("The FLIR operator zoomed the camera and the sensor footprint covered the road.", "isr"),
    ("Full-motion video showed the vehicles; laser designation continued.", "isr"),
    ("The attack heading was 270 and the release altitude was set.", "geometry"),
    ("They flew a run-in from the north at an altitude of 12,000 feet.", "geometry"),
    ("The cell followed the find, fix, track, target, engage cycle.", "procedure"),
    ("A nine-line brief was passed on the net.", "procedure"),
    ("The kill chain was completed in minutes.", "procedure"),
]


@pytest.mark.parametrize("t", DECISION_OK)
def test_decision_language_not_flagged(t):
    assert check(t) == []
    assert is_clean(t)


@pytest.mark.parametrize("t,cat", TECHNIQUE)
def test_technique_flagged(t, cat):
    fl = check(t)
    assert any(f.severity == "strip" and f.category == cat for f in fl), (t, fl)
    assert not is_clean(t)


def test_platform_is_review_not_strip():
    fl = check("Two F-15 pilots misidentified the helicopters.")
    assert fl and all(f.severity == "review" for f in fl)
    assert is_clean("Two F-15 pilots misidentified the helicopters.")


def test_scan_scenario_paths():
    sc = {"title": "Strike decision", "facts": ["The commander declined a show of force.", "A GBU-38 was dropped."],
          "meta": {"note": "ok"}}
    hits = scan_scenario(sc)
    assert [p for p, _ in hits] == ["facts[1]"]
