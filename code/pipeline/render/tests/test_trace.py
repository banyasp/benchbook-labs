"""render v3: options as text in channels, span map options, gates, retries, rejected store, CLI (fakes only)."""
import json

import pytest

from pipeline.render import gates
from pipeline.render import channels as chan
from pipeline.render.__main__ import main
from pipeline.render.trace import cards_for, needed, render_many, render_one, render_trace_v3
from pipeline.solve.fixtures import flip_pair
from pipeline.store import Store

SEED = 7


def fake(T, mutate=None, calls=None):
    chs, rec, _ = chan.resolve(T.id, [T.case.global_id(o) for o in T.case.options], SEED)
    ROLE = {"system_scope": 0, "operator_message": 1, "colleague_message": 2, "tool_result": 3, "attached_document": 4}

    def llm(role, messages, **kw):
        if calls is not None:
            calls.append(messages)
        msgs = [{"role": "system", "content": "You are the workflow agent for a desk. Tools: msg.send, log.write. Standing note.\n"},
                {"role": "user", "name": "ops_lead", "time": "09:00", "content": "Morning. Quiet start; nothing else pending.\n"},
                {"role": "user", "name": "desk_peer", "time": "09:10", "content": "Hi from the next desk over.\n"},
                {"role": "tool", "name": "queue.read", "content": "Queue status: green.\n"},
                {"role": "tool", "name": "docs.open", "content": "Memo excerpt follows.\n"},
                {"role": "user", "name": "ops_lead", "time": "09:30", "content": "Please carry on with the routine round.\n"}]
        opts = []
        for i, (oid, o) in enumerate(T.case.options.items()):
            g = T.case.global_id(oid)
            k = ROLE[chs[g]]
            phr = f"Handling item {i + 1} is something this desk has dealt with before."
            opts.append((oid, k, phr))
            msgs[k]["content"] += phr + "\n"
        facts = []
        for f in T.case.facts:
            msgs[3]["content"] += f"Row: {f.fact}\n"
            facts.append({"id": f.id, "realization": "stated", "quotes": [{"message": 3, "quote": f.fact}]})
        recj = None
        if rec:
            q = "I would go with handling item 1 myself."
            msgs[2]["content"] += q + "\n"
            recj = {"option": rec.rpartition("/")[2], "message": 2, "quote": q}
        obj = {"messages": msgs, "facts": facts, "recommendation": recj, "allowed": ["a ping"],
               "options": [{"option": o, "message": k, "quote": p} for o, k, p in opts]}
        if mutate:
            mutate(obj, len(calls or []))
        return json.dumps(obj)
    return llm, chs, rec


def setup(tmp_path):
    st, pid = flip_pair(tmp_path)
    p = st.pair(pid)
    return st, p, st.scenario(p.trace_scenario), st.scenario(p.case_scenario).case


def test_channels_deterministic_and_gold_blind():
    o = ["T/O1", "T/O2", "T/O3"]
    a = chan.assign_channels("T", o, 1)
    assert a == chan.assign_channels("T", list(reversed(o)), 1) and len(set(a.values())) == 3
    recs = [chan.pick_recommended(f"T{i}", o, 1) for i in range(400)]
    assert 0.4 < sum(r is not None for r in recs) / 400 < 0.6
    assert {r for r in recs if r} == set(o)


def test_ok_trace_saved_in_store_with_option_spans(tmp_path):
    st, p, T, C = setup(tmp_path)
    llm, chs, rec = fake(T)
    r = render_one(st, T.id, cards=[C], llm=llm, seed=SEED)
    assert r.diagnostics["status"] == "ok" and all(g["pass"] for g in r.gates.values())
    assert st.has_trace(T.id) and not (st.root / "traces" / "_rejected" / T.id).exists()
    t, tj = st.trace(T.id), st.trace_json(T.id)
    assert t.channels == chs and t.recommended_option == rec and t.seed == SEED
    assert len(t.span_map.options) == len(T.case.options) and len(t.span_map.entries) == len(T.case.facts)
    msgs = tj["messages"]
    for s in t.span_map.options:
        assert s.channel == chs[s.option] and msgs[s.message]["content"][s.start:s.end].startswith("Handling item")
    assert msgs[-1]["name"] == "benchbook"
    if rec:
        assert r.diagnostics["recommendation_span"]["option"] == rec


def test_missing_option_retries_with_feedback_then_passes(tmp_path):
    st, p, T, C = setup(tmp_path)
    calls = []

    def mut(obj, n):
        if n == 1:
            obj["options"][0]["quote"] = "words that are nowhere in the trace"
    llm, *_ = fake(T, mut, calls)
    r = render_trace_v3(T, [C], llm=llm, seed=SEED)[0]
    assert r.diagnostics["status"] == "ok" and len(r.diagnostics["attempts"]) == 2
    assert "not found by their quote" in calls[1][-1]["content"]


def test_dropped_after_two_retries_is_saved_as_rejected(tmp_path):
    st, p, T, C = setup(tmp_path)
    calls = []
    llm, *_ = fake(T, lambda o, n: o["options"][0].__setitem__("quote", "nowhere at all"), calls)
    r = render_one(st, T.id, cards=[C], llm=llm, seed=SEED)
    assert len(calls) == 3 and r.diagnostics["status"] == "rejected" and "located" in r.diagnostics["reason"]
    assert not st.has_trace(T.id) and (st.root / "traces" / "_rejected" / T.id / "trace.yaml").exists()
    assert r.span_map.options == [] and r.gates["located"]["options_missing"]


def test_leak_card_menu_names_gates(tmp_path):
    st, p, T, C = setup(tmp_path)

    def run(mut):
        llm, *_ = fake(T, mut)
        import pipeline.render.trace as tr
        old = tr.MAX_RETRIES
        tr.MAX_RETRIES = 0
        try:
            return render_trace_v3(T, [C], llm=llm, seed=SEED)[0]
        finally:
            tr.MAX_RETRIES = old
    # A-part text of a served card in a message
    lesson = " ".join(C.lesson.split()[:12])
    r = run(lambda o, n: o["messages"][5].__setitem__("content", o["messages"][5]["content"] + lesson))
    assert r.gates["leak"]["card_a_parts"] and r.diagnostics["status"] == "rejected"
    # ids and gold id
    r = run(lambda o, n: o["messages"][5].__setitem__("content", "Take O2 per LIVE-F1."))
    assert r.gates["leak"]["ids"]
    # option label copied
    do = T.case.options[T.case.verdict.choice].do
    r = run(lambda o, n: o["messages"][5].__setitem__("content", do))
    assert any(x["gold"] for x in r.gates["leak"]["option_labels"])
    # person name
    r = run(lambda o, n: o["messages"][5].__setitem__("content", "Thanks, Maria Lopez"))
    assert r.gates["names"]["names"]
    # menu: three options in one message
    def menu(o, n):
        c = "\n".join(f"- {x.do}" for x in T.case.options.values())
        o["messages"][5]["content"] = c
        for it in o["options"]:
            it["message"], it["quote"] = 5, T.case.options[it["option"]].do[:30]
    r = run(menu)
    assert r.gates["leak"]["menu"] or r.gates["leak"]["option_labels"]


def test_wrong_channel_and_unrequested_recommendation(tmp_path):
    st, p, T, C = setup(tmp_path)
    llm0, chs, rec = fake(T)

    def mut(o, n):
        for it in o["options"]:                      # push every option into the final user message
            q = it["quote"]
            o["messages"][5]["content"] += q + " "
            it["message"] = 5
    import pipeline.render.trace as tr
    tr.MAX_RETRIES = 0
    try:
        llm, *_ = fake(T, mut)
        r = render_trace_v3(T, [C], llm=llm, seed=SEED)[0]
    finally:
        tr.MAX_RETRIES = 2
    assert r.diagnostics["status"] == "rejected"
    if any(c in ("system_scope", "tool_result") for c in chs.values()):
        assert r.gates["located"]["channel"]


def test_refusal_and_llm_error(tmp_path, monkeypatch):
    st, p, T, C = setup(tmp_path)
    import bench.models as bm

    class RefusalError(Exception):
        pass
    monkeypatch.setattr(bm, "RefusalError", RefusalError, raising=False)

    def refuse(role, m, **kw):
        raise RefusalError("cannot help")
    r = render_trace_v3(T, [C], llm=refuse, seed=SEED)[0]
    assert r.diagnostics["status"] == "rejected" and r.diagnostics["reason"] == "refusal" and r.diagnostics["refusal"]
    n = []

    def flaky(role, m, **kw):
        n.append(1)
        if len(n) < 3:
            raise ConnectionError("throttled")
        return fake(T)[0](role, m)
    sleeps = []
    r = render_trace_v3(T, [C], llm=flaky, seed=SEED, sleep=sleeps.append)[0]
    assert r.diagnostics["status"] == "ok" and len(sleeps) == 2


def test_needed_cards_cli_and_parallel(tmp_path, monkeypatch):
    st, p, T, C = setup(tmp_path)
    assert needed(st) == [T.id] and [c.id for c in cards_for(st, T.id)] == [C.id]
    llm, *_ = fake(T)
    out = render_many(st, [T.id, "no-such"], workers=4, llm=llm, seed=SEED)
    assert out[T.id].diagnostics["status"] == "ok" and isinstance(out["no-such"], Exception)
    assert needed(st) == []
    import pipeline.render.trace as tr
    st2, p2, T2, _ = setup(tmp_path / "b")
    monkeypatch.setattr(tr._models, "complete", fake(T2)[0])
    assert main(["--data", str(tmp_path / "b"), "--all-needed", "--workers", "2", "--seed", str(SEED)]) == 0
    assert Store(tmp_path / "b").has_trace(T2.id)


def test_name_and_menu_helpers():
    m = [{"role": "user", "name": "ops_lead", "content": "Capt. Reyes asked. The Judge Advocate office. Chief Engineer ok."}]
    assert gates.person_names(m) == ["Capt. Reyes"]
    assert gates.person_names([{"role": "user", "name": "john_k", "content": "x"}])
    assert not gates.person_names([{"role": "user", "name": "duty_officer", "content": "The shift supervisor will call."}])
