"""Polite fetching for the H3 pilot: acquire.fetch (honest UA, immutable raw store), >= 1.5 s between requests.
A non-200 is raised, never worked around."""
from __future__ import annotations
import time
from pipeline.ingest.acquire import RAW, fetch

_last = [0.0]
DELAY = 1.6


def get(url: str) -> str:
    wait = DELAY - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    try:
        return fetch(url)
    finally:
        _last[0] = time.time()


def raw_path(sha: str):
    return RAW / sha
