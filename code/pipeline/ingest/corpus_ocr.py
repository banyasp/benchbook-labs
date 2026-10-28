#!/usr/bin/env python3
"""Resumable page-by-page OCR for corpus PDFs flagged needs_ocr (2026-10-27).

  python3 -I corpus_ocr.py OUT_DIR [--ids NS-..,NS-..] [--workers 4] [--dpi 200] [--budget 160]

For each flagged item it renders each page (pdftoppm), runs tesseract, and caches the page text in
OUT_DIR/ocr/<id>/p<NNNN>.txt, so a run killed by a time limit resumes where it stopped. Within --budget seconds
it stops scheduling new pages. When every page of a document is done, it rewrites OUT_DIR/text/<id>.txt
(keeping the header, adding FLAGS ocr) and updates meta (flags: ocr; chars).
"""
import argparse, concurrent.futures as cf, glob, json, os, re, subprocess, tempfile, time


def n_pages(pdf):
    out = subprocess.run(["pdfinfo", pdf], capture_output=True).stdout.decode("utf-8", "replace")
    m = re.search(r"Pages:\s+(\d+)", out)
    return int(m.group(1)) if m else 0


def ocr_page(pdf, page, dest, dpi):
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "p")
        subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(page), "-l", str(page), "-gray", "-png", pdf, base],
                       capture_output=True, timeout=120)
        imgs = glob.glob(base + "*.png")
        txt = ""
        if imgs:
            txt = subprocess.run(["tesseract", imgs[0], "-", "--psm", "3"], capture_output=True,
                                 timeout=180).stdout.decode("utf-8", "replace")
    tmp = dest + ".tmp"
    open(tmp, "w").write(txt)
    os.replace(tmp, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--ids", default=""); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dpi", type=int, default=200); ap.add_argument("--budget", type=float, default=160)
    a = ap.parse_args()
    t0 = time.time()
    metas = {}
    for f in glob.glob(os.path.join(a.out, "meta", "*.json")):
        if f.endswith(".links.json"):
            continue
        m = json.load(open(f))
        if m.get("ok") and m.get("kind") == "pdf" and ("needs_ocr" in m.get("flags", []) or
                                                       (a.ids and m["id"] in a.ids.split(","))):
            metas[m["id"]] = (f, m)
    jobs = []
    for iid, (f, m) in sorted(metas.items()):
        pdf = os.path.join(a.out, "raw", iid + ".pdf")
        d = os.path.join(a.out, "ocr", iid)
        os.makedirs(d, exist_ok=True)
        n = m.get("pages") or n_pages(pdf)
        for p in range(1, n + 1):
            dest = os.path.join(d, f"p{p:04d}.txt")
            if not os.path.exists(dest):
                jobs.append((pdf, p, dest))
    print(f"{len(metas)} docs, {len(jobs)} pages to OCR", flush=True)
    done = 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        pending = set()
        it = iter(jobs)
        while True:
            while len(pending) < a.workers * 2 and time.time() - t0 < a.budget:
                try:
                    pdf, p, dest = next(it)
                except StopIteration:
                    break
                pending.add(ex.submit(ocr_page, pdf, p, dest, a.dpi))
            if not pending:
                break
            fin, pending = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
            done += len(fin)
    print(f"OCR'd {done} pages this run", flush=True)
    for iid, (f, m) in sorted(metas.items()):
        n = m.get("pages") or 0
        d = os.path.join(a.out, "ocr", iid)
        have = sorted(glob.glob(os.path.join(d, "p*.txt")))
        if n and len(have) >= n:
            body = "".join(f"\n\n[[page {i + 1}]]\n" + open(p).read() for i, p in enumerate(have))
            tpath = os.path.join(a.out, "text", iid + ".txt")
            head = open(tpath).read().split("=" * 80 + "\n", 1)[0]
            head = head.replace("needs_ocr", "ocr")
            open(tpath, "w").write(head + "=" * 80 + "\n" + body)
            m["flags"] = [x for x in m.get("flags", []) if x != "needs_ocr"] + ["ocr"]
            m["chars"] = len(body)
            json.dump(m, open(f, "w"), indent=1)
            print(f"complete {iid}: {n} pages, {len(body)} chars", flush=True)
        else:
            print(f"partial  {iid}: {len(have)}/{n} pages", flush=True)


if __name__ == "__main__":
    main()
