"""Extract C (from the cited decision) and T (from the citing one) with ingest.extract.extract_episode, writing ONLY to
results/h3-pilot/ (extract_episode's `data=` is pointed at results/h3-pilot/_data; scenarios are saved to
results/h3-pilot/scenarios/). Nothing is written to data/store/."""
from __future__ import annotations
import sys, yaml, json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from pipeline.ingest.extract import extract_episode, ExtractionError
from .crawl import OUT, load
from .text import paragraphs

SC = OUT / "scenarios"
DATA = OUT / "_data"
NOLEAK = (" Do not mention, cite or allude to any other OHA decision or case number anywhere in the scenario."
          " Keep the Administrative Judge as the decider (agent_recast false).")


def source(cn: str, pid: str) -> dict:
    e = load()[cn]
    return {"id": f"H3-{pid.replace('__', '-')}-{cn}", "family": f"H3-{pid.replace('__', '-')}-{cn}", "title": f"DOE OHA personnel security decision {cn}", "url": e["pdf_url"],
            "kind": "DOE OHA personnel security decision", "license": "US Government work, public domain",
            "domain": "personnel security adjudication"}


def do(cn: str, focus: str, role: str, pid: str):
    f = SC / f"{role}-{pid}.yaml"
    if f.exists():
        return f"{f.name} exists"
    sp = paragraphs(cn)
    sha = load()[cn]["sha256"]
    try:
        ep = {"n": 1, "focus": focus + NOLEAK}
        src = source(cn, pid)
        src["episodes"] = [ep]
        s = extract_episode(src, ep, sp, sha, "eval-only", data=DATA)
    except Exception as e:
        return f"REJECTED {role} {cn}: {e}"
    SC.mkdir(parents=True, exist_ok=True)
    f.write_text(yaml.safe_dump(s.dump(), sort_keys=False, allow_unicode=True))
    return f"{f.name} choice={s.case.verdict.choice}"


def main(pairs_file):
    pairs = yaml.safe_load(Path(pairs_file).read_text())["pairs"]
    jobs = []
    for p in pairs:
        jobs.append((p["cited"], p["focus_C"], "C", p["id"]))
        jobs.append((p["citing"], p["focus_T"], "T", p["id"]))
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(lambda j: do(*j), jobs):
            print(r, flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
