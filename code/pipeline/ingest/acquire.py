"""Acquire: URL -> data/raw/<sha256> (exact bytes) + <sha256>.meta.json. Immutable: an existing raw file is never rewritten."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from pipeline.store import DATA

USER_AGENT = "benchbook-labs-research/0.1 (peterbanyas@outlook.com; academic research on public-domain decisions)"
RAW = DATA / "raw"


def store_raw(content: bytes, meta: dict, raw_dir: Path = RAW) -> str:
    sha = hashlib.sha256(content).hexdigest()
    raw_dir.mkdir(parents=True, exist_ok=True)
    f, m = raw_dir / sha, raw_dir / f"{sha}.meta.json"
    if not f.exists():
        f.write_bytes(content)
    if not m.exists():
        m.write_text(json.dumps({**meta, "sha256": sha, "size": len(content)}, indent=1))
    return sha


def fetch(url: str, raw_dir: Path = RAW, session=None) -> str:
    import requests
    s = session or requests
    r = s.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"{url}: HTTP {r.status_code}")
    return store_raw(r.content, {"url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                 "content_type": r.headers.get("content-type"), "http_status": r.status_code,
                                 "user_agent": USER_AGENT}, raw_dir)


def acquire(sources: list[dict], acquired: dict, refresh: bool = False, delay: float = 1.5, fetcher=fetch) -> dict:
    for s in sources:
        if s["id"] in acquired and not refresh:
            continue
        sha = fetcher(s["url"])
        acquired[s["id"]] = {"sha256": sha, "sha12": sha[:12], "url": s["url"]}
        time.sleep(delay)
    return acquired
