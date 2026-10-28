"""project: SFT / RLVR / Inspect records; they load in training.sft_data and score in scorers (offline)."""
import json
from pathlib import Path

import pytest

from bench.schema import parse_reply
from harness.tests.store_helpers import v24_pair
from pipeline.project import eval_cells, project_all, project_pair, split_for_mode
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
    r = project_pair(p, st, mode="B")["sft"]
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
    out = project_pair(p, st, EQ, mode="B")
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
    o2 = project_pair(p2, st2, mode="B")
    s2 = score_reply(parse_reply(o2["sft"]["completion"]), to_key(o2["rl"]["answer_key"]), to_served(o2["rl"]["served"]), StubJudge())
    assert s2["verdict_choice"] == 1 and s2["relation"] == 1 and s2["via_match"] == 1 and s2["via_consistent"] == 1


def test_mode_is_required_no_silent_default(tmp_path):
    st, p, g = solved(flip_pair, tmp_path)
    with pytest.raises(TypeError):
        project_pair(p, st)
    with pytest.raises(ValueError):
        project_pair(p, st, mode="A")
    with pytest.raises(TypeError):
        project_all(st, "v0")


def test_sft_export_mode_c_meta_and_plain_prompt(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, split="train", tags=("rationalized",))
    m = project_all(st, "v1", mode="C")
    out = st.exports / "v1"
    assert m["mode"] == "C" and m["counts"] == {"sft": 1, "dev": 0, "rl": 1, "eval": 0}
    r = json.loads((out / "sft" / "sft.jsonl").read_text())
    meta = r["meta"]
    for k in ("arm", "card_view", "AR", "writer", "rationalized", "d", "realization", "tier", "intent", "family", "split"):
        assert k in meta, k
    assert meta["arm"] == "relevant" and meta["card_view"] == "full" and meta["AR"] is True and meta["writer"] == "granite-rs"
    assert meta["rationalized"] is True and meta["d"] == 0.3 and meta["tier"] == "by-construction" and meta["mode"] == "C"
    assert "mask_after" not in r and r["prefill"].endswith("kind: fact_enumeration\n")
    assert r["completion"].count("</think>") == 1 and r["prompt_text"].endswith("kind: fact_enumeration\n")
    ok, why = sft_data.verify(r)
    assert ok, why
    assert "<benchbook_method>" in r["messages"][1]["content"]            # AR on for this row
    assert "worked example" not in r["prompt_text"].lower()
    assert json.loads((out / "rl" / "rlvr.jsonl").read_text())["meta"]["arm"] == "relevant"
    # the teacher writer is not in the default export; asking for it includes it
    st2, p2 = v24_pair(flip_pair, tmp_path / "t", split="train", writer="teacher")
    assert project_all(st2, "v1", mode="C")["counts"]["sft"] == 0
    assert project_all(st2, "v1", mode="C", writers=("teacher",))["counts"]["sft"] == 1


def test_decoy_row_carries_mask_after(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, split="train")
    d = p.model_dump(by_alias=True)
    row = project_pair(p, st, mode="C")["sft"]
    assert "mask_after" not in row and sft_data.mask_kind(row) is None
    row["meta"]["arm"] = "decoy"
    assert sft_data.mask_kind(row) == "applicability"


def test_eval_export_cells_and_g(tmp_path):
    st, p = v24_pair(journalist_pair, tmp_path, solve=False, split="eval-only")
    m = project_all(st, "v1", mode="C")
    rows = [json.loads(l) for l in (st.exports / "v1" / "eval" / "inspect.jsonl").read_text().splitlines()]
    assert m["eval_by_cell"] == {"core": 1, "ar_off": 1, "thin": 1, "eq_off": 1}
    by = {r["metadata"]["cell"]: r for r in rows}
    assert by["core"]["metadata"]["AR"] is True and by["ar_off"]["metadata"]["AR"] is False
    assert by["thin"]["metadata"]["card_view"] == "thin" and by["eq_off"]["metadata"]["equities_on"] is False
    assert "<benchbook_equities>" not in by["eq_off"]["prompt_text"] and "<benchbook_method>" not in by["ar_off"]["input"][1]["content"]
    assert len(by["thin"]["prompt_text"]) < len(by["core"]["prompt_text"])
    assert len({r["id"] for r in rows}) == 4
    for r in rows:                                                  # G rides along
        assert to_key(r["metadata"]["answer_key"]).choice == r["target"] and r["prefill"]
        assert to_served(r["metadata"]["served"])
    md = by["core"]["metadata"]
    assert md["trace_relevant_d"] == 0.3 and md["split"] == "eval-only" and md["tier"] == "source-endorsed"
    only_core = project_all(st, "v2", mode="C", eval_cells_="core")
    assert only_core["eval_by_cell"] == {"core": 1}


def test_eval_flip_pair_gets_no_thin_cell(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, solve=False, split="eval-only")
    assert [c["cell"] for c in eval_cells(p)] == ["core", "ar_off", "eq_off"]


def test_family_leak_between_train_and_eval_is_refused(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, split="train")
    ev = p.model_copy(update={"id": "P-eval", "split": "eval-only"})
    st.save_pair(ev)
    with pytest.raises(ValueError, match="share a family"):
        project_all(st, "v1", mode="C")


def test_max_length_report_logs_drops(tmp_path):
    tok()
    st, p = v24_pair(flip_pair, tmp_path, split="train")
    m = project_all(st, "v1", mode="C", max_length=100)
    assert m["max_length_report"]["n_dropped_max_length"] == 1
    assert (st.exports / "v1" / "sft" / "length_report.json").exists()
    assert m["counts"]["sft"] == 1                                   # the row stays in the export; the report says it would drop


def test_none_and_self_arms_export(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, solve=False, split="eval-only", arm="none")
    m = project_all(st, "v1", mode="C")
    r = [json.loads(l) for l in (st.exports / "v1" / "eval" / "inspect.jsonl").read_text().splitlines()]
    assert m["eval_by_cell"] == {"core": 1, "eq_off": 1}               # no AR-off cell: nothing to prompt about
    k = to_key(r[0]["metadata"]["answer_key"])
    assert k.served is None and k.relation is None and k.via is None and k.arm == "none" and k.choice == r[0]["target"]
    assert r[0]["metadata"]["served"] == "[]" and "id: REF1" not in r[0]["prompt_text"]
    st2, p2 = v24_pair(flip_pair, tmp_path / "s", solve=False, split="eval-only", arm="self")
    project_all(st2, "v1", mode="C")
    r2 = json.loads((st2.exports / "v1" / "eval" / "inspect.jsonl").read_text().splitlines()[0])
    assert to_key(r2["metadata"]["answer_key"]).arm == "self" and "id: REF1" in r2["prompt_text"]
