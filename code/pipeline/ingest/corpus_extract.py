"""Extract a stratified batch of natsec-corpus episodes into scenarios X = (F, Q, A) (Peter, 2026-10-28: "500, stratified
from throughout the domains").

    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.corpus_extract [--batch corpus-batch2] select [--n 500] [--seed 0]
    PYTHONPATH=code .venv/bin/python -m pipeline.ingest.corpus_extract --batch corpus-batch2 incidents   # then select again
    BENCHBOOK_EQUITY_SET=pilot2 PYTHONPATH=code .venv/bin/python -m pipeline.ingest.corpus_extract --batch corpus-batch2 \
        --scope corpus_scope.v2 run [--workers 16]
A later batch never reuses an earlier batch's episodes, inherits the family (and so the split) of any document or
incident an earlier batch used, and drops a targeting episode whose family is already train/dev.

select: reads data/store/episodes/corpus/*.yaml and writes data/store/episodes/corpus-batch1.yaml.
- Buckets by content_domain with quotas (QUOTAS); 1,402 free-text `other:` labels share one bucket.
- Excluded: doctrine candidates with no stated course (gold would be model-solved: not this batch), and documents about
  an incident already in the W8b held-out set (title match, LEAK_TERMS): those would leak into train.
- Within a bucket: round-robin over collections, then families, one episode per family before any second; within a
  family the episode with the widest span range. At least MIN_DOCTRINE doctrine episodes overall.
- Families: per document, except multi-part investigations (one incident across many files: Uruzgan, Chilcot, Church,
  Walsh, Tonkin, Pueblo, Bay of Pigs, Able Archer), which are one family per collection (brief W8b: family per incident).
- Splits per family: targeting -> held out (test, Peter's natsec ruling); otherwise registry.assign_splits_v2 per bucket
  (~20/10/70 test/dev/train). A family with any targeting episode is all test (no leakage).
run: the standard extractor (extract_fq.v2 + extract_a.v1 + option rules) with prompts/corpus_scope.v1.md appended, the
technique screen with up to two re-extractions (as natsec_extract), equity set from BENCHBOOK_EQUITY_SET (pilot2).
Outcomes in data/store/episodes/corpus-batch1.results.jsonl; scenarios in the store under their family.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from pipeline.store import DATA, Store, write_yaml

from . import registry as R
from . import technique_check as TC
from .extract import EQUITY_SET, ExtractionError, IncompleteExtraction, TechniqueSkip, extract_episode, save_incomplete

HERE = Path(__file__).parent
EP_DIR = DATA / "store" / "episodes" / "corpus"
EPISODES = DATA / "store" / "episodes"
BATCH = EPISODES / "corpus-batch1.yaml"                       # configure() points these at --batch
RESULTS = EPISODES / "corpus-batch1.results.jsonl"
INCIDENTS = EPISODES / "corpus.incidents.json"                # incident groups across all batches (batch 1's seeded it)
INCIDENTS_B1 = EPISODES / "corpus-batch1.incidents.json"
CORPUS_META = DATA / "corpus" / "natsec" / "meta"
SCOPE = HERE / "prompts" / "corpus_scope.v1.md"             # batch 1; batch 2 on: corpus_scope.v2 (3-4 genuine options)


def configure(batch: str, scope: str | None = None):
    global BATCH, RESULTS, SCOPE
    BATCH, RESULTS = EPISODES / f"{batch}.yaml", EPISODES / f"{batch}.results.jsonl"
    if scope:
        SCOPE = HERE / "prompts" / f"{scope}.md"
    if not INCIDENTS.exists() and INCIDENTS_B1.exists():
        INCIDENTS.write_text(INCIDENTS_B1.read_text())


def previous_batches() -> list[dict]:
    """Episodes of every other corpus batch (they fix families and splits for this one)."""
    out = []
    for f in sorted(EPISODES.glob("corpus-batch*.yaml")):
        if f != BATCH:
            out += [{**e, "_batch": f.stem} for e in (yaml.safe_load(f.read_text()) or {}).get("episodes", [])]
    return out

QUOTAS = {"targeting": 80, "operational-command": 90, "intel-oversight": 85, "intel-analysis": 85,
          "use-of-force-policy": 60, "small": 20, "other": 80}
SMALL = {"cyber-policy", "gov-ethics", "security-clearance"}
MIN_DOCTRINE = 30
INCIDENT_COLLECTIONS = {"uruzgan", "chilcot", "church", "walsh", "nsa-tonkin", "nsa-pueblo", "nsarchive-bop",
                        "nsarchive-ablearcher"}
LEAK_TERMS = re.compile(r"kunduz|tarnak|mosul|jadida|al[- ]?jinah|harim|vincennes|\bstark\b|black ?hawk|"
                        r"operation provide comfort|farah|granai|world central kitchen|\bwck\b|anaconda|shahikot|"
                        r"icty|grdelica|djakovica|\brts\b", re.I)
DOMAIN_OF_BUCKET = {"targeting": "military-operational"}      # targeting joins the existing held-out domain


def bucket(cd: str) -> str:
    return "small" if cd in SMALL else cd if cd in QUOTAS else "other"


def family_id(doc: dict) -> str:
    c = str(doc.get("collection") or "")
    return f"CORPUS-{c.upper()}" if c in INCIDENT_COLLECTIONS else f"CORPUS-{doc['source']}"


def _width(ep: dict) -> int:
    a, b = ep["span_range"]
    pa, pb = (re.search(r"#p(\d+)\.(\d+)$", x) for x in (a, b))
    return (int(pb[1]) - int(pa[1])) * 50 + int(pb[2]) - int(pa[2]) if pa and pb else 0


def candidates() -> tuple[list[dict], Counter]:
    out, dropped = [], Counter()
    for f in sorted(EP_DIR.glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        for ep in doc.get("episodes") or []:
            if doc.get("doctrine") and "choice_stated" in (ep.get("relaxed") or []):
                dropped["doctrine without a stated course"] += 1
                continue
            if LEAK_TERMS.search(" ".join(str(x or "") for x in (doc.get("title"), ep.get("decision"), ep.get("focus")))):
                dropped["W8b incident (leak guard)"] += 1
                continue
            out.append({**ep, "source": doc["source"], "doc": doc["doc"], "title": doc.get("title"),
                        "collection": doc.get("collection"), "doctrine": bool(doc.get("doctrine")),
                        "family": family_id(doc), "bucket": bucket(ep["content_domain"])})
    return out, dropped


def select(n_total: int = 500, seed: int = 0) -> dict:
    cands, dropped = candidates()
    prev = previous_batches()
    prev_keys = {(e["source"], e["n"]) for e in prev}
    n0 = len(cands)
    cands = [e for e in cands if (e["source"], e["n"]) not in prev_keys]
    if n0 - len(cands):
        dropped["already in an earlier batch"] = n0 - len(cands)
    prev_fam_of_key = {(e["source"], e["n"]): e["family"] for e in prev}
    prev_fams_of_src = defaultdict(set)
    for e in prev:
        prev_fams_of_src[e["source"]].add(e["family"])
    prev_split = {e["family"]: e["split"] for e in prev}
    prev_held = {e["family"] for e in prev if e.get("held_out")}
    for e in cands:                                            # same document as an earlier batch -> same family
        if len(prev_fams_of_src.get(e["source"], ())) == 1:
            e["family"] = next(iter(prev_fams_of_src[e["source"]]))
    # incident groups (the same event in several documents) are one family; applied before picking, so the one-per-family
    # spread and the held-out checks see final families
    key_fam = incident_families(prev_fam_of_key)
    for e in cands:
        if (e["source"], e["n"]) in key_fam:
            e["family"] = e["incident_family"] = key_fam[(e["source"], e["n"])]
    prev_src_split = defaultdict(set)
    for e in prev:
        prev_src_split[e["source"]].add(e["split"])
    locked = lambda e: bool(({prev_split.get(e["family"])} | prev_src_split.get(e["source"], set())) & {"train", "dev"})
    n0 = len(cands)
    cands = [e for e in cands if not (e["bucket"] == "targeting" and locked(e))]   # could not be held out
    if n0 - len(cands):
        dropped["targeting tied to an earlier train/dev family or document"] = n0 - len(cands)
    seen_before = lambda f: f in prev_split                                        # families earlier batches used
    scale = n_total / sum(QUOTAS.values())
    quotas = {b: round(q * scale) for b, q in QUOTAS.items()}
    rng = random.Random(seed)
    by_b = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))      # bucket -> collection -> family -> eps
    for e in cands:
        by_b[e["bucket"]][e["collection"]][e["family"]].append(e)
    chosen, used = [], Counter()

    def take(b, pred, limit):
        """Round-robin collections -> families (one episode per family per pass; families no earlier batch used first),
        widest span range first."""
        got = []
        colls = sorted(by_b[b])
        rng.shuffle(colls)
        queues = {c: sorted(by_b[b][c], key=lambda f: (seen_before(f), hashlib.sha256(f"{seed}{f}".encode()).hexdigest()))
                  for c in colls}
        passes = 0
        while len(got) < limit and passes < 50:
            moved = False
            for c in colls:
                for fam in queues[c]:
                    if len(got) >= limit:
                        break
                    if used[fam] > passes:
                        continue
                    eps = sorted((e for e in by_b[b][c][fam] if pred(e) and not e.get("_taken")), key=_width, reverse=True)
                    if eps:
                        eps[0]["_taken"] = True
                        used[fam] += 1
                        got.append(eps[0])
                        moved = True
                        break                                        # next collection: spread across collections
            passes += 0 if moved else 1
            if not moved and passes > max(used.values(), default=0):
                break
        return got

    # doctrine first (counted against each bucket's quota), then fill
    doc_per_b = {b: 0 for b in quotas}
    nd = MIN_DOCTRINE
    for b in sorted(quotas, key=lambda b: -sum(1 for e in cands if e["bucket"] == b and e["doctrine"])):
        k = min(nd, max(1, quotas[b] // 6))
        g = take(b, lambda e: e["doctrine"], k)
        chosen += g
        doc_per_b[b] = len(g)
        nd -= len(g)
        if nd <= 0:
            break
    for b, q in quotas.items():
        chosen += take(b, lambda e: True, q - doc_per_b.get(b, 0))
    for e in chosen:
        e.pop("_taken", None)
    splits, held, warns, moved = split_groups(prev, chosen)
    eps = []
    for e in sorted(chosen, key=lambda e: (e["bucket"], e["family"], e["n"])):
        e["split"], e["held_out"] = splits[e["family"]], e["family"] in held
        multi = e["family"] != f"CORPUS-{e['source']}"               # incident / multi-part family: add the document
        e["id"] = f"{e['family']}-{e['source']}-E{e['n']}" if multi else f"{e['family']}-E{e['n']}"
        eps.append(e)
    fams = {e["family"] for e in eps}
    summary = {"n": len(eps), "quotas": quotas, "by_bucket": dict(Counter(e["bucket"] for e in eps)),
               "by_split": dict(Counter(e["split"] for e in eps)), "doctrine": sum(e["doctrine"] for e in eps),
               "families": len(fams), "collections": len({e["collection"] for e in eps}), "dropped": dict(dropped),
               "split_warnings": warns, "seed": seed, "candidates": len(cands),
               "families_from_earlier_batches": sum(1 for f in fams if f in prev_split),
               "earlier_batch_episodes_resplit": moved}
    write_yaml(BATCH, {"batch": BATCH.stem, "created": time.strftime("%Y-%m-%d"), "summary": summary, "episodes": eps})
    if moved:
        apply_prev_splits(prev, splits, held)
    return summary


def split_groups(prev: list[dict], chosen: list[dict]) -> tuple[dict, set, list, list]:
    """One split per SPLIT GROUP: families joined by a shared document or incident, across all batches (R82).
    Group with a targeting episode -> test, held out. Earlier batches' splits are kept; if they disagree inside a group,
    the group goes to test (conservative) and those earlier episodes are moved (`moved`). New groups: assign_splits_v2."""
    allx = prev + chosen
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    first_fam_of_src = {}
    for e in allx:
        find(e["family"])
        if e["source"] in first_fam_of_src:
            union(e["family"], first_fam_of_src[e["source"]])
        else:
            first_fam_of_src[e["source"]] = e["family"]
    comp = defaultdict(list)
    for e in allx:
        comp[find(e["family"])].append(e)
    splits, held, new_dom = {}, set(), {}
    for root, es in comp.items():
        fams = {e["family"] for e in es}
        tgt = any(e["bucket"] == "targeting" or e.get("held_out") for e in es)
        old = {e["split"] for e in es if e.get("_batch")}
        if tgt or len(old) > 1:
            sp = "test"
        elif old:
            sp = next(iter(old))
        else:
            new_dom[root] = sorted(e["bucket"] for e in es)[0]
            continue
        for f in fams:
            splits[f] = sp
            if tgt:
                held.add(f)
    new_splits, warns = R.assign_splits_v2(new_dom, held_out=())
    for root, sp in new_splits.items():
        for e in comp[root]:
            splits[e["family"]] = sp
    moved = sorted({e["id"] for e in prev if splits.get(e["family"]) != e["split"]
                    or (e["family"] in held) != bool(e.get("held_out"))})
    return splits, held, warns, moved


def apply_prev_splits(prev: list[dict], splits: dict, held: set):
    """Write changed splits back into earlier batch files and their extracted scenarios (only valid while those scenarios
    have not been perturbed or paired: check before calling)."""
    store = Store()
    by_batch = defaultdict(list)
    for e in prev:
        by_batch[e["_batch"]].append(e)
    for bname, es in by_batch.items():
        f = EPISODES / f"{bname}.yaml"
        doc = yaml.safe_load(f.read_text())
        for e in doc["episodes"]:
            sp, h = splits.get(e["family"], e["split"]), e["family"] in held
            if (sp, h) != (e["split"], bool(e.get("held_out"))):
                e["split"], e["held_out"] = sp, h
                sid = f"DR-{e['id']}@v1"
                try:
                    s = store.scenario(sid)
                except (KeyError, FileNotFoundError):              # rejected / not extracted: batch file only
                    continue
                if any(p.case_scenario == sid or p.trace_scenario == sid for p in store.pairs()):
                    raise SystemExit(f"{sid} is already paired; resplit it with pipeline.ingest resplit instead")
                s.split, s.held_out = sp, h
                s.provenance.step(id="corpus.resplit", operator="extract", ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                  notes=f"split group joined with {BATCH.stem} (shared document or incident, R82): {sp}")
                store.save_scenario(s)
        write_yaml(f, doc)


# ------------------------------------------------------------------ incident groups
INCIDENT_PROMPT = """Below are {n} decisions, each with the title of the document it comes from. Several may concern the SAME
historical incident or the SAME specific decision seen from different documents (for example two accounts of the Inchon
landing decision, or the Gulf of Tonkin incident described by NSA and by a JSOU study). Group them by incident: two items
belong together when they concern the same specific event, operation or crisis (same place and time), even if they describe
different decision points within it. Doctrine and generic situations are never grouped. Do not group items that merely share
a theme (two different covert actions, two different accidents).

Reply with one JSON object: {{"groups": [{{"incident": "<short name>", "items": [<indices>]}}]}} listing ONLY groups of 2 or
more items.

{lines}"""


def incident_families(prev_fam_of_key: dict | None = None) -> dict:
    """(source, n) -> family, from INCIDENTS (accumulated over grouping passes). A group with a member in an earlier
    batch takes that member's family, so the incident keeps the split it already has."""
    if not INCIDENTS.exists():
        return {}
    prev_fam_of_key = prev_fam_of_key or {}
    out = {}
    for g in json.loads(INCIDENTS.read_text()):
        fid = "CORPUS-INC-" + re.sub(r"[^A-Z0-9]+", "-", g["incident"].upper()).strip("-")[:40]
        old = sorted({prev_fam_of_key[tuple(m)] for m in g["members"] if tuple(m) in prev_fam_of_key})
        fid = old[0] if old else fid
        for src, n in g["members"]:
            out[(src, n)] = fid
    return out


def group_incidents(complete_fn=None) -> list[dict]:
    """One Luna call over the current batch's decision lines; new groups are merged into INCIDENTS (a group that shares a
    member with an existing one joins it)."""
    if complete_fn is None:
        from bench.models import complete as complete_fn
    from .extract import parse_json
    b = yaml.safe_load(BATCH.read_text())["episodes"] + previous_batches()     # incidents across batches too
    lines = "\n".join(f"{i}: [{(e.get('title') or '')[:70]}] {e['decision'][:220]}" for i, e in enumerate(b))
    o = parse_json(complete_fn("extractor", [{"role": "system", "content": "Reply with one JSON object only."},
                                             {"role": "user", "content": INCIDENT_PROMPT.format(n=len(b), lines=lines)}],
                               stage="corpus.incident-groups"))
    groups = json.loads(INCIDENTS.read_text()) if INCIDENTS.exists() else []
    for g in o.get("groups") or []:
        mem = [[b[i]["source"], b[i]["n"]] for i in g.get("items") or [] if isinstance(i, int) and i < len(b)]
        if len(mem) < 2:
            continue
        hit = next((x for x in groups if {tuple(m) for m in x["members"]} & {tuple(m) for m in mem}), None)
        if hit:
            hit["members"] = [list(t) for t in sorted({tuple(m) for m in hit["members"] + mem})]
        else:
            groups.append({"incident": g.get("incident", "incident"), "members": mem})
    INCIDENTS.write_text(json.dumps(groups, indent=1, ensure_ascii=False))
    return groups


# ------------------------------------------------------------------ extraction
def _doc_spans(doc_path: str) -> list[dict]:
    return [json.loads(l) for l in (DATA.parent / doc_path).read_text().splitlines() if l.strip()]


def _flags(s) -> list[str]:
    return sorted({f"{p}: {f.match}" for p, f in TC.scan_scenario(s.case.dump()) if f.severity == "strip"})


def extract_one(ep: dict, store: Store, complete_fn=None) -> dict:
    meta = json.loads((CORPUS_META / f"{ep['source']}.json").read_text())
    domain = DOMAIN_OF_BUCKET.get(ep["bucket"], ep["content_domain"] if ep["bucket"] != "other" else "natsec-other")
    source = {"id": ep["source"], "family": ep["family"], "domain": domain, "url": meta.get("url"), "title": ep.get("title"),
              "kind": "national-security corpus document" + (" (doctrine)" if ep["doctrine"] else ""),
              "license": "natsec corpus v1 (data/corpus/natsec/README.md): mostly U.S. government works (public domain); "
                         "others copyrighted, used as source material for extracting decision episodes only",
              "held_out": ep["held_out"], "content_domain": ep["content_domain"],
              "refusal_sensitivity": ep.get("refusal_sensitivity")}
    e2 = {"n": ep["n"], "focus": " ".join(ep["focus"].split()), "span_range": ep["span_range"],
          "content_domain": ep["content_domain"], "refusal_sensitivity": ep.get("refusal_sensitivity")}
    source["episodes"] = [e2]
    spans = _doc_spans(ep["doc"])
    sid = f"DR-{ep['id']}@v1"
    rec = {"episode": ep["id"], "scenario": sid, "family": ep["family"], "bucket": ep["bucket"], "split": ep["split"]}
    scope = SCOPE.read_text()
    addendum, flags, attempt = scope, [], 0
    for attempt in (1, 2, 3):
        try:
            s = extract_episode(source, e2, spans, meta.get("sha256") or "", ep["split"], complete_fn, DATA,
                                addendum=addendum, sid=sid)
        except TechniqueSkip as e:
            return {**rec, "outcome": "rejected", "criterion": 4, "reason": f"extractor skip: {e.reason}", "step": e.step}
        except IncompleteExtraction as e:
            save_incomplete(e, ep["family"], sid, DATA)
            return {**rec, "outcome": "refusal" if e.reason == "refusal" else "incomplete", "reason": str(e)[:300],
                    "refusal": e.refusal}
        except ExtractionError as e:
            return {**rec, "outcome": "incomplete", "reason": str(e)[:300]}
        flags = _flags(s)
        if not flags:
            break
        addendum = (scope + "\n\n### Your previous extraction of this episode contained operational technique. Remove every "
                    "one of these details (replace by its decision-level consequence or omit it):\n- " + "\n- ".join(flags[:30]))
    if flags:
        return {**rec, "outcome": "rejected", "criterion": 4, "reason": "technique remains after two re-extractions",
                "flags": flags[:30]}
    s.held_out, s.split = ep["held_out"], ep["split"]
    s.tags += ["natsec", "corpus", BATCH.stem, f"bucket-{ep['bucket']}"] + (["doctrine-derived"] if ep["doctrine"] else []) \
        + (["held-out-domain"] if ep["held_out"] else [])
    s.case.library["equities"] = EQUITY_SET
    s.provenance.step(id="corpus.scope", operator="extract", ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      notes=(f"{BATCH.stem} episode {ep['id']} ({ep['collection']}); {SCOPE.stem}; equities {EQUITY_SET}; "
                             f"technique screen clean after {attempt} extraction(s)"),
                      params={"attempts": attempt, "bucket": ep["bucket"], "doctrine": ep["doctrine"]})
    store.save_scenario(s)
    return {**rec, "outcome": "ok", "attempts": attempt, "facts": len(s.case.facts), "options": len(s.case.options),
            "choice": s.case.verdict.choice}


def run(workers: int = 16, only=None) -> dict:
    batch = yaml.safe_load(BATCH.read_text())["episodes"]
    done = set()
    if RESULTS.exists():
        final = {"ok", "rejected", "refusal"}                 # errors and incompletes are retried
        done = {r["episode"] for r in map(json.loads, filter(str.strip, RESULTS.read_text().splitlines()))
                if r["outcome"] in final}
    todo = [e for e in batch if e["id"] not in done and (not only or e["id"] in only)]
    print(f"{len(todo)} episodes to extract ({len(done)} already have a result); equities {EQUITY_SET}", file=sys.stderr)
    store = Store()

    def safe(e):
        try:
            r = extract_one(e, store)
        except Exception as ex:                                       # noqa: BLE001 - one bad episode must not sink the batch
            r = {"episode": e["id"], "outcome": "error", "reason": f"{type(ex).__name__}: {ex}"[:300]}
        with open(RESULTS, "a") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(json.dumps(r, ensure_ascii=False)[:240], flush=True)
        return r

    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(safe, todo))
    return dict(Counter(r["outcome"] for r in res))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", default="corpus-batch1", help="batch name: data/store/episodes/<batch>.yaml")
    ap.add_argument("--scope", help="scope addendum prompt name (default corpus_scope.v1; batch 2 on: corpus_scope.v2)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--n", type=int, default=500)
    s.add_argument("--seed", type=int, default=0)
    sub.add_parser("incidents", help="group the current batch by incident (Luna); then run select again")
    r = sub.add_parser("run")
    r.add_argument("--workers", type=int, default=16)
    r.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    configure(a.batch, a.scope)
    if a.cmd == "select":
        print(json.dumps(select(a.n, a.seed), indent=1))
    elif a.cmd == "incidents":
        g = group_incidents()
        print(json.dumps({"groups": len(g), "members": sum(len(x["members"]) for x in g)}))
    else:
        if EQUITY_SET != "pilot2":
            print(f"warning: equity set is {EQUITY_SET}; this batch is meant to use pilot2 (BENCHBOOK_EQUITY_SET=pilot2)",
                  file=sys.stderr)
        print(json.dumps(run(a.workers, set(a.only) if a.only else None)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
