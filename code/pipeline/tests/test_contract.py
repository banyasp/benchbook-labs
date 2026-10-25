"""2f contract: Scenario and PairRecord round-trip through the store (built from the PDF fixture)."""
from pathlib import Path

import pytest

from bench.schema import Case
from bench.schema.pipeline import GoldMap, GPair, PairRecord, Scenario, SourceRef
from pipeline.store import Store

FIX = Path(__file__).resolve().parents[2] / "bench" / "fixtures" / "pdf_example"


def scen(tmp_path):
    case = Case.load(FIX / "REF1.case.yaml")
    return Scenario(id=case.id, family="PDF-001", split="eval-only", domain="maritime", case=case,
                    verdict_tier="source-endorsed", basis="Peter Banyas (PDF v0.4)",
                    source=SourceRef(sha256="0" * 64, doc="000000000000.jsonl"),
                    fact_spans={"F1": ["src:000000000000#p11.3"], "F2": []})


def test_scenario_roundtrip(tmp_path):
    st = Store(tmp_path)
    s = scen(tmp_path)
    p = st.save_scenario(s)
    assert st.scenario(s.id).case.verdict.choice == "O1" and s.grounded_facts() == ["F1"]
    st.save_scenario(s)                                       # second write keeps a version
    assert list((p.parent / "versions").glob("*.yaml"))


def test_scenario_rejects_bad_spans(tmp_path):
    d = scen(tmp_path).dump()
    d["fact_spans"] = {"F99": ["nope"]}
    with pytest.raises(ValueError):
        Scenario.model_validate(d)


def test_pair_rules(tmp_path):
    C = "DR-PDF-001@v1"
    pr = PairRecord(id="P-test", intent="restyle", case_scenario=C, trace_scenario="DR-PDF-001-rs1@v1",
                    split="eval-only", frame={"question": "same", "decider": "same", "role": "same"},
                    options_map={"DR-PDF-001-rs1@v1/O1": f"{C}/O1"},
                    fact_map=GoldMap(matched=[GPair(live="DR-PDF-001-rs1@v1/F1", case=f"{C}/F1")]),
                    consideration_map=GoldMap(), governs=True, relation="follows",
                    choice="DR-PDF-001-rs1@v1/O1", gold_tier="by-construction")
    Store(tmp_path).save_pair(pr)
    assert Store(tmp_path).pair("P-test").relation == "follows"
    with pytest.raises(ValueError):
        PairRecord.model_validate({**pr.dump(), "relation": "flips"})          # flips without via
    with pytest.raises(ValueError):
        PairRecord.model_validate({**pr.dump(), "relation": "not_governed"})   # governs must be false
