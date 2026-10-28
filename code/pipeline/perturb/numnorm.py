"""Numeric drift check for restyle (R43): numbers, dates, times and amounts in a decisive fact must survive unchanged.

`numbers(text)` -> set of canonical values (strings). Normalizes formatting: "$1,200" == "1200 dollars" == "1.2k"; "40%" ==
"40 percent"; "twelve" == "12"; "March 3, 2025" == "3 March 2025" == "3/3/2025"; "2:30 pm" == "14:30"; "three-quarters" is not
handled (left as no number). The values 0 and 1 are ignored (they collide with "none", "one of", "a").
"""
from __future__ import annotations

import re
from decimal import Decimal

WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                    "fifteen sixteen seventeen eighteen nineteen twenty".split())}
WORDS.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "dozen": 12})
MONTHS = {m: i for i, m in enumerate("january february march april may june july august september october november december".split(), 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items()) if m != "may"})
MONTHS["sept"] = 9
SCALE = {"k": 10**3, "thousand": 10**3, "m": 10**6, "mm": 10**6, "million": 10**6, "b": 10**9, "billion": 10**9, "hundred": 100}
TIME = re.compile(r"\b(\d{1,2}):(\d{2})(?:\s*([ap])\.?m\.?)?", re.I)
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?:st|nd|rd|th)?(?:\s*(k|m{1,2}|b|thousand|million|billion|hundred)\b)?", re.I)
WORD = re.compile(r"\b(" + "|".join(sorted(WORDS, key=len, reverse=True)) + r")(?:[- ](one|two|three|four|five|six|seven|eight|nine))?\b"
                  r"(?:\s+(thousand|million|billion|hundred)\b)?", re.I)
MONTH = re.compile(r"\b(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\b\.?", re.I)


def _canon(x: Decimal) -> str:
    return format(x.normalize(), "f")


def numbers(text: str) -> set[str]:
    t = text.replace("‑", "-").replace("−", "-")
    out: set[Decimal] = set()

    def times(m):
        h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower()
        if ap == "p" and h < 12:
            h += 12
        if ap == "a" and h == 12:
            h = 0
        out.update({Decimal(h), Decimal(mi)})
        return " "
    t = TIME.sub(times, t)

    def months(m):
        name = m.group(1).lower()
        if name == "may" and not re.match(r"\s*\d", t[m.end():]) and not re.search(r"\d\s*$", t[:m.start()]):
            return m.group(0)                       # the verb "may"
        out.add(Decimal(MONTHS[name]))
        return " "
    t = MONTH.sub(months, t)

    def words(m):
        v = Decimal(WORDS[m.group(1).lower()])
        if m.group(2):
            v += WORDS[m.group(2).lower()]
        if m.group(3):
            v *= SCALE[m.group(3).lower()]
        out.add(v)
        return " "
    t = WORD.sub(words, t)
    for m in NUM.finditer(t):
        v = Decimal(m.group(1).replace(",", "") + (m.group(2) or ""))
        if m.group(3):
            v *= SCALE[m.group(3).lower()]
        out.add(v)
    return {_canon(v) for v in out if v not in (0, 1)}


def drift(original: str, restyled: str) -> dict:
    a, b = numbers(original), numbers(restyled)
    return {"missing": sorted(a - b, key=float), "added": sorted(b - a, key=float), "ok": a == b}
