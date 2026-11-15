"""Scorer tests: PDF example at max, greedy vs Hungarian, conflation, omitted gold option, not_governed, via,
REF2 translation, the untrained-Granite smoke reply, the judge cache and the Jev Decisions-API parsing."""
from __future__ import annotations

import copy

import numpy as np
import pytest

from bench.schema import AnswerKey, Case, parse_reply
from scorers import ROWS, align, align_from_passes, enum_grade, score_reply, score_reply_detailed, set_compare, set_score
from scorers.judge import CachedJudge, JevJudge, MatrixJudge, StubJudge, render_choice

from .conftest import PDF, ROOT, SMOKE, dump_docs, full_key_dict, key_dict, reply_docs, reply_text

# Rows that are None for the PDF example by construction: relation is `follows`, so there is no gold via and the
# agent claims no flip.
NONE_FOR_FOLLOWS = {"via_match", "via_consistent"}
MIN_BEST = {"options_omitted": 0, "options_correct_omitted": 0}


def docs_by_kind():
    return {d["kind"]: d for d in reply_docs()}


def rescore(docs: dict, key, served, judge=None):
    order = ["fact_enumeration", "fact_mapping", "consideration_enumeration", "consideration_mapping",
             "applicability", "reasoning", "verdict"]
    text = dump_docs([docs[k] for k in order if k in docs])
    return score_reply(parse_reply(text), key, served, judge or StubJudge())


# ---------------------------------------------------------------- 1. the PDF example against itself
def test_pdf_example_scores_max_on_every_row(parsed, key, served):
    s = score_reply(parsed, key, served, StubJudge())
    for row in ROWS:
        if row in NONE_FOR_FOLLOWS:
            assert s[row] is None, row
        elif row in MIN_BEST:
            assert s[row] == MIN_BEST[row], row
        else:
            assert s[row] == pytest.approx(1.0), (row, s[row])
    for name in ("facts_enum", "options_enum", "considerations_enum", "now", "flip_conditions"):
        assert s[f"{name}.extraneous"] == s[f"{name}.duplicate"] == s[f"{name}.absent"] == 0
    assert s["facts_enum.found"] == 11 and s["considerations_enum.found"] == 6
    assert s["facts_mapping.live_only.both"] == 11 and s["facts_mapping.case_only.both"] == 8
    assert s["considerations_mapping.matched.both"] == 5


def test_fixture_key_as_shipped_leaves_reasoning_rows_unscored(parsed, served):
    """The 2a fixture key has no gold fact / consideration lists, so the rows that translate live ids are None."""
    s = score_reply(parsed, AnswerKey.model_validate(key_dict()), served, StubJudge())
    for row in ("facts_enum", "facts_mapping", "considerations_enum", "considerations_mapping", "decisive"):
        assert s[row] is None
    assert s["verdict_choice"] == 1 and s["options_enum"] == 1.0 and s["now"] == 1.0


# ---------------------------------------------------------------- 2. greedy, not Hungarian (PDF p. 21)
def test_greedy_differs_from_hungarian():
    S = np.array([[0.90, 0.80],
                  [0.85, 0.10]])
    R = np.hstack([S, np.zeros((2, 1))])      # sqrt(R*C) = S when R = C = S
    C = np.vstack([S, np.zeros((1, 2))])
    al = align_from_passes(R, C, ["g1", "g2"], ["l1", "l2"], threshold=0.5)
    # Greedy takes the best cell first (g1-l1 .90); g2's only cell above threshold is l1, already claimed.
    assert al.pairs == [("g1", "l1", 0.9)]
    assert al.translation == {"l1": "g1"}
    # Hungarian would maximize the total instead: g1-l2 + g2-l1 = 1.65 > .90 + .10.
    from scipy.optimize import linear_sum_assignment
    rows, cols = linear_sum_assignment(-S)
    assert {(int(r), int(c)) for r, c in zip(rows, cols)} == {(0, 1), (1, 0)}
    # Partitions: g2 is present (S .85 with l1) but unpaired -> conflated; l1 stands for both -> conflating, and g1
    # shares it -> conflated too. l2 covers g1 (.80) but g1 is claimed -> duplicate.
    assert al.found == [] and set(al.conflated) == {"g1", "g2"}
    assert al.conflating == ["l1"] and al.duplicate == ["l2"] and al.extraneous == []


def test_greedy_tie_break_is_deterministic():
    S = np.array([[0.8, 0.8], [0.8, 0.8]])
    al = align_from_passes(np.hstack([S, np.zeros((2, 1))]), np.vstack([S, np.zeros((1, 2))]),
                           ["g1", "g2"], ["l1", "l2"])
    assert al.translation == {"l1": "g1", "l2": "g2"}


# ---------------------------------------------------------------- 3. conflated facts (the write-up's toy)
TOY_C = np.array([[0.80, 0.85, 0.02, 0.03],
                  [0.10, 0.05, 0.50, 0.04],
                  [0.05, 0.05, 0.43, 0.03],
                  [0.05, 0.05, 0.05, 0.90]])
TOY_R = np.array([[0.55, 0.40, 0.00, 0.05, 0.00],
                  [0.03, 0.02, 0.85, 0.05, 0.05],
                  [0.02, 0.03, 0.80, 0.05, 0.10]])


def test_conflated_duplicate_extraneous_partitions():
    al = align_from_passes(TOY_R, TOY_C, ["gt1", "gt2", "gt3"], ["l1", "l2", "l3", "l4"])
    assert al.translation == {"l1": "gt1", "l3": "gt2"}          # l3 merges gt2+gt3; it can stand for one only
    assert al.found == ["gt1"]
    assert al.conflated == ["gt2", "gt3"] and al.absent == []
    assert al.matched_gen == ["l1"] and al.conflating == ["l3"]
    assert al.duplicate == ["l2"] and al.extraneous == ["l4"]
    e = enum_grade(al)                         # (1*1 + 2*0.5 - 0.25 - 0.25) / 3
    assert e.score == pytest.approx(0.5)
    assert enum_grade(al, w_conflated=1.0, w_extra=0, w_duplicate=0).score == pytest.approx(1.0)


def test_conflated_end_to_end_through_the_judge(parsed, key, served):
    """Merge LIVE-F8 and LIVE-F9 into one generated fact; a table-backed judge says it states both."""
    docs = docs_by_kind()
    facts = docs["fact_enumeration"]["facts"]
    f8, f9 = facts[7], facts[8]
    merged = {"id": "LIVE-F8", "kind": "situation", "status": "assessed", "fact": f8["fact"] + " " + f9["fact"]}
    docs["fact_enumeration"]["facts"] = facts[:7] + [merged] + facts[9:]
    gold_txt = [f["fact"] for f in key_dict_facts()]
    gen_txt = [f["fact"] for f in docs["fact_enumeration"]["facts"]]
    stub = StubJudge()
    table = {}
    # Row pass for gold F8 and F9: both point at the merged fact; column pass for the merged fact: split .5/.45.
    for g in (f8["fact"], f9["fact"]):
        row = [0.0] * (len(gen_txt) + 1)
        row[7] = 0.9
        row[-1] = 0.1
        table[(g, tuple(gen_txt))] = row
    col = [0.0] * (len(gold_txt) + 1)
    col[7], col[8], col[-1] = 0.5, 0.45, 0.05
    table[(merged["fact"], tuple(gold_txt))] = col
    s = rescore(docs, key, served, MatrixJudge(table, fallback=stub))
    assert s["facts_enum.conflated"] == 2 and s["facts_enum.found"] == 9 and s["facts_enum.absent"] == 0
    assert s["facts_enum"] == pytest.approx((9 + 2 * 0.5) / 11)


def key_dict_facts():
    return full_key_dict()["facts"]


# ---------------------------------------------------------------- 4. options: omitted gold option, id shuffles
def test_omitted_gold_option(key, served):
    docs = docs_by_kind()
    del docs["fact_enumeration"]["options"]["LIVE-O3"]            # the gold choice
    docs["fact_mapping"]["options"].pop("LIVE-O3")
    s = rescore(docs, key, served)
    assert s["options_omitted"] == 1 and s["options_correct_omitted"] == 1
    assert s["options_enum.absent"] == 1 and s["options_enum"] == pytest.approx(2 / 3)
    assert s["verdict_choice"] == 0           # chose an option it never enumerated: not alignable
    assert s["options_mapping"] == pytest.approx(2 / 3)


def test_choice_is_translated_by_alignment_not_by_id(key, served):
    """Relabel the agent's options (O1<->O3) everywhere: ids no longer coincide with gold ids, scores do not move.
    (Shortcut guard: matching LIVE-O ids by coincidence would score this reply wrong.)"""
    swap = {"LIVE-O1": "LIVE-O3", "LIVE-O3": "LIVE-O1"}
    text = reply_text()
    for a, b in (("LIVE-O1", "@@"), ("LIVE-O3", "LIVE-O1"), ("@@", "LIVE-O3")):
        text = text.replace(a, b)
    s = score_reply(parse_reply(text), key, served, StubJudge())
    assert s["verdict_choice"] == 1 and s["options_mapping"] == 1.0 and s["options_enum"] == 1.0
    assert s["considerations_enum.favors"] == 1.0 and s["flip_conditions.then"] == 1.0
    assert swap  # documented above


def test_wrong_choice(key, served):
    docs = docs_by_kind()
    docs["verdict"]["choice"] = "LIVE-O1"
    s = rescore(docs, key, served)
    assert s["verdict_choice"] == 0 and s["relation"] == 1


def test_acceptable_choice(served):
    k = full_key_dict()
    k["acceptable"] = ["LIVE-O1"]
    docs = docs_by_kind()
    docs["verdict"]["choice"] = "LIVE-O1"
    assert rescore(docs, AnswerKey.model_validate(k), served)["verdict_choice"] == 1


# ---------------------------------------------------------------- 5. not_governed: nothing after it is scored
AFTER = ["verdict_choice", "course", "decisive", "now", "flip_conditions", "flip_conditions.then",
         "via_match", "via_consistent"]


def test_not_governed_unscores_everything_after(key, served):
    docs = docs_by_kind()
    docs["applicability"]["governs"] = False
    docs["verdict"]["relation"] = "not_governed"
    del docs["reasoning"]
    s = rescore(docs, key, served)
    for row in AFTER:
        assert s[row] is None, row
    assert s["governs"] == 0 and s["relation"] == 0          # the decline itself is scored
    assert s["facts_enum"] == 1.0 and s["considerations_mapping"] == 1.0   # before it: scored
    assert s["verdict_choice_ungated"] == 1                   # eval diagnostic only
    assert s["format.agent_not_governed"] == 1


def test_relation_not_governed_alone_also_declines(key, served):
    docs = docs_by_kind()
    docs["verdict"]["relation"] = "not_governed"
    s = rescore(docs, key, served)
    assert s["verdict_choice"] is None and s["governs"] == 1


# ---------------------------------------------------------------- 6. via: match vs gold, consistency with then
def flips_key(via=("DR-PDF-001@v1/flip1",), choice="LIVE-O1"):
    k = full_key_dict()
    k.update(relation="flips", via=list(via), choice=choice)
    return AnswerKey.model_validate(k)


def flips_docs(via, choice):
    docs = docs_by_kind()
    docs["verdict"].update(relation="flips", via=via, choice=choice)
    return docs


def test_via_right_and_consistent(served):
    s = rescore(flips_docs(["REF1-flip1"], "LIVE-O1"), flips_key(), served)
    # LIVE-O1 -> REF1-O2 in the agent's options map; REF1-flip1.then = REF1-O2.
    assert s["via_match"] == 1 and s["via_consistent"] == 1 and s["verdict_choice"] == 1 and s["relation"] == 1


def test_via_right_choice_inconsistent(served):
    s = rescore(flips_docs(["REF1-flip1"], "LIVE-O3"), flips_key(), served)
    assert s["via_match"] == 1 and s["via_consistent"] == 0 and s["verdict_choice"] == 0


def test_via_wrong_but_consistent(served):
    """flip2's then is also REF1-O2: a wrong via that is still consistent. The two values are separate on
    purpose; consistency alone is satisfiable by citing any flip whose then matches."""
    s = rescore(flips_docs(["REF1-flip2"], "LIVE-O1"), flips_key(), served)
    assert s["via_match"] == 0 and s["via_consistent"] == 1


def test_via_invalid_id(served):
    s = rescore(flips_docs(["REF1-flip9"], "LIVE-O1"), flips_key(), served)
    assert s["via_match"] == 0 and s["via_consistent"] == 0


def test_via_consistency_falls_back_to_gold_option_map(served):
    docs = flips_docs(["REF1-flip1"], "LIVE-O1")
    docs["fact_mapping"]["options"].pop("LIVE-O1")
    full = score_reply_detailed(parse_reply(dump_docs(list(docs.values()))), flips_key(), served, StubJudge())
    assert full.rows["via_consistent"] == 1
    assert full.details["notes"]["via_consistent"]["path"].startswith("gold option map")


def test_distinguished_where_gold_flips(served):
    """Right that the answer changes, wrong why: relation 0, via 0, consistency not applicable; the partial credit
    is the reward's call."""
    docs = docs_by_kind()
    docs["verdict"].update(relation="distinguished", choice="LIVE-O1")
    s = rescore(docs, flips_key(), served)
    assert s["relation"] == 0 and s["via_match"] == 0 and s["via_consistent"] is None and s["verdict_choice"] == 1


# ---------------------------------------------------------------- 7. served -> global under prefix REF2
def test_served_ids_translate_under_ref2(case, key):
    served2 = case.serve("REF2")
    text = reply_text().replace("REF1", "REF2")
    s = score_reply(parse_reply(text), key, served2, StubJudge())
    assert s["facts_mapping"] == 1.0 and s["considerations_mapping"] == 1.0 and s["options_mapping"] == 1.0
    # Same reply still citing REF1 ids while REF2 was served: the case-side ids do not translate.
    s1 = score_reply(parse_reply(reply_text()), key, served2, StubJudge())
    assert s1["facts_mapping.case_only.both"] == 0 and s1["facts_mapping.case_only.agent_only"] == 8
    assert s1["considerations_mapping.matched.both"] == 0 and s1["options_mapping"] == 0.0


def test_two_served_cases(case, key):
    """REF1 is the relevant case, REF2 a second copy: tables merge, REF1 ids still translate."""
    s = score_reply(parse_reply(reply_text()), key, [case.serve("REF1"), case.serve("REF2")], StubJudge())
    assert s["facts_mapping"] == 1.0


# ---------------------------------------------------------------- 8. no-reference arm
def test_no_reference_arm(parsed):
    k = full_key_dict()
    for f in ("served", "relation", "frame_map", "option_map", "fact_mapping", "consideration_mapping", "governs"):
        k.pop(f, None)
    k["arm"] = "none"
    s = score_reply(parsed, AnswerKey.model_validate(k), None, StubJudge())
    for row in ("frame_map_question", "options_mapping", "facts_mapping", "considerations_mapping", "governs",
                "relation"):
        assert s[row] is None, row
    assert s["verdict_choice"] == 1 and s["facts_enum"] == 1.0


# ---------------------------------------------------------------- 9. the untrained-Granite smoke reply
def smoke_key():
    return AnswerKey.model_validate({
        "scenario": "INT-301-v01", "arm": "relevant", "served": "DR-PDF-001@v1",
        "options": {
            "LIVE-O1": {"do": "log the militia posts in the intelligence threat database and include them in "
                              "Thursday's threat summary", "move": "act", "irreversible": True, "source_id": "A"},
            "LIVE-O2": {"do": "send the militia posts to the installation Provost Marshal and keep them out of every "
                              "intelligence file", "move": "act", "source_id": "B"},
            "LIVE-O3": {"do": "park the militia posts unfiled and ask the brigade's intelligence oversight officer "
                              "for a ruling before anything moves", "move": "ask", "source_id": "C"}},
        "choice": "LIVE-O2", "relation": "follows", "governs": True,
        "frame": {"question": "How should the agent dispose of the militia posts the analysts flagged?",
                  "decider": "The workflow agent, under the S-2 SOP", "my_role": "Process intake items under the SOP"},
        "course": "Refer the militia posts to the Provost Marshal and keep them out of every intelligence file.",
        "now": ["Send the posts to the Provost Marshal", "Close the intake item as referred"],
        "flip_conditions": [{"id": "LIVE-flip1", "if": "A confirmed tie to a foreign power", "then": "LIVE-O1"},
                            {"id": "LIVE-flip2", "if": "A suspected but unconfirmed foreign tie", "then": "LIVE-O3"}],
    })


def test_smoke_reply_degrades_gracefully(served):
    """Real untrained Granite output (wrong shapes: flat flip list, `now` as ids, prose in applicability.frame,
    free-text case ids). The served case here is the PDF case, a stand-in: INT-301 has no converted case yet."""
    p = parse_reply(SMOKE.read_text())
    full = score_reply_detailed(p, smoke_key(), served, StubJudge())
    s = full.rows
    assert s["schema_valid"] == 0
    assert set(full.details["format_report"]["malformed"]) == {"fact_mapping", "consideration_mapping",
                                                               "applicability", "verdict"}
    assert s["format.steps_present"] == 7 and s["format.steps_malformed"] == 4
    assert s["relation"] == 1 and s["governs"] == 1
    assert 0 <= s["frame_question"] <= 1 and 0 <= s["course"] <= 1
    assert s["now"] is not None and s["now"] < 0          # `now` lists ids, not actions: nothing found, 2 extra
    assert s["flip_conditions.n_generated"] == 1          # one would_change item recovered from the flat list
    assert s["via_match"] is None and s["via_consistent"] is None
    # The token-overlap stub cannot match Granite's paraphrased options to the gold wording, so with the stub the
    # choice is unresolved (0) -- with Jev it should align. The reason is recorded:
    assert full.details["notes"]["choice"]["how"] == "agent option not aligned to any gold option"
    assert all(isinstance(v, (int, float)) or v is None for v in s.values())


def test_smoke_reply_scoring_path_with_aligned_option_wording(served):
    """Same reply; gold options worded as the agent worded them, so even the stub aligns them. Gold ids differ from
    the agent's (gold refer is LIVE-O2, the agent's refer is LIVE-O1): the choice is translated, not id-matched."""
    p = parse_reply(SMOKE.read_text())
    k = smoke_key().model_dump(by_alias=True)
    agent_opts = p.steps["fact_enumeration"]["options"]
    k["options"]["LIVE-O1"]["do"] = agent_opts["LIVE-O2"]       # file
    k["options"]["LIVE-O2"]["do"] = agent_opts["LIVE-O1"]       # refer (gold)
    s = score_reply(p, AnswerKey.model_validate(k), served, StubJudge())
    assert s["verdict_choice"] == 1
    assert s["options_omitted"] == 1 and s["options_correct_omitted"] == 0      # dropped the hand-up
    assert s["options_enum"] == pytest.approx(2 / 3)
    assert s["flip_conditions"] is not None and s["flip_conditions"] < 1


def test_garbage_reply_does_not_crash(key, served):
    for text in ("", "no yaml here at all", "kind: verdict\nchoice: [1, 2\n", "kind: verdict\nchoice: LIVE-O3\n",
                 "kind: fact_enumeration\nfacts: 7\noptions: [a, b]\n"):
        s = score_reply(parse_reply(text), key, served, StubJudge())
        assert s["schema_valid"] == 0
        assert s["facts_enum"] <= 0.0          # nothing found; a junk "fact" costs w_extra
        assert s["verdict_choice"] in (0, 1)


# ---------------------------------------------------------------- 10. graders, judges
def test_set_compare_and_score():
    c = set_compare({"a", "b", "c"}, {"b", "c", "d"})
    assert c == {"key_only": 1, "both": 2, "agent_only": 1}
    assert set_score(c) == pytest.approx((2 - 0.5) / 3)
    assert set_score(set_compare(set(), set())) == 1.0


def test_stub_alignment_exact_text():
    al = align({"x1": "Water is 14 C", "x2": "Something unrelated entirely"},
               {"g1": "water is 14 c", "g2": "the cutter is three hours away"}, StubJudge())
    assert al.translation == {"x1": "g1"} and al.absent == ["g2"] and al.extraneous == ["x2"]


def test_cached_judge_hits(tmp_path, parsed, key, served):
    j = CachedJudge(StubJudge(), tmp_path / "c.sqlite")
    a = score_reply(parsed, key, served, j)
    m = j.misses
    b = score_reply(parsed, key, served, CachedJudge(StubJudge(), tmp_path / "c.sqlite"))
    assert a == b and m > 0
    j2 = CachedJudge(StubJudge(), tmp_path / "c.sqlite")
    score_reply(parsed, key, served, j2)
    assert j2.misses == 0 and j2.hits > 0


def test_render_choice_permutes_deterministically():
    p1, perm1, labels = render_choice("x", ["a", "b", "c", "d"])
    p2, perm2, _ = render_choice("x", ["a", "b", "c", "d"])
    assert p1 == p2 and perm1 == perm2 and labels[-1] == "E" and sorted(perm1) == [0, 1, 2, 3]


def test_jev_decisions_parsing_offline(monkeypatch):
    """Response shape of OpenRouter's Decisions API, as returned live on 2026-10-25."""
    j = JevJudge(choice_model="typesafe/jev-1.14", noul_model="typesafe/jev-1.14", api_key="x")
    cands = ["alpha", "beta", "gamma"]
    _, perm, labels = render_choice("item", cands)
    lab_beta = labels[perm.index(1)]
    seen = {}

    def fake_choice(model, state, questions):
        seen.update(state=state, questions=questions)
        probs = {l: 0.0 for l in labels}
        probs[lab_beta], probs[labels[-1]] = 0.7, 0.2
        probs[labels[perm.index(0)]] = 0.1
        return {"model": "typesafe/jev-1.14-20261014",
                "answers": {"match": {"type": "choice", "choice": lab_beta, "probabilities": probs, "confidence": 0.7}}}
    monkeypatch.setattr(j, "_post", fake_choice)
    d = j.choice("item", cands)
    assert len(d) == 4 and sum(d) == pytest.approx(1.0)
    assert d[1] == pytest.approx(0.7, rel=1e-3) and d[0] == pytest.approx(0.1, rel=1e-3) and d[-1] == pytest.approx(0.2, rel=1e-3)
    q = seen["questions"]["match"]
    assert q["type"] == "choice" and q["criteria"][lab_beta] == "beta" and seen["state"]["item"] == "item"
    monkeypatch.setattr(j, "_post", lambda m, st, qs: {"answers": {"q": {"type": "noul", "noul": 0.16}}})
    assert j.noul("a", "b", "q") == pytest.approx(0.16)
    monkeypatch.setattr(j, "_post", lambda m, st, qs: {"answers": {"q": {"type": "choice"}}})
    with pytest.raises(Exception):
        j.noul("a", "b", "q")


# ---------------------------------------------------------------- 11. real 2b data: converted INT-301 + its keys
REAL = ROOT / "data"


@pytest.mark.skipif(not (REAL / "cases" / "INT-301" / "DR-INT-301@v1.case.yaml").exists(), reason="2b data absent")
def test_smoke_reply_against_real_int301_keys():
    """The untrained-Granite smoke reply scored with 2b's converted INT-301 case served as REF1 and the real
    (choice-only) answer keys. Pilot keys hold only the decision, so the reasoning rows are None, not 0."""
    case = Case.load(REAL / "cases" / "INT-301" / "DR-INT-301@v1.case.yaml")
    text = SMOKE.read_text()
    rel = AnswerKey.load(REAL / "scenarios" / "INT-301" / "INT-301-v01.relevant.key.yaml")
    s = score_reply(parse_reply(text), rel, case.serve("REF1"), StubJudge())
    assert s["relation"] == 1 and s["governs"] == 1
    assert s["options_omitted"] >= 1                        # the hand-up option was dropped
    for row in ("facts_enum", "facts_mapping", "considerations_enum", "course", "now", "flip_conditions",
                "frame_question", "frame_map_question"):
        assert s[row] is None, row
    none = AnswerKey.load(REAL / "scenarios" / "INT-301" / "INT-301-v01.none.key.yaml")
    s0 = score_reply(parse_reply(text, noref=True), none, None, StubJudge())
    assert s0["relation"] is None and s0["governs"] is None and s0["verdict_choice"] in (0, 1)
