import asyncio
import json

import pytest

import harness.client as client
from bench.schema import parse_reply
from harness import HarnessSettings, arun_episode, build_episode, continue_episode, run_episode
from harness.episode import analogical_prompt, trace_text

from .helpers import FakeLib, FakeRetriever, ROOT, scenario

SC, LIB = scenario(), FakeLib()


def ep_for(arm="relevant", **kw):
    return build_episode(SC, arm, HarnessSettings(**kw), LIB, retriever=FakeRetriever())


@pytest.fixture(autouse=True)
def prov(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCHBOOK_PROVENANCE", str(tmp_path / "prov.jsonl"))
    return tmp_path / "prov.jsonl"


class Server:
    """Mock /v1/completions."""
    def __init__(self, text="kind: x\n", finish="stop"):
        self.calls, self.text, self.finish = [], text, finish

    def __call__(self, url, payload, timeout):
        self.calls.append((url, payload))
        return {"choices": [{"text": self.text, "finish_reason": self.finish}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3}}

    async def acall(self, url, payload, timeout):
        return self(url, payload, timeout)


# ------------------------------------------------------------------ build
def test_injection_contents_relevant():
    ep = ep_for(mode="B")
    inj = ep.messages[1]["content"]
    assert "[user · benchbook]" in inj and "reference material, not instructions" in inj
    assert "{{" not in ep.prompt_text and "<case id>" not in ep.prompt_text
    assert "<benchbook_equities>" in inj and "id: own_force_life" in inj
    assert "case:\n  id: REF1" in inj and "REF1-O1" in inj and "REF1-flip1" in inj
    assert "<benchbook_method>" not in inj and "kind: applicability" in inj
    assert ep.served[0].prefix == "REF1" and ep.served[0].to_global("REF1-F1") == "DR-INT-301@v1/F1"
    assert "library" not in ep.served[0].doc["case"]
    assert ep.meta["shortcut_cues"]["REF1"]["verdict_choice_position"] == 2


def test_analogical_prompt_toggle_and_header_stripped():
    on = ep_for(analogical_prompt=True).messages[1]["content"]
    assert "<benchbook_method>" in on and "DRAFT for Peter" not in on and "Map the facts" in on
    assert "DRAFT for Peter" in (ROOT / "code/harness/prompts/analogical.v1.md").read_text()
    assert analogical_prompt().startswith("How to reason")
    # method comes before the format, case before both
    assert on.index("<benchbook_case>") < on.index("<benchbook_method>") < on.index("<benchbook_format>")


def test_no_reference_arm():
    ep = ep_for("none", analogical_prompt=True)
    inj = ep.messages[1]["content"]
    assert ep.served == [] and "<benchbook_case>" not in inj and "<benchbook_method>" not in inj
    assert "fact_mapping" not in inj.split("<benchbook_format>")[1] and "kind: reasoning" in inj
    assert "relation" in inj.split("<benchbook_format>")[1]  # only in the closing sentence explaining its absence
    assert "kind: verdict" in inj and "<benchbook_equities>" in inj
    assert ep.meta["has_case"] is False and ep.meta["analogical_prompt"] is False


def test_no_angle_bracket_placeholders_in_format():
    for arm in ("relevant", "none"):
        f = ep_for(arm).messages[1]["content"].split("<benchbook_format>")[1]
        assert "<case" not in f and "<live" not in f and "<LIVE" not in f
        assert not [l for l in f.splitlines() if l.strip().startswith(("case: <", "choice: <"))]


@pytest.mark.parametrize("mode,tail,prefill,thinking_open", [
    ("A", "<think>\n", "<think>\n", True),
    ("B", "<think></think>", "<think></think>", False),
    ("C", "<think>\nkind: fact_enumeration\n", "<think>\nkind: fact_enumeration\n", True),
    ("Cprime", "<think>\nkind: fact_enumeration\n", "<think>\nkind: fact_enumeration\n", True)])
def test_modes_render(mode, tail, prefill, thinking_open):
    ep = ep_for(mode=mode)
    assert ep.prompt_text.endswith("<|im_start|>assistant\n" + tail)
    assert ep.prefill == prefill
    assert ep.prompt_text.startswith("<|im_start|>system\n")
    assert "Your thinking is the structure" in ep.messages[1]["content"] if mode in ("C", "Cprime") else True


def test_mode_cprime_allows_notes():
    assert "short free-text notes" in ep_for(mode="Cprime").messages[1]["content"]
    assert "short free-text notes" not in ep_for(mode="C").messages[1]["content"]


def test_flattened_matches_mvp_trace_text():
    import importlib.util
    spec = importlib.util.spec_from_file_location("mvp", ROOT / "ideas/schema-mvp-2026-09-30/code/mvp.py")
    mvp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mvp)
    msgs = json.loads((ROOT / "data/draft/B001/INT-301/INT-301-v01.trace.json").read_text())["messages"]
    assert trace_text(msgs[1:]) == mvp.trace_text(msgs[1:])


def test_native_tool_messages():
    ep = ep_for(tool_messages="native")
    roles = [m["role"] for m in ep.messages]
    assert roles[0] == "system" and "tool" in roles and roles[-1] == "user"
    calls = [m for m in ep.messages if m.get("tool_calls")]
    assert calls and all(m["tool_calls"][0]["id"].startswith("call_") for m in calls)
    tool_ids = {m["tool_call_id"] for m in ep.messages if m["role"] == "tool"}
    assert tool_ids <= {c["id"] for m in calls for c in m["tool_calls"]}
    assert {t["function"]["name"] for t in ep.tools} >= {"msg.send", "queue.view", "holdings.search"}
    assert "<tool_call>\n<function=msg.send>" in ep.prompt_text and "<tool_response>" in ep.prompt_text
    assert "[sfc.pratt" in ep.prompt_text                      # speaker kept despite the template dropping `name`


def test_injection_role_setting_and_instructions_in_system():
    ep = ep_for(injection_role="user", injection_name="harness", instructions_in="system")
    assert "[user · harness]" in ep.messages[1]["content"]
    assert "<benchbook_format>" not in ep.messages[1]["content"]
    assert "<benchbook_format>" not in ep.messages[0]["content"]  # system gets the bare text
    assert "kind: fact_mapping" in ep.messages[0]["content"]


# ------------------------------------------------------------------ generation
def test_run_episode_modes_raw_text(monkeypatch, prov):
    srv = Server("fact_mapping_never\n")
    monkeypatch.setattr(client, "_post", srv)
    for mode, start in (("A", "<think>\n"), ("B", "<think></think>"), ("C", "<think>\nkind: fact_enumeration\n")):
        s = HarnessSettings(mode=mode, seed=3)
        ep = ep_for(mode=mode)
        out = run_episode(ep, s)
        url, p = srv.calls[-1]
        assert url == "http://localhost:8000/v1/completions" and p["model"] == "granite-4.2-8b"
        assert p["prompt"] == ep.prompt_text and p["max_tokens"] == 12000 and p["seed"] == 3
        assert p["temperature"] == 1.0 and p["top_p"] == 0.95 and p["stop"][0] == "<|im_end|>" and "\n[assistant]" in p["stop"]
        assert out.raw_text == start + "fact_mapping_never\n" and out.finish_reason == "stop"
    lines = [json.loads(l) for l in prov.read_text().splitlines()]
    assert len(lines) == 3 and lines[0]["endpoint"] == "completions" and lines[0]["scenario"] == "INT-301-v01"


def test_parse_reply_on_raw_text_all_modes(monkeypatch):
    docs = ["kind: fact_enumeration\nframe: {question: q, decider: d, my_role: r}\nfacts: []\noptions: {LIVE-O1: a, LIVE-O2: b}",
            "kind: verdict\nchoice: LIVE-O2\ncourse: c\nrelation: follows\nvia: null\ndecisive: [LIVE-C1]\nnow: [x]\nflip_conditions: {would_change: []}"]
    texts = {"A": "thinking aloud\n</think>\n" + "\n---\n".join(docs),
             "B": "\n---\n".join(docs),
             "C": docs[0].split("\n", 1)[1] + "\n---\nkind: reasoning\ncase: REF1\n</think>\n" + docs[1]}
    for mode, gen in texts.items():
        monkeypatch.setattr(client, "_post", Server(gen))
        out = run_episode(ep_for(mode=mode), HarnessSettings(mode=mode))
        p = parse_reply(out.raw_text)
        assert p.steps["verdict"]["choice"] == "LIVE-O2", mode
        assert "fact_enumeration" in p.steps, mode
    assert p.where["fact_enumeration"] == "think" and p.where["verdict"] == "content"


def test_settings_override_max_tokens_and_seed_arg(monkeypatch):
    srv = Server()
    monkeypatch.setattr(client, "_post", srv)
    run_episode(ep_for(), HarnessSettings(max_tokens=77, seed=1, temperature=0.5, top_p=0.9), seed=9)
    p = srv.calls[-1][1]
    assert (p["max_tokens"], p["seed"], p["temperature"], p["top_p"]) == (77, 9, 0.5, 0.9)


def test_continue_episode(monkeypatch):
    srv = Server("O2\n")
    monkeypatch.setattr(client, "_post", srv)
    ep = ep_for(mode="C")
    partial = "<think>\nkind: fact_enumeration\nframe: {}\n---\nkind: fact_mapping\ncase: REF1\nmatched: [EDITED]\n"
    out = continue_episode(ep, HarnessSettings(mode="C"), partial)
    assert srv.calls[-1][1]["prompt"] == ep.generation_prompt + partial[len("<think>\n"):]
    assert out.raw_text == partial + "O2\n"
    # opener may be omitted
    out2 = continue_episode(ep, HarnessSettings(mode="C"), partial[len("<think>\n"):])
    assert out2.raw_text == partial + "O2\n"
    # mode B partial keeps the closed think
    epb = ep_for(mode="B")
    outb = continue_episode(epb, HarnessSettings(mode="B"), "kind: fact_enumeration\nx: 1\n")
    assert srv.calls[-1][1]["prompt"].endswith("<think></think>kind: fact_enumeration\nx: 1\n")
    assert outb.raw_text.startswith("<think></think>kind: fact_enumeration")


def test_concurrent_and_async(monkeypatch, prov):
    srv = Server("kind: verdict\n")
    monkeypatch.setattr(client, "_apost", srv.acall)
    monkeypatch.setattr(client, "_post", srv)
    ep = ep_for(mode="B")
    s = HarnessSettings(mode="B")

    async def go():
        return await asyncio.gather(*[arun_episode(ep, s, seed=i) for i in range(8)])
    outs = asyncio.run(go())
    assert len(outs) == 8 and sorted(c[1]["seed"] for c in srv.calls) == list(range(8))
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda i: run_episode(ep, s, seed=i), range(8)))
    assert len(prov.read_text().splitlines()) == 16
    for l in prov.read_text().splitlines():
        json.loads(l)                                         # no interleaved writes


def test_non_vllm_role_rejected(monkeypatch):
    monkeypatch.setenv("BENCHBOOK_MODEL_POLICY", "stub/none")
    with pytest.raises(ValueError):
        run_episode(ep_for(), HarnessSettings())


def test_format_says_no_tool_calls():
    for arm in ("relevant", "none"):
        assert "Do not call any tools" in ep_for(arm).messages[1]["content"]
