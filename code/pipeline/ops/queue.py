"""Human task queue (OPERATORS-SPEC-v1 §Solver module, `human` backend; console labelling pages).

    data/store/queue/<task_id>.yaml    one task: {id, type, created, source, ref, payload, context}
    data/labels/labels.jsonl           append-only answers: {task_id, type, answer, ground_truth, note, ts, by}

Never edits source data. A task's current answer is its LAST label line (earlier lines stay as the record).

Task types
    verdict          BLIND: payload holds only the frame, facts, question and options (no gold, reasoning, Φ, parent)
    condition_holds  payload: facts + the `if` text -> holds yes/no
    review           spot-check of an operator output: ref = scenario id; the page shows before/after vs its parent,
                     the step's gates and annotations -> approve / reject / edit (+ note, ground_truth)

Resuming an operator chain from an answer is NOT built (docs/OUTSTANDING.md).
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
QUEUE = ROOT / "data" / "store" / "queue"
LABELS = ROOT / "data" / "labels" / "labels.jsonl"
TYPES = ("verdict", "condition_holds", "review")
_LOCK = threading.Lock()


def blind_case(case: dict) -> dict:
    """Only F and Q and the agent frame; never considerations, reasoning, verdict or flip conditions."""
    keep = ("title", "setting", "decider", "agent", "agent_role", "situation", "question", "facts")
    shown = {k: case[k] for k in keep if k in case}
    shown["options"] = {k: {"do": v["do"]} for k, v in case["options"].items()}
    return shown


def _task_id(kind: str, ref: str | None, payload: dict) -> str:
    h = hashlib.sha256(json.dumps([kind, ref, payload], sort_keys=True, default=str).encode()).hexdigest()[:10]
    return f"{kind[:3].upper()}-{h}"


def enqueue(kind: str, payload: dict, *, ref: str | None = None, source: str = "manual", context: dict | None = None,
            queue: Path = QUEUE) -> str:
    """Write one task (idempotent: the same kind+ref+payload gives the same id and is not duplicated)."""
    if kind not in TYPES:
        raise ValueError(f"unknown task type {kind!r}")
    if kind == "verdict" and any(k in payload.get("case", {}) for k in ("verdict", "reasoning", "considerations",
                                                                         "flip_conditions")):
        raise ValueError("verdict tasks are blind: pass blind_case(case)")
    tid = _task_id(kind, ref, payload)
    p = queue / f"{tid}.yaml"
    if not p.exists():
        queue.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump({"id": tid, "type": kind, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                     "source": source, "ref": ref, "payload": payload, "context": context or {}},
                                    sort_keys=False, allow_unicode=True, width=120))
    return tid


def enqueue_review(scenario_id: str, *, source: str = "manual", queue: Path = QUEUE) -> str:
    return enqueue("review", {"scenario": scenario_id}, ref=scenario_id, source=source, queue=queue)


def labels(path: Path = LABELS) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def latest_labels(path: Path = LABELS) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in labels(path):
        out[r["task_id"]] = r
    return out


def tasks(queue: Path = QUEUE, labels_path: Path = LABELS) -> list[dict]:
    lab = latest_labels(labels_path)
    out = []
    for p in sorted(queue.glob("*.yaml")):
        t = yaml.safe_load(p.read_text())
        t["answer"] = lab.get(t["id"])
        out.append(t)
    out.sort(key=lambda t: (t["answer"] is not None, t.get("created", ""), t["id"]))
    return out


def task(tid: str, queue: Path = QUEUE) -> dict | None:
    p = queue / f"{tid}.yaml"
    if not p.exists() or "/" in tid:
        return None
    return yaml.safe_load(p.read_text())


def answer(tid: str, ans, *, ground_truth=None, note: str = "", by: str = "peter", labels_path: Path = LABELS,
           queue: Path = QUEUE) -> dict:
    t = task(tid, queue)
    if t is None:
        raise KeyError(tid)
    row = {"task_id": tid, "type": t["type"], "ref": t.get("ref"), "answer": ans, "ground_truth": ground_truth,
           "note": note, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "by": by}
    with _LOCK:
        labels_path.parent.mkdir(parents=True, exist_ok=True)
        with labels_path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def answer_of(tid: str, labels_path: Path = LABELS) -> dict | None:
    return latest_labels(labels_path).get(tid)


# ------------------------------------------------------------------ sign-off (Peter, 2026-11-11)
SIGNOFF_KINDS = ("scenario", "batch", "run")
SIGNOFF_DECISIONS = ("approve", "reject", "needs-work")


def signoff(target_kind: str, target_id: str, decision: str, note: str = "", by: str = "peter",
            labels_path: Path = LABELS) -> dict:
    """Record a sign-off on a scenario, a batch / dataset version, or a run (append-only; the last one counts)."""
    if target_kind not in SIGNOFF_KINDS or decision not in SIGNOFF_DECISIONS:
        raise ValueError(f"bad sign-off {target_kind!r} / {decision!r}")
    row = {"task_id": f"signoff:{target_kind}:{target_id}", "type": "signoff", "target_kind": target_kind,
           "target_id": target_id, "decision": decision, "answer": decision, "note": note,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "by": by}
    with _LOCK:
        labels_path.parent.mkdir(parents=True, exist_ok=True)
        with labels_path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def signoffs(labels_path: Path = LABELS) -> dict[tuple[str, str], dict]:
    """(target_kind, target_id) -> latest sign-off row, with `history` = all earlier rows for that target."""
    out: dict[tuple[str, str], dict] = {}
    hist: dict[tuple[str, str], list] = {}
    for r in labels(labels_path):
        if r.get("type") == "signoff":
            k = (r["target_kind"], r["target_id"])
            hist.setdefault(k, []).append(r)
            out[k] = r
    for k, v in out.items():
        v["history"] = hist[k]
    return out


def tasks_only(queue: Path = QUEUE, labels_path: Path = LABELS) -> list[dict]:
    return tasks(queue, labels_path)
