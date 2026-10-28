"""OCR helper for scanned PDFs (W8b). Rasterises selected pages with pdftoppm and reads them with tesseract into a
scratch directory; never touches data/raw/. Also holds the text-layer quality screen used to decide which pages need OCR.

    page_quality(text) -> dict(score, tokens, ...)     higher = more like running English/German prose
    needs_ocr(text)    -> bool                          empty or garbage text layer
    ocr_pages(pdf, pages, scratch) -> {page: text}      pdftoppm -r 300 + tesseract -l eng --psm 1
    tool_versions()    -> {"tesseract": "...", "pdftoppm": "..."}  recorded in the doc meta
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

DPI = 300
LANG = "eng"
PSM = "1"
MIN_SCORE = 0.55


def page_quality(text: str) -> dict:
    toks = re.findall(r"\S+", text)
    n = len(toks)
    if n == 0:
        return {"score": 0.0, "tokens": 0}
    words = [t for t in toks if re.fullmatch(r"[A-Za-zÄÖÜäöüß][a-zäöüß]*[,.;:]?|[A-Z]{2,}[,.;:]?|[0-9][0-9,.\-/]*", t)]
    wordlike = [t for t in words if len(t.strip(",.;:")) >= 2 or t.strip(",.;:") in ("a", "A", "I")]
    vowels = [t for t in toks if re.search(r"[aeiouäöüAEIOU]", t)]
    single = sum(1 for t in toks if len(t.strip(",.;:")) <= 1)
    score = 0.5 * len(wordlike) / n + 0.5 * len(vowels) / n - 0.6 * single / n
    return {"score": round(max(score, 0.0), 3), "tokens": n, "single_char_frac": round(single / n, 3)}


def needs_ocr(text: str) -> bool:
    q = page_quality(text)
    alnum = sum(c.isalnum() for c in text)
    return alnum < 40 or q["score"] < MIN_SCORE


def tool_versions() -> dict:
    t = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
    p = subprocess.run(["pdftoppm", "-v"], capture_output=True, text=True)
    return {"tesseract": (t.stdout or t.stderr).splitlines()[0].strip(),
            "pdftoppm": (p.stderr or p.stdout).splitlines()[0].strip(), "dpi": DPI, "lang": LANG, "psm": PSM}


def ocr_pages(pdf: Path, pages: list[int], scratch: Path) -> dict[int, str]:
    scratch.mkdir(parents=True, exist_ok=True)
    out = {}
    for p in pages:
        base = scratch / f"{pdf.name[:12]}-p{p}"
        txt = base.with_suffix(".txt")
        if not txt.exists():
            subprocess.run(["pdftoppm", "-r", str(DPI), "-f", str(p), "-l", str(p), "-png", "-singlefile", str(pdf), str(base)],
                           check=True, capture_output=True)
            subprocess.run(["tesseract", str(base.with_suffix(".png")), str(base), "-l", LANG, "--psm", PSM],
                           check=True, capture_output=True)
            base.with_suffix(".png").unlink(missing_ok=True)
        out[p] = txt.read_text(errors="replace")
    return out
