"""The TRL and Inspect adapters call the same score_reply."""
from __future__ import annotations

import math

import pytest

from bench.schema import parse_reply
from scorers import ROWS, StubJudge, score_reply
from scorers.trl_adapter import reward_funcs, served_column

from .conftest import full_key_dict, reply_text


def test_trl_reward_funcs(served):
    judge = StubJudge()
    funcs = reward_funcs(judge)
    assert len(funcs) == len(ROWS) and funcs[0].__name__ == "benchbook_schema_valid"
    good = reply_text()
    bad = good.replace("choice: LIVE-O3", "choice: LIVE-O1")
    cols = {"answer_key": [full_key_dict()] * 3, "served": [served_column(served)] * 3}
    completions = [good, [{"role": "assistant", "content": bad}], ""]
    out = {f.__name__: f(["p"] * 3, completions, **cols) for f in funcs}
    assert out["benchbook_verdict_choice"] == [1.0, 0.0, 0.0]
    assert out["benchbook_via_match"] == [None, None, None]
    assert out["benchbook_facts_enum"][0] == 1.0
    assert out["benchbook_considerations_enum__facts"][0] == 1.0
    calls = dict(judge.calls)
    funcs[0](["p"] * 3, completions, **cols)        # memoized: no new judge calls
    assert judge.calls == calls


def test_inspect_scorer_matches_score_reply(served):
    import asyncio

    from inspect_ai.model import ChatMessageAssistant, ModelOutput
    from inspect_ai.scorer import Target
    from inspect_ai.solver import TaskState

    from scorers.inspect_adapter import benchbook_scorer

    out = ModelOutput.from_content(model="mock", content=reply_text())
    state = TaskState(model="mock", sample_id="PDF-JOURNALIST", epoch=1, input="x", messages=[],
                      output=out, metadata={"answer_key": full_key_dict(), "served": served_column(served)})
    sc = benchbook_scorer(StubJudge())
    s = asyncio.run(sc(state, Target("")))
    from bench.schema import AnswerKey
    want = score_reply(parse_reply(reply_text()), AnswerKey.model_validate(full_key_dict()), served, StubJudge())
    assert {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in s.value.items()} == want
    assert s.value["verdict_choice"] == 1


def test_inspect_eval_end_to_end(served, tmp_path):
    """A real (mock-model) Inspect eval: the dict value and the None-skipping metrics survive the pipeline."""
    from inspect_ai import Task, eval
    from inspect_ai.dataset import Sample
    from inspect_ai.model import get_model, ModelOutput
    from inspect_ai.solver import generate

    from scorers.inspect_adapter import benchbook_scorer

    model = get_model("mockllm/model", custom_outputs=[ModelOutput.from_content("mockllm/model", reply_text())] * 2)
    md = {"answer_key": full_key_dict(), "served": served_column(served)}
    task = Task(dataset=[Sample(input="go", id="s1", metadata=md)], solver=generate(),
                scorer=benchbook_scorer(StubJudge()))
    log = eval(task, model=model, log_dir=str(tmp_path), display="none")[0]
    assert log.status == "success", log.error
    metrics = {m.name: m.value for sc in log.results.scores for m in sc.metrics.values()}
    by = {sc.name: {k: m.value for k, m in sc.metrics.items()} for sc in log.results.scores}
    assert by["verdict_choice"]["scored_mean"] == 1.0
    # Inspect drops NaN (= not scored) samples before metrics; a key never scored reports NaN, never 0.
    assert math.isnan(by["via_match"]["scored_mean"])
    assert by["via_match"]["scored_n"] == 0.0 or math.isnan(by["via_match"]["scored_n"])
    assert by["now"]["scored_n"] == 1.0
    assert metrics
