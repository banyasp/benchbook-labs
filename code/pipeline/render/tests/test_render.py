"""render: quote location, span map, trace file, provenance (offline, mock renderer)."""
import json

import pytest

from pipeline.render import RenderError, find_quote, render_pair, render_trace
from pipeline.render.render import INJECTION
from pipeline.solve.fixtures import flip_pair, mock_render_llm
from pipeline.store import Store


def test_find_quote_variants():
    c = "Photo page:\n  four   photos of the gate."
    assert find_quote(c, "four   photos") == (14 + 2, 14 + 2 + 13) or find_quote(c, "four photos") is not None
    assert find_quote(c, "FOUR PHOTOS of the gate") is not None
    assert find_quote(c, "nothing like this") is None


def test_render_pair_writes_trace_and_span_map(tmp_path):
    st, pid = flip_pair(tmp_path)
    p = st.pair(pid)
    T = st.scenario(p.trace_scenario)
    p = render_pair(p, st, llm=mock_render_llm(T))
    tr = json.loads((st.pair_dir(pid) / "trace.json").read_text())
    msgs = tr["messages"]
    assert msgs[0]["role"] == "system" and msgs[-1]["name"] == "benchbook" and msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == INJECTION and "{{CARD}}" in msgs[-1]["content"]
    assert len(p.span_map.entries) == 10
    for e in p.span_map.entries:        # ranges are computed in Python and index the stored text exactly
        fact = next(f for f in T.case.facts if f.id == e.fact.rpartition("/")[2])
        assert msgs[e.message]["content"][e.start:e.end] == fact.fact
    d = json.loads((st.pair_dir(pid) / "render.diagnostics.json").read_text())
    assert d["coverage"] == 1.0 and d["facts_located"] == 10
    s = [x for x in Store(tmp_path).pair(pid).provenance.steps if x.id == "render"][0]
    assert s.role == "renderer" and s.model.startswith("bedrock/") and "+" in s.prompt_version and s.inputs["trace"]
    assert Store(tmp_path).pair(pid).trace == "trace.json"


def test_model_offsets_are_ignored(tmp_path):
    st, pid = flip_pair(tmp_path)
    T = st.scenario(st.pair(pid).trace_scenario)
    base = mock_render_llm(T)

    def llm(role, m, **kw):
        o = json.loads(base(role, m))
        for f in o["facts"]:
            f["quotes"][0]["message"] = 0          # wrong message index: located by search
            f["quotes"][0]["start"] = 999
        return json.dumps(o)
    r = render_trace(T, llm=llm)
    assert len(r["span_map"].entries) == 10 and r["diagnostics"]["coverage"] == 1.0
    e = r["span_map"].entries[0]
    assert e.message != 0


def test_split_and_missing(tmp_path):
    st, pid = flip_pair(tmp_path)
    T = st.scenario(st.pair(pid).trace_scenario)
    base = mock_render_llm(T)

    def llm(role, m, **kw):
        o = json.loads(base(role, m))
        o["facts"][0]["quotes"].append({"message": 2, "quote": o["messages"][2]["content"][:20]})
        o["facts"][1]["quotes"] = [{"message": 1, "quote": "not in the trace at all"}]
        return json.dumps(o)
    r = render_trace(T, llm=llm)
    assert r["diagnostics"]["missing"] == ["F2"] and r["diagnostics"]["coverage"] == 0.9
    assert sum(e.realization == "split" for e in r["span_map"].entries) == 2


def test_rejects_bad_traces_and_retries(tmp_path):
    st, pid = flip_pair(tmp_path)
    T = st.scenario(st.pair(pid).trace_scenario)
    good = mock_render_llm(T)
    calls = []

    def llm(role, m, **kw):
        calls.append(1)
        if len(calls) == 1:
            return "not json"
        return good(role, m)
    assert render_trace(T, llm=llm)["diagnostics"]["coverage"] == 1.0 and len(calls) == 2
    with pytest.raises(RenderError):
        render_trace(T, llm=lambda r, m, **k: json.dumps({"messages": [{"role": "user", "content": "x"}], "facts": []}))

    def leaky(role, m, **kw):
        o = json.loads(good(role, m))
        o["messages"].append({"role": "user", "name": "benchbook", "content": "{{CARD}}"})
        return json.dumps(o)
    with pytest.raises(RenderError):
        render_trace(T, llm=leaky, attempts=1)


def test_diagnostics_flags(tmp_path):
    st, pid = flip_pair(tmp_path)
    T = st.scenario(st.pair(pid).trace_scenario)
    r = render_trace(T, llm=mock_render_llm(T))
    d = r["diagnostics"]
    assert d["near_verbatim"]            # the mock copies fact text word for word: flagged (R5)
    assert "words" in d and "last_fact_is_decisive" in d
