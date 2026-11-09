"""Report for an eval.allpairs run: the headline numbers, the who-helps-whom matrix, and the secondary metrics.

    PYTHONPATH=code .venv/bin/python -m eval.allpairs_report --run results/allpairs/A1

Writes <run>/report.md, <run>/matrix.csv (X1 rows x X2 columns: 1 correct, 0 wrong, blank not run; first columns are
X1's family, its control success rate and its self cell) and <run>/per_x1.csv.

Headline (each a mean over X1, 95% CI from a family bootstrap: X1s resampled by family):
    control          G(T(X1)) with no case: mean of its k samples
    random case      mean over X2 != X1 of the grid cell (what a random pick from this library gives)
    best case        confirm phase: the success rate over k fresh samples of one X2 that worked in the grid (0 if none)
    self             X2 = X1 (the scenario's own case; a ceiling check)
    any X2 (pass@N)  1 if any X2 != X1 grid cell is correct. INFLATED: with N tries and no-case success rate p, chance
                     alone gives 1 - (1 - p)^N; that null is printed next to it.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .core import read_samples

SEC = [("facts found / gold", "facts_enum.found", "facts_enum.n_gold"),
       ("options found / gold", "options_enum.found", "options_enum.n_gold"),
       ("considerations found / gold", "considerations_enum.found", "considerations_enum.n_gold")]
SEC_SCORES = ["facts_enum", "options_enum", "frame_question", "frame_decider", "frame_role", "considerations_enum",
              "considerations_enum.equity"]


def ok(v):
    return v if v is not None else 0.0      # unscored (judge error) counted wrong; the report says how many


def fam_boot(per_x1: dict[str, float], fam: dict[str, str], B: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    xs = [x for x in per_x1 if per_x1[x] is not None]
    if not xs:
        return (float("nan"),) * 3
    by = defaultdict(list)
    for x in xs:
        by[fam[x]].append(per_x1[x])
    fams = list(by)
    rng = random.Random(seed)
    vals = []
    for _ in range(B):
        pick = [v for f in (rng.choice(fams) for _ in fams) for v in by[f]]
        vals.append(mean(pick))
    vals.sort()
    return mean(per_x1[x] for x in xs), vals[int(0.025 * B)], vals[int(0.975 * B) - 1]


def pct(t):
    m, lo, hi = t
    return "n/a" if m != m else f"{100 * m:.0f}% [{100 * lo:.0f}-{100 * hi:.0f}]"


def build(run: Path) -> dict:
    cfg = json.loads((run / "config.json").read_text())
    S = [r for r in read_samples(run / "samples.jsonl") if r["model"] == cfg["model"]]
    x1s, x2s = cfg["x1"], cfg["x2"]
    fam = {}
    ctrl, grid, conf = defaultdict(list), {}, defaultdict(list)
    for r in S:
        fam[r["x1"]] = r.get("x1_family")
        if r["phase"] == "control":
            ctrl[r["x1"]].append(r)
        elif r["phase"] == "grid":
            grid[(r["x1"], r["x2"])] = r
        else:
            conf[r["x1"]].append(r)
    seen = [x for x in x1s if x in fam]
    p0 = {x: mean(ok(r["correct"]) for r in ctrl[x]) if ctrl[x] else None for x in seen}
    rand = {}
    anyx = {}
    nx2 = {}
    for x in seen:
        cells = [ok(grid[(x, y)]["correct"]) for y in x2s if y != x and (x, y) in grid]
        nx2[x] = len(cells)
        rand[x] = mean(cells) if cells else None
        anyx[x] = (1.0 if any(c == 1.0 for c in cells) else 0.0) if cells else None
    null = {x: (1 - (1 - p0[x]) ** nx2[x]) if (p0[x] is not None and nx2[x]) else None for x in seen}
    selfc = {x: ok(grid[(x, x)]["correct"]) if (x, x) in grid else None for x in seen}
    picks = {}
    for p in sorted(run.glob("confirm-picks.*.json")):
        picks = json.loads(p.read_text())
    best = {}
    for x in seen:
        if x not in picks:
            best[x] = None
        elif picks[x] is None:
            best[x] = 0.0
        else:
            rs = [ok(r["correct"]) for r in conf[x] if r["x2"] == picks[x]]
            best[x] = mean(rs) if rs else None
    # help / harm, per cell (X2 != X1), relative to the X1's control rate
    rel_acc = defaultdict(list)
    help_ = harm = n_lo = n_hi = 0
    for (x, y), r in grid.items():
        rel_acc[r.get("relation_x1_x2") or "?"].append(ok(r["correct"]))
        if x == y or p0.get(x) is None:
            continue
        c = ok(r["correct"])
        if p0[x] < 0.5:
            n_lo += 1
            help_ += c == 1.0
        else:
            n_hi += 1
            harm += c == 0.0
    # secondary
    sec = {}
    for name, grp in (("control", [r for v in ctrl.values() for r in v]),
                      ("case (grid, X2 != X1)", [r for (x, y), r in grid.items() if x != y]),
                      ("best case (confirm)", [r for v in conf.values() for r in v])):
        d = {}
        for lab, f, n in SEC:
            num = sum((r["secondary"] or {}).get(f) or 0 for r in grp)
            den = sum((r["secondary"] or {}).get(n) or 0 for r in grp)
            d[lab] = (num / den) if den else None
        for k in SEC_SCORES:
            v = [(r["secondary"] or {}).get(k) for r in grp]
            v = [x for x in v if isinstance(x, (int, float))]
            d[k] = mean(v) if v else None
        d["n"] = len(grp)
        d["truncated"] = mean(r.get("finish_reason") == "length" for r in grp) if grp else None
        d["no verdict"] = mean(r.get("parsed_choice") is None for r in grp) if grp else None
        d["off menu"] = mean(bool(r.get("off_menu")) for r in grp) if grp else None
        d["unscored"] = sum(r.get("correct") is None for r in grp)
        sec[name] = d
    leak = {}
    for lp in sorted(Path("results/allpairs").glob("answer-leak-*.jsonl")):
        for line in lp.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                leak[r["scenario"]] = "gold" if (r.get("flag") and r.get("option_is_gold")) else ("other" if r.get("flag") else "none")
    return dict(leak=leak, cfg=cfg, S=S, seen=seen, fam=fam, p0=p0, rand=rand, anyx=anyx, null=null, selfc=selfc, best=best,
                picks=picks, grid=grid, ctrl=ctrl, conf=conf, rel_acc=rel_acc, help=(help_, n_lo), harm=(harm, n_hi),
                sec=sec, nx2=nx2)


def write(run: Path, R: dict) -> str:
    cfg, seen, fam = R["cfg"], R["seen"], R["fam"]
    n_cells = sum(1 for (x, y) in R["grid"] if x != y)
    full = len(cfg["x1"]) * (len(cfg["x2"]) - 1)
    L = [f"# All-pairs case benefit: {run.name}", "",
         f"Model `{cfg['model']}`, mode {cfg['mode']}, equities `{cfg['equities']}`, AR prompt on, full card, "
         f"max_tokens {cfg['max_tokens']}. X1 = {len(cfg['x1'])} traced scenarios, X2 = {len(cfg['x2'])} "
         f"(self included). Grid cells done (X2 != X1): **{n_cells} / {full}**; control samples: "
         f"{sum(len(v) for v in R['ctrl'].values())}; confirm samples: {sum(len(v) for v in R['conf'].values())}.", "",
         "## Headline: verdict exact-match after translation (mean over X1, 95% family-bootstrap CI)", "",
         "| measure | score | X1s |", "|---|---|---|"]
    def row(lab, d, note=""):
        n = sum(1 for x in seen if d.get(x) is not None)
        L.append(f"| {lab} | {pct(fam_boot(d, fam))} | {n} |{note}")
    row("control: no case (k samples per X1)", R["p0"])
    row("random case: mean over X2 != X1", R["rand"])
    row("**best case (confirmed)**: k fresh samples of one X2 that worked", R["best"])
    row("self: X2 = X1", R["selfc"])
    row("any X2 != X1 correct (pass@N, inflated)", R["anyx"])
    row("chance null for the line above: 1-(1-control)^N", R["null"])
    lk = R["leak"]
    if lk:
        L += ["", "Split by the answer-leak check (report-only, `pipeline.render.answer_leak`): `gold` = the trace was "
                  "flagged as stating that the gold course was already decided or describing the outcome.", "",
              "| X1 leak flag | X1s | control | random case | best case | self |", "|---|---|---|---|---|---|"]
        for tag in ("none", "other", "gold"):
            xs = [x for x in seen if lk.get(x, "unchecked") == tag]
            if xs:
                sub = lambda d: pct(fam_boot({x: d[x] for x in xs}, fam))
                L.append(f"| {tag} | {len(xs)} | {sub(R['p0'])} | {sub(R['rand'])} | {sub(R['best'])} | {sub(R['selfc'])} |")
    nopt = {}
    for r in R["S"]:
        nopt[r["x1"]] = r.get("x1_n_options")
    L += ["", "By number of options (chance = 1/n, R86):", "",
          "| options | X1s | chance | control | random case | best case |", "|---|---|---|---|---|---|"]
    for n in sorted({v for v in nopt.values() if v}):
        xs = [x for x in seen if nopt.get(x) == n]
        sub = lambda d: pct(fam_boot({x: d[x] for x in xs}, fam))
        L.append(f"| {n} | {len(xs)} | {100 / n:.0f}% | {sub(R['p0'])} | {sub(R['rand'])} | {sub(R['best'])} |")
    h, nl = R["help"]
    m, nh = R["harm"]
    L += ["", f"**Help:** of {nl} cells whose X1 the model usually gets wrong without a case (control < 50%), "
              f"{h} ({100 * h / max(1, nl):.0f}%) were right with the case. **Harm:** of {nh} cells whose X1 it usually "
              f"gets right (control >= 50%), {m} ({100 * m / max(1, nh):.0f}%) were wrong with the case.", "",
          "## Grid accuracy by how X2 relates to X1", "", "| relation | cells | accuracy |", "|---|---|---|"]
    for k in ("self", "derived", "same_family", "other"):
        v = R["rel_acc"].get(k, [])
        if v:
            L.append(f"| {k} | {len(v)} | {100 * mean(v):.0f}% |")
    L += ["", "`derived`: one is a perturbation (restyle / flip / add-fact) of the other, or both of one parent. "
              "`same_family`: same source, not derived.", "",
          "## Secondary metrics (per sample; enumeration = found / gold, Jev-aligned)", ""]
    names = list(R["sec"])
    keys = [k for k in next(iter(R["sec"].values())) if k != "n"]
    L += ["| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    L.append("| samples | " + " | ".join(str(R["sec"][n]["n"]) for n in names) + " |")
    for k in keys:
        def f(v):
            if v is None:
                return "n/a"
            return str(v) if isinstance(v, int) and k == "unscored" else f"{v:.2f}"
        L.append(f"| {k} | " + " | ".join(f(R["sec"][n][k]) for n in names) + " |")
    L += ["", "Files: `matrix.csv` (X1 x X2), `per_x1.csv`, `samples.jsonl`, raw replies in `raw/`."]
    md = "\n".join(L) + "\n"
    (run / "report.md").write_text(md)
    x2s = R["cfg"]["x2"]
    with open(run / "matrix.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["x1", "x1_family", "control", "self"] + x2s)
        for x in seen:
            w.writerow([x, fam[x], "" if R["p0"][x] is None else f"{R['p0'][x]:.3f}",
                        "" if R["selfc"][x] is None else int(R["selfc"][x])]
                       + ["" if (x, y) not in R["grid"] else int(ok(R["grid"][(x, y)]["correct"])) for y in x2s])
    with open(run / "per_x1.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["x1", "family", "control", "random_case", "self", "any_x2", "null_any", "best_pick", "best_case"])
        for x in seen:
            g = lambda d: "" if d.get(x) is None else f"{d[x]:.3f}"
            w.writerow([x, fam[x], g(R["p0"]), g(R["rand"]), g(R["selfc"]), g(R["anyx"]), g(R["null"]),
                        R["picks"].get(x) or "", g(R["best"])])
    return md


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    a = ap.parse_args(argv)
    run = Path(a.run)
    print(write(run, build(run)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
