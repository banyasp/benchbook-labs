"""Print the 5 example traces and 5 revised cards for results/DATAGEN-2026-10-28.md (markdown)."""
import random
from pipeline.store import Store

st = Store()
scen = {s.id: s for s in st.scenarios()}
pairs = st.active_pairs()


def pick(pred, k=1, seed=7):
    xs = sorted(x for x in pred)
    random.Random(seed).shuffle(xs)
    return xs[:k]


traces = {t.trace_scenario: t for t in st.traces()}
want = [
    ("OHA flip, indirect realization (train)", lambda s: s.lineage.operator == "flip" and s.split == "train" and "OHA" in s.id
     and (s.lineage.detail or {}).get("realization") == "indirect"),
    ("5 CFR 2635 example, restyle (train)", lambda s: s.lineage.operator == "restyle" and "OGE" in s.id and s.split == "train"),
    ("Held-out natsec source scenario (test)", lambda s: s.held_out and not s.lineage.parent),
    ("add_fact, model-solved gold (train)", lambda s: s.lineage.operator == "add_fact" and s.split == "train"),
    ("OHA source scenario with a recommendation (test)", lambda s: not s.lineage.parent and s.split == "test" and not s.held_out),
]
print("## Five traces\n")
used = set()
for title, pred in want:
    cands = [t for t in traces if t in scen and pred(scen[t]) and t not in used]
    if title.endswith("recommendation (test)"):
        cands = [t for t in cands if traces[t].recommended_option]
    if not cands:
        continue
    tid = pick(cands)[0]
    used.add(tid)
    T, tr = scen[tid], traces[tid]
    c = T.case
    print(f"### {title}: `{tid}`\n")
    print(f"- Question: {c.question}")
    print(f"- Options (channel): " + "; ".join(f"**{o}** {v.do} ({tr.channels.get(f'{tid}/{o}', '?')})" for o, v in c.options.items()))
    print(f"- Trace scenario's own verdict: {c.verdict.choice}. Recommended in the trace: "
          f"{(tr.recommended_option or 'none').rpartition('/')[2]}. Words: {tr.diagnostics.get('words')}, "
          f"decisive share {tr.diagnostics.get('decisive_word_share')}, render attempts {len(tr.diagnostics.get('attempts') or [])}"
          f"{', re-gated' if tr.diagnostics.get('regated') else ''}.")
    tj = st.trace_json(tid)
    print("\n```text")
    for m in tj["messages"]:
        who = m.get("role") + (f" ({m['name']})" if m.get("name") else "")
        body = str(m.get("content") or "").strip()
        print(f"[{who}] {body[:1400]}{' …' if len(body) > 1400 else ''}\n")
    print("```\n")

print("## Five revised cards (C → C′)\n")
revs = [s for s in scen.values() if s.lineage.operator == "revise_card" and s.split == "train"]
for Cp in pick([s.id for s in revs], 5, seed=3):
    Cp = scen[Cp]
    C = scen[Cp.lineage.parent]
    det = Cp.lineage.detail or {}
    dk = det.get("delta_k") or {}
    print(f"### `{Cp.id}` (from `{C.id}`)\n")
    print(f"- Question: {C.case.question}")
    print(f"- C's verdict: **{C.case.verdict.choice}** {C.case.options[C.case.verdict.choice].do}")
    print(f"- C′'s verdict (target picked in code, move `{det.get('target_move')}`): **{Cp.case.verdict.choice}** "
          f"{Cp.case.options[Cp.case.verdict.choice].do}")
    print(f"- Δ_K: changed {dk.get('changed')}, added {dk.get('added')}")
    oc = {c.id: c for c in C.case.considerations}
    for c in Cp.case.considerations:
        o = oc.get(c.id)
        if o is None:
            print(f"  - **{c.id} (new)**: {c.equity}, favors {c.favors}, {c.weight}: {c.why}")
        elif (o.weight, o.favors) != (c.weight, c.favors):
            print(f"  - **{c.id}**: {o.weight} favoring {o.favors} → {c.weight} favoring {c.favors}: {c.why}")
    print(f"- C′ weighing: {Cp.case.reasoning.weighing[:700]}\n")
