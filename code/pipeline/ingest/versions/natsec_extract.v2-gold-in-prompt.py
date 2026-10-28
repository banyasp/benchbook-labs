"""W8b natsec extraction: sources-natsec.episodes.yaml -> held-out test scenarios (BUILD-BRIEF-v2.4 W8b).

    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec_extract [--episode KUNDUZ-2009-1 ...] [--workers 4]

Per episode: the episode's decision spans + the gold-finding spans (W8b's `spans` and `gold.spans`) are given to the
standard extractor (extract_fq.v2 + extract_a.v1 and the option rules) with prompts/natsec_scope.v1.md appended.
Scope = the decision, not the technique:
- the extractor may answer {"skip": "technique"} -> the episode fails criterion 4 (rejected, recorded);
- the output is screened with technique_check; any `strip` flag -> one re-extraction told which details to remove;
  still flagged -> rejected (criterion 4). Never retried elsewhere: a refusal is recorded, never routed around.
Outcomes: scenarios (split test, held_out, refusal_sensitivity high) in the store; rejects and refusals in
data/store/episodes/rejected-natsec.jsonl; incomplete extractions in data/store/incomplete/; a summary JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from pipeline.store import DATA, ROOT, Store

from . import technique_check as TC
from .extract import ExtractionError, IncompleteExtraction, TechniqueSkip, extract_episode, save_incomplete

HERE = Path(__file__).parent
EPISODES = HERE / "sources-natsec.episodes.yaml"
SCOPE = HERE / "prompts" / "natsec_scope.v1.md"
ACQ = DATA / "store" / "registry" / "acquired-natsec.yaml"
DOMAIN = "military-operational"
KIND = "national-security investigation, inquiry or tribunal report"


def _doc_spans(doc: str, data: Path) -> list[dict]:
    return [json.loads(l) for l in (data / "docs" / f"{doc}.jsonl").read_text().splitlines() if l.strip()]


def _range(spans: list[dict], doc: str, a: str, b: str) -> list[dict]:
    ids = [s["span"] for s in spans]
    ia, ib = ids.index(f"src:{doc}#{a}"), ids.index(f"src:{doc}#{b}")
    return spans[min(ia, ib):max(ia, ib) + 1]


def episode_spans(ep: dict, data: Path) -> list[dict]:
    """Decision spans then gold-finding spans, in order, de-duplicated."""
    out, seen, cache = [], set(), {}
    for r in list(ep.get("spans") or []) + list((ep.get("gold") or {}).get("spans") or []):
        sp = cache.setdefault(r["doc"], _doc_spans(r["doc"], data))
        for s in _range(sp, r["doc"], r["from"], r["to"]):
            if s["span"] not in seen:
                seen.add(s["span"])
                out.append(s)
    return out


def raw_sha(doc: str, data: Path) -> str:
    hits = [p.name for p in (data / "raw").glob(f"{doc}*") if not p.name.endswith(".json")]
    if len(hits) != 1:
        raise ExtractionError(f"raw file for doc {doc}: {hits}")
    return hits[0]


def source_meta(sid: str) -> dict:
    acq = yaml.safe_load(ACQ.read_text())["sources"]
    return acq[sid]


def gold_block(ep: dict) -> str:
    """R61 (batch 2026-10-28): the first run took the course the decider actually took as the verdict in 8/17 episodes.
    The gold is the convening/final authority's finding (W8b `gold`), so the extractor is told it explicitly."""
    g = ep.get("gold") or {}
    if not g.get("finding"):
        return ""
    return ("\n\n### The endorsed answer (gold) for this episode\n"
            f"Convening / final authority: {' '.join(str(g.get('authority', '')).split())}\n"
            f"Its finding: {' '.join(str(g['finding']).split())}\n"
            "`verdict.choice` (and `real_option`) must be the course of action this finding endorses as what the decider "
            "SHOULD have done, which may differ from what the decider actually did. When the finding criticises the "
            "decision taken, the endorsed option is the alternative course the finding implies (e.g. not striking, "
            "warning first, verifying first). State what was actually done, if needed, as a fact or in the reasoning, "
            "never as the verdict. `basis_statement` must be in English and name offices, not persons.")


def _flags(s) -> list[str]:
    return sorted({f"{p}: {f.match}" for p, f in TC.scan_scenario(s.case.dump()) if f.severity == "strip"})


def extract_one(ep: dict, store: Store, data: Path = DATA, complete_fn=None) -> dict:
    src = source_meta(ep["source"])
    source = {"id": ep["source"], "family": ep["family"], "domain": DOMAIN, "url": src.get("url"), "title": src.get("title"),
              "kind": KIND, "license": src.get("license"), "held_out": True,
              "content_domain": ep.get("content_domain"), "refusal_sensitivity": "high"}
    e2 = {"n": ep.get("n", 1), "focus": " ".join(ep["focus"].split()), "content_domain": ep.get("content_domain"),
          "refusal_sensitivity": "high"}
    source["episodes"] = [e2]
    spans = episode_spans(ep, data)
    sha = raw_sha(ep["doc"], data)
    sid = f"DR-{ep['id']}@v1"
    scope = SCOPE.read_text() + gold_block(ep)
    rec = {"episode": ep["id"], "scenario": sid, "family": ep["family"], "n_spans": len(spans)}
    addendum, flags = scope, []
    for attempt in (1, 2):
        try:
            s = extract_episode(source, e2, spans, sha, "test", complete_fn, data, addendum=addendum, sid=sid)
        except TechniqueSkip as e:
            return {**rec, "outcome": "rejected", "criterion": 4, "reason": f"extractor skip: {e.reason}", "step": e.step}
        except IncompleteExtraction as e:
            save_incomplete(e, ep["family"], sid, data)
            out = "refusal" if e.reason == "refusal" else "incomplete"
            return {**rec, "outcome": out, "reason": str(e)[:300], "refusal": e.refusal}
        except ExtractionError as e:
            return {**rec, "outcome": "incomplete", "reason": str(e)[:300]}
        flags = _flags(s)
        if not flags:
            break
        addendum = (scope + "\n\n### Your previous extraction of this episode contained operational technique. Remove every "
                    "one of these details (replace by its decision-level consequence or omit it):\n- " + "\n- ".join(flags[:30]))
    if flags:
        return {**rec, "outcome": "rejected", "criterion": 4, "reason": "technique remains after one re-extraction",
                "flags": flags[:30]}
    s.held_out, s.split = True, "test"
    s.tags += ["natsec", "held-out-domain", f"tier-{ep.get('tier', 1)}"] + (["translated-de"] if ep.get("language") == "de" else []) \
        + (["ocr"] if "ocr" in (src.get("tags") or []) else [])
    gold = ep.get("gold") or {}
    s.provenance.step(id="natsec.scope", operator="extract", ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      notes=(f"W8b episode {ep['id']}; scope addendum natsec_scope.v1; technique screen clean after "
                             f"{attempt} extraction(s); gold authority: {gold.get('authority')}"
                             + ("; translated from German by the extractor (R60)" if ep.get("language") == "de" else "")
                             + (f"; dispute: {' '.join(str(ep['dispute']).split())[:300]}" if ep.get("dispute") else "")),
                      params={"attempts": attempt})
    store.save_scenario(s)
    return {**rec, "outcome": "ok", "attempts": attempt, "facts": len(s.case.facts),
            "grounded": len(s.grounded_facts()), "choice": s.case.verdict.choice}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--episode", nargs="*")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    eps = yaml.safe_load(EPISODES.read_text())["episodes"]
    if a.episode:
        eps = [e for e in eps if e["id"] in a.episode]
    store = Store()

    def run(ep):
        try:
            r = extract_one(ep, store)
        except Exception as e:                                  # noqa: BLE001 - record and continue
            r = {"episode": ep["id"], "outcome": "error", "reason": f"{type(e).__name__}: {e}"[:300]}
        print(json.dumps(r, ensure_ascii=False), flush=True)
        return r

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(run, eps))
    rej = DATA / "store" / "episodes" / "rejected-natsec.jsonl"
    rej.parent.mkdir(parents=True, exist_ok=True)
    with open(rej, "a") as f:
        for r in res:
            if r["outcome"] != "ok":
                f.write(json.dumps({**r, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, ensure_ascii=False) + "\n")
    n = len(res)
    summ = {"episodes": n, **{k: sum(r["outcome"] == k for r in res) for k in ("ok", "rejected", "refusal", "incomplete", "error")}}
    summ["refusal_rate"] = round(summ["refusal"] / max(1, n), 3)
    summ["router_needed"] = summ["refusal_rate"] > 0.2          # W8b: > ~20% false-positive refusals -> pull the router forward
    out = ROOT / "results" / "datagen-2026-10-28" / "natsec-extract.json"
    out.write_text(json.dumps({"summary": summ, "results": res}, indent=1, ensure_ascii=False))
    print(json.dumps(summ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
