"""v2.4.1 contract (BUILD-BRIEF-v2.4 Step 0): arms, card views, pair ids, trace store, served-card stripping."""
from pathlib import Path

import pytest

from bench.schema import Case
from bench.schema.pipeline import (FrameCmp, GoldMap, OptionSpan, PairRecord, SpanEntry, SpanMap, TraceRecord,
                                   pair_id)
from pipeline.store import Store

FIX = Path(__file__).resolve().parents[2] / "bench" / "fixtures" / "pdf_example"


def case():
    return Case.load(FIX / "REF1.case.yaml")


def test_served_card_strips_backend_tags():
    v = case().serve("REF1")
    for o in v.doc["case"]["options"].values():
        assert set(o) == {"do"}
    assert all("move" in t for t in v.backend["options"].values())
    assert "flip_conditions" in v.doc["case"] and v.card_view == "full"


def test_thin_view_drops_flip_conditions_lesson_limits_and_refs():
    v = case().serve("REF1", card_view="thin")
    c = v.doc["case"]
    assert not {"flip_conditions", "lesson", "limits"} & set(c)
    assert v.flip_refs() == []
    assert c["verdict"]["choice"].startswith("REF1-O")


def test_bad_card_view():
    with pytest.raises(ValueError):
        case().serve("REF1", card_view="skinny")


def rec(**kw):
    base = dict(id="P-x", intent="restyle", case_scenario="DR-A@v1", trace_scenario="DR-A-r1@v1", split="train",
                frame=FrameCmp(question="same", decider="same", role="same"), options_map={}, fact_map=GoldMap(),
                consideration_map=GoldMap(), governs=True, relation="follows", choice="DR-A-r1@v1/O1",
                gold_tier="by-construction")
    return PairRecord(**{**base, **kw})


def test_legacy_records_get_arm_and_view():
    d = rec().dump()
    d.pop("arm"), d.pop("card_view")
    assert PairRecord.model_validate(d).arm == "relevant"
    d2 = {**d, "intent": "decoy", "relation": "not_governed", "governs": False}
    r = PairRecord.model_validate(d2)
    assert (r.arm, r.card_view) == ("decoy", "full")


def test_pair_id_includes_arm_and_view():
    a = pair_id("C", "T", "restyle", "relevant", "full")
    assert a != pair_id("C", "T", "restyle", "relevant", "thin") != pair_id("C", "T", "restyle", "revised", "full")


@pytest.mark.parametrize("kw", [
    dict(card_view="thin", relation="flips", via=["DR-A@v1/flip1"]),
    dict(arm="decoy"),
    dict(arm="augmented"),
    dict(arm="self"),
    dict(arm="none", split="test"),
])
def test_arm_rules(kw):
    with pytest.raises(ValueError):
        rec(**kw)


def test_trace_store_roundtrip(tmp_path):
    s = Store(tmp_path)
    sm = SpanMap(entries=[SpanEntry(fact="T/F1", message=1, start=0, end=4, realization="stated")],
                 options=[OptionSpan(option="T/O1", message=2, start=3, end=9, channel="tool_result")])
    t = TraceRecord(trace_scenario="DR-A-r1@v1", split="train", span_map=sm,
                    channels={"T/O1": "tool_result", "T/O2": "system_scope"}, recommended_option="T/O2", seed=7)
    s.save_trace(t, {"messages": [{"role": "system", "content": "x"}]})
    assert s.has_trace("DR-A-r1@v1") and s.trace("DR-A-r1@v1").recommended_option == "T/O2"
    assert s.trace_json("DR-A-r1@v1")["messages"][0]["content"] == "x"
    with pytest.raises(ValueError):
        TraceRecord(trace_scenario="X", split="train", span_map=sm, channels={"T/O1": "tool_result"},
                    recommended_option="T/O9")
