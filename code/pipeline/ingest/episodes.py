"""Episode finder (design v2.4.1 4.2, brief W4): gpt-oss lists the decision points of a normalized document.

    python -m pipeline.ingest episodes --source ID [--data DIR] [--dry-run]

Passes (all 4 criteria) -> data/store/episodes/<source>.yaml in the seed's episode shape
  {n, focus, span_range:[first,last], decision, content_domain, refusal_sensitivity}  (extract reads `span_range`).
Rejects are kept -> data/store/episodes/rejected.jsonl, each with the failed criteria. A refusal is recorded there too
(failed: [refusal]) and never retried elsewhere.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from bench.models import RefusalError
from pipeline.store import DATA, write_yaml

from . import registry as R
from .extract import (CONTENT_SENSITIVITY, DOMAIN_TO_CONTENT, ExtractionError, call_json, prompt_file, scenario_domain_fields,
                      spans_text)
from . import option_rules as OR
from .normalize import load_spans

CRITERIA = ("real_choice", "choice_stated", "reasons_given", "in_scope")
SENS = {"low", "medium", "high"}
WINDOW_CHARS = 60000


def windows(spans: list[dict], limit: int = WINDOW_CHARS) -> list[list[dict]]:
    out, cur, n = [], [], 0
    for s in spans:
        if cur and n + len(s["text"]) > limit:
            out.append(cur)
            cur, n = [], 0
        cur.append(s)
        n += len(s["text"]) + 20
    return out + ([cur] if cur else [])


def validate_candidates(o: dict, ids: list[str]) -> list[str]:
    errs = []
    if not isinstance(o.get("candidates"), list):
        return ["`candidates` must be a list"]
    for i, c in enumerate(o["candidates"], 1):
        for k in ("decision", "focus", "span_start", "span_end", "criteria", "content_domain", "refusal_sensitivity"):
            if k not in c:
                errs.append(f"candidate {i}: missing `{k}`")
        if errs:
            continue
        for k in ("span_start", "span_end"):
            if c[k] not in ids:
                errs.append(f"candidate {i}: unknown span id {c[k]}")
        if c["span_start"] in ids and c["span_end"] in ids and ids.index(c["span_start"]) > ids.index(c["span_end"]):
            errs.append(f"candidate {i}: span_start is after span_end")
        for k in CRITERIA:
            if not isinstance((c["criteria"] or {}).get(k), dict) or not isinstance(c["criteria"][k].get("pass"), bool):
                errs.append(f"candidate {i}: criteria.{k} must be {{\"pass\": true|false, \"note\": ...}}")
        if c["refusal_sensitivity"] not in SENS:
            errs.append(f"candidate {i}: refusal_sensitivity must be low|medium|high")
        errs += OR.name_errors({f"candidate {i}.decision": c["decision"], f"candidate {i}.focus": c["focus"]})
    return errs


def find_episodes(source: dict, spans: list[dict], complete_fn: Callable | None = None, data: Path = DATA) -> dict:
    if complete_fn is None:
        from bench.models import complete as complete_fn
    tmpl, version, _ = prompt_file("find_episodes.v1")
    sys_msg = "You are a careful legal-and-policy analyst. Reply with one JSON object only."
    log_dir = data / "store" / "episodes" / "logs"
    passes, rejects = [], []
    ids_all = [s["span"] for s in spans]
    base = scenario_domain_fields(source, {})
    for wi, win in enumerate(windows(spans)):
        ids = [s["span"] for s in win]
        try:
            obj, _, _ = call_json(f"EP{wi}", "extractor", sys_msg, tmpl.replace("{{SPANS}}", spans_text(win)),
                                  lambda o: validate_candidates(o, ids), complete_fn, log_dir, source["id"])
        except ExtractionError as e:
            refused = getattr(e, "reason", "") == "refusal"
            rejects.append({"source": source["id"], "window": wi, "failed": ["refusal" if refused else "finder-error"],
                            "reason": str(e)[:300], "refusal": getattr(e, "refusal", None),
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            continue
        for c in obj["candidates"]:
            failed = [k for k in CRITERIA if not c["criteria"][k]["pass"]]
            cd = c["content_domain"] if c["content_domain"] else base["content_domain"]
            rs = c["refusal_sensitivity"]
            if base["refusal_sensitivity"] == "high":          # a seed that says high (natsec) is never lowered by the model
                rs = "high"
            if failed:
                rejects.append({"source": source["id"], "decision": c["decision"], "span_range": [c["span_start"], c["span_end"]],
                                "failed": failed, "notes": {k: c["criteria"][k].get("note") for k in failed},
                                "content_domain": cd, "refusal_sensitivity": rs,
                                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            else:
                passes.append({"decision": c["decision"], "focus": c["focus"], "span_range": [c["span_start"], c["span_end"]],
                               "content_domain": cd, "refusal_sensitivity": rs, "criteria": {k: True for k in CRITERIA}})
    seen, eps = set(), []
    for p in passes:                                            # dedupe identical ranges across windows
        key = tuple(p["span_range"])
        if key in seen:
            continue
        seen.add(key)
        eps.append({"n": len(eps) + 1, "focus": p["focus"], "span_range": p["span_range"], "decision": p["decision"],
                    "content_domain": p["content_domain"], "refusal_sensitivity": p["refusal_sensitivity"]})
    d = data / "store" / "episodes"
    d.mkdir(parents=True, exist_ok=True)
    write_yaml(d / f"{source['id']}.yaml", {"source": source["id"], "prompt": version, "episodes": eps})
    if rejects:
        with open(d / "rejected.jsonl", "a") as f:
            for r in rejects:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"passed": eps, "rejected": rejects}


def run(source_id: str, complete_fn=None, data: Path = DATA) -> list[str]:
    reg, acq = R.load_registry(), R.load_acquired()
    src = next((s for s in reg["sources"] if s["id"] == source_id), None)
    if src is None:
        raise SystemExit(f"unknown source {source_id}")
    spans = load_spans(acq[source_id]["sha256"][:12])
    out = find_episodes(src, spans, complete_fn, data)
    lines = [f"{source_id}: {len(out['passed'])} episodes pass, {len(out['rejected'])} rejected"]
    lines += [f"  ep{e['n']} [{e['content_domain']}/{e['refusal_sensitivity']}] {e['decision']}" for e in out["passed"]]
    lines += [f"  REJECT {r.get('decision', r.get('reason'))} failed={r['failed']}" for r in out["rejected"]]
    return lines
