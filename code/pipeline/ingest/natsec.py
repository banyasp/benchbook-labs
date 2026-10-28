"""W8b acquire for the national-security sources (BUILD-BRIEF-v2.4 §W8b). Acquire only: extraction waits for W4a + the
v2 option rules.

    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec acquire     # fetch the seed, record blocks
    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec status
    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec ingest-manual   # files Peter downloaded by hand
    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec normalize       # raw -> data/docs/<sha12>.jsonl (+ .meta.json)

Blocked sources: run fetch-blocked-natsec.sh on a laptop, copy its output into data/raw/manual/ (with manifest.tsv),
then ingest-manual stores each listed file in the raw store and moves the source from blocked to acquired.

Seed: sources-natsec.seed.yaml. Same polite fetcher as pipeline.ingest.acquire (descriptive User-Agent, delay,
immutable raw store). A non-200 is recorded, never worked around (no UA spoofing, no alternative routes beyond the
mirrors the catalog itself lists). `follow:` fetches same-host links matching a regex (multi-page reports).
Writes data/store/registry/acquired-natsec.yaml and results/SOURCES-BLOCKED-2026-10-28.md.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml

import json
import subprocess

from pipeline.store import DATA, ROOT, _keep_version, write_yaml

from .acquire import USER_AGENT, fetch

SEED = Path(__file__).with_name("sources-natsec.seed.yaml")
ACQ = DATA / "store" / "registry" / "acquired-natsec.yaml"
BLOCKED = ROOT / "results" / "SOURCES-BLOCKED-2026-10-28.md"
MAX_FOLLOW = 40


def _links(html: str, base: str, pattern: str) -> list[str]:
    host = urlparse(base).netloc
    out = []
    for href in re.findall(r'href="([^"#]+)"', html):
        u = urljoin(base, href)
        if urlparse(u).netloc == host and re.search(pattern, u) and u not in out:
            out.append(u)
    return out[:MAX_FOLLOW]


def acquire(delay: float = 1.5) -> dict:
    seed = yaml.safe_load(SEED.read_text())
    d = seed.get("defaults", {})
    acq = yaml.safe_load(ACQ.read_text()) if ACQ.exists() else {"sources": {}, "blocked": {}}
    for s in seed["sources"]:
        if s["id"] in acq["sources"]:
            continue
        rec = {**{k: d[k] for k in ("split", "held_out_domain", "refusal_sensitivity", "license")}, **s,
               "files": [], "tags": (["ocr"] if s.get("ocr") else [])}
        try:
            sha = fetch(s["url"])
            rec["files"].append({"url": s["url"], "sha256": sha})
            if s.get("follow"):
                html = (DATA / "raw" / sha).read_bytes().decode("utf-8", "replace")
                for u in _links(html, s["url"], s["follow"]):
                    time.sleep(delay)
                    try:
                        rec["files"].append({"url": u, "sha256": fetch(u)})
                    except Exception as e:
                        rec.setdefault("partial_failures", []).append({"url": u, "error": str(e)[:200]})
            acq["sources"][s["id"]] = rec
            acq["blocked"].pop(s["id"], None)
            print(f"ok      {s['id']}: {len(rec['files'])} file(s)")
        except Exception as e:
            acq["blocked"][s["id"]] = {"url": s["url"], "title": s["title"], "family": s["family"],
                                       "error": str(e)[:200], "tried_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())}
            print(f"BLOCKED {s['id']}: {str(e)[:120]}")
        time.sleep(delay)
    write_yaml(ACQ, acq)
    write_blocked(acq)
    return acq


def write_blocked(acq: dict):
    lines = ["# Sources that could not be fetched from the EC2 box (2026-10-28)", "",
             "W8b access rule: no user-agent spoofing or workarounds. Please download these by hand into",
             "`data/raw/manual/` (keep the original file name; add a line to `data/raw/manual/README.md` with the URL).",
             f"Fetcher User-Agent: `{USER_AGENT}`.", "",
             "| Source id | Family | Title | URL | Error |", "|---|---|---|---|---|"]
    for sid, b in sorted(acq["blocked"].items()):
        lines.append(f"| {sid} | {b['family']} | {b['title']} | {b['url']} | {b['error']} |")
    partial = [(sid, f) for sid, s in acq["sources"].items() for f in s.get("partial_failures", [])]
    if partial:
        lines += ["", "## Partial failures (main page fetched, a linked page was not)", "", "| Source id | URL | Error |",
                  "|---|---|---|"] + [f"| {sid} | {f['url']} | {f['error']} |" for sid, f in partial]
    if not acq["blocked"] and not partial:
        lines += ["", "None: every seeded source fetched."]
    BLOCKED.parent.mkdir(parents=True, exist_ok=True)
    BLOCKED.write_text("\n".join(lines) + "\n")


MANUAL = DATA / "raw" / "manual"


def ingest_manual() -> dict:
    """Register hand-downloaded files listed in data/raw/manual/manifest.tsv (source_id, url, file)."""
    from .acquire import store_raw
    seed = {s["id"]: s for s in yaml.safe_load(SEED.read_text())["sources"]}
    d = yaml.safe_load(SEED.read_text()).get("defaults", {})
    acq = yaml.safe_load(ACQ.read_text()) if ACQ.exists() else {"sources": {}, "blocked": {}}
    rows = [ln.split("\t") for ln in (MANUAL / "manifest.tsv").read_text().splitlines()[1:] if ln.strip()]
    for sid, url, fname in rows:
        if sid not in seed:
            print(f"skip    {fname}: unknown source id {sid}")
            continue
        f = MANUAL / fname
        if not f.exists():
            print(f"missing {fname}")
            continue
        sha = store_raw(f.read_bytes(), {"url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(f.stat().st_mtime)), "acquired_by": "manual download (Peter)",
                        "manual_file": fname})
        s = seed[sid]
        rec = acq["sources"].setdefault(sid, {**{k: d[k] for k in ("split", "held_out_domain",
                                        "refusal_sensitivity", "license")}, **s, "files": [],
                                        "tags": (["ocr"] if s.get("ocr") else []) + ["manual"]})
        if not any(x["sha256"] == sha for x in rec["files"]):
            rec["files"].append({"url": url, "sha256": sha})
        acq["blocked"].pop(sid, None)
        print(f"stored  {sid}: {fname} -> raw/{sha[:12]}")
    write_yaml(ACQ, acq)
    write_blocked(acq)
    return acq


def status():
    acq = yaml.safe_load(ACQ.read_text()) if ACQ.exists() else {"sources": {}, "blocked": {}}
    fams = sorted({s["family"] for s in acq["sources"].values()})
    print(f"acquired {len(acq['sources'])} sources ({sum(len(s['files']) for s in acq['sources'].values())} files), "
          f"{len(fams)} families; blocked {len(acq['blocked'])}")
    for sid, s in acq["sources"].items():
        print(f"  {sid:26} {s['family']:26} {s['content_domain']:20} files={len(s['files'])} tags={s['tags']}")
    for sid, b in acq["blocked"].items():
        print(f"  BLOCKED {sid:18} {b['error'][:80]}")


# ---------------------------------------------------------------- normalize (W8b)
DOCS_REG = DATA / "store" / "registry" / "normalized-natsec.yaml"
SCRATCH = DATA / "scratch" / "ocr"
# main-content container per site; first selector that matches wins (strips menus, share widgets, footers)
CONTENT_SELECTORS = ["#content", "section.col-md-9", "article", "main", "body"]
BLOCK = ["h1", "h2", "h3", "h4", "p", "li", "pre", "td"]
# globalsecurity.org page boilerplate that survives inside #content
BOILER = re.compile(r"^(Share on|Share|Update|Print|Tweet|Email|Facebook|Twitter)$", re.I)


def html_blocks(data: bytes) -> list[str]:
    """HTML -> paragraphs: main-content container only; <pre> split on blank lines; nested blocks not duplicated."""
    from bs4 import BeautifulSoup
    from .normalize import clean
    soup = BeautifulSoup(data, "html.parser")
    for t in soup(["script", "style", "nav", "header", "footer", "form", "noscript"]):
        t.decompose()
    root = next((r for sel in CONTENT_SELECTORS if (r := soup.select_one(sel)) is not None), soup)
    out: list[str] = []
    for e in root.find_all(BLOCK):
        if e.name != "pre" and e.find(BLOCK):
            continue
        if e.name == "pre":
            out += [clean(b) for b in re.split(r"\n[ \t]*\n", e.get_text())]
        else:
            out.append(clean(e.get_text(" ")))
    return [t for t in out if t and not BOILER.match(t)]


MAX_PARA = 1400
_SENT = re.compile(r"(?<=[.!?;:\"\u201d)]) (?=(?:\d{1,3}\. |[A-Z\u00c4\u00d6\u00dc(\u201c\"]))")
_NUMBERED = re.compile(r"(?<=[.!?;:]) (?=\d{1,3}\. [A-Z])")


def split_long(par: str, limit: int = MAX_PARA) -> list[str]:
    """Deterministically split an over-long paragraph (pdftotext often yields one block per page) at numbered-paragraph
    markers first, then at sentence boundaries, packing chunks up to `limit` characters."""
    if len(par) <= limit:
        return [par]
    pieces: list[str] = []
    for blk in _NUMBERED.split(par):
        sents = _SENT.split(blk) if len(blk) > limit else [blk]
        cur = ""
        for s in sents:
            if cur and len(cur) + 1 + len(s) > limit:
                pieces.append(cur)
                cur = s
            else:
                cur = f"{cur} {s}".strip()
        if cur:
            pieces.append(cur)
    return pieces


def pdf_paragraphs(page_text: str) -> list[str]:
    from .normalize import split_paragraphs
    out = []
    for p in split_paragraphs(page_text):
        if re.fullmatch(r"\d{1,4}|Page \d+( of \d+)?", p):
            continue
        out += split_long(p)
    return out


def pdf_page_texts(path: Path) -> list[str]:
    """Text layer per page via poppler pdftotext (reading order, no layout)."""
    txt = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True, check=True).stdout
    pages = txt.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def normalize_source(sid: str, rec: dict, data: Path = DATA) -> list[dict]:
    """One doc per file (reading order = acquisition order). Returns the per-file entries for the registry."""
    from . import ocr
    entries = []
    for order, f in enumerate(rec["files"], 1):
        sha = f["sha256"]
        sha12 = sha[:12]
        raw = data / "raw" / sha
        head = raw.read_bytes()[:5]
        meta = {"doc": f"data/docs/{sha12}.jsonl", "source_id": sid, "family": rec["family"], "order": order,
                "url": f["url"], "sha256": sha, "language": rec.get("language", "en"), "tags": list(rec.get("tags", [])),
                "content_domain": rec.get("content_domain")}
        if meta["language"] != "en":
            meta["translation_note"] = (f"source language {meta['language']}; extraction translates to English "
                                        "(R60: record the translation in scenario provenance)")
        if head == b"%PDF-":
            pages = pdf_page_texts(raw)
            force_all = bool(rec.get("ocr"))
            todo = [i + 1 for i, t in enumerate(pages) if force_all or ocr.needs_ocr(t)]
            used = []
            if todo:
                got = ocr.ocr_pages(raw, todo, SCRATCH / sha12)
                for p, t in got.items():
                    if ocr.page_quality(t)["score"] >= ocr.page_quality(pages[p - 1])["score"] or not pages[p - 1].strip():
                        pages[p - 1] = t
                        used.append(p)
                meta["ocr"] = {**ocr.tool_versions(), "pages_ocr": used, "pages_attempted": len(todo),
                               "scratch": f"data/scratch/ocr/{sha12}"}
                if used and (force_all or len(used) >= 0.1 * len(pages)):
                    meta["tags"] = sorted(set(meta["tags"]) | {"ocr"})
            weak = [i + 1 for i, t in enumerate(pages) if ocr.needs_ocr(t)]
            meta["weak_pages_after"] = weak
            meta["pages"] = len(pages)
            paras = [pdf_paragraphs(t) for t in pages]
        else:
            paras = [html_blocks(raw.read_bytes())]
            meta["pages"] = 1
        lines = [json.dumps({"span": f"src:{sha12}#p{pn}.{i}", "text": t}, ensure_ascii=False)
                 for pn, ps in enumerate(paras, 1) for i, t in enumerate(ps, 1)]
        body = "\n".join(lines) + "\n"
        out = data / "docs" / f"{sha12}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.exists() or out.read_text() != body:
            _keep_version(out)
            out.write_text(body)
        meta["paragraphs"] = len(lines)
        meta["chars"] = sum(len(t) for ps in paras for t in ps)
        mp = out.with_suffix(".meta.json")
        mj = json.dumps(meta, indent=1, ensure_ascii=False)
        if not mp.exists() or mp.read_text() != mj:
            _keep_version(mp)
            mp.write_text(mj)
        entries.append({k: meta[k] for k in ("doc", "order", "url", "pages", "paragraphs", "tags")}
                       | ({"ocr_pages": meta["ocr"]["pages_ocr"]} if "ocr" in meta else {})
                       | ({"weak_pages_after": meta["weak_pages_after"]} if meta.get("weak_pages_after") else {}))
        print(f"{sid:26} {sha12} #{order:<2} pages={meta['pages']:<4} paras={len(lines):<5} tags={meta['tags']}"
              + (f" ocr={len(meta['ocr']['pages_ocr'])}/{meta['pages']}" if "ocr" in meta else ""))
    return entries


def normalize_all(only: str | None = None) -> dict:
    acq = yaml.safe_load(ACQ.read_text())
    reg = {"tool": "pipeline.ingest.natsec normalize", "sources": {}}
    for sid, rec in acq["sources"].items():
        if only and sid != only:
            continue
        reg["sources"][sid] = {"family": rec["family"], "language": rec.get("language", "en"),
                               "docs": normalize_source(sid, rec)}
    write_yaml(DOCS_REG, reg)
    return reg


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["acquire", "status", "ingest-manual", "normalize"])
    a = ap.parse_args(argv)
    {"acquire": acquire, "status": status, "ingest-manual": ingest_manual, "normalize": normalize_all}[a.cmd]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
