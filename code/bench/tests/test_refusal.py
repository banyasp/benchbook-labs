"""Refusal detection and recording (design 4.2; brief W4). Fakes only."""
import json
import sys
import types

import pytest

from bench import models


def llm():
    return models._llm()


def test_detect_refusal():
    d = llm().detect_refusal
    assert d("", "content_filtered") == "stop_reason:content_filtered"
    assert d("x", "guardrail_intervened")
    assert d("I'm sorry, but I can't help with that.", "end_turn") == "refusal-shaped reply"
    assert d("I cannot assist with this request.", None)
    assert d('{"title": "I cannot assist"}', "end_turn") is None
    assert d("The Administrative Judge denies the request.", "end_turn") is None
    assert d("", "end_turn") is None and d("partial", "max_tokens") is None


def test_exposed_from_models():
    assert models.RefusalError is llm().RefusalError and issubclass(models.RefusalError, llm().LLMError)


def test_complete_records_refusal(tmp_path, monkeypatch):
    L = llm()
    monkeypatch.setitem(L.BACKENDS, "openrouter", lambda bare, m, t, mt, ctx: (ctx.update(stop_reason="content_filter") or "", {}))
    prov = tmp_path / "p.jsonl"
    with pytest.raises(models.RefusalError) as ei:
        L.complete("openrouter/openai/gpt-oss-120b", [{"role": "user", "content": "x"}], provenance=prov, stage="extract.FQ")
    assert ei.value.reason == "stop_reason:content_filter"
    rec = json.loads(prov.read_text().splitlines()[-1])
    assert rec["refusal"] is True and rec["refusal_reason"] and rec["stage"] == "extract.FQ"


def test_hook_is_unset_by_default_and_used_when_set(tmp_path, monkeypatch):
    L = llm()
    assert L.REFUSAL_HOOK is None
    monkeypatch.setitem(L.BACKENDS, "openrouter", lambda bare, m, t, mt, ctx: ("I'm sorry, but I can't help with that.", {}))
    monkeypatch.setattr(L, "REFUSAL_HOOK", lambda e, model, messages, ctx: "fallback text")
    out = L.complete("openrouter/openai/gpt-oss-120b", [{"role": "user", "content": "x"}], provenance=tmp_path / "p.jsonl")
    assert out == "fallback text"
    assert json.loads((tmp_path / "p.jsonl").read_text())["refusal_hook"] == "invoked"
