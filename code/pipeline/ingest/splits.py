"""W4a splits (design v2.4.1 §13.5): re-split the store under registry.SPLIT_RULE, and the leak assertion.

    python -m pipeline.ingest resplit        # rewrite scenario splits (versioned); report pairs that now cross splits
    python -m pipeline.ingest check-splits   # assert no eval trace or card shares a lineage root with a train pair

A derived scenario inherits its root's split. Pilot imports (eval-only) are left alone.
"""
from __future__ import annotations

from collections import Counter

from bench.schema.pipeline import EVAL_SPLITS, Scenario
from pipeline.store import Store

from . import registry as R


def root_of(s: Scenario, scen: dict[str, Scenario]) -> Scenario:
    seen = set()
    while s.lineage.parent and s.lineage.parent in scen and s.id not in seen:
        seen.add(s.id)
        s = scen[s.lineage.parent]
    return s


def resplit(store: Store | None = None, reg: dict | None = None, write: bool = True) -> dict:
    store = store or Store()
    reg = reg or R.load_registry()
    legacy, splits = reg.get("legacy_families", {}), reg["splits"]
    scen = {s.id: s for s in store.scenarios()}
    changed, unknown = [], []
    for s in scen.values():
        root = root_of(s, scen)
        if root.split == "eval-only" or "eval-only-import" in root.tags:
            continue
        fam = legacy.get(root.family, root.family)
        new = splits.get(fam)
        if new is None:
            unknown.append(s.id)
            continue
        if new != s.split:
            changed.append((s.id, s.split, new))
            if write:
                s.split = new
                s.provenance.step(id=f"resplit.{len(s.provenance.steps)}", operator="registry",
                                  notes=f"re-split {changed[-1][1]} -> {new} (document family {fam}); {R.SPLIT_RULE}")
                store.save_scenario(s)
    scen = {s.id: s for s in store.scenarios()}
    crossing, pairs_changed, invalid = [], [], []
    for p in store.pairs():
        if p.trace_scenario not in scen:
            continue
        if p.case_scenario and p.case_scenario in scen and scen[p.case_scenario].split != scen[p.trace_scenario].split:
            crossing.append(p.id)
        elif scen[p.trace_scenario].split != p.split:
            pairs_changed.append((p.id, p.split, scen[p.trace_scenario].split))
            if write:
                p.split = scen[p.trace_scenario].split
                p.provenance.step(id=f"resplit.{len(p.provenance.steps)}", operator="registry",
                                  notes=f"re-split {pairs_changed[-1][1]} -> {p.split} with its trace scenario")
                try:
                    store.save_pair(p)
                except ValueError as e:        # e.g. an eval-only arm whose trace moved to train: rebuild via pair
                    invalid.append((p.id, str(e).splitlines()[1].strip() if "\n" in str(e) else str(e)))
    return {"changed": changed, "pairs_changed": pairs_changed, "pairs_invalid_after_resplit": invalid, "unknown_family": unknown, "pairs_now_crossing_splits": crossing,
            "splits": Counter(s.split for s in scen.values())}


INACTIVE = {"superseded", "legacy-2f", "rejected"}       # pairs no consumer uses (kept on disk, never deleted)


def check_no_leak(store: Store | None = None) -> list[str]:
    """-> violations: an eval pair (test/eval-only) whose trace or card shares a lineage root with any train pair,
    or a pair whose card and trace come from different splits."""
    store = store or Store()
    scen = {s.id: s for s in store.scenarios()}
    root = lambda sid: root_of(scen[sid], scen).id if sid in scen else sid   # noqa: E731
    pairs = store.active_pairs()
    train_roots = {root(x) for p in pairs if p.split == "train" for x in (p.case_scenario, p.trace_scenario) if x}
    errs = []
    for p in pairs:
        ids = [x for x in (p.case_scenario, p.trace_scenario) if x]
        if p.split in EVAL_SPLITS:
            errs += [f"{p.id} ({p.arm}): {x} shares root {root(x)} with a train pair" for x in ids if root(x) in train_roots]
        sp = {scen[x].split for x in ids if x in scen}
        if len(sp) > 1:
            errs.append(f"{p.id}: card and trace in different splits {sorted(sp)}")
    return errs
