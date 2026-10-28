"""Persist an operator result: X' as a scenario, the gold partial as data/store/partials/<T id>.yaml."""
from __future__ import annotations

import yaml

from pipeline.store import Store, write_yaml

from .common import dump_partial


def partial_path(store: Store, tid: str):
    return store.root / "partials" / f"{tid}.yaml"


def revised_partial_path(store: Store, tid: str):
    """revise_card partials live in partials/revised/ (NOT partials/*.yaml): their trace_scenario is a placeholder, so pair's
    derived-record scan must not mistake them for ordinary (C, T) pairs. W2 reads them explicitly."""
    return store.root / "partials" / "revised" / f"{tid}.yaml"


INHERIT = ("held_out", "content_domain", "refusal_sensitivity")


def save_result(store: Store, T, partial: dict):
    if T.lineage.parent:                     # derived scenarios inherit the domain tags of their parent (held-out panel)
        try:
            P = store.scenario(T.lineage.parent)
        except KeyError:
            P = None
        for k in INHERIT if P is not None else ():
            setattr(T, k, getattr(P, k))
    sp = store.save_scenario(T)
    pp = revised_partial_path(store, T.id) if partial.get("intent") == "revised" else partial_path(store, T.id)
    write_yaml(pp, dump_partial(partial))
    return sp, pp


def load_partial(store: Store, tid: str) -> dict:
    p = partial_path(store, tid)
    return yaml.safe_load((p if p.exists() else revised_partial_path(store, tid)).read_text())
