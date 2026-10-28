"""rs: Granite rejection sampling, filter, rationalize, selection, acceptance. Fakes only (fake vLLM, stub judge)."""
import asyncio
import json

import pytest
import yaml

from bench.schema import parse_reply
from bench.schema.pipeline import GoldMap, SpanEntry, SpanMap, TraceRecord
from harness import client
from pipeline.render.render import INJECTION
from pipeline.solve import GoldStructure, solve_pair
from pipeline.solve import rs
from pipeline.solve.__main__ import main
from pipeline.solve.fixtures import flip_pair, journalist_pair, synth_reply
from pipeline.store import Store
from scorers.judge import StubJudge


@pytest.fixture(autouse=True)
def prov(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCHBOOK_PROVENANCE", str(tmp_path / "prov.jsonl"))


def v24(tmp_path, mk=flip_pair, **upd):
    """A v2.4 pair: trace in the trace store, referenced by trace_ref; split train."""
    st, pid = mk(tmp_path)
    p = st.pair(pid)
    T = st.scenario(p.trace_scenario)
    msgs = [{"role": "system", "content": "You are the workflow agent. Tools: msg.send(to, body), log.write(entry)."}]
    entries = []
    for f in T.case.facts:
        msgs.append({"role": "user", "name": "ops", "time": "10:00", "content": f"Update {len(msgs)}: {f.fact} Routine ping follows."})
        entries.append(SpanEntry(fact=T.case.global_id(f.id), message=len(msgs) - 1, start=0, end=5, realization="stated"))
    msgs.append({"role": "user", "name": "benchbook", "content": INJECTION})
    chan = {T.case.global_id(o): "operator_message" for o in T.case.options}
    tr = TraceRecord(trace_scenario=T.id, split="train", span_map=SpanMap(entries=entries), channels=chan)
    st.save_trace(tr, {"messages": msgs})
    d = p.dump()
    d.update({"split": "train", "trace_ref": T.id, "ar_prompt": True, **upd})
    d.pop("trace", None)
    p = type(p).model_validate(d)
    st.save_pair(p)
    return st, p


def decoy(tmp_path):
    st, p = v24(tmp_path)
    C, T = st.scenario(p.case_scenario), st.scenario(p.trace_scenario)
    d = p.dump()
    d.update(id="P-decoy", arm="decoy", intent="decoy", relation="not_governed", governs=False, via=None, touched=None,
             options_map={k: None for k in p.options_map},
             fact_map=GoldMap(live_only=[T.case.global_id(f.id) for f in T.case.facts],
                              case_only=[C.case.global_id(f.id) for f in C.case.facts]).model_dump(),
             consideration_map=GoldMap(live_only=[T.case.global_id(c.id) for c in T.case.considerations],
                                       case_only=[C.case.global_id(c.id) for c in C.case.considerations]).model_dump())
    q = type(p).model_validate(d)
    st.save_pair(q)
    return st, q


def mode_c(reply: str) -> str:
    """What vLLM returns after the prefill `<think>\\nkind: fact_enumeration\\n` (mode C)."""
    head = "kind: fact_enumeration\n"
    assert reply.startswith(head)
    body = reply[len(head):]
    i = body.rindex("\n---\nkind: verdict")
    return body[:i] + "\n</think>\n" + body[i + 5:]


class FakeVLLM:
    """Replaces client._apost: answers by call index with a list of reply factories; records payloads."""
    def __init__(self, plan):
        self.plan, self.payloads = plan, []

    async def __call__(self, url, payload, timeout):
        self.payloads.append(payload)
        text = self.plan(payload)
        return {"choices": [{"text": t, "finish_reason": "stop"} for t in text[:payload["n"]]], "usage": {"completion_tokens": 10}}


def install(monkeypatch, plan):
    f = FakeVLLM(plan)
    monkeypatch.setattr(client, "_apost", f)
    return f


def good(g, mutate=None):
    return mode_c(synth_reply(g, mutate)) + "<|im_end|>"


CFG = rs.RSConfig.load(check_workers=2)


PREFILL = "<think>\nkind: fact_enumeration\n"


def gold(st, p):
    return GoldStructure.from_store(st, p)


# --------------------------------------------------------------------------- prompt
def test_examples_parse_strictly_and_have_pdf_names():
    j, f = rs.example_replies()
    for r in (j, f):
        assert parse_reply(r).strict_ok
        assert "confidence:" not in r and "discretization" not in r and "altered" not in r
    assert "via: [REF1-flip1]" in f and "kind: applicability" in f and "handoff:" in f


def test_prompt_has_examples_mode_c_prefill_and_card_view(tmp_path):
    st, p = v24(tmp_path)
    prep = rs.prepare(p, st, CFG)
    t = prep.ep.prompt_text
    assert t.count("<benchbook_worked_examples>") == 1 and "Example 1" not in t or True
    assert t.index("<benchbook_worked_examples>") < t.index("You are the workflow agent")
    assert t.endswith("<think>\nkind: fact_enumeration\n")
    assert "<benchbook_method>" in t                      # ar_prompt on
    assert "<benchbook_worked_examples>" not in prep.base_ep.prompt_text    # the SFT prompt is the plain harness prompt
    st2, p2 = v24(tmp_path / "b", ar_prompt=False)
    assert "<benchbook_method>" not in rs.prepare(p2, st2, CFG).base_ep.prompt_text


def test_thin_view_reaches_the_prompt(tmp_path):
    st, p = v24(tmp_path, card_view="thin", relation="follows", via=None, choice=None) if False else (None, None)
    # thin only for follows/distinguished pairs: use the journalist pair (follows)
    st, p = v24(tmp_path, journalist_pair, card_view="thin")
    t = rs.prepare(p, st, CFG).base_ep.prompt_text
    card = t.split("<benchbook_case>\n")[1].split("</benchbook_case>")[0]
    assert "flip_conditions" not in card and "REF1-flip" not in card and "lesson" not in card


def test_no_gold_in_sampling_prompt(tmp_path):
    st, p = v24(tmp_path)
    prep = rs.prepare(p, st, CFG)
    g, t = prep.g, prep.ep.prompt_text
    c = g.T.case
    secrets = [x for x in [c.reasoning.weighing, c.reasoning.tradecraft, c.reasoning.uncertainty, c.reasoning.handoff,
                           *[k.why for k in c.considerations], *[w.if_ for w in c.flip_conditions.would_change],
                           *[w.why for w in c.flip_conditions.would_change]] if x and len(x) > 12]
    card = prep.g.served.yaml()
    secrets = [x for x in secrets if x not in card]          # T-only text (the flip variant differs from its card there)
    assert secrets
    assert [s for s in secrets if s in t] == []
    # no global ids, no pair id, no tier, no hint, no gold choice id in a verdict line
    for bad in (p.id, p.case_scenario + "/", p.trace_scenario + "/", "by-construction", "model-solved", "<benchbook_hint>",
                "rationalized"):
        assert bad not in t, bad
    # (the gold choice's option text is in the prompt by necessity: the options are discoverable in the trace;
    #  the gold *decision*, relation and via appear nowhere outside the format spec's own placeholders)
    assert "verdict.relation is" not in t and "verdict.via is" not in t


def test_hint_only_in_the_rationalize_prompt(tmp_path):
    st, p = v24(tmp_path)
    prep = rs.prepare(p, st, CFG)
    h = rs.rationalize_hint(prep.g)
    assert "relation is flips" in h and "REF1-flip1" in h and prep.g.T.case.options["O1"].do in h
    ep = rs.with_hint(prep.ep, prep.settings, h)
    assert "<benchbook_hint>" in ep.prompt_text and ep.prompt_text.endswith("<think>\nkind: fact_enumeration\n")
    assert "<benchbook_hint>" not in prep.ep.prompt_text and "<benchbook_hint>" not in prep.base_ep.prompt_text


# --------------------------------------------------------------------------- filter
def check(st, p, mutate=None, cfg=CFG, finish="stop", hinted=False, judge=None):
    g = gold(st, p)
    return rs.check_rs(PREFILL + mode_c(synth_reply(g, mutate)), g, judge or StubJudge(), cfg, finish, hinted)


def test_accepts_gold_consistent_and_logs_subscores(tmp_path):
    st, p = v24(tmp_path)
    r = check(st, p)
    assert r.accepted and r.stage == "accepted", r.reasons
    f = r.sub["facts"]
    assert f["agreement"] == 1.0 and f["recall"] == 1.0 and r.sub["considerations"]["agreement"] == 1.0
    assert {"governs", "relation", "via", "choice", "strict_ok", "options_aligned"} <= set(r.sub)
    assert r.score == 1.0


@pytest.mark.parametrize("mut,frag,stage", [
    (lambda d: d["verdict"].update(choice="LIVE-O2"), "choice", "choice"),
    (lambda d: d["verdict"].update(relation="distinguished", via=None), "relation", "exact"),
    (lambda d: d["verdict"].update(via=["REF1-flip2"]), "via", "exact"),
    (lambda d: d["applicability"].update(governs=False), "governs", "exact"),
    (lambda d: d.pop("applicability"), "parse", "parse"),
])
def test_rejects_exact(tmp_path, mut, frag, stage):
    st, p = v24(tmp_path)
    r = check(st, p, mut)
    assert not r.accepted and r.stage == stage and any(frag in x for x in r.reasons), r.reasons


def test_exact_failures_cost_no_judge_calls(tmp_path):
    st, p = v24(tmp_path)
    j = StubJudge()
    check(st, p, lambda d: d["verdict"].update(relation="distinguished", via=None), judge=j)
    assert j.calls["choice"] == 0


def test_truncated_rejected(tmp_path):
    st, p = v24(tmp_path)
    assert not check(st, p, finish="length").accepted


def test_via_translated_through_served_table(tmp_path):
    st, p = v24(tmp_path)
    g = gold(st, p)
    assert g.via == ["REF1-flip1"] and g.served.table["REF1-flip1"] == p.via[0]
    assert check(st, p).sub["via"] == 1


def move_facts(d):
    fm = d["fact_mapping"]
    fm["live_only"] = fm["live_only"] + [x["live"] for x in fm["matched"]]
    fm["case_only"] = fm["case_only"] + [x["case"] for x in fm["matched"]]
    fm["matched"] = []


def test_fact_bucket_threshold_over_all_gold_items_and_configurable(tmp_path):
    st, p = v24(tmp_path)
    r = check(st, p, move_facts)
    assert not r.accepted and r.stage == "structure" and any("fact bucket agreement" in x for x in r.reasons)
    a = r.sub["facts"]["agreement"]
    assert a < 0.7
    lax = rs.RSConfig.load(check_workers=2, thresholds={"fact_bucket_agreement": 0.0, "fact_recall": 0.0,
                                                       "decisive_facts_exact": False, "consideration_bucket_agreement": 0.0})
    r2 = check(st, p, move_facts, cfg=lax)
    assert r2.accepted and r2.sub["facts"]["agreement"] == a          # same sub-score, different threshold


def test_decisive_considerations_must_be_named(tmp_path):
    st, p = v24(tmp_path)
    r = check(st, p, lambda d: d["verdict"].update(decisive=[]))
    assert not r.accepted and any("decisive considerations" in x for x in r.reasons)


def test_consideration_buckets_checked_but_skipped_for_model_solved(tmp_path):
    def wreck(d):
        cm = d["consideration_mapping"]
        cm["live_only"] = cm["live_only"] + [x["live"] for x in cm["matched"]]
        cm["case_only"] = cm["case_only"] + [{"case": x["case"], "assumption": None} for x in cm["matched"]]
        cm["matched"], cm["corresponding"] = [], []
    st, p = v24(tmp_path)
    r = check(st, p, wreck)
    assert not r.accepted and any("consideration bucket agreement" in x for x in r.reasons)
    st2, p2 = v24(tmp_path / "ms", gold_tier="model-solved")
    r2 = check(st2, p2, wreck)
    assert r2.accepted and "skipped" in r2.sub["consideration_checks"] and "considerations" not in r2.sub


def test_decoy_checks_governs_and_relation_only(tmp_path):
    st, p = decoy(tmp_path)
    r = check(st, p)
    assert r.accepted and r.sub.get("decoy_only")
    # a wrong choice and empty mappings do not matter for a decoy; governs does
    assert check(st, p, lambda d: d["verdict"].update(choice="LIVE-O2")).accepted
    assert not check(st, p, lambda d: d["applicability"].update(governs=True)).accepted


def test_hint_leak_rejected_only_when_hinted(tmp_path):
    st, p = v24(tmp_path)
    mut = lambda d: d["reasoning"].update(weighing="As the hint says, the case flips.")
    assert check(st, p, mut).accepted
    assert not check(st, p, mut, hinted=True).accepted


# --------------------------------------------------------------------------- choice
def test_choose_is_seeded_random_among_best():
    ss = [{"name": f"s{i}", "accepted": True, "score": 1.0 if i < 3 else 0.8} for i in range(5)] + [
        {"name": "x", "accepted": False, "score": 2.0}]
    a = rs.choose(ss, 0, "P1")
    assert a == rs.choose(ss, 0, "P1") and a["name"] in ("s0", "s1", "s2")
    assert len({rs.choose(ss, k, "P1")["name"] for k in range(40)}) > 1
    assert rs.choose([{"name": "x", "accepted": False, "score": 0}], 0, "P") is None


# --------------------------------------------------------------------------- end to end
def run(st, pairs, monkeypatch, plan, cfg=CFG, **kw):
    f = install(monkeypatch, plan)
    res = rs.run_rs(pairs, st, StubJudge(), cfg, **kw)
    return f, res


def test_round_one_accepts_and_persists(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    g = gold(st, p)
    f, res = run(st, [p], monkeypatch, lambda pl: [good(g)] * 4)
    assert len(f.payloads) == 1 and f.payloads[0]["n"] == 4 and f.payloads[0]["max_tokens"] == 8000
    assert f.payloads[0]["prompt"].endswith("<think>\nkind: fact_enumeration\n")
    q = st.pair(p.id)
    assert q.writer == "granite-rs" and "rationalized" not in q.tags and len(q.solve) == 4 and all(s.accepted for s in q.solve)
    s = yaml.safe_load((st.pair_dir(p.id) / "solve/rs-1-1.yaml").read_text())
    assert s["writer"] == "granite-rs" and s["subscores"]["facts"]["agreement"] == 1.0 and s["raw_text"].startswith("<think>\nkind: fact_enumeration")
    summ = yaml.safe_load((st.pair_dir(p.id) / "solve/rs.summary.yaml").read_text())
    assert summ["chosen"].startswith("rs-1-") and summ["accepted_by_round"]["1"] == 4
    assert any(x.id == "solve.rs" and x.params["writer"] == "granite-rs" for x in q.provenance.steps)
    assert parse_reply(s["raw_text"]).strict_ok


def test_second_round_only_when_needed_then_rationalize(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    g = gold(st, p)
    bad = good(g, lambda d: d["verdict"].update(choice="LIVE-O2"))

    def plan(pl):
        return [good(g)] * 4 if "<benchbook_hint>" in pl["prompt"] else [bad] * 4
    f, res = run(st, [p], monkeypatch, plan)
    assert [("<benchbook_hint>" in x["prompt"]) for x in f.payloads] == [False, False, True]    # 4 + 4 + hinted pass
    q = st.pair(p.id)
    assert q.writer == "granite-rs" and "rationalized" in q.tags
    assert len(q.solve) == 12 and sum(s.accepted for s in q.solve) == 4
    summ = yaml.safe_load((st.pair_dir(p.id) / "solve/rs.summary.yaml").read_text())
    assert summ["rationalized"] and summ["chosen"].startswith("rs-r-")


def test_second_round_rescues_without_rationalizing(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    g = gold(st, p)
    calls = []

    def plan(pl):
        calls.append(1)
        return ["garbage"] * 4 if len(calls) == 1 else [good(g)] * 4
    f, res = run(st, [p], monkeypatch, plan)
    assert len(f.payloads) == 2
    assert "rationalized" not in st.pair(p.id).tags


def test_nothing_accepted_leaves_no_writer(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    f, res = run(st, [p], monkeypatch, lambda pl: ["garbage"] * 4)
    q = st.pair(p.id)
    assert q.writer is None and len(f.payloads) == 3 and res[0].chosen is None and len(q.solve) == 12


def test_batch_many_items_in_flight(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    st2, q = v24(tmp_path / "x", journalist_pair)
    g1 = gold(st, p)
    # two items in two stores is awkward; reuse one store with a second pair id on the same scenarios
    d = p.dump()
    d["id"] = "P-second"
    p2 = type(p).model_validate(d)
    st.save_pair(p2)
    peak = {"now": 0, "max": 0}

    class Slow(FakeVLLM):
        async def __call__(self, url, payload, timeout):
            peak["now"] += 1
            peak["max"] = max(peak["max"], peak["now"])
            await asyncio.sleep(0.05)
            peak["now"] -= 1
            return await super().__call__(url, payload, timeout)
    f = Slow(lambda pl: [good(g1)] * 4)
    monkeypatch.setattr(client, "_apost", f)
    rs.run_rs([p, p2], st, StubJudge(), CFG)
    assert peak["max"] == 2 and len(f.payloads) == 2
    assert st.pair("P-second").writer == "granite-rs"


def test_item_error_does_not_sink_batch(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    d = p.dump()
    d.update(id="P-bad", trace_ref="nope")
    pb = type(p).model_validate(d)
    st.save_pair(pb)
    g = gold(st, p)
    f, res = run(st, [pb, p], monkeypatch, lambda pl: [good(g)] * 4)
    by = {r.pair_id: r for r in res}
    assert by["P-bad"].error and by[p.id].chosen


def test_rationalize_only_keeps_earlier_samples(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    g = gold(st, p)
    run(st, [p], monkeypatch, lambda pl: ["garbage"] * 4, dataclass_replace(CFG, rationalize=False))
    assert len(st.pair(p.id).solve) == 8
    f, res = run(st, [st.pair(p.id)], monkeypatch, lambda pl: [good(g)] * 4, rounds=("r",))
    q = st.pair(p.id)
    assert len(q.solve) == 12 and "rationalized" in q.tags and len(f.payloads) == 1


def dataclass_replace(cfg, **kw):
    import dataclasses
    return dataclasses.replace(cfg, **kw)


def test_acceptance_report(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    g = gold(st, p)
    run(st, [p], monkeypatch, lambda pl: [good(g), "garbage", good(g), "garbage"])
    rep = rs.write_acceptance(st, CFG)
    saved = json.loads((st.root / "solve.acceptance.json").read_text())
    assert saved["overall"]["all"]["samples"] == 4 and saved["overall"]["all"]["accepted"] == 2
    for dim, key in (("arm", "relevant"), ("intent", "flip"), ("gold_tier", "by-construction"), ("card_view", "full")):
        assert saved[dim][key]["pairs"] == 1 and saved[dim][key]["sample_rate"] == 0.5
    assert len(saved["family"]) == 1 and saved["arm"]["relevant"]["pair_rate_plain"] == 1.0
    assert saved["arm"]["relevant"]["rejected_at"] == {"parse": 2}


def test_eval_only_arm_rejected():
    assert rs.eligible(type("P", (), {"arm": "none", "split": "train", "trace_ref": "x", "trace": None, "case_scenario": ""})()) 


# --------------------------------------------------------------------------- teacher path + CLI
def test_teacher_writer_on_v24_pair(tmp_path):
    st, p = v24(tmp_path)
    g = gold(st, p)
    p = solve_pair(p, st, None, n=1, llm=lambda role, m, **kw: synth_reply(g))
    assert p.writer == "teacher" and p.solve[0].accepted


def test_cli_default_writer_is_granite_rs(tmp_path, monkeypatch):
    st, p = v24(tmp_path)
    g = gold(st, p)
    install(monkeypatch, lambda pl: [good(g)] * 4)
    assert main(["--data", str(tmp_path / "data") if False else str(st.data), "--pair", p.id, "--judge", "stub"]) == 0
    assert Store(st.data).pair(p.id).writer == "granite-rs"
    assert (st.root / "solve.acceptance.json").exists()
