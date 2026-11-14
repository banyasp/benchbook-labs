"""One autoresearch trial for one-epoch LoRA SFT (2026-11-14; Peter: tune the hyperparameters within one epoch,
in the spirit of Karpathy's autoresearch). Read `program.md` first.

A trial = the base config (`sft_lora.v4-1epoch.yaml`) + overrides, trained for ONE epoch on a fixed, arm-stratified
quarter of the gen1 training rows (the proxy: ~69 optimizer steps, ~1 h), then scored once on the full gen1
validation set (296 rows, val-split anchors). The metric is the final validation loss (lower is better);
token accuracy and entropy are recorded alongside. Every trial, failed or not, gets a row in `results.tsv`.

    PYTHONPATH=code .venv/bin/python -m training.autoresearch.run_trial --name ar-001 \
        --desc "baseline" [--set train.learning_rate=2e-4 --set lora.r=32 ...] [--full]

`--full` trains on all 2,210 rows (the confirmation run for a finalist, ~4 h).
Writes: results/sft/autoresearch/<name>/ (config.yaml, train.log, trial.json, <name>/ = the sft_lora run with its checkpoints),
        code/training/autoresearch/trials/<name>.yaml (the config, in git), and a row in both results.tsv files.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "code/training/configs/sft_lora.v4-1epoch.yaml"
TRAIN = ROOT / "results/sft/gen1/golden.jsonl"
VAL = ROOT / "results/sft/gen-val/golden.jsonl"
OUT = ROOT / "results/sft/autoresearch"
SUBSET = OUT / "subset-train-q1.jsonl"            # fixed for every trial
GIT = Path(__file__).resolve().parent
TSV_COLS = ["name", "utc", "data", "val_loss", "val_acc", "val_entropy", "train_loss", "steps", "minutes", "status",
            "overrides", "desc"]


def make_subset(frac: float = 0.25, seed: str = "autoresearch-q1|0") -> Path:
    """Arm-stratified quarter of the gen1 rows, drawn once and reused (same rows, same order, every trial)."""
    if SUBSET.exists():
        return SUBSET
    rows = [json.loads(l) for l in TRAIN.read_text().splitlines() if l.strip()]
    by = defaultdict(list)
    for r in rows:
        by[(r.get("meta") or {}).get("arm")].append(r)
    rng, keep = random.Random(seed), []
    for arm in sorted(by, key=str):
        g = sorted(by[arm], key=lambda r: r["id"])
        keep += rng.sample(g, round(len(g) * frac))
    keep.sort(key=lambda r: r["id"])
    OUT.mkdir(parents=True, exist_ok=True)
    SUBSET.write_text("".join(json.dumps(r) + "\n" for r in keep))
    return SUBSET


def _set(cfg: dict, dotted: str, raw: str):
    *path, last = dotted.split(".")
    d = cfg
    for k in path:
        d = d.setdefault(k, {})
    v = yaml.safe_load(raw)
    if isinstance(v, str):                        # YAML 1.1 reads "2e-4" as a string: make it a number
        try:
            v = float(v)
        except ValueError:
            pass
    d[last] = v


def _append(row: dict):
    for p in (OUT / "results.tsv", GIT / "results.tsv"):
        new = not p.exists()
        with p.open("a") as f:
            if new:
                f.write("\t".join(TSV_COLS) + "\n")
            f.write("\t".join(str(row.get(c, "")).replace("\t", " ") for c in TSV_COLS) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--desc", required=True, help="what this trial changes and why (one line)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="dotted override, YAML value")
    ap.add_argument("--full", action="store_true", help="all gen1 rows (confirmation run)")
    ap.add_argument("--no-wandb", action="store_true")
    a = ap.parse_args(argv)
    d = OUT / a.name
    if d.exists():
        raise SystemExit(f"{d} exists: trial names are never reused")
    cfg = yaml.safe_load(BASE.read_text())
    over = {}
    for s in a.set:
        k, v = s.split("=", 1)
        _set(cfg, k, v)
        over[k] = v
    t = cfg["train"]
    t["num_train_epochs"] = 1                     # the point of the exercise: one epoch, never more
    t["eval_strategy"] = "steps"
    t["eval_steps"] = 100000                      # validation once, at the end of the epoch
    data = TRAIN if a.full else make_subset()
    d.mkdir(parents=True)
    (d / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    (GIT / "trials" / f"{a.name}.yaml").write_text(
        f"# {a.desc}\n# data: {os.path.relpath(data, ROOT)}; overrides: {json.dumps(over)}\n" + yaml.safe_dump(cfg, sort_keys=False))
    cmd = [sys.executable, "-m", "training.sft_lora", "--config", str(d / "config.yaml"), "--data", str(data),
           "--eval-data", str(VAL), "--out", str(d / a.name)] + (["--no-wandb"] if a.no_wandb else [])
    t0 = time.time()
    with (d / "train.log").open("w") as log:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    mins = round((time.time() - t0) / 60, 1)
    row = {"name": a.name, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()), "minutes": mins,
           "data": "full" if a.full else "q1", "overrides": json.dumps(over), "desc": a.desc}
    hist_p = d / a.name / "log_history.json"
    if rc != 0 or not hist_p.exists():
        tail = (d / "train.log").read_text()[-3000:]
        row["status"] = "oom" if "OutOfMemory" in tail or "CUDA out of memory" in tail else f"crash(rc={rc})"
    else:
        h = json.loads(hist_p.read_text())
        ev = [x for x in h if "eval_loss" in x]
        tr = [x for x in h if "loss" in x and "eval_loss" not in x]
        end = [x for x in h if "train_loss" in x]
        if not ev:
            row["status"] = "no-eval"
        else:
            e = ev[-1]
            row.update(val_loss=round(e["eval_loss"], 5), val_acc=round(e.get("eval_mean_token_accuracy", float("nan")), 5),
                       val_entropy=round(e.get("eval_entropy", float("nan")), 4), status="ok")
        row["steps"] = (tr[-1]["step"] if tr else None)
        row["train_loss"] = round(end[-1]["train_loss"], 5) if end else None
    (d / "trial.json").write_text(json.dumps(row, indent=1))
    _append(row)
    print(json.dumps(row))
    return 0 if row["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
