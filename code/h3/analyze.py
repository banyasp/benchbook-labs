"""Score runs against O(T) (OHA's own outcome). -> results/h3-pilot/summary.json and a markdown table fragment."""
from __future__ import annotations
import collections, json, math, yaml
from .crawl import OUT


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 3), round(c + h, 3)


def load():
    pairs = yaml.safe_load((OUT / "pairs.yaml").read_text())["pairs"]
    T = {}
    for p in pairs:
        f = OUT / "scenarios" / f"T-{p['id']}.yaml"
        if f.exists() and (OUT / "scenarios" / f"C-{p['id']}.yaml").exists():
            sc = yaml.safe_load(f.read_text())
            T[p["id"]] = (p, sc["case"])
    return T


def runs(role):
    out = collections.defaultdict(list)
    for f in sorted((OUT / "runs" / role).glob("*.json")):
        r = json.loads(f.read_text())
        out[(r["pair"], r["arm"])].append(r)
    return out


def summarize(role):
    T = load()
    R = runs(role)
    rows = {}
    for band in ("all", "same", "different"):
        for arm in ("with_c", "no_c"):
            maj, samp, ns = 0, [0, 0], 0
            for pid, (p, case) in T.items():
                if band != "all" and p["band"] != band:
                    continue
                rs = R.get((pid, arm))
                if not rs:
                    continue
                gold = case["verdict"]["choice"]
                ok = [r["parsed"]["choice"] == gold for r in rs]
                ns += 1
                samp[0] += sum(ok); samp[1] += len(ok)
                maj += sum(ok) * 2 > len(ok)          # strict majority of samples
            rows[(band, arm)] = {"n_pairs": ns, "maj_correct": maj, "maj_acc": round(maj / ns, 3) if ns else None,
                                 "maj_ci": wilson(maj, ns), "sample_acc": round(samp[0] / samp[1], 3) if samp[1] else None,
                                 "samples": samp[1]}
    return rows


def baselines():
    T = load()
    out = {}
    for band in ("all", "same", "different"):
        gm = collections.Counter(); n = 0; chance = 0.0
        for pid, (p, c) in T.items():
            if band != "all" and p["band"] != band:
                continue
            n += 1
            gm[c["options"][c["verdict"]["choice"]]["move"]] += 1
            chance += 1 / len(c["options"])
        top, cnt = gm.most_common(1)[0] if gm else (None, 0)
        # majority-class baseline: always pick the option whose move type is most common among golds (when present)
        hit = 0
        for pid, (p, c) in T.items():
            if band != "all" and p["band"] != band:
                continue
            cands = [k for k, v in c["options"].items() if v["move"] == top]
            hit += (c["verdict"]["choice"] in cands) / max(1, len(cands))
        out[band] = {"n": n, "gold_moves": dict(gm), "majority_move": top, "majority_move_baseline": round(hit / n, 3) if n else None,
                     "chance": round(chance / n, 3) if n else None}
    return out


if __name__ == "__main__":
    import sys
    res = {r: {f"{b}|{a}": v for (b, a), v in summarize(r).items()} for r in sys.argv[1:]}
    res["baselines"] = baselines()
    (OUT / "summary.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
