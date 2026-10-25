"""Indirectness check for flips (design 4a): the new fact(s) must not paraphrase the would_change `if` text.

score = content-word recall of the `if` text in the new text (crude stemming), plus the longest run of `if`
content words that also appear contiguously (same order) in the new text. A realization passes when
recall <= MAX_RECALL and run <= MAX_RUN. The score is logged on every flip (lineage.detail).
"""
from __future__ import annotations

import re

MAX_RECALL = 0.5      # at most half of the `if` content words may reappear in the new fact(s)
MAX_RUN = 2           # no contiguous run of 3+ shared content words

STOP = set("""a an the of to in on at by for from with without and or but nor not no is are was were be been being it its
this that these those there their his her he she they them we you i as if than then so such can could may might will would
shall should must do does did done has have had having into onto over under up down out off about after before during while
until per via any all each other some more most less least only also still yet already""".split())


def stem(w: str) -> str:
    for suf in ("ingly", "ing", "ed", "es", "ly", "s", "e"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def content_tokens(s: str) -> list[str]:
    return [stem(w) for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]


def overlap(new_text: str, if_text: str) -> dict:
    a, b = content_tokens(if_text), content_tokens(new_text)
    if not a:
        return {"recall": 0.0, "run": 0, "pass": True}
    bs = set(b)
    recall = sum(1 for t in set(a) if t in bs) / len(set(a))
    run = 0                                   # longest contiguous run of `a` found contiguously in `b`
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            run = max(run, k)
    return {"recall": round(recall, 3), "run": run, "pass": recall <= MAX_RECALL and run <= MAX_RUN}


def jaccard(a: str, b: str) -> float:
    x, y = set(re.findall(r"[a-z0-9]+", a.lower())), set(re.findall(r"[a-z0-9]+", b.lower()))
    return len(x & y) / len(x | y) if x | y else 1.0
