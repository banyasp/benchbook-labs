"""Crawl OHA listing pages -> article -> PDF, via acquire.fetch (>=1.5 s apart). Index: results/h3-pilot/index.json
(case no -> {article, pdf_url, sha256}). Stops (does not work around) on any HTTP error other than 404 for an article."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from urllib.parse import urljoin
from pipeline.ingest.acquire import RAW
from .net import get, raw_path

OUT = Path(__file__).resolve().parents[2] / "results" / "h3-pilot"
BASE = "https://www.energy.gov"
IDX = OUT / "index.json"


def load():
    return json.loads(IDX.read_text()) if IDX.exists() else {}


def save(idx):
    IDX.write_text(json.dumps(idx, indent=1, sort_keys=True))


def case_no(slug: str) -> str | None:
    m = re.match(r"/oha/articles/([a-z]{3})-(\d\d)-(\d{4})-matter", slug)
    return f"{m[1].upper()}-{m[2]}-{m[3]}" if m else None


def article_pdf(idx, cn, article):
    e = idx.setdefault(cn, {"article": BASE + article})
    if e.get("sha256"):
        return e
    try:
        h = raw_path(get(e["article"])).read_text(errors="ignore")
    except RuntimeError as ex:
        e["error"] = str(ex); save(idx)
        if "404" in str(ex):
            return e
        raise
    pdfs = re.findall(r'href="([^"]*\.pdf)"', h)
    if not pdfs:
        e["error"] = "no pdf link"; save(idx); return e
    e["pdf_url"] = urljoin(BASE, pdfs[0])
    e["sha256"] = get(e["pdf_url"])
    e.pop("error", None)
    save(idx)
    return e


def crawl_listing(pages):
    idx = load()
    for p in pages:
        h = raw_path(get(f"{BASE}/oha/listings/security-cases?page={p}")).read_text(errors="ignore")
        for slug in sorted(set(re.findall(r'href="(/oha/articles/[^"]*)"', h))):
            cn = case_no(slug)
            if cn:
                idx.setdefault(cn, {"article": BASE + slug, "listing_page": p})
        save(idx)
        print("listing", p, len(idx), flush=True)
    return idx


def crawl_docs(only=None):
    idx = load()
    for cn in sorted(idx, reverse=True):
        if only and cn not in only:
            continue
        if not idx[cn].get("sha256") and "error" not in idx[cn]:
            article_pdf(idx, cn, idx[cn]["article"][len(BASE):])
            print("doc", cn, idx[cn].get("sha256", "")[:12], idx[cn].get("error", ""), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "listing":
        crawl_listing(range(int(sys.argv[2]), int(sys.argv[3])))
    else:
        crawl_docs()


def targeted(cns):
    """Fetch specific cited decisions: from the index if listed, else guess the article slug (404 is recorded, not worked around)."""
    idx = load()
    for cn in cns:
        if idx.get(cn, {}).get("sha256"):
            continue
        slug = f"/oha/articles/{cn.lower()}-matter-personnel-security-hearing"
        if cn in idx and idx[cn].get("article"):
            slug = idx[cn]["article"][len(BASE):]
        idx.pop(cn, None) if "error" in idx.get(cn, {}) else None
        try:
            e = article_pdf(idx, cn, slug)
        except RuntimeError as ex:
            print("FAIL", cn, ex, flush=True); continue
        print("doc", cn, e.get("sha256", "")[:12], e.get("error", ""), flush=True)
