"""PDF -> paragraphs (via ingest.normalize, which runs pypdf in a separate interpreter: BENCHBOOK_PDF_PYTHON)."""
from __future__ import annotations
import json
from pathlib import Path
from pipeline.ingest.normalize import pages_for
from .net import raw_path
from .crawl import OUT, load

TEXT = OUT / "text"


def paragraphs(cn: str) -> list[dict]:
    """-> [{span, text}] with span ids src:<sha12>#p<page>.<para> exactly as ingest.normalize makes them."""
    f = TEXT / f"{cn}.jsonl"
    if f.exists():
        return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    sha = load()[cn]["sha256"]
    pages = pages_for("pdf", raw_path(sha))
    spans = [{"span": f"src:{sha[:12]}#p{pn}.{i}", "text": t} for pn, ps in enumerate(pages, 1) for i, t in enumerate(ps, 1)]
    TEXT.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in spans) + "\n")
    return spans
