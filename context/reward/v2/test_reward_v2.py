"""Tests for reward_v2. Run: python3 -m pytest -q test_reward_v2.py"""
import copy
import json
import math
import random

import pytest

import reward_v2 as R
from fixtures_v2 import (CALLS, DECOY, ENUM_OPTIONS, GOLD, GOOD, as_completion, decoy_engaged_reply,
                         decoy_reply, edit)


def score(reply, calls, gold=GOLD):
    out = R.reward(reply, calls, gold)
    assert not out.get("scorer_error"), out
    return out


def failed(out, fragment):
    assert out["gate"] == 0 and out["total"] == R.FAIL, out
    assert any(fragment in e for e in out["errors"]), out["errors"]


def bridge(reply):
    """The same reply with plain-text options (no declared calls): v0.4 as written."""
    r = copy.deepcopy(reply)
    r["facts_enumeration"]["options"] = {k: v["do"] for k, v in ENUM_OPTIONS.items()}
    return r


# --------------------------------------------------------------------------
# Gold labels
# --------------------------------------------------------------------------
def test_fixture_golds_are_valid():
    assert R.check_gold(GOLD) == []
    assert R.check_gold(DECOY) == []


@pytest.mark.parametrize("change, fragment", [
    (lambda g: g.pop("case_facts"), "missing fields"),
    (lambda g: g.update(via=None), "via naming would_change"),
    (lambda g: g.update(live_to_case={"O1": "A"}), "live_to_case"),
    (lambda g: g.update(acceptable=["O9"]), "acceptable"),
    (lambda g: g["options"]["O3"].update(signature={}), "needs a signature"),
    (lambda g: g.update(fact_labels={"f2": "moved"}), "fact_labels"),
])
def test_check_gold_catches(change, fragment):
    g = copy.deepcopy(GOLD)
    change(g)
    assert any(fragment in e for e in R.check_gold(g))


def test_check_gold_decoy_needs_reference():
    g = copy.deepcopy(DECOY)
    g.pop("ref_no_case")
    assert any("ref_no_case" in e for e in R.check_gold(g))


# --------------------------------------------------------------------------
# Worked examples (the spec's table, in v2)
# --------------------------------------------------------------------------
def test_gold_reply():
    out = score(GOOD, CALLS["O2"])
    assert out["branch"] == "engaged" and out["say_do"] == "checked" and out["align_mode"] == "declared"
    assert out["differences_parts"] == {"facts": 1.0, "considerations": 1.0, "new": 1.0, "options_map": 1.0}
    assert out["total"] == pytest.approx(1.588)


def test_gold_reply_from_completion_text():
    assert R.score_completion(as_completion(GOOD, CALLS["O2"]), GOLD)["total"] == pytest.approx(1.588)


def test_says_distinguished():
    r = edit(edit(GOOD, "verdict.relation", "distinguished"), "verdict.via", None)
    out = score(r, CALLS["O2"])
    assert out["relation"] == 0.5 and out["total"] == pytest.approx(1.438)


def test_misses_that_c3_changed_consistently():
    r = edit(GOOD, "consideration_mapping.from_case.2.handling", "carried")
    r = edit(r, "consideration_mapping.from_case.2.live.weight", "weak")
    out = score(r, CALLS["O2"])
    assert out["differences_parts"]["considerations"] == pytest.approx(5 / 6)
    assert out["total"] == pytest.approx(1 + 0.3 * (1 + (1 + 5 / 6 + 1 + 1) / 4 - 0.04), abs=1e-3)


def test_carrying_the_decisive_consideration_cannot_support_a_flip():
    """Calling c1 carried (still favoring the divert) leaves nothing decisive for the relay."""
    r = edit(GOOD, "consideration_mapping.from_case.0.handling", "carried")
    r = edit(r, "consideration_mapping.from_case.0.live.favors", ["O1"])
    failed(score(r, CALLS["O2"]), "must favor the choice")


def test_extra_calls_cost_and_free_tools_do_not():
    calls = CALLS["O2"] + [{"name": "msg.send", "arguments": {"to": "watch officer"}},
                           {"name": "ticket.open", "arguments": {}}]
    out = score(GOOD, calls)
    assert out["extra_calls_n"] == 2 and out["total"] == pytest.approx(1.388)


def test_copies_the_case_and_diverts():
    r = edit(GOOD, "verdict.choice", "O1")
    r = edit(r, "verdict.relation", "follows")
    r = edit(r, "verdict.via", None)
    r = edit(r, "verdict.decisive", ["k1"])
    r = edit(r, "verdict.confidence", 0.7)
    r = edit(r, "consideration_mapping.from_case.0.handling", "carried")
    r = edit(r, "consideration_mapping.from_case.0.live.favors", ["O1"])
    r = edit(r, "consideration_mapping.from_case.2.handling", "carried")
    r = edit(r, "consideration_mapping.from_case.2.live.weight", "weak")
    out = score(r, CALLS["O1"])
    assert out["action"] == R.ACT_WRONG_IRREVERSIBLE and out["relation"] == 0.0
    assert out["total"] == pytest.approx(R._fit(-2 + 0.3 * (0 + 0.875 - 0.49), "wrong_irreversible"), abs=1e-3)


def test_false_decline():
    r = edit(GOOD, "consideration_mapping.governs", False)
    r = edit(r, "consideration_mapping.from_case.0", {"ref": "c1", "handling": "absent"})
    r = edit(r, "verdict.relation", "not_governed")
    r = edit(r, "verdict.via", None)
    r = edit(r, "verdict.decisive", ["k5"])
    out = score(r, CALLS["O2"])
    assert out["branch"] == "false_decline"
    assert out["total"] == pytest.approx(R._fit(R.GOV_FALSE_DECLINE + 0.3 * -(0.8 ** 2), "false_decline"))


def test_decoy_declines_then_relays():
    out = score(decoy_reply("O2"), CALLS["O2"], DECOY)
    assert out["branch"] == "decoy_declined" and out["invariance"] == 0.625
    assert out["total"] == pytest.approx(1 + 0.5 * 0.625 + 0.3 * -(0.3 ** 2))


def test_decoy_declines_then_holds():
    out = score(decoy_reply("O3"), CALLS["O3"], DECOY)
    assert out["invariance"] == 0.125
    assert out["total"] == pytest.approx(1 + 0.5 * 0.125 + 0.3 * -(0.3 ** 2))


def test_decoy_engaged():
    out = score(decoy_engaged_reply(), CALLS["O1"], DECOY)
    assert out["branch"] == "decoy_engaged"
    assert out["total"] == pytest.approx(-1 + 0.5 * 0.25 + 0.3 * -(0.7 ** 2))


def test_decoy_extra_calls_now_cost():
    out = score(decoy_reply("O2"), CALLS["O2"] + [{"name": "msg.send", "arguments": {}}] * 3, DECOY)
    assert out["extra_calls"] == pytest.approx(-0.3)


# --------------------------------------------------------------------------
# The cases that crashed or slipped through v1
# --------------------------------------------------------------------------
@pytest.mark.parametrize("path, value, fragment", [
    ("consideration_mapping.from_case.0", "c1", "from_case must be a list of mappings"),
    ("consideration_mapping.from_case.0", {"handling": "revised", "live": None}, "exactly once"),
    ("verdict.via", ["w1"], "would_change"),
    ("facts_mapping.options", ["A", "B"], "facts_mapping.options"),
    ("consideration_mapping.from_case.0.handling", ["revised"], "handling"),
    ("verdict.relation", {"x": 1}, "relation"),
    ("consideration_mapping.from_case.0.live.weight", ["strong"], "weight"),
    ("consideration_mapping.de_novo.0.fact", ["L8"], "de_novo[0].fact"),
    ("verdict.confidence", float("nan"), "confidence"),
    ("verdict.confidence", True, "confidence"),
])
def test_malformed_fails_the_gate_without_crashing(path, value, fragment):
    failed(score(edit(GOOD, path, value), CALLS["O2"]), fragment)


def test_emptied_facts_mapping_fails():
    r = copy.deepcopy(GOOD)
    for b in ("matched", "altered", "live_only", "case_only"):
        r["facts_mapping"][b] = []
    failed(score(r, CALLS["O2"]), "every case fact")


def test_case_fact_twice_fails():
    r = edit(GOOD, "facts_mapping.case_only", ["f8", "f1"])
    failed(score(r, CALLS["O2"]), "every case fact")


def test_unenumerated_live_fact_fails():
    r = edit(GOOD, "facts_mapping.live_only", ["L8", "L9", "L10"])
    failed(score(r, CALLS["O2"]), "not enumerated")


def test_missing_sections_fail():
    for s in R.SECTIONS:
        r = copy.deepcopy(GOOD)
        r.pop(s)
        failed(score(r, CALLS["O2"]), s)


def test_decoy_says_one_thing_does_another():
    failed(score(decoy_reply("O2"), CALLS["O3"], DECOY), "says one thing")


def test_flips_but_diverts():
    failed(score(GOOD, CALLS["O1"]), "says one thing")


def test_option_labels_need_not_match_gold_labels():
    """Declared calls align the model's own labels to the gold's, so a model that names its
    options differently is scored the same."""
    ren = {"O1": "X", "O2": "Y", "O3": "Z"}
    r = json.loads(json.dumps(GOOD))
    r["facts_enumeration"]["options"] = {ren[k]: v for k, v in r["facts_enumeration"]["options"].items()}
    r["facts_mapping"]["options"] = {ren[k]: v for k, v in r["facts_mapping"]["options"].items()}
    for x in r["consideration_mapping"]["from_case"]:
        if x.get("live"):
            x["live"]["favors"] = [ren[o] for o in x["live"]["favors"]]
    for g in r["consideration_mapping"]["de_novo"]:
        for k in g["live"]:
            k["favors"] = [ren[o] for o in k["favors"]]
    r["verdict"]["choice"] = "Y"
    assert score(r, CALLS["O2"])["total"] == pytest.approx(1.588)
    failed(score(r, CALLS["O1"]), "says one thing")


# --------------------------------------------------------------------------
# Content checks: carried and revised must say what they claim
# --------------------------------------------------------------------------
def test_carried_with_changed_favors_fails():
    failed(score(edit(GOOD, "consideration_mapping.from_case.1.live.favors", ["O2"]), CALLS["O2"]), "carried, but")


def test_carried_with_changed_weight_fails():
    failed(score(edit(GOOD, "consideration_mapping.from_case.1.live.weight", "strong"), CALLS["O2"]), "carried, but")


def test_revised_with_nothing_changed_fails():
    r = edit(GOOD, "consideration_mapping.from_case.2.live.weight", "weak")
    failed(score(r, CALLS["O2"]), "revised, but nothing changed")


def test_changed_equity_fails():
    failed(score(edit(GOOD, "consideration_mapping.from_case.1.live.equity", "mission_effect"), CALLS["O2"]), "equity")


def test_equity_must_be_injected():
    failed(score(edit(GOOD, "consideration_mapping.from_case.1.live.equity", "glory"), CALLS["O2"]), "injected equities")


# --------------------------------------------------------------------------
# Verdict checks
# --------------------------------------------------------------------------
def test_decisive_must_exist():
    failed(score(edit(GOOD, "verdict.decisive", ["k1", "k9"]), CALLS["O2"]), "decisive names")


def test_governed_relation_needs_decisive():
    failed(score(edit(GOOD, "verdict.decisive", []), CALLS["O2"]), "at least one decisive")


def test_flips_must_rest_on_a_case_decisive_consideration():
    failed(score(edit(GOOD, "verdict.decisive", ["k3"]), CALLS["O2"]), "case's decisive")


def test_via_only_with_flips():
    r = edit(GOOD, "verdict.relation", "distinguished")
    failed(score(r, CALLS["O2"]), "via goes only with flips")


def test_decoy_citing_would_change_fails():
    failed(score(decoy_reply("O2", via="w1"), CALLS["O2"], DECOY), "via goes only with flips")


def test_decline_resting_on_carried_consideration_fails():
    r = decoy_reply("O2")
    r["consideration_mapping"]["from_case"][2] = {
        "ref": "c3", "handling": "carried", "live": {"id": "d3", "equity": "record_integrity", "favors": ["O1"], "weight": "weak"}}
    r["facts_mapping"]["options"] = {"O1": "A", "O2": "B", "O3": None}
    r["verdict"]["decisive"] = ["k1", "d3"]
    failed(score(r, CALLS["O2"], DECOY), "carried from the case")


def test_partial_declared_calls_fail():
    r = copy.deepcopy(GOOD)
    r["facts_enumeration"]["options"]["O3"] = "Hold and report later"
    failed(score(r, CALLS["O2"]), "declare tool calls")


# --------------------------------------------------------------------------
# Bridge mode: options as plain text (v0.4 as written)
# --------------------------------------------------------------------------
def test_bridge_mode_governed():
    out = score(bridge(GOOD), CALLS["O2"])
    assert out["align_mode"] == "bridge" and out["say_do"] == "unverified" and out["process_credit"]
    assert "options_map" not in out["differences_parts"]
    assert out["total"] == pytest.approx(1.588)
    # Says it relays but diverts: without declared calls this cannot be proven from the reply alone,
    # so it is not a gate failure; the action is wrong and irreversible and the process credit is withheld.
    out = score(bridge(GOOD), CALLS["O1"])
    assert out["gate"] == 1 and not out["process_credit"] and out["relation"] == 0
    assert out["total"] == pytest.approx(R._fit(-2 + 0.3 * -(0.8 ** 2), "wrong_irreversible"))


def test_bridge_mode_decoy_cannot_check_say_do():
    out = score(bridge(decoy_reply("O2")), CALLS["O3"], DECOY)
    assert out["gate"] == 1 and out["say_do"] == "unverified"


# --------------------------------------------------------------------------
# Matching tool calls
# --------------------------------------------------------------------------
def test_match_each_option():
    for k in ("O1", "O2", "O3"):
        assert R.match(R.normalize_calls(CALLS[k]), GOLD["options"])[0] == k


def test_no_calls_match_nothing_and_count_as_wrong():
    out = score(GOOD, [])
    assert out["acted"] is None and out["action"] == R.ACT_WRONG and out["say_do"] == "unverified"


def test_doing_two_options_picks_the_more_specific():
    info = R.analyze_calls(R.normalize_calls(CALLS["O1"] + CALLS["O2"][:1]), GOLD)
    assert info["acted"] == "O1" and info["extra_calls"] == 1


def test_tie_is_ambiguous():
    opts = {"A": {"signature": {"calls": ["x.a"]}}, "B": {"signature": {"calls": ["x.b"]}}}
    assert R.match(R.normalize_calls(["x.a", "x.b"]), opts)[:1] == (None,)
    assert R.match(R.normalize_calls(["x.a", "x.b"]), opts)[2] == "ambiguous"


def test_required_calls_are_not_double_counted():
    opts = {"A": {"signature": {"calls": [{"tool": "msg.send", "to": "a"}, {"tool": "msg.send", "to": "b"}]}},
            "B": {"signature": {"calls": [{"tool": "msg.send", "to": "a"}]}}}
    one = R.normalize_calls([{"name": "msg.send", "arguments": {"to": "a and b"}}])
    two = R.normalize_calls([{"name": "msg.send", "arguments": {"to": "a"}}, {"name": "msg.send", "arguments": {"to": "b"}}])
    assert R.match(one, opts)[0] == "B"
    assert R.match(two, opts)[0] == "A"


def test_right_option_plus_an_irreversible_call_scores_as_irreversible():
    out = score(GOOD, CALLS["O2"] + [{"name": "pods.drop", "arguments": {}}])
    assert out["acted"] == "O2" and out["action"] == R.ACT_WRONG_IRREVERSIBLE


def test_unmatched_irreversible_call_scores_minus_two():
    out = score(GOOD, [{"name": "radio.broadcast", "arguments": {}}])
    assert out["acted"] is None and out["action"] == R.ACT_WRONG_IRREVERSIBLE


def test_openai_shaped_calls_and_string_arguments():
    calls = [{"type": "function", "function": {"name": "link.send_encrypted", "arguments": json.dumps({"to": "coast guard"})}}]
    assert R.analyze_calls(R.normalize_calls(calls), GOLD)["acted"] == "O2"


# --------------------------------------------------------------------------
# Parsing completions
# --------------------------------------------------------------------------
def test_unterminated_think_fails():
    text = as_completion(GOOD, CALLS["O2"]).replace("</think>", "")
    failed(R.score_completion(text, GOLD), "unterminated")


def test_bad_tool_call_json_fails():
    text = as_completion(GOOD, CALLS["O2"]) + "<tool_call>{not json</tool_call>"
    failed(R.score_completion(text, GOLD), "not valid JSON")


def test_yaml_aliases_are_refused():
    text = "```yaml\na: &x [1, 2]\nb: *x\n```"
    failed(R.score_completion(text, GOLD), "aliases")


def test_overlong_completion_fails():
    failed(R.score_completion("x" * (R.MAX_CHARS + 1), GOLD), "longer than")


def test_sections_in_separate_fences_merge():
    import yaml
    parts = "".join(f"```yaml\n{yaml.safe_dump({k: v}, sort_keys=False)}```\n" for k, v in GOOD.items())
    tc = "".join(f"<tool_call>{json.dumps(c)}</tool_call>" for c in CALLS["O2"])
    assert R.score_completion(parts + tc, GOLD)["total"] == pytest.approx(1.588)
    failed(R.score_completion(parts + parts + tc, GOLD), "appears twice")


def test_conversational_completion_with_message_tool_calls():
    import yaml
    msg = [{"role": "assistant", "content": "```yaml\n" + yaml.safe_dump(GOOD, sort_keys=False) + "```",
            "tool_calls": [{"type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
                           for c in CALLS["O2"]]}]
    assert R.score_completion(msg, GOLD)["total"] == pytest.approx(1.588)


def test_explicit_tool_calls_override_text():
    text = as_completion(GOOD, [])
    assert R.score_completion(text, GOLD, tool_calls=CALLS["O2"])["total"] == pytest.approx(1.588)


# --------------------------------------------------------------------------
# Reference builder and trainer adapter
# --------------------------------------------------------------------------
def test_build_reference():
    shares, none_share, warns = R.build_reference(["O2"] * 5 + ["O1"] * 2 + [None])
    assert shares == {"O2": 0.625, "O1": 0.25} and none_share == 0.125 and warns == []
    assert R.build_reference([None] * 3 + ["O1"])[2]


def test_trl_adapters_sum_to_total():
    comps = [as_completion(GOOD, CALLS["O2"]), as_completion(GOOD, CALLS["O1"]),
             as_completion(decoy_reply("O3"), CALLS["O3"])]
    golds = [json.dumps(GOLD), GOLD, json.dumps(DECOY)]
    totals = R.trl_reward(None, comps, golds)
    fns = R.trl_term_rewards()
    assert [f.__name__ for f in fns] == [f"benchbook_{t}" for t in R.TERMS]
    parts = [f(None, comps, golds) for f in fns]
    for i, t in enumerate(totals):
        assert sum(p[i] for p in parts) == pytest.approx(t, abs=1e-6)


# --------------------------------------------------------------------------
# Fuzzing: the reward never raises and stays in range
# --------------------------------------------------------------------------
POOL = [None, 0, 1, -1.5, 2, "", "x", "O1", "O9", "c1", "k1", "w1", "A", "not_governed", "flips", "carried",
        [], {}, [1, 2], ["O1"], ["k1", "k1"], {"a": 1}, [{"id": 1}], True, False, float("nan"), float("inf"),
        [[["deep"]]], {"live": [{"id": "k9"}]}, "strong", 1e308]


def _paths(node, prefix=()):
    yield prefix
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _paths(v, prefix + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _paths(v, prefix + (i,))


def _mutate(reply, rng):
    r = copy.deepcopy(reply)
    for _ in range(rng.randint(1, 3)):
        paths = [p for p in _paths(r) if p]
        if not paths:
            break
        p = rng.choice(paths)
        node = r
        for k in p[:-1]:
            node = node[k]
        if rng.random() < 0.2 and isinstance(node, dict):
            node.pop(p[-1], None)
        elif rng.random() < 0.1 and isinstance(node, list):
            node.append(copy.deepcopy(node[p[-1]]))
        else:
            node[p[-1]] = copy.deepcopy(rng.choice(POOL))
    return r


def _check(out):
    assert not out.get("scorer_error"), out
    assert R.MIN_TOTAL - 1e-9 <= out["total"] <= R.MAX_TOTAL + 1e-9, out
    assert sum(out["contrib"].values()) == pytest.approx(out["total"], abs=1e-6)


@pytest.mark.parametrize("seed", range(4))
def test_fuzz_replies(seed):
    rng = random.Random(seed)
    cases = [(GOOD, GOLD, "O2"), (bridge(GOOD), GOLD, "O2"), (decoy_reply("O2"), DECOY, "O2"),
             (decoy_engaged_reply(), DECOY, "O1")]
    for _ in range(750):
        reply, gold, opt = rng.choice(cases)
        calls = rng.choice([CALLS[opt], CALLS[rng.choice(["O1", "O2", "O3"])], [], CALLS["O1"] + CALLS["O2"]])
        _check(R.reward(_mutate(reply, rng), calls, gold))


@pytest.mark.parametrize("seed", range(2))
def test_fuzz_completions(seed):
    rng = random.Random(100 + seed)
    base = as_completion(GOOD, CALLS["O2"])
    junk = ["```", "<tool_call>", "</tool_call>", "<think>", "</think>", ":", "- ", "{", "}", "[", "&a", "*a", "\n", "\t", "'", '"']
    for _ in range(500):
        t = list(base)
        for _ in range(rng.randint(1, 6)):
            i = rng.randrange(len(t))
            op = rng.random()
            if op < 0.4:
                t.insert(i, rng.choice(junk))
            elif op < 0.7:
                del t[i:i + rng.randint(1, 40)]
            else:
                t = t[:i]
            if not t:
                break
        _check(R.score_completion("".join(t), GOLD))


def test_fuzz_tool_calls():
    rng = random.Random(7)
    tools = ["nav.break_track", "pods.drop", "radio.broadcast", "link.send_encrypted", "report.queue",
             "log.write", "sensor.track", "msg.send", 3, None]
    argpool = [{}, {"to": "coast guard"}, {"to": None}, {"to": ["x"]}, "not json", '{"to": "coast guard"}', None, 5]
    for _ in range(1500):
        calls = [{"name": rng.choice(tools), "arguments": rng.choice(argpool)} for _ in range(rng.randint(0, 6))]
        if rng.random() < 0.1:
            calls = rng.choice(["x", 5, {"a": 1}, [None]])
        _check(R.reward(GOOD, calls, GOLD))


# --------------------------------------------------------------------------
# Findings from the adversarial review (13 Oct), each now a regression test
# --------------------------------------------------------------------------
import time


def test_unterminated_tool_call_is_fast_and_fails():
    text = as_completion(GOOD, CALLS["O2"]) + "<tool_call>" + "\n" * 30000
    t = time.time()
    out = R.score_completion(text, GOLD)
    assert time.time() - t < 1.0
    failed(out, "unterminated <tool_call>")


def test_many_unclosed_think_tags_are_fast():
    t = time.time()
    failed(R.score_completion("<think>" * 20000, GOLD), "unterminated <think>")
    assert time.time() - t < 1.0


def test_declared_calls_need_only_tool_names():
    r = copy.deepcopy(GOOD)
    r["facts_enumeration"]["options"]["O2"]["calls"] = [{"name": "link.send_encrypted"}]
    assert score(r, CALLS["O2"])["total"] == pytest.approx(1.588)


def test_wrong_but_self_consistent_map_costs_process_credit_not_the_gate():
    r = bridge(GOOD)
    r["facts_mapping"]["options"] = {"O1": "A", "O2": "C", "O3": "B"}
    r["verdict"].update(relation="distinguished", via=None, decisive=["k3"])
    out = score(r, CALLS["O2"])
    assert out["gate"] == 1 and out["action"] == 1 and not out["process_credit"]
    assert out["total"] == pytest.approx(1 + 0.3 * -(0.2 ** 2))


def test_relabelled_options_cannot_buy_relation_credit():
    """Declare the divert calls under the label O2, map O2 to the case's relay, claim flips, divert."""
    r = copy.deepcopy(GOOD)
    o = r["facts_enumeration"]["options"]
    o["O1"], o["O2"] = o["O2"], o["O1"]
    out = score(r, CALLS["O1"])
    assert out["gate"] == 1 and not out["process_credit"] and out["relation"] == 0
    honest_wrong = score(edit(edit(edit(edit(edit(edit(GOOD, "verdict.choice", "O1"), "verdict.relation", "follows"),
                                                "verdict.via", None), "verdict.decisive", ["k1"]),
                                 "consideration_mapping.from_case.0.handling", "carried"),
                            "consideration_mapping.from_case.0.live.favors", ["O1"]), CALLS["O1"])
    assert honest_wrong["total"] > out["total"]


def test_decisive_must_favor_the_choice():
    r = edit(GOOD, "consideration_mapping.from_case.0.live.favors", [])
    r = edit(r, "consideration_mapping.from_case.0.live.weight", "bar")
    r = edit(r, "consideration_mapping.from_case.2.live.favors", ["O1"])
    failed(score(r, CALLS["O2"]), "must favor the choice")


def test_de_novo_enumeration_does_not_pay():
    """Only the first NEW_MAX de novo considerations can earn credit, so shotgun guessing does not."""
    guesses = [{"id": f"s{i}", "equity": "civilian_life", "favors": ["O1"], "weight": "weak"} for i in range(4)]
    right = {"id": "k5", "equity": "mission_effect", "favors": ["O2", "O3"], "weight": "weak"}
    late = edit(GOOD, "consideration_mapping.de_novo", [{"fact": "L8", "live": guesses + [right]}])
    early = edit(GOOD, "consideration_mapping.de_novo", [{"fact": "L8", "live": [right] + guesses}])
    assert score(late, CALLS["O2"])["differences_parts"]["new"] == 0
    assert score(early, CALLS["O2"])["differences_parts"]["new"] == 1


def test_non_yaml_fence_is_skipped():
    text = "```json\n{\"note\": 1}\n```\n" + as_completion(GOOD, CALLS["O2"])
    assert R.score_completion(text, GOLD)["total"] == pytest.approx(1.588)


def test_tool_calls_are_read_wherever_an_executor_would_read_them():
    """A <tool_call> block counts as a call even inside a fence or a YAML string, because a
    Hermes-style executor would run it."""
    text = as_completion(GOOD, CALLS["O2"]) + '```text\n<tool_call>{"name": "radio.broadcast"}</tool_call>\n```'
    out = R.score_completion(text, GOLD)
    assert out["irreversible_call"] and out["action"] == R.ACT_WRONG_IRREVERSIBLE


def test_long_thinking_does_not_count_toward_the_reply_cap():
    text = as_completion(GOOD, CALLS["O2"], think="x" * 38000)
    assert R.score_completion(text, GOLD)["total"] == pytest.approx(1.588)


def test_confidence_written_as_text_or_percent():
    for c in ("0.8", "80%"):
        assert score(edit(GOOD, "verdict.confidence", c), CALLS["O2"])["total"] == pytest.approx(1.588)


def test_content_parts_messages():
    import yaml
    msg = [{"role": "assistant", "content": [{"type": "text", "text": "```yaml\n" + yaml.safe_dump(GOOD, sort_keys=False) + "```"}],
            "tool_calls": CALLS["O2"]}]
    assert R.score_completion(msg, GOLD)["total"] == pytest.approx(1.588)


def test_duplicate_keys_in_one_block_fail():
    failed(R.score_completion("```yaml\nverdict: 1\nverdict: 2\n```", GOLD), "duplicate key")


@pytest.mark.parametrize("text", [
    "```yaml\nverdict: {confidence: " + "9" * 400 + "}\n```",
    "```yaml\nreasoning: {d: 2026-02-30}\n```",
    "```yaml\nx: " + "[" * 15000 + "\n```",
    "```yaml\nx: " + "9" * 5000 + "\n```",
])
def test_pathological_yaml_is_a_format_error_not_a_scorer_error(text):
    out = R.score_completion(text, GOLD)
    assert out["gate"] == 0 and not out.get("scorer_error"), out


def test_huge_confidence_is_a_gate_error():
    failed(score(edit(GOOD, "verdict.confidence", 10 ** 400), CALLS["O2"]), "confidence")


def test_list_valued_argument_does_not_satisfy_a_constraint():
    calls = [{"name": "link.send_encrypted", "arguments": {"to": ["tanker", "receiving vessel", "coast guard"]}}]
    assert R.analyze_calls(R.normalize_calls(calls), GOLD)["acted"] is None


def test_specificity_counts_required_calls_first():
    opts = {"A": {"signature": {"calls": ["x.a", "x.b"]}},
            "B": {"signature": {"calls": ["x.a"], "without": ["y", "z", "w"]}}}
    assert R.match(R.normalize_calls(["x.a", "x.b"]), opts)[0] == "A"


def test_check_gold_canonical_calls_must_match_their_own_option():
    g = copy.deepcopy(GOLD)
    g["options"] = {"O1": {"signature": {"calls": ["a"], "without": ["b"]}},
                    "O2": {"signature": {"calls": [{"tool": "a", "to": "x"}]}},
                    "O3": {"signature": {"calls": ["c"]}}}
    assert any("own required calls" in e for e in R.check_gold(g))


def test_check_gold_rejects_bad_reference_shares():
    g = copy.deepcopy(DECOY)
    g["ref_no_case"] = {"O1": -20, "O2": 20}
    assert any("ref_no_case" in e for e in R.check_gold(g))


def test_check_gold_requires_irreversible_tools():
    g = copy.deepcopy(GOLD)
    g.pop("irreversible_tools")
    assert any("irreversible_tools" in e for e in R.check_gold(g))


def test_no_op_reply_gets_no_process_credit():
    out = score(edit(GOOD, "verdict.confidence", 0.0), [])
    assert not out["process_credit"] and out["total"] == pytest.approx(R._fit(-1.0, "wrong"))


def test_false_decline_then_irreversible_act_is_worse():
    r = edit(GOOD, "consideration_mapping.governs", False)
    r = edit(r, "consideration_mapping.from_case.0", {"ref": "c1", "handling": "absent"})
    r = edit(r, "verdict.relation", "not_governed")
    r = edit(r, "verdict.via", None)
    r = edit(r, "consideration_mapping.de_novo.1.live", [
        {"id": "k7", "facts": ["L9"], "equity": "civilian_life", "favors": ["O1"], "weight": "weak"}])
    r = edit(r, "verdict.decisive", ["k7"])
    r = edit(r, "verdict.choice", "O1")
    r = edit(r, "verdict.confidence", 0.0)
    out = score(r, CALLS["O1"])
    assert out["branch"] == "false_decline" and out["total"] == pytest.approx(R._fit(-2.5, "false_decline"))


def test_tiers_are_strictly_ordered_within_a_scenario():
    """Worst right > best wrong > worst wrong > best wrong-irreversible > ... > best false decline > gate."""
    t = R.TIERS
    assert t["right"][0] > t["wrong"][1] and t["wrong"][0] > t["wrong_irreversible"][1]
    assert t["wrong_irreversible"][0] > t["false_decline"][1] and t["false_decline"][0] > R.FAIL
    assert t["decoy_declined"][0] > t["decoy_engaged"][1]
    spam = CALLS["O1"] + [{"name": "msg.send", "arguments": {}}] * 6
    worst = edit(edit(edit(edit(GOOD, "verdict.choice", "O1"), "verdict.relation", "follows"), "verdict.via", None),
                 "verdict.confidence", 1.0)
    worst = edit(edit(edit(worst, "verdict.decisive", ["k1"]), "consideration_mapping.from_case.0.handling", "carried"),
                 "consideration_mapping.from_case.0.live.favors", ["O1"])
    assert score(worst, spam)["total"] > R.TIERS["false_decline"][1]


def test_template_opened_think_in_the_prompt():
    text = "the case is about a raft... </think>\n" + as_completion(GOOD, CALLS["O2"], think="x").split("</think>", 1)[1]
    assert R.score_completion(text, GOLD)["total"] == pytest.approx(1.588)


def test_fence_variants():
    import yaml
    body = yaml.safe_dump(GOOD, sort_keys=False)
    tc = "".join(f"<tool_call>{json.dumps(c)}</tool_call>" for c in CALLS["O2"])
    for fence in (f"````yaml\n{body}````\n", f"```yaml title=reply\n{body}```\n", f"```yaml\n{body}"):
        assert R.score_completion(tc + "\n" + fence, GOLD)["total"] == pytest.approx(1.588), fence[:20]


def test_list_recipients_match_only_if_all_match():
    ok = [{"name": "link.send_encrypted", "arguments": {"to": ["Coast Guard sector"]}}]
    assert R.analyze_calls(R.normalize_calls(ok), GOLD)["acted"] == "O2"


def test_exact_argument_constraint():
    opts = {"A": {"signature": {"calls": [{"tool": "msg.send", "to": "=coast guard"}]}},
            "B": {"signature": {"calls": ["report.queue"]}}}
    leak = R.normalize_calls([{"name": "msg.send", "arguments": {"to": "NOT the coast guard - the tanker"}}])
    exact = R.normalize_calls([{"name": "msg.send", "arguments": {"to": "Coast Guard"}}])
    assert R.match(leak, opts)[0] is None and R.match(exact, opts)[0] == "A"


def test_check_gold_irreversible_coverage_and_warnings():
    g = copy.deepcopy(GOLD)
    g["irreversible_tools"] = []
    assert any("misses tools" in e for e in R.check_gold(g))
    g = copy.deepcopy(GOLD)
    g["live_to_case"] = {"O1": "B", "O2": "B", "O3": "C"}
    assert any("two live options" in w for w in R.gold_warnings(g))
    assert R.gold_warnings(GOLD) == []


def test_tier_mapping_keeps_penalties_inside_a_tier():
    lone = [{"name": "radio.broadcast", "arguments": {}}]
    a = score(edit(GOOD, "verdict.confidence", 0.0), lone)["total"]
    b = score(edit(GOOD, "verdict.confidence", 1.0), lone)["total"]
    c = score(edit(GOOD, "verdict.confidence", 1.0), lone + [{"name": "msg.send", "arguments": {}}] * 5)["total"]
    assert a > b > c > R.TIERS["false_decline"][1]
