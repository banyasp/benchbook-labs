"""Grid samples (eval.grid) -> results/RESULTS-<date>.md + figures under results/figures/.

    PYTHONPATH=code .venv/bin/python -m eval.grid_report results/eval-v1/run1 [--out results/RESULTS-2026-10-28.md]
                                                         [--figs results/figures] [--tag 2026-10-28]

Sections: headline (accuracy vs d, four curves), by-arm graph, off-menu, baselines, accuracy given the gold option was
enumerated, revised "follows both", decoy vs none, % incorrect irreversible / % ask a human, within-family curves,
breakdowns (arm, intent, realization, tier, family), the held-out domain as its own panel, the pilot imports as their own
set, and the second-pass cells when present. CIs: 95% percentile bootstrap resampling whole families (eval.stats).
The headline and breakdowns exclude the held-out domain and the pilot imports; each has its own section.
An existing output file is copied to versions/ first.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import stats
from .core import read_samples

HAND_UP = ("ask", "refuse")
IMPORT_TAG = "eval-only-import"
HELD_OUT_DOMAIN = "military-operational"
ARM_ORDER = ("none", "relevant", "augmented", "revised", "decoy", "self")
MODEL_LABEL = {"base": "base", "sft": "SFT"}
# categorical slots 1-2 of the dataviz reference palette (model identity); card = line style
COLOR = {"base": "#2a78d6", "sft": "#eb6834"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e5e4e0"


# ------------------------------------------------------------------ helpers
def acc(rows, n_boot=stats.N_BOOT):
    return stats.family_bootstrap(rows, lambda r: r["correct"], n_boot)


def pct(c) -> str:
    if not c or c.get("mean") is None:
        return "n/a"
    flag = "*" if c.get("few_families") else ""
    return f"{100 * c['mean']:.0f}% [{100 * c['lo']:.0f}-{100 * c['hi']:.0f}]{flag} (n={c['n']})"


def rate(rows, f) -> str:
    v = [f(r) for r in rows]
    v = [x for x in v if x is not None]
    return f"{100 * sum(v) / len(v):.0f}% (n={len(v)})" if v else "n/a"


def table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def is_import(r) -> bool:
    return IMPORT_TAG in (r.get("tags") or [])


def is_held_out(r) -> bool:
    return bool(r.get("held_out")) or r.get("domain") == HELD_OUT_DOMAIN


def split_sets(rows):
    imp = [r for r in rows if is_import(r)]
    held = [r for r in rows if is_held_out(r) and not is_import(r)]
    main = [r for r in rows if not is_import(r) and not is_held_out(r)]
    return main, held, imp


def x_of(r):
    """d for the headline: relevant -> its own d; none -> its trace's relevant-pair d; self -> 0."""
    if r["arm"] == "self":
        return 0.0
    if r["arm"] == "none":
        return r.get("trace_relevant_d")
    return r.get("d")


def models_in(rows):
    return [m for m in ("base", "sft") if any(r["model"] == m for r in rows)]


def core(rows):
    return [r for r in rows if r.get("cell", "core") == "core"]


def bins_for(rows, k=5):
    xs = sorted(x for x in (x_of(r) for r in rows if r["arm"] in ("relevant", "none")) if x is not None)
    if len(xs) < 2:
        return []
    edges = sorted(set(np.quantile(xs, np.linspace(0, 1, k + 1)).round(6)))
    return edges if len(edges) > 2 else [edges[0], edges[-1]]


def binned(rows, edges):
    out = []
    for lo, hi, last in zip(edges[:-1], edges[1:], [False] * (len(edges) - 2) + [True]):
        sel = [r for r in rows if x_of(r) is not None and lo <= x_of(r) and (x_of(r) <= hi if last else x_of(r) < hi)]
        if sel:
            out.append((float(np.mean([x_of(r) for r in sel])), acc(sel), sel))
    return out


def curves(rows, edges):
    """(model, card) -> [(x, acc dict)], card in none | relevant."""
    out = {}
    for m in models_in(rows):
        for arm in ("none", "relevant"):
            sel = [r for r in rows if r["model"] == m and r["arm"] == arm]
            if sel:
                out[(m, arm)] = [(x, a) for x, a, _ in binned(sel, edges)]
    return out


# ------------------------------------------------------------------ figures
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.color": GRID, "grid.linewidth": 0.8, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
    return plt


def fig_headline(rows, edges, path, title="Choice accuracy vs structural distance d(C, T)", self_pts=None):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    cv = curves(rows, edges)
    for (m, arm), pts in cv.items():
        xs = [p[0] for p in pts]
        ys = [100 * p[1]["mean"] for p in pts]
        lo = [100 * p[1]["lo"] for p in pts]
        hi = [100 * p[1]["hi"] for p in pts]
        ls, fill = ("-", COLOR[m]) if arm == "relevant" else ("--", "none")
        ax.errorbar(xs, ys, yerr=[np.array(ys) - lo, np.array(hi) - ys], color=COLOR[m], ls=ls, lw=2, marker="o", ms=8,
                    mfc=fill, mec=COLOR[m], capsize=3, label=f"{MODEL_LABEL[m]} + {arm}")
    for m, (a, mean) in (self_pts or {}).items():
        ax.errorbar([0], [100 * a["mean"]], yerr=[[100 * (a["mean"] - a["lo"])], [100 * (a["hi"] - a["mean"])]], color=COLOR[m],
                    marker="D", ms=8, capsize=3, ls="none", label=f"{MODEL_LABEL[m]} + self (d = 0)")
    ax.set_xlabel("d(C, T)  (none rows at their trace's relevant-pair d)")
    ax.set_ylabel("choice accuracy (%)")
    ax.set_ylim(0, 100)
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="best")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_by_arm(rows, path, title="Choice accuracy by arm"):
    plt = _plt()
    arms = [a for a in ARM_ORDER if any(r["arm"] == a for r in rows)]
    ms = models_in(rows)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    w = 0.38
    for j, m in enumerate(ms):
        for i, a in enumerate(arms):
            c = acc([r for r in rows if r["model"] == m and r["arm"] == a])
            if c["mean"] is None:
                continue
            x = i + (j - (len(ms) - 1) / 2) * w
            ax.bar(x, 100 * c["mean"], width=w * 0.9, color=COLOR[m], label=MODEL_LABEL[m] if i == 0 else None)
            ax.errorbar([x], [100 * c["mean"]], yerr=[[100 * (c["mean"] - c["lo"])], [100 * (c["hi"] - c["mean"])]], color=INK,
                        capsize=3, lw=1)
    ax.set_xticks(range(len(arms)), arms)
    ax.set_ylim(0, 100)
    ax.set_ylabel("choice accuracy (%)")
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_within_family(rows, path, min_n=6):
    plt = _plt()
    ms = models_in(rows)
    fig, axes = plt.subplots(1, max(1, len(ms)), figsize=(4.6 * max(1, len(ms)), 4.2), sharey=True, squeeze=False)
    drawn = 0
    for ax, m in zip(axes[0], ms):
        by = defaultdict(list)
        for r in rows:
            if r["model"] == m and r["arm"] == "relevant" and r.get("d") is not None:
                by[r["family"]].append(r)
        for fam, rs in by.items():
            if len(rs) < min_n:
                continue
            rs = sorted(rs, key=lambda r: r["d"])
            k = 3
            chunks = np.array_split(np.arange(len(rs)), k)
            xs = [np.mean([rs[i]["d"] for i in c]) for c in chunks if len(c)]
            ys = [100 * np.mean([rs[i]["correct"] or 0 for i in c]) for c in chunks if len(c)]
            ax.plot(xs, ys, marker="o", ms=5, lw=1.5, color=COLOR[m], alpha=0.5)
            drawn += 1
        ax.set_title(f"{MODEL_LABEL[m]} + relevant, one line per family", loc="left", fontsize=10, color=INK)
        ax.set_xlabel("d(C, T) (tertiles within family)")
        ax.set_ylim(0, 100)
    axes[0][0].set_ylabel("choice accuracy (%)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return drawn


# ------------------------------------------------------------------ baselines
def baselines(rows):
    """Model-independent baselines over distinct core pairs (first model present). Majority disposition per domain is
    leave-one-out inside the domain (the row's own gold move is not counted)."""
    ms = models_in(rows)
    if not ms:
        return {}
    pairs = {r["pair"]: r for r in rows if r["model"] == ms[0]}
    by_dom = defaultdict(list)
    for r in pairs.values():
        by_dom[r.get("domain")].append(r["gold_move"])
    out = defaultdict(dict)
    for arm in ARM_ORDER:
        rs = [r for r in pairs.values() if r["arm"] == arm]
        if not rs:
            continue
        maj = []
        for r in rs:
            c = Counter(by_dom[r.get("domain")])
            c[r["gold_move"]] -= 1
            c = +c
            maj.append(float(bool(c) and sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] == r["gold_move"]))
        out[arm] = {"n": len(rs),
                    "always_hand_up": np.mean([r["gold_move"] in HAND_UP for r in rs]),
                    "always_act": np.mean([r["gold_move"] == "act" for r in rs]),
                    "majority_domain": float(np.mean(maj)),
                    "copy_case": (np.mean([r["copy_correct"] for r in rs if r.get("copy_available")])
                                  if any(r.get("copy_available") for r in rs) else None)}
    return out


# ------------------------------------------------------------------ report
def sections_main(rows, figs: Path, tag: str, n_boot) -> list[str]:
    md = []
    ms = models_in(rows)
    arms = [a for a in ARM_ORDER if any(r["arm"] == a for r in rows)]
    edges = bins_for(rows)
    self_pts = {m: (acc([r for r in rows if r["model"] == m and r["arm"] == "self"], n_boot), None) for m in ms
                if any(r["model"] == m and r["arm"] == "self" for r in rows)}
    self_pts = {m: v for m, v in self_pts.items() if v[0]["mean"] is not None}

    md.append("## 1. Headline: choice accuracy vs d(C, T)\n")
    if edges:
        p = figs / f"headline-{tag}.png"
        fig_headline(rows, edges, p, self_pts=self_pts)
        md.append(f"![headline]({p.relative_to(figs.parent) if figs.parent in p.parents else p})\n")
        md.append("Four curves: base + none, base + relevant, SFT + none, SFT + relevant. AR prompt on, full card, mode C, "
                  "n = 1. `none` rows are plotted at their trace's relevant-pair d; `self` is the d = 0 point. d is binned "
                  "into quintiles of the pooled relevant/none rows.\n")
        cv = curves(rows, edges)
        trs = []
        for (m, arm), pts in sorted(cv.items()):
            for x, a in pts:
                trs.append([MODEL_LABEL[m], arm, f"{x:.3f}", pct(a)])
        md.append(table(["model", "card", "mean d", "accuracy [95% CI]"], trs))
    else:
        md.append("No d values in these samples; the headline curve needs `relevant` pairs with d.\n")

    md.append("## 2. By arm\n")
    p = figs / f"by-arm-{tag}.png"
    fig_by_arm(rows, p)
    md.append(f"![by arm]({p.relative_to(figs.parent) if figs.parent in p.parents else p})\n")
    md.append(table(["arm"] + [MODEL_LABEL[m] for m in ms],
                    [[a] + [pct(acc([r for r in rows if r["model"] == m and r["arm"] == a], n_boot)) for m in ms] for a in arms]))

    md.append("## 3. Off-menu rate\nA parsed choice that aligns to no gold option (counted wrong in every accuracy).\n")
    md.append(table(["arm"] + [MODEL_LABEL[m] for m in ms],
                    [[a] + [rate([r for r in rows if r["model"] == m and r["arm"] == a], lambda r: float(r["off_menu"])) for m in ms]
                     for a in arms]))

    md.append("## 4. Baselines (no model)\n")
    b = baselines(rows)
    f = lambda v: "n/a" if v is None else f"{100 * v:.0f}%"
    md.append(table(["arm", "pairs", "copy-the-case", "always hand up (ask/refuse)", "always `act`", "majority disposition per domain"],
                    [[a, v["n"], f(v["copy_case"]), f(v["always_hand_up"]), f(v["always_act"]), f(v["majority_domain"])]
                     for a, v in b.items()]))
    md.append("Copy-the-case translates the served card's verdict through the options map. **On `revised` it is 100% by "
              "construction** (the gold is the revised card's own verdict through the map), so it says nothing about the "
              "model there; on `self` it is also 100% (card = trace). Copy-the-case by intent (relevant arm):\n")
    ints = sorted({r["intent"] for r in rows if r["arm"] == "relevant"})
    first = ms[0] if ms else None
    md.append(table(["intent", "pairs", "copy-the-case", "model: " + " / ".join(MODEL_LABEL[m] for m in ms)],
                    [[i, len({r["pair"] for r in rows if r["arm"] == "relevant" and r["intent"] == i and r["model"] == first}),
                      f(np.mean([r["copy_correct"] for r in rows if r["arm"] == "relevant" and r["intent"] == i and r["model"] == first
                                 and r.get("copy_available")]) if any(r.get("copy_available") for r in rows if r["intent"] == i and r["arm"] == "relevant") else None),
                      " / ".join(pct(acc([r for r in rows if r["model"] == m and r["arm"] == "relevant" and r["intent"] == i], n_boot))
                                 for m in ms)] for i in ints]))
    md.append("Majority disposition is leave-one-out inside each domain over the eval pairs shown (R58).\n")

    md.append("## 5. Accuracy given the gold option was enumerated (R29)\n")
    md.append(table(["arm"] + [MODEL_LABEL[m] + " (all / gold enumerated)" for m in ms],
                    [[a] + [pct(acc(rs)) + " / " + pct(acc([r for r in rs if r.get("gold_option_present") == 1]))
                            for rs in ([r for r in rows if r["model"] == m and r["arm"] == a] for m in ms)] for a in arms]))

    md.append("## 6. Revised: does the model follow both cards?\n")
    byk = {(r["model"], r["pair"]): r for r in rows}
    tr = []
    for m in ms:
        rev = [r for r in rows if r["model"] == m and r["arm"] == "revised" and r.get("restyle_partner")]
        pairs = [(r, byk.get((m, r["restyle_partner"]))) for r in rev]
        pairs = [(a, p_) for a, p_ in pairs if p_ is not None]
        diff = [(a, p_) for a, p_ in pairs if a["gold_choice"] != p_["gold_choice"]]
        both = lambda ps: rate(ps, lambda t: float(bool(t[0]["correct"]) and bool(t[1]["correct"])))
        tr.append([MODEL_LABEL[m], len(pairs), rate(pairs, lambda t: t[0]["correct"]), rate(pairs, lambda t: t[1]["correct"]), both(pairs),
                   len(diff), both(diff)])
    md.append(table(["model", "revised/partner pairs", "revised correct", "relevant partner correct", "follows both",
                     "pairs whose gold differs", "follows both (gold differs)"], tr))
    md.append("\"Follows both\" = correct on the revised card AND on the relevant restyle partner (same trace, original card). "
              "Where the two golds differ it measures card sensitivity directly.\n")

    md.append("## 7. Decoy vs none (PDF falsifier 3)\n")
    tr = []
    for m in ms:
        d_ = [r for r in rows if r["model"] == m and r["arm"] == "decoy"]
        n_ = [r for r in rows if r["model"] == m and r["arm"] == "none"]
        if d_ and n_:
            x = stats.family_bootstrap_diff(d_, n_, lambda r: r["correct"], n_boot)
            tr.append([MODEL_LABEL[m], pct(acc(d_)), pct(acc(n_)),
                       "n/a" if x["diff"] is None else f"{100 * x['diff']:+.1f} pts [{100 * x['lo']:+.1f}, {100 * x['hi']:+.1f}]"])
    md.append(table(["model", "decoy", "none", "decoy - none"], tr) + "Negative = decoys mislead.\n")

    md.append("## 8. Safety-shaped rates\n")
    md.append(table(["model", "arm", "% incorrect irreversible", "% ask a human"],
                    [[MODEL_LABEL[m], a,
                      rate([r for r in rows if r["model"] == m and r["arm"] == a],
                           lambda r: float(bool(r["chosen_irreversible"]) and not r["correct"])),
                      rate([r for r in rows if r["model"] == m and r["arm"] == a], lambda r: float(r["chosen_move"] == "ask"))]
                     for m in ms for a in arms]))
    md.append("Incorrect irreversible = a wrong choice whose option is tagged irreversible (backend tag), over all rows; ask a human = chosen option's move is `ask`.\n")

    md.append("## 9. Within-family curves (R56)\n")
    p = figs / f"within-family-{tag}.png"
    n = fig_within_family(rows, p)
    md.append(f"![within family]({p.relative_to(figs.parent) if figs.parent in p.parents else p})\n\n{n} family lines drawn (families with at least 6 relevant pairs).\n")

    md.append("## 10. Breakdowns (relevant, augmented, revised and decoy arms; none and self excluded)\n")
    sub = [r for r in rows if r["arm"] not in ("none", "self")]
    for dim in ("arm", "intent", "realization", "tier", "family"):
        groups = sorted({str(r.get(dim)) for r in sub})
        md.append(f"### by {dim}\n")
        md.append(table([dim] + [MODEL_LABEL[m] for m in ms],
                        [[g] + [pct(acc([r for r in sub if r["model"] == m and str(r.get(dim)) == g], n_boot)) for m in ms] for g in groups]))
    return md


def build(run_dirs, figs: Path, tag: str, n_boot=stats.N_BOOT) -> str:
    rows = []
    for d in run_dirs:
        rows += read_samples(Path(d) / "samples.jsonl")
    if not rows:
        return "# No samples.\n"
    allrows = rows
    rows = core(rows)
    main, held, imp = split_sets(rows)
    ms = models_in(rows)
    md = [f"# Benchbook v2.4 core eval grid ({time.strftime('%Y-%m-%d')})\n",
          f"Runs: {', '.join(Path(d).name for d in run_dirs)}. {len(allrows)} samples ({len(rows)} core cell), "
          f"models {', '.join(MODEL_LABEL[m] for m in ms)}; AR prompt on, full card, n = 1, mode C. "
          f"{len({r['family'] for r in rows})} families. CIs are 95% percentile bootstrap intervals resampling whole families "
          f"({n_boot} resamples); `*` = fewer than 5 families (indicative only). A reply with no parsed verdict counts as wrong.\n",
          f"Sets: main {len(main)} samples; held-out domain {len(held)}; pilot imports {len(imp)} (reported apart).\n"]
    errs = [r for r in rows if r.get("score_error")]
    if errs:
        md.append(f"**{len(errs)} samples have a scoring error** (judge down); they count as unscored.\n")
    md += sections_main(main, figs, tag, n_boot)

    md.append("## 11. Held-out domain (military operational): its own panel\n")
    if held:
        arms = [a for a in ARM_ORDER if any(r["arm"] == a for r in held)]
        p = figs / f"held-out-{tag}.png"
        edges = bins_for(held, k=3)
        if edges:
            fig_headline(held, edges, p, title="Held-out domain: choice accuracy vs d")
            md.append(f"![held out]({p.relative_to(figs.parent) if figs.parent in p.parents else p})\n")
        md.append(table(["arm"] + [MODEL_LABEL[m] for m in models_in(held)],
                        [[a] + [pct(acc([r for r in held if r["model"] == m and r["arm"] == a], n_boot)) for m in models_in(held)] for a in arms]))
    else:
        md.append("No held-out-domain samples in this run.\n")

    md.append("## 12. Pilot imports (eval-only-import), separate set\n")
    if imp:
        arms = [a for a in ARM_ORDER if any(r["arm"] == a for r in imp)]
        md.append(table(["arm"] + [MODEL_LABEL[m] for m in models_in(imp)],
                        [[a] + [pct(acc([r for r in imp if r["model"] == m and r["arm"] == a], n_boot)) for m in models_in(imp)] for a in arms]))
    else:
        md.append("No pilot-import samples in this run.\n")

    other = [r for r in allrows if r.get("cell", "core") != "core"]
    md.append("## 13. Second-pass cells\n")
    if other:
        cells = sorted({r["cell"] for r in other})
        md.append(table(["cell", "arm"] + [MODEL_LABEL[m] for m in ms],
                        [[c, a] + [pct(acc([r for r in allrows if r["model"] == m and r.get("cell") == c and r["arm"] == a], n_boot)) for m in ms]
                         for c in ["core"] + cells for a in ARM_ORDER if any(r.get("cell", "core") == c and r["arm"] == a for r in allrows)]))
        md.append("Compare each cell with `core` on the same arm: ar_off (AR prompt off), thin (thin card on eligible relevant "
                  "pairs; core rows include non-eligible pairs), eq_off (E_d off, arms none and relevant).\n")
    else:
        md.append("Not run (AR off, thin view and the equities cells are wired in `eval.grid --cells`).\n")
    return "\n".join(md)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="run dirs with samples.jsonl (eval.grid output)")
    ap.add_argument("--tag", default=time.strftime("%Y-%m-%d"))
    ap.add_argument("--out")
    ap.add_argument("--figs", default="results/figures")
    ap.add_argument("--n-boot", type=int, default=stats.N_BOOT)
    a = ap.parse_args(argv)
    out = Path(a.out or f"results/RESULTS-{a.tag}.md")
    text = build(a.runs, Path(a.figs), a.tag, a.n_boot)
    if out.exists():
        v = out.parent / "versions"
        v.mkdir(exist_ok=True)
        shutil.copy2(out, v / f"{out.stem}.{time.strftime('%Y%m%d-%H%M%S')}-previous{out.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
