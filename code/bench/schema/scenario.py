"""Live scenario: a trace at its decision point, what each arm serves, the answer keys, the perturbation record.

    data/scenarios/<FAMILY>/<scenario id>.scenario.yaml

The perturbation record is per scenario (variant type, operator, which facts/considerations were touched and how),
so distance weighting can be applied later without regenerating anything (DECISIONS 2026-10-25).
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from .answer_key import AnswerKey
from .common import Strict

Arm = Literal["none", "relevant", "augmented", "decoy"]


class Touched(Strict):
    item: str                       # global case item id the perturbation acts on (or a new LIVE id)
    item_kind: Literal["fact", "consideration", "option", "authority", "frame"]
    change: Literal["same", "restyled", "revised", "added", "removed", "influence"]
    note: str | None = None


class Perturbation(Strict):
    variant: str                    # restyle | trap | flip | boundary | transfer ... (v2.6 `variant`)
    operator: str | None = None     # what was done, e.g. "revise fact", "add fact", "swap authority"
    source_case: str                # global id of the case the scenario was derived from
    touched: list[Touched] = Field(default_factory=list)
    domain_shift: bool = False      # cross-domain transfer
    notes: str | None = None


class ArmSpec(Strict):
    served: list[str] = Field(default_factory=list)    # global case ids, in serving order (REF1, REF2...)
    key: str                                          # path (relative to the scenario file) of the AnswerKey


class LiveScenario(Strict):
    id: str
    family: str
    split: Literal["train", "dev", "test", "pilot"] = "pilot"
    domain: str | None = None
    trace: str                                        # path to the trace json (repo-relative)
    equities: str                                     # equities set id (data/registry/equities/<id>.yaml)
    arms: dict[str, ArmSpec]
    perturbation: Perturbation
    provenance: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _arms(self):
        bad = [a for a in self.arms if a not in ("none", "relevant", "augmented", "decoy")]
        if bad:
            raise ValueError(f"unknown arms {bad}")
        if "none" in self.arms and self.arms["none"].served:
            raise ValueError("arm `none` serves nothing")
        return self

    @classmethod
    def load(cls, path) -> "LiveScenario":
        p = Path(path)
        s = cls.model_validate(yaml.safe_load(p.read_text()))
        s._path = p
        return s

    def answer_key(self, arm: str) -> AnswerKey:
        base = getattr(self, "_path", Path(".")).parent
        return AnswerKey.load(base / self.arms[arm].key)
