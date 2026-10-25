"""Answer key: the gold for each scored row of the PDF's table (pp. 23-24), for one live scenario under one arm.

Every field except `choice` is optional: today's pilot keys hold only the decision (choice, acceptable,
relation, via, the gold option set); full keys (facts, mappings, considerations...) come with the converted
data. A scorer whose gold is absent returns None (not scored), never 0.

Namespaces: live items use LIVE-* ids (the gold's own); case items use **global** ids (DR-...@v1/F1) so a key
does not depend on which REF<n> prefix the case was served under. Scorers translate the agent's served ids
through ServedCase.table.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from .common import FactKind, FactStatus, FrameCompare, Move, Relation, Strict, Weight


class GoldOption(Strict):
    do: str
    move: Move | None = None
    irreversible: bool | None = None
    source_id: str | None = None          # id in the source data (e.g. v2.6 letter "B")


class GoldFact(Strict):
    id: str
    kind: FactKind
    status: FactStatus
    fact: str
    weight: float = 1.0                    # importance for ENUM_GRADER (salient vs texture); weights are Peter's


class GoldFrame(Strict):
    question: str
    decider: str
    my_role: str


class GoldFrameMap(Strict):
    question: FrameCompare
    decider: FrameCompare
    role: FrameCompare


class GoldPair(Strict):
    live: str
    case: str                              # global case item id


class GoldMapping(Strict):
    matched: list[GoldPair] = Field(default_factory=list)
    corresponding: list[GoldPair] = Field(default_factory=list)
    live_only: list[str] = Field(default_factory=list)
    case_only: list[str] = Field(default_factory=list)


class GoldConsideration(Strict):
    id: str
    facts: list[str]
    equity: str
    favors: list[str]
    weight: Weight
    why: str | None = None


class GoldFlip(Strict):
    id: str
    if_: str = Field(alias="if")
    then: str | None = None
    why: str | None = None


class AnswerKey(Strict):
    scenario: str                          # live scenario id
    arm: str                               # none | relevant | augmented | decoy
    served: str | None = None              # global case id served in this arm (None for the no-reference arm)
    options: dict[str, GoldOption]         # the scenario's gold option set (Options Enumeration + choice translation)
    choice: str                            # gold option id
    acceptable: list[str] = Field(default_factory=list)   # other ids that score as correct (empty: only `choice`)
    relation: Relation | None = None       # None for the no-reference arm
    via: list[str] | None = None           # global would_change id(s) for flips
    # Full keys (optional today)
    frame: GoldFrame | None = None
    facts: list[GoldFact] | None = None
    frame_map: GoldFrameMap | None = None
    option_map: dict[str, str | None] | None = None     # live option -> global case option
    fact_mapping: GoldMapping | None = None
    considerations: list[GoldConsideration] | None = None
    consideration_mapping: GoldMapping | None = None
    governs: bool | None = None
    course: str | None = None
    decisive: list[str] | None = None
    now: list[str] | None = None
    flip_conditions: list[GoldFlip] | None = None
    provenance: dict = Field(default_factory=dict)       # how this key was made (converted / authored / reviewed)

    @model_validator(mode="after")
    def _refs(self):
        errs = []
        ids = set(self.options)
        if self.choice not in ids:
            errs.append(f"choice {self.choice} is not a gold option")
        errs += [f"acceptable {a} is not a gold option" for a in self.acceptable if a not in ids]
        if self.relation == "flips" and not self.via:
            errs.append("relation flips needs via")
        if self.relation != "flips" and self.via:
            errs.append("via only with relation flips")
        if self.arm == "none" and (self.served or self.relation):
            errs.append("the no-reference arm has no served case and no relation")
        if errs:
            raise ValueError("; ".join(errs))
        return self

    def correct(self, gold_option_id: str | None) -> bool:
        return gold_option_id is not None and (gold_option_id == self.choice or gold_option_id in self.acceptable)

    @classmethod
    def load(cls, path) -> "AnswerKey":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))
