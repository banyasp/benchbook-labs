"""v2.4 store fixtures built on pipeline.solve.fixtures: a pair whose trace lives in the trace store (trace_ref)."""
from bench.schema.pipeline import PairRecord, TraceRecord
from pipeline.render import render_pair
from pipeline.solve import GoldStructure, solve_pair
from pipeline.solve.fixtures import mock_render_llm, synth_reply


def v24_pair(mk, tmp_path, *, solve=True, split="train", arm="relevant", writer="granite-rs", ar=True, tags=()):
    """-> (store, pair). The pair references its trace by trace_ref; legacy pair.trace and pair.span_map are dropped."""
    st, pid = mk(tmp_path)
    p = st.pair(pid)
    T = st.scenario(p.trace_scenario)
    p = render_pair(p, st, llm=mock_render_llm(T))
    g = GoldStructure.build(p, st.scenario(p.case_scenario), T)
    if solve:
        p = solve_pair(p, st, None, n=2, llm=lambda r, m, **k: synth_reply(g))
    tj = st.pair_dir(p.id) / p.trace
    import json
    opts = [T.case.global_id(o) for o in T.case.options]
    rec = TraceRecord(trace_scenario=T.id, split="eval-only", span_map=p.span_map, channels={o: "operator_message" for o in opts})
    st.save_trace(rec, json.loads(tj.read_text()))
    d = p.model_dump(by_alias=True)
    d.update(trace_ref=T.id, trace=None, span_map=None, split=split, arm=arm, writer=writer, ar_prompt=ar,
             tags=list(tags), d=0.3)
    if arm in ('none', 'self'):
        d['case_scenario'] = ''
    if arm == 'none':
        d.update(relation='follows', via=None)
    p2 = PairRecord.model_validate({k: v for k, v in d.items() if v is not None})
    st.save_pair(p2)
    return st, p2
