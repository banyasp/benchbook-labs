"""2a reference tests: the PDF v0.4 worked example must load, serve with the PDF's ids, and parse in every mode."""
from pathlib import Path

import pytest
import yaml

from bench.schema import AnswerKey, Case, EquitySet, parse_reply

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "pdf_example"
ROOT = Path(__file__).resolve().parents[3]
REPLY = (FIX / "journalist.reply.yaml").read_text()


def body(text):
    """The reply without its leading comment lines."""
    return "\n".join(ln for ln in text.splitlines() if not ln.startswith("#"))


# ------------------------------------------------------------------ case + equities
def test_case_loads_and_serves_with_pdf_ids():
    case = Case.load(FIX / "REF1.case.yaml")
    view = case.serve("REF1")
    c = view.doc["case"]
    assert c["id"] == "REF1"
    assert list(c["options"]) == ["REF1-O1", "REF1-O2", "REF1-O3"]
    assert [f["id"] for f in c["facts"]][:2] == ["REF1-F1", "REF1-F2"]
    assert c["considerations"][0] == {"id": "REF1-C1", "facts": ["REF1-F2", "REF1-F3", "REF1-F4"],
                                      "equity": "civilian_life", "favors": ["REF1-O1"], "weight": "strong",
                                      "why": "Four people will likely die before any other help arrives; the USV is the only help in time."}
    assert c["verdict"] == {"choice": "REF1-O1", "basis": "recommended", "decisive": ["REF1-C1"]}
    assert c["flip_conditions"]["would_change"][0]["then"] == "REF1-O2"
    assert c["flip_conditions"]["would_change"][0]["id"] == "REF1-flip1"
    assert "encrypted report (REF1-O2)" in c["reasoning"]["read"]           # prose refs rewritten
    assert "turn on REF1-flip1." in c["reasoning"]["uncertainty"]
    assert "library" not in c and "status" not in c
    assert view.to_global("REF1-F3") == "DR-PDF-001@v1/F3"
    assert view.to_global("REF1") == "DR-PDF-001@v1"
    assert yaml.safe_load(view.yaml()) == view.doc


def test_case_served_under_another_prefix():
    v = Case.load(FIX / "REF1.case.yaml").serve("REF2")
    assert list(v.doc["case"]["options"]) == ["REF2-O1", "REF2-O2", "REF2-O3"]
    assert v.to_global("REF2-O2") == "DR-PDF-001@v1/O2"


def test_case_reference_errors():
    d = yaml.safe_load((FIX / "REF1.case.yaml").read_text())
    d["considerations"][0]["facts"] = ["F99"]
    d["verdict"]["choice"] = "O9"
    d["reasoning"]["read"] += " See {C42}."
    with pytest.raises(ValueError) as e:
        Case.model_validate(d)
    msg = str(e.value)
    assert "unknown fact F99" in msg and "choice O9" in msg and "{C42}" in msg


def test_equities():
    eq = EquitySet.model_validate(yaml.safe_load((FIX / "equities.yaml").read_text()))
    assert {"civilian_life", "partner_relationship"} <= eq.ids()
    assert eq.served()["equities"][0]["id"] == "civilian_life"


# ------------------------------------------------------------------ reply parsing
def test_pdf_reply_is_strictly_valid():
    p = parse_reply(REPLY)
    assert p.strict_ok, p.errors
    assert p.in_order and not p.missing
    v = p.models["verdict"]
    assert v.choice == "LIVE-O3" and v.relation == "follows" and v.via is None
    assert len(p.models["fact_enumeration"].facts) == 11
    assert p.models["consideration_mapping"].live_only == ["LIVE-C6"]


def test_mode_a_structure_after_think():
    p = parse_reply(REPLY, reasoning="Let me think freely about who can warn her in time. kind of tricky.")
    assert p.strict_ok and set(p.where.values()) == {"content"}


def test_mode_b_fenced():
    p = parse_reply("Here is my analysis.\n```yaml\n" + body(REPLY) + "\n```\nDone.")
    assert p.strict_ok, p.errors


def test_mode_c_structure_inside_think_verdict_after():
    docs = body(REPLY).split("\n---\n")
    think, verdict = "\n---\n".join(docs[:-1]), docs[-1]
    p = parse_reply("<think>\n" + think + "\n</think>\n" + verdict)
    assert p.strict_ok, p.errors
    assert p.where["fact_enumeration"] == "think" and p.where["verdict"] == "content"


def test_mode_c_prime_prose_between_docs():
    docs = body(REPLY).split("\n---\n")
    think = "\n\nNow I compare the considerations to the case. Something to note: the count differs.\n\n".join(docs[:-1])
    p = parse_reply(docs[-1], reasoning=think)       # vLLM hands <think> text over as `reasoning`
    assert p.strict_ok, p.errors                      # prose between docs is allowed (C'); never scored
    assert any(d.prose_after for d in p.all_docs)


def test_content_beats_think_for_duplicates():
    v1 = body(REPLY).split("\n---\n")[-1]
    p = parse_reply(v1, reasoning=v1.replace("choice: LIVE-O3", "choice: LIVE-O1"))
    assert p.steps["verdict"]["choice"] == "LIVE-O3"


def test_placeholder_repair_is_recorded():
    bad = body(REPLY).replace("\ncase: REF1\n", "\ncase: <case id: CASE INT-301>\n")
    p = parse_reply(bad)
    assert not p.missing
    assert any("placeholder" in r for rs in p.repairs.values() for r in rs)
    assert not p.strict_ok


def test_missing_and_malformed_reported():
    docs = body(REPLY).split("\n---\n")
    p = parse_reply("\n---\n".join(d for d in docs if not d.startswith("kind: reasoning")).replace("relation: follows", "relation: copies"))
    assert p.missing == ["reasoning"]
    assert "relation" in p.errors["verdict"]


def test_not_governed_needs_no_reasoning():
    docs = body(REPLY).split("\n---\n")
    kept = [d.replace("governs: true", "governs: false").replace("relation: follows", "relation: not_governed")
            for d in docs if not d.startswith("kind: reasoning")]
    p = parse_reply("\n---\n".join(kept))
    assert p.missing == [] and p.strict_ok, p.errors


def test_via_rules():
    v = body(REPLY).split("\n---\n")[-1]
    p = parse_reply(v.replace("relation: follows", "relation: flips"))
    assert "via" in p.errors["verdict"]
    p = parse_reply(v.replace("relation: follows", "relation: flips").replace("via: null", "via: REF1-flip1"))
    assert p.models["verdict"].via == ["REF1-flip1"]


def test_smoke_outputs_parse():
    """Step 1's real Granite outputs: thinking reply is clean YAML; non-thinking needs the placeholder repair."""
    sm = ROOT / "results" / "smoke"
    if not (sm / "INT-301-v01.think.reply.yaml").exists():
        pytest.skip("smoke outputs not present")
    t = parse_reply((sm / "INT-301-v01.think.reply.yaml").read_text())
    assert not t.missing and t.steps["verdict"]["choice"] == "LIVE-O1"
    n = parse_reply((sm / "INT-301-v01.nothink.reply.yaml").read_text())
    assert not n.missing and n.steps["verdict"]["choice"] == "LIVE-O1"


# ------------------------------------------------------------------ answer key
def test_answer_key():
    k = AnswerKey.load(FIX / "journalist.answer_key.yaml")
    assert k.correct("LIVE-O3") and not k.correct("LIVE-O1")
    assert k.option_map["LIVE-O3"] == "DR-PDF-001@v1/O1"
    d = yaml.safe_load((FIX / "journalist.answer_key.yaml").read_text())
    d["relation"] = "flips"
    with pytest.raises(ValueError):
        AnswerKey.model_validate(d)


def test_noref_reply():
    docs = {d.split("\n", 1)[0]: d for d in body(REPLY).split("\n---\n")}
    keep = [docs["kind: fact_enumeration"], docs["kind: consideration_enumeration"],
            docs["kind: reasoning"].replace("case: REF1\n", "").split("case_approach:")[0]
            + "weighing:" + docs["kind: reasoning"].split("weighing:", 1)[1],
            docs["kind: verdict"].replace("relation: follows\n", "").replace("via: null\n", "")]
    p = parse_reply("\n---\n".join(keep), noref=True)
    assert p.strict_ok, p.errors
    full = parse_reply("\n---\n".join(keep))
    assert "fact_mapping" in full.missing and "relation" in full.errors["verdict"]


def test_flattened_frame_is_repaired():
    flat = body(REPLY).replace("frame: {question: same_kind, decider: same_kind, role: same}",
                               "question: same_kind\ndecider: same_kind\nrole: same")
    p = parse_reply(flat)
    assert "applicability" in p.models and p.repairs["applicability"] and not p.strict_ok


def test_column0_lists_parse():
    import yaml as _y
    docs = [_y.safe_load(d) for d in body(REPLY).split("\n---\n")]
    text = "\n---\n".join(_y.safe_dump(d, sort_keys=False, allow_unicode=True) for d in docs)   # `- ` at column 0
    p = parse_reply(text)
    assert p.strict_ok, p.errors
