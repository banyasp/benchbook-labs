"""[OURS] Patched variant of solver_v2 used only to show that the proposed fixes remove the counterexamples.
Changes (each behind a flag so the red-team scripts can toggle them):
  per_equity  : a distinction is significant if ANY of its equities is left unsubstituted (not 'any equity downplayed').
  pairwise    : n-ary. A new factor favoring option p is compared only with the precedent's factors favoring p
                (not with every non-winning factor), and blocking in effective() only counts factors of the winning
                side vs. the factor's own side.
  ladder_nary : support() counts >=2 distinct on-point outcomes as 'bounded' (v2 falls through to 'unprecedented' at 3).
"""
S = {"weak": 1, "strong": 2}
side = lambda cat, f: cat[f][0]
edges = lambda cat, f: cat[f][1]

def effective(cat, f, facts, P, pairwise=False, o=None):
    st = dict(edges(cat, f)).get(P)
    if st is None: return 0
    if st == "strong": return 2
    if pairwise and o is not None:
        # only factors favoring the precedent's outcome block an against-factor, and vice versa
        opp = (lambda g: side(cat, g) == o) if side(cat, f) != o else (lambda g: side(cat, g) != o)
    else:
        opp = lambda g: side(cat, g) != side(cat, f)
    return 0 if any(opp(g) and dict(edges(cat, g)).get(P) == "strong" for g in facts) else 1

def analyse(cat, case, Y, per_equity=False, pairwise=False):
    X, o, R = case["facts"], case["outcome"], case["reason"]
    if not (R & Y): return "off_point", []
    D = [(f, 1) for f in sorted(R - Y)] + [(f, 2) for f in sorted(Y) if side(cat, f) != o and f not in X]
    out = []
    for f, kind in D:
        emph = down = False
        for P, st in edges(cat, f):
            need = S[st]
            if kind == 1:
                alt = max([effective(cat, g, Y, P, pairwise, o) for g in Y if g != f and side(cat, g) == o] or [0])
            else:
                if effective(cat, f, Y, P, pairwise, o) == 0: continue
                pool = [g for g in X if side(cat, g) == side(cat, f)] if pairwise else [g for g in X if side(cat, g) != o]
                alt = max([effective(cat, g, X, P, pairwise, o) for g in pool] or [0])
            if alt >= need: down = True
            else: emph = True
        sig = cat[f][2] or (emph if per_equity else (emph and not down))
        out.append({"factor": f, "kind": ["", "missing_reason", "new_against"][kind],
                    "equities": [P for P, _ in edges(cat, f)], "significant": sig})
    if not out: return "binding", out
    return ("distinguish" if any(d["significant"] for d in out) else "analogous"), out

def support(cat, casebook, Y, per_equity=False, pairwise=False, ladder_nary=False):
    res = {cid: analyse(cat, c, Y, per_equity, pairwise) for cid, c in casebook.items()}
    for level in ("binding", "analogous"):
        sides = {casebook[cid]["outcome"] for cid, (lab, _) in res.items() if lab == level}
        if len(sides) == 1: return level, sides.pop(), res
        if len(sides) > 1: return "bounded", None, res
    on_point = {casebook[cid]["outcome"] for cid, (lab, _) in res.items() if lab != "off_point"}
    if (len(on_point) >= 2) if ladder_nary else (len(on_point) == 2): return "bounded", None, res
    if len(on_point) == 1: return "open", None, res
    return "unprecedented", None, res
