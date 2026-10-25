"""Real 2b library + real 2c harness (prompt building, request, continuation) with only the HTTP transport and the
judge-dependent scorer faked. No GPU, no vLLM, no network."""
import pytest

from eval import core, faithfulness, run_checkpoint2
from eval.tests.fakes import GOOD, FakeBackend

harness = pytest.importorskip("harness")
library = pytest.importorskip("library")


@pytest.fixture
def real_backend(monkeypatch):
    import harness.client as hc
    seen = []

    def post(url, payload, timeout):
        seen.append(payload)
        text = GOOD[GOOD.index("kind: fact_enumeration"):]
        if payload["prompt"].rstrip().endswith("---"):      # a continuation cut before the verdict
            text = GOOD[GOOD.index("kind: verdict"):]
        return {"choices": [{"text": text + "<|im_end|>", "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7}}

    async def apost(url, payload, timeout):
        return post(url, payload, timeout)
    monkeypatch.setattr(hc, "_post", post)
    monkeypatch.setattr(hc, "_apost", apost)
    from harness import HarnessSettings, build_episode, arun_episode, acontinue_episode, run_episode, continue_episode
    be = core.Backend(build_episode=build_episode, run_episode=run_episode, continue_episode=continue_episode,
                      score_reply=FakeBackend.score_reply, make_settings=HarnessSettings,
                      arun_episode=arun_episode, acontinue_episode=acontinue_episode)
    return be, seen


def test_runner_and_faithfulness_on_real_library(tmp_path, real_backend):
    be, seen = real_backend
    lib = library.Library(root="data")
    argv = ["--run-id", "real", "--results-dir", str(tmp_path), "--samples", "1", "--concurrency", "4",
            "--limit-scenarios", "2", "--data-root", "data"]
    assert run_checkpoint2.main(argv, lib=lib, backend=be, judge=object()) == 0
    rows = core.read_samples(tmp_path / "real" / "samples.jsonl")
    assert not (tmp_path / "real" / "errors.jsonl").exists(), (tmp_path / "real" / "errors.jsonl").read_text()[:800]
    n_items = len(core.enumerate_items(sorted(lib.scenarios(), key=lambda s: s.id)[:2]))
    assert len(rows) == n_items
    assert {r["mode"] for r in rows} == {"A", "B", "C", "Cprime"}
    assert all(r["tokens"]["prompt"] == 5 for r in rows)
    # the seed reaches the request
    assert len({p.get("seed") for p in seen}) > 1
    assert faithfulness.main([str(tmp_path / "real"), "--max-samples", "12", "--data-root", "data"], lib=lib, backend=be) == 0
