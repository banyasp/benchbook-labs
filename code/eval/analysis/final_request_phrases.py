"""Count stock phrases in the final request of rendered traces (O17, O18; saved 2026-11-10 from the ad-hoc queries).

For every live trace whose trace.yaml names the given render prompt version, take the last message that is not from
the harness (name != "benchbook") and count phrase occurrences (lower-cased substring match) and how many final
requests open with each phrase. Deterministic; no LLM.

    .venv/bin/python code/eval/analysis/final_request_phrases.py --render render.v5
"""
import argparse
import collections
import glob
import json
import re

PHRASES = ["disposition", "please give your", "routing pass", "for the record", "what do you want", "what's your call",
           "what’s your call", "your call", "how do you want", "what do we do", "what should"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", required=True, help="render prompt name as written in trace.yaml, e.g. render.v5")
    ap.add_argument("--store", default="data/store/traces")
    a = ap.parse_args(argv)
    n, has, opens = 0, collections.Counter(), collections.Counter()
    for p in glob.glob(f"{a.store}/*/trace.yaml"):
        if a.render not in open(p).read():
            continue
        try:
            msgs = json.load(open(p.rsplit("/", 1)[0] + "/trace.json"))["messages"]
        except Exception:                                    # noqa: BLE001
            continue
        last = [m for m in msgs if m.get("name") != "benchbook"][-1]
        text = str(last.get("content") or "").lower()
        n += 1
        first = re.split(r"(?<=[.?!])\s+", text.strip())[-1] if text.strip() else ""
        for ph in PHRASES:
            has[ph] += ph in text
            opens[ph] += first.startswith(ph) or text.strip().startswith(ph)
    print(json.dumps({"render": a.render, "traces": n, "contains": dict(has), "opens_with": dict(opens)}, indent=1))


if __name__ == "__main__":
    main()
