"""The student's prompt for a pair, built by the harness's own build_episode (same injection, equities, served card,
format spec). Shared by solve (teacher input), rs (Granite rejection sampling) and project (SFT / RL / Inspect prompts).

v2.4: the trace comes from the trace store (`pair.trace_ref`; the legacy per-pair `pair.trace` is the fallback), the
card is served in the pair's `card_view` (build_episode's own card_view argument), the analogical-reasoning prompt
follows `pair.ar_prompt` when it is set, and arm `none` serves no card."""
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


def trace_file(pair: PairRecord, store: Store) -> Path:
    """The rendered trace.json: the trace store entry if the pair has a trace_ref, else the legacy per-pair file."""
    if pair.trace_ref:
        return store.trace_dir(pair.trace_ref) / store.trace(pair.trace_ref).trace
    if pair.trace:
        return store.pair_dir(pair.id) / pair.trace
    raise ValueError(f"pair {pair.id} has no trace (run render first)")


def student_episode(pair: PairRecord, store: Store, equities: EquitySet | None = None,
                    settings: HarnessSettings | None = None, C: Scenario | None = None) -> Episode:
    settings = settings or HarnessSettings(mode="B")
    if pair.ar_prompt is not None:
        settings = settings.with_(analogical_prompt=bool(pair.ar_prompt))
    has_card = bool(pair.case_scenario) and pair.arm != "none"
    C = (C or store.scenario(pair.case_scenario)) if has_card else None
    T = store.scenario(pair.trace_scenario)
    tf = trace_file(pair, store)
    eq = equities or load_equities(pair.equities or None, T)
    scen = types.SimpleNamespace(id=pair.id, family=T.family, trace=str(tf), equities=eq.id)
    return build_episode(scen, pair.arm, settings, _Lib(eq),
                         retriever=_Retriever([C.case] if C else []), card_view=pair.card_view)
