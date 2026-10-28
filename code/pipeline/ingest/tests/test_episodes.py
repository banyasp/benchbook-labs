import json

import yaml

from pipeline.ingest import episodes

SPANS = [{"span": f"src:aaaaaaaaaaaa#p1.{i}", "text": f"Paragraph {i}."} for i in range(1, 7)]
SRC = {"id": "SRC1", "domain": "personnel security adjudication", "content_domain": None}


def crit(*fails):
    return {k: {"pass": k not in fails, "note": "n"} for k in episodes.CRITERIA}


def test_find_episodes_passes_and_rejects(tmp_path):
    reply = json.dumps({"candidates": [
        {"decision": "The Administrative Judge decides whether to restore access.", "focus": "f", "span_start": SPANS[0]["span"],
         "span_end": SPANS[3]["span"], "criteria": crit(), "content_domain": "security-clearance", "refusal_sensitivity": "low"},
        {"decision": "The agency chooses a fuze setting.", "focus": "f", "span_start": SPANS[4]["span"], "span_end": SPANS[5]["span"],
         "criteria": crit("in_scope"), "content_domain": "targeting", "refusal_sensitivity": "high"}]})
    out = episodes.find_episodes(SRC, SPANS, lambda r, m, stage=None: reply, tmp_path)
    assert len(out["passed"]) == 1 and out["passed"][0]["n"] == 1 and out["passed"][0]["span_range"][0].endswith("p1.1")
    assert out["rejected"][0]["failed"] == ["in_scope"]
    y = yaml.safe_load((tmp_path / "store/episodes/SRC1.yaml").read_text())
    assert y["episodes"][0]["content_domain"] == "security-clearance" and y["episodes"][0]["refusal_sensitivity"] == "low"
    rows = [json.loads(l) for l in (tmp_path / "store/episodes/rejected.jsonl").read_text().splitlines()]
    assert rows[0]["failed"] == ["in_scope"]


def test_bad_span_retries_and_refusal_recorded(tmp_path):
    bad = json.dumps({"candidates": [{"decision": "d", "focus": "f", "span_start": "src:x#p9.9", "span_end": "src:x#p9.9",
                                      "criteria": crit(), "content_domain": "x", "refusal_sensitivity": "low"}]})
    good = json.dumps({"candidates": []})
    seq = [bad, good]
    calls = []
    out = episodes.find_episodes(SRC, SPANS, lambda r, m, stage=None: calls.append(1) or seq.pop(0), tmp_path)
    assert len(calls) == 2 and out["passed"] == []
    from bench.models import RefusalError

    def refuse(r, m, stage=None):
        raise RefusalError("stop_reason:content_filtered", "", "m", stage)
    out = episodes.find_episodes(SRC, SPANS, refuse, tmp_path)
    assert out["rejected"][0]["failed"] == ["refusal"]
