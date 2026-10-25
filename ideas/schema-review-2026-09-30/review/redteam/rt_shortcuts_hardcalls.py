"""RT-8: trivial-classifier shortcuts on the 100 Hard Calls cases.
Predict the outcome letter from surface features only (no situation reading).
Run: python3 rt_shortcuts_hardcalls.py"""
import yaml, collections, os, re, random
HERE = os.path.dirname(os.path.abspath(__file__))
D = yaml.safe_load(open(os.path.join(HERE, "../../src/scenarios/hard-calls-v1/hard-calls-cases.yaml")))

def acc(pred):
    return sum(pred(c) == c["outcome"] for c in D) / len(D)

def argmax(scores, tiebreak):
    best = max(scores.values())
    tied = [k for k in sorted(scores) if scores[k] == best]
    return tiebreak(tied)

rules = {}
rules["majority class (always C)"] = lambda c: "C"
rules["n_options==3 -> C, 4 -> B (fit on all 100)"] = None  # filled below
rules["longest option text"] = lambda c: max(c["options"], key=lambda k: len(str(c["options"][k])))
rules["longest option text, excluding A"] = lambda c: max((k for k in c["options"] if k != "A"), key=lambda k: len(str(c["options"][k])))
rules["most words in option"] = lambda c: max(c["options"], key=lambda k: len(str(c["options"][k]).split()))
rules["most commas/semicolons/'and' in option"] = lambda c: max(c["options"], key=lambda k: len(re.findall(r",|;|\band\b|\bthen\b|\bwhile\b", str(c["options"][k]))))
rules["option with most catalog factors (tie->last)"] = lambda c: argmax(collections.Counter(f["favors"] for f in c["factors"]) | {k: collections.Counter(f["favors"] for f in c["factors"]).get(k, 0) for k in c["options"]}, lambda t: t[-1])
rules["option with most STRONG factors (tie->last)"] = lambda c: argmax({k: sum(1 for f in c["factors"] if f["favors"] == k and f["support"] == "strong") for k in c["options"]}, lambda t: t[-1])
rules["option with FEWEST flip-rule targets (tie->C)"] = lambda c: argmax({k: -sum(1 for r in c["flip_rules"] if r["then"] == k) for k in c["options"]}, lambda t: "C" if "C" in t else t[-1])

# fit a two-feature lookup on 3/4-option count, evaluated by leave-one-out
def nopt_rule_loo():
    hits = 0
    for i, c in enumerate(D):
        rest = D[:i] + D[i + 1:]
        maj = collections.Counter(x["outcome"] for x in rest if len(x["options"]) == len(c["options"])).most_common(1)[0][0]
        hits += maj == c["outcome"]
    return hits / len(D)

print(f"{'rule':60s} acc")
for name, r in rules.items():
    if r is None:
        print(f"{'n_options -> majority outcome (leave-one-out)':60s} {nopt_rule_loo():.2f}"); continue
    print(f"{name:60s} {acc(r):.2f}")

# breakdown
print("\noutcome by n_options:", {n: dict(collections.Counter(c['outcome'] for c in D if len(c['options']) == n)) for n in (3, 4)})
print("outcome letter == last option:", sum(c["outcome"] == sorted(c["options"])[-1] for c in D))
# rank of outcome option by length
ranks = collections.Counter()
for c in D:
    order = sorted(c["options"], key=lambda k: -len(str(c["options"][k])))
    ranks[order.index(c["outcome"])] += 1
print("rank of the winning option by text length (0 = longest):", dict(sorted(ranks.items())))
# mean length winner vs others
wl = [len(str(c["options"][c["outcome"]])) for c in D]
ol = [len(str(v)) for c in D for k, v in c["options"].items() if k != c["outcome"]]
print(f"mean chars: winner {sum(wl)/len(wl):.0f}, non-winners {sum(ol)/len(ol):.0f}")
# option A is the 'tempting wrong answer'?
print("flip-rule 'then' letters:", collections.Counter(r["then"] for c in D for r in c["flip_rules"]))
print("outcome == A in", sum(c["outcome"] == "A" for c in D), "cases")

# ---- robustness: unique-max (no tie-break help) and per-area
def unique_max(scores):
    best = max(scores.values()); t = [k for k in scores if scores[k] == best]
    return t[0] if len(t) == 1 else None
for name, feat in [("strong factors", lambda c, k: sum(1 for f in c["factors"] if f["favors"] == k and f["support"] == "strong")),
                   ("all factors", lambda c, k: sum(1 for f in c["factors"] if f["favors"] == k)),
                   ("option chars", lambda c, k: len(str(c["options"][k])))]:
    u = [unique_max({k: feat(c, k) for k in c["options"]}) for c in D]
    print(f"{name:15s}: unique max in {sum(x is not None for x in u)} cases; unique max == outcome in {sum(x == c['outcome'] for x, c in zip(u, D))}")
by_area = collections.defaultdict(list)
for c in D: by_area[c["id"][:3]].append(max(c["options"], key=lambda k: len(str(c["options"][k]))) == c["outcome"])
print("longest-option accuracy by area:", {a: f"{sum(v)}/{len(v)}" for a, v in by_area.items()})
print("cases where longest option != outcome:", [c["id"] for c in D if max(c["options"], key=lambda k: len(str(c["options"][k]))) != c["outcome"]])

# ---- Distinguish scenarios are generated 'one per flip rule': is their gold readable off the changed factor's ID letter?
plus = [(c, r) for c in D for r in c["flip_rules"] if str(r["change"]).startswith("+")]
minus = [(c, r) for c in D for r in c["flip_rules"] if str(r["change"]).startswith("-")]
hit_plus = sum(r["then"] == str(r["change"])[1] for c, r in plus)
print(f"\n'+X' flip rules: {len(plus)}; then == letter of X in {hit_plus}; then == escalate in {sum(r['then']=='escalate' for c,r in plus)}")
print(f"'-X' flip rules: {len(minus)}; X favors the case outcome in {sum(str(r['change'])[1]==c['outcome'] for c,r in minus)}; "
      f"then distribution {dict(collections.Counter(r['then'] for c,r in minus))}")
# trivial rule for a flip-rule scenario: '+X' -> letter(X); '-X' -> 'A' (the option the case rejected most often)
triv = sum((r["then"] == (str(r["change"])[1] if str(r["change"]).startswith("+") else "A")) for c, r in plus + minus)
print(f"trivial rule ('+X'->letter(X), '-X'->A) on the {len(plus)+len(minus)} factor-keyed flip rules: {triv} correct "
      f"({triv/(len(plus)+len(minus)):.0%}); escalate is {sum(r['then']=='escalate' for c,r in plus+minus)} of them")
