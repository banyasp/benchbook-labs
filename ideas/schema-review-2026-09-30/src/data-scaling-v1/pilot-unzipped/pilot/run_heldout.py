"""Held-out test of the Benchbook solver on real DOHA Guideline F decisions.

Casebook = cases with conversion.split == casebook (6); held-out = split == heldout (4).
Run 1 uses the SEAD 4 catalog only; run 2 adds the doctrine extension (BX1, BX2, AX1).
Supplements: leave-one-out over all 10 cases, and three baselines.
Writes heldout-results.md next to this file. Uses solver_v2.py (pilot copy, unmodified).
"""
import glob, os, yaml
from solver_v2 import support, residual, analyse

INTERPRETATION = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "heldout-interpretation.md")).read()
HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = {"A": "grant", "B": "deny"}


def primary_only(cat):
    """Sensitivity variant: keep only each factor's first-listed equity."""
    return {f: (sd, eq[:1], forced) for f, (sd, eq, forced) in cat.items()}


def load_catalog(with_doctrine):
    c = yaml.safe_load(open(f"{HERE}/catalog-F.yaml"))["catalog"]
    cat = {}
    for fid, v in c["factors_B"].items():
        cat[fid] = ("B", [tuple(e) for e in v["equities"]], bool(v.get("forced_significance")))
    for fid, v in c["factors_A"].items():
        if "scale" in v:
            for step in v["scale"].values():
                cat[step["id"]] = ("A", [tuple(e) for e in step["equities"]], False)
        else:
            cat[fid] = ("A", [tuple(e) for e in v["equities"]], bool(v.get("forced_significance")))
    if with_doctrine:
        for fid, v in c["factors_doctrine"].items():
            cat[fid] = (v["favors"], [tuple(e) for e in v["equities"]], False)
    return cat, c["default"]["outcome"]


def load_cases(cat):
    cases = {}
    for f in sorted(glob.glob(f"{HERE}/cases/DOHA-F-*.yaml")):
        d = yaml.safe_load(open(f))
        c = d["case"]
        tags = {t for fact in c["facts"] for t in fact["factors"]}
        if "A20d@established" in tags:          # threshold factors are closed downward
            tags.add("A20d@initiated")
        tags &= set(cat)                          # drops doctrine factors in run 1
        reason = set(c["reason"]) & set(cat)
        assert reason <= tags, (c["id"], reason - tags)
        cases[c["id"]] = {"facts": tags, "outcome": c["outcome"], "reason": reason,
                          "split": d["conversion"]["split"], "caseno": c["source"]["caseno"]}
    return cases


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0


def predict(cat, casebook, Y, default):
    level, out, res = support(cat, casebook, Y)
    return level, out, res


def run_split(cat, cases, default, label):
    cb = {k: v for k, v in cases.items() if v["split"] == "casebook"}
    ho = {k: v for k, v in cases.items() if v["split"] == "heldout"}
    lines = [f"### {label}", "",
             "Casebook: " + ", ".join("%s (%s)" % (k, NAMES[v["outcome"]]) for k, v in cb.items()), "",
             "| Held-out | Real outcome | Support | Solver prediction | Match | Default-B | 1-NN (Jaccard) |",
             "|---|---|---|---|---|---|---|"]
    detail = []
    for hid, h in ho.items():
        Y = h["facts"]
        level, out, res = predict(cat, cb, Y, default)
        nn = max(cb, key=lambda k: (jaccard(cb[k]["facts"], Y), k))
        match = "—" if out is None else ("yes" if out == h["outcome"] else "NO")
        lines.append(f"| {hid} {h['caseno']} | {NAMES[h['outcome']]} | {level} | "
                     f"{NAMES[out] if out else 'none'} | {match} | "
                     f"{'yes' if default == h['outcome'] else 'NO'} | "
                     f"{NAMES[cb[nn]['outcome']]} via {nn} ({'yes' if cb[nn]['outcome'] == h['outcome'] else 'NO'}) |")
        detail.append(f"**{hid}** tags: `{' '.join(sorted(Y))}`")
        for cid, (lab, dist) in res.items():
            sig = [d["factor"] + ("(missing)" if d["kind"] == "missing_reason" else "(new)") for d in dist if d["significant"]]
            nonsig = [d["factor"] for d in dist if not d["significant"]]
            line = f"- vs {cid} ({NAMES[cb[cid]['outcome']]}, reason {sorted(cb[cid]['reason'])}): **{lab}**"
            if sig: line += f"; significant: {', '.join(sig)}"
            if nonsig: line += f"; downplayed: {', '.join(nonsig)}"
            if lab == "distinguish":
                r = residual(cat, cb[cid], Y, dist)
                line += f"; reopened equities: {', '.join(r['open'])}"
            detail.append(line)
        if level in ("bounded", "open", "unprecedented"):
            reopened = sorted({e for cid, (lab, dist) in res.items() if lab == "distinguish"
                               for e in residual(cat, cb[cid], Y, dist)["open"]})
            detail.append(f"- residual: support **{level}**; equities reopened across the distinguished precedents: "
                          f"{', '.join(reopened)}")
        detail.append("")
    return lines + [""] + detail


def run_loo(cat, cases, default):
    rows, tally = [], {"binding/analogous": [0, 0], "bounded/open/unprec.": [0, 0]}
    for hid, h in cases.items():
        cb = {k: v for k, v in cases.items() if k != hid}
        level, out, res = support(cat, cb, h["facts"])
        binders = sorted(cid for cid, (lab, _) in res.items() if lab in ("binding", "analogous"))
        if out is not None:
            key = "binding/analogous"; tally[key][0] += 1; tally[key][1] += (out == h["outcome"])
        else:
            key = "bounded/open/unprec."; tally[key][0] += 1; tally[key][1] += (default == h["outcome"])
        rows.append(f"| {hid} | {NAMES[h['outcome']]} | {level} | {NAMES[out] if out else 'none'} | "
                    f"{', '.join(binders) or '—'} |")
    head = ["| Case | Real | Support | Solver | Binding/analogous precedents |", "|---|---|---|---|---|"]
    summ = (f"Decided by precedent (binding/analogous): {tally['binding/analogous'][0]} of {len(cases)}, "
            f"correct {tally['binding/analogous'][1]}. Left to residual judgment: {tally['bounded/open/unprec.'][0]}; "
            f"if resolved by the SEAD 4 default (B), correct {tally['bounded/open/unprec.'][1]}.")
    return head + rows + ["", summ, ""]


if __name__ == "__main__":
    out = ["# Held-out results: DOHA Guideline F pilot", "",
           "Generated by `run_heldout.py` from `catalog-F.yaml` and `cases/DOHA-F-*.yaml` with the unmodified "
           "`solver_v2.py`. Tags come from the converter's reading of each decision (gold tags), so this tests "
           "the precedent logic given judge-level perception, not an agent's perception of a raw file.", ""]
    for with_doc, title in ((False, "Run 1: SEAD 4 catalog only"), (True, "Run 2: SEAD 4 + doctrine extension (BX1, BX2, AX1)")):
        cat, default = load_catalog(with_doc)
        cases = load_cases(cat)
        out += ["## " + title, ""] + run_split(cat, cases, default, "6 / 4 split")
        out += ["### Supplement: leave-one-out over all 10 (each case vs the other 9)", ""] + run_loo(cat, cases, default)
    cat, default = load_catalog(False)
    cat = primary_only(cat)
    cases = load_cases(cat)
    out += ["## Run 3 (sensitivity): SEAD 4 catalog, each factor reduced to its first-listed equity", ""]
    out += run_split(cat, cases, default, "6 / 4 split")[:10]
    out += ["### Supplement: leave-one-out", ""] + run_loo(cat, cases, default)
    out += [INTERPRETATION]
    open(f"{HERE}/heldout-results.md", "w").write("\n".join(out))
    print("\n".join(out))
