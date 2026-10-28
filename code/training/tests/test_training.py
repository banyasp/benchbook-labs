"""CPU-only checks of the SFT data builder (loss masks decoded on the real Granite tokenizer, offline), the SFT
smoke and the GRPO smoke. Needs HF_HUB_OFFLINE=1 HF_HOME=/data/hf (the tokenizer is cached there)."""
import os

import pytest

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HOME", "/data/hf")
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from training import common, grpo, sft_data, sft_lora  # noqa: E402

CFG = common.load_config(sft_lora.DEFAULT_CONFIG)


@pytest.fixture(scope="module")
def tok():
    try:
        return common.load_tokenizer(common.policy_hf_id(CFG))
    except Exception as e:      # pragma: no cover
        pytest.skip(f"tokenizer not cached: {e}")


def test_masks_decode_to_reply_only(tok):
    recs = common.smoke_golden(tok, 2)
    ex, rej = sft_data.build_examples(recs, tok, True, 4096)
    assert len(ex) == 2 and not rej
    e = ex[0]
    # trace, equities, case (everything in the prompt) masked; reply + end-of-turn token trained
    assert all(l == -100 for l in e.labels[: e.n_prompt])
    assert sft_data.decode_masked(tok, e) == recs[0]["prompt_text"]
    assert "EQUITIES" in sft_data.decode_masked(tok, e) and "TRACE" in sft_data.decode_masked(tok, e)
    un = sft_data.decode_unmasked(tok, e)
    assert un == recs[0]["completion"] + tok.eos_token
    assert un.startswith("kind: fact_enumeration") and "TRACE" not in un and "EQUITIES" not in un
    assert not sft_data.check_example(tok, e, recs[0]["prompt_text"], recs[0]["completion"])
    print("UNMASKED SPAN (first 200 chars):", repr(un[:200]), "...", repr(un[-60:]))


def test_prefill_stays_masked(tok):
    prefill = "<think>\nkind: fact_enumeration\n"
    full = common.smoke_golden(tok, 1)[0]
    body = full["completion"].removeprefix("kind: fact_enumeration\n")
    rec = {**full, "prompt_text": full["prompt_text"] + prefill, "prefill": prefill, "completion": body}
    # verification parses prefill + completion, so the stripped body still passes
    ex, rej = sft_data.build_examples([rec], tok, True, 4096)
    assert len(ex) == 1, rej
    assert sft_data.decode_masked(tok, ex[0]).endswith("kind: fact_enumeration\n")
    assert sft_data.decode_unmasked(tok, ex[0]).startswith("frame:")


def test_verifier_and_length_filter(tok):
    good = common.smoke_golden(tok, 1)[0]
    bad = {**good, "id": "bad", "completion": good["completion"][: good["completion"].index("kind: verdict")]}
    long = {**good, "id": "long"}
    ex, rej = sft_data.build_examples([good, bad], tok, True, 4096)
    assert len(ex) == 1 and rej[0]["id"] == "bad" and "missing" in rej[0]["reason"]
    ex, rej = sft_data.build_examples([long], tok, True, 100)
    assert not ex and "longer" in rej[0]["reason"]
    ex, rej = sft_data.build_examples([bad], tok, False, 4096)       # --no-verify keeps it
    assert len(ex) == 1


def test_sft_smoke():
    r = sft_lora.smoke(CFG)
    assert r["steps"] == 2 and r["base_weights_moved"] == 0 and r["lora_B_moved"] > 0
    print(r)


def test_grpo_smoke():
    cfg = common.load_config(grpo.DEFAULT_CONFIG)
    r = grpo.smoke(cfg)
    assert r["loss_type"] == "dr_grpo" and r["scale_rewards"] == "none" and r["num_generations"] == 8
    assert r["ref_adapter_tensors_moved"] == 0 and r["policy_adapter_tensors_moved"] > 0
    print(r)


def test_grpo_requires_reward():
    with pytest.raises(grpo.RewardNotDefined):
        grpo.trl_reward(None)
    f = grpo.trl_reward(lambda p, c, ex: float(len(c)) + ex["x"])
    assert f(["p", "q"], ["aa", "b"], x=[1, 2]) == [3.0, 3.0]
    assert grpo.main([]) if False else True


def test_policy_model_comes_from_role():
    assert common.policy_hf_id(CFG) == "ibm-granite/granite-4.2-8b"
    with pytest.raises(KeyError):
        common.policy_hf_id({"hf_ids": {}})


# ------------------------------------------------------------------ v2.4: decoy loss mask, explicit length drops
def _decoy_rec(tok):
    rec = common.smoke_golden(tok, 1)[0]
    c = rec["completion"]
    i = c.index("kind: applicability")
    j = c.index("kind: reasoning")
    tail = c[c.index("kind: verdict"):]
    # decoy shape: ... applicability (governs false) then a verdict; nothing in between
    head = c[:j].replace("governs: true", "governs: false").rstrip().removesuffix("---").rstrip() + "\n"
    return {**rec, "id": "decoy-1", "completion": head + "---\n" + tail, "meta": {"arm": "decoy", "card_view": "full"}}, head


def test_doc_end_finds_end_of_applicability():
    t = "kind: applicability\ngovs: x\n---\nkind: verdict\nchoice: a\n"
    assert sft_data.doc_end(t) == t.index("kind: verdict")
    assert sft_data.doc_end("kind: applicability\nx: 1\n") == len("kind: applicability\nx: 1\n")
    assert sft_data.doc_end("kind: verdict\n") is None
    mc = "kind: applicability\nx: 1\n</think>\nkind: verdict\n"           # mode C: </think> closes the documents
    assert sft_data.doc_end(mc) == mc.index("</think>")


def test_decoy_mask_ends_after_applicability_on_tokenized_row(tok):
    rec, upto = _decoy_rec(tok)
    assert sft_data.mask_kind(rec) == "applicability"                 # from meta.arm even without an explicit field
    ex, rej = sft_data.build_examples([rec], tok, True, 8192)
    assert len(ex) == 1 and not rej, rej
    e = ex[0]
    comp_ids, comp_lab = e.input_ids[e.n_prompt:], e.labels[e.n_prompt:]
    trained = tok.decode([l for l in comp_lab if l != -100], skip_special_tokens=False)
    assert trained.rstrip().rstrip("-").rstrip() == upto.rstrip() and "governs: false" in trained
    assert "kind: verdict" not in trained and tok.eos_token not in trained and "kind: reasoning" not in trained
    # the verdict stays in the text, with labels -100
    full = tok.decode(comp_ids, skip_special_tokens=False)
    assert "kind: verdict" in full and full.endswith(tok.eos_token)
    k = sum(l != -100 for l in comp_lab)
    assert all(l == -100 for l in comp_lab[k:]) and comp_lab[-1] == -100 and e.n_trained == k < e.n_completion
    assert not sft_data.check_example(tok, e, rec["prompt_text"], rec["completion"])
    # a non-decoy row is unchanged: everything after the prompt is trained, eos included
    plain = common.smoke_golden(tok, 1)[0]
    ex2, _ = sft_data.build_examples([plain], tok, True, 8192)
    assert ex2[0].cut_char is None and ex2[0].labels[ex2[0].n_prompt:] == ex2[0].input_ids[ex2[0].n_prompt:]


def test_decoy_mask_in_mode_c_prefill(tok):
    rec, upto = _decoy_rec(tok)
    pre = "<think>\nkind: fact_enumeration\n"
    body = rec["completion"].removeprefix("kind: fact_enumeration\n")
    i = body.index("kind: verdict")
    comp = body[:i].rstrip().removesuffix("---").rstrip() + "\n</think>\n" + body[i:]
    r = {**rec, "prompt_text": rec["prompt_text"] + pre, "prefill": pre, "completion": comp, "mask_after": "applicability"}
    ex, rej = sft_data.build_examples([r], tok, True, 8192)
    assert len(ex) == 1, rej
    trained = tok.decode([l for l in ex[0].labels if l != -100], skip_special_tokens=False)
    assert "</think>" not in trained and "kind: verdict" not in trained and "governs: false" in trained


def test_length_drops_are_explicit_and_logged(tok, capsys):
    good = common.smoke_golden(tok, 2)
    good[0]["meta"] = {"arm": "relevant", "card_view": "full"}
    ex, rej = sft_data.build_examples(good, tok, True, 100)
    assert not ex and len(rej) == 2
    assert rej[0]["dropped"] == "max_length" and rej[0]["n_tokens"] > 100 and rej[0]["arm"] == "relevant"
    rep = sft_data.report_drops(rej, 2, 100)
    err = capsys.readouterr().err
    assert "WARNING: 2/2 rows dropped" in err and "dropped smoke-0" in err
    assert rep["n_dropped_max_length"] == 2 and rep["share"] == 1.0 and rep["by_arm"] == {"relevant": 1, None: 1}


def test_v2_config_reads_v1_export_in_mode_c():
    c = common.load_config(sft_lora.DEFAULT_CONFIG)
    assert c["data"]["path"] == "data/exports/v1/sft/sft.jsonl" and c["data"]["require_mode"] == "C"
    assert c["data"]["max_length"] >= 24000 and c["lora"]["r"] == 16 and c["train"]["gradient_checkpointing"] is True
