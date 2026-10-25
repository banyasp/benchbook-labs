"""Fix evaluation on DOHA: leave-one-out coverage/accuracy and one-tag wrong-act count, solver_v2 vs per-equity patch.
Run: python3 rt_doha_fix.py"""
from doha_common import load
import solver_v2 as V, solver_patched as P
cat, default, cases = load()
def close(Y):
    Y = set(Y)
    if "A20d@established" in Y: Y.add("A20d@initiated")
    return Y
def act(sup, cb, Y):
    lvl, out, _ = sup(cat, cb, Y)
    return out if lvl in ("binding", "analogous") else "ask"
for name, sup in [("solver_v2", V.support), ("per-equity", lambda c, cb, Y: P.support(c, cb, Y, per_equity=True))]:
    dec = cor = wrong = changed = tot = 0
    for hid, h in cases.items():
        cb = {k: v for k, v in cases.items() if k != hid}
        a0 = act(sup, cb, h["facts"])
        if a0 != "ask": dec += 1; cor += a0 == h["outcome"]
        for f in cat:
            Y = close(h["facts"] | {f}) if f not in h["facts"] else (close(h["facts"] - {f}) if f != "A20d@initiated" else h["facts"] - {"A20d@initiated", "A20d@established"})
            a = act(sup, cb, Y); tot += 1
            if a != a0:
                changed += 1
                if a not in ("ask", h["outcome"]): wrong += 1
    print(f"{name:11s}: LOO decided by precedent {dec}/10 (correct {cor}); one-tag perturbations changing the action {changed}/{tot}; "
          f"producing a WRONG autonomous act {wrong}/{tot}")
