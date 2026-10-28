"""W4a split rule v2 (design v2.4.1 §13.5)."""
from pipeline.ingest import registry as R


def test_document_family_shared_by_episodes():
    src = {"id": "OGE-5CFR2635-B", "family_prefix": "OGE", "episodes": [{"n": 1, "section": "2635.204", "family": "a"},
                                                                         {"n": 2, "section": "2635.204", "family": "b"}]}
    assert {R.family_of(src, e) for e in src["episodes"]} == {"OGE-2635-204"}
    assert R.family_of({"id": "X", "family": "OHA-1", "episodes": []}, {"n": 1}) == "OHA-1"


def test_split_fractions_and_held_out():
    fd = {f"OHA-{i}": "psa" for i in range(40)} | {f"NS-{i}": "military-operational" for i in range(10)}
    sp, warn = R.assign_splits_v2(fd)
    oha = [sp[f"OHA-{i}"] for i in range(40)]
    assert oha.count("test") == 8 and oha.count("dev") == 4 and oha.count("train") == 28
    assert all(sp[f"NS-{i}"] == "test" for i in range(10)) and not warn


def test_small_domain_warns():
    sp, warn = R.assign_splits_v2({f"G-{i}": "ethics" for i in range(6)})
    assert list(sp.values()).count("test") == 1 and warn
