"""Persist an operator result: X' as a scenario, the gold partial as data/store/partials/<T id>.yaml."""
from __future__ import annotations

import yaml

from pipeline.store import Store, write_yaml

from .common import dump_partial


def partial_path(store: Store, tid: str):
    return store.root / "partials" / f"{tid}.yaml"


def save_result(store: Store, T, partial: dict):
    sp = store.save_scenario(T)
    pp = partial_path(store, T.id)
    write_yaml(pp, dump_partial(partial))
    return sp, pp


def load_partial(store: Store, tid: str) -> dict:
    return yaml.safe_load(partial_path(store, tid).read_text())
