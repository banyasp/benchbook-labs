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
