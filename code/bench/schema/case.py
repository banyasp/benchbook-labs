"""Reference case in the PDF v0.4 format (pp. 11-14), stored canonically with local ids.

    case = Case.load("data/cases/INT-301/DR-INT-301@v1.case.yaml")
    view = case.serve("REF1")          # ServedCase: .doc (dict in the PDF's served form), .table (served id -> global)
    view.yaml()                        # the text the harness injects
    case.serve("REF1", card_view="thin")   # design v2.4.1 §9.3: no flip conditions, lesson or limits

Served cards never carry the backend option tags `move`, `irreversible` or `to:` (design §5.1; Peter confirmed
2026-10-27, departure from the PDF card recorded in the reconciliation file). They stay on `ServedCase.backend`
for balance and analysis code, and never reach the prompt.

`library` holds authoring metadata (domain, family, provenance, review status...) and is stripped before serving.
Prose may reference items as {O2}, {flip1}; serving rewrites them to REF1-O2, REF1-flip1.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import re
from typing import Literal

import yaml
from pydantic import Field, field_validator, model_validator

from .common import (CASE_ID, LOCAL_ID, PROSE_REF, SERVED_PREFIX, AgentRole, Basis, FactKind, FactStatus, Move,
                     Strict, Weight)


CardView = Literal["full", "thin"]
OPTION_TAGS = ("move", "irreversible", "to")          # backend-only option tags, stripped from the served card
FLIP_REF = re.compile(r"(?:REF\d+-)?(?:flip|noflip|watch)\d+")
_SENT = re.compile(r"(?<=[.!?;])\s+")


def _drop_flip_refs(text: str) -> str:
    """Thin view: remove every sentence (or clause after a semicolon) that cites a flip condition."""
    if not FLIP_REF.search(text):
        return text
    kept = [s for s in _SENT.split(text) if not FLIP_REF.search(s)]
    return " ".join(kept).strip()


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

    def serve(self, prefix: str = "REF1", card_view: CardView = "full") -> "ServedCase":
        if not SERVED_PREFIX.match(prefix):
            raise ValueError(f"served prefix `{prefix}` must be REF<n>")
        return ServedCase.build(self, prefix, card_view)


def _thin_prose(obj):
    if isinstance(obj, dict):
        return {k: _thin_prose(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_thin_prose(v) for v in obj]
    return _drop_flip_refs(obj) if isinstance(obj, str) else obj


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
    """The served projection: PDF served form (`case: {id: REF1, ...}` content) + renumbering table.
    `backend` holds what was stripped (option tags), keyed by served option id; it is never serialized."""

    def __init__(self, case_id: str, prefix: str, doc: dict, table: dict[str, str], card_view: CardView = "full",
                 backend: dict | None = None):
        self.case_id, self.prefix, self.doc, self.table = case_id, prefix, doc, table
        self.card_view, self.backend = card_view, backend or {}

    @classmethod
    def build(cls, case: Case, prefix: str, card_view: CardView = "full") -> "ServedCase":
        if card_view not in ("full", "thin"):
            raise ValueError(f"card_view must be full or thin, not {card_view!r}")
        d = case.dump()
        d.pop("library", None)
        d.pop("status", None)
        d.pop("title", None)
        tags = {o: {k: v[k] for k in OPTION_TAGS if k in v} for o, v in d["options"].items()}
        d["options"] = {o: {"do": v["do"]} for o, v in d["options"].items()}
        if card_view == "thin":
            for k in ("flip_conditions", "lesson", "limits"):
                d.pop(k, None)
        locals_ = {f.id for f in case.facts} | {c.id for c in case.considerations} | set(case.options)
        fc = case.flip_conditions
        locals_ |= {w.id for w in fc.would_change} | {w.id for w in fc.would_not_change} | {w.id for w in fc.watch_for}

        def fn(s: str) -> str:
            if s in locals_:
                return f"{prefix}-{s}"
            return PROSE_REF.sub(lambda m: f"{prefix}-{m.group(1)}", s)

        body = _rename({k: v for k, v in d.items() if k != "id"}, fn)
        if card_view == "thin":
            body = _thin_prose(body)
        doc = {"case": {"id": prefix, **body}}
        table = {f"{prefix}-{x}": case.global_id(x) for x in sorted(locals_)}
        table[prefix] = case.id
        backend = {"options": {f"{prefix}-{o}": t for o, t in tags.items()}}
        return cls(case.id, prefix, doc, table, card_view, backend)

    def flip_refs(self) -> list[str]:
        """Every flip-condition reference left anywhere in the served text (thin view must have none)."""
        return FLIP_REF.findall(self.yaml())

    def yaml(self) -> str:
        return yaml.safe_dump(self.doc, sort_keys=False, allow_unicode=True, width=120)

    def to_global(self, served_id: str) -> str | None:
        return self.table.get(served_id)
