import re, sys, yaml
sys.path.insert(0, "/home/claude/benchbook/reward")
import reward_v2 as R
docs = list(yaml.safe_load_all(open(sys.argv[1])))
D = {d["kind"]: d for d in docs}
eq = {e["id"] for e in D["equities"]["equities"]}
case, disc, fm = D["case"], D["discretization"], D["fact_mapping"]
ce, cm, ap, rs, vd, ts, tc = (D[k] for k in ("consideration_enumeration", "consideration_mapping", "applicability", "reasoning", "verdict", "trace_summary", "tool_calls"))
gold = ts["gold"]
errs = []
def need(c, m):
    if not c: errs.append(m)
live_f = [f["id"] for f in disc["facts"]]; case_f = [f["id"] for f in case["facts"]]
need(live_f == [f"LIVE-F{i}" for i in range(1, len(live_f)+1)], "live facts numbered in order")
used_l = [x["live"] for b in ("matched","altered") for x in fm[b]] + fm["live_only"]
used_c = [x["case"] for b in ("matched","altered") for x in fm[b]] + fm["case_only"]
need(sorted(used_l) == sorted(live_f), "each live fact exactly once"); need(sorted(used_c) == sorted(case_f), "each case fact exactly once")
lopts, copts = list(disc["options"]), list(case["scenario"]["options"])
omap = fm["options"]; need(set(omap) == set(lopts) and all(v in copts or v is None for v in omap.values()), "options map")
lc = {c["id"]: c for c in ce["considerations"]}; cc = {c["id"]: c for c in case["considerations"]}
for c in lc.values():
    need(set(c["facts"]) <= set(live_f), f"{c['id']} facts"); need(c["equity"] in eq, f"{c['id']} equity injected")
    need(set(c["favors"]) <= set(lopts), f"{c['id']} favors"); need(c["weight"] in R.WEIGHTS, f"{c['id']} weight")
ul = [x["live"] for b in ("carried","revised") for x in cm[b]] + cm["live_only"]
uc = [x["case"] for b in ("carried","revised") for x in cm[b]] + [x if isinstance(x, str) else x["case"] for x in cm["case_only"]]
need(sorted(ul) == sorted(lc), "each live consideration exactly once"); need(sorted(uc) == sorted(cc), "each case consideration exactly once")
for b in ("carried", "revised"):
    for x in cm[b]:
        l, c = lc[x["live"]], cc[x["case"]]
        same = l["equity"] == c["equity"] and {omap[o] for o in l["favors"]} == set(c["favors"]) and l["weight"] == c["weight"]
        need(l["equity"] == c["equity"], f"{x} equity"); need(same == (b == "carried"), f"{x} content fits {b}")
handled = {x["case"]: b for b in ("carried","revised") for x in cm[b]}
case_dec = case["verdict"]["decisive"]
gov = ap["frame"]["question"] != "different" and any(handled.get(c) in ("carried","revised") for c in case_dec)
need(ap["governs"] == gov, "applicability rule"); need(ap["frame"] == {k: fm["frame"][k] for k in ("question","decider","role")}, "frame copied")
need((vd["relation"] == "not_governed") == (not ap["governs"]), "governs <-> relation")
need(omap[vd["choice"]] == case["verdict"]["choice"] if vd["relation"] == "follows" else True, "follows keeps the case's choice")
from_dec = {x["live"] for b in ("carried","revised") for x in cm[b] if x["case"] in case_dec}
need(set(vd["decisive"]) & from_dec, "rests on a case-decisive consideration")
need(all(vd["choice"] in lc[d]["favors"] for d in vd["decisive"]), "decisive favor the choice")
need(vd["via"] is None, "no via for follows")
# gold agreement
need(vd["relation"] == gold["relation"] and vd["choice"] in gold["acceptable"], "gold relation and choice")
need(gold["facts"]["live_only"] == fm["live_only"] and gold["facts"]["case_only"] == fm["case_only"], "gold facts")
need(gold["considerations"] == {c: handled.get(c, "case_only") for c in cc}, "gold considerations")
need(gold["live_to_case"] == omap, "gold options map")
need(any(lc[k]["equity"] == n["equity"] and set(lc[k]["favors"]) == set(n["favors"]) for k in cm["live_only"] for n in gold["new_considerations"]), "planted new consideration found")
need({c["id"]: c["favors"] for c in cc.values()} and True, "")
for k, o in gold["options"].items():
    need(R.match(R._canonical_calls(o["signature"]), gold["options"])[0] == k, f"signature {k} matches itself")
info = R.analyze_calls(R.normalize_calls(tc["calls"]), gold)
need(info["acted"] == vd["choice"] and info["extra_calls"] == 0, f"tool calls carry out the verdict: {info}")
# every id mentioned anywhere is defined
defined = set(live_f) | set(case_f) | set(lc) | set(cc) | set(lopts) | set(copts)
defined |= {w["id"] for k in ("would_change","would_not_change","watch_for") for w in case["flip_conditions"][k]}
defined |= {w["id"] for k in ("would_change","would_not_change","watch_for") for w in vd["flip_conditions"][k]}
text = open(sys.argv[1]).read()
mentioned = set(re.findall(r"\b(?:REF1|LIVE)-(?:F|C|O|flip|noflip|watch)\d+\b", text))
need(mentioned <= defined, f"undefined ids: {sorted(mentioned - defined)}")
print("errors:", errs or "none")
print("words, agent steps 3-9:", sum(len(yaml.safe_dump(D[k]).split()) for k in ("discretization","fact_mapping","consideration_enumeration","consideration_mapping","applicability","reasoning","verdict")))
