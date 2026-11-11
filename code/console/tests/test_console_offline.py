"""Offline tests for the console's data layer, the queue / sign-off records, and the app routes (no model calls).
Writes only to pytest tmp paths (queue and labels are redirected)."""
from __future__ import annotations

import json

import pytest

from console import data as D
from pipeline.ops import queue as Q

ANCHOR = "DR-CORPUS-CHILCOT-NX-249d4566-E44@v1"
RUN = "results/transfer/pilot2-modeA"


def test_queue_roundtrip_and_blindness(tmp_path):
    qd, lab = tmp_path / "q", tmp_path / "l.jsonl"
    case = D.scenario(ANCHOR)["case"]
    with pytest.raises(ValueError):
        Q.enqueue("verdict", {"case": case}, queue=qd)                 # full case = not blind
    blind = Q.blind_case(case)
    assert not {"verdict", "reasoning", "considerations", "flip_conditions"} & set(blind)
    t1 = Q.enqueue("verdict", {"case": blind}, ref=ANCHOR, queue=qd)
    assert Q.enqueue("verdict", {"case": blind}, ref=ANCHOR, queue=qd) == t1       # idempotent
    assert [t["id"] for t in Q.tasks(qd, lab)] == [t1] and Q.tasks(qd, lab)[0]["answer"] is None
    Q.answer(t1, "O1", note="first", labels_path=lab, queue=qd)
    Q.answer(t1, "O2", note="changed my mind", labels_path=lab, queue=qd)
    assert Q.answer_of(t1, lab)["answer"] == "O2" and len(Q.labels(lab)) == 2      # append-only, last wins


def test_signoff_records_history(tmp_path):
    lab = tmp_path / "l.jsonl"
    Q.signoff("run", RUN, "needs-work", "check copies", labels_path=lab)
    Q.signoff("run", RUN, "approve", labels_path=lab)
    s = Q.signoffs(lab)[("run", RUN)]
    assert s["decision"] == "approve" and len(s["history"]) == 2
    with pytest.raises(ValueError):
        Q.signoff("run", RUN, "maybe", labels_path=lab)


def test_scenario_index_and_lineage():
    idx = D.SCEN.get()
    assert len(idx["rows"]) > 1000 and ANCHOR in idx["by_id"]
    derived = next(r for r in idx["rows"] if r.get("parent") and r["parent"] in idx["by_id"])
    chain = D.lineage_chain(derived["id"])
    assert chain[-1]["id"] == derived["id"] and chain[-2]["id"] == derived["parent"]
    assert any(d["id"] == derived["id"] for d in D.descendants(derived["parent"]))
    assert all(r["held_out"] is True for r in D.scenario_rows({"held_out": "true"}))


def test_diffs_and_highlight():
    assert D.word_diff("the team stays", "the team leaves") == "the team <del>stays</del><ins>leaves</ins>"
    diff = D.case_diff({"facts": [{"id": "F1", "fact": "a b"}]}, {"facts": [{"id": "F1", "fact": "a c"}, {"id": "F2", "fact": "x"}]})
    kinds = {x["path"]: x["kind"] for x in diff}
    assert kinds == {"facts[F1].fact": "changed", "facts[F2].fact": "added"}
    h = D.highlight("abc <def> ghi", [{"start": 4, "end": 9, "label": "F1", "kind": "fact", "realization": "stated"}])
    assert "&lt;def&gt;" in h and '<mark class="fact"' in h


def test_trace_and_answer_key():
    t = D.trace(ANCHOR)
    assert t and t["messages"] and any("<mark" in m["html"] for m in t["messages"])
    k = D.answer_key(ANCHOR)
    assert "error" not in k and k["key"]["choice"]


def test_run_views():
    rs = {r["run"]: r for r in D.runs()}
    assert RUN in rs and rs[RUN]["n"] > 0
    res = D.run_results(RUN, max_idx=0)
    assert {r["arm"] for r in res["rows"]} >= {"control", "self", "transfer", "flip", "decoy"} and res["idx"] == [0]
    data = D.run_data(RUN)
    assert data["by_arm"].get("transfer") and data["manifest"] and data["manifest"]["files_checked"] > 0
    ch = D.run_changes(RUN, "results/transfer/pilot2")
    assert ch["prev"] == "results/transfer/pilot2" and any(x["key"] == "mode" for x in ch["config_diff"])
    pu = {p["what"]: p for p in D.prompts_used(D.run_config(RUN))}
    assert "mode line (key A)" in pu and pu["mode line (key A)"]["text"]


def test_docs_are_safe_and_render():
    assert D.safe_path("../../etc/passwd") is None and D.safe_path("config/models.yaml") is None
    html = D.render_md("- a\n  - b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n\n[m](M11-scaffold-ablation.md)",
                       D.ROOT / "measurements" / "README.md")
    assert "<ul>" in html and html.count("<li>") == 2 and '<table class="grid">' in html
    assert 'href="/doc?path=measurements/M11-scaffold-ablation.md"' in html


def test_funnel_and_batches():
    st = {s["stage"]: s for s in D.funnel()}
    assert st["Raw corpus documents"]["count"] > 0 and st["Extracted anchor scenarios"]["count"] > 0
    b = D.batch_detail("filter:op=permute", sample_n=2)
    assert b["n"] >= 1 and len(b["sample"]) <= 2 and b["cues"]


def test_app_routes(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from console.app import app
    lab, qd = tmp_path / "l.jsonl", tmp_path / "q"
    real_signoff, real_signoffs = Q.signoff, Q.signoffs
    monkeypatch.setattr(Q, "signoff", lambda *a, **k: real_signoff(*a, labels_path=lab, **k))
    monkeypatch.setattr(Q, "signoffs", lambda *a, **k: real_signoffs(lab))
    c = TestClient(app)
    for u in ["/", "/funnel", "/scenarios?op=permute", f"/scenario/{ANCHOR}", f"/scenario/{ANCHOR}/trace",
              "/runs", f"/run?run={RUN}", "/measurements", "/prompts", "/operators", "/queue", "/signoff",
              "/batches", "/outstanding", "/search?q=CHILCOT"]:
        assert c.get(u).status_code == 200, u
    r = c.post("/signoff", data={"target_kind": "run", "target_id": RUN, "decision": "approve", "note": "t",
                                 "back": "/runs"}, follow_redirects=False)
    assert r.status_code == 303 and json.loads(lab.read_text().splitlines()[-1])["decision"] == "approve"
    assert c.get("/file?path=config/models.yaml").status_code == 404


def test_pipeline_page_data():
    from console import data as D
    c = D._pipeline_counts()
    assert c["docs"] > 0 and c["anchors"] > 0 and c["episodes"] >= 0
    for y in D.pairs_yields():
        assert y["recipe"].startswith("pairs_v1_") and all("buckets" in s for s in y["steps"])


def test_dataset_pages_data():
    from console import data as D
    tags = D.dataset_tags("pairs-v1")
    if not tags:
        return
    o = D.dataset_overview("pairs-v1", tags[-1], "transfer")
    assert o["anchors"] and set(o["by_arm"]) <= set(D.ARM_INFO) and "drop_option" not in o["by_arm"]
    a = D.dataset_anchor("pairs-v1", tags[-1], o["anchors"][0])
    assert [x["arm"] for x in a["arms"]] == D.ARM_ORDER
    for arm in a["arms"]:
        for s in arm["served"]:
            assert s["cell"]["x1"] == o["anchors"][0] and len(s["hops"]) == len(s["cell"]["chain"]) - 1
