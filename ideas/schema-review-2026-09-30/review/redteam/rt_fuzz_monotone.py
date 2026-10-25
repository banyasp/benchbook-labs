"""Fuzz: does solver_v2 respect a fortiori monotonicity in the BINARY case?
Adding a factor that favors the precedent's outcome to Y (or removing one against it) must never make a
binding/analogous precedent distinguished/off_point. Run on the VEP catalog and the DOHA catalog.
Run: python3 rt_fuzz_monotone.py"""
import random
from solver_v2 import VEP, CB, analyse
from doha_common import load
random.seed(0)
GOOD = ("binding", "analogous")
def fuzz(cat, cases, n=20000):
    fids = sorted(cat); viol = []
    for _ in range(n):
        cid = random.choice(sorted(cases)); c = cases[cid]
        Y = set(random.sample(fids, random.randint(1, min(8, len(fids)))))
        lab, _ = analyse(cat, c, Y)
        if lab not in GOOD: continue
        for f in fids:
            if cat[f][0] == c["outcome"] and f not in Y:
                Y2 = Y | {f}
            elif cat[f][0] != c["outcome"] and f in Y:
                Y2 = Y - {f}
            else: continue
            lab2, _ = analyse(cat, c, Y2)
            if lab2 not in GOOD: viol.append((cid, sorted(Y), f, lab, lab2))
    return viol
cat, _, cases = load()
for name, ct, cb in [("VEP", VEP, CB), ("DOHA-F", cat, cases)]:
    v = fuzz(ct, cb)
    print(f"{name}: a-fortiori violations found: {len(v)}", v[:3])
