"""Readable review sheet of built transfer sisters (and flips), grouped by anchor.

    PYTHONPATH=code .venv/bin/python -m pipeline.transfer.sheet --log results/transfer/build-pilot-20261109.jsonl \\
        --out results/transfer/PILOT-SISTERS-2026-11-09.md
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import yaml

from bench.schema.pipeline import Scenario


def load(path):
    try:
        return Scenario.model_validate(yaml.safe_load(Path(path).read_text()))
    except Exception:                                                 # noqa: BLE001
        return None


def case_md(S: Scenario, inv: dict) -> list[str]:
    c = S.case
    L = [f"- **Setting:** {c.setting} · **Decider:** {c.decider} · **Agent:** {c.agent}",
         f"- **Question:** {c.question}", "- **Options** (anchor option in brackets; ★ = verdict):"]
    for k, o in c.options.items():
        L.append(f"  - {'★ ' if k == c.verdict.choice else ''}{k} [{inv.get(k, k)}]: {o.do}")
    L.append("- **Facts:**")
    L += [f"  - {f.id} ({f.kind}, {f.status}): {f.fact}" for f in c.facts]
    L.append("- **Considerations:**")
    L += [f"  - {k.id} {k.equity} → {', '.join(k.favors)} ({k.weight}){' **decisive**' if k.id in c.verdict.decisive else ''}: "
          f"{k.why}" for k in c.considerations]
    w = c.reasoning.weighing if hasattr(c.reasoning, "weighing") else ""
    L.append(f"- **Weighing:** {w}")
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", required=True, nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    recs = [json.loads(l) for f in a.log for l in Path(f).read_text().splitlines() if l.strip()]
    by = defaultdict(list)
    for r in recs:
        by[r["anchor"]].append(r)
    from collections import Counter
    cnt = Counter(r.get("bucket", r.get("final")) for r in recs)
    fcnt = Counter((r.get("flip") or {}).get("bucket", "none") for r in recs)
    L = ["# Transfer pilot: built sisters (2026-11-09)", "",
         "Each sister X2 was written by GPT-6 Luna from the Claude sketch and the anchor's full case: same considerations "
         "(ids, equities, favors, weights), the anchor's reasoning re-expressed, the anchor's verdict mapped. Option ids "
         "are shuffled (the anchor option is in brackets). Each flip makes one of the case's stated flip conditions "
         "true, so its verdict differs.", "",
         "**Buckets.** accepted: used in the pilot. hard: the setting adds a strong consideration that could change the "
         "decision (kept for later, `data/store/transfer-hard/`). rejected: answer leak or technique "
         "(`data/store/transfer-rejected/`).", "",
         "**Checks shown.** *Equivalence*: a blind solver (GPT-6 Luna, no answer shown) picks the same option on the "
         "sister as on the anchor (it is a test of sameness, not correctness: the solver often disagrees with the "
         "source's own verdict on anchors). *Adds*: strong considerations the probe says this setting brings in.", "",
         f"Sisters: {dict(cnt)}. Flips: {dict(fcnt)}.", ""]
    for anchor, rs in by.items():
        L += [f"## {anchor}", ""]
        for r in sorted(rs, key=lambda x: x["sister"]):
            if not r.get("path"):
                L += [f"### {r['sister']}: {r.get('final')} {r.get('error', '')}", ""]
                continue
            S = load(r["path"])
            chk = r.get("checks") or {}
            eqv = chk.get("equivalence") or {}
            inv = {v: k for k, v in ((S.lineage.detail or {}).get("option_permutation") or {}).items()} if S else {}
            L += [f"### {S.case.title if S else r['sister']} — {r.get('subdomain')} — **{r.get('bucket')}**", "",
                  f"`{r['sister']}` · file `{r['path']}` · sketch FLAG: {r.get('sketch_flag')} · "
                  f"equivalence: {'same choice as on the anchor' if eqv.get('same') else 'different choice'} · "
                  f"adds: {[(m.get('equity'), m.get('weight'), m.get('why')) for m in chk.get('adds_new_vs_anchor') or []] or 'none'}", ""]
            if S:
                L += case_md(S, inv)
            f = r.get("flip") or {}
            if f.get("path"):
                F = load(f["path"])
                if F and S:
                    old = {x.id: x.fact for x in S.case.facts}
                    ch = [x for x in F.case.facts if old.get(x.id) != x.fact]
                    L += ["", f"**Flip** `{f['id']}` — **{f.get('bucket')}** · condition made true: "
                          f"\"{(F.lineage.detail or {}).get('flip_item', {}).get('if')}\" → verdict {F.case.verdict.choice} "
                          f"[{inv.get(F.case.verdict.choice, F.case.verdict.choice)}]",
                          "- Changed or added facts:"] + [f"  - {x.id}: {x.fact}" for x in ch]
            L.append("")
    Path(a.out).write_text("\n".join(L) + "\n")
    print(a.out, len(recs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
