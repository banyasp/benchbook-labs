"""Offline tests for pipeline.ingest (the model is mocked; no network)."""
import json
import shutil
from pathlib import Path

import pytest

from bench.schema.pipeline import Scenario
from pipeline import store as store_mod
from pipeline.ingest import acquire, extract, importpilot, normalize, registry

REPO = Path(__file__).resolve().parents[4]
SHA = "ab" * 32


# ------------------------------------------------------------------ registry
def test_seed_registry_valid_and_splits():
    src = registry.load_seed()
    assert registry.validate(src, registry.catalog_rows()) == []
    assert len(src) == 4
    sp = registry.assign_splits(registry.families(src))
    assert "dev" in sp.values() and "test" in sp.values() and "train" in sp.values()
    assert sp == registry.assign_splits(list(reversed(registry.families(src))))      # deterministic
    n = sum(len(s["episodes"]) for s in src)
    assert 6 <= n <= 10


def test_registry_rejects_missing_license():
    bad = [dict(registry.load_seed()[0], license="proprietary")]
    assert any("public domain" in e for e in registry.validate(bad))


# ------------------------------------------------------------------ acquire
def test_raw_is_immutable(tmp_path):
    sha = acquire.store_raw(b"hello", {"url": "u"}, tmp_path)
    (tmp_path / sha).write_bytes(b"hello")
    m1 = (tmp_path / f"{sha}.meta.json").read_text()
    assert acquire.store_raw(b"hello", {"url": "other"}, tmp_path) == sha
    assert (tmp_path / f"{sha}.meta.json").read_text() == m1          # meta not rewritten
    assert json.loads(m1)["size"] == 5 and json.loads(m1)["sha256"] == sha


# ------------------------------------------------------------------ normalize
def test_pdf_paragraphs():
    t = "Heading line\n \nA paragraph that wraps\nonto a second line.\n \n- 3 -\n \nNext one."
    assert normalize.split_paragraphs(t) == ["Heading line", "A paragraph that wraps onto a second line.", "Next one."]


XML = b"<DIV6><HEAD>Sub B</HEAD><DIV8><HEAD>\xc2\xa7 1.1 Rule.</HEAD><P>(a) Text <I>italic</I> here.</P><EXAMPLE><HED>Example 1:</HED><PSPACE>An employee may not.</PSPACE></EXAMPLE></DIV8></DIV6>"


def test_xml_and_stable_rerun(tmp_path):
    assert normalize.xml_paragraphs(XML) == ["Sub B", "§ 1.1 Rule.", "(a) Text italic here.", "Example 1: An employee may not."]
    raw = tmp_path / "raw"
    sha = acquire.store_raw(XML, {"url": "x"}, raw)
    p1 = normalize.normalize(sha, "xml", tmp_path)
    b1 = p1.read_bytes()
    p2 = normalize.normalize(sha, "xml", tmp_path)
    assert p2.read_bytes() == b1 and not (tmp_path / "docs" / "versions").exists()      # unchanged => no new version
    spans = normalize.load_spans(sha[:12], tmp_path)
    assert spans[0]["span"] == f"src:{sha[:12]}#p1.1" and len(spans) == 4


# ------------------------------------------------------------------ extract (mock model)
SPANS = [{"span": f"src:{SHA[:12]}#p1.{i}", "text": f"Source paragraph {i}."} for i in range(1, 9)]
SRC = {"id": "T", "url": "https://x/y.pdf", "title": "t", "kind": "k", "license": "public domain", "domain": "d", "family": "FAM",
       "episodes": [{"n": 1, "focus": "decide it"}]}


def fq_reply(bad=False):
    facts = [{"id": f"F{i}", "kind": "situation", "status": "confirmed", "fact": f"Fact {i}.", "spans": [SPANS[i]["span"]]} for i in range(1, 7)]
    opts = {"O1": {"do": "Do the first thing now", "move": "act", "irreversible": True},
            "O2": {"do": "Do the second thing now", "move": "hold"},
            "O3": {"do": "Do the third thing now", "move": "ask"}}
    if bad:
        facts[0]["spans"] = ["src:ffffffffffff#p9.9"]
    return json.dumps({"title": "T", "setting": "s", "decider": "the judge", "agent": "the judge", "agent_role": "decide", "agent_recast": False,
                       "recast_note": "", "situation": "A situation.", "question": "What should the judge do?", "facts": facts,
                       "options": opts, "real_option": "O1", "authored_options": ["O2", "O3"]})


def a_reply(choice):
    eq = "lawful_authority"
    return json.dumps({
        "considerations": [{"id": "C1", "facts": ["F1", "F2"], "equity": eq, "favors": [choice], "weight": "strong", "why": "Because."}],
        "reasoning": {"read": "r", "weighing": "w", "tradecraft": "t", "uncertainty": "u", "handoff": "h",
                      "tempting_wrong": {"option": "O2" if choice != "O2" else "O3", "pull": "p", "why_wrong": "w"}, "rejected": {}},
        "verdict": {"choice": choice, "basis": "recommended", "decisive": ["C1"]}, "basis_statement": "The judge concluded so.",
        "flip_conditions": {"would_change": [{"id": "flip1", "if": "x", "then": "O2" if choice != "O2" else "O3", "why": "y", "origin": "authored", "spans": []}],
                            "would_not_change": [], "watch_for": []},
        "lesson": "l", "limits": "m", "authored": ["lesson"], "equity_gaps": []})


def make_mock(replies):
    calls = []

    def fn(role_name, msgs, stage=None):
        calls.append((stage, msgs))
        return replies.pop(0)(msgs) if callable(replies[0]) else replies.pop(0)
    fn.calls = calls
    return fn


def test_extract_with_retry_and_gate(tmp_path):
    real_holder = {}

    def a_fn(msgs):
        # the real option was relabeled by code; the prompt states it
        import re
        real = re.search(r"real outcome is option (O\d)", msgs[1]["content"]).group(1)
        real_holder["real"] = real
        return a_reply(real)
    mock = make_mock([fq_reply(bad=True), fq_reply(), a_fn])
    s = extract.extract_episode(SRC, SRC["episodes"][0], SPANS, SHA, "dev", mock, data=tmp_path)
    assert [c[0] for c in mock.calls] == ["extract.FQ", "extract.FQ", "extract.A"]        # one retry on FQ
    assert "unknown span" in mock.calls[1][1][-1]["content"]                                 # errors fed back
    assert s.id == "DR-FAM@v1" and s.split == "dev" and s.verdict_tier == "source-endorsed" and s.basis
    assert s.case.verdict.choice == real_holder["real"]
    assert len(s.grounded_facts()) == 6 and s.provenance.steps[0].params["attempts"] == 2
    assert "flip-conditions-authored" in s.tags and "case.flip_conditions.flip1" in s.provenance.authored
    assert {"case.facts", "case.verdict"} <= set(s.provenance.fields)
    assert s.provenance.steps[0].prompt_version.startswith("extract_fq.v1+")
    st = store_mod.Store(tmp_path)
    st.save_scenario(s)
    assert st.scenario(s.id).case.verdict.choice == s.case.verdict.choice
    assert list((tmp_path / "store" / "scenarios" / "FAM" / "extract-logs").glob("*.log.json"))


def test_option_shuffle_is_deterministic_and_tracks_real():
    fq = json.loads(fq_reply())
    a, b = extract.relabel_options(fq, "DR-X@v1"), extract.relabel_options(fq, "DR-X@v1")
    assert a == b and a["options"][a["real_option"]]["do"] == fq["options"]["O1"]["do"]
    positions = {extract.relabel_options(fq, f"DR-{i}@v1")["real_option"] for i in range(30)}
    assert len(positions) == 3                                                            # not pinned to one position


def test_fq_validation_rejects_unmatched_options_and_bad_spans():
    fq = json.loads(fq_reply())
    allowed = {s["span"] for s in SPANS}
    assert extract.validate_fq(fq, allowed) == []
    fq["options"]["O1"]["do"] = "word " * 30
    assert any("not matched" in e for e in extract.validate_fq(fq, allowed))


def test_gate_rejects_ungrounded_fact(tmp_path):
    mock = make_mock([fq_reply(), lambda m: a_reply(__import__("re").search(r"option (O\d)\.", m[1]["content"]).group(1))])
    s = extract.extract_episode(SRC, SRC["episodes"][0], SPANS, SHA, "train", mock, data=tmp_path)
    d = s.dump()
    d["fact_spans"]["F1"] = []
    s2 = Scenario.model_validate(d)
    with pytest.raises(extract.ExtractionError):
        extract.gate(s2)


def test_gives_up_after_three_attempts(tmp_path):
    mock = make_mock(["not json", "{}", "[]"])
    with pytest.raises(extract.ExtractionError):
        extract.extract_episode(SRC, SRC["episodes"][0], SPANS, SHA, "train", mock, data=tmp_path)
    assert len(mock.calls) == 3


# ------------------------------------------------------------------ import-pilot
def test_import_pilot_copies_and_leaves_cases_untouched(tmp_path):
    src = REPO / "data" / "cases"
    dst = tmp_path / "cases"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("versions"))
    before = {p: p.read_bytes() for p in dst.rglob("*.yaml")}
    ids = importpilot.import_pilot(data=tmp_path, root=REPO)
    assert len(ids) == 10
    st = store_mod.Store(tmp_path)
    s = st.scenario("DR-INT-103@v1")
    assert s.split == "eval-only" and s.status == "needs_review" and "eval-only-import" in s.tags and s.verdict_tier == "source-endorsed"
    assert {p: p.read_bytes() for p in dst.rglob("*.yaml")} == before
