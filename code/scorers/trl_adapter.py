"""TRL reward-function wrappers: one per scorer row, all calling scorers.score_reply.

    from scorers.trl_adapter import reward_funcs
    funcs = reward_funcs(judge)                      # every headline row (score.ROWS), or reward_funcs(judge, ["verdict_choice", "facts_enum"])
    GRPOTrainer(..., reward_funcs=funcs, args=GRPOConfig(reward_weights=[...]))   # the weights are Peter's (TBD)

Signature (TRL >= 0.14): f(prompts, completions, **kwargs) -> list[float | None]. TRL passes every extra dataset
column as a kwarg list (one entry per completion). Columns this adapter reads:
    answer_key   AnswerKey | dict | YAML/JSON str               (required)
    served       ServedCase | list[ServedCase] | dict {case_id, prefix, doc, table} | list of those | JSON str | None
    reasoning    optional: reasoning text the server returned separately (vLLM reasoning parser)
`completions` may be strings or conversational message lists (the last assistant message's content; a
`reasoning_content` field is passed to the parser as the think text).

None is returned as None: TRL treats it as "not applicable" (NaN, ignored in the weighted sum), which is exactly the
scorers' meaning (gold absent, or after not_governed). Caution for the reward design: if None ends up worth more than
a wrong answer, a policy learns to say not_governed to escape every post-applicability penalty.

One score_reply call per completion is shared across all the reward functions (an LRU memo keyed by the completion
and its columns), so asking for 30 rows costs one round of judge calls, not 30.
"""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Any, Callable

import yaml

from bench.schema import AnswerKey, ServedCase, parse_reply

from .judge import Judge
from .score import ROWS, score_reply


def _text_of(completion) -> tuple[str, str | None]:
    if isinstance(completion, str):
        return completion, None
    if isinstance(completion, dict):
        return completion.get("content") or "", completion.get("reasoning_content") or completion.get("reasoning")
    if isinstance(completion, list):
        msgs = [m for m in completion if isinstance(m, dict) and m.get("role", "assistant") == "assistant"]
        if msgs:
            return _text_of(msgs[-1])
    return str(completion), None


def to_key(x) -> AnswerKey:
    if isinstance(x, AnswerKey):
        return x
    if isinstance(x, str):
        x = yaml.safe_load(x)
    return AnswerKey.model_validate(x)


def to_served(x) -> list[ServedCase]:
    if x is None:
        return []
    if isinstance(x, ServedCase):
        return [x]
    if isinstance(x, str):
        x = json.loads(x) if x.strip() else None
        return to_served(x)
    if isinstance(x, dict):
        return [ServedCase(x["case_id"], x["prefix"], x["doc"], x["table"])]
    return [s for item in x for s in to_served(item)]


def served_column(served) -> str:
    """Serialize ServedCase(s) into a dataset column (JSON string)."""
    return json.dumps([{"case_id": s.case_id, "prefix": s.prefix, "doc": s.doc, "table": s.table}
                       for s in to_served(served)])


def _fingerprint(*parts) -> str:
    def norm(p):
        if isinstance(p, AnswerKey):
            return p.model_dump(by_alias=True)
        if isinstance(p, ServedCase) or (isinstance(p, list) and p and isinstance(p[0], ServedCase)):
            return served_column(p)
        return p
    return hashlib.sha256(json.dumps([norm(p) for p in parts], default=str, sort_keys=True).encode()).hexdigest()


class RewardScorer:
    """Holds the judge and the memo; .scores(completions, **columns) -> list of score dicts."""

    def __init__(self, judge: Judge, memo_size: int = 4096, score_kwargs: dict | None = None):
        self.judge, self.memo_size, self.score_kwargs = judge, memo_size, score_kwargs or {}
        self._memo: OrderedDict[str, dict] = OrderedDict()

    def one(self, completion, answer_key, served=None, reasoning=None) -> dict:
        content, reas = _text_of(completion)
        reas = reasoning or reas
        fp = _fingerprint(content, reas, answer_key, served)
        if fp in self._memo:
            self._memo.move_to_end(fp)
            return self._memo[fp]
        key = to_key(answer_key)
        s = score_reply(parse_reply(content, reas, noref=key.arm == "none"), key, to_served(served), self.judge,
                        **self.score_kwargs)
        self._memo[fp] = s
        if len(self._memo) > self.memo_size:
            self._memo.popitem(last=False)
        return s

    def scores(self, completions, answer_key, served=None, reasoning=None, **_) -> list[dict]:
        n = len(completions)
        served = served if served is not None else [None] * n
        reasoning = reasoning if reasoning is not None else [None] * n
        return [self.one(c, k, s, r) for c, k, s, r in zip(completions, answer_key, served, reasoning)]


def reward_func(scorer: RewardScorer, row: str) -> Callable[..., list[float | None]]:
    def f(prompts, completions, **kwargs) -> list[float | None]:
        out = []
        for s in scorer.scores(completions, **kwargs):
            v = s.get(row)
            out.append(None if v is None else float(v))
        return out
    f.__name__ = f"benchbook_{row.replace('.', '__')}"      # TRL logs rewards under __name__
    f.__qualname__ = f.__name__
    return f


def reward_funcs(judge: Judge, rows: list[str] | None = None, **kw: Any) -> list[Callable]:
    scorer = RewardScorer(judge, **kw)
    return [reward_func(scorer, r) for r in (rows or ROWS)]
