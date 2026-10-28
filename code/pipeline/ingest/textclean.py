"""Clean `pdftotext -layout` text from the natsec corpus before it is split into spans (Peter, 2026-10-28).

corpus_fetch.py extracted PDFs with `pdftotext -layout`, which keeps the page geometry: on a two-column page each line
holds a slice of the left column, a gap, then a slice of the right column, so reading a line straight across
interleaves two texts (36% of the corpus, mostly *Studies in Intelligence*). The raw PDFs are on Peter's Mac, so this
repairs the layout text instead of re-extracting:

- `decolumnize(page)`: find the page's gutter (the column where the right-hand text starts on many lines, after a gap),
  split each line there, and emit each run of two-column lines as all left halves, then all right halves. Lines that
  cross the gutter (titles, full-width paragraphs, tables) end a run and stay in place.
- `fix_chars`: ligatures (ﬁ -> fi), common UTF-8-as-cp1252 mojibake (â€™ -> ’), control characters, `(cid:NN)`.
- `dehyphenate`: `acknowl-\\nedging` -> `acknowledging` (a lowercase letter must follow; `50-\\nyear` keeps its hyphen);
  `rejoin`: on two-column pages, blank lines inside a sentence (left by the other column's longer text) are closed.

The corpus files themselves are never changed; cleaned text goes only into data/docs spans. `clean_text` returns
stats so the change is visible per document.
"""
from __future__ import annotations

import re
from collections import Counter

GAP_MIN = 3                 # spaces between the columns
TOL = 3                     # right-column starts within +-TOL of the gutter count as one column
INDENT = 8                  # a right-column line may start up to this far past the gutter (paragraph indent, heading)
MIN_TWO_COL_LINES = 6       # a page needs this many split lines ...
MIN_TWO_COL_SHARE = 0.25    # ... and this share of its text lines to be treated as two-column
LEFT_MIN, RIGHT_MAX = 0.25, 0.80   # the gutter lies within this part of the page width

LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
MOJIBAKE = {"â€™": "’", "â€˜": "‘", "â€œ": "“", "â€\x9d": "”", "â€”": "—", "â€“": "–", "â€¦": "…", "Â ": " ", "Â§": "§",
            "Ã©": "é", "Ã¨": "è", "Ã¶": "ö", "Ã¼": "ü", "Ã¤": "ä"}
CTRL = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f�]")
CID = re.compile(r"\(cid:\d+\)")
RUN = re.compile(rf" {{{GAP_MIN},}}(?=\S)")


def fix_chars(text: str) -> tuple[str, dict]:
    st = Counter()
    for a, b in {**LIGATURES, **MOJIBAKE}.items():
        n = text.count(a)
        if n:
            text = text.replace(a, b)
            st["ligature" if a in LIGATURES else "mojibake"] += n
    text, n = CID.subn("", text)
    st["cid"] += n
    text, n = CTRL.subn("", text)
    st["control"] += n
    return text, dict(st)


def gutter(lines: list[str]) -> int | None:
    """Most common start column of a right-hand text run (after a gap) inside the gutter band, if it is common enough."""
    width = max((len(l.rstrip()) for l in lines), default=0)
    if width < 40:
        return None
    starts = Counter()
    for l in lines:
        for m in RUN.finditer(l.rstrip()):
            x = m.end()
            if LEFT_MIN * width <= x <= RIGHT_MAX * width and l[:m.start()].strip():
                starts[x] += 1
    if not starts:
        return None
    best = max(starts, key=lambda x: sum(starts[y] for y in range(x - TOL, x + TOL + 1)))
    n = sum(starts[y] for y in range(best - TOL, best + TOL + 1))
    text_lines = sum(1 for l in lines if l.strip())
    return best if n >= MIN_TWO_COL_LINES and n >= MIN_TWO_COL_SHARE * text_lines else None


def split_line(l: str, g: int) -> tuple[str, str] | None:
    """(left, right) if `l` fits a two-column layout with its gutter at g, else None (the line crosses the gutter)."""
    l = l.rstrip()
    if not l.strip():
        return "", ""
    if len(l) < g - TOL:                                   # left text only
        return l, ""
    if not l[:max(g - TOL, 0)].strip():                    # right text only (left column empty here)
        return "", l
    for m in RUN.finditer(l):                              # leftmost gap ending at the gutter or a little past it
        if g - TOL <= m.end() <= g + INDENT:
            return l[:m.start()], l[m.end():]
    return None


def squash(t: str) -> str:
    """Justified text stretches spaces between words (`interoperability     and     equipment`)."""
    return " ".join(t.split())


def decolumnize(page: str) -> tuple[str, bool]:
    lines = page.split("\n")
    g = gutter(lines)
    if g is None:
        return page, False
    out, left, right = [], [], []

    def flush():
        if left or right:
            out.extend(left)
            out.append("")                                 # column break = paragraph break
            out.extend(right)
            left.clear()
            right.clear()

    for l in lines:
        s = split_line(l, g)
        if s is None:
            flush()
            out.append(squash(l))
        else:
            left.append(squash(s[0]))
            right.append(squash(s[1]))
    flush()
    return "\n".join(out), True


def dehyphenate(text: str) -> tuple[str, int]:
    text = re.sub(r"(\d)-\n[ \t]*([a-z])", r"\1-\2", text)                # 50-\nyear -> 50-year
    return re.subn(r"([A-Za-z])-\n[ \t]*([a-z])", r"\1\2", text)


def rejoin(text: str) -> str:
    """A column cut short by the other column's longer text leaves blank lines inside a sentence: join them when the
    line before ends mid-sentence and the next starts lowercase."""
    return re.sub(r"([a-z,;:])[ \t]*\n(?:[ \t]*\n)+[ \t]*([a-z])", r"\1\n\2", text)


def clean_text(body: str) -> tuple[str, dict]:
    """Whole document (pages separated by form feeds) -> (clean text, stats)."""
    body, st = fix_chars(body)
    pages, n2 = [], 0
    for p in body.split("\f"):
        p2, two = decolumnize(p)
        n2 += two
        p2, nh = dehyphenate(rejoin(p2) if two else p2)
        st["dehyphenated"] = st.get("dehyphenated", 0) + nh
        pages.append(p2)
    st["pages"] = len(pages)
    st["two_column_pages"] = n2
    return "\f".join(pages), st
