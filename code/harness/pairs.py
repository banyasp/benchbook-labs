"""build_pair_episode: one PairRecord (+ its TraceRecord + the served card for the arm) -> the harness Episode.

The single prompt builder for eval, SFT export, RL and W1's rejection sampler (design §9.3):

    from harness.pairs import build_pair_episode
    ep = build_pair_episode(pair, store, HarnessSettings(mode="C"))

What it assembles: the rendered trace (store.trace_json(pair.trace_ref)), equities E_d (pair.equities; off with
`equities=False`), the served card for the pair's arm (`pair.case_scenario`, `pair.card_view`; arm `none` serves
nothing, arm `self` serves the trace's own scenario), the analogical-reasoning prompt (`pair.ar_prompt`), and the
format spec for the settings' mode. Thin view: `Case.serve(.., card_view="thin")` plus a leak check that fails loudly
(`ThinLeakError`) if any flip-condition reference survives.

Mode is NOT defaulted here: pass `settings` (project passes mode C explicitly).
"""
from __future__ import annotations

import types
from pathlib import Path

import yaml

from bench.models import ROOT
from bench.schema import EquitySet
from bench.schema.pipeline import PairRecord

from .episode import Episode, ThinLeakError, build_episode, serve_cases  # noqa: F401
from .settings import HarnessSettings

DEFAULT_EQUITIES = "pilot"


def load_equities(spec: str | Path | None) -> EquitySet:
    """spec: a path to an equities yaml, or a set id under data/registry/equities."""
    spec = spec or DEFAULT_EQUITIES
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


def trace_path(pair: PairRecord, store) -> Path:
    """The pair's rendered trace.json: the trace store (pair.trace_ref) or, for pre-v2.4 pairs, the pair's own file."""
    if pair.trace_ref:
        rec = store.trace(pair.trace_ref)
        return store.trace_dir(pair.trace_ref) / rec.trace
    if pair.trace:
        return store.pair_dir(pair.id) / pair.trace
    raise ValueError(f"pair {pair.id} has neither trace_ref nor trace (run render first)")


def build_pair_episode(pair: PairRecord, store, settings: HarnessSettings, *, equities: bool | EquitySet = True,
                       card_view: str | None = None, ar_prompt: bool | None = None, case=None) -> Episode:
    """pair: PairRecord. store: pipeline.store.Store. settings: HarnessSettings (mode explicit).
    equities: True = E_d from pair.equities; False = equities-off cell; an EquitySet = use it.
    card_view / ar_prompt: override the pair's own (eval cells); None = the pair's value (ar_prompt None -> the
    settings' value). case: pre-loaded bench.schema.Case to serve (tests, speed); default store.scenario(...).case."""
    view = card_view or pair.card_view
    if pair.arm == "none":
        cases = []
    else:
        sid = pair.case_scenario or pair.trace_scenario        # `self`: the trace's own scenario is the card
        cases = [case if case is not None else store.scenario(sid).case]
    ar = ar_prompt if ar_prompt is not None else (pair.ar_prompt if pair.ar_prompt is not None
                                                  else settings.analogical_prompt)
    settings = settings.with_(analogical_prompt=bool(ar))
    eq = equities if isinstance(equities, EquitySet) else (load_equities(pair.equities) if equities else None)
    scen = types.SimpleNamespace(id=pair.id, family=None, trace=str(trace_path(pair, store)),
                                 equities=(eq.id if eq is not None else pair.equities))
    try:
        T = store.scenario(pair.trace_scenario)
        scen.family = T.family
    except Exception:
        pass
    ep = build_episode(scen, pair.arm, settings, _Lib(eq), retriever=_Retriever(cases), card_view=view,
                       equities=eq is not None)
    ep.meta.update({"pair": pair.id, "arm": pair.arm, "intent": pair.intent, "card_view": view, "ar_prompt": bool(ar),
                    "equities_on": eq is not None, "trace_scenario": pair.trace_scenario,
                    "case_scenario": pair.case_scenario})
    return ep
