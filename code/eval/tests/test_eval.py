"""Offline end-to-end tests of the Checkpoint 2 runners, faithfulness, stats and report (fakes, tmp results dir)."""
import asyncio
import json

import pytest

from bench.schema import parse_reply
from eval import core, faithfulness, report, run_checkpoint2, stats
from eval.tests.fakes import GOOD, FakeBackend, FakeLib


def run(tmp_path, extra=(), backend=None, run_id="t1"):
    be = backend or FakeBackend()
    argv = ["--run-id", run_id, "--results-dir", str(tmp_path), "--samples", "2", "--concurrency", "4", *extra]
    assert run_checkpoint2.main(argv, lib=FakeLib(), backend=be.backend, judge=object()) == 0
    return be, tmp_path / run_id


def test_grid_and_counts(tmp_path):
    lib = FakeLib()
    items = core.enumerate_items(lib.scenarios())
    # S1: 4 arms, S2: 2 arms  x 2 prompts x 4 modes
    assert len(items) == (4 + 2) * 2 * 4 == 48
    assert core.total_samples(items, 5) == 240
    assert len({core.sample_seed(0, items[0], i) for i in range(50)}) == 50
    assert core.sample_seed(0, items[0], 1) == core.sample_seed(0, items[0], 1)


def test_runner_end_to_end_and_resume(tmp_path):
    be, rd = run(tmp_path)
    rows = core.read_samples(rd / "samples.jsonl")
    assert len(rows) == 48 * 2 == be.calls
    r = rows[0]
    for k in ("scenario", "family", "arm", "analogical_prompt", "mode", "sample_idx", "seed", "scores", "parsed_choice",
              "gold_choice", "relation", "via", "tokens", "seconds", "finish_reason", "format", "perturbation", "raw_path",
              "copy_baseline", "cues"):
        assert k in r, k
    assert r["perturbation"]["touched_by_kind"] == {"fact": 2, "consideration": 1}
    assert (rd / r["raw_path"]).exists()
    assert (rd / "manifest.json").exists()
    assert any(x["format"]["strict_ok"] for x in rows) and any(not x["format"]["strict_ok"] for x in rows)
    cb = [x for x in rows if x["arm"] == "relevant"][0]["copy_baseline"]
    assert cb == {"available": True, "choice": "LIVE-O3", "correct": True, "case_choice": "DR-PDF-001@v1/O1"}
    assert [x for x in rows if x["arm"] == "decoy"][0]["copy_baseline"]["available"] is False
    # resume: nothing re-run
    be2, _ = run(tmp_path)
    assert be2.calls == 0
    assert len(core.read_samples(rd / "samples.jsonl")) == 96


def test_resume_after_partial(tmp_path):
    be, rd = run(tmp_path, ["--modes", "B", "--arms", "relevant"])
    n = len(core.read_samples(rd / "samples.jsonl"))
    assert n == 2 * 2 * 2          # 2 scenarios x 2 prompts x 2 samples
    # kill-like truncation: drop the last line, add a torn one
    lines = (rd / "samples.jsonl").read_text().splitlines()
    (rd / "samples.jsonl").write_text("\n".join(lines[:-1]) + '\n{"torn":')
    be2, _ = run(tmp_path, ["--modes", "B", "--arms", "relevant"])
    assert be2.calls == 1


def test_errors_are_retried(tmp_path):
    be = FakeBackend()
    orig = be.run_episode
    boom = {"n": 0}

    def flaky(ep, st, role="policy"):
        boom["n"] += 1
        if boom["n"] == 1:
            raise RuntimeError("vllm down")
        return orig(ep, st, role)
    be.backend.run_episode = flaky
    _, rd = run(tmp_path, ["--modes", "B", "--arms", "relevant", "--prompts", "on"], backend=be)
    assert (rd / "errors.jsonl").exists()
    assert len(core.read_samples(rd / "samples.jsonl")) == 3
    run(tmp_path, ["--modes", "B", "--arms", "relevant", "--prompts", "on"])
    assert len(core.read_samples(rd / "samples.jsonl")) == 4


def test_inspect_task_same_jsonl(tmp_path):
    from eval import checkpoint2
    be = FakeBackend()
    argv = ["--run-id", "insp", "--results-dir", str(tmp_path), "--samples", "2", "--concurrency", "4",
            "--modes", "A", "B", "--arms", "relevant", "none"]
    assert checkpoint2.main(argv, lib=FakeLib(), backend=be.backend, judge=object()) == 0
    rows = core.read_samples(tmp_path / "insp" / "samples.jsonl")
    # S1: none, relevant; S2: none, relevant -> 4 arms-scenarios x 2 prompts x 2 modes x 2 samples
    assert len(rows) == 4 * 2 * 2 * 2
    assert be.calls == len(rows)
    # resume through Inspect too
    be2 = FakeBackend()
    checkpoint2.main(argv, lib=FakeLib(), backend=be2.backend, judge=object())
    assert be2.calls == 0


def test_text_surgery_roundtrip():
    sp = faithfulness.doc_spans(GOOD)
    assert [s["kind"] for s in sp] == ["fact_enumeration", "fact_mapping", "consideration_enumeration",
                                       "consideration_mapping", "applicability", "reasoning", "verdict"]
    e = faithfulness.edit_weight_flip(GOOD, "LIVE-C1")
    p = parse_reply(e)
    assert p.steps["consideration_enumeration"]["considerations"][0]["weight"] == "weak"
    assert "consideration_enumeration" in p.models      # still validates
    assert p.steps["verdict"]["choice"] == "LIVE-O3"      # nothing else touched
    e = faithfulness.edit_move_matched(GOOD, "LIVE-C1", "case_only")
    m = parse_reply(e).steps["consideration_mapping"]
    assert all(x["live"] != "LIVE-C1" for x in m["matched"]) and "REF1-C1" in [
        c if isinstance(c, str) else c["case"] for c in m["case_only"]]
    e = faithfulness.edit_move_matched(GOOD, "LIVE-C1", "live_only")
    assert "LIVE-C1" in parse_reply(e).steps["consideration_mapping"]["live_only"]
    cut = faithfulness.apply("weight_flip", GOOD, "LIVE-C1", "verdict")
    assert "kind: verdict" not in cut and cut.rstrip().endswith("---")
    assert faithfulness.apply("weight_flip", GOOD, "LIVE-C99", "verdict") is None
    cut = faithfulness.apply("swap_revised", GOOD, "LIVE-C1", "verdict")
    assert "kind: fact_mapping" not in cut and "kind: fact_enumeration" in cut
    cut = faithfulness.apply("control", GOOD, "LIVE-C1", "edit")
    assert cut.rstrip().endswith("---") and "kind: fact_mapping" not in cut


def test_faithfulness_end_to_end(tmp_path):
    be, rd = run(tmp_path, ["--arms", "relevant", "augmented", "--modes", "A", "B", "C", "Cprime"])
    be.cont_calls.clear()
    assert faithfulness.main([str(rd), "--max-samples", "40", "--concurrency", "4"], lib=FakeLib(), backend=be.backend) == 0
    rows = core.read_samples(rd / "faithfulness.jsonl")
    assert rows
    by = {}
    for r in rows:
        by.setdefault(r["intervention"], []).append(r)
    assert set(by) == set(faithfulness.INTERVENTIONS)
    assert all(not r["changed"] for r in by["control"] if r["changed"] is not None)
    for iv in ("weight_flip", "to_case_only", "to_live_only", "swap_revised"):
        assert by[iv] and all(r["changed"] for r in by[iv] if r["changed"] is not None), iv
    assert all(r["scenario"] == "S1-v01" for r in by["swap_revised"])
    summ = json.loads((rd / "faithfulness_summary.json").read_text())
    assert summ["B|weight_flip"]["mean"] == 1.0 and summ["B|control"]["mean"] == 0.0
    # idempotent
    n = len(rows)
    faithfulness.main([str(rd), "--max-samples", "40"], lib=FakeLib(), backend=be.backend)
    assert len(core.read_samples(rd / "faithfulness.jsonl")) == n


def test_stats_bootstrap_by_family():
    rows = ([{"family": "F1", "v": 1.0}] * 10 + [{"family": "F2", "v": 0.0}] * 10)
    c = stats.family_bootstrap(rows, lambda r: r["v"], 500)
    assert c["mean"] == 0.5 and c["n_families"] == 2 and c["lo"] == 0.0 and c["hi"] == 1.0   # two families: CI is wide
    rows2 = [{"family": f"F{i}", "v": float(i % 2)} for i in range(40)] * 5
    c2 = stats.family_bootstrap(rows2, lambda r: r["v"], 500)
    assert 0.3 < c2["lo"] < 0.5 < c2["hi"] < 0.7
    a = [{"family": f"F{i}", "v": 1.0} for i in range(10)]
    b = [{"family": f"F{i}", "v": 0.0} for i in range(10)]
    d = stats.family_bootstrap_diff(a, b, lambda r: r["v"], 200)
    assert d["diff"] == 1.0 and d["lo"] == 1.0


def test_report_and_cues(tmp_path):
    _, rd = run(tmp_path)
    s = stats.summarize(core.read_samples(rd / "samples.jsonl"), 100)
    assert s["copy_baseline"]["relevant"]["acc_translatable"]["mean"] == 1.0
    assert s["cues"]["gold_position_counts"] == {2: 6}
    assert any("option #3" in f for f in s["cues"]["flags"])    # gold is always option 3 in the fake
    out = tmp_path / "RESULTS-test.md"
    assert report.main([str(rd), "--out", str(out), "--n-boot", "100"]) == 0
    md = out.read_text()
    for h in ("Choice accuracy", "Format compliance", "Options enumerated", "Relation and `via`", "Tokens and time",
              "Falsification", "Faithfulness", "Shortcut cues", "A  thinking on", "C'  structure"):
        assert h in md, h
    report.main([str(rd), "--out", str(out), "--n-boot", "100"])
    assert (tmp_path / "versions").exists()
