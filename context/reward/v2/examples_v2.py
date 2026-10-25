"""Worked examples for reward_v2 on LIVE-MAR-001a (gold: flips via w1, relay = O2) and a decoy.
Run: python3 examples_v2.py > examples_v2.out"""
import json

import reward_v2 as R
from fixtures_v2 import CALLS, DECOY, GOLD, GOOD, decoy_engaged_reply, decoy_reply, edit

rows = []


def run(label, reply, calls, gold):
    rows.append((label, R.reward(reply, calls, gold)))


def chain(reply, *edits):
    for path, value in edits:
        reply = edit(reply, path, value)
    return reply


run("Gold reply: flips via w1, relays, confidence 0.8", GOOD, CALLS["O2"], GOLD)
run("Right action, but says distinguished",
    chain(GOOD, ("verdict.relation", "distinguished"), ("verdict.via", None)), CALLS["O2"], GOLD)
run("Right action, misses that c3 changed (calls it carried, consistently)",
    chain(GOOD, ("consideration_mapping.from_case.2.handling", "carried"),
          ("consideration_mapping.from_case.2.live.weight", "weak")), CALLS["O2"], GOLD)
run("Right action plus two extra tool calls",
    GOOD, CALLS["O2"] + [{"name": "msg.send", "arguments": {}}, {"name": "ticket.open", "arguments": {}}], GOLD)
run("Copies the case: follows, diverts (irreversible)",
    chain(GOOD, ("verdict.choice", "O1"), ("verdict.relation", "follows"), ("verdict.via", None),
          ("verdict.decisive", ["k1"]), ("verdict.confidence", 0.7),
          ("consideration_mapping.from_case.0.handling", "carried"),
          ("consideration_mapping.from_case.0.live.favors", ["O1"]),
          ("consideration_mapping.from_case.2.handling", "carried"),
          ("consideration_mapping.from_case.2.live.weight", "weak")), CALLS["O1"], GOLD)
run("Says flips via w1 (relay) but its calls divert", GOOD, CALLS["O1"], GOLD)
run("Writes the right mapping, makes no tool call", GOOD, [], GOLD)
run("Declines a case that governs",
    chain(GOOD, ("consideration_mapping.governs", False),
          ("consideration_mapping.from_case.0", {"ref": "c1", "handling": "absent"}),
          ("verdict.relation", "not_governed"), ("verdict.via", None), ("verdict.decisive", ["k5"])), CALLS["O2"], GOLD)
run("Decoy: declines, then relays (the usual no-case answer)", decoy_reply("O2"), CALLS["O2"], DECOY)
run("Decoy: declines, then holds (rare without a case)", decoy_reply("O3"), CALLS["O3"], DECOY)
run("Decoy: treats it as governing and follows it", decoy_engaged_reply(), CALLS["O1"], DECOY)
run("Decoy: declines, but its calls do something else than its verdict", decoy_reply("O2"), CALLS["O3"], DECOY)
run("Decoy: declines, but cites the case's w1", decoy_reply("O2", via="w1"), CALLS["O2"], DECOY)

for label, out in rows:
    keep = {k: out[k] for k in ("branch", "acted", "say_do", "process_credit") if k in out}
    print(f"{out['total']:>7.3f}  {label}\n          {json.dumps(keep)}\n          contrib {json.dumps(out['contrib'])}"
          + (f"\n          errors: {out['errors']}" if out.get("errors") else ""))
