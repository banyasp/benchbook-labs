"""Find sentences in OHA decisions that cite another OHA decision (Case No. PSH-xx-xxxx / TSO / VSO)."""
from __future__ import annotations
import json, re
from .crawl import OUT, load
from .text import paragraphs

_C = re.compile(r"\b(PSH|TSO|VSO)\s*-\s*(\d\d)\s*-\s*(\d{4})\b")


class _Cite:
    def search(self, t): return _C.search(t)
    def finditer(self, t):
        for m in _C.finditer(t):
            yield _M(m)


class _M:
    def __init__(self, m): self.m = m
    def group(self, i): return f"{self.m[1]}-{self.m[2]}-{self.m[3]}"
    def start(self): return self.m.start()
    def end(self): return self.m.end()


CITE = _Cite()


def sentences(text):
    return re.split(r"(?<=[.;])\s+(?=[A-Z“\"(])", text)


def find(cns=None):
    out = []
    for cn, e in sorted(load().items()):
        if not e.get("sha256") or (cns and cn not in cns):
            continue
        sp = paragraphs(cn)
        for i, s in enumerate(sp):
            if not CITE.search(s["text"]) or "Filing Date" in s["text"] or "Case No.:" in s["text"][:200] and i < 6:
                continue
            for m in CITE.finditer(s["text"]):
                c = m.group(1)
                if c == cn:
                    continue
                t = s["text"]
                lo = max(0, t.rfind(". ", 0, m.start()) + 2) if t.rfind(". ", 0, m.start()) >= 0 else 0
                lo = max(lo, m.start() - 450)
                hi = min(len(t), m.end() + 350)
                out.append({"citing": cn, "cited": [c], "span": s["span"], "sentence": t[lo:hi].strip(), "context": t[:1800]})
    return out


if __name__ == "__main__":
    r = find()
    (OUT / "cite-candidates.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
    print(len(r), "candidate sentences,", len({x["citing"] for x in r}), "citing decisions")
