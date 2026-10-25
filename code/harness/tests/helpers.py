"""Shared test helpers: a fake library/retriever (2b is built in parallel) and the INT-301-v01 scenario."""
from pathlib import Path

import yaml

from bench.schema import Case, EquitySet, LiveScenario

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[3]
TRACE = "data/draft/B001/INT-301/INT-301-v01.trace.json"


class FakeLib:
    def equities(self, set_id):
        return EquitySet.model_validate(yaml.safe_load((FIX / "equities.yaml").read_text()))


class FakeRetriever:
    def __init__(self, cases=None):
        self.cases = cases if cases is not None else [Case.load(FIX / "DR-INT-301.case.yaml")]

    def retrieve(self, scenario, arm):
        return [] if arm == "none" else list(self.cases)


def scenario() -> LiveScenario:
    return LiveScenario.model_validate({
        "id": "INT-301-v01", "family": "INT-301", "trace": TRACE, "equities": "pilot-fixture",
        "arms": {"none": {"served": [], "key": "x.yaml"}, "relevant": {"served": ["DR-INT-301@v1"], "key": "x.yaml"}},
        "perturbation": {"variant": "restyle", "source_case": "DR-INT-301@v1"}})
