"""M17 (2026-11-14): base Granite vs SFT gen1 (final adapter, checkpoint-300) on the pairs-v1 val cells, per
case-trace relationship. Format v4, mode B, k=4.

Per run x arm, X1-averaged with a 95% family bootstrap (eval.allpairs_report.fam_boot, B=2000):
  correct        choice maps to the cell's key (as scored by allpairs: Jev Choice option alignment)
  correct_text   same, but when the reply's options list repeats X1's option texts verbatim, the choice is mapped by
                 that text (no judge). The SFT model often numbers the options differently from the key; the judge
                 then sometimes maps both key options onto one reply option and the reply is scored off-menu
                 (131 of the final adapter's 428 such replies). Where the judge did map, it agreed with the text in
                 every case, so this only rescues judge failures.
  readable(_text) a choice that maps to an option
  copied         the choice (text-corrected) equals the served case's verdict traced back to X1's options
                 (tensor.served_verdict_live); on flip arms copying is the error
  relation_ok    the verdict's relation is the arm's expected one (replies with a verdict)
  not_governed   relation == not_governed (replies with a verdict)
  agree_nocase   unrelated arm (Peter, 2026-11-13): chance the reply's choice equals a random no-case reply of the same
                 run on the same X1 (readable, text-corrected); control rows = leave-one-out baseline

    PYTHONPATH=code .venv/bin/python -m eval.analysis.m17_sft_val [--out results/pairs-v1/eval-val/m17-report.md]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

D = Path("results/pairs-v1/eval-val")
RUNS = {"base": "base-v4B", "sft-ckpt300": "sft-ckpt300-v4B", "sft-final": "sft-final-v4B"}
ORDER = ["control", "self", "revised", "neighbor", "noflip", "transfer", "xd_neighbor", "xd_noflip",
         "same_domain_flip", "flip_neighbor", "transfer_flip", "random"]
LABEL = {"control": "No case", "self": "Own case", "revised": "Revised case", "neighbor": "In-domain neighbor",
         "noflip": "Non-flip edit", "transfer": "Cross-domain transfer", "xd_neighbor": "Cross-domain neighbor*",
         "xd_noflip": "Cross-domain non-flip edit*", "same_domain_flip": "In-domain flip",
         "flip_neighbor": "Flip-neighbor*", "transfer_flip": "Flip-transfer", "random": "Unrelated case"}
EXPECT = {"self": "follows", "revised": "follows", "neighbor": "follows", "noflip": "follows", "transfer": "follows",
          "xd_neighbor": "follows", "xd_noflip": "follows", "same_domain_flip": "flips", "flip_neighbor": "flips",
          "transfer_flip": "flips", "random": "not_governed"}
COPY = {"neighbor", "noflip", "transfer", "xd_neighbor", "xd_noflip", "same_domain_flip", "flip_neighbor",
        "transfer_flip"}


def _norm(s) -> str:
    return re.sub(r"\W+", " ", str(s).lower()).strip()


def collect() -> list[dict]:
    from bench.schema import parse_reply
    from pipeline.store import Store
    from pipeline.project.project import gold_for
    from eval.allpairs import none_pair
    from eval.analysis.tensor import served_verdict_live
    store, keys, served, rows = Store(), {}, {}, []
    for name, rd in RUNS.items():
        d = D / rd
        cells = {(c["arm"], c["x1"], c["x2"]): c for c in json.loads((d / "config.json").read_text())["cells"]}
        for line in (d / "samples.jsonl").read_text().splitlines():
            s = json.loads(line)
            x1, arm = s["x1"], s["phase"]
            if x1 not in keys:
                keys[x1] = gold_for(none_pair(store, x1, "pilot2"), store)[1]
            gold_txt = {_norm(o.do): g for g, o in keys[x1].options.items()}
            p = parse_reply((d / s["raw_path"]).read_text())
            opts = (p.steps.get("fact_enumeration") or {}).get("options")
            txt = {k: _norm(v) for k, v in opts.items() if isinstance(v, str)} if isinstance(opts, dict) else {}
            exact = bool(txt) and all(v in gold_txt for v in txt.values())
            choice = s.get("translated_choice")
            if exact and s.get("parsed_choice") in txt:
                choice_t = gold_txt[txt[s["parsed_choice"]]]
            else:
                choice_t = choice
            target = None
            if arm in COPY:
                ck = (arm, x1, s["x2"])
                if ck not in served:
                    served[ck] = served_verdict_live(store, cells[ck], keys)
                target = served[ck]
            rel = s.get("model_relation")
            has_v = s.get("parsed_choice") is not None
            rows.append({
                "run": name, "arm": arm, "x1": x1, "family": s.get("x1_family"), "idx": s["idx"],
                "gold": s["gold_choice"], "choice": choice, "choice_t": choice_t,
                "correct": float(choice is not None and choice == s["gold_choice"]) if s.get("correct") is not None
                else 0.0,
                "correct_text": float(choice_t is not None and choice_t == s["gold_choice"]),
                "readable": float(choice is not None), "readable_text": float(choice_t is not None),
                "copied": (float(choice_t == target) if (target is not None and choice_t is not None) else None),
                "relation_ok": (float(rel == EXPECT[arm]) if (arm in EXPECT and has_v) else None),
                "not_governed": (float(rel == "not_governed") if (arm != "control" and has_v) else None),
                "exact_opts": float(exact), "swapped": float(exact and any(gold_txt[v] != k for k, v in txt.items())),
                "no_verdict": float(not has_v), "truncated": float(s.get("finish_reason") == "length"),
                "completion_tokens": (s.get("tokens") or {}).get("completion"),
            })
    # agreement with the same run's own no-case choices (text-corrected, readable)
    nc = defaultdict(Counter)
    for r in rows:
        if r["arm"] == "control" and r["choice_t"] is not None:
            nc[(r["run"], r["x1"])][r["choice_t"]] += 1
    for r in rows:
        cnt = nc.get((r["run"], r["x1"]))
        r["agree_nocase"] = None
        if cnt and r["choice_t"] is not None and r["arm"] in ("control", "random"):
            cnt = Counter(cnt)
            if r["arm"] == "control":
                cnt[r["choice_t"]] -= 1
            n = sum(cnt.values())
            if n > 0:
                r["agree_nocase"] = cnt[r["choice_t"]] / n
    return rows


def stat(rows, col):
    from eval.allpairs_report import fam_boot
    per, fam = defaultdict(list), {}
    for r in rows:
        if r[col] is not None:
            per[r["x1"]].append(r[col])
            fam[r["x1"]] = r["family"]
    if not per:
        return None
    m, lo, hi = fam_boot({k: sum(v) / len(v) for k, v in per.items()}, fam, B=2000)
    return {"m": m, "lo": lo, "hi": hi, "nx": len(per), "n": sum(len(v) for v in per.values())}


def fmt(s, ci=True):
    if s is None:
        return "—"
    return f"{100 * s['m']:.1f}" + (f" [{100 * s['lo']:.1f}, {100 * s['hi']:.1f}]" if ci else "")


def report(rows) -> tuple[str, dict]:
    by = defaultdict(list)
    for r in rows:
        by[(r["run"], r["arm"])].append(r)
    S = {f"{run}|{arm}": {c: stat(by[(run, arm)], c) for c in
                          ("correct", "correct_text", "readable", "readable_text", "copied", "relation_ok",
                           "not_governed", "agree_nocase", "exact_opts", "swapped", "no_verdict", "truncated")}
         | {"replies": len(by[(run, arm)])}
         for run in RUNS for arm in ORDER}
    L = ["# M17 tables (generated by `code/eval/analysis/m17_sft_val.py`)", "",
         "X1-averaged %, 95% family bootstrap in brackets. * = extension arm (not in SFT gen1's training data).", ""]

    def table(title, col, note=""):
        L.extend([f"## {title}", ""] + ([note, ""] if note else []))
        L.append("| Relationship | replies | " + " | ".join(RUNS) + " |")
        L.append("|---|---|" + "---|" * len(RUNS))
        for arm in ORDER:
            vals = [fmt(S[f"{run}|{arm}"][col]) for run in RUNS]
            if all(v == "—" for v in vals):
                continue
            L.append(f"| {LABEL[arm]} | {S[f'base|{arm}']['replies']} | " + " | ".join(vals) + " |")
        L.append("")
    table("Choice accuracy, text-corrected (headline)", "correct_text",
          "The cell's key: X1's gold, except the revised arm (C''s verdict). Options listed verbatim are mapped by text.")
    table("Choice accuracy, as scored (Jev Choice option alignment)", "correct")
    table("Readable (choice maps to an option), as scored", "readable")
    table("Readable, text-corrected", "readable_text")
    table("Copied the served case's verdict (text-corrected; on flip arms this is the error)", "copied")
    table("Relation label correct", "relation_ok")
    table("Labelled not_governed", "not_governed")
    table("Agreement with own no-case choice (unrelated arm; control = leave-one-out baseline)", "agree_nocase")
    table("Options listed verbatim (X1's option texts)", "exact_opts")
    table("Options listed verbatim but numbered differently from the key", "swapped")
    table("No verdict", "no_verdict")
    return "\n".join(L) + "\n", S


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D / "m17-report.md"))
    a = ap.parse_args(argv)
    rows = collect()
    md, S = report(rows)
    Path(a.out).write_text(md)
    Path(a.out).with_suffix(".json").write_text(json.dumps(S, indent=1))
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
