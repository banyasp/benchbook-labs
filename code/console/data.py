"""Read-only data layer for the research console (2026-11-11, Peter).

Everything here reads files under the repo and computes views on request. Nothing writes, except
`pipeline.ops.queue` (task files and the append-only labels file), which the app calls for the labelling pages.
"""
from __future__ import annotations

import difflib
import glob
import hashlib
import html
import json
import os
import re
import subprocess
import threading
import time
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
STORE = DATA / "store"
RUN_PARENTS = [ROOT / "results" / "transfer", ROOT / "results" / "allpairs"]
LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
INDEX_TTL = 120          # seconds before the scenario/sample indexes are rebuilt on the next request
GIT_PATHS = ["code/harness", "code/eval", "code/scorers", "code/pipeline", "code/bench", "code/datagen/prompts",
             "data/registry/equities", "config"]


def rel(p: Path | str) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def load_yaml(p: Path) -> dict:
    return yaml.load(p.read_text(), Loader=LOADER) or {}


def sha16(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def mtime(p: Path) -> str | None:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(p.stat().st_mtime)) if p.exists() else None


class _Cached:
    """A value rebuilt at most every `ttl` seconds (or on demand)."""

    def __init__(self, fn, ttl=INDEX_TTL):
        self.fn, self.ttl, self.val, self.t, self.lock = fn, ttl, None, 0.0, threading.Lock()

    def get(self, force=False):
        with self.lock:
            if force or self.val is None or time.time() - self.t > self.ttl:
                self.val, self.t = self.fn(), time.time()
            return self.val

    @property
    def built(self):
        return time.strftime("%H:%M:%S UTC", time.gmtime(self.t)) if self.t else None


# ====================================================================== scenarios
def _scenario_files() -> list[tuple[Path, str]]:
    out = [(Path(p), "store") for p in glob.glob(str(STORE / "scenarios" / "*" / "*.yaml"))]
    for b in ("hard", "rejected"):
        out += [(Path(p), f"held/{b}") for p in glob.glob(str(STORE / "held" / b / "*.yaml"))]
    for legacy in ("transfer-hard", "transfer-rejected"):
        out += [(Path(p), legacy) for p in glob.glob(str(STORE / legacy / "*.yaml"))]
    return out


def _bucket(where: str, d: dict) -> str:
    steps = (d.get("lineage") or {}).get("steps") or []
    if steps and steps[-1].get("bucket"):
        return steps[-1]["bucket"]
    return {"store": "accepted", "held/hard": "hard", "held/rejected": "rejected", "transfer-hard": "hard",
            "transfer-rejected": "rejected"}[where]


def _index_row(p: Path, where: str) -> dict | None:
    try:
        d = load_yaml(p)
    except Exception as e:                                            # noqa: BLE001
        return {"id": p.stem, "path": rel(p), "where": where, "error": str(e)[:200]}
    c = d.get("case") or {}
    lin = d.get("lineage") or {}
    steps = lin.get("steps") or []
    last = steps[-1] if steps else {}
    opts = list((c.get("options") or {}).keys())
    gold = (c.get("verdict") or {}).get("choice")
    return {"id": d.get("id", p.stem), "path": rel(p), "where": where, "family": d.get("family"),
            "domain": d.get("domain"), "content_domain": d.get("content_domain"), "split": d.get("split"),
            "held_out": bool(d.get("held_out")), "status": d.get("status"), "tier": d.get("verdict_tier"),
            "title": c.get("title"), "agent_role": c.get("agent_role"), "n_options": len(opts), "gold": gold,
            "gold_pos": (opts.index(gold) + 1) if gold in opts else None, "n_facts": len(c.get("facts") or []),
            "parent": lin.get("parent"), "anchor": lin.get("anchor") or (None if lin.get("parent") else d.get("id")),
            "legacy_op": lin.get("operator"), "op": last.get("op"), "mode": last.get("mode"),
            "bucket": _bucket(where, d), "tags": d.get("tags") or [],
            "has_trace": (STORE / "traces" / d.get("id", p.stem) / "trace.json").exists()}


def _build_index() -> dict:
    rows = [r for p, w in _scenario_files() if (r := _index_row(p, w))]
    by_id = {r["id"]: r for r in rows}
    children = defaultdict(list)
    for r in rows:
        if r.get("parent"):
            children[r["parent"]].append(r["id"])
    return {"rows": rows, "by_id": by_id, "children": dict(children)}


SCEN = _Cached(_build_index)


def scenario_rows(f: dict) -> list[dict]:
    rows = SCEN.get()["rows"]
    q = (f.get("q") or "").lower().strip()
    out = []
    for r in rows:
        if q and q not in (r["id"] + " " + (r.get("title") or "")).lower():
            continue
        ok = True
        for k in ("family", "domain", "content_domain", "split", "status", "bucket", "op", "mode", "where", "tier",
                  "agent_role"):
            v = f.get(k)
            if v and str(r.get(k)) != v:
                ok = False
                break
        if not ok:
            continue
        if f.get("held_out") in ("true", "false") and r["held_out"] != (f["held_out"] == "true"):
            continue
        if f.get("derived") == "anchor" and r.get("parent"):
            continue
        if f.get("derived") == "derived" and not r.get("parent"):
            continue
        if f.get("trace") == "yes" and not r["has_trace"]:
            continue
        if f.get("tag") and f["tag"] not in r["tags"]:
            continue
        out.append(r)
    return out


def facet_values() -> dict:
    rows = SCEN.get()["rows"]
    out = {}
    for k in ("family", "domain", "content_domain", "split", "status", "bucket", "op", "mode", "where", "tier",
              "agent_role"):
        out[k] = sorted({str(r.get(k)) for r in rows if r.get(k) is not None})
    out["tag"] = sorted({t for r in rows for t in r["tags"]})
    return out


def scenario_path(sid: str) -> Path | None:
    r = SCEN.get()["by_id"].get(sid)
    return ROOT / r["path"] if r else None


def scenario(sid: str) -> dict | None:
    p = scenario_path(sid)
    if p is None or not p.exists():
        return None
    return load_yaml(p)


def lineage_chain(sid: str) -> list[dict]:
    """Root first: [{id, row}] following lineage.parent."""
    by = SCEN.get()["by_id"]
    chain, cur, seen = [], sid, set()
    while cur and cur not in seen:
        seen.add(cur)
        chain.append({"id": cur, "row": by.get(cur)})
        cur = (by.get(cur) or {}).get("parent")
    return list(reversed(chain))


def descendants(sid: str) -> list[dict]:
    idx = SCEN.get()
    out, stack = [], [(c, 1) for c in idx["children"].get(sid, [])]
    while stack:
        c, depth = stack.pop(0)
        out.append({"id": c, "depth": depth, "row": idx["by_id"].get(c)})
        stack[:0] = [(g, depth + 1) for g in idx["children"].get(c, [])]
    return out


# ---------------------------------------------------------------- source excerpts
def _span_doc(span: str) -> tuple[str, str] | None:
    m = re.match(r"src:([0-9a-f]{12})#(.+)", span or "")
    return (m.group(1), span) if m else None


@lru_cache(maxsize=64)
def _doc_lines(sha12: str) -> tuple:
    p = DATA / "docs" / f"{sha12}.jsonl"
    if not p.exists():
        return ()
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return tuple(out)


def fact_sources(d: dict, window: int = 1) -> dict[str, list[dict]]:
    """fact id -> [{span, text, context:[...]}] from data/docs (the source excerpt), when available."""
    out = {}
    for fid, spans in (d.get("fact_spans") or {}).items():
        items = []
        for sp in spans or []:
            sd = _span_doc(sp)
            if not sd:
                items.append({"span": sp, "text": None, "context": []})
                continue
            lines = _doc_lines(sd[0])
            pos = next((i for i, l in enumerate(lines) if l.get("span") == sp), None)
            if pos is None:
                items.append({"span": sp, "text": None, "context": []})
                continue
            ctx = [{"span": l.get("span"), "text": l.get("text"), "hit": i == pos}
                   for i, l in enumerate(lines[max(0, pos - window): pos + window + 1], start=max(0, pos - window))]
            items.append({"span": sp, "text": lines[pos].get("text"), "context": ctx})
        out[fid] = items
    return out


# ---------------------------------------------------------------- diffs
def word_diff(a: str | None, b: str | None) -> str:
    """HTML: words removed in <del>, added in <ins>."""
    a, b = a or "", b or ""
    if a == b:
        return html.escape(a)
    aw, bw = re.findall(r"\S+|\s+", a), re.findall(r"\S+|\s+", b)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, aw, bw, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(html.escape("".join(aw[i1:i2])))
        if op in ("delete", "replace"):
            out.append(f"<del>{html.escape(''.join(aw[i1:i2]))}</del>")
        if op in ("insert", "replace"):
            out.append(f"<ins>{html.escape(''.join(bw[j1:j2]))}</ins>")
    return "".join(out)


def _flat(o, prefix="") -> dict[str, str]:
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(_flat(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(o, list):
        if all(isinstance(x, dict) and "id" in x for x in o) and o:
            for x in o:
                out.update(_flat({k: v for k, v in x.items() if k != "id"}, f"{prefix}[{x['id']}]"))
        else:
            out[prefix] = json.dumps(o, ensure_ascii=False) if any(isinstance(x, (dict, list)) for x in o) else \
                ", ".join(str(x) for x in o)
    else:
        out[prefix] = "" if o is None else str(o)
    return out


def case_diff(parent_case: dict, child_case: dict) -> list[dict]:
    """Field-level diff of two cases (ids matched): [{path, kind: changed|added|removed, html}]."""
    a, b = _flat(parent_case or {}), _flat(child_case or {})
    out = []
    for k in sorted(set(a) | set(b), key=lambda k: (k.split(".")[0], k)):
        if k.startswith("library"):
            continue
        if k in a and k in b:
            if a[k] != b[k]:
                out.append({"path": k, "kind": "changed", "html": word_diff(a[k], b[k])})
        elif k in b:
            out.append({"path": k, "kind": "added", "html": f"<ins>{html.escape(b[k])}</ins>"})
        else:
            out.append({"path": k, "kind": "removed", "html": f"<del>{html.escape(a[k])}</del>"})
    return out


# ====================================================================== traces and answer keys
def trace(sid: str) -> dict | None:
    d = STORE / "traces" / sid
    tj = d / "trace.json"
    if not tj.exists():
        return None
    t = json.loads(tj.read_text())
    rec = load_yaml(d / "trace.yaml") if (d / "trace.yaml").exists() else {}
    spans = defaultdict(list)
    for e in (rec.get("span_map") or {}).get("entries") or []:
        spans[e["message"]].append({"start": e["start"], "end": e["end"], "label": e["fact"].split("/")[-1],
                                    "kind": "fact", "realization": e.get("realization")})
    for e in (rec.get("span_map") or {}).get("options") or []:
        spans[e["message"]].append({"start": e["start"], "end": e["end"], "label": e["option"].split("/")[-1],
                                    "kind": "option", "realization": e.get("channel")})
    msgs = []
    for i, m in enumerate(t.get("messages") or []):
        content = m.get("content") or ""
        msgs.append({"i": i, "role": m.get("role"), "name": m.get("name"), "time": m.get("time"),
                     "tool_calls": m.get("tool_calls"), "html": highlight(content, spans.get(i, []))})
    return {"sid": sid, "messages": msgs, "facts": t.get("facts"), "options": t.get("options"),
            "recommendation": t.get("recommendation"), "record": {k: v for k, v in rec.items() if k != "span_map"},
            "mtime": mtime(tj), "sha": sha16(tj), "path": rel(tj)}


def highlight(text: str, spans: list[dict]) -> str:
    """Escape text and wrap fact/option spans (non-overlapping, earliest first) in <mark> with a label."""
    spans = sorted([s for s in spans if 0 <= s["start"] < s["end"] <= len(text)], key=lambda s: s["start"])
    out, pos = [], 0
    for s in spans:
        if s["start"] < pos:
            continue
        out.append(html.escape(text[pos:s["start"]]))
        out.append(f'<mark class="{s["kind"]}" title="{html.escape(s["label"])} ({html.escape(str(s["realization"]))})">'
                   f'<sup>{html.escape(s["label"])}</sup>{html.escape(text[s["start"]:s["end"]])}</mark>')
        pos = s["end"]
    out.append(html.escape(text[pos:]))
    return "".join(out)


def answer_key(sid: str, equities: str = "pilot2") -> dict:
    """The no-case answer key the eval scores against (code only: pipeline.project gold_for)."""
    try:
        from eval.allpairs import none_pair
        from pipeline.project.project import gold_for
        from pipeline.store import Store
        st = Store()
        g, key = gold_for(none_pair(st, sid, equities), st)
        return {"key": key.model_dump(mode="json", by_alias=True, exclude_none=True), "warnings": g.warnings}
    except Exception as e:                                            # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:400]}


# ====================================================================== runs
def _runs_yaml() -> dict:
    p = ROOT / "measurements" / "runs.yaml"
    d = load_yaml(p) if p.exists() else {}
    return {"defaults": d.get("defaults") or {}, "runs": {r["run"].rstrip("/"): r for r in d.get("runs") or []}}


def run_dirs() -> list[Path]:
    out = []
    for parent in RUN_PARENTS:
        for d in sorted(parent.iterdir()) if parent.exists() else []:
            if d.is_dir() and (d / "config.json").exists():
                out.append(d)
    return out


def _count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with p.open("rb") as f:
        return sum(1 for _ in f)


def _scheduled(d: Path, cfg: dict) -> int | None:
    mans = sorted(d.glob("manifest.run.*.json"))
    if mans:
        try:
            return json.loads(mans[-1].read_text()).get("scheduled")
        except Exception:                                             # noqa: BLE001
            pass
    if cfg.get("cells"):
        return (len(cfg["cells"]) + len(cfg.get("x1") or [])) * int(cfg.get("k") or 1)
    return None


@lru_cache(maxsize=1)
def _live_procs_cached(bucket: int) -> str:
    try:
        return subprocess.run(["pgrep", "-af", "allpairs run"], capture_output=True, text=True, timeout=5).stdout
    except Exception:                                                 # noqa: BLE001
        return ""


def live_runs() -> set[str]:
    txt = _live_procs_cached(int(time.time() // 10))
    return {rel(m) for m in re.findall(r"--run\s+(\S+)", txt)} | {m.rstrip("/") for m in re.findall(r"--run\s+(\S+)", txt)}


def runs() -> list[dict]:
    reg = _runs_yaml()
    live = live_runs()
    out = []
    for d in run_dirs():
        r = rel(d)
        cfg = json.loads((d / "config.json").read_text())
        n = _count_lines(d / "samples.jsonl")
        sched = _scheduled(d, cfg)
        entry = reg["runs"].get(r, {})
        out.append({"run": r, "name": d.name, "group": d.parent.name, "created": cfg.get("created"),
                    "model": cfg.get("model"), "mode": cfg.get("mode"), "scaffold": cfg.get("scaffold") or "schema",
                    "modes_version": cfg.get("modes_version") or "v1", "k": cfg.get("k"),
                    "max_tokens": cfg.get("max_tokens"), "n": n, "scheduled": sched,
                    "running": r in live, "registered": bool(entry), "status": entry.get("status"),
                    "measurement": entry.get("measurement"), "entry": entry,
                    "n_cells": len(cfg.get("cells") or []) if cfg.get("cells") else None,
                    "n_x1": len(cfg.get("x1") or [])})
    out.sort(key=lambda r: r["created"] or "", reverse=True)
    return out


def run_config(run: str) -> dict:
    return json.loads((ROOT / run / "config.json").read_text())


def samples(run: str) -> list[dict]:
    p = ROOT / run / "samples.jsonl"
    out = []
    if p.exists():
        for line in p.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


ARMS = ["control", "self", "transfer", "flip", "decoy"]


def run_results(run: str, max_idx: int | None = None) -> dict:
    """Per arm: n, X1s, accuracy (mean over X1 of per-X1 mean, as the reports), raw accuracy, off-menu, no verdict,
    and the copy rate from the tensor (when the run is registered and the tensor has it)."""
    S = [s for s in samples(run) if max_idx is None or s.get("idx", 0) <= max_idx]
    by = defaultdict(lambda: defaultdict(list))
    off, nov, n = Counter(), Counter(), Counter()
    for s in S:
        arm = s.get("phase")
        by[arm][s.get("x1")].append(float(s.get("correct") or 0.0))
        n[arm] += 1
        off[arm] += bool(s.get("off_menu"))
        nov[arm] += s.get("parsed_choice") is None
    copied = _tensor_copied(run, max_idx)
    rows = []
    for arm in sorted(by, key=lambda a: (ARMS.index(a) if a in ARMS else 99, a)):
        x1m = [sum(v) / len(v) for v in by[arm].values()]
        allv = [x for v in by[arm].values() for x in v]
        rows.append({"arm": arm, "n": n[arm], "x1s": len(by[arm]), "acc": sum(x1m) / len(x1m) if x1m else None,
                     "acc_raw": sum(allv) / len(allv) if allv else None, "off_menu": off[arm] / n[arm],
                     "no_verdict": nov[arm] / n[arm], "copied": copied.get(arm)})
    idxs = sorted({s.get("idx") for s in S})
    return {"rows": rows, "n": len(S), "idx": idxs}


@lru_cache(maxsize=4)
def _tensor(mtime_key: float):
    import pandas as pd
    return pd.read_parquet(ROOT / "results" / "tensor" / "replies.parquet")


def _tensor_copied(run: str, max_idx: int | None) -> dict:
    p = ROOT / "results" / "tensor" / "replies.parquet"
    if not p.exists():
        return {}
    try:
        t = _tensor(p.stat().st_mtime)
        t = t[t["run"].astype(str).str.rstrip("/") == run]
        if max_idx is not None:
            t = t[t["idx"] <= max_idx]
        if t.empty or "copied" not in t:
            return {}
        out = {}
        for arm, g in t.groupby("arm"):
            g = g.dropna(subset=["copied"])
            if len(g):
                out[arm] = float(g.groupby("x1")["copied"].mean().mean())
        return out
    except Exception:                                                 # noqa: BLE001
        return {}


def run_data(run: str) -> dict:
    """What data the run used: X1s, cells per arm, the X2s' operators, and the dataset manifest check."""
    cfg = run_config(run)
    cells = cfg.get("cells") or []
    by_arm = Counter(c.get("arm") for c in cells)
    idx = SCEN.get()["by_id"]
    x2_ops = Counter()
    for c in cells:
        r = idx.get(c.get("x2"))
        if r and r.get("parent"):
            x2_ops[f"{c.get('arm')}: {r.get('op') or r.get('legacy_op')}" + (f"/{r['mode']}" if r.get("mode") else "")] += 1
        elif r:
            x2_ops[f"{c.get('arm')}: anchor (no operator)"] += 1
        else:
            x2_ops[f"{c.get('arm')}: not in store"] += 1
    cells_hash = hashlib.sha256(json.dumps(cells, sort_keys=True).encode()).hexdigest()[:10] if cells else None
    return {"x1": cfg.get("x1") or [], "x2": cfg.get("x2") or [], "cells": cells, "by_arm": dict(by_arm),
            "x2_ops": dict(sorted(x2_ops.items())), "cells_hash": cells_hash, "manifest": manifest_check(cells_hash)}


def _manifests() -> list[Path]:
    return sorted((ROOT / "measurements" / "datasets").glob("*.manifest.json"))


def manifest_check(cells_hash: str | None) -> dict | None:
    """Find the dataset manifest whose cells file matches, and compare every recorded hash with the file now."""
    for mp in _manifests():
        m = json.loads(mp.read_text())
        cf = ROOT / m.get("cells_file", "")
        if not cf.exists():
            continue
        h = hashlib.sha256(json.dumps(json.loads(cf.read_text()), sort_keys=True).encode()).hexdigest()[:10]
        if cells_hash and h != cells_hash:
            continue
        changed, n = [], 0
        for x in m.get("x1") or []:
            checks = [("scenario", x.get("scenario_file"), x.get("scenario_sha"))]
            if x.get("trace_dir"):
                checks.append(("trace", str(Path(x["trace_dir"]) / "trace.json"), x.get("trace_sha")))
            checks += [("x2", c.get("x2_file"), c.get("x2_sha")) for c in x.get("cells") or [] if c.get("x2_file")]
            for kind, f, h0 in checks:
                if not f or not h0:
                    continue
                n += 1
                p = ROOT / f
                h1 = sha16(p)
                if h1 != h0:
                    backup = DATA / "store" / "versions" / "pre-ops-migration-20261111" / f
                    changed.append({"kind": kind, "file": f, "now": h1, "recorded": h0, "mtime": mtime(p),
                                    "migration_only": backup.exists() and sha16(backup) == h0})
        return {"manifest": rel(mp), "doc": rel(mp).replace(".manifest.json", ".md"), "generated": m.get("generated"),
                "files_checked": n, "changed": changed}
    return None


def prompts_used(cfg: dict) -> list[dict]:
    """The harness prompt files a run's config implies (eval.allpairs SCAFFOLDS; harness.episode)."""
    hp = "code/harness/prompts"
    fs = cfg.get("format_spec") or "v1"
    mv = cfg.get("modes_version") or "v1"
    out = [{"what": "format spec (with a case)", "path": f"{hp}/format.{fs}.md"},
           {"what": "format spec (no case)", "path": f"{hp}/format.{fs}-noref.md"},
           {"what": f"mode line (key {cfg.get('mode')})", "path": f"{hp}/modes.{mv}.yaml", "key": cfg.get("mode")}]
    if cfg.get("ar_prompt", True):
        out.append({"what": "analogical method prompt (with a case)", "path": f"{hp}/analogical.v1.md"})
    eq = cfg.get("equities")
    if eq:
        out.append({"what": "equities", "path": f"data/registry/equities/{eq}.yaml"})
    for o in out:
        p = ROOT / o["path"]
        o["exists"] = p.exists()
        o["mtime"] = mtime(p)
        if o.get("key") and p.exists():
            o["text"] = (load_yaml(p) or {}).get(o["key"])
    if cfg.get("api_start_instruction"):
        out.append({"what": "API start instruction (code/eval/allpairs.py)", "path": None,
                    "text": cfg["api_start_instruction"].strip()})
    return out


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=20, cwd=ROOT).stdout.strip()
    except Exception:                                                 # noqa: BLE001
        return ""


@lru_cache(maxsize=256)
def commit_at(ts: str | None) -> str | None:
    if not ts:
        return None
    return _git("rev-list", "-1", f"--before={ts}Z", "HEAD") or None


def run_commit(cfg: dict) -> tuple[str | None, str]:
    g = cfg.get("git") or {}
    if g.get("commit"):
        return g["commit"], "recorded at launch"
    return commit_at(cfg.get("created")), "inferred: last commit before the run's creation time"


def git_log(a: str | None, b: str | None, paths=GIT_PATHS) -> list[dict]:
    if not a or not b or a == b:
        return []
    txt = _git("log", "--format=%h%x09%ad%x09%s", "--date=format:%Y-%m-%d %H:%M", f"{a}..{b}", "--", *paths)
    out = []
    for line in txt.splitlines():
        h, d, s = (line.split("\t", 2) + ["", ""])[:3]
        files = _git("show", "--name-only", "--format=", h, "--", *paths).splitlines()
        out.append({"hash": h, "date": d, "subject": s, "files": files[:30]})
    return out


def previous_run(run: str) -> str | None:
    rs = [r for r in runs() if r["group"] == Path(run).parent.name]
    rs.sort(key=lambda r: r["created"] or "")
    names = [r["run"] for r in rs]
    if run not in names:
        return None
    i = names.index(run)
    return names[i - 1] if i > 0 else None


SKIP_CFG = {"x1", "x2", "cells", "created", "git"}


def run_changes(run: str, prev: str | None) -> dict:
    """What changed between `prev` and `run`: config diff, git log of pipeline code and prompts, and files of the
    run's data (X1 scenarios, traces, X2s) modified between the two runs or after this run."""
    cfg = run_config(run)
    out = {"prev": prev, "config_diff": [], "commits": [], "data_between": [], "data_after": []}
    c1, how1 = run_commit(cfg)
    out["commit"], out["commit_how"] = c1, how1
    out["dirty"] = (cfg.get("git") or {}).get("dirty_code")
    if not prev:
        return out
    pcfg = run_config(prev)
    for k in sorted((set(cfg) | set(pcfg)) - SKIP_CFG):
        if cfg.get(k) != pcfg.get(k):
            out["config_diff"].append({"key": k, "prev": pcfg.get(k), "this": cfg.get(k)})
    if (cfg.get("cells") or []) != (pcfg.get("cells") or []):
        a = {(c["x1"], c["x2"], c["arm"]) for c in pcfg.get("cells") or []}
        b = {(c["x1"], c["x2"], c["arm"]) for c in cfg.get("cells") or []}
        out["config_diff"].append({"key": "cells", "prev": f"{len(a)} cells", "this": f"{len(b)} cells "
                                   f"({len(b - a)} added, {len(a - b)} removed)"})
    if set(cfg.get("x1") or []) != set(pcfg.get("x1") or []):
        out["config_diff"].append({"key": "x1", "prev": f"{len(pcfg.get('x1') or [])} X1s",
                                   "this": f"{len(cfg.get('x1') or [])} X1s"})
    c0, _ = run_commit(pcfg)
    out["prev_commit"] = c0
    out["commits"] = git_log(c0, c1)
    t0, t1 = pcfg.get("created") or "", cfg.get("created") or ""
    files = set()
    for x in cfg.get("x1") or []:
        files.add(("X1 trace", STORE / "traces" / x / "trace.json"))
        p = scenario_path(x)
        if p:
            files.add(("X1 scenario", p))
    for c in cfg.get("cells") or []:
        p = scenario_path(c.get("x2") or "")
        if p:
            files.add(("X2 scenario", p))
    for kind, p in sorted(files, key=lambda kv: str(kv[1])):
        m = mtime(p)
        if not m:
            continue
        mm = m.rstrip("Z")
        if t0 < mm <= t1:
            out["data_between"].append({"kind": kind, "file": rel(p), "mtime": m})
        elif mm > t1:
            out["data_after"].append({"kind": kind, "file": rel(p), "mtime": m})
    return out


def sample(run: str, sid: str) -> dict | None:
    for s in samples(run):
        if s.get("sample_id") == sid:
            d = ROOT / run
            raw = d / s["raw_path"] if s.get("raw_path") else None
            det = d / s["details_path"] if s.get("details_path") else None
            return {"row": s, "raw": raw.read_text() if raw and raw.exists() else None,
                    "details": json.loads(det.read_text()) if det and det.exists() else None}
    return None


def rebuild_prompt(run: str, s: dict) -> dict:
    """Rebuild the exact model input for a sample with the CURRENT code and files (code only, no model call)."""
    try:
        from eval import allpairs as AP
        from harness.pairs import build_pair_episode
        import harness
        from pipeline.store import Store
        cfg = run_config(run)
        st = Store()
        sc = AP.SCAFFOLDS[cfg.get("scaffold") or "schema"]
        base = AP.none_pair(st, s["x1"], cfg.get("equities") or "pilot2")
        pair = base if not s.get("x2") else AP.case_pair(base, s["x2"])
        settings = harness.HarnessSettings(mode=cfg.get("mode") or "C", analogical_prompt=sc["analogical"],
                                           max_tokens=cfg.get("max_tokens") or 8000, seed=s.get("seed") or 0,
                                           model=AP.MODELS[cfg.get("model") or "base"], format_spec=sc["format_spec"],
                                           modes_version=cfg.get("modes_version") or sc["modes_version"])
        ep = build_pair_episode(pair, st, settings, ar_prompt=sc["analogical"])
        msgs = [dict(m) for m in ep.messages]
        if cfg.get("api_start_instruction"):
            msgs[-1]["content"] = msgs[-1]["content"].rstrip() + cfg["api_start_instruction"]
        return {"messages": msgs, "prefill": None if cfg.get("api_role") else ep.prefill,
                "api": bool(cfg.get("api_role"))}
    except Exception as e:                                            # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:500]}


# ---------------------------------------------------------------- samples by scenario
def _build_usage() -> dict:
    use = defaultdict(list)
    for d in run_dirs():
        r = rel(d)
        for s in samples(r):
            row = {"run": r, "sample_id": s.get("sample_id"), "phase": s.get("phase"), "x1": s.get("x1"),
                   "x2": s.get("x2"), "idx": s.get("idx"), "correct": s.get("correct"),
                   "choice": s.get("translated_choice"), "gold": s.get("gold_choice"), "off_menu": s.get("off_menu")}
            use[s.get("x1")].append({**row, "as": "X1"})
            if s.get("x2") and s.get("x2") != s.get("x1"):
                use[s.get("x2")].append({**row, "as": "X2"})
    return dict(use)


USAGE = _Cached(_build_usage, ttl=300)


def usage(sid: str) -> dict:
    rows = USAGE.get().get(sid, [])
    agg = defaultdict(lambda: {"n": 0, "correct": 0.0, "phases": Counter()})
    for r in rows:
        a = agg[(r["run"], r["as"])]
        a["n"] += 1
        a["correct"] += float(r["correct"] or 0)
        a["phases"][r["phase"]] += 1
    summary = [{"run": k[0], "as": k[1], "n": v["n"], "acc": v["correct"] / v["n"], "phases": dict(v["phases"])}
               for k, v in sorted(agg.items())]
    return {"summary": summary, "rows": rows}


# ====================================================================== documents
DOC_DIRS = ("measurements", "docs", "context", "code", "results", "examples-v21", "ideas")
TEXT_EXT = {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".jsonl"}


def safe_path(p: str) -> Path | None:
    """A repo file the console may show (text, inside the allowed folders, never secrets)."""
    try:
        q = (ROOT / p).resolve()
        q.relative_to(ROOT)
    except Exception:                                                 # noqa: BLE001
        return None
    parts = q.relative_to(ROOT).parts
    if not parts or parts[0] not in DOC_DIRS + ("data", "scripts", "measurements"):
        return None
    if any(s in q.name.lower() for s in (".env", "secret", "key", "credential", "token")) and q.suffix != ".md":
        return None
    if q.is_file() and q.suffix not in TEXT_EXT:
        return None
    return q


def _indent_lists(md: str) -> str:
    """The repo's markdown nests lists with 2 spaces; Python-Markdown wants 4. Double leading indentation outside
    fenced code blocks."""
    out, fence = [], False
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append(line.lstrip() if not fence or line.startswith("```") else line)
            continue
        if not fence:
            n = len(line) - len(line.lstrip(" "))
            if n:
                line = " " * (2 * n) + line.lstrip(" ")
        out.append(line)
    return "\n".join(out)


def render_md(text: str, base: Path | None = None) -> str:
    import markdown
    h = markdown.markdown(_indent_lists(text), extensions=["tables", "fenced_code", "sane_lists", "toc"])
    if base is not None:
        def fix(m):
            href = m.group(1)
            if re.match(r"^(https?:|mailto:|#|/)", href):
                return m.group(0)
            path, _, frag = href.partition("#")
            target = (base.parent / path).resolve()
            try:
                r = target.relative_to(ROOT)
            except ValueError:
                return m.group(0)
            route = "/doc" if target.suffix == ".md" else "/file"
            return f'href="{route}?path={r}' + (f"#{frag}" if frag else "") + '"'
        h = re.sub(r'href="([^"]+)"', fix, h)
    return h.replace("<table>", '<table class="grid">')


def doc(path: str) -> dict | None:
    p = safe_path(path)
    if p is None or not p.is_file():
        return None
    text = p.read_text(errors="replace")
    if p.suffix == ".md":
        return {"path": rel(p), "html": render_md(text, p), "mtime": mtime(p), "kind": "md"}
    return {"path": rel(p), "text": text[:400_000], "mtime": mtime(p), "kind": p.suffix.lstrip(".")}


def measurements() -> dict:
    mdir = ROOT / "measurements"
    rows = []
    readme = (mdir / "README.md").read_text() if (mdir / "README.md").exists() else ""
    for line in readme.splitlines():
        m = re.match(r"\|\s*\[(M\d+)\]\(([^)]+)\)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|", line)
        if m:
            rows.append({"id": m.group(1), "path": f"measurements/{m.group(2)}", "date": m.group(3).strip(),
                         "title": m.group(4).strip(), "status": m.group(5).strip()})
    views = [{"path": rel(p), "name": p.name, "mtime": mtime(p)} for p in sorted((mdir / "views").glob("*.md"))]
    data = [{"path": rel(p), "name": p.name} for p in sorted((mdir / "datasets").glob("*.md"))]
    return {"rows": rows, "views": views, "datasets": data}


# ====================================================================== prompts
PROMPT_GLOBS = ["code/harness/prompts", "code/pipeline/*/prompts", "code/datagen/prompts", "code/scorers/prompts",
                "code/library/convert/prompts", "code/datagen/prompts"]


@lru_cache(maxsize=1)
def _py_sources(bucket: int) -> list[tuple[str, str]]:
    out = []
    for p in (ROOT / "code").rglob("*.py"):
        if "versions" in p.parts or "tests" in p.parts:
            continue
        try:
            out.append((rel(p), p.read_text(errors="replace")))
        except Exception:                                             # noqa: BLE001
            pass
    return out


def prompts() -> list[dict]:
    dirs = []
    for g in PROMPT_GLOBS:
        dirs += [Path(p) for p in glob.glob(str(ROOT / g))]
    out, seen = [], set()
    srcs = _py_sources(int(time.time() // 300))
    for d in sorted(set(dirs)):
        if d in seen:
            continue
        seen.add(d)
        files = sorted([p for p in d.iterdir() if p.is_file()])
        vers = sorted((d / "versions").glob("*")) if (d / "versions").exists() else []
        items = []
        for p in files:
            stem = p.name
            users = sorted({f for f, txt in srcs if stem in txt})
            olds = [rel(v) for v in vers if v.name.startswith(p.stem.split(".v")[0] + ".") or v.name.startswith(p.stem)]
            items.append({"path": rel(p), "name": p.name, "mtime": mtime(p), "users": users, "versions": olds})
        out.append({"dir": rel(d), "files": items, "versions": [rel(v) for v in vers]})
    return out


def prompt_runs(path: str) -> list[str]:
    """Run directories whose config implies this harness prompt file."""
    out = []
    for r in runs():
        try:
            used = {u["path"] for u in prompts_used(run_config(r["run"])) if u.get("path")}
        except Exception:                                             # noqa: BLE001
            continue
        if path in used:
            out.append(r["run"])
    return out


def file_diff(a: str, b: str) -> str | None:
    pa, pb = safe_path(a), safe_path(b)
    if not pa or not pb or not pa.is_file() or not pb.is_file():
        return None
    al, bl = pa.read_text(errors="replace").splitlines(), pb.read_text(errors="replace").splitlines()
    rows = []
    for line in difflib.unified_diff(al, bl, a, b, lineterm="", n=3):
        cls = "add" if line.startswith("+") and not line.startswith("+++") else \
            "del" if line.startswith("-") and not line.startswith("---") else "hunk" if line.startswith("@@") else ""
        rows.append(f'<span class="{cls}">{html.escape(line)}</span>')
    return "\n".join(rows) or "(identical)"


# ====================================================================== operators
GATE_NAMES = ["structure", "leak", "technique", "setting_adds", "condition_realized"]
ANNOT_NAMES = ["verdict_shift", "k_support", "fact_edit"]


def operators() -> dict:
    import inspect
    from pipeline.ops import record
    from pipeline.ops.recipes import OPS
    built = defaultdict(list)
    for (op, mode), code in record.CODES.items():
        built[op].append({"mode": mode, "code": code})
    out = []
    for name, fn in OPS.items():
        mod = inspect.getmodule(fn)
        src = inspect.getsource(mod) if mod else ""
        out.append({"name": name, "module": rel(mod.__file__) if mod else None, "signature": str(inspect.signature(fn)),
                    "doc": inspect.getdoc(fn) or "", "module_doc": inspect.getdoc(mod) or "",
                    "modes": built.get(name, []),
                    "gates": [g for g in GATE_NAMES if re.search(rf"[\"']{g}[\"']|{g}_gate", src)],
                    "annotations": [a for a in ANNOT_NAMES if a in src]})
    recipes = []
    for p in sorted((ROOT / "code" / "pipeline" / "ops" / "recipes").glob("*.yaml")):
        recipes.append({"name": p.stem, "path": rel(p), "text": p.read_text(), "data": load_yaml(p)})
    return {"ops": out, "recipes": recipes}


def _analytics() -> str:
    from pipeline.ops import analytics
    from pipeline.store import Store
    return analytics.report(analytics.collect(Store()))


ANALYTICS = _Cached(_analytics, ttl=600)      # a full pass over the store takes ~20 s


def analytics_md(force: bool = False) -> str:
    return ANALYTICS.get(force)


def op_counts() -> list[dict]:
    rows = SCEN.get()["rows"]
    c = Counter((r.get("op") or (f"legacy:{r['legacy_op']}" if r.get("legacy_op") else None), r.get("mode"),
                 r.get("bucket")) for r in rows if r.get("parent"))
    out = defaultdict(lambda: {"accepted": 0, "hard": 0, "rejected": 0})
    for (op, mode, b), n in c.items():
        out[(op, mode)][b if b in ("accepted", "hard", "rejected") else "accepted"] += n
    return [{"op": k[0], "mode": k[1], **v} for k, v in sorted(out.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1])))]


# ====================================================================== home
def home() -> dict:
    from pipeline.ops import queue as Q
    rs = runs()
    ts = Q.tasks()
    return {"runs": rs[:12], "running": [r for r in rs if r["running"]],
            "measurements": measurements()["rows"][-8:][::-1],
            "queue": {"pending": sum(1 for t in ts if not t["answer"]), "answered": sum(1 for t in ts if t["answer"])},
            "scenarios": len(SCEN.get()["rows"]), "index_built": SCEN.built}


# ====================================================================== sign-off
def signoffs() -> dict:
    from pipeline.ops import queue as Q
    return Q.signoffs()


def signoff_of(kind: str, target: str) -> dict | None:
    return signoffs().get((kind, target))


# ====================================================================== batches (for batch sign-off)
DATASETS = DATA / "datasets"
OPS_RUNS = ROOT / "results" / "ops" / "runs"


def batches() -> list[dict]:
    """Every batch Peter may sign off: operator recipe runs (results/ops/runs/*.jsonl) and dataset versions
    (data/datasets/<name>/)."""
    out = []
    for p in sorted(OPS_RUNS.glob("*.jsonl")) if OPS_RUNS.exists() else []:
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        out.append({"id": f"opsrun:{p.stem}", "kind": "operator run", "name": p.stem, "path": rel(p), "mtime": mtime(p),
                    "n": len(rows), "buckets": dict(Counter(r.get("bucket") for r in rows))})
    for d in sorted(DATASETS.iterdir()) if DATASETS.exists() else []:
        if d.is_dir():
            out.append({"id": f"dataset:{d.name}", "kind": "dataset version", "name": d.name, "path": rel(d),
                        "mtime": mtime(d), "n": len(batch_items(f"dataset:{d.name}")), "buckets": {}})
    so = signoffs()
    for b in out:
        b["signoff"] = so.get(("batch", b["id"]))
    out.sort(key=lambda b: b["mtime"] or "", reverse=True)
    return out


def batch_items(bid: str) -> list[str]:
    kind, _, name = bid.partition(":")
    if kind == "opsrun":
        p = OPS_RUNS / f"{name}.jsonl"
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
        return [r["id"] for r in rows if r.get("id")]
    if kind == "dataset":
        d = DATASETS / name
        ids = []
        tags = dataset_tags(name)
        cf = d / (f"cells-{tags[-1]}.json" if tags else "cells.json")
        if cf.exists():
            for c in json.loads(cf.read_text()):
                ids += [c.get("x1"), c.get("x2")]
        for f in ("items.txt", "ids.txt"):
            if (d / f).exists():
                ids += [l.split()[0] for l in (d / f).read_text().splitlines() if l.strip() and not l.startswith("#")]
        return list(dict.fromkeys(i for i in ids if i))
    if kind == "filter":
        from urllib.parse import parse_qs
        f = {k: v[0] for k, v in parse_qs(name).items()}
        return [r["id"] for r in scenario_rows(f)]
    return []


def batch_detail(bid: str, sample_n: int = 8, seed: int = 0) -> dict:
    """Bucket counts, gate failures, drift/cue table, and a random spot-check sample with full context."""
    import random
    from pipeline.ops.analytics import drift
    ids = batch_items(bid)
    idx = SCEN.get()["by_id"]
    buckets, gates, ops = Counter(), Counter(), Counter()
    dr = []
    for i in ids:
        r = idx.get(i)
        if not r:
            buckets["missing"] += 1
            continue
        buckets[r["bucket"]] += 1
        ops[f"{r.get('op') or r.get('legacy_op') or 'anchor'}" + (f"/{r['mode']}" if r.get("mode") else "")] += 1
        d = scenario(i) or {}
        steps = (d.get("lineage") or {}).get("steps") or []
        for g, v in ((steps[-1].get("gates") if steps else None) or {}).items():
            if isinstance(v, dict) and not v.get("pass", True):
                gates[g] += 1
        try:
            dr.append(drift(d["case"]))
        except Exception:                                             # noqa: BLE001
            pass
    cues = {}
    if dr:
        n = len(dr)
        # pipeline.ops.analytics.drift (2026-11-11 fix): gold UNIQUELY longest in characters vs the chance of that
        # (ties count as not-longest); older drift versions had only a word rank, kept as a fallback
        if "gold_unique_longest" in dr[0]:
            longest = sum(bool(x["gold_unique_longest"]) for x in dr) / n
            chance = sum(x["chance_unique_longest"] for x in dr) / n
        else:
            longest = sum(x.get("gold_len_rank") == 1 for x in dr) / n
            chance = sum(1 / x["n_options"] for x in dr) / n
        ratios = sorted(x.get("gold_len_ratio") for x in dr if x.get("gold_len_ratio") is not None)
        cues = {"n": n, "gold_longest": longest, "gold_longest_chance": chance,
                "gold_len_ratio": ratios[len(ratios) // 2] if ratios else None,
                "support_gold": sum(x["support_gold"] for x in dr) / n,
                "support_other": sum(x["support_other_mean"] for x in dr) / n,
                "handup_gold": sum(bool(x["handup_gold"]) for x in dr) / n,
                "gold_pos": dict(sorted(Counter(f"{x['n_options']}-opt pos {x['gold_pos']}" for x in dr).items())),
                "len_spread": sorted(x["len_spread"] for x in dr)[n // 2]}
    rng = random.Random(f"{bid}:{seed}")
    pick = rng.sample([i for i in ids if i in idx], min(sample_n, len([i for i in ids if i in idx])))
    return {"id": bid, "n": len(ids), "buckets": dict(buckets), "gate_failures": dict(gates), "ops": dict(ops),
            "cues": cues, "sample": [review_context(i) for i in pick], "ids": ids}


def review_context(sid: str) -> dict:
    """Everything a reviewer needs on one page (memory: review sheets need context): agent, role, decider,
    question, options with gold, and the before/after against the parent, plus the step's gates/annotations."""
    d = scenario(sid) or {}
    c = d.get("case") or {}
    lin = d.get("lineage") or {}
    parent = scenario(lin["parent"]) if lin.get("parent") else None
    steps = lin.get("steps") or []
    return {"id": sid, "row": SCEN.get()["by_id"].get(sid), "case": c, "parent_id": lin.get("parent"),
            "diff": case_diff((parent or {}).get("case") or {}, c) if parent else [],
            "step": steps[-1] if steps else None, "legacy": {k: lin.get(k) for k in ("operator", "detail")},
            "signoff": signoff_of("scenario", sid)}


# ====================================================================== readiness funnel
def funnel() -> list[dict]:
    """Corpus -> anchors -> eligible -> option-matched -> derived pair cases -> traces -> pair cells -> runs -> exports.
    Each stage: count, what blocks the next, and a drill-down link."""
    rows = SCEN.get()["rows"]
    anchors = [r for r in rows if not r.get("parent") and r["where"] == "store"]
    corpus_anchors = [r for r in anchors if str(r.get("family", "")).startswith("CORPUS")]
    derived = [r for r in rows if r.get("parent")]
    st = []
    docs = list((DATA / "docs").glob("*.jsonl"))
    st.append({"stage": "Raw corpus documents", "count": len(docs), "where": "data/docs/*.jsonl",
               "link": None, "blocking": None})
    st.append({"stage": "Extracted anchor scenarios", "count": len(anchors),
               "detail": f"{len(corpus_anchors)} from the corpus families (CORPUS*); {len(anchors) - len(corpus_anchors)} older/other",
               "where": "data/store/scenarios/* (no lineage parent)", "link": "/scenarios?derived=anchor&where=store",
               "blocking": f"status: {dict(Counter(r.get('status') for r in anchors))}"})
    el = DATASETS / "pairs-v1" / "eligibility.jsonl"
    if el.exists():
        er = [json.loads(l) for l in el.read_text().splitlines() if l.strip()]
        ok = [r for r in er if r.get("eligible", r.get("pass"))]
        fails = Counter()
        for r in er:
            for k, v in (r.get("checks") or {}).items():
                if (isinstance(v, dict) and not v.get("pass", True)) or v is False:
                    fails[k] += 1
        st.append({"stage": "Quality-eligible anchors", "count": len(ok), "detail": f"of {len(er)} checked",
                   "where": rel(el), "link": "/eligibility", "blocking": f"failed checks: {dict(fails.most_common())}"})
    else:
        st.append({"stage": "Quality-eligible anchors", "count": None, "where": "data/datasets/pairs-v1/eligibility.jsonl",
                   "link": None, "blocking": "eligibility file not written yet"})
    mo = [r for r in rows if r.get("op") == "surface_edit" and r.get("mode") == "match_options"]
    st.append({"stage": "Option-matched cases (after transfer / neighbor; anchors need none, M12)", "count": len([r for r in mo if r["bucket"] == "accepted"]),
               "detail": f"{len(mo)} attempted; buckets {dict(Counter(r['bucket'] for r in mo))}" if mo else "none yet: runs as a step in the pairs-v1 transfer and neighbor recipes",
               "where": "surface_edit / match_options", "link": "/scenarios?op=surface_edit&mode=match_options",
               "blocking": None})
    by = Counter((r.get("op") or f"legacy:{r.get('legacy_op')}", r.get("mode"), r["bucket"]) for r in derived)
    acc = sum(n for (o, m, b), n in by.items() if b == "accepted")
    st.append({"stage": "Derived pair cases (all operators)", "count": acc,
               "detail": f"{len(derived)} derived in total; hard {sum(n for k, n in by.items() if k[2] == 'hard')}, "
                         f"rejected {sum(n for k, n in by.items() if k[2] == 'rejected')}",
               "where": "lineage.parent set", "link": "/scenarios?derived=derived", "blocking": None,
               "table": [{"op": o, "mode": m, "bucket": b, "n": n} for (o, m, b), n in sorted(by.items(), key=str)]})
    traces = list((STORE / "traces").glob("*/trace.json"))
    st.append({"stage": "Rendered traces", "count": len(traces), "where": "data/store/traces/*/trace.json",
               "link": "/scenarios?trace=yes",
               "blocking": f"{sum(1 for r in anchors if not r['has_trace'])} store anchors without a trace"})
    _t = dataset_tags("pairs-v1")
    cf = DATASETS / "pairs-v1" / (f"cells-{_t[-1]}.json" if _t else "cells.json")
    if cf.exists():
        cells = json.loads(cf.read_text())
        st.append({"stage": "Pair cells (pairs-v1)", "count": len(cells), "where": rel(cf),
                   "detail": str(dict(Counter(c.get("arm") for c in cells))), "link": "/dataset/pairs-v1",
                   "blocking": None})
    else:
        st.append({"stage": "Pair cells (pairs-v1)", "count": None, "where": "data/datasets/pairs-v1/cells.json",
                   "link": None, "blocking": "not built yet"})
    rs = runs()
    used = set(USAGE.get())
    st.append({"stage": "Eval runs", "count": len(rs), "where": "results/transfer, results/allpairs",
               "detail": f"{len(used)} scenarios appear in at least one run; "
                         f"{sum(1 for r in rs if r['running'])} running now", "link": "/runs", "blocking": None})
    ex = [d for d in (DATA / "exports").iterdir() if d.is_dir()] if (DATA / "exports").exists() else []
    exd = []
    for d in sorted(ex):
        m = json.loads((d / "manifest.json").read_text()) if (d / "manifest.json").exists() else {}
        exd.append(f"{d.name}: {m.get('counts')} ({m.get('created', '?')[:10]})")
    st.append({"stage": "Exports (SFT / RL / eval)", "count": len(ex), "where": "data/exports/", "detail": "; ".join(exd),
               "link": None, "blocking": "exports predate the operator dataset; rebuild after pairs-v1"})
    return st


def eligibility() -> list[dict]:
    el = DATASETS / "pairs-v1" / "eligibility.jsonl"
    return [json.loads(l) for l in el.read_text().splitlines() if l.strip()] if el.exists() else []


# ====================================================================== sign-off queue and search
def awaiting_signoff() -> dict:
    so = signoffs()
    rs = [r for r in runs() if (r.get("status") in ("complete", None)) and not r["running"]
          and ("run", r["run"]) not in so]
    bs = [b for b in batches() if not b["signoff"]]
    from pipeline.ops import queue as Q
    reviews = [t for t in Q.tasks() if t["type"] == "review" and not t["answer"]]
    done = sorted(so.values(), key=lambda r: r["ts"], reverse=True)
    return {"runs": rs, "batches": bs, "reviews": reviews, "done": done}


def search(q: str, limit: int = 60) -> dict:
    q = (q or "").strip().lower()
    if not q:
        return {"scenarios": [], "runs": [], "measurements": [], "families": []}
    rows = SCEN.get()["rows"]
    sc = [r for r in rows if q in r["id"].lower() or q in (r.get("title") or "").lower()
          or q in str(r.get("family", "")).lower()][:limit]
    fam = sorted({r["family"] for r in rows if q in str(r.get("family", "")).lower()})[:30]
    rs = [r for r in runs() if q in r["run"].lower()]
    ms = [m for m in measurements()["rows"] if q in (m["id"] + " " + m["title"]).lower()]
    return {"scenarios": sc, "runs": rs, "measurements": ms, "families": fam}


# ---------------------------------------------------------------- system diagram page (2026-11-11, Peter)
def _pipeline_counts() -> dict:
    out = {"docs": len(list((DATA / "docs").glob("*.jsonl")))}
    n_ep = n_docs = 0
    for p in (STORE / "episodes" / "corpus").glob("*.yaml"):
        d = load_yaml(p)
        eps = d.get("episodes", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
        n_docs += 1
        n_ep += len(eps)
    out.update(episodes=n_ep, episode_docs=n_docs)
    sel = ok = 0
    for b in ("corpus-batch1", "corpus-batch2"):
        p = STORE / "episodes" / f"{b}.results.jsonl"
        if p.exists():
            rs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            sel += len(rs)
            ok += sum(1 for r in rs if (r.get("outcome") or r.get("status")) == "ok")
    out.update(selected=sel, extracted_ok=ok)
    rows = SCEN.get()["rows"]
    anchors = [r for r in rows if not r.get("parent") and r["where"] == "store"]
    out["anchors"] = len(anchors)
    out["corpus_anchors"] = sum(1 for r in anchors if str(r.get("family", "")).startswith("CORPUS"))
    el = DATA / "datasets" / "pairs-v1" / "eligibility.jsonl"
    if el.exists():
        er = [json.loads(l) for l in el.read_text().splitlines() if l.strip()]
        out["eligible"] = sum(1 for r in er if r.get("eligible"))
        out["leak_fail"] = sum(1 for r in er if "leak" in (r.get("why_not") or []))
    return out


PIPE = _Cached(_pipeline_counts, ttl=600)


def pairs_yields() -> list[dict]:
    """Latest run log of each pairs-v1 recipe: buckets per step (results/ops/runs/pairs_v1_<arm>-<ts>.jsonl)."""
    runs_dir = ROOT / "results" / "ops" / "runs"
    latest = {}
    for p in sorted(runs_dir.glob("pairs_v1_*.jsonl")):
        latest[p.name.split("-")[0]] = p                      # sorted by timestamp in the name: last wins
    out = []
    for name, p in sorted(latest.items()):
        steps = {}
        for l in p.read_text().splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            st = steps.setdefault(r.get("recipe_step"), {"op": r.get("op"), "mode": r.get("mode"), "buckets": {}})
            st["buckets"][r.get("bucket")] = st["buckets"].get(r.get("bucket"), 0) + 1
        out.append({"recipe": name, "log": rel(p), "stem": p.stem, "steps": [dict(step=k, **v) for k, v in sorted(steps.items())]})
    return out


# ====================================================================== datasets (pairs-v1 browser)
ARM_INFO = {
    "self": ("Self", "X2 = X1's own case (ceiling)"),
    "transfer": ("Transfer", "same structure (K, V) in another domain; options matched, gold position balanced"),
    "transfer_flip": ("Flipped transfer", "the transfer case with one would_change condition made true: V changes"),
    "same_domain_flip": ("Same-domain flip", "the anchor with one would_change condition made true: V changes"),
    "noflip": ("Would-not-change edit", "a would_not_change condition made true: facts change, V holds"),
    "revised": ("Revised case C′", "the case's weights edited so its weighing reaches another option"),
    "neighbor": ("Neighbor control", "same sub-domain, a different situation with the same K and V"),
    "decoy": ("Decoy", "another pilot anchor (different family and domain): should be not_governed"),
}
ARM_ORDER = list(ARM_INFO)


def dataset_tags(name: str) -> list[str]:
    d = DATASETS / name
    return sorted(p.stem[len("manifest-"):] for p in d.glob("manifest-*.json")) if d.exists() else []


def _ds_load(name: str, tag: str) -> dict:
    d = DATASETS / name
    man = json.loads((d / f"manifest-{tag}.json").read_text())
    cells = json.loads((d / f"cells-{tag}.json").read_text())
    att = [json.loads(l) for l in (d / f"attempts-{tag}.jsonl").read_text().splitlines() if l.strip()]
    return {"manifest": man, "cells": cells, "attempts": att}


def _case_brief(sid: str) -> dict:
    d = scenario(sid) or {}
    c = d.get("case") or {}
    r = SCEN.get()["by_id"].get(sid) or {}
    gold = (c.get("verdict") or {}).get("choice")
    return {"id": sid, "title": d.get("title") or r.get("title"), "domain": d.get("domain"), "family": d.get("family"),
            "question": c.get("question"), "role": c.get("agent_role"), "decider": c.get("decider"),
            "n_options": len(c.get("options") or {}), "gold": gold,
            "gold_text": ((c.get("options") or {}).get(gold) or {}).get("do"), "has_trace": bool(r.get("has_trace"))}


def dataset_overview(name: str, tag: str, arm: str | None = None) -> dict:
    ds = _ds_load(name, tag)
    cells, att = ds["cells"], ds["attempts"]
    anchors = sorted({c["x1"] for c in cells})
    grid = {a: {k: [] for k in ARM_ORDER} for a in anchors}
    for c in cells:
        grid[c["x1"]][c["arm"]].append(c)
    briefs = {a: _case_brief(a) for a in anchors}
    # yield: per recipe x step x bucket (drop_option shown but marked excluded)
    yields = defaultdict(Counter)
    for a in att:
        yields[(a["recipe"], a["step"], a["op"] + (f"/{a['mode']}" if a.get("mode") else ""), a["arm_excluded"])][a["bucket"]] += 1
    ytab = [{"recipe": k[0], "step": k[1], "op": k[2], "excluded": k[3], **dict(v), "total": sum(v.values())}
            for k, v in sorted(yields.items())]
    arm_rows = None
    if arm:
        arm_rows = [{"cell": c, "x1": briefs[c["x1"]], "x2": _case_brief(c["x2"])} for c in cells if c["arm"] == arm]
    return {"name": name, "tag": tag, "tags": dataset_tags(name), "manifest": ds["manifest"], "anchors": anchors,
            "grid": grid, "briefs": briefs, "yields": ytab, "arm": arm, "arm_rows": arm_rows,
            "by_arm": Counter(c["arm"] for c in cells),
            "anchors_with": {k: sum(1 for a in anchors if grid[a][k]) for k in ARM_ORDER}}


def dataset_anchor(name: str, tag: str, aid: str) -> dict:
    """One anchor and everything built from it: the served cells per arm (with the full operator chain, each hop's
    diff, and the end-to-end diff against the anchor), plus every attempt that did not make it and why."""
    ds = _ds_load(name, tag)
    a_doc = scenario(aid) or {}
    a_case = a_doc.get("case") or {}
    cells = [c for c in ds["cells"] if c["x1"] == aid]
    att = [x for x in ds["attempts"] if x["anchor"] == aid]
    by_id = {x["id"]: x for x in att if x.get("id")}
    arms = []
    for k in ARM_ORDER:
        served = []
        for c in [c for c in cells if c["arm"] == k]:
            x2 = scenario(c["x2"]) or {}
            hops = []
            for i in range(1, len(c["chain"])):
                p, ch = c["chain"][i - 1], c["chain"][i]
                st = ((scenario(ch) or {}).get("lineage") or {}).get("steps") or []
                hops.append({"from": p, "to": ch, "attempt": by_id.get(ch), "step": st[-1] if st else None,
                             "diff": case_diff((scenario(p) or {}).get("case") or {}, (scenario(ch) or {}).get("case") or {})})
            served.append({"cell": c, "case": x2.get("case") or {}, "title": x2.get("title"), "domain": x2.get("domain"),
                           "hops": hops, "diff": case_diff(a_case, x2.get("case") or {}) if k not in ("self", "decoy") else [],
                           "signoff": signoff_of("scenario", c["x2"])})
        arms.append({"arm": k, "label": ARM_INFO[k][0], "what": ARM_INFO[k][1], "served": served})
    failed = [x for x in att if x["bucket"] in ("rejected", "hard")]
    return {"name": name, "tag": tag, "id": aid, "doc": a_doc, "case": a_case, "brief": _case_brief(aid),
            "arms": arms, "failed": failed, "attempts": att,
            "elig": next((json.loads(l) for l in (DATASETS / name / "eligibility.jsonl").read_text().splitlines()
                          if f'"id": "{aid}"' in l), None) if (DATASETS / name / "eligibility.jsonl").exists() else None}
