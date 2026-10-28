"""build_pair_episode: one prompt builder for eval / SFT / RL / rejection sampling. Fakes only (no server, no judge)."""
import os

import pytest

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HOME", "/data/hf")

from bench.schema import Case, ServedCase  # noqa: E402
from harness import HarnessSettings, ThinLeakError, build_pair_episode  # noqa: E402
from harness.episode import serve_cases  # noqa: E402
from pipeline.solve.fixtures import PDF, flip_pair, journalist_pair  # noqa: E402

from .store_helpers import v24_pair  # noqa: E402

EQ = str(PDF / "equities.yaml")
C = HarnessSettings(mode="C")


def test_episode_from_trace_store_and_card(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, ar=True)
    ep = build_pair_episode(p, st, C)
    t = ep.prompt_text
    assert "<benchbook_equities>" in t and "id: REF1" in t and "REF1-flip1" in t
    assert ep.prefill.endswith("kind: fact_enumeration\n") and t.endswith("kind: fact_enumeration\n")
    assert "<benchbook_method>" in ep.messages[1]["content"] and ep.meta["ar_prompt"] is True
    assert ep.meta["card_view"] == "full" and ep.meta["arm"] == "relevant" and ep.meta["pair"] == p.id
    # the plain harness prompt: no worked examples, no hints
    assert "rationaliz" not in t.lower() and "worked example" not in t.lower()


def test_ar_prompt_follows_pair_and_override(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, ar=False)
    assert "<benchbook_method>" not in build_pair_episode(p, st, C).messages[1]["content"]
    assert "<benchbook_method>" in build_pair_episode(p, st, C, ar_prompt=True).messages[1]["content"]


def test_arm_none_serves_no_card(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, solve=False, split="eval-only", arm="none")
    ep = build_pair_episode(p, st, C)
    assert ep.served == [] and "id: REF1" not in ep.prompt_text and "<benchbook_equities>" in ep.prompt_text
    assert "<benchbook_method>" not in ep.messages[1]["content"]


def test_arm_self_serves_the_trace_scenario(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, solve=False, split="eval-only", arm="self")
    ep = build_pair_episode(p, st, C)
    assert ep.served[0].case_id == p.trace_scenario


def test_equities_off_cell(tmp_path):
    st, p = v24_pair(flip_pair, tmp_path, solve=False)
    ep = build_pair_episode(p, st, C, equities=False)
    assert "<benchbook_equities>" not in ep.prompt_text and ep.meta["equities_on"] is False
    assert "id: REF1" in ep.prompt_text


def test_thin_view_drops_flip_material_and_passes_leak_check(tmp_path):
    st, p = v24_pair(journalist_pair, tmp_path, solve=False)
    full = build_pair_episode(p, st, C, card_view="full")
    thin = build_pair_episode(p, st, C, card_view="thin")
    assert thin.meta["card_view"] == "thin" and thin.served[0].card_view == "thin"
    assert thin.served[0].flip_refs() == []
    case_part = thin.messages[1]["content"]
    assert "flip_conditions" not in case_part.split("<benchbook_case>")[1].split("</benchbook_case>")[0]
    assert len(thin.prompt_text) < len(full.prompt_text)
    # move / irreversible / to never reach the prompt
    assert "irreversible:" not in full.prompt_text.split("<benchbook_case>")[1].split("</benchbook_case>")[0]


def test_thin_leak_fails_loudly(tmp_path, monkeypatch):
    st, p = v24_pair(journalist_pair, tmp_path, solve=False)
    monkeypatch.setattr(ServedCase, "flip_refs", lambda self: ["REF1-flip2"])
    with pytest.raises(ThinLeakError):
        build_pair_episode(p, st, C, card_view="thin")
    build_pair_episode(p, st, C, card_view="full")          # full view is never leak-checked


def test_serve_cases_thin_is_clean_on_real_card():
    from pipeline.solve.fixtures import INT301
    s = serve_cases([Case.load(INT301)], "thin")
    assert s[0].flip_refs() == [] and "flip_conditions" not in s[0].doc["case"]


def test_model_override_goes_to_the_request(monkeypatch, tmp_path):
    import harness.client as client
    st, p = v24_pair(flip_pair, tmp_path, solve=False)
    ep = build_pair_episode(p, st, C)
    seen = {}

    def post(url, payload, timeout):
        seen.update(payload)
        return {"choices": [{"text": "x", "finish_reason": "stop"}], "usage": {}}
    monkeypatch.setattr(client, "_post", post)
    monkeypatch.setenv("BENCHBOOK_PROVENANCE", str(tmp_path / "prov.jsonl"))
    client.run_episode(ep, C.with_(model="sft"))
    assert seen["model"] == "sft"
    client.run_episode(ep, C)
    assert seen["model"] == "granite-4.2-8b"
