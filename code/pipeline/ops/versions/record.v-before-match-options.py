"""Lineage records, ids, inheritance and storage for the scenario operators (context/OPERATORS-SPEC-v1.md).

Everything here is code. Models never write lineage: an operator returns an `OpResult` (X', delta, gates, annotations,
backend metadata) and `finish` turns it into one lineage step, sets the inherited fields and stores X' by bucket.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from bench.schema.pipeline import Lineage, Scenario, sha256_text
from pipeline.store import Store, write_yaml

SPEC = "OPERATORS-SPEC-v1"
CODES = {("permute", None): "pm", ("surface_edit", "reword"): "sr", ("surface_edit", "neighbor"): "sn",
         ("surface_edit", "transfer"): "st", ("structural_edit", "flip"): "xf", ("structural_edit", "target_f"): "xn",
         ("frame_edit", "drop_option"): "fd", ("judgment_edit", None): "je"}
BUCKETS = ("accepted", "hard", "rejected")
INHERIT = ("family", "split", "held_out", "content_domain", "refusal_sensitivity")


@dataclass
class OpResult:
    """What an operator hands back. `scenario` is X' (may be None if the writer failed)."""
    op: str
    mode: str | None
    args: dict
    scenario: Scenario | None
    delta: dict = field(default_factory=dict)          # fact_map, k_map, option_map, relation, via, choice
    gates: dict = field(default_factory=dict)          # name -> {"pass": bool, ...}
    annotations: dict = field(default_factory=dict)    # name -> {...}; never decide the bucket
    writer: dict | None = None                         # {"backend": "llm"|"human"|"code", "role", "model", "prompt", "tries"}
    solver: dict | None = None                         # {"backend": ..., "used_for": "annotation"|"verdict"} or None
    intended: dict | None = None
    log: list = field(default_factory=list)            # writer attempt log (errors per try)
    skipped: str | None = None                         # reason the operator did not apply (e.g. a no-op condition)

    @property
    def bucket(self) -> tuple[str, str]:
        if self.skipped:
            return "skipped", self.skipped
        if self.scenario is None:
            return "rejected", "writer failed"
        hard_gates = {"setting_adds"}                                 # spec: hard, not rejected
        for name, g in self.gates.items():
            if not g.get("pass", True) and name not in hard_gates:
                return "rejected", f"gate {name}"
        for name in hard_gates:
            if name in self.gates and not self.gates[name].get("pass", True):
                return "hard", f"gate {name}"
        return "accepted", "ok"


# ------------------------------------------------------------------ ids
def _stem(family: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "-", family)


_ID_LOCK = threading.Lock()
_RESERVED: set[str] = set()


def new_id(store: Store, family: str, op: str, mode: str | None) -> str:
    """DR-<family>-<code><n>@v1, unique over the scenario store, the held buckets and ids reserved in this process
    (operators run in threads; two jobs on the same family must not get the same id)."""
    code = CODES[(op, mode)]
    stem = f"DR-{_stem(family)}-{code}"
    pat = re.compile(re.escape(stem) + r"(\d+)@v1")
    with _ID_LOCK:
        used = {int(m.group(1)) for r in _RESERVED if (m := pat.fullmatch(r))}
        for d in (store.root / "scenarios" / family, store.root / "held" / "hard", store.root / "held" / "rejected"):
            if d.exists():
                for p in d.glob(f"{stem}*@v1.yaml"):
                    m = pat.fullmatch(p.stem)
                    if m:
                        used.add(int(m.group(1)))
        n = max(used, default=0) + 1
        sid = f"{stem}{n}@v1"
        _RESERVED.add(sid)
        return sid


# ------------------------------------------------------------------ lineage
def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.exists() else "missing"


def make_step(r: OpResult, parent: Scenario, bucket: str, why: str) -> dict:
    return {"op": r.op, "mode": r.mode, "args": r.args, "parent": parent.id, "writer": r.writer, "solver": r.solver,
            "gates": r.gates, "annotations": r.annotations, "intended": r.intended, "delta": r.delta,
            "bucket": bucket, "bucket_why": why, "spec": SPEC, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def finish(store: Store, X: Scenario, r: OpResult, *, save: bool = True) -> dict:
    """Append the lineage step to X' (in code), inherit family/split/domain tags from X, store by bucket.
    Returns a log row {op, mode, parent, id, bucket, why, path}."""
    bucket, why = r.bucket
    row = {"op": r.op, "mode": r.mode, "args": r.args, "parent": X.id, "bucket": bucket, "why": why,
           "writer_log": r.log[-3:] if r.log else None}
    if r.scenario is None or bucket == "skipped":
        return row
    S = r.scenario
    for k in INHERIT:
        setattr(S, k, getattr(X, k))
    steps = copy.deepcopy(X.lineage.steps) if X.lineage.steps else []
    steps.append(make_step(r, X, bucket, why))
    anchor = X.id if X.lineage.parent is None else (X.lineage.anchor or walk_anchor(store, X))
    S.lineage = Lineage(parent=X.id, operator=S.lineage.operator or r.op, detail=S.lineage.detail, anchor=anchor, steps=steps)
    S.tags = sorted(set(S.tags) | {"derived", f"op:{r.op}" + (f":{r.mode}" if r.mode else "")})
    S.status = "derived"
    row["id"] = S.id
    row["anchor"] = S.lineage.anchor
    if save:
        row["path"] = str(store_by_bucket(store, S, bucket))
    return row


def walk_anchor(store: Store, X: Scenario) -> str:
    seen, cur = set(), X
    while cur.lineage.parent and cur.id not in seen:
        seen.add(cur.id)
        if cur.lineage.anchor:
            return cur.lineage.anchor
        try:
            cur = store.scenario(cur.lineage.parent)
        except KeyError:
            return cur.lineage.parent
    return cur.id


def store_by_bucket(store: Store, S: Scenario, bucket: str) -> Path:
    Scenario.model_validate(S.dump())
    if bucket == "accepted":
        return store.save_scenario(S)
    p = store.root / "held" / bucket / f"{S.id}.yaml"
    write_yaml(p, S.dump())
    return p


def load_any(store: Store, sid: str) -> Scenario:
    """A scenario from the store or the held buckets (so recipes can chain from hard outputs when asked)."""
    try:
        return store.scenario(sid)
    except KeyError:
        for b in ("hard", "rejected"):
            p = store.root / "held" / b / f"{sid}.yaml"
            if p.exists():
                return Scenario.load(p)
        for legacy in ("transfer-hard", "transfer-rejected"):
            p = store.root / legacy / f"{sid}.yaml"
            if p.exists():
                return Scenario.load(p)
        raise


# ------------------------------------------------------------------ backend metadata (code)
def llm_writer(role: str, prompt_path: Path | None, tries: int | None = None, **extra) -> dict:
    from pipeline.perturb.common import model_of
    try:
        model = model_of(role)
    except Exception:                                          # noqa: BLE001
        model = None
    d = {"backend": "llm", "role": role, "model": model}
    if prompt_path is not None:
        d["prompt"] = f"{prompt_path.name}@{file_sha(prompt_path)}"
    if tries is not None:
        d["tries"] = tries
    d.update(extra)
    return d


def code_writer(note: str) -> dict:
    return {"backend": "code", "note": note}


def dump_delta(partial: dict) -> dict:
    """A perturb-style partial (pydantic GoldMaps etc.) -> plain dict delta."""
    keep = ("intent", "options_map", "fact_map", "consideration_map", "relation", "via", "choice", "gold_tier", "touched",
            "frame", "distance_features", "governs")
    out = {}
    for k in keep:
        if k in partial:
            v = partial[k]
            out[k] = v.model_dump(exclude_none=True) if hasattr(v, "model_dump") else v
    return json.loads(json.dumps(out, default=str))
