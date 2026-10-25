"""samples.jsonl (+ faithfulness output) -> results/RESULTS-<date>.md  (the PDF's Checkpoint 2 tables).

    PYTHONPATH=code .venv/bin/python -m eval.report results/checkpoint2/<run> [--out results/RESULTS-2026-10-25.md]

Per mode x arm x prompt: choice accuracy (95% CI, whole families resampled), format compliance (strict + all steps
present), options enumerated and gold-option omissions, relation and `via` accuracy, tokens and seconds, plus the
faithfulness change rate per mode, the copy-the-case baseline and the shortcut cues. A column whose scorer key
2d did not provide shows n/a (fix the aliases in eval/score_names.py).
An existing output file is never overwritten: it is copied to versions/ first (repo rule: keep every version).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from . import score_names, stats
from .core import ARMS, MODES, read_samples

MODE_LABEL = {"A": "A  thinking on", "B": "B  thinking off", "C": "C  structure in <think>", "Cprime": "C'  structure + notes in <think>"}


def pct(c, digits=0) -> str:
    if not c or c.get("mean") is None:
        return "n/a"
    f = lambda x: f"{100 * x:.{digits}f}"   # noqa: E731
    flag = "*" if c.get("few_families") else ""
    return f"{f(c['mean'])}% [{f(c['lo'])}-{f(c['hi'])}]{flag}"


def num(c, digits=0) -> str:
    if not c or c.get("mean") is None:
        return "n/a"
    return f"{c['mean']:.{digits}f}"


def table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def arm_order(rows):
    return [a for a in ARMS if any(r["arm"] == a for r in rows)]


def build(run_dir: Path, n_boot: int = stats.N_BOOT) -> str:
    rows = read_samples(run_dir / "samples.jsonl")
    if not rows:
        return "# No samples.\n"
    man = json.loads((run_dir / "manifest.json").read_text()) if (run_dir / "manifest.json").exists() else {}
    S = stats.summarize(rows, n_boot)
    cells = S["cells"]
    arms = arm_order(rows)
    modes = [m for m in MODES if any(r["mode"] == m for r in rows)]

    def cell(mode, arm, p, metric):
        return cells.get(f"{mode}|{arm}|{p}", {}).get(metric)

    md = [f"# Checkpoint 2 results: run `{run_dir.name}`  ({time.strftime('%Y-%m-%d')})\n"]
    md.append(f"Base model, untrained. {S['n_samples']} samples from {S['n_families']} case families; "
              f"{man.get('n_samples', '?')} samples per item. Policy: `{(man.get('policy') or {}).get('model') if isinstance(man.get('policy'), dict) else man.get('policy')}`. "
              f"Sampling/params: {json.dumps({k: v for k, v in (man.get('policy') or {}).items() if k != 'model'}) if isinstance(man.get('policy'), dict) else '?'}.\n")
    md.append("CIs are 95% percentile bootstrap intervals resampling whole case families "
              f"({n_boot} resamples). `*` = fewer than 5 families, treat the interval as indicative only. "
              "A reply with no parsed verdict counts as a wrong choice.\n")
    n_err = (run_dir / "errors.jsonl")
    if n_err.exists():
        md.append(f"**{len(n_err.read_text().splitlines())} sample attempts errored** (errors.jsonl); they are absent from every table.\n")
    n_score_err = sum(1 for r in rows if r.get("score_error"))
    if n_score_err:
        md.append(f"**{n_score_err} samples have a scoring error** (judge/scorer failed; run `eval.run_checkpoint2 --rescore`).\n")

    # 1. accuracy
    md.append("## 1. Choice accuracy (verdict `choice`, translated to gold ids, exact match)\n")
    hdr = ["mode", "arm"] + ["with prompt", "no prompt"]
    t = []
    for m in modes:
        for a in arms:
            t.append([MODE_LABEL[m], a, pct(cell(m, a, True, "choice_acc")), pct(cell(m, a, False, "choice_acc"))])
    md.append(table(hdr, t))
    md.append("Chance level is 1/#options (about 33% with three options). The copy-the-case baseline is in section 6.\n")

    # 2. format
    md.append("## 2. Format compliance\n")
    t = []
    for m in modes:
        for a in arms:
            for p in (True, False):
                t.append([MODE_LABEL[m], a, "on" if p else "off", pct(cell(m, a, p, "strict_ok")), pct(cell(m, a, p, "steps_present")),
                          pct(cell(m, a, p, "has_verdict")), pct(cell(m, a, p, "hit_length_cap"))])
    md.append(table(["mode", "arm", "prompt", "strict_ok (all steps valid, no repairs)", "all required steps present", "verdict parsed", "hit token cap"], t))

    # 3. options
    md.append("## 3. Options enumerated and gold-option omissions\n")
    t = []
    for m in modes:
        for a in arms:
            for p in (True, False):
                t.append([MODE_LABEL[m], a, "on" if p else "off", num(cell(m, a, p, "options_enumerated"), 1),
                          num(cell(m, a, p, "options_score"), 2), pct(cell(m, a, p, "gold_option_omitted")),
                          num(cell(m, a, p, "options_omitted"), 2)])
    md.append(table(["mode", "arm", "prompt", "mean #options listed", "options-enumeration score", "gold option omitted (rate)", "omitted count (scorer)"], t))

    # 4. relation, via
    md.append("## 4. Relation and `via` accuracy\n")
    t = []
    for m in modes:
        for a in arms:
            if a == "none":
                continue
            for p in (True, False):
                t.append([MODE_LABEL[m], a, "on" if p else "off", pct(cell(m, a, p, "relation_acc")), pct(cell(m, a, p, "via_acc"))])
    md.append(table(["mode", "arm", "prompt", "relation exact match", "via (flips only)"], t))

    # 5. tokens
    md.append("## 5. Tokens and time\n")
    t = []
    for m in modes:
        for a in arms:
            for p in (True, False):
                t.append([MODE_LABEL[m], a, "on" if p else "off", num(cell(m, a, p, "tokens_prompt")), num(cell(m, a, p, "tokens_completion")),
                          num(cell(m, a, p, "tokens_thinking")), num(cell(m, a, p, "seconds"), 1)])
    md.append(table(["mode", "arm", "prompt", "prompt tok", "completion tok", "thinking tok", "seconds"], t))

    # 6. contrasts + copy baseline
    md.append("## 6. Falsification contrasts (PDF p. 28)\n")
    t = []
    for c in S["contrasts"]:
        if c.get("diff") is None:
            continue
        t.append([MODE_LABEL[c["mode"]], "on" if c["prompt"] else "off", f"{c['a']} - {c['b']}",
                  f"{100 * c['diff']:+.0f} pts" + (f" [{100 * c['lo']:+.0f}, {100 * c['hi']:+.0f}]" if c.get("lo") is not None else "")])
    md.append(table(["mode", "prompt", "contrast (choice accuracy)", "difference [95% CI]"], t))
    md.append("Test 3: `decoy - none` below zero means irrelevant precedent misleads. Test 4: `relevant - copy_case_verdict` "
              "must be above zero or the gains are shortcuts, not reasoning (computed on scenarios whose served case verdict "
              "translates through the gold option map).\n")
    t = []
    for arm, c in S["copy_baseline"].items():
        t.append([arm, c["n_scenarios"], c["n_available"], pct(c["acc_translatable"]),
                  pct(c["acc_all"]) if c["acc_all"] else "n/a"])
    md.append("**Copy-the-case's-verdict baseline** (deterministic; per scenario-arm):\n\n" +
              table(["arm", "scenario-arms", "with translatable verdict", "accuracy (translatable)", "accuracy (all; untranslatable = wrong)"], t))

    # 7. faithfulness
    md.append("## 7. Faithfulness (edit the mapping, let the model continue, does the verdict change?)\n")
    fp = run_dir / "faithfulness_summary.json"
    if fp.exists():
        fs = json.loads(fp.read_text())
        t = []
        for k, v in fs.items():
            m, iv = k.split("|")
            ex = v.get("excess_over_control")
            t.append([MODE_LABEL[m], iv, pct(v), v["n"],
                      (f"{100 * ex['diff']:+.0f} pts [{100 * ex['lo']:+.0f}, {100 * ex['hi']:+.0f}]" if ex and ex.get("diff") is not None else "-")])
        md.append(table(["mode", "intervention", "verdict change rate [95% CI]", "n", "excess over control"], t))
        md.append("`control` regenerates the unedited partial: its change rate is sampling noise. Prediction under test: mode A is the least sensitive.\n")
    else:
        md.append("Not run for this run (`python -m eval.faithfulness <run dir>`).\n")

    # 8. shortcut cues
    cu = S["cues"]
    md.append("## 8. Shortcut cues\n")
    if cu:
        md.append(f"Over {cu['n_scenario_arms']} scenario-arms: gold option position counts {cu['gold_position_counts']} (0 = first); "
                  f"#options {cu['n_options_counts']}; gold moves {cu['gold_move_counts']}; gold is a hand-up move "
                  f"(ask/refuse): {100 * cu['gold_hand_up_rate']:.0f}%; gold is the longest option {100 * cu['gold_longest_rate']:.0f}% "
                  f"(chance {100 * cu['chance_longest']:.0f}%), shortest {100 * cu['gold_shortest_rate']:.0f}%; gold text length / mean other "
                  f"option length = {cu['gold_len_over_mean_other'] if cu['gold_len_over_mean_other'] is None else round(cu['gold_len_over_mean_other'], 2)}. "
                  f"Model picks its first-listed option in {'n/a' if cu['model_first_option_rate'] is None else format(100 * cu['model_first_option_rate'], '.0f') + '%'} of replies.\n")
        md.append("Accuracy by gold option position: " + ", ".join(f"#{int(p) + 1}: {pct(v)}" for p, v in cu["acc_by_gold_position"].items()) + ".\n")
        md.append("**Flags:** " + ("; ".join(cu["flags"]) if cu["flags"] else "none over the thresholds (gold position share > chance+20 pts, hand-up > 50%, longest/shortest > chance+20 pts, model first-option > 60%).") + "\n")
    # perturbation
    md.append("### Accuracy by perturbation (relevant and augmented arms, pooled over modes and prompt)\n")
    t = []
    for var in sorted({r["perturbation"]["variant"] for r in rows}):
        sub = [r for r in rows if r["perturbation"]["variant"] == var and r["arm"] in ("relevant", "augmented")]
        if sub:
            t.append([var, len({r["scenario"] for r in sub}), pct(stats.family_bootstrap(sub, stats.choice_correct, n_boot))])
    md.append(table(["variant", "scenarios", "choice accuracy"], t))
    md.append("Per-sample perturbation features (variant, operator, touched counts by kind and change) are in samples.jsonl `perturbation` for distance weighting.\n")

    # 9. housekeeping
    seen = {k for r in rows for k in (r.get("scores") or {})}
    missing = [m for m, al in score_names.ALIASES.items() if not any(k in seen for k in al)]
    md.append("## 9. Scorer keys seen\n")
    md.append(f"`{sorted(seen)}`. Metrics with no matching key (shown n/a above): {missing or 'none'}.\n")
    return "\n".join(md)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--out", default=f"results/RESULTS-{time.strftime('%Y-%m-%d')}.md")
    ap.add_argument("--n-boot", type=int, default=stats.N_BOOT)
    a = ap.parse_args(argv)
    text = build(Path(a.run_dir), a.n_boot)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        v = out.parent / "versions"
        v.mkdir(exist_ok=True)
        n = len(list(v.glob(out.stem + ".v*"))) + 1
        shutil.copy2(out, v / f"{out.stem}.v{n}-previous{out.suffix}")
    out.write_text(text)
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
