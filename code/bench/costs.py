"""Spend and usage: a running total of every model call (Bedrock, OpenRouter, local vLLM) and the Jev judge.

    PYTHONPATH=code .venv/bin/python -m bench.costs                    # report -> results/COSTS.md + results/costs.json
    PYTHONPATH=code .venv/bin/python -m bench.costs --since 2026-10-28 --no-live

Sources:
- every `results/**/provenance*.jsonl` record written by code/datagen/llm.py (one per call: model, stage, usage; since
  2026-10-28 also `cost_usd`). Cost = the record's `cost_usd`, else OpenRouter's own `usage.cost`, else tokens x
  config/prices.yaml (Bedrock: an ESTIMATE, labelled so; local vLLM: $0, tokens counted);
- Jev judge calls: results/costs/judge-calls.jsonl (scorers/judge.py logs each call since 2026-10-28) and, for earlier
  days, the judge cache's rows (one per call; cost not known per call);
- live, ground truth for OpenRouter: the key's usage from openrouter.ai/api/v1/key (all OpenRouter spend, Jev included).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PRICES = ROOT / "config" / "prices.yaml"
RESULTS = ROOT / "results"
JUDGE_LOG = RESULTS / "costs" / "judge-calls.jsonl"
JUDGE_CACHE = RESULTS / "judge_cache.sqlite"
_PRICES: dict | None = None


def prices() -> dict:
    global _PRICES
    if _PRICES is None:
        _PRICES = yaml.safe_load(PRICES.read_text()) if PRICES.exists() else {"models": {}}
    return _PRICES


def tokens(usage: dict | None) -> tuple[int, int, int]:
    """(input, output, cached input) from a Bedrock or OpenAI-style usage block."""
    u = usage or {}
    if "inputTokens" in u or "outputTokens" in u:                          # Bedrock converse
        return int(u.get("inputTokens") or 0), int(u.get("outputTokens") or 0), int(u.get("cacheReadInputTokens") or 0)
    cached = int(((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0)
    return int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0), cached


def call_cost(model: str, usage: dict | None) -> tuple[float | None, str]:
    """-> (USD, basis) for one call. basis: exact (provider-reported) | estimate (price table) | local | unknown."""
    u = usage or {}
    if isinstance(u.get("cost"), (int, float)):
        return float(u["cost"]), "exact"
    p = prices().get("models", {}).get(model)
    if p is None:
        return None, "unknown"
    i, o, c = tokens(u)
    if model.startswith("vllm/"):
        return 0.0, "local"
    cached_price = p.get("cached_input", p.get("input", 0))
    if "inputTokens" in u or "outputTokens" in u:            # Bedrock: cache reads are IN ADDITION to inputTokens
        usd = (i * p.get("input", 0) + c * cached_price + o * p.get("output", 0)) / 1e6
    else:                                                     # OpenAI style: cached tokens are part of prompt_tokens
        usd = ((i - c) * p.get("input", 0) + c * cached_price + o * p.get("output", 0)) / 1e6
    return usd, "estimate"


def provider(model: str) -> str:
    return model.partition("/")[0] or "?"


def _records(since: str | None):
    for f in sorted(RESULTS.rglob("provenance*.jsonl")):
        if "failed-attempt" in f.name:
            continue
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if since and r.get("ts", "") < since:
                    continue
                yield f, r


def openrouter_live() -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    try:
        import httpx
        d = httpx.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"}, timeout=15).json()["data"]
        return {k: d.get(k) for k in ("usage", "usage_daily", "usage_weekly", "usage_monthly", "limit", "limit_remaining")}
    except Exception as e:                                                  # noqa: BLE001 - report without it
        return {"error": f"{type(e).__name__}: {e}"[:200]}


def report(since: str | None = None, live: bool = True) -> dict:
    agg = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "usd": 0.0,
                               "basis": set(), "unpriced_calls": 0})
    by_day, by_stage = defaultdict(float), defaultdict(float)
    for _, r in _records(since):
        m = r.get("model") or "?"
        usd, basis = (r["cost_usd"], r.get("cost_basis", "estimate")) if isinstance(r.get("cost_usd"), (int, float)) \
            else call_cost(m, r.get("usage"))
        a = agg[m]
        a["calls"] += 1
        i, o, c = tokens(r.get("usage"))
        a["input_tokens"] += i
        a["output_tokens"] += o
        a["cached_tokens"] += c
        a["basis"].add(basis)
        if usd is None:
            a["unpriced_calls"] += 1
            continue
        a["usd"] += usd
        by_day[(r.get("ts", "")[:10], provider(m))] += usd
        by_stage[(str(r.get("stage", "")).split(".")[0], m)] += usd
    # judge calls
    judge = defaultdict(int)
    if JUDGE_LOG.exists():
        for line in JUDGE_LOG.read_text().splitlines():
            r = json.loads(line)
            if not since or r["ts"] >= since:
                judge[r["ts"][:10]] += 1
    logged_days = set(judge)
    if JUDGE_CACHE.exists():
        con = sqlite3.connect(f"file:{JUDGE_CACHE}?mode=ro", uri=True)
        for day, n in con.execute("select date(created,'unixepoch'), count(*) from cache group by 1"):
            if day not in logged_days and (not since or day >= since[:10]):
                judge[day] += n
        con.close()
    models = {m: {**v, "basis": sorted(v["basis"]), "usd": round(v["usd"], 4)} for m, v in agg.items()}
    est = sum(v["usd"] for m, v in agg.items() if m.startswith("bedrock/"))
    exact_or = sum(v["usd"] for m, v in agg.items() if m.startswith("openrouter/"))
    out = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "since": since,
           "prices_as_of": str(prices().get("as_of")),
           "totals": {"bedrock_usd_estimate": round(est, 4), "openrouter_llm_usd": round(exact_or, 4),
                      "local_vllm_usd": 0.0, "judge_calls": sum(judge.values())},
           "models": models,
           "by_day": {f"{d} {p}": round(v, 4) for (d, p), v in sorted(by_day.items())},
           "by_stage": {f"{s} | {m}": round(v, 4) for (s, m), v in sorted(by_stage.items(), key=lambda x: -x[1])},
           "judge_calls_by_day": dict(sorted(judge.items()))}
    if live:
        out["openrouter_key_live"] = openrouter_live()
    return out


def write_md(rep: dict, path: Path):
    t = rep["totals"]
    live = rep.get("openrouter_key_live") or {}
    L = [f"# Spend and usage (generated {rep['generated']})", "",
         f"Since: {rep['since'] or 'all logs'}. Prices: config/prices.yaml as of {rep['prices_as_of']}. "
         "Regenerate: `PYTHONPATH=code .venv/bin/python -m bench.costs`.", "",
         "| | USD | basis |", "|---|---|---|",
         f"| Bedrock (Luna, gpt-oss) | {t['bedrock_usd_estimate']:.2f} | **estimate**: tokens x list price (no Cost Explorer access) |",
         f"| OpenRouter: LLM calls in our logs | {t['openrouter_llm_usd']:.2f} | provider-reported where logged |",
         (f"| OpenRouter: whole key (incl. Jev judge) | {live['usage']:.2f} | **exact**, live from OpenRouter; today "
          f"{live.get('usage_daily', 0):.2f}; limit {live.get('limit')} |" if isinstance(live.get("usage"), (int, float))
          else "| OpenRouter: whole key | n/a | live lookup unavailable |"),
         "| Local vLLM (Granite) | 0.00 | GPU instance hours billed separately |",
         f"| Jev judge calls | {t['judge_calls']:,} calls | cost inside the OpenRouter key total |", "",
         "## By model", "", "| model | calls | input tok | output tok | cached | USD | basis |", "|---|---|---|---|---|---|---|"]
    for m, v in sorted(rep["models"].items(), key=lambda x: -x[1]["usd"]):
        L.append(f"| `{m}` | {v['calls']:,} | {v['input_tokens']:,} | {v['output_tokens']:,} | {v['cached_tokens']:,} | "
                 f"{v['usd']:.2f} | {', '.join(v['basis'])}{' (' + str(v['unpriced_calls']) + ' unpriced)' if v['unpriced_calls'] else ''} |")
    L += ["", "## By day and provider", "", "| day, provider | USD |", "|---|---|"]
    L += [f"| {k} | {v:.2f} |" for k, v in rep["by_day"].items()]
    L += ["", "## Top stages", "", "| stage, model | USD |", "|---|---|"]
    L += [f"| {k} | {v:.2f} |" for k, v in list(rep["by_stage"].items())[:15]]
    L += ["", "## Judge calls by day", "", "| day | calls |", "|---|---|"] + [f"| {d} | {n:,} |" for d, n in rep["judge_calls_by_day"].items()]
    path.write_text("\n".join(L) + "\n")


def log_judge_call(model: str, data: dict | None, seconds: float | None = None):
    """Called by scorers/judge.py after each OpenRouter decisions call (best effort; never raises)."""
    try:
        JUDGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": model,
               "build": (data or {}).get("model"), "usage": (data or {}).get("usage"), "seconds": seconds}
        with open(JUDGE_LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:                                                       # noqa: BLE001 - logging must not break scoring
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="ISO date, e.g. 2026-10-28")
    ap.add_argument("--no-live", action="store_true", help="skip the OpenRouter key lookup")
    ap.add_argument("--out", default=str(RESULTS / "COSTS.md"))
    a = ap.parse_args(argv)
    rep = report(a.since, live=not a.no_live)
    write_md(rep, Path(a.out))
    (RESULTS / "costs.json").write_text(json.dumps(rep, indent=1, default=list))
    t = rep["totals"]
    live = rep.get("openrouter_key_live") or {}
    print(f"Bedrock (estimate) ${t['bedrock_usd_estimate']:.2f} | OpenRouter key (exact) "
          f"${live.get('usage', float('nan')):.2f} | judge calls {t['judge_calls']:,} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
