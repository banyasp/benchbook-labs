"""Direction analysis: classify each gold option as deny (access not granted/restored, concern not resolved) or grant, then
baselines (always-deny, copy-C-direction) and splits by whether C and T point the same way."""
from __future__ import annotations
import json, re, collections, yaml
from .analyze import load, runs, wilson, OUT

DENY = re.compile(r"\b(den(y|ies|ied|ial)|not (restore|grant|resolved|mitigated)|refus|revoke|decline|uphold|remain(s)? (un|not)|finds? .*not (resolved|mitigated)|unresolved|unmitigated|continue[sd]? to (suspend|deny)|does not (restore|resolve))", re.I)
GRANT = re.compile(r"\b(restor|grant|resolved|mitigated|reinstat|approv)", re.I)


def direction(case, opt):
    t = case["options"][opt]["do"]
    d, g = bool(DENY.search(t)), bool(GRANT.search(t))
    return "deny" if d else ("grant" if g else "other")


def main():
    T = load()
    rows = []
    for pid, (p, tc) in T.items():
        cc = yaml.safe_load((OUT / "scenarios" / f"C-{pid}.yaml").read_text())["case"]
        rows.append({"pair": pid, "band": p["band"], "gold_T": direction(tc, tc["verdict"]["choice"]),
                     "gold_C": direction(cc, cc["verdict"]["choice"]),
                     "gold_T_text": tc["options"][tc["verdict"]["choice"]]["do"], "gold_C_text": cc["options"][cc["verdict"]["choice"]]["do"]})
    return rows


if __name__ == "__main__":
    rows = main()
    (OUT / "directions.json").write_text(json.dumps(rows, indent=1))
    c = collections.Counter((r["gold_T"], r["gold_C"]) for r in rows)
    print(c)
    for r in rows:
        print(r["pair"], r["band"], "| T:", r["gold_T"], r["gold_T_text"][:90], "| C:", r["gold_C"], r["gold_C_text"][:90])
