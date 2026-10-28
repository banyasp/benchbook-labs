"""Episode finder over the natsec decision corpus (brief W8b; Peter 2026-10-28: "run the episode finder over text/").

    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.corpus_episodes [--only ID ..] [--workers 24] [--dry-run]

Input: data/corpus/natsec/text/<id>.txt (header, a line of `=`, the text; form feeds = pages) and index.csv.
Each document is normalized to data/docs/<sha12>.jsonl (span ids `src:<sha12>#p<page>.<i>`, as natsec.normalize) and
run through the W4 finder (find_episodes.v1 + the corpus addendum). Passes -> data/store/episodes/corpus/<id>.yaml,
rejects -> data/store/episodes/corpus/rejected.jsonl; a summary -> data/store/episodes/corpus/summary.json.

Skipped: thin pages, texts under MIN_CHARS, and documents already acquired as W8b seed sources (same URL).
Doctrine (collection `doctrine`, catalog A1): criterion `choice_stated` is relaxed: a decision the doctrine frames
without stating the course passes with `relaxed: [choice_stated]`, and extraction tags it `doctrine-derived` with
model-solved gold (brief W8b). Held-out rule (Peter, 2026-10-28): `targeting` episodes are held out (test); command and
intelligence episodes take the usual per-document split; recorded per episode as `held_out`.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from pipeline.store import DATA, _keep_version, write_yaml

from .episodes import find_episodes
from .extract import prompt_file
from .natsec import pdf_paragraphs, split_long
from .textclean import clean_text

CORPUS = DATA / "corpus" / "natsec"
OUT = DATA / "store" / "episodes" / "corpus"
ACQ = DATA / "store" / "registry" / "acquired-natsec.yaml"
MIN_CHARS = 2000
PROMPT = "find_episodes.natsec-corpus.v2"     # v1 passed definitions, review summaries and a collection procedure
HELD_OUT_CONTENT = {"targeting"}
NATSEC_CONTENT = {"targeting", "operational-command", "intel-analysis", "intel-oversight", "use-of-force-policy",
                  "cyber-policy"}
DOCTRINE_NOTE = ("This document is doctrine (a manual, directive or policy). A decision point here is a decision the "
                 "doctrine frames for a decider in a concrete situation it describes (a vignette, example, or a rule that "
                 "chooses between named courses): the situation, the courses open, and what it says to weigh. Principles, "
                 "definitions and descriptions of process are not decision points. For criterion "
                 "2 (`choice_stated`), pass only if the doctrine states which course it requires or recommends in that "
                 "situation; otherwise fail it (the candidate is still kept). Criterion 3 passes when the doctrine gives its "
                 "reasons or the factors to weigh.")


def read_text(cid: str) -> tuple[dict, str]:
    raw = (CORPUS / "text" / f"{cid}.txt").read_text(errors="replace")
    head, _, body = raw.partition("\n" + "=" * 80 + "\n")
    h = {}
    for line in head.splitlines():
        k, sep, v = line.partition(": ")
        if sep:
            h[k.strip()] = v.strip()
    return h, body


def normalize_text(cid: str, row: dict) -> tuple[str, list[dict]]:
    """-> (sha12, spans). Text cleaned first (textclean: two-column layout, ligatures, mojibake, hyphenation), then pages
    from form feeds and paragraphs as natsec.normalize (pdf_paragraphs / split_long). sha12 is of the cleaned text, so
    spans from the uncleaned text (episodes found before 2026-10-28 14:30) keep their own file."""
    head, body = read_text(cid)
    body, clean_stats = clean_text(body)
    sha12 = hashlib.sha256(body.encode()).hexdigest()[:12]
    pages = body.split("\f")
    paras = [pdf_paragraphs(t) if row.get("kind") == "pdf" else [q for p in t.split("\n\n") if p.strip()
                                                                  for q in split_long(" ".join(p.split()))]
             for t in pages]
    spans = [{"span": f"src:{sha12}#p{pn}.{i}", "text": t} for pn, ps in enumerate(paras, 1) for i, t in enumerate(ps, 1)]
    out = DATA / "docs" / f"{sha12}.jsonl"
    body_out = "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in spans)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.read_text() != body_out:
        _keep_version(out)
        out.write_text(body_out)
    meta = {"doc": f"data/docs/{sha12}.jsonl", "source_id": cid, "corpus": "natsec-v1", "url": row.get("url"),
            "title": row.get("title"), "collection": row.get("collection"), "kind": row.get("kind"),
            "flags": row.get("flags"), "clean": clean_stats, "pages": len(pages), "paragraphs": len(spans), "chars": len(body),
            "header": head}
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return sha12, spans


def is_doctrine(row: dict) -> bool:
    return row.get("collection") == "doctrine" or str(row.get("collection", "")).startswith("A1 ")


def seed_urls() -> set[str]:
    if not ACQ.exists():
        return set()
    acq = yaml.safe_load(ACQ.read_text()) or {}
    urls = set()
    for rec in (acq.get("sources") or {}).values():
        urls.add(rec.get("url"))
        urls |= {f.get("url") for f in rec.get("files") or []}
    return {u for u in urls if u}


def todo(only=None) -> tuple[list[dict], dict]:
    rows = list(csv.DictReader((CORPUS / "index.csv").open()))
    seeds, skipped, out = seed_urls(), {}, []
    for r in rows:
        cid = r["id"]
        if only and cid not in only:
            continue
        why = ("no text" if r["ok"] != "1" or not (CORPUS / "text" / f"{cid}.txt").exists()
               else "thin_page" if "thin_page" in (r.get("flags") or "")
               else "needs_ocr" if "needs_ocr" in (r.get("flags") or "")
               else f"under {MIN_CHARS} chars" if int(r.get("chars") or 0) < MIN_CHARS
               else "W8b seed source" if r.get("url") in seeds
               else None)
        if why:
            skipped[cid] = why
        else:
            out.append(r)
    return out, skipped


def run_one(row: dict, complete_fn=None) -> dict:
    cid = row["id"]
    t0 = time.time()
    sha12, spans = normalize_text(cid, row)
    tmpl, _, _ = prompt_file(PROMPT)
    head, _ = read_text(cid)
    hdr = "\n".join(f"{k}: {head[k]}" for k in ("TITLE", "CATALOG", "KIND") if k in head)
    doctrine = is_doctrine(row)
    add = tmpl.replace("{{HEADER}}", hdr).replace("{{DOCTRINE}}", DOCTRINE_NOTE if doctrine else "")
    src = {"id": cid, "domain": "natsec-corpus", "refusal_sensitivity": None}
    res = find_episodes(src, spans, complete_fn, addendum=add, relax=("choice_stated",) if doctrine else (),
                        out_dir=OUT)
    eps = res["passed"]
    for e in eps:
        cd = e["content_domain"]
        e["held_out"] = cd in HELD_OUT_CONTENT
        e["natsec"] = cd in NATSEC_CONTENT
        if doctrine:
            e["tags"] = ["doctrine-derived"]
            if "choice_stated" in e.get("relaxed", []):
                e["gold_tier"] = "model-solved"
        if cd in ("targeting", "use-of-force-policy"):              # force involved (brief W8b)
            e["refusal_sensitivity"] = "high"
    write_yaml(OUT / f"{cid}.yaml", {"source": cid, "doc": f"data/docs/{sha12}.jsonl", "url": row.get("url"),
                                     "title": row.get("title"), "collection": row.get("collection"),
                                     "doctrine": doctrine, "prompt": f"find_episodes.v1+{PROMPT}", "episodes": eps})
    return {"id": cid, "collection": row.get("collection"), "passed": len(eps), "rejected": len(res["rejected"]),
            "refusals": sum("refusal" in r["failed"] for r in res["rejected"]),
            "errors": sum("finder-error" in r["failed"] for r in res["rejected"]),
            "domains": [e["content_domain"] for e in eps], "seconds": round(time.time() - t0)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--redo", action="store_true", help="re-run documents that already have an output")
    ap.add_argument("--dry-run", action="store_true", help="list what would run")
    a = ap.parse_args(argv)
    rows, skipped = todo(set(a.only) if a.only else None)
    OUT.mkdir(parents=True, exist_ok=True)
    if not a.redo:
        rows = [r for r in rows if not (OUT / f"{r['id']}.yaml").exists()]
    rows.sort(key=lambda r: -int(r.get("chars") or 0))          # longest first: they set the wall time
    print(f"{len(rows)} documents to run, {len(skipped)} skipped", file=sys.stderr)
    if a.dry_run:
        print(json.dumps({"skipped_by_reason": {w: sum(v == w for v in skipped.values()) for w in set(skipped.values())}}))
        return 0

    def safe(r):
        try:
            out = run_one(r)
        except Exception as e:                                        # noqa: BLE001 - one bad document must not sink the run
            out = {"id": r["id"], "error": f"{type(e).__name__}: {e}"[:300]}
        print(json.dumps(out, ensure_ascii=False), flush=True)
        return out

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(safe, rows))
    prev = json.loads((OUT / "summary.json").read_text()) if (OUT / "summary.json").exists() else {"documents": {}}
    prev["documents"].update({r["id"]: r for r in res})
    prev["skipped"] = skipped
    docs = prev["documents"].values()
    prev["totals"] = {"documents": len(prev["documents"]), "episodes": sum(d.get("passed", 0) for d in docs),
                      "refusals": sum(d.get("refusals", 0) for d in docs), "errors": sum(1 for d in docs if "error" in d)}
    (OUT / "summary.json").write_text(json.dumps(prev, indent=1, ensure_ascii=False))
    print(json.dumps(prev["totals"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
