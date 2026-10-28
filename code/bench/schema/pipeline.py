"""2f data pipeline records (BUILD-BRIEF-2f-2026-10-25; design v2.2 §2-4, §6). Extends the 2a models; no fork.

Scenario X = (F, Q, A) is a 2a `Case` (the PDF case format: facts = F; setting/decider/agent/question/options = Q;
considerations/reasoning/verdict/flip_conditions/lesson/limits = A) wrapped with lineage, provenance, status,
family and split. Any scenario can be served as a case C or rendered as a trace T.

PairRecord = one (C, T) with the gold mapping M_{C,T} the operator emitted, the relation/via/verdict gold and its
tier, the touched weighing condition, the rendered trace + span map, and the teacher's solve samples.

v2.4.1 contract (BUILD-BRIEF-v2.4 Step 0; design §7.1, §8.1, §9): PairRecord gains arm, card_view,
recommended_option, d, writer, trace_ref; pair id = hash(C, T, intent, arm, card_view) (`pair_id`). Rendered traces
live once per trace scenario in the trace store (`TraceRecord`, data/store/traces/<trace-scenario-id>/); pairs
reference them by `trace_ref` and never copy them. Records written before v2.4 load with arm = relevant
(decoy-intent records: arm = decoy), card_view = full.

Ids: scenario ids are 2a case ids (DR-<family>-<n>@v<k>); items are local (F1, C1, O1, flip1) and global as
"<scenario id>/<local>". Pair records hold **global** ids on both sides; `project` renumbers T's items to LIVE-*
in trace order (from the span map) and C's to REF1-* (Case.serve), and stores both tables.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, field_validator, model_validator

from .case import Case, CardView
from .common import Relation, Strict

GoldTier = Literal["by-construction", "source-endorsed", "model-solved"]
Split = Literal["train", "dev", "test", "eval-only"]
Status = Literal["extracted", "derived", "needs_review", "reviewed", "rejected"]
Realization = Literal["stated", "paraphrased", "implied", "split"]
Intent = Literal["restyle", "flip", "add_fact", "decoy", "revised", "pilot", "reverse_restyle", "augmented", "self",
                 "none"]
Arm = Literal["relevant", "augmented", "revised", "decoy", "none", "self"]
Writer = Literal["granite-rs", "teacher"]
FlipRealization = Literal["indirect", "paraphrase", "direct"]
RefusalSensitivity = Literal["low", "medium", "high"]
Channel = Literal["system_scope", "operator_message", "colleague_message", "tool_result", "attached_document"]
CHANNELS: tuple[str, ...] = Channel.__args__
TRAIN_ARMS = ("relevant", "augmented", "revised", "decoy")      # none and self are eval only (design §7.2)
EVAL_SPLITS = ("test", "eval-only")
SPAN = re.compile(r"^src:[0-9a-f]{12}#p\d+\.\d+(\[\d+:\d+\])?$")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_obj(o) -> str:
    return sha256_text(json.dumps(o, sort_keys=True, ensure_ascii=False, default=str))


# ------------------------------------------------------------------ provenance
class ProvStep(Strict):
    """One operation that produced (part of) an artifact."""
    id: str                                   # step id, unique within the artifact (e.g. "extract.FQ", "perturb")
    operator: str                             # acquire | normalize | extract | perturb | pair | render | solve | project | import
    model: str | None = None                  # model spec (bench.models role's model) or None for code
    role: str | None = None                   # bench.models role name
    prompt_version: str | None = None         # e.g. "extract_fq.v1" (+ sha12 of the prompt file)
    inputs: dict[str, str] = Field(default_factory=dict)   # name -> sha256 of each input
    params: dict = Field(default_factory=dict)             # temperature, reasoning_effort, seed...
    ts: str | None = None
    notes: str | None = None


class Provenance(Strict):
    steps: list[ProvStep] = Field(default_factory=list)
    fields: dict[str, str] = Field(default_factory=dict)   # field path (e.g. "case.facts", "case.verdict") -> step id
    authored: list[str] = Field(default_factory=list)      # field paths written by a model without a source span/statement

    def step(self, **kw) -> ProvStep:
        s = ProvStep(**kw)
        self.steps.append(s)
        return s


# ------------------------------------------------------------------ scenario
class SourceRef(Strict):
    sha256: str                               # data/raw/<sha256>
    doc: str                                  # data/docs/<sha12>.jsonl
    url: str | None = None
    title: str | None = None
    kind: str | None = None                   # e.g. "DOE OHA personnel security decision"
    license: str | None = None


class Lineage(Strict):
    parent: str | None = None                 # scenario id this was derived from
    operator: str | None = None               # restyle | flip | add_fact | ...
    detail: dict = Field(default_factory=dict)


class Scenario(Strict):
    id: str                                   # = case.id
    family: str                               # incident family; splits are per family (R18)
    split: Split
    domain: str
    content_domain: str | None = None         # design §4.2, e.g. security-clearance, gov-ethics, targeting
    refusal_sensitivity: RefusalSensitivity | None = None
    held_out: bool = False                    # the whole held-out source domain (design §13.5); split is test
    status: Status = "extracted"
    case: Case                                # F, Q, A in the PDF case format
    verdict_tier: GoldTier                    # where case.verdict.choice comes from
    basis: str | None = None                  # who endorsed the answer, in the source's terms (e.g. "Administrative Judge")
    source: SourceRef | None = None
    fact_spans: dict[str, list[str]] = Field(default_factory=dict)   # local fact id -> span ids (empty list = authored)
    tags: list[str] = Field(default_factory=list)   # e.g. agent-recast, flip-conditions-authored, eval-only-import
    lineage: Lineage = Field(default_factory=Lineage)
    provenance: Provenance = Field(default_factory=Provenance)

    @model_validator(mode="after")
    def _check(self):
        errs = []
        if self.id != self.case.id:
            errs.append(f"scenario id {self.id} != case id {self.case.id}")
        fids = {f.id for f in self.case.facts}
        errs += [f"fact_spans for unknown fact {k}" for k in self.fact_spans if k not in fids]
        for k, spans in self.fact_spans.items():
            errs += [f"{k}: bad span id {s}" for s in spans if not SPAN.match(s)]
        if self.verdict_tier == "source-endorsed" and not self.source:
            errs.append("source-endorsed verdict needs a source")
        if self.held_out and self.split != "test":
            errs.append("a held-out-domain scenario must be split test")
        if errs:
            raise ValueError("; ".join(errs))
        return self

    def grounded_facts(self) -> list[str]:
        return [f for f, s in self.fact_spans.items() if s]

    @classmethod
    def load(cls, path) -> "Scenario":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))

    def dump(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


# ------------------------------------------------------------------ pair
class GPair(Strict):
    live: str                                 # global T item id
    case: str                                 # global C item id
    note: str | None = None


class GoldMap(Strict):
    matched: list[GPair] = Field(default_factory=list)
    corresponding: list[GPair] = Field(default_factory=list)
    live_only: list[str] = Field(default_factory=list)       # global T ids
    case_only: list[str] = Field(default_factory=list)       # global C ids


class FrameCmp(Strict):
    question: Literal["same", "same_kind", "different"]
    decider: Literal["same", "same_kind", "different"]
    role: Literal["same", "same_kind", "different"]


class Touched(Strict):
    """The condition in C's weighing the operator changed (R25: the teacher must cite it)."""
    item: str | None = None                   # global id: a would_change / would_not_change item or a consideration
    condition: str                            # the condition in words
    how: str                                  # what the operator did to it (e.g. "realized indirectly via a tool result")


class SpanEntry(Strict):
    fact: str                                 # global T fact id
    message: int                              # index into trace["messages"]
    start: int
    end: int
    realization: Realization


class OptionSpan(Strict):
    """Where an option is discoverable in the trace (design §8.1): never a menu; channel pre-assigned by code."""
    option: str                               # global T option id
    message: int
    start: int
    end: int
    channel: Channel


class SpanMap(Strict):
    entries: list[SpanEntry]
    options: list[OptionSpan] = Field(default_factory=list)
    allowed: list[str] = Field(default_factory=list)          # true-but-not-in-F_T details the renderer added
    planted: list[str] = Field(default_factory=list)          # look-alikes, if any


class SolveSample(Strict):
    path: str                                 # pairs/<id>/solve/sample-<k>.yaml (raw teacher output)
    accepted: bool
    reasons: list[str] = Field(default_factory=list)          # why rejected (or empty)


class TraceRecord(Strict):
    """One rendered trace per trace scenario (design §7.1): data/store/traces/<trace_scenario>/trace.yaml (+ trace.json).
    Channels and the recommendation belong to the trace and are never conditioned on any pair's gold (§7.4)."""
    trace_scenario: str
    split: Split
    trace: str = "trace.json"                 # path relative to the trace dir
    span_map: SpanMap
    channels: dict[str, Channel]              # global T option id -> discovery channel (seeded permutation)
    recommended_option: str | None = None     # global T option id someone in the trace recommends (~50% of traces)
    seed: int | None = None
    gates: dict[str, Any] = Field(default_factory=dict)       # gate name -> pass/fail + detail
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance = Field(default_factory=Provenance)

    @model_validator(mode="after")
    def _check(self):
        if self.recommended_option is not None and self.recommended_option not in self.channels:
            raise ValueError(f"recommended_option {self.recommended_option} is not one of the trace's options")
        return self

    @classmethod
    def load(cls, path) -> "TraceRecord":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))

    def dump(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


def pair_id(case_scenario: str, trace_scenario: str, intent: str, arm: str, card_view: str = "full") -> str:
    """Pair id = hash(C, T, intent, arm, card_view) (design §7.1)."""
    return "P-" + sha256_text(f"{case_scenario}|{trace_scenario}|{intent}|{arm}|{card_view}")[:10]


class PairRecord(Strict):
    id: str                                   # e.g. P-<sha10>
    intent: Intent
    arm: Arm = "relevant"
    card_view: CardView = "full"
    ar_prompt: bool | None = None             # analogical-reasoning prompt on/off (assigned per train item, seeded)
    case_scenario: str                        # C (served); "" for arm none
    trace_scenario: str                       # T (rendered)
    split: Split                              # inherited from the family (C and T share a family for derived pairs)
    equities: str = "pilot"                   # equities set id (data/registry/equities/<id>.yaml) injected with C
    # gold structure (M_{C,T} + verdict)
    frame: FrameCmp
    options_map: dict[str, str | None]        # global T option -> global C option (None: no counterpart)
    fact_map: GoldMap
    consideration_map: GoldMap
    governs: bool
    relation: Relation
    via: list[str] | None = None              # global C would_change ids (flips only)
    choice: str                               # global T option id (gold verdict)
    acceptable: list[str] = Field(default_factory=list)
    gold_tier: GoldTier
    touched: Touched | None = None
    realization: FlipRealization | None = None   # flips: indirect | paraphrase; augmented: direct (design §6.3, §7.2)
    recommended_option: str | None = None     # copied from the trace record (global T option id)
    d: float | None = None                    # structural distance d(C, T), design §7.5; features in distance_features
    writer: Writer | None = None              # who wrote the accepted SFT target (design §10)
    tags: list[str] = Field(default_factory=list)   # e.g. revised-authored, composed-with-C, rationalized
    # artifacts
    trace_ref: str | None = None              # trace store key (= trace scenario id), data/store/traces/<trace_ref>/
    trace: str | None = None                  # legacy (pre-v2.4): path (relative to the pair dir) of trace.json
    span_map: SpanMap | None = None
    solve: list[SolveSample] = Field(default_factory=list)
    distance_features: dict = Field(default_factory=dict)     # operator axis, #facts touched, magnitude...
    provenance: Provenance = Field(default_factory=Provenance)

    @model_validator(mode="before")
    @classmethod
    def _legacy(cls, v):
        if isinstance(v, dict) and "arm" not in v:
            v = {**v, "arm": "decoy" if v.get("intent") == "decoy" else "relevant"}
        return v

    @field_validator("via", mode="before")
    @classmethod
    def _via(cls, v):
        if v in (None, "", []):
            return None
        return [v] if isinstance(v, str) else v

    @model_validator(mode="after")
    def _check(self):
        errs = []
        if self.relation == "flips" and not self.via:
            errs.append("flips needs via")
        if self.relation != "flips" and self.via:
            errs.append("via only with flips")
        if (self.relation == "not_governed") == self.governs:
            errs.append("governs must be false exactly when relation is not_governed")
        if self.choice in self.acceptable:
            errs.append("choice repeated in acceptable")
        if self.card_view == "thin" and self.relation in ("flips", "not_governed"):
            errs.append("thin cards only on follows/distinguished pairs (design §9.3)")
        if self.arm == "decoy" and self.relation != "not_governed":
            errs.append("decoy arm gold must be not_governed")
        if self.arm == "augmented" and self.relation != "flips":
            errs.append("augmented arm gold must be flips")
        if self.arm in ("none", "self") and self.split not in EVAL_SPLITS:
            errs.append(f"arm {self.arm} is eval only")
        if self.arm == "none" and self.case_scenario:
            errs.append("arm none serves no card (case_scenario must be empty)")
        if errs:
            raise ValueError("; ".join(errs))
        return self

    @classmethod
    def load(cls, path) -> "PairRecord":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))

    def dump(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)
