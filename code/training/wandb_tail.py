"""Stream a running trainer's stdout log into a wandb run (for jobs started before wandb was wired in, 2026-11-13).

HF/TRL print one dict per logging step (`{'loss': '0.50', ..., 'epoch': '0.18'}`); the global step is exact:
logging_steps x (train dicts so far), from the training config. After the first evaluation the progress bar
swallows printed dicts (eval and train alike; checked 2026-11-13), so the trainer's own log_history in each
checkpoint's trainer_state.json (every save_steps) and the final log_history.json is the complete source: every
train and eval entry with its exact step, deduplicated against what the stdout pass already logged. The live
stdout part covers only the steps before the first evaluation; native wandb (training.tracking) is live throughout. Metrics and run metadata only (see training.tracking); the sidecar exits when the
trainer's pid is gone, after a last pass over the log. Restarted, it resumes the run in <out>/wandb_run.json.

    PYTHONPATH=code .venv/bin/python -m training.wandb_tail --log logs/sft-run-gen1.log --pid 1715075 \\
        --config code/training/configs/sft_lora.v3-gen1.yaml --out results/sft/run-gen1
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import time
from pathlib import Path

from . import common, tracking

DICT = re.compile(r"\{'(?:loss|eval_loss|train_runtime)'[^{}]*\}")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", required=True)
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--kind", default="sft")
    ap.add_argument("--project")
    ap.add_argument("--poll", type=int, default=60)
    a = ap.parse_args(argv)
    cfg = common.load_config(a.config)
    t = cfg["train"]
    log_every = int(t["logging_steps"])
    run_file = Path(a.out) / "wandb_run.json"
    if run_file.exists():                  # restarted sidecar: resume the same wandb run, skip steps already logged
        os.environ["WANDB_RUN_ID"] = json.loads(run_file.read_text())["id"]
        os.environ["WANDB_RESUME"] = "allow"
    d = cfg.get("data") or {}
    import wandb
    rt = tracking.start(a.kind, cfg, a.out, data_files=[d.get("path"), d.get("eval_path")],
                        extra={"config_file": a.config, "streamed_from_log": a.log, "trainer_pid": a.pid},
                        project=a.project, name=f"{Path(a.out).name}", tags=["log-stream"])
    if rt != "wandb":
        raise SystemExit("wandb unavailable")
    wandb.define_metric("train/global_step")
    wandb.define_metric("*", step_metric="train/global_step")
    seen = 0
    n_train = 0
    done_step = int(wandb.run.summary.get("train/global_step") or 0)
    train_steps_logged = set(range(log_every, done_step + 1, log_every))
    eval_steps_logged = set()
    while True:
        alive = _alive(a.pid)
        text = Path(a.log).read_text(errors="replace")
        found = DICT.findall(text)
        for s in found[seen:]:
            try:
                rec = ast.literal_eval(s)
            except (ValueError, SyntaxError):
                continue
            vals = {k: _num(v) for k, v in rec.items()}
            if "eval_loss" in rec:
                continue                                    # eval comes from log_history (below), exact steps
            elif "train_runtime" in rec:
                wandb.run.summary.update({f"train/{k}": v for k, v in vals.items() if v is not None})
            else:
                n_train += 1
                step = n_train * log_every
                if step in train_steps_logged:
                    continue
                train_steps_logged.add(step)
                wandb.log({"train/global_step": step, **{f"train/{k}": v for k, v in vals.items() if v is not None}})
        seen = len(found)
        hists = sorted(Path(a.out).glob("checkpoint-*/trainer_state.json")) + [Path(a.out) / "log_history.json"]
        for hp in hists:
            if not hp.exists():
                continue
            try:
                h = json.loads(hp.read_text())
            except ValueError:
                continue
            for e in (h.get("log_history") if isinstance(h, dict) else h) or []:
                if "loss" in e and "eval_loss" not in e and e.get("step") not in train_steps_logged:
                    train_steps_logged.add(e.get("step"))
                    wandb.log({"train/global_step": e["step"], **{f"train/{k}": _num(v) for k, v in e.items()
                                                                  if k not in ("step",) and _num(v) is not None}})
                if "eval_loss" in e and e.get("step") not in eval_steps_logged:
                    eval_steps_logged.add(e.get("step"))
                    wandb.log({"train/global_step": e["step"], "train/epoch": e.get("epoch"),
                               **{f"eval/{k[5:]}": _num(v) for k, v in e.items() if k.startswith("eval_")}})
        if not alive:
            break
        time.sleep(a.poll)
    hist = Path(a.out) / "log_history.json"
    if hist.exists():
        wandb.run.summary["log_history_file"] = str(hist)
        wandb.run.summary["final_log_entries"] = len(json.loads(hist.read_text()))
    tracking.finish()


if __name__ == "__main__":
    main()
