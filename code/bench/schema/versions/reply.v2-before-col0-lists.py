"""The agent's reply: the PDF v0.4 steps 4-11 as `kind:` YAML documents (pp. 14-18), plus `via` in the verdict.

    parsed = parse_reply(content, reasoning=reasoning_content)   # tolerant
    parsed.steps["verdict"]          # dict (raw YAML), whatever the model wrote
    parsed.models["verdict"]         # the strict pydantic model, if that step validated
    parsed.errors["fact_mapping"]    # why it didn't
    parsed.strict_ok                 # every required step present, validated, no repairs (SCHEMA_VALIDATOR 0/1)

Tolerance (reasoning modes A, B, C, C' of DECISIONS 2026-10-25): documents may sit after `</think>` (A, B),
inside `<think>` (C), or inside it with free prose between them (C'); in ```yaml fences or not; separated by
`---` or not. A document starts at a line `kind: <step>` and ends at the next `kind:` line, `---`, fence, or the
first column-0 line that is not a `snake_case_key:` (prose). Repairs (recorded, and they fail strict_ok): unquoted
`<placeholder>` values. When a step appears more than once, the last occurrence outside <think> wins, else the
last inside; all occurrences are kept in `parsed.all_docs`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml
from pydantic import Field, ValidationError, field_validator, model_validator

from .common import FactKind, FactStatus, FrameCompare, Relation, Strict, Weight

STEPS = ["fact_enumeration", "fact_mapping", "consideration_enumeration", "consideration_mapping",
         "applicability", "reasoning", "verdict"]
# The no-reference arm has nothing to map to: no mapping/applicability steps, no `case` in reasoning,
# no `relation`/`via` in the verdict (parse_reply(..., noref=True)).
NOREF_STEPS = ["fact_enumeration", "consideration_enumeration", "reasoning", "verdict"]
CASE_BOUND = {"reasoning": ["case", "case_approach"], "verdict": ["relation"]}   # required unless noref


# ---------------------------------------------------------------- step models
class Frame(Strict):
    question: str
    decider: str
    my_role: str


class LiveFact(Strict):
    id: str
    kind: FactKind
    status: FactStatus
    fact: str


class FactEnumeration(Strict):
    kind: str = "fact_enumeration"
    frame: Frame
    facts: list[LiveFact]
    options: dict[str, str]

    @model_validator(mode="after")
    def _ids(self):
        ids = [f.id for f in self.facts]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"duplicate fact ids {sorted(dup)}")
        if len(self.options) < 2:
            raise ValueError("fewer than two options")
        return self


class FrameMap(Strict):
    question: FrameCompare
    decider: FrameCompare
    role: FrameCompare


class Pair(Strict):
    live: str
    case: str
    role: str | None = None        # considerations: what the pair does in the argument
    note: str | None = None        # facts: what changed (corresponding)


class CaseOnly(Strict):
    """A case-only item, optionally with the assumption the agent makes about its live counterpart (PDF p. 13)."""
    case: str
    assumption: str | None = None


def _case_only(v):
    return [CaseOnly(case=x) if isinstance(x, str) else x for x in (v or [])]


class FactMapping(Strict):
    kind: str = "fact_mapping"
    case: str
    frame: FrameMap
    note: str | None = None
    note_2: str | None = None
    options: dict[str, str | None]
    matched: list[Pair]
    corresponding: list[Pair]
    live_only: list[str]
    case_only: list[CaseOnly]

    _co = field_validator("case_only", mode="before")(lambda cls, v: _case_only(v))


class LiveConsideration(Strict):
    id: str
    facts: list[str]
    equity: str
    favors: list[str]
    weight: Weight
    why: str
    rules_out: list[str] | None = None


class ConsiderationEnumeration(Strict):
    kind: str = "consideration_enumeration"
    considerations: list[LiveConsideration]


class ConsiderationMapping(Strict):
    kind: str = "consideration_mapping"
    case: str
    matched: list[Pair]
    corresponding: list[Pair]
    live_only: list[str]
    case_only: list[CaseOnly]

    _co = field_validator("case_only", mode="before")(lambda cls, v: _case_only(v))


class Applicability(Strict):
    kind: str = "applicability"
    case: str
    frame: FrameMap
    governs: bool
    why: str
    decisive_in_case: list[str] | None = None   # A4 open with Peter: optional for now


class TemptingWrong(Strict):
    option: str
    pull: str
    why_wrong: str


class Reasoning(Strict):
    kind: str = "reasoning"
    case: str | None = None             # required unless noref (enforced in parse_reply)
    case_approach: str | None = None
    weighing: str
    tradecraft: str
    uncertainty: str
    handoff: str
    tempting_wrong: TemptingWrong
    rejected: dict[str, str] = Field(default_factory=dict)


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


class VerdictFlips(Strict):
    would_change: list[WouldChange]
    would_not_change: list[WouldNotChange] = Field(default_factory=list)
    watch_for: list[WatchFor] = Field(default_factory=list)


class Verdict(Strict):
    kind: str = "verdict"
    choice: str
    course: str
    relation: Relation | None = None    # required unless noref (enforced in parse_reply)
    via: list[str] | None = None     # served case would_change id(s) that fired; required iff relation is flips
    decisive: list[str]
    now: list[str]
    flip_conditions: VerdictFlips

    @field_validator("via", mode="before")
    @classmethod
    def _via(cls, v):
        if v in (None, "", "null", []):
            return None
        return [v] if isinstance(v, str) else v

    @model_validator(mode="after")
    def _via_rule(self):
        if self.relation == "flips" and not self.via:
            raise ValueError("relation flips needs `via`: the served case's would_change id(s) that fired")
        if self.relation != "flips" and self.via:
            raise ValueError(f"`via` is only for relation flips (got {self.relation})")
        return self


MODELS = {"fact_enumeration": FactEnumeration, "fact_mapping": FactMapping,
          "consideration_enumeration": ConsiderationEnumeration, "consideration_mapping": ConsiderationMapping,
          "applicability": Applicability, "reasoning": Reasoning, "verdict": Verdict}


# ---------------------------------------------------------------- parser
@dataclass
class Doc:
    kind: str
    data: dict
    where: str                # "content" | "think"
    start_line: int
    repairs: list[str] = field(default_factory=list)
    prose_after: bool = False  # free text followed this doc (allowed in mode C'; never scored)


@dataclass
class ParsedReply:
    steps: dict[str, dict] = field(default_factory=dict)        # kind -> chosen raw doc
    where: dict[str, str] = field(default_factory=dict)         # kind -> content | think
    models: dict[str, Any] = field(default_factory=dict)        # kind -> validated pydantic model
    errors: dict[str, str] = field(default_factory=dict)        # kind -> validation error (or "missing")
    repairs: dict[str, list[str]] = field(default_factory=dict)
    all_docs: list[Doc] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)           # chunks that started `kind:` but never parsed
    unknown_kinds: list[str] = field(default_factory=list)
    noref: bool = False

    @property
    def missing(self) -> list[str]:
        return [k for k in self.required() if k not in self.steps]

    def required(self) -> list[str]:
        """Reasoning is not required after applicability governs: false (not_governed ends the reasoning)."""
        if self.noref:
            return list(NOREF_STEPS)
        gov = self.steps.get("applicability", {}).get("governs")
        return [k for k in STEPS if not (k == "reasoning" and gov is False)]

    @property
    def in_order(self) -> bool:
        order = [d.kind for d in self.all_docs if d.kind in STEPS]
        firsts = list(dict.fromkeys(order))
        return firsts == [k for k in STEPS if k in firsts]

    @property
    def strict_ok(self) -> bool:
        return (not self.missing and all(k in self.models for k in self.required())
                and not any(self.repairs.values()) and not self.unknown_kinds)

    def model(self, kind):
        return self.models.get(kind)


THINK = re.compile(r"<think>(.*?)(?:</think>|\Z)", re.S)
KIND_LINE = re.compile(r"^kind:\s*['\"]?([A-Za-z_]+)['\"]?\s*$")
STOP_LINE = re.compile(r"^(---+|```.*|\.\.\.)\s*$")
TOP_KEY = re.compile(r"^[a-z_][a-z0-9_]*:(\s|$)")   # top-level lines of a step doc are always snake_case keys
PLACEHOLDER = re.compile(r"^(\s*(?:-\s+)?[A-Za-z_][\w-]*:\s+)(<[^>\n]*>.*)$")


def split_think(content: str | None, reasoning: str | None = None) -> tuple[str, str]:
    """(think_text, outside_text). vLLM's reasoning parser hands <think> text over separately as `reasoning`;
    raw text may still carry <think>...</think> inline."""
    content = content or ""
    think = [reasoning] if reasoning else []
    think += THINK.findall(content)
    outside = THINK.sub("", content)
    outside = outside.replace("</think>", "")
    return "\n".join(t for t in think if t), outside


def _load(lines: list[str]) -> tuple[dict | None, list[str]]:
    """Parse a candidate chunk; if it fails, quote unquoted <placeholder> values once and retry."""
    cur = list(lines)
    while cur and not cur[-1].strip():
        cur.pop()
    try:
        d = yaml.safe_load("\n".join(cur))
        if isinstance(d, dict) and "kind" in d:
            return d, []
    except yaml.YAMLError:
        pass
    repairs, fixed = [], []
    for ln in cur:
        m = PLACEHOLDER.match(ln)
        if m:
            fixed.append(m.group(1) + yaml.safe_dump(m.group(2), default_style='"').strip())
            repairs.append(f"quoted placeholder value: {m.group(2)[:40]}")
        else:
            fixed.append(ln)
    if repairs:
        try:
            d = yaml.safe_load("\n".join(fixed))
            if isinstance(d, dict) and "kind" in d:
                return d, repairs
        except yaml.YAMLError:
            pass
    return None, []


def _scan(text: str, where: str) -> tuple[list[Doc], list[str]]:
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if KIND_LINE.match(ln)]
    docs, bad = [], []
    for n, s in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        chunk, prose = [], False
        for ln in lines[s:end]:
            if chunk and (STOP_LINE.match(ln) or (ln[:1].strip() and not TOP_KEY.match(ln) and not ln.startswith("#"))):
                prose = prose or not STOP_LINE.match(ln)
                break
            chunk.append(ln)
        d, repairs = _load(chunk)
        if d is None:
            bad.append("\n".join(chunk[:3]))
            continue
        docs.append(Doc(str(d.get("kind")), d, where, s, repairs, prose_after=prose))
    return docs, bad


FLAT_FRAME = {"fact_enumeration": ("question", "decider", "my_role"),
              "fact_mapping": ("question", "decider", "role"), "applicability": ("question", "decider", "role")}


def _unflatten_frame(kind: str, d: dict) -> tuple[dict, list[str]]:
    """Granite often writes frame's keys at the top level; fold them back into `frame` (a recorded repair)."""
    keys = FLAT_FRAME.get(kind)
    if not keys or "frame" in d or not all(k in d for k in keys):
        return d, []
    d = dict(d)
    d["frame"] = {k: d.pop(k) for k in keys}
    return d, ["folded top-level question/decider/role into frame"]


def parse_reply(content: str | None, reasoning: str | None = None, *, noref: bool = False) -> ParsedReply:
    """noref=True for the no-reference arm (NOREF_STEPS; no case/relation)."""
    think, outside = split_think(content, reasoning)
    out = ParsedReply(noref=noref)
    for text, where in ((think, "think"), (outside, "content")):
        docs, bad = _scan(text, where)
        out.all_docs += docs
        out.unparsed += bad
    for d in out.all_docs:
        if d.kind not in MODELS:
            out.unknown_kinds.append(d.kind)
            continue
        prev = out.where.get(d.kind)
        if prev == "content" and d.where == "think":
            continue                      # an outside occurrence beats one inside <think>
        data, fixes = _unflatten_frame(d.kind, d.data)
        out.steps[d.kind], out.where[d.kind], out.repairs[d.kind] = data, d.where, d.repairs + fixes
    for k in (NOREF_STEPS if noref else STEPS):
        if k not in out.steps:
            out.errors[k] = "missing"
            continue
        try:
            m = MODELS[k].model_validate(out.steps[k])
        except ValidationError as e:
            out.errors[k] = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())[:600]
            continue
        absent = [f for f in CASE_BOUND.get(k, []) if not noref and getattr(m, f) is None]
        if absent:
            out.errors[k] = f"missing {', '.join(absent)}"
            continue
        out.models[k] = m
    return out
