"""Reference RLVR reward for the Benchbook (v1 spec, 2026-09-28). Built on solver_v2."""
from solver_v2 import VEP, support, analyse, residual

W_TAG, W_REASON, W_CAL, RHO = 0.5, 1.0, 0.5, 0.25

def f1(pred, gold):
    pred, gold = set(pred), set(gold)
    if not pred and not gold: return 1.0
    if not pred or not gold: return 0.0
    p, r = len(pred & gold) / len(pred), len(pred & gold) / len(gold)
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)

def threshold(L, k, rho=RHO):
    """Confidence above which acting alone beats asking, given +1 / -L / -k + rho."""
    return (L - k) / (1 + L - rho)

def harness_action(cat, casebook, tags, resolution, conf, L, k, unlisted, may_act=True):
    """The harness, not the model, decides: solver on the MODEL's tags, then the confidence gate."""
    if not may_act or unlisted: return ("ask", None)
    level, outcome, _ = support(cat, casebook, set(tags))
    if level in ("binding", "analogous"): return ("act", outcome)
    if resolution and conf >= threshold(L, k): return ("act", resolution)
    return ("ask", None)

def reward(out, gold, cat, casebook, L, k):
    """out: parsed model output; gold: scenario labels. Returns (total, parts)."""
    if not out.get("parses", False):                      # format gate
        return -(L + 1), {"fail": True}
    tags = set(out["tags"])
    r_tag = f1(tags, gold["tags"])
    # reasoning, scored against the solver run on the model's OWN tags
    lvl, _, res = support(cat, casebook, tags)
    lab, dist = res[gold["primary"]]
    sig = {d["factor"] for d in dist if d["significant"]}
    checks = [f1(out["distinctions"], {d["factor"] for d in dist}),
              f1(out["significant"], sig),
              float(out["verdict"] == ("distinguish" if sig else "follow" if lab in ("binding", "analogous") else "no_precedent")),
              float(out["support"] == lvl),
              float(bool(out["unlisted"]) == gold["unlisted_planted"])]
    if lab == "distinguish":
        checks.append(f1(out["reopened"], residual(cat, casebook[gold["primary"]], tags, dist)["open"]))
    r_reason = sum(checks) / len(checks)
    # outcome of what the harness actually does
    act, d = harness_action(cat, casebook, tags, out["resolution"], out["confidence"], L, k,
                            out["unlisted"], gold.get("may_act", True))
    truth = gold["decision"]                               # forced outcome, hidden resolution, or None if contested
    if act == "act":
        r_out = 1.0 if (truth is not None and d == truth) else -L
    else:
        r_out = 0.0 if (truth is None or not gold.get("may_act", True)) else -k
        if truth is not None and out["resolution"] == truth: r_out += RHO
    # calibration (Brier) wherever the model had to resolve something itself
    r_cal = 0.0
    if gold["level"] in ("bounded", "open", "unprecedented"):
        y = 1.0 if (truth is not None and out["resolution"] == truth) else 0.0
        r_cal = -(out["confidence"] - y) ** 2
    total = W_TAG * r_tag + W_REASON * r_reason + r_out + W_CAL * r_cal
    return total, dict(tag=r_tag, reason=round(r_reason, 3), out=r_out, cal=round(r_cal, 3), action=(act, d))

if __name__ == "__main__":
    from solver_v2 import CB
    Y = ["D1", "D2@moderate", "D2@high", "D3", "D4", "R1", "R2", "R3"]      # the bounded VEP situation
    gold = dict(tags=Y, primary="VEP-001", level="bounded", decision="disclose", unlisted_planted=False)
    base = dict(parses=True, tags=Y, distinctions=["D2@high", "D3", "D4"], significant=["D2@high", "D3", "D4"],
                verdict="distinguish", support="bounded", reopened=["partners", "threat"], unlisted=[],
                resolution="disclose", confidence=0.7)
    L, k = 9, 0.5
    print("p* VEP =", round(threshold(L, k), 3), " p* low stakes (L=1,k=0.2) =", round(threshold(1, 0.2), 3))
    print("honest 0.7, right  :", reward(base, gold, VEP, CB, L, k))
    print("inflated 0.95, right:", reward({**base, "confidence": 0.95}, gold, VEP, CB, L, k))
    print("inflated 0.95, wrong:", reward({**base, "confidence": 0.95, "resolution": "retain"}, gold, VEP, CB, L, k))
    print("contested, conf 0.1 :", reward({**base, "confidence": 0.1}, {**gold, "decision": None}, VEP, CB, L, k))
    print("parse failure       :", reward({"parses": False}, gold, VEP, CB, L, k))
    Yb = ["D1", "D2@moderate", "D2@high", "D3", "R1", "R3"]                   # forced by VEP-004
    gb = dict(tags=Yb, primary="VEP-001", level="binding", decision="disclose", unlisted_planted=False)
    ob = dict(parses=True, tags=Yb, distinctions=["R2", "D2@high", "D3"], significant=["R2", "D2@high", "D3"],
              verdict="distinguish", support="binding", reopened=["target_value", "threat"], unlisted=[],
              resolution=None, confidence=0.0)
    print("binding, right tags :", reward(ob, gb, VEP, CB, L, k))
    print("binding, fake unlisted to dodge:", reward({**ob, "unlisted": ["something new"]}, gb, VEP, CB, L, k))
    # expected-value check: honest reporting is optimal around the threshold
    for p in (0.80, 0.85, 0.90):
        ev_act = p * 1 + (1 - p) * -L
        ev_ask = -k + RHO * p
        print(f"p={p:.2f}: E[act]={ev_act:+.2f}  E[ask]={ev_ask:+.2f}")
