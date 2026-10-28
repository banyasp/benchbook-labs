"""Balance which option position wins across a batch of extracted scenarios (Peter, 2026-10-28).

    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.balance_options --batch corpus-batch2 [--dry-run]
    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.balance_options --scenarios DR-a@v1 DR-b@v1 ...

Extraction already shuffles options with a per-scenario seed (extract.relabel_options), so the winning position is
random but not balanced: batch 2's first 36 three-option scenarios had the winner at O3 only 7 times. This pass makes it
balanced by construction. Scenarios are grouped by (number of options, train vs eval); within a group, in a seeded
hash order, each scenario gets a target position cycling 1..n, so every position wins equally often (counts differ by
at most one). The winning option (`verdict.choice`) moves to its target; the others keep their relative order.

Relabelling rewrites EVERY option id in the scenario: dict keys (options, rejected, the cue tables), lists (favors,
rules_out), scalars (choice, then, tempting_wrong.option, real_option), field paths (`case.options.O2`) and prose
("favors O1"), in two phases so a swap never chains. The old file is kept in <family>/versions/. Only for scenarios not
yet perturbed or paired (checked): afterwards their ids are referenced by X' and pair records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict

import yaml

from bench.schema.pipeline import Scenario
from pipeline.store import DATA, Store, write_yaml

OPT = re.compile(r"\bO(\d+)\b")
EVAL = {"dev", "test"}


def permutation(n: int, winner: int, target: int) -> dict[str, str]:
    """old id -> new id: the winner goes to `target` (1-based), the others keep their relative order."""
    others = [k for k in range(1, n + 1) if k != winner]
    order = others[:target - 1] + [winner] + others[target - 1:]          # order[i] = old index at new position i+1
    return {f"O{old}": f"O{new}" for new, old in enumerate(order, 1)}


def _rename(obj, mp: dict[str, str]):
    """Two-phase rename of option ids everywhere in a nested structure."""
    tmp = {k: f"\x00OPT{v[1:]}\x00" for k, v in mp.items()}

    def phase(o, table, pat):
        if isinstance(o, dict):
            return {phase(k, table, pat) if isinstance(k, str) else k: phase(v, table, pat) for k, v in o.items()}
        if isinstance(o, list):
            return [phase(x, table, pat) for x in o]
        if isinstance(o, str):
            return pat.sub(lambda m: table.get(m.group(0), m.group(0)), o)
        return o

    once = phase(obj, tmp, OPT)
    back = {v: mp[k] for k, v in tmp.items()}
    return phase(once, back, re.compile("\x00OPT\\d+\x00"))


def relabel(d: dict, mp: dict[str, str]) -> dict:
    """Scenario dump -> relabelled dump with case.options in the new O1..On order."""
    out = _rename(d, mp)
    opts = out["case"]["options"]
    out["case"]["options"] = {k: opts[k] for k in sorted(opts, key=lambda k: int(k[1:]))}
    return out


def targets(scens: list[Scenario], seed: int = 0) -> dict[str, int]:
    groups = defaultdict(list)
    for s in scens:
        groups[(len(s.case.options), "eval" if s.split in EVAL else "train")].append(s)
    out = {}
    for (n, _), ss in groups.items():
        ss.sort(key=lambda s: hashlib.sha256(f"{seed}|{s.id}".encode()).hexdigest())
        start = int(hashlib.sha256(f"{seed}|{n}".encode()).hexdigest(), 16) % n
        for i, s in enumerate(ss):
            out[s.id] = (start + i) % n + 1
    return out


def check(before: Scenario, after: Scenario, mp: dict[str, str]):
    c0, c1 = before.case, after.case
    assert c1.verdict.choice == mp[c0.verdict.choice]
    assert [c1.options[mp[k]].do for k in c0.options] == [c0.options[k].do for k in c0.options]
    for x, y in zip(c0.considerations, c1.considerations):
        assert [mp[f] for f in x.favors] == list(y.favors)
    assert set(c1.options) == {f"O{i}" for i in range(1, len(c1.options) + 1)}


def balance(sids: list[str], store: Store, seed: int = 0, dry: bool = False) -> dict:
    scens = [store.scenario(s) for s in sids]
    used = {p.case_scenario for p in store.pairs()} | {p.trace_scenario for p in store.pairs()}
    derived = {s.lineage.parent for s in store.scenarios() if s.lineage and getattr(s.lineage, "parent", None)}
    blocked = [s.id for s in scens if s.id in used or s.id in derived]
    if blocked:
        raise SystemExit(f"{len(blocked)} scenario(s) already perturbed or paired (e.g. {blocked[:3]}): not relabelling")
    tg = targets(scens, seed)
    before = Counter((len(s.case.options), int(s.case.verdict.choice[1:])) for s in scens)
    moved = 0
    for s in scens:
        n, win = len(s.case.options), int(s.case.verdict.choice[1:])
        mp = permutation(n, win, tg[s.id])
        if all(k == v for k, v in mp.items()):
            continue
        new = Scenario.model_validate(relabel(s.dump(), mp))
        check(s, new, mp)
        moved += 1
        if dry:
            continue
        p = store.scenario_path(s)
        vdir = p.parent / "versions"
        vdir.mkdir(exist_ok=True)
        (vdir / f"{p.stem}.v1-before-option-balance.yaml").write_text(p.read_text())
        new.provenance.step(id="balance.options", operator="extract", ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            notes=f"options relabelled so the winning position is balanced across the batch: {json.dumps(mp)}",
                            params={"seed": seed, "target": tg[s.id]})
        store.save_scenario(new)
    after = Counter((len(s.case.options), tg[s.id]) for s in scens)
    fmt = lambda c: {f"{n} options": {f"O{p}": c[(n, p)] for p in range(1, n + 1)} for n in sorted({n for n, _ in c})}
    return {"scenarios": len(scens), "relabelled": moved, "dry_run": dry, "winner_before": fmt(before), "winner_after": fmt(after)}


def batch_scenarios(batch: str, store: Store) -> list[str]:
    eps = yaml.safe_load((DATA / "store" / "episodes" / f"{batch}.yaml").read_text())["episodes"]
    out = []
    for e in eps:
        sid = f"DR-{e['id']}@v1"
        try:
            store.scenario_path(sid)
            out.append(sid)
        except KeyError:
            pass
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--batch")
    g.add_argument("--scenarios", nargs="+")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    store = Store()
    sids = batch_scenarios(a.batch, store) if a.batch else a.scenarios
    print(json.dumps(balance(sids, store, a.seed, a.dry_run), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
