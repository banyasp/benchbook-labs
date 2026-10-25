"""project: SFT / RLVR / Inspect records; they load in training.sft_data and score in scorers (offline)."""
import json
from pathlib import Path

import pytest

from bench.schema import parse_reply
from pipeline.project import project_all, project_pair, split_for_mode
from pipeline.render import render_pair
from pipeline.solve import GoldStructure, solve_pair
from pipeline.solve.fixtures import PDF, flip_pair, journalist_pair, mock_render_llm, synth_reply
from scorers import StubJudge, score_reply
from scorers.trl_adapter import RewardScorer, reward_funcs, to_key, to_served
from training import sft_data

EQ = str(PDF / "equities.yaml")


def solved(mk, tmp_path, equities=None):
    st, pid = mk(tmp_path)
    p = st.pair(pid)
    T = st.scenario(p.trace_scenario)
    p = render_pair(p, st, llm=mock_render_llm(T))
    g = GoldStructure.build(p, st.scenario(p.case_scenario), T)
    p = solve_pair(p, st, equities, n=2, llm=lambda r, m, **k: synth_reply(g))
    return st, p, g


def tok():
    try:
        return sft_data and __import__("transformers").AutoTokenizer.from_pretrained("ibm-granite/granite-4.2-8b")
    except Exception:
        pytest.skip("granite tokenizer not available offline")


def test_sft_record_loads_with_target_only_loss(tmp_path):
    st, p, g = solved(flip_pair, tmp_path)
    r = project_pair(p, st)["sft"]
    assert set(r) >= {"id", "prompt_text", "completion", "prefill", "meta", "messages"}
    # prompt = what the harness shows: injected card with equities, served REF1, format, trace; no gold
    pt = r["prompt_text"]
    assert "<benchbook_equities>" in pt and "id: REF1" in pt and "kind: fact_enumeration" in pt
    assert "LIVE-F1" not in r["messages"][1]["content"].split("<benchbook_format>")[0]
    ok, why = sft_data.verify(r)
    assert ok, why
    t = tok()
    ex, rej = sft_data.build_examples([r], t, True, 40000)
    assert len(ex) == 1 and not rej
    assert sft_data.check_example(t, ex[0], r["prompt_text"], r["completion"]) == []
    assert all(l == -100 for l in ex[0].labels[:ex[0].n_prompt]) and ex[0].n_completion > 100


def test_mode_c_splits_think(tmp_path):
    st, p, g = solved(flip_pair, tmp_path)
    r = project_pair(p, st, mode="C")["sft"]
    assert r["prefill"].endswith("kind: fact_enumeration\n") and r["completion"].count("</think>") == 1
    assert r["completion"].split("</think>")[1].lstrip().startswith("kind: verdict")
    ok, why = sft_data.verify(r)
    assert ok, why
    with pytest.raises(ValueError):
        split_for_mode("x", "A", "")


def test_rlvr_record_scores_with_stub_judge(tmp_path):
    st, p, g = solved(journalist_pair, tmp_path, EQ)
    out = project_pair(p, st, EQ)
    rl, sft = out["rl"], out["sft"]
    assert set(rl) >= {"prompt", "answer_key", "served", "gold", "tables"}
    assert "why" not in json.dumps(rl["gold"]) and "reasoning" not in rl["gold"]
    key = to_key(rl["answer_key"])
    assert key.relation == "follows" and key.choice == "LIVE-O3" and key.served == "DR-PDF-001@v1"
    parsed = parse_reply(sft["completion"])
    s = score_reply(parsed, key, to_served(rl["served"]), StubJudge())
    assert s["verdict_choice"] == 1 and s["relation"] == 1 and s["governs"] == 1 and s["schema_valid"] == 1
    # TRL columns: the reward functions accept the row as-is
    f = reward_funcs(StubJudge(), ["verdict_choice", "relation"])
    assert [fn([rl["prompt"]], [sft["completion"]], answer_key=[rl["answer_key"]], served=[rl["served"]]) for fn in f] == [[1.0], [1.0]]
    # flip: via
    st2, p2, g2 = solved(flip_pair, tmp_path / "f")
    o2 = project_pair(p2, st2)
    s2 = score_reply(parse_reply(o2["sft"]["completion"]), to_key(o2["rl"]["answer_key"]), to_served(o2["rl"]["served"]), StubJudge())
    assert s2["verdict_choice"] == 1 and s2["relation"] == 1 and s2["via_match"] == 1 and s2["via_consistent"] == 1


def test_inspect_sample_and_manifest(tmp_path):
    st, p, g = solved(flip_pair, tmp_path)
    m = project_all(st, "v0")
    out = st.exports / "v0"
    assert m["counts"] == {"sft": 1, "rl": 1, "eval": 1} and m["by_intent"] == {"flip": 1}
    ev = json.loads((out / "eval" / "inspect.jsonl").read_text().splitlines()[0])
    assert ev["target"] == "LIVE-O1" and ev["input"][-1]["role"] == "user"
    assert to_key(ev["metadata"]["answer_key"]).via and to_served(ev["metadata"]["served"])
    assert m["input_sha256"] and m["file_sha256"]["sft"] and m["settings"]["mode"] == "B"
    project_all(st, "v0")                                   # second run keeps the first
    assert list((out / "sft" / "versions").glob("*.jsonl"))
    # a pair without an accepted sample is skipped, not projected
    p.solve[0].accepted = p.solve[1].accepted = False
    st.save_pair(p)
    assert project_all(st, "v1")["skipped"][0]["reason"] == "no accepted sample"
