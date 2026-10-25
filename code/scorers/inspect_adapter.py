"""Inspect (inspect_ai 0.3.x) adapter: one @scorer whose Score.value is the dict of per-row scores.

    from scorers.inspect_adapter import benchbook_scorer
    Task(dataset=..., solver=..., scorer=benchbook_scorer(judge))

Per sample it reads:
    state.metadata["answer_key"]   AnswerKey | dict | YAML str          (required)
    state.metadata["served"]       ServedCase(s) | dict(s) | JSON str | None   (see trl_adapter.to_served)
    state.metadata["raw_text"]     optional: the full assistant text incl. any prefill (harness Completion.raw_text;
                                   modes C/C' prefill `<think>\\nkind: fact_enumeration\\n`, which output.completion
                                   would miss). Else state.output.completion + the message's reasoning content.
Score.value = score_reply(...) with None (not scored) written as NaN, because Inspect's epoch reducer turns None
into 0; Score.metadata = the format report, alignments and paths.
Metrics: for every key, the mean over the samples where it was scored, and how many were (`scored_mean`,
`scored_n`); None never counts as 0.
"""
from __future__ import annotations

import math

from inspect_ai.scorer import Score, Target, metric, scorer
from inspect_ai.solver import TaskState

from bench.schema import parse_reply

from .judge import Judge, StubJudge
from .score import score_reply_detailed
from .trl_adapter import to_key, to_served


def _vals(scores):
    out = []
    for s in scores:
        v = getattr(s, "score", s).value          # SampleScore or (per-key dict metrics) Score
        if v is None or isinstance(v, (dict, list, str)):
            continue
        v = float(v)
        if not math.isnan(v):
            out.append(v)
    return out


@metric
def scored_mean():
    """Mean over the samples where this key was scored (None skipped, not counted as 0)."""
    def m(scores):
        v = _vals(scores)
        return sum(v) / len(v) if v else float("nan")
    return m


@metric
def scored_n():
    """How many samples were scored on this key."""
    def m(scores):
        return float(len(_vals(scores)))
    return m


def _reasoning_of(state: TaskState) -> str | None:
    msg = getattr(state.output, "message", None)
    content = getattr(msg, "content", None)
    if isinstance(content, list):
        parts = [getattr(c, "reasoning", None) for c in content if getattr(c, "type", None) == "reasoning"]
        parts = [p for p in parts if p]
        return "\n".join(parts) if parts else None
    return None


@scorer(metrics=[{"*": [scored_mean(), scored_n()]}])
def benchbook_scorer(judge: Judge | None = None, threshold: float | None = None, weights: dict | None = None):
    judge = judge or StubJudge()

    async def score(state: TaskState, target: Target) -> Score:
        md = state.metadata or {}
        raw = md.get("raw_text")
        if raw:
            parsed = parse_reply(raw)
        else:
            parsed = parse_reply(state.output.completion if state.output else "", _reasoning_of(state))
        full = score_reply_detailed(parsed, to_key(md["answer_key"]), to_served(md.get("served")), judge,
                                    threshold=threshold, weights=weights)
        choice = full.details["notes"].get("choice") or {}
        # None -> NaN: Inspect's epoch reducer maps None to 0, which would score "not scored" as wrong.
        value = {k: (float("nan") if v is None else v) for k, v in full.rows.items()}
        return Score(value=value, answer=str(choice.get("gold_id")),
                     explanation=f"choice -> {choice.get('gold_id')} ({choice.get('how')})",
                     metadata={"format_report": full.details["format_report"],
                               "option_alignment": full.details["option_alignment"],
                               "notes": full.details["notes"]})

    return score
