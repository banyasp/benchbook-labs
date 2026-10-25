"""Live check against the running vLLM server: 6 generations on INT-301-v01 with the hand-converted fixture case.

    PYTHONPATH=code python -m harness.live_check [--out results/harness-check]

Not part of the test suite (costs GPU time). Fixture case = code/harness/tests/fixtures/DR-INT-301.case.yaml.
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bench.models import ROOT
from bench.schema import parse_reply
from harness import HarnessSettings, build_episode, run_episode
from harness.tests.helpers import FakeLib, FakeRetriever, scenario

RUNS = {  # name -> (arm, settings kwargs, max_tokens)
    "A": ("relevant", dict(mode="A"), 9000),
    "B": ("relevant", dict(mode="B"), 4500),
    "C": ("relevant", dict(mode="C"), 4500),
    "Cprime": ("relevant", dict(mode="Cprime"), 4500),
    "B-noref": ("none", dict(mode="B"), 4500),
    "B-native-analogical": ("relevant", dict(mode="B", tool_messages="native", analogical_prompt=True), 4500),
}


def one(item, out):
    name, (arm, kw, mt) = item
    s = HarnessSettings(seed=0, max_tokens=mt, **kw)
    ep = build_episode(scenario(), arm, s, FakeLib(), retriever=FakeRetriever())
    ep.save(out / f"{name}.episode.json")
    (out / f"{name}.prompt.txt").write_text(ep.prompt_text)
    c = run_episode(ep, s)
    (out / f"{name}.raw.txt").write_text(c.raw_text)
    p = parse_reply(c.raw_text)
    v = p.steps.get("verdict", {})
    rep = {"name": name, "arm": arm, "settings": s.to_dict(), "prompt_tokens": c.usage.get("prompt_tokens"),
           "completion_tokens": c.usage.get("completion_tokens"), "seconds": c.seconds, "finish_reason": c.finish_reason,
           "steps_found": list(p.steps), "where": p.where, "missing": p.missing, "in_order": p.in_order,
           "strict_ok": p.strict_ok, "errors": p.errors, "repairs": p.repairs, "choice": v.get("choice"),
           "relation": v.get("relation"), "options": (p.steps.get("fact_enumeration") or {}).get("options"),
           "think_chars": len(c.reasoning), "content_chars": len(c.content)}
    (out / f"{name}.report.json").write_text(json.dumps(rep, indent=1, default=str))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/harness-check")
    ap.add_argument("--only", nargs="*", help="run names to run (default all)")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(lambda it: one(it, out), [i for i in RUNS.items() if not a.only or i[0] in a.only]):
            print(json.dumps({k: r[k] for k in ("name", "completion_tokens", "seconds", "finish_reason", "steps_found",
                                                "missing", "in_order", "choice", "relation")}))


if __name__ == "__main__":
    main()
