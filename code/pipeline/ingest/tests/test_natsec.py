import json
from pathlib import Path

import yaml

from pipeline.ingest import natsec
from pipeline.ingest.technique_check import check

EPISODES = Path(natsec.__file__).with_name("sources-natsec.episodes.yaml")
DOCS = natsec.DATA / "docs"


def test_split_long_is_deterministic_and_bounded():
    par = " ".join(f"Sentence number {i} is here." for i in range(200))
    a = natsec.split_long(par)
    assert a == natsec.split_long(par)
    assert all(len(x) <= natsec.MAX_PARA + 40 for x in a)
    assert " ".join(a) == par


def test_html_blocks_drops_menu_and_keeps_pre_paragraphs():
    html = b"<html><body><div id='header'><ul><li>Military Menu</li></ul></div><div id='content'><p>Body one.</p><pre>a\nb\n\nc</pre><p>previous |</p></div></body></html>"
    assert natsec.html_blocks(html) == ["Body one.", "a b", "c"]


def test_episode_file_shape_and_scope():
    e = yaml.safe_load(EPISODES.read_text())
    eps = e["episodes"]
    assert len(eps) >= 15 and len({x["family"] for x in eps}) >= 10
    assert all(x["refusal_sensitivity"] == "high" and x["tier"] == 1 and x["split"] == "test" for x in eps)
    for x in eps:
        assert x["content_domain"] in ("targeting", "operational-command")
        assert set(x["criteria"]) == {1, 2, 3, 4}
        # the decision statement itself must carry no technique
        assert not [f for f in check(x["focus"]) if f.severity == "strip"], x["id"]


def test_episode_spans_resolve_in_normalized_docs():
    e = yaml.safe_load(EPISODES.read_text())
    for x in e["episodes"] + e["rejected"]:
        for sp in x["spans"] + x.get("gold", {}).get("spans", []):
            f = DOCS / f"{sp['doc']}.jsonl"
            if not f.exists():
                continue  # docs are data, not code; skip on a box without them
            ids = [json.loads(l)["span"].split("#")[1] for l in f.read_text().splitlines() if l.strip()]
            assert sp["from"] in ids and sp["to"] in ids and ids.index(sp["from"]) <= ids.index(sp["to"]), (x["id"], sp)
