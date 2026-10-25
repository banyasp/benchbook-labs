"""The student's prompt for a pair, built by the harness's own build_episode (same injection, equities, served card,
format spec). Shared by solve (teacher input) and project (SFT / RL / Inspect prompts)."""
from __future__ import annotations

import types
from pathlib import Path

import yaml

from bench.models import ROOT
from bench.schema import EquitySet
from bench.schema.pipeline import PairRecord, Scenario
from harness.episode import Episode, build_episode
from harness.settings import HarnessSettings
from pipeline.store import Store

DEFAULT_EQUITIES = "pilot"


def load_equities(spec: str | Path | None, T: Scenario | None = None) -> EquitySet:
    """spec: a path to an equities yaml, or a set id under data/registry/equities. Default: T.case.library['equities']
    if present, else the pilot set."""
    spec = spec or (T.case.library.get("equities") if T else None) or DEFAULT_EQUITIES
    p = Path(str(spec))
    if not p.exists():
        p = ROOT / "data" / "registry" / "equities" / f"{spec}.yaml"
    return EquitySet.model_validate(yaml.safe_load(p.read_text()))


class _Lib:
    def __init__(self, eq: EquitySet):
        self.eq = eq

    def equities(self, _id):
        return self.eq


class _Retriever:
    def __init__(self, cases):
        self.cases = cases

    def retrieve(self, scenario, arm):
        return list(self.cases)


def student_episode(pair: PairRecord, store: Store, equities: EquitySet | None = None,
                    settings: HarnessSettings | None = None, C: Scenario | None = None) -> Episode:
    settings = settings or HarnessSettings(mode="B")
    C = C or store.scenario(pair.case_scenario)
    T = store.scenario(pair.trace_scenario)
    if not pair.trace:
        raise ValueError(f"pair {pair.id} has no trace (run render first)")
    eq = equities or load_equities(None, T)
    scen = types.SimpleNamespace(id=pair.id, family=T.family, trace=str(store.pair_dir(pair.id) / pair.trace),
                                 equities=eq.id)
    return build_episode(scen, "relevant", settings, _Lib(eq), retriever=_Retriever([C.case]))
