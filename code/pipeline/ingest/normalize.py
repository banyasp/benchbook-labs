"""Normalize: raw PDF / HTML / eCFR XML -> data/docs/<sha12>.jsonl, one paragraph per line
{"span": "src:<sha12>#p<page>.<para>", "text": ...}. Deterministic: re-running yields identical bytes.

PDF text comes from pypdf run in a *separate* interpreter (env BENCHBOOK_PDF_PYTHON) via pdf_text.py, because the
main venv has no PDF library and must not be modified. Paragraphs = blank-line-separated blocks of a page's text;
"- N -" page-number lines are dropped; wrapped lines are joined. HTML/XML documents are one "page" (p1).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline.store import DATA, _keep_version

PDF_TEXT = Path(__file__).with_name("pdf_text.py")
PAGE_NO = re.compile(r"^-\s*\d+\s*-$")


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def pdf_pages(path: Path) -> list[str]:
    py = os.environ.get("BENCHBOOK_PDF_PYTHON")
    if not py:
        raise RuntimeError("set BENCHBOOK_PDF_PYTHON to an interpreter that has pypdf (see ingest/README.md)")
    out = subprocess.run([py, "-I", str(PDF_TEXT), str(path)], capture_output=True, text=True, check=True).stdout
    return [p["text"] for p in sorted(json.loads(out), key=lambda p: p["page"])]


def split_paragraphs(page_text: str) -> list[str]:
    out = []
    for block in re.split(r"\n[ \t]*\n", page_text):
        t = clean(block)
        if t and not PAGE_NO.match(t):
            out.append(t)
    return out


def xml_paragraphs(data: bytes) -> list[str]:
    root = ET.fromstring(data)
    out: list[str] = []

    def text(e):
        return clean("".join(e.itertext()))

    def walk(e):
        if e.tag == "EXAMPLE":
            out.append(clean(" ".join(text(c) for c in e)))
            return
        if e.tag in ("HEAD", "P", "PSPACE"):
            out.append(text(e))
            return
        for c in e:
            walk(c)

    walk(root)
    return [p for p in out if p]


def html_paragraphs(data: bytes) -> list[str]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(data, "html.parser")
    for t in soup(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    return [t for t in (clean(e.get_text(" ")) for e in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"])) if t]


def pages_for(fmt: str, raw_path: Path) -> list[list[str]]:
    """-> list of pages, each a list of paragraphs."""
    if fmt == "pdf":
        return [split_paragraphs(t) for t in pdf_pages(raw_path)]
    data = raw_path.read_bytes()
    if fmt == "xml":
        return [xml_paragraphs(data)]
    if fmt == "html":
        return [html_paragraphs(data)]
    raise ValueError(f"unknown format {fmt}")


def normalize(sha256: str, fmt: str, data: Path = DATA) -> Path:
    sha12 = sha256[:12]
    pages = pages_for(fmt, data / "raw" / sha256)
    lines = [json.dumps({"span": f"src:{sha12}#p{pn}.{i}", "text": t}, ensure_ascii=False)
             for pn, paras in enumerate(pages, 1) for i, t in enumerate(paras, 1)]
    body = "\n".join(lines) + "\n"
    out = data / "docs" / f"{sha12}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.read_text() != body:
        _keep_version(out)
        out.write_text(body)
    return out


def load_spans(sha12: str, data: Path = DATA) -> list[dict]:
    return [json.loads(l) for l in (data / "docs" / f"{sha12}.jsonl").read_text().splitlines() if l.strip()]


if __name__ == "__main__":
    print(normalize(sys.argv[1], sys.argv[2]))
