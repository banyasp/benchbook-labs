"""RT-10/RT-11/RT-12 on the real DOHA Guideline F pilot (10 cases, unmodified solver_v2).
 (a) circularity: how much of the verdict a trivial tag rule recovers (leave-one-out selection)
 (b) sensitivity: how often ONE tag error changes the harness action (leave-one-out casebooks)
 (c) Horty consistency of the casebook
Run: python3 rt_doha.py"""
import collections, itertools
from doha_common import load
from solver_v2 import support, analyse

cat, default, cases = load(with_doctrine=False)
A = lambda Y: sorted(f for f in Y if cat[f][0] == "A")
B = lambda Y: sorted(f for f in Y if cat[f][0] == "B")

# ---------------- (a) circularity ----------------
print("== (a) circularity: trivial rules on judge-perception tags ==")
for cid, c in cases.items():
    print(f"  {cid} real={c['outcome']}  #A-tags={len(A(c['facts']))}  #B-tags={len(B(c['facts']))}")
rules = {
    "grant iff #A-tags >= 4": lambda Y: "A" if len(A(Y)) >= 4 else "B",
    "grant iff A20a or A20b2 tagged": lambda Y: "A" if {"A20a", "A20b2"} & Y else "B",
    "grant iff #A-tags - #B-tags >= 2": lambda Y: "A" if len(A(Y)) - len(B(Y)) >= 2 else "B",
}
for name, r in rules.items():
    print(f"  {name:38s} {sum(r(c['facts']) == c['outcome'] for c in cases.values())}/10")
# leave-one-out: pick the #A-tags threshold on 9 cases, apply to the 10th (no peeking)
hits = 0
for hid, h in cases.items():
    train = [c for k, c in cases.items() if k != hid]
    best = max(range(0, 8), key=lambda t: (sum((("A" if len(A(c["facts"])) >= t else "B") == c["outcome"]) for c in train), -t))
    hits += (("A" if len(A(h["facts"])) >= best else "B") == h["outcome"])
print(f"  LOO-selected threshold on #A-tags:      {hits}/10   (solver LOO decided 4/10, all correct; 6 left bounded)")

# ---------------- (b) one-tag sensitivity ----------------
print("\n== (b) one-tag sensitivity of the harness action (LOO casebook = other 9) ==")
def close(Y):
    Y = set(Y)
    if "A20d@established" in Y: Y.add("A20d@initiated")
    return Y
def action(cb, Y):
    lvl, out, _ = support(cat, cb, Y)
    return (lvl, out if lvl in ("binding", "analogous") else "ask")
tally = collections.Counter(); per_case = {}
examples = []
for hid, h in cases.items():
    cb = {k: v for k, v in cases.items() if k != hid}
    Y0 = h["facts"]; base = action(cb, Y0)
    perts = [("+" + f, close(Y0 | {f})) for f in cat if f not in Y0] + \
            [("-" + f, close(Y0 - {f}) if f != "A20d@initiated" else Y0 - {"A20d@initiated", "A20d@established"}) for f in Y0]
    ch = 0
    for name, Y in perts:
        new = action(cb, Y)
        kind = None
        if new[1] != base[1]:
            ch += 1
            if base[1] == "ask": kind = "ask->act(right)" if new[1] == h["outcome"] else "ask->act(WRONG)"
            elif new[1] == "ask": kind = "act->ask"
            else: kind = "act->act(flipped)"
            tally[kind] += 1
            if kind in ("ask->act(WRONG)", "act->act(flipped)") and len(examples) < 8:
                examples.append((hid, h["outcome"], base, name, new))
        tally["total"] += 1
    per_case[hid] = (base, ch, len(perts))
for hid, (base, ch, n) in per_case.items():
    print(f"  {hid} real={cases[hid]['outcome']}  base action={base}  one-tag perturbations that change the action: {ch}/{n}")
print("  totals:", dict(tally))
print("  examples of one-tag errors that produce a WRONG autonomous act:")
for e in examples: print("    ", e)

# focused: the over-tag the pilot warns about (B19b 'unwillingness', which judges left unargued)
print("\n  adding B19b (the over-tag the pilot notes an unconstrained extractor would make):")
for hid, h in cases.items():
    cb = {k: v for k, v in cases.items() if k != hid}
    print(f"    {hid} real={h['outcome']}: {action(cb, h['facts'])} -> {action(cb, h['facts'] | {'B19b'})}")

# ---------------- (c) Horty consistency ----------------
print("\n== (c) Horty consistency: pairs of opposite-outcome precedents that would BOTH bind some situation ==")
bad = []
for (p, P), (q, Q) in itertools.combinations(cases.items(), 2):
    if P["outcome"] == Q["outcome"]: continue
    Y = close(P["reason"] | Q["reason"])
    lp, _ = analyse(cat, P, Y); lq, _ = analyse(cat, Q, Y)
    if lp in ("binding", "analogous") and lq in ("binding", "analogous"):
        bad.append((p, lp, q, lq, sorted(Y)))
print(f"  opposite-outcome pairs that both bind/are analogous on Y = R_p ∪ R_q: {len(bad)}")
for b in bad[:8]: print("    ", b)
