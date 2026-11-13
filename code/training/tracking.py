"""Experiment tracking with Weights & Biases (Peter, 2026-11-13: "wire things up for wandb").

What goes to wandb: training metrics (loss, eval loss, learning rate, grad norm, token accuracy, rewards for GRPO) and
run metadata (the training config, data file paths with sha256 and row counts by arm / source, git commit, output dir).
What never goes: prompts, targets, completions or adapter weights (WANDB_LOG_MODEL=false; nothing is uploaded as an
artifact). The training data are natsec decision text; they stay on the box.

Credentials come from ~/.netrc (`wandb login`); nothing here reads or prints the key. Project defaults to
`benchbook` (override with WANDB_PROJECT or --wandb-project); entity from WANDB_ENTITY or the login's default.

    # in a trainer
    report_to = tracking.start("sft", cfg, out, data_files=[...], enabled=not a.no_wandb)
    ...SFTConfig(report_to=report_to)...    # HF's WandbCallback reuses the run started here
    tracking.finish()
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

DEFAULT_PROJECT = "benchbook"


def _git() -> dict:
    root = Path(__file__).resolve().parents[2]
    def run(*a):
        try:
            return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:                                               # noqa: BLE001
            return None
    return {"commit": run("rev-parse", "HEAD"), "dirty_code": bool(run("status", "--porcelain", "--", "code"))}


def data_summary(path: str) -> dict:
    """sha256 + counts of a JSONL training file (by meta.arm / meta.source when present). Reads, never uploads, rows."""
    p = Path(path)
    if not p.exists():
        return {"path": str(path), "missing": True}
    h = hashlib.sha256()
    arms, sources, n = collections.Counter(), collections.Counter(), 0
    with open(p, "rb") as f:
        for line in f:
            h.update(line)
            if not line.strip():
                continue
            n += 1
            try:
                m = json.loads(line).get("meta") or {}
            except ValueError:
                continue
            arms[m.get("arm")] += 1
            sources[m.get("source")] += 1
    out = {"path": str(path), "sha256": h.hexdigest(), "rows": n}
    if any(k for k in arms):
        out["by_arm"] = dict(arms)
    if any(k for k in sources):
        out["by_source"] = dict(sources)
    return out


def metadata(kind: str, cfg: dict, out: str, data_files=(), extra: dict | None = None) -> dict:
    return {"kind": kind, "train_config": cfg, "out": str(out), "git": _git(),
            "data": [data_summary(d) for d in data_files if d], **(extra or {})}


def start(kind: str, cfg: dict, out: str, data_files=(), extra: dict | None = None, enabled: bool = True,
          project: str | None = None, name: str | None = None, tags=()) -> str:
    """Start a wandb run for this training job; returns the `report_to` value for the HF/TRL config ("wandb" or
    "none"). Disabled (or wandb unavailable / not logged in) -> "none", and training goes on untracked."""
    if not enabled:
        return "none"
    try:
        import wandb
    except ImportError:
        print("tracking: wandb not installed; training untracked", flush=True)
        return "none"
    os.environ["WANDB_LOG_MODEL"] = "false"          # never upload checkpoints or adapters
    os.environ.setdefault("WANDB_WATCH", "false")
    os.environ.setdefault("WANDB_SILENT", "true")
    Path(out).mkdir(parents=True, exist_ok=True)
    try:
        wandb.init(project=project or os.environ.get("WANDB_PROJECT") or DEFAULT_PROJECT,
                   entity=os.environ.get("WANDB_ENTITY") or None, group=kind, job_type="train",
                   name=name or f"{Path(out).name}-{time.strftime('%Y%m%dT%H%MZ', time.gmtime())}",
                   tags=[kind, *tags], dir=str(out), config=metadata(kind, cfg, out, data_files, extra))
    except Exception as e:                                              # noqa: BLE001
        print(f"tracking: wandb.init failed ({type(e).__name__}: {e}); training untracked", flush=True)
        return "none"
    (Path(out) / "wandb_run.json").write_text(json.dumps({"url": wandb.run.url, "id": wandb.run.id,
                                                          "project": wandb.run.project}, indent=1))
    print(f"tracking: wandb run {wandb.run.url}", flush=True)
    return "wandb"


def finish():
    try:
        import wandb
        if wandb.run is not None:
            wandb.finish()
    except ImportError:
        pass
