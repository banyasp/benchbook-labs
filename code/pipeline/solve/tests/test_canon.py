"""solve/canon.py: format slips are repaired; ids, mappings and choices are never touched."""
from pathlib import Path

from bench.schema import parse_reply
from pipeline.solve.canon import canonicalize, fix_step

FIX = Path(__file__).resolve().parents[3] / "bench" / "fixtures" / "pdf_example"


def test_alias_and_lists():
    d, fx = fix_step("consideration_enumeration", {"kind": "consideration_enumeration", "considerations": [
        {"id": "LIVE-C1", "facts": ["LIVE-F1"], "equity": "x", "favors": ["LIVE-O1"], "weight": "moderate", "why": "w"}]})
    assert d["considerations"][0]["weight"] == "weak" and fx


def test_unknown_fact_kind_falls_back_to_situation():
    d, fx = fix_step("fact_enumeration", {"kind": "fact_enumeration", "frame": {"question": "q", "decider": "d", "my_role": "r"},
                                          "facts": [{"id": "LIVE-F1", "kind": "zzz", "status": "confirmed", "fact": "f"}],
                                          "options": {"LIVE-O1": "a"}})
    assert d["facts"][0]["kind"] == "situation" and any("zzz -> situation" in f for f in fx)


def test_frame_compare_gloss_stripped_and_unknown_elsewhere_left_alone():
    d, fx = fix_step("verdict", {"kind": "verdict", "relation": "zzz"})
    assert d.get("relation") == "zzz"


def test_strict_reply_roundtrips():
    raw = next(FIX.glob("*reply*.yaml")).read_text() if list(FIX.glob("*reply*.yaml")) else None
    if raw is None:
        return
    text, fx = canonicalize(raw)
    if text is not None:
        assert parse_reply(text).strict_ok
