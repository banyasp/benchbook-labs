#!/usr/bin/env python3
"""Assemble fetched corpus builds into the repo corpus (data/corpus/natsec/).

  python3 -I corpus_assemble.py REPO_CORPUS_DIR BUILD_DIR [BUILD_DIR ...]

Copies text/<id>.txt and meta/<id>.json (+ .links.json) for every ok item from each build (later builds win
only if the earlier one failed), then writes index.csv (one row per manifest item, ok or not) and blocked.csv.
Raw files are not copied; they stay in the build directories (Peter's Mac keeps the permanent raw store).
"""
import csv, glob, json, os, shutil, sys


def main():
    dest, builds = sys.argv[1], sys.argv[2:]
    for d in ("text", "meta"):
        os.makedirs(os.path.join(dest, d), exist_ok=True)
    best = {}
    for b in builds:
        for f in glob.glob(os.path.join(b, "meta", "*.json")):
            if f.endswith(".links.json"):
                continue
            m = json.load(open(f))
            cur = best.get(m["id"])
            if cur is None or (not cur[1].get("ok") and m.get("ok")):
                best[m["id"]] = (b, m)
    rows, blocked = [], []
    for iid, (b, m) in sorted(best.items()):
        m = {k: v for k, v in m.items() if k != "attempts"} | {"attempts": m.get("attempts", [])}
        json.dump(m, open(os.path.join(dest, "meta", iid + ".json"), "w"), indent=1)
        if m.get("ok"):
            shutil.copyfile(os.path.join(b, "text", iid + ".txt"), os.path.join(dest, "text", iid + ".txt"))
            lk = os.path.join(b, "meta", iid + ".links.json")
            if os.path.exists(lk):
                shutil.copyfile(lk, os.path.join(dest, "meta", iid + ".links.json"))
        row = {"id": iid, "ok": int(bool(m.get("ok"))), "collection": m.get("section") or "",
               "part": m.get("part") or "", "title": (m.get("title") or m.get("page_title") or "")[:200],
               "url": m["url"], "via": m.get("via") or "", "kind": m.get("kind") or "",
               "pages": m.get("pages") or "", "chars": m.get("chars") or 0,
               "flags": ",".join(m.get("flags", [])), "catalog_status": m.get("status") or ""}
        rows.append(row)
        if not m.get("ok"):
            last = (m.get("attempts") or [{}])[-1]
            blocked.append({"id": iid, "collection": row["collection"], "title": row["title"], "url": m["url"],
                            "last_attempt": f"{last.get('via','')} {last.get('status') or last.get('error','')}"[:120]})
    with open(os.path.join(dest, "index.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(dest, "blocked.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "collection", "title", "url", "last_attempt"])
        w.writeheader(); w.writerows(blocked)
    ok = sum(r["ok"] for r in rows)
    print(f"{len(rows)} items, {ok} ok, {len(blocked)} blocked; text {sum(r['chars'] for r in rows) / 1e6:.1f} M chars")


if __name__ == "__main__":
    main()
