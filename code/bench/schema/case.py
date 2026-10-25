"""Reference case in the PDF v0.4 format (pp. 11-14), stored canonically with local ids.

    case = Case.load("data/cases/INT-301/DR-INT-301@v1.case.yaml")
    view = case.serve("REF1")          # ServedCase: .doc (dict in the PDF's served form), .table (served id -> global)
    view.yaml()                        # the text the harness injects

`library` holds authoring metadata (domain, family, provenance, review status...) and is stripped before serving.
Prose may reference items as {O2}, {flip1}; serving rewrites them to REF1-O2, REF1-flip1.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator, model_validator

from .common import (CASE_ID, LOCAL_ID, PROSE_REF, SERVED_PREFIX, AgentRole, Basis, FactKind, FactStatus, Move,
                     Strict, Weight)


class CaseOption(Strict):
    do: str
    move: Move
    irreversible: bool | None = None
    to: str | None = None


class CaseFact(Strict):
    id: str
    kind: FactKind
    status: FactStatus
    fact: str


class CaseConsideration(Strict):
    id: str
    facts: list[str]
    equity: str
    favors: list[str]
    weight: Weight
    why: str
    rules_out: list[str] | None = None      # only with weight: bar (v2.6 carry-over)


class TemptingWrong(Strict):
    option: str
    pull: str
    why_wrong: str


class CaseReasoning(Strict):
    read: str
    weighing: str
    tradecraft: str
    uncertainty: str
    handoff: str
    tempting_wrong: TemptingWrong
    rejected: dict[str, str] = Field(default_factory=dict)


class CaseVerdict(Strict):
    choice: str
    basis: Basis
    decisive: list[str]


class WouldChange(Strict):
    id: str
    if_: str = Field(alias="if")
    then: str
    why: str


class WouldNotChange(Strict):
    id: str
    if_: str = Field(alias="if")
    why: str


class WatchFor(Strict):
    id: str
    what: str
    favors: list[str]
    why: str


class FlipConditions(Strict):
    would_change: list[WouldChange]
    would_not_change: list[WouldNotChange] = Field(default_factory=list)
    watch_for: list[WatchFor] = Field(default_factory=list)


class Case(Strict):
    id: str
    title: str
    status: str = "draft"                    # draft | converted | needs_review | reviewed
    setting: str
    decider: str
    agent: str
    agent_role: AgentRole
    situation: str
    question: str
    options: dict[str, CaseOption]
    facts: list[CaseFact]
    considerations: list[CaseConsideration]
    reasoning: CaseReasoning
    verdict: CaseVerdict
    flip_conditions: FlipConditions
    lesson: str
    limits: str
    library: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _cid(cls, v):
        if not CASE_ID.match(v):
            raise ValueError(f"case id `{v}` must look like DR-<family>@v<k>")
        return v

    @model_validator(mode="after")
    def _refs(self):
        errs = []
        fact_ids = [f.id for f in self.facts]
        con_ids = [c.id for c in self.considerations]
        opt_ids = list(self.options)
        fc = self.flip_conditions
        flip_ids = [w.id for w in fc.would_change] + [w.id for w in fc.would_not_change] + [w.id for w in fc.watch_for]
        for kind, ids in (("F", fact_ids), ("C", con_ids), ("O", opt_ids)):
            for i in ids:
                if not (LOCAL_ID.match(i) and i.startswith(kind) and i[len(kind):].isdigit()):
                    errs.append(f"`{i}` should be a local {kind}<n> id")
        for name, pre, ids in (("would_change", "flip", [w.id for w in fc.would_change]),
                               ("would_not_change", "noflip", [w.id for w in fc.would_not_change]),
                               ("watch_for", "watch", [w.id for w in fc.watch_for])):
            for i in ids:
                if not (i.startswith(pre) and i[len(pre):].isdigit()):
                    errs.append(f"{name} id `{i}` should be {pre}<n>")
        for ids, what in ((fact_ids, "fact"), (con_ids, "consideration"), (flip_ids, "flip condition")):
            dup = {i for i in ids if ids.count(i) > 1}
            if dup:
                errs.append(f"duplicate {what} ids {sorted(dup)}")
        for c in self.considerations:
            errs += [f"{c.id} cites unknown fact {f}" for f in c.facts if f not in fact_ids]
            errs += [f"{c.id} favors unknown option {o}" for o in c.favors if o not in opt_ids]
            if (c.weight == "bar") != bool(c.rules_out):
                errs.append(f"{c.id}: rules_out goes with weight bar, and only with it")
            errs += [f"{c.id} rules out unknown option {o}" for o in (c.rules_out or []) if o not in opt_ids]
        v = self.verdict
        if v.choice not in opt_ids:
            errs.append(f"verdict choice {v.choice} is not an option")
        errs += [f"verdict decisive {d} is not a consideration" for d in v.decisive if d not in con_ids]
        r = self.reasoning
        if r.tempting_wrong.option not in opt_ids:
            errs.append(f"tempting_wrong option {r.tempting_wrong.option} is not an option")
        errs += [f"rejected {o} is not an option" for o in r.rejected if o not in opt_ids]
        errs += [f"{w.id} then {w.then} is not an option" for w in fc.would_change if w.then not in opt_ids]
        errs += [f"{w.id} favors unknown option {o}" for w in fc.watch_for for o in w.favors if o not in opt_ids]
        known = set(fact_ids) | set(con_ids) | set(opt_ids) | set(flip_ids)
        for ref in PROSE_REF.findall(" ".join(self._prose())):
            if ref not in known:
                errs.append(f"prose references unknown item {{{ref}}}")
        if errs:
            raise ValueError("; ".join(errs))
        return self

    def _prose(self) -> list[str]:
        r = self.reasoning
        fc = self.flip_conditions
        return ([self.situation, r.read, r.weighing, r.tradecraft, r.uncertainty, r.handoff, r.tempting_wrong.pull,
                 r.tempting_wrong.why_wrong, self.lesson, self.limits, *r.rejected.values()]
                + [c.why for c in self.considerations]
                + [w.why for w in fc.would_change] + [w.why for w in fc.would_not_change] + [w.why for w in fc.watch_for])

    @classmethod
    def load(cls, path) -> "Case":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))

    def dump(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)

    def global_id(self, local: str) -> str:
        return f"{self.id}/{local}"

    def serve(self, prefix: str = "REF1") -> "ServedCase":
        if not SERVED_PREFIX.match(prefix):
            raise ValueError(f"served prefix `{prefix}` must be REF<n>")
        return ServedCase.build(self, prefix)


def _rename(obj, fn):
    """Recursively rewrite ids (dict keys that are ids, id-valued strings, prose refs)."""
    if isinstance(obj, dict):
        return {fn(k) if isinstance(k, str) else k: _rename(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rename(v, fn) for v in obj]
    if isinstance(obj, str):
        return fn(obj)
    return obj


class ServedCase:
    """The served projection: PDF served form (`case: {id: REF1, ...}` content) + renumbering table."""

    def __init__(self, case_id: str, prefix: str, doc: dict, table: dict[str, str]):
        self.case_id, self.prefix, self.doc, self.table = case_id, prefix, doc, table

    @classmethod
    def build(cls, case: Case, prefix: str) -> "ServedCase":
        d = case.dump()
        d.pop("library", None)
        d.pop("status", None)
        d.pop("title", None)
        locals_ = {f.id for f in case.facts} | {c.id for c in case.considerations} | set(case.options)
        fc = case.flip_conditions
        locals_ |= {w.id for w in fc.would_change} | {w.id for w in fc.would_not_change} | {w.id for w in fc.watch_for}

        def fn(s: str) -> str:
            if s in locals_:
                return f"{prefix}-{s}"
            return PROSE_REF.sub(lambda m: f"{prefix}-{m.group(1)}", s)

        body = _rename({k: v for k, v in d.items() if k != "id"}, fn)
        doc = {"case": {"id": prefix, **body}}
        table = {f"{prefix}-{x}": case.global_id(x) for x in sorted(locals_)}
        table[prefix] = case.id
        return cls(case.id, prefix, doc, table)

    def yaml(self) -> str:
        return yaml.safe_dump(self.doc, sort_keys=False, allow_unicode=True, width=120)

    def to_global(self, served_id: str) -> str | None:
        return self.table.get(served_id)
