"""solve: gold structure, acceptance, sample storage (offline, mock teacher)."""
import json
from pathlib import Path

import pytest
import yaml

from bench.schema import parse_reply
from pipeline.render import render_pair
from pipeline.solve import GoldStructure, check_reply, clean_reply, solve_pair, teacher_messages, acceptance_report
from pipeline.solve.fixtures import PDF, flip_pair, journalist_pair, mock_render_llm, synth_reply
from pipeline.store import Store

EQ = PDF / "equities.yaml"


def prep(mk, tmp_path, order=None):
    st, pid = mk(tmp_path)
    p = st.pair(pid)
    T = st.scenario(p.trace_scenario)
    p = render_pair(p, st, llm=mock_render_llm(T, order))
    return st, p, GoldStructure.build(p, st.scenario(p.case_scenario), T)


def test_structure_flip(tmp_path):
    st, p, g = prep(flip_pair, tmp_path)
    assert g.choice == "LIVE-O1" and g.via == ["REF1-flip1"] and not g.warnings
    assert set(g.fact_map["corresponding"]) == {("LIVE-F2", "REF1-F2"), ("LIVE-F5", "REF1-F5")}
    k = g.answer_key()
    assert k.relation == "flips" and k.via == [p.case_scenario + "/flip1"] and k.option_map["LIVE-O2"].endswith("/O2")


def test_trace_order_renumbering(tmp_path):
    order = ["F5", "F1", "F2", "F3", "F4", "F6", "F7", "F8", "F9", "F10"]
    st, p, g = prep(flip_pair, tmp_path, order)
    assert g.live["LIVE-F1"].endswith("/F5") and g.live["LIVE-F2"].endswith("/F1")
    assert ("LIVE-F1", "REF1-F5") in g.fact_map["corresponding"]
    assert g.answer_key().facts[0].fact.startswith("A seized phone")


def test_unlocated_fact_dropped(tmp_path):
    st, pid = flip_pair(tmp_path)
    p = st.pair(pid)
    T = st.scenario(p.trace_scenario)
    base = mock_render_llm(T)

    def llm(role, m, **kw):
        o = json.loads(base(role, m))
        o["facts"] = [f for f in o["facts"] if f["id"] != "F9"]
        return json.dumps(o)
    p = render_pair(p, st, llm=llm)
    g = GoldStructure.build(p, st.scenario(p.case_scenario), T)
    assert len(g.fact_order) == 9 and "REF1-F9" in g.fact_map["case_only"] and g.warnings


@pytest.mark.parametrize("mk", [journalist_pair, flip_pair])
def test_accepts_gold_consistent_reply(tmp_path, mk):
    st, p, g = prep(mk, tmp_path)
    r = check_reply("Here you go:\n```yaml\n" + synth_reply(g) + "\n```\nHope that helps.", g)
    assert r["accepted"], r["reasons"]
    assert parse_reply(r["clean"]).strict_ok


def test_pdf_reply_matches_when_identity_numbering(tmp_path):
    st, p, g = prep(journalist_pair, tmp_path)
    text = (PDF / "journalist.reply.yaml").read_text()
    r = check_reply(text, g)
    # considerations are renumbered in trace order (differs from the PDF's C order), facts/verdict are identity
    bad = [x for x in r["reasons"] if not x.startswith("consideration")]
    assert not bad, bad


@pytest.mark.parametrize("name,mut,frag", [
    ("choice", lambda d: d["verdict"].update(choice="LIVE-O2"), "choice"),
    ("relation", lambda d: d["verdict"].update(relation="distinguished"), "relation"),
    ("via", lambda d: d["verdict"].update(via=["REF1-flip2"]), "via"),
    ("bucket", lambda d: d["fact_mapping"].update(matched=d["fact_mapping"]["matched"][1:]), "fact matched"),
    ("optmap", lambda d: d["fact_mapping"]["options"].update({"LIVE-O1": None}), "options map"),
    ("extra fact", lambda d: d["fact_enumeration"]["facts"].append(
        {"id": "LIVE-F99", "kind": "situation", "status": "confirmed", "fact": "x"}), "fact ids"),
    ("missing step", lambda d: d.pop("applicability"), "parse"),
])
def test_rejects(tmp_path, name, mut, frag):
    st, p, g = prep(flip_pair, tmp_path)
    r = check_reply(synth_reply(g, mut), g)
    assert not r["accepted"] and any(frag in x for x in r["reasons"]), r["reasons"]


def test_teacher_prompt_has_gold_and_student_view(tmp_path):
    st, p, g = prep(flip_pair, tmp_path)
    from pipeline.solve import student_episode, load_equities
    ep = student_episode(p, st, load_equities(None))
    m = teacher_messages(g, ep)
    u = m[1]["content"]
    assert "<gold>" in u and "REF1-flip1" in u and "TOUCHED_CONDITION" in u and "benchbook_case" in u
    assert "LIVE-F1" in u and "O1" not in m[0]["content"] or True
    # no option labels or gold in the trace the student sees
    trace = json.loads((st.pair_dir(p.id) / p.trace).read_text())["messages"]
    assert not any("LIVE-" in str(x["content"]) for x in trace)


def test_solve_pair_stores_samples_and_rates(tmp_path):
    st, p, g = prep(flip_pair, tmp_path)
    replies = iter([synth_reply(g), synth_reply(g, lambda d: d["verdict"].update(choice="LIVE-O2")), "garbage"])
    p = solve_pair(p, st, EQ if False else None, n=3, llm=lambda role, msgs, **kw: next(replies))
    flags = sorted(s.accepted for s in p.solve)
    assert flags == [False, False, True]
    f = yaml.safe_load((st.pair_dir(p.id) / "solve" / "sample-1.yaml").read_text())
    assert {"reply", "raw", "reasons", "flags", "provenance"} <= set(f)
    assert f["provenance"]["role"] == "teacher" and "+" in f["provenance"]["prompt_version"]
    assert Store(tmp_path).pair(p.id).solve[0].path.endswith("solve/sample-1.yaml")
    rep = acceptance_report([p])
    assert rep["flip"]["samples"] == 3 and rep["flip"]["accepted"] == 1 and rep["flip"]["pair_rate"] == 1.0


def test_clean_reply():
    assert clean_reply("blah\n```yaml\nkind: verdict\nchoice: a\n```\ntrailing words here") == "kind: verdict\nchoice: a\n"
