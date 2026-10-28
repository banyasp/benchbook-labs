"""All numbers for the report -> results/h3-pilot/report-numbers.json (and printed)."""
from __future__ import annotations
import collections, json, yaml
from .analyze import load, runs, wilson, OUT
from .extra import direction, main as dirs


def run():
    T = load()
    D = {r["pair"]: r for r in dirs()}
    out = {"n_pairs": len(T)}
    # baselines
    def base(sel):
        ids = [p for p in T if sel(p)]
        n = len(ids)
        deny = sum(D[p]["gold_T"] == "deny" for p in ids)
        copyc = sum(D[p]["gold_T"] == D[p]["gold_C"] for p in ids)
        return {"n": n, "always_deny": deny, "always_deny_ci": wilson(deny, n), "copy_C_direction": copyc, "copy_C_ci": wilson(copyc, n),
                "grant": sum(D[p]["gold_T"] == "grant" for p in ids), "chance": round(sum(1 / len(T[p][1]["options"]) for p in ids) / max(1, n), 3)}
    subsets = {"all": lambda p: True, "band=same": lambda p: T[p][0]["band"] == "same", "band=different": lambda p: T[p][0]["band"] == "different",
               "C_agrees_T": lambda p: D[p]["gold_T"] == D[p]["gold_C"], "C_opposes_T": lambda p: D[p]["gold_T"] != D[p]["gold_C"],
               "T_deny": lambda p: D[p]["gold_T"] == "deny", "T_grant": lambda p: D[p]["gold_T"] == "grant"}
    out["baselines"] = {k: base(f) for k, f in subsets.items()}
    out["models"] = {}
    for role in ("h3_standin", "h3_standin2"):
        R = runs(role)
        m = {}
        for sk, f in subsets.items():
            for arm in ("with_c", "no_c"):
                ids = [p for p in T if f(p) and (p, arm) in R]
                maj = samp = ns = 0
                for p in ids:
                    gold = T[p][1]["verdict"]["choice"]
                    ok = [r["parsed"]["choice"] == gold for r in R[(p, arm)]]
                    maj += sum(ok) * 2 > len(ok); samp += sum(ok); ns += len(ok)
                n = len(ids)
                m[f"{sk}|{arm}"] = {"n": n, "maj": maj, "maj_acc": round(maj / n, 3) if n else None, "ci": wilson(maj, n),
                                    "sample_acc": round(samp / ns, 3) if ns else None}
        # paired changes with vs without C (majority)
        up, down = [], []
        copy = tot = 0
        for p in T:
            gold = T[p][1]["verdict"]["choice"]
            w = sum(r["parsed"]["choice"] == gold for r in R[(p, "with_c")]) * 2 > 3 - 0 and True
            wc = sum(r["parsed"]["choice"] == gold for r in R[(p, "with_c")]) >= 2
            nc = sum(r["parsed"]["choice"] == gold for r in R[(p, "no_c")]) >= 2
            if wc and not nc: up.append(p)
            if nc and not wc: down.append(p)
            for r in R[(p, "with_c")]:
                ch = r["parsed"]["choice"]
                if ch:
                    tot += 1
                    copy += direction(T[p][1], ch) == D[p]["gold_C"]
        m["helped"], m["hurt"] = up, down
        m["with_c_direction_equals_C_direction"] = [copy, tot]
        rel = collections.Counter(r["parsed"]["relation"] for p in T for r in R[(p, "with_c")])
        m["relations"] = dict(rel)
        out["models"][role] = m
    # agreement between the two families (majority choice) with C
    (OUT / "report-numbers.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
