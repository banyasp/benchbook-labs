"""RT-6/RT-9 support: structural checks on the 100 Hard Calls cases (n-ary lumping exposure, flip-rule determinacy).
Run: python3 rt_hardcalls_structure.py"""
import yaml, collections, os, re, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
D = yaml.safe_load(open(os.path.join(HERE, "../../src/scenarios/hard-calls-v1/hard-calls-cases.yaml")))
S = {"weak": 1, "strong": 2}
def strength(f):
    # a scaled factor's strongest step counts
    if f.get("scale"): return max(S[v] for v in f["scale"].values())
    return S[f["support"]]

# (1) Lumping exposure: two factors favoring DIFFERENT non-winning options share an equity,
#     so solver_v2 would let one downplay a new instance of the other (loser_X lumps them).
lump = []
for c in D:
    o = c["outcome"]; F = c["factors"]
    pairs = [(f["id"], g["id"], f["equity"]) for f, g in itertools.permutations(F, 2)
             if f["favors"] != o and g["favors"] != o and f["favors"] != g["favors"]
             and f["equity"] == g["equity"] and strength(g) >= strength(f)]
    if pairs: lump.append((c["id"], pairs[:3]))
print(f"(1) cases where a factor for one losing option could be 'downplayed' by a factor for a DIFFERENT losing option on the same equity: {len(lump)}/100")
for x in lump[:6]: print("    ", x)

# (1b) same-equity factors favoring the winner and a loser: weak winner factors that a strong loser factor would 'block' in effective()
block = [c["id"] for c in D if any(f["favors"] == c["outcome"] and strength(f) == 1 and any(g["favors"] != c["outcome"] and g["equity"] == f["equity"] and strength(g) == 2 for g in c["factors"]) for f in c["factors"])]
print(f"(1b) cases where a weak factor for the WINNING option shares an equity with a strong factor for some other option (blocked by effective()): {len(block)}/100")

# (2) equities spanning >= 3 options within one case (two-sided 'for/against' has no meaning)
span = [c["id"] for c in D if any(len({f["favors"] for f in c["factors"] if f["equity"] == e}) >= 3 for e in {f["equity"] for f in c["factors"]})]
print(f"(2) cases with an equity that has factors favoring 3+ different options: {len(span)}/100")

# (3) flip-rule determinacy: same factor change, different 'then'
ids = lambda c: {f["id"] for f in c["factors"]}
same_change_diff_then, unknown_ids, plus_reason, n_factor_rules = [], [], [], 0
for c in D:
    by = collections.defaultdict(set)
    for r in c["flip_rules"]:
        ch = str(r["change"]).strip()
        if ch == "new": continue
        n_factor_rules += 1
        by[ch].add(r["then"])
        for tok in re.findall(r"[A-D]\d+(?:@\w+)?", ch):
            if tok.split("@")[0] not in ids(c): unknown_ids.append((c["id"], ch))
        if ch.startswith("+") and ch[1:] in c["reason"]: plus_reason.append((c["id"], ch))
    for ch, thens in by.items():
        if len(thens) > 1: same_change_diff_then.append((c["id"], ch, sorted(thens)))
print(f"(3) factor-keyed flip rules: {n_factor_rules}; same factor change mapped to different 'then' within a case: {len(same_change_diff_then)}", same_change_diff_then[:6])
print(f"    flip rules whose change names a factor ID not in the case: {len(unknown_ids)}", unknown_ids[:5])
print(f"    '+X' flip rules where X is already in the reason set: {len(plus_reason)}", plus_reason[:5])
# (4) flip rules whose 'then' equals the case outcome (a 'flip' that doesn't flip)
noflip = [(c["id"], r["change"]) for c in D for r in c["flip_rules"] if r["then"] == c["outcome"]]
print(f"(4) flip rules whose 'then' is the case's own outcome: {len(noflip)}", noflip[:5])
# (5) factor-keyed rules that fire on a single-factor change and point at the ORIGINAL 'tempting' option A
print("(5) 'then' distribution for factor-keyed rules:", collections.Counter(r["then"] for c in D for r in c["flip_rules"] if str(r["change"]).strip() != "new"))
# (6) mixed-side reason sets
mixed = [c["id"] for c in D if any(f[0] != c["outcome"] for f in c["reason"])]
print(f"(6) reason sets containing a factor that favors a non-winning option: {len(mixed)}/100 (known: 21)")
# (7) no 'facts' field: the precedent's X is undefined, so loser_X (and new_against distinctions) cannot be computed
print("(7) cases with a structured facts list:", sum('facts' in c for c in D), "/100")
