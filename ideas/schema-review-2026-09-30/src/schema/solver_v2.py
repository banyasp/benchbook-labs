"""Reference solver v2 for the Extension Training schema (2026-09-28).
v1: one precedent -> distinctions (Horty reason model) + significance (Zhang et al., strength-aware downplay).
v2 adds: a case base, the support ladder, the residual judgment, and the stakes-aware act-or-ask threshold."""
S = {"weak": 1, "strong": 2}

def side(cat, f): return cat[f][0]
def edges(cat, f): return cat[f][1]

def effective(cat, f, facts, P):
    st = dict(edges(cat, f)).get(P)
    if st is None: return 0
    if st == "strong": return 2
    blocked = any(side(cat, g) != side(cat, f) and dict(edges(cat, g)).get(P) == "strong" for g in facts)
    return 0 if blocked else 1

def analyse(cat, case, Y):
    """One precedent against situation Y -> (label, distinctions). label: binding | analogous | distinguish | off_point"""
    X, o, R = case["facts"], case["outcome"], case["reason"]
    loser_X = {f for f in X if side(cat, f) != o}
    if not (R & Y): return "off_point", []
    D = [(f, 1) for f in sorted(R - Y)] + [(f, 2) for f in sorted(Y) if side(cat, f) != o and f not in loser_X]
    out = []
    for f, kind in D:
        emph = down = False
        for P, st in edges(cat, f):
            need = S[st]
            if kind == 1:
                alt = max([effective(cat, g, Y, P) for g in Y if g != f and side(cat, g) == o] or [0])
            else:
                if effective(cat, f, Y, P) == 0: continue
                alt = max([effective(cat, g, X, P) for g in loser_X] or [0])
            if alt >= need: down = True
            else: emph = True
        out.append({"factor": f, "kind": ["", "missing_reason", "new_against"][kind],
                    "equities": [P for P, _ in edges(cat, f)], "significant": cat[f][2] or (emph and not down)})
    if not out: return "binding", out
    return ("distinguish" if any(d["significant"] for d in out) else "analogous"), out

def support(cat, casebook, Y):
    """The support ladder over the whole case base."""
    res = {cid: analyse(cat, c, Y) for cid, c in casebook.items()}
    for level in ("binding", "analogous"):
        sides = {casebook[cid]["outcome"] for cid, (lab, _) in res.items() if lab == level}
        if len(sides) == 1: return level, sides.pop(), res
        if len(sides) > 1: return "bounded", None, res          # precedents pull both ways
    on_point = {casebook[cid]["outcome"] for cid, (lab, _) in res.items() if lab != "off_point"}
    if len(on_point) == 2: return "bounded", None, res
    if len(on_point) == 1: return "open", None, res
    return "unprecedented", None, res

def residual(cat, case, Y, dist):
    """Equities the precedent still settles vs the ones its significant distinctions reopen."""
    open_eq = sorted({P for d in dist if d["significant"] for P in d["equities"]})
    all_eq = sorted({P for f in Y for P, _ in edges(cat, f)})
    return {"settled": [e for e in all_eq if e not in open_eq], "open": open_eq}

def threshold(L, k):
    """Act alone iff P(correct) exceeds this: +1 right, -L wrong, -k to ask (Chow's reject rule)."""
    return (L - k) / (1 + L)

VEP = {
 "D1": ("disclose", [("exposure", "strong")], False),
 "D2@moderate": ("disclose", [("threat", "weak")], False),
 "D2@high": ("disclose", [("threat", "strong")], False),
 "D3": ("disclose", [("threat", "strong")], False),
 "D4": ("disclose", [("partners", "strong")], False),
 "D6": ("disclose", [("exposure", "strong")], False),
 "R1": ("retain", [("target_value", "weak")], False),
 "R2": ("retain", [("target_value", "strong")], False),
 "R3": ("retain", [("need_now", "strong")], False),
 "R4": ("retain", [("no_substitute", "strong")], False),
 "R5": ("retain", [("exposure", "strong")], False),
 "R6": ("retain", [("target_value", "strong")], False),   # target central to strategic early warning
}
CB = {
 "VEP-001": {"facts": {"D1", "D2@moderate", "R1", "R2", "R3"}, "outcome": "retain", "reason": {"R2", "R3"}},
 "VEP-004": {"facts": {"D1", "D2@moderate", "D2@high", "D3", "R1", "R3"}, "outcome": "disclose", "reason": {"D2@high", "D3"}},
}
situations = {
 "new: NC3 node + exploitation + allies": {"D1", "D2@moderate", "D2@high", "D3", "D4", "R1", "R2", "R3"},
 "forced by VEP-004 (VEP-001 distinguished)": {"D1", "D2@moderate", "D2@high", "D3", "R1", "R3"},
 "analogous: early-warning node instead of NC3": {"D1", "D2@moderate", "R1", "R6", "R3"},
 "unprecedented": {"D4", "R4"},
}
if __name__ == "__main__":
    for name, Y in situations.items():
        level, outcome, res = support(VEP, CB, Y)
        print(f"{name}: {level} {outcome or ''}")
        for cid, (lab, dist) in res.items():
            sig = [d["factor"] for d in dist if d["significant"]]
            print(f"   {cid}: {lab}  significant={sig}")
        lab, dist = res["VEP-001"]
        if lab == "distinguish": print("   residual vs VEP-001:", residual(VEP, CB["VEP-001"], Y, dist))
    print("threshold VEP (L=9,k=0.5):", threshold(9, 0.5), " low stakes (L=1,k=0.2):", threshold(1, 0.2))
