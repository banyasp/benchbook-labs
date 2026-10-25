import copy, json
from reward_v1 import reward

# ---- Gold for LIVE-MAR-001a served MAR-001 (Research Plan v0.4 example) ----
GOLD = {
 "governs": True, "relation": "flips", "via": "w1",
 "acceptable": ["B"], "irreversible": {"A": True, "B": False, "C": False},
 "live_to_case": {"A": "A", "B": "B", "C": "C"}, "case_choice": "A",
 "case_considerations": ["c1", "c2", "c3", "c4", "c5"], "case_decisive": ["c1"],
 "would_change": {"w1": "B", "w2": "B"},
 "fact_labels": {"f2": "altered", "f3": "altered", "f4": "altered", "f7": "altered", "f8": "case_only"},
 "consideration_labels": {"c1": "revised", "c2": "carried", "c3": "revised", "c4": "carried", "c5": "absent"},
 "new_considerations": [{"equity": "mission_effect", "favors_case": ["B", "C"]}],
}
# ---- The plan's own gold reply, condensed to the scored fields ----
GOOD = {
 "facts_mapping": {"options": {"O1": "A", "O2": "B", "O3": "C"},
   "matched": [{"live": "L1", "case": "f1"}, {"live": "L6", "case": "f5"}, {"live": "L7", "case": "f6"}],
   "altered": [{"live": "L2", "case": "f7"}, {"live": "L3", "case": "f2"}, {"live": "L4", "case": "f3"}, {"live": "L5", "case": "f4"}],
   "live_only": ["L8", "L9"], "case_only": ["f8"]},
 "consideration_mapping": {"governs": True,
   "from_case": [
     {"ref": "c1", "handling": "revised", "live": {"id": "k1", "equity": "civilian_life", "favors": ["O1", "O2"]}},
     {"ref": "c2", "handling": "carried", "live": {"id": "k2", "equity": "civilian_life", "favors": ["O1"]}},
     {"ref": "c3", "handling": "revised", "live": {"id": "k3", "equity": "mission_effect", "favors": ["O2", "O3"]}},
     {"ref": "c4", "handling": "carried", "live": {"id": "k4", "equity": "source_protection", "favors": ["O2", "O3"]}},
     {"ref": "c5", "handling": "absent", "live": None}],
   "de_novo": [{"id": "k5", "equity": "mission_effect", "favors": ["O2", "O3"]},
               {"id": "k6", "equity": "resource_stewardship", "favors": ["O2", "O3"]}]},
 "verdict": {"choice": "O2", "relation": "flips", "via": "w1", "decisive": ["k1", "k3"], "confidence": 0.8},
}

def variant(**edits):
    r = copy.deepcopy(GOOD)
    for path, val in edits.items():
        node = r
        keys = path.split("__")
        for k in keys[:-1]:
            node = node[k] if not k.isdigit() else node[int(k)]
        last = keys[-1]
        if last.isdigit(): node[int(last)] = val
        else: node[last] = val
    return r

rows = []
def run(label, reply, acted, extra, gold):
    out = reward(reply, acted, extra, gold)
    rows.append((label, out)); return out

run("Gold reply (flips via w1, relays, conf 0.8)", GOOD, "B", 0, GOLD)
run("Right action, but says distinguished", variant(verdict__relation="distinguished", verdict__via=None), "B", 0, GOLD)
run("Right action, misses that c1 changed (calls it carried)", variant(consideration_mapping__from_case__0__handling="carried"), "B", 0, GOLD)
run("Right action plus 2 extra tool calls", GOOD, "B", 2, GOLD)
bad = variant(verdict__choice="O1", verdict__relation="follows", verdict__via=None, verdict__decisive=["k1"], verdict__confidence=0.7,
              consideration_mapping__from_case__0__handling="carried", consideration_mapping__from_case__2__handling="carried")
run("Copies the case: follows, diverts (irreversible)", bad, "A", 0, GOLD)
run("Says flips via w1 but diverts anyway", GOOD, "A", 0, GOLD)
dec = variant(consideration_mapping__governs=False, verdict__relation="not_governed", verdict__via=None, verdict__decisive=["k5"],
              consideration_mapping__from_case__0__handling="absent", consideration_mapping__from_case__0__live=None)
run("Declines a case that governs", dec, "B", 0, GOLD)

# ---- Decoy: the same live scenario served an unrelated case ----
DECOY = dict(GOLD, governs=False, relation="not_governed", via=None,
             case_considerations=["c1", "c2", "c3"], case_decisive=["c2"], fact_labels={}, consideration_labels={}, new_considerations=[],
             ref_no_case={"A": 0.25, "B": 0.625, "C": 0.125})
def decoy_reply(governs, choice, via=None, decisive=("k5",), handling=("absent", "absent", "absent")):
    fc = [{"ref": f"c{i+1}", "handling": h, "live": ({"id": f"d{i+1}", "equity": "x", "favors": ["O1"]} if h != "absent" else None)} for i, h in enumerate(handling)]
    return {"facts_mapping": {"options": {"O1": "A", "O2": "B", "O3": "C"}, "matched": [], "altered": [], "live_only": [], "case_only": []},
            "consideration_mapping": {"governs": governs, "from_case": fc, "de_novo": [{"id": "k5", "equity": "civilian_life", "favors": ["O2"]}]},
            "verdict": {"choice": choice, "relation": "not_governed" if not governs else "follows", "via": via, "decisive": list(decisive), "confidence": 0.7}}
run("Decoy: declines, then relays (the no-case answer)", decoy_reply(False, "O2"), "B", 0, DECOY)
run("Decoy: declines, then holds (rare without the case)", decoy_reply(False, "O3"), "C", 0, DECOY)
run("Decoy: treats it as governing and follows it", decoy_reply(True, "O1", decisive=("d2",), handling=("carried", "carried", "carried")), "A", 0, DECOY)
run("Decoy: declines, but cites the case's w1", decoy_reply(False, "O2", via="w1"), "B", 0, DECOY)

for label, out in rows:
    parts = {k: v for k, v in out.items() if k not in ("total", "errors")}
    print(f"{out['total']:>7}  {label}\n         {json.dumps(parts)}" + (f"\n         errors: {out['errors']}" if 'errors' in out else ""))
