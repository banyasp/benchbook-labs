"""Figures for an eval.allpairs run (static PNGs for the report; light theme, reference palette of the dataviz method).

    PYTHONPATH=code .venv/bin/python -m eval.allpairs_plots --run results/allpairs/B2

Writes to <run>/figures/:
    headline.png        verdict accuracy per measure (mean over X1, 95% family-bootstrap CI), chance marked
    matrix.png          the who-helps-whom matrix: X1 rows x X2 columns, grouped by family; cell = correct / wrong
                        with the case, coloured by help (right where the no-case model is usually wrong) and harm
                        (wrong where it is usually right); left strip = the X1's no-case success rate
    secondary.png       secondary metrics (facts, options, frame, considerations) for control / random case / best case
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

from .allpairs_report import build, fam_boot, ok  # noqa: E402

# reference palette (dataviz references/palette.md), light mode
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"           # categorical slots 1-3 (validated all-pairs)
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
HELP, HARM, NEUTRAL_OK, NEUTRAL_NO, NOTRUN = "#256abf", "#e34948", "#9ec5f4", "#f0efec", SURFACE


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def headline(R, out: Path):
    fam = R["fam"]
    rows = [("No case (control)", R["p0"]), ("Random case (mean over X2)", R["rand"]),
            ("Best case (confirmed)", R["best"]), ("Own case (X2 = X1)", R["selfc"])]
    rows = [(lab, fam_boot(d, fam), sum(1 for v in d.values() if v is not None)) for lab, d in rows]
    nopt = [r.get("x1_n_options") for r in R["S"] if r.get("x1_n_options")]
    chance = (sum(1 / n for n in nopt) / len(nopt)) if nopt else None
    fig, ax = plt.subplots(figsize=(7.5, 3.2), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    for i, (lab, (m, lo, hi), n) in enumerate(rows[::-1]):
        if m != m:
            ax.text(0.01, i, "not run yet", va="center", color=MUTED, fontsize=9)
            continue
        ax.plot([lo, hi], [i, i], color=BLUE, linewidth=2, solid_capstyle="round")
        ax.plot([m], [i], "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.text(hi + 0.015, i, f"{100 * m:.0f}%  (n={n})", va="center", color=INK, fontsize=9)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows[::-1]], color=INK)
    if chance:
        ax.axvline(chance, color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
        ax.text(chance + 0.01, -0.45, f"chance {100 * chance:.0f}%", color=MUTED, fontsize=8, ha="left", va="center")
    ax.set_xlim(0, 1.08)
    ax.set_xticks([0, .25, .5, .75, 1])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Verdict matches the answer key (mean over X1, 95% CI by family)", color=INK2, fontsize=9)
    ax.set_title(f"Case benefit: {R['cfg'].get('x1') and len(R['cfg']['x1'])} live scenarios, base Granite",
                 color=INK, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def matrix(R, out: Path):
    x1s = [x for x in R["cfg"]["x1"] if x in R["fam"]]
    x2s = R["cfg"]["x2"]
    fam = R["fam"]
    famx2 = {}
    for r in R["S"]:
        if r.get("x2"):
            famx2[r["x2"]] = r.get("x2_family")
    o1 = sorted(x1s, key=lambda x: (fam.get(x) or "", x))
    o2 = sorted(x2s, key=lambda x: (famx2.get(x) or fam.get(x) or "", x))
    # codes: 0 not run, 1 wrong (control usually right = harm), 2 wrong (neutral), 3 right (neutral), 4 right (help)
    M = []
    for x in o1:
        p = R["p0"].get(x)
        row = []
        for y in o2:
            r = R["grid"].get((x, y))
            if r is None:
                row.append(0)
                continue
            c = ok(r["correct"]) == 1.0
            if p is None:
                row.append(3 if c else 2)
            elif c:
                row.append(4 if p < 0.5 else 3)
            else:
                row.append(1 if p >= 0.5 else 2)
        M.append(row)
    n1, n2 = len(o1), len(o2)
    size = max(6.0, min(14.0, 0.09 * n2 + 3))
    fig = plt.figure(figsize=(size + 1.2, size * n1 / max(1, n2) + 1.6), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, max(8, n2 // 4)], wspace=0.02)
    axc, ax = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    cmap = ListedColormap([NOTRUN, HARM, NEUTRAL_NO, NEUTRAL_OK, HELP])
    ax.imshow(M, cmap=cmap, vmin=0, vmax=4, aspect="auto", interpolation="nearest")
    ctrl = [[R["p0"].get(x) if R["p0"].get(x) is not None else float("nan")] for x in o1]
    axc.imshow(ctrl, cmap=ListedColormap(SEQ), vmin=0, vmax=1, aspect="auto", interpolation="nearest")
    for a in (ax, axc):
        a.set_xticks([])
        a.set_yticks([])
        for s in a.spines.values():
            s.set_visible(False)
    # family boundaries
    def bounds(order, f):
        out, prev = [], None
        for i, x in enumerate(order):
            if f(x) != prev and i:
                out.append(i - 0.5)
            prev = f(x)
        return out
    for b in bounds(o1, lambda x: fam.get(x)):
        ax.axhline(b, color=SURFACE, linewidth=1.2)
        axc.axhline(b, color=SURFACE, linewidth=1.2)
    for b in bounds(o2, lambda x: famx2.get(x) or fam.get(x)):
        ax.axvline(b, color=SURFACE, linewidth=1.2)
    axc.set_xlabel("no-case\nrate", color=INK2, fontsize=8)
    ax.set_xlabel("X2: the case served (grouped by family)", color=INK2, fontsize=9)
    axc.set_ylabel("X1: the live scenario (grouped by family)", color=INK2, fontsize=9)
    ax.set_title("Who helps whom", color=INK, fontsize=11, loc="left")
    from matplotlib.patches import Patch
    leg = [Patch(color=HELP, label="right with this case; usually wrong without (help)"),
           Patch(color=NEUTRAL_OK, label="right with this case; usually right without"),
           Patch(color=NEUTRAL_NO, label="wrong with this case; usually wrong without"),
           Patch(color=HARM, label="wrong with this case; usually right without (harm)"),
           Patch(facecolor=NOTRUN, edgecolor=AXIS, label="not run yet")]
    fig.legend(handles=leg, loc="lower center", ncol=2, frameon=False, fontsize=8, labelcolor=INK2,
               bbox_to_anchor=(0.55, -0.01))
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(out, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def secondary(R, out: Path):
    names = list(R["sec"])
    colors = [BLUE, ORANGE, AQUA]
    metrics = [("facts found / gold", "Facts (F): found / gold"),
               ("options found / gold", "Options (Q): found / gold"),
               ("frame_question", "Question frame (Q): Jev_Noul"),
               ("frame_decider", "Decider (Q): Jev_Noul"),
               ("considerations found / gold", "Considerations (K): found / gold"),
               ("considerations_enum.equity", "Considerations (K): equity exact")]
    fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    off = [-0.22, 0, 0.22]
    for k, (name, col) in enumerate(zip(names, colors)):
        for i, (m, _) in enumerate(metrics[::-1]):
            v = R["sec"][name].get(m)
            if v is None:
                continue
            ax.plot([v], [i + off[k]], "o", color=col, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2,
                    label=name if i == 0 else None)
            ax.text(v + 0.015, i + off[k], f"{v:.2f}", va="center", fontsize=7, color=INK2)
    ax.set_yticks(range(len(metrics)))
    ax.set_yticklabels([m[1] for m in metrics[::-1]], color=INK)
    ax.set_xlim(0, 1.08)
    ax.set_xlabel("mean per sample (1 = everything in the answer key recovered)", color=INK2, fontsize=9)
    ax.set_title("Where along the reasoning the case helps", color=INK, fontsize=11, loc="left")
    ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    a = ap.parse_args(argv)
    run = Path(a.run)
    R = build(run)
    d = run / "figures"
    d.mkdir(exist_ok=True)
    headline(R, d / "headline.png")
    matrix(R, d / "matrix.png")
    secondary(R, d / "secondary.png")
    print(sorted(str(p) for p in d.glob("*.png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
