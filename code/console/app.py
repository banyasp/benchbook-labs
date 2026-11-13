"""Benchbook research console (2026-11-11, Peter): observability over the whole research effort + human solver and
sign-off. Local only: serve on 127.0.0.1 and reach it through the editor's SSH port forwarding (README).

    PYTHONPATH=code .venv/bin/python -m console            # http://127.0.0.1:8765 (8000 is vLLM)
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote, urlencode

import yaml
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from pipeline.ops import queue as Q

from . import data as D
from . import sft as SFTD

HERE = Path(__file__).parent
app = FastAPI(title="Benchbook console", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]))


def _pct(x, digits=0):
    return "–" if x is None else f"{100 * x:.{digits}f}%"


def _pretty(o):
    from jinja2 import Undefined
    if isinstance(o, dict):
        o = {k: v for k, v in o.items() if not isinstance(v, Undefined)}
    return yaml.safe_dump(o, sort_keys=False, allow_unicode=True, width=110) if o is not None and not isinstance(o, Undefined) else ""


env.filters.update(pct=_pct, pretty=_pretty, q=lambda s: quote(str(s), safe=""),
                   js=lambda o: Markup(json.dumps(o, ensure_ascii=False)), md=lambda s: Markup(D.render_md(s or "")))
env.globals.update(urlencode=urlencode)


def page(name: str, crumbs: list | None = None, **ctx) -> HTMLResponse:
    so = ctx.pop("_signoff", None)
    return HTMLResponse(env.get_template(name).render(crumbs=crumbs or [], signoff=so, **ctx))


# ---------------------------------------------------------------- home, funnel, search
@app.get("/", response_class=HTMLResponse)
def home():
    return page("home.html", [], h=D.home(), funnel=D.funnel())


@app.get("/funnel", response_class=HTMLResponse)
def funnel():
    return page("funnel.html", [("Data readiness", None)], funnel=D.funnel())


@app.get("/eligibility", response_class=HTMLResponse)
def eligibility():
    return page("eligibility.html", [("Data readiness", "/funnel"), ("Eligibility", None)], rows=D.eligibility())


@app.get("/search", response_class=HTMLResponse)
def search(q: str = ""):
    res = D.search(q)
    if len(res["scenarios"]) == 1 and not res["runs"] and q.strip() == res["scenarios"][0]["id"]:
        return RedirectResponse(f"/scenario/{quote(q.strip(), safe='')}", 302)
    return page("search.html", [("Search", None)], q=q, r=res)


@app.get("/refresh")
def refresh(back: str = "/"):
    D.SCEN.get(force=True)
    D.USAGE.get(force=True)
    return RedirectResponse(back if back.startswith("/") else "/", 302)


# ---------------------------------------------------------------- scenarios
@app.get("/scenarios", response_class=HTMLResponse)
def scenarios(request: Request):
    f = {k: v for k, v in request.query_params.items() if v}
    rows = D.scenario_rows(f)
    limit = int(f.get("limit", 300))
    so = D.signoffs()
    return page("scenarios.html", [("Scenarios", None)], rows=rows[:limit], total=len(rows), f=f,
                facets=D.facet_values(), so=so, built=D.SCEN.built, limit=limit,
                batch_link="/batch/filter:" + quote(urlencode({k: v for k, v in f.items() if k != "limit"}), safe=""))


@app.get("/scenario/{sid}", response_class=HTMLResponse)
def scenario(sid: str):
    d = D.scenario(sid)
    if d is None:
        raise HTTPException(404, f"no scenario {sid}")
    row = D.SCEN.get()["by_id"][sid]
    lin = d.get("lineage") or {}
    parent = D.scenario(lin["parent"]) if lin.get("parent") else None
    chain = D.lineage_chain(sid)
    crumbs = [("Scenarios", "/scenarios"), (row.get("family") or "?", f"/scenarios?family={quote(str(row.get('family')))}")]
    crumbs += [(c["id"], f"/scenario/{quote(c['id'], safe='')}") for c in chain[:-1]] + [(sid, None)]
    return page("scenario.html", crumbs, d=d, row=row, c=d.get("case") or {}, lin=lin, parent=parent,
                diff=D.case_diff(parent.get("case") or {}, d.get("case") or {}) if parent else [],
                chain=chain, desc=D.descendants(sid), sources=D.fact_sources(d), use=D.usage(sid),
                has_trace=row["has_trace"], _signoff=("scenario", sid, D.signoff_of("scenario", sid)))


@app.get("/scenario/{sid}/trace", response_class=HTMLResponse)
def trace(sid: str, key: int = 0):
    t = D.trace(sid)
    if t is None:
        raise HTTPException(404, f"no trace for {sid}")
    d = D.scenario(sid) or {}
    return page("trace.html", [("Scenarios", "/scenarios"), (sid, f"/scenario/{quote(sid, safe='')}"), ("Trace", None)],
                t=t, sid=sid, c=d.get("case") or {}, key=D.answer_key(sid) if key else None)


# ---------------------------------------------------------------- runs
@app.get("/runs", response_class=HTMLResponse)
def runs():
    so = D.signoffs()
    return page("runs.html", [("Runs", None)], runs=D.runs(), so=so)


@app.get("/run", response_class=HTMLResponse)
def run(run: str, vs: str | None = None, max_idx: int | None = None):
    if D.safe_path(run) is None or not (D.ROOT / run / "config.json").exists():
        raise HTTPException(404, run)
    cfg = D.run_config(run)
    info = next((r for r in D.runs() if r["run"] == run), {})
    prev = vs or D.previous_run(run)
    return page("run.html", [("Runs", "/runs"), (run, None)], run=run, info=info,
                cfg={k: v for k, v in cfg.items() if k not in D.SKIP_CFG}, git=cfg.get("git"), created=cfg.get("created"),
                res=D.run_results(run, max_idx), data=D.run_data(run), prompts=D.prompts_used(cfg),
                ch=D.run_changes(run, prev), all_runs=[r["run"] for r in D.runs()], max_idx=max_idx,
                _signoff=("run", run, D.signoff_of("run", run)))


@app.get("/run/samples", response_class=HTMLResponse)
def run_samples(run: str, arm: str | None = None, x1: str | None = None, wrong: int = 0):
    S = D.samples(run)
    S = [s for s in S if (not arm or s.get("phase") == arm) and (not x1 or s.get("x1") == x1)
         and (not wrong or not s.get("correct"))]
    return page("samples.html", [("Runs", "/runs"), (run, f"/run?run={quote(run)}"), ("Samples", None)],
                run=run, rows=S[:500], total=len(S), arm=arm, x1=x1, wrong=wrong)


@app.get("/run/sample", response_class=HTMLResponse)
def run_sample(run: str, sid: str, prompt: int = 0):
    s = D.sample(run, sid)
    if s is None:
        raise HTTPException(404, sid)
    pr = D.rebuild_prompt(run, s["row"]) if prompt else None
    return page("sample.html", [("Runs", "/runs"), (run, f"/run?run={quote(run)}"), (sid, None)], run=run, sid=sid,
                s=s, pr=pr)


# ---------------------------------------------------------------- documents
@app.get("/measurements", response_class=HTMLResponse)
def measurements():
    return page("measurements.html", [("Measurements", None)], m=D.measurements())


@app.get("/doc", response_class=HTMLResponse)
def doc(path: str):
    d = D.doc(path)
    if d is None:
        raise HTTPException(404, path)
    return page("doc.html", [(p, None) for p in [path]], d=d)


@app.get("/file", response_class=HTMLResponse)
def file(path: str):
    p = D.safe_path(path)
    if p is not None and p.is_dir():
        items = sorted(p.iterdir())
        return page("dir.html", [(path, None)], path=D.rel(p),
                    items=[{"name": i.name + ("/" if i.is_dir() else ""), "path": D.rel(i)} for i in items][:500])
    d = D.doc(path)
    if d is None:
        raise HTTPException(404, path)
    return page("doc.html", [(path, None)], d=d)


@app.get("/outstanding", response_class=HTMLResponse)
def outstanding():
    return page("doc.html", [("Outstanding work", None)], d=D.doc("docs/OUTSTANDING.md"))


@app.get("/notes", response_class=HTMLResponse)
def notes(which: str = "observations"):
    path = {"observations": "docs/OBSERVATIONS.md", "risks": "docs/RISK-REGISTER.md",
            "priorities": "docs/V2-PRIORITIES.md"}.get(which, "docs/OBSERVATIONS.md")
    return page("doc.html", [("Notes", None), (which, None)], d=D.doc(path), tabs=True, which=which)


# ---------------------------------------------------------------- prompts and operators
@app.get("/prompts", response_class=HTMLResponse)
def prompts():
    return page("prompts.html", [("Prompts", None)], groups=D.prompts())


@app.get("/prompt", response_class=HTMLResponse)
def prompt(path: str):
    d = D.doc(path)
    if d is None:
        raise HTTPException(404, path)
    if d["kind"] == "md":
        d["text"] = (D.ROOT / path).read_text()
    grp = next((g for g in D.prompts() for f in g["files"] if f["path"] == path), None)
    meta = next((f for f in grp["files"] if f["path"] == path), None) if grp else None
    return page("prompt.html", [("Prompts", "/prompts"), (path, None)], d=d, meta=meta,
                runs=D.prompt_runs(path) if path.startswith("code/harness/prompts") else [])


@app.get("/prompt/diff", response_class=HTMLResponse)
def prompt_diff(a: str, b: str):
    h = D.file_diff(a, b)
    if h is None:
        raise HTTPException(404, "file not found")
    return page("diff.html", [("Prompts", "/prompts"), ("Diff", None)], a=a, b=b, h=Markup(h))


@app.get("/pipeline", response_class=HTMLResponse)
def pipeline():
    return page("pipeline.html", [("System diagram", None)], c=D.PIPE.get(), yields=D.pairs_yields())


@app.get("/operators", response_class=HTMLResponse)
def operators():
    return page("operators.html", [("Operators", None)], o=D.operators(), counts=D.op_counts())


@app.get("/operators/analytics", response_class=HTMLResponse)
def operators_analytics(fresh: int = 0):
    html = D.render_md(D.analytics_md(force=bool(fresh)))
    return page("doc.html", [("Operators", "/operators"), ("Analytics", None)],
                d={"path": "pipeline.ops analytics (cached up to 10 min; add ?fresh=1 to recompute)", "html": html,
                   "kind": "md", "mtime": D.ANALYTICS.built})


# ---------------------------------------------------------------- queue (human solver + review)
@app.get("/queue", response_class=HTMLResponse)
def queue(show: str = "pending", type: str | None = None):
    ts = Q.tasks()
    if show == "pending":
        ts = [t for t in ts if not t["answer"]]
    elif show == "answered":
        ts = [t for t in ts if t["answer"]]
    if type:
        ts = [t for t in ts if t["type"] == type]
    return page("queue.html", [("Queue", None)], tasks=ts, show=show, type=type)


def _next_pending(after: str | None = None) -> str | None:
    ts = [t for t in Q.tasks() if not t["answer"]]
    ids = [t["id"] for t in ts]
    if after in ids:
        i = ids.index(after)
        ids = ids[i + 1:] + ids[:i]
    return ids[0] if ids else None


@app.get("/queue/{tid}", response_class=HTMLResponse)
def task(tid: str):
    t = Q.task(tid)
    if t is None:
        raise HTTPException(404, tid)
    ctx = None
    if t["type"] == "review":
        ctx = D.review_context(t["payload"]["scenario"])
    return page("task.html", [("Queue", "/queue"), (tid, None)], t=t, ctx=ctx, ans=Q.answer_of(tid),
                nxt=_next_pending(tid))


@app.post("/queue/{tid}/answer")
def task_answer(tid: str, answer: str = Form(...), ground_truth: str = Form(""), note: str = Form(""),
                go: str = Form("next")):
    if Q.task(tid) is None:
        raise HTTPException(404, tid)
    Q.answer(tid, answer, ground_truth=ground_truth or None, note=note)
    nxt = _next_pending(tid) if go == "next" else tid
    return RedirectResponse(f"/queue/{nxt}" if nxt else "/queue?show=answered", 303)


# ---------------------------------------------------------------- sign-off and batches
@app.get("/signoff", response_class=HTMLResponse)
def signoff_page():
    return page("signoff.html", [("Sign-off", None)], a=D.awaiting_signoff())


@app.post("/signoff")
def signoff(target_kind: str = Form(...), target_id: str = Form(...), decision: str = Form(...), note: str = Form(""),
            back: str = Form("/signoff")):
    Q.signoff(target_kind, target_id, decision, note)
    return RedirectResponse(back if back.startswith("/") else "/signoff", 303)


# ---------------------------------------------------------------- datasets (pairs-v1 browser)
@app.get("/datasets")
def datasets_index():
    names = [d.name for d in sorted(D.DATASETS.iterdir()) if d.is_dir() and D.dataset_tags(d.name)] if D.DATASETS.exists() else []
    return RedirectResponse(f"/dataset/{names[0]}" if names else "/batches", 303)


@app.get("/dataset/{name}", response_class=HTMLResponse)
def dataset(name: str, tag: str | None = None, arm: str | None = None):
    tags = D.dataset_tags(name)
    if not tags:
        raise HTTPException(404, f"no assembled versions of {name}")
    tag = tag if tag in tags else tags[-1]
    d = D.dataset_overview(name, tag, arm if arm in D.ARM_INFO else None)
    return page("dataset.html", [("Datasets", "/datasets"), (f"{name} · {tag}", None)], d=d, arm_info=D.ARM_INFO)


@app.get("/dataset/{name}/anchor/{aid}", response_class=HTMLResponse)
def dataset_anchor(name: str, aid: str, tag: str | None = None):
    tags = D.dataset_tags(name)
    if not tags:
        raise HTTPException(404, f"no assembled versions of {name}")
    tag = tag if tag in tags else tags[-1]
    d = D.dataset_anchor(name, tag, aid)
    if not d["attempts"] and not any(a["served"] for a in d["arms"]):
        raise HTTPException(404, f"{aid} is not an anchor of {name} · {tag}")
    return page("dataset_anchor.html", [("Datasets", "/datasets"), (f"{name} · {tag}", f"/dataset/{name}?tag={tag}"),
                                        (aid, None)], d=d)


@app.get("/batches", response_class=HTMLResponse)
def batches():
    return page("batches.html", [("Batches", None)], b=D.batches())


@app.get("/batch/{bid:path}", response_class=HTMLResponse)
def batch(bid: str, n: int = 8, seed: int = 0):
    b = D.batch_detail(bid, n, seed)
    return page("batch.html", [("Batches", "/batches"), (bid, None)], b=b, n=n, seed=seed,
                _signoff=("batch", bid, D.signoff_of("batch", bid)))


# ---------------------------------------------------------------- SFT target generation (2026-11-13)
@app.get("/sft", response_class=HTMLResponse)
def sft_runs():
    return page("sft_runs.html", [("SFT", None)], runs=SFTD.runs())


@app.get("/sft/run", response_class=HTMLResponse)
def sft_run(run: str):
    if not run.startswith("results/sft/") or not (SFTD.ROOT / run / "cells.json").exists():
        raise HTTPException(404, f"no SFT run at {run}")
    return page("sft_run.html", [("SFT", "/sft"), (run, None)], d=SFTD.run_overview(run))


@app.get("/sft/cell", response_class=HTMLResponse)
def sft_cell(run: str, cell: str):
    if not run.startswith("results/sft/") or not (SFTD.ROOT / run / "cells.json").exists():
        raise HTTPException(404, f"no SFT run at {run}")
    try:
        d = SFTD.cell_detail(run, cell)
    except StopIteration:
        raise HTTPException(404, f"no cell {cell} in {run}")
    return page("sft_cell.html", [("SFT", "/sft"), (run, f"/sft/run?run={quote(run, safe='')}"), (cell, None)], d=d)

