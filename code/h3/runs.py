"""Stand-in R* runs: arm `with_c` (extend C to T) and arm `no_c` (answer T alone). Same T facts/question/options in both.
Raw replies -> results/h3-pilot/runs/<role>/<pair>.<arm>.<k>.json."""
from __future__ import annotations
import json, re, sys, yaml
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .crawl import OUT

SYS = ("You assist a DOE Administrative Judge (Office of Hearings and Appeals) who decides personnel security cases under "
       "10 C.F.R. Part 710 and the Adjudicative Guidelines. Reply with one JSON object only.")


def render_case(c: dict) -> str:
    o = "\n".join(f"  {k}: {v['do']}" for k, v in c["options"].items())
    f = "\n".join(f"  {x['id']} [{x['kind']}, {x['status']}]: {x['fact']}" for x in c["facts"])
    k = "\n".join(f"  {x['id']} (facts {','.join(x['facts'])}; equity {x['equity']}; favors {','.join(x['favors'])}; {x['weight']}): {x['why']}"
                  for x in c["considerations"])
    r = c["reasoning"]
    v = c["verdict"]
    fc = c["flip_conditions"]
    flips = "\n".join(f"  if {x['if']} -> {x['then']}: {x['why']}" for x in fc.get("would_change") or [])
    return (f"REFERENCE CASE: {c['title']}\nSetting: {c['setting']}\nSituation: {c['situation']}\nQuestion: {c['question']}\n"
            f"Options:\n{o}\nFacts:\n{f}\nConsiderations:\n{k}\nReasoning:\n  read: {r.get('read')}\n  weighing: {r.get('weighing')}\n"
            f"  tempting wrong: {json.dumps(r.get('tempting_wrong'))}\n  rejected: {json.dumps(r.get('rejected'))}\n"
            f"Verdict: {v['choice']} ({v.get('basis')}); decisive: {v.get('decisive')}\nWould change if:\n{flips}\n"
            f"Lesson: {c.get('lesson')}\nLimits: {c.get('limits')}")


def render_t(c: dict) -> str:
    o = "\n".join(f"  {k}: {v['do']}" for k, v in c["options"].items())
    f = "\n".join(f"  {x['id']} [{x['kind']}, {x['status']}]: {x['fact']}" for x in c["facts"])
    return (f"CASE TO DECIDE\nSetting: {c['setting']}\nSituation: {c['situation']}\nFacts:\n{f}\n"
            f"Question: {c['question']}\nOptions:\n{o}")


FMT_C = ('Reply with JSON: {"relation": "follows|flips|distinguished|not_governed", "reasoning": "<=120 words: which of the reference '
         'case\'s considerations carry over to this case and which do not", "choice": "O<n>"}. `follows` = the reference case\'s '
         'reasoning governs and its outcome carries over; `flips` = same reasoning, different facts reverse the outcome; '
         '`distinguished` = the case differs in a way that matters, so decide on the merits; `not_governed` = the reference case does not '
         'bear on this one, so decide on the merits. In every case choose exactly one option.')
FMT_N = 'Reply with JSON: {"reasoning": "<=120 words", "choice": "O<n>"}. Choose exactly one option.'


def prompt(arm: str, C: dict | None, T: dict) -> list[dict]:
    if arm == "with_c":
        u = (f"{render_case(C)}\n\n---\n\n{render_t(T)}\n\nThe reference case is an earlier OHA decision that may be controlling or analogous. "
             f"Extend its reasoning to the case to decide, then choose what the Administrative Judge should do. {FMT_C}")
    else:
        u = f"{render_t(T)}\n\nChoose what the Administrative Judge should do. {FMT_N}"
    return [{"role": "system", "content": SYS}, {"role": "user", "content": u}]


def parse(reply: str, opts) -> dict:
    m = re.search(r"\{.*\}", reply, re.S)
    try:
        o = json.loads(m.group(0)) if m else {}
    except ValueError:
        o = {}
    ch = o.get("choice")
    if ch not in opts:
        mm = re.findall(r'"choice"\s*:\s*"?(O\d+)', reply)
        ch = mm[-1] if mm and mm[-1] in opts else None
    return {"choice": ch, "relation": o.get("relation"), "reasoning": o.get("reasoning")}


def one(role_name, pid, arm, k, C, T, complete):
    f = OUT / "runs" / role_name / f"{pid}.{arm}.{k}.json"
    if f.exists():
        return
    msgs = prompt(arm, C, T)
    try:
        reply = complete(role_name, msgs, stage=f"h3.{role_name}.{arm}")
    except Exception as e:  # keep going; the error is recorded
        reply = f"ERROR {type(e).__name__}: {str(e)[:300]}"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"pair": pid, "arm": arm, "k": k, "role": role_name, "reply": reply, "parsed": parse(reply, T["options"]),
                             "prompt": msgs[1]["content"]}, indent=1, ensure_ascii=False))


def main(role_name, ks=3, workers=5, only=None):
    from bench.models import complete
    pairs = yaml.safe_load((OUT / "pairs.yaml").read_text())["pairs"]
    jobs = []
    for p in pairs:
        if only and p["id"] not in only:
            continue
        cf, tf = OUT / "scenarios" / f"C-{p['id']}.yaml", OUT / "scenarios" / f"T-{p['id']}.yaml"
        if not (cf.exists() and tf.exists()):
            continue
        C, T = yaml.safe_load(cf.read_text())["case"], yaml.safe_load(tf.read_text())["case"]
        for arm in ("with_c", "no_c"):
            for k in range(ks):
                jobs.append((role_name, p["id"], arm, k, C, T, complete))
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda j: one(*j), jobs))
    print(len(jobs), "jobs")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3)
