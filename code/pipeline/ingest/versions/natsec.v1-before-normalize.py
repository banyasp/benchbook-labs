"""W8b acquire for the national-security sources (BUILD-BRIEF-v2.4 §W8b). Acquire only: extraction waits for W4a + the
v2 option rules.

    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec acquire     # fetch the seed, record blocks
    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec status
    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec ingest-manual   # files Peter downloaded by hand

Blocked sources: run fetch-blocked-natsec.sh on a laptop, copy its output into data/raw/manual/ (with manifest.tsv),
then ingest-manual stores each listed file in the raw store and moves the source from blocked to acquired.

Seed: sources-natsec.seed.yaml. Same polite fetcher as pipeline.ingest.acquire (descriptive User-Agent, delay,
immutable raw store). A non-200 is recorded, never worked around (no UA spoofing, no alternative routes beyond the
mirrors the catalog itself lists). `follow:` fetches same-host links matching a regex (multi-page reports).
Writes data/store/registry/acquired-natsec.yaml and results/SOURCES-BLOCKED-2026-10-28.md.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml

from pipeline.store import DATA, ROOT, write_yaml

from .acquire import USER_AGENT, fetch

SEED = Path(__file__).with_name("sources-natsec.seed.yaml")
ACQ = DATA / "store" / "registry" / "acquired-natsec.yaml"
BLOCKED = ROOT / "results" / "SOURCES-BLOCKED-2026-10-28.md"
MAX_FOLLOW = 40


def _links(html: str, base: str, pattern: str) -> list[str]:
    host = urlparse(base).netloc
    out = []
    for href in re.findall(r'href="([^"#]+)"', html):
        u = urljoin(base, href)
        if urlparse(u).netloc == host and re.search(pattern, u) and u not in out:
            out.append(u)
    return out[:MAX_FOLLOW]


def acquire(delay: float = 1.5) -> dict:
    seed = yaml.safe_load(SEED.read_text())
    d = seed.get("defaults", {})
    acq = yaml.safe_load(ACQ.read_text()) if ACQ.exists() else {"sources": {}, "blocked": {}}
    for s in seed["sources"]:
        if s["id"] in acq["sources"]:
            continue
        rec = {**{k: d[k] for k in ("split", "held_out_domain", "refusal_sensitivity", "license")}, **s,
               "files": [], "tags": (["ocr"] if s.get("ocr") else [])}
        try:
            sha = fetch(s["url"])
            rec["files"].append({"url": s["url"], "sha256": sha})
            if s.get("follow"):
                html = (DATA / "raw" / sha).read_bytes().decode("utf-8", "replace")
                for u in _links(html, s["url"], s["follow"]):
                    time.sleep(delay)
                    try:
                        rec["files"].append({"url": u, "sha256": fetch(u)})
                    except Exception as e:
                        rec.setdefault("partial_failures", []).append({"url": u, "error": str(e)[:200]})
            acq["sources"][s["id"]] = rec
            acq["blocked"].pop(s["id"], None)
            print(f"ok      {s['id']}: {len(rec['files'])} file(s)")
        except Exception as e:
            acq["blocked"][s["id"]] = {"url": s["url"], "title": s["title"], "family": s["family"],
                                       "error": str(e)[:200], "tried_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())}
            print(f"BLOCKED {s['id']}: {str(e)[:120]}")
        time.sleep(delay)
    write_yaml(ACQ, acq)
    write_blocked(acq)
    return acq


def write_blocked(acq: dict):
    lines = ["# Sources that could not be fetched from the EC2 box (2026-10-28)", "",
             "W8b access rule: no user-agent spoofing or workarounds. Please download these by hand into",
             "`data/raw/manual/` (keep the original file name; add a line to `data/raw/manual/README.md` with the URL).",
             f"Fetcher User-Agent: `{USER_AGENT}`.", "",
             "| Source id | Family | Title | URL | Error |", "|---|---|---|---|---|"]
    for sid, b in sorted(acq["blocked"].items()):
        lines.append(f"| {sid} | {b['family']} | {b['title']} | {b['url']} | {b['error']} |")
    partial = [(sid, f) for sid, s in acq["sources"].items() for f in s.get("partial_failures", [])]
    if partial:
        lines += ["", "## Partial failures (main page fetched, a linked page was not)", "", "| Source id | URL | Error |",
                  "|---|---|---|"] + [f"| {sid} | {f['url']} | {f['error']} |" for sid, f in partial]
    if not acq["blocked"] and not partial:
        lines += ["", "None: every seeded source fetched."]
    BLOCKED.parent.mkdir(parents=True, exist_ok=True)
    BLOCKED.write_text("\n".join(lines) + "\n")


MANUAL = DATA / "raw" / "manual"


def ingest_manual() -> dict:
    """Register hand-downloaded files listed in data/raw/manual/manifest.tsv (source_id, url, file)."""
    from .acquire import store_raw
    seed = {s["id"]: s for s in yaml.safe_load(SEED.read_text())["sources"]}
    d = yaml.safe_load(SEED.read_text()).get("defaults", {})
    acq = yaml.safe_load(ACQ.read_text()) if ACQ.exists() else {"sources": {}, "blocked": {}}
    rows = [ln.split("\t") for ln in (MANUAL / "manifest.tsv").read_text().splitlines()[1:] if ln.strip()]
    for sid, url, fname in rows:
        if sid not in seed:
            print(f"skip    {fname}: unknown source id {sid}")
            continue
        f = MANUAL / fname
        if not f.exists():
            print(f"missing {fname}")
            continue
        sha = store_raw(f.read_bytes(), {"url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(f.stat().st_mtime)), "acquired_by": "manual download (Peter)",
                        "manual_file": fname})
        s = seed[sid]
        rec = acq["sources"].setdefault(sid, {**{k: d[k] for k in ("split", "held_out_domain",
                                        "refusal_sensitivity", "license")}, **s, "files": [],
                                        "tags": (["ocr"] if s.get("ocr") else []) + ["manual"]})
        if not any(x["sha256"] == sha for x in rec["files"]):
            rec["files"].append({"url": url, "sha256": sha})
        acq["blocked"].pop(sid, None)
        print(f"stored  {sid}: {fname} -> raw/{sha[:12]}")
    write_yaml(ACQ, acq)
    write_blocked(acq)
    return acq


def status():
    acq = yaml.safe_load(ACQ.read_text()) if ACQ.exists() else {"sources": {}, "blocked": {}}
    fams = sorted({s["family"] for s in acq["sources"].values()})
    print(f"acquired {len(acq['sources'])} sources ({sum(len(s['files']) for s in acq['sources'].values())} files), "
          f"{len(fams)} families; blocked {len(acq['blocked'])}")
    for sid, s in acq["sources"].items():
        print(f"  {sid:26} {s['family']:26} {s['content_domain']:20} files={len(s['files'])} tags={s['tags']}")
    for sid, b in acq["blocked"].items():
        print(f"  BLOCKED {sid:18} {b['error'][:80]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["acquire", "status", "ingest-manual"])
    a = ap.parse_args(argv)
    {"acquire": acquire, "status": status, "ingest-manual": ingest_manual}[a.cmd]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
