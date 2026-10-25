"""Equities: the deployer's short list of values the harness injects (PDF p. 11; ~10-20 per deployment)."""
from __future__ import annotations

import re

from pydantic import field_validator, model_validator

from .common import Strict

EQUITY_ID = re.compile(r"^[a-z][a-z0-9_]*$")


class Equity(Strict):
    id: str
    gloss: str

    @field_validator("id")
    @classmethod
    def _id(cls, v):
        if not EQUITY_ID.match(v):
            raise ValueError(f"equity id `{v}` must be snake_case")
        return v


class EquitySet(Strict):
    id: str                       # deployment / set name
    status: str | None = None     # e.g. needs_review | reviewed
    equities: list[Equity]

    @model_validator(mode="after")
    def _unique(self):
        ids = [e.id for e in self.equities]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"duplicate equity ids: {sorted(dup)}")
        return self

    def ids(self) -> set[str]:
        return {e.id for e in self.equities}

    def served(self) -> dict:
        """What the harness injects (PDF p. 11 form)."""
        return {"equities": [{"id": e.id, "gloss": e.gloss} for e in self.equities]}
