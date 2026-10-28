#!/usr/bin/env python3
"""Fetch a URL manifest into a text corpus (natsec decision sources, 2026-10-27).

Usage:
  python3 -I corpus_fetch.py MANIFEST.json OUT_DIR [--workers 6] [--only ID,ID] [--retry-failed]

For each manifest item {id, url, ...} it writes:
  OUT_DIR/raw/<id>.<ext>      original bytes (kept off git; large)
  OUT_DIR/text/<id>.txt       extracted text (PDF via pdftotext -layout; HTML/XML via BeautifulSoup)
  OUT_DIR/meta/<id>.json      url, final_url, via, http status, sha256, bytes, content type, pages, chars, flags
and appends one line per attempt to OUT_DIR/log.jsonl. Resumable: items with a meta file marked ok are skipped.

Access rules (brief W8b): honest User-Agent, no spoofing, no proxies. If the host refuses (401/402/403/429) or
times out, it tries a public archive copy instead -- the Internet Archive's DTIC collection for DTIC
reports, then the Wayback Machine's stored copy -- and records `via`. Anything still refused is listed as
blocked for a manual download in a browser.
"""
import argparse, concurrent.futures as cf, hashlib, json, os, re, subprocess, sys, time, urllib.parse

import requests
from bs4 import BeautifulSoup

UA = "benchbook-labs-research/0.1 (academic research on public decision records)"
MAX_BYTES = 400 * 1024 * 1024
BOT = re.compile(r"just a moment|cf-chl|challenge-platform|access denied|request rejected|are you a robot|"
                 r"captcha|enable javascript and cookies", re.I)
REFUSED = {401, 402, 403, 405, 429, 451, 503}


def alt_urls(url):
    alts = []
    m = re.search(r"apps\.dtic\.mil/sti/(?:pdfs|tr/pdf)/(A[DB]\w+)\.pdf", url, re.I)
    if m:
        d = m.group(1).upper()
        alts.append(("archive.org-dtic", f"https://archive.org/download/DTIC_{d}/DTIC_{d}.pdf"))
    m = re.match(r"https?://arxiv\.org/abs/([\w.]+)", url)
    if m:
        alts.insert(0, ("arxiv-pdf", f"https://arxiv.org/pdf/{m.group(1)}"))
    alts.append(("wayback", "https://web.archive.org/web/2026id_/" + url))
    return alts


def get_curl(url):
    """Fallback when Python's TLS stack fails (e.g. a host's certificate chain): system curl, same honest UA."""
    out = subprocess.run(["curl", "-sS", "-L", "--max-time", "300", "-A", UA, "-D", "-", "-o", "/dev/stdout", url],
                         capture_output=True, timeout=320)
    raw = out.stdout
    # split the last header block from the body
    parts = raw.split(b"\r\n\r\n")
    body_start, status, ctype = 0, 0, ""
    i = 0
    while raw[i:i + 5] == b"HTTP/":
        end = raw.find(b"\r\n\r\n", i)
        if end < 0:
            break
        head = raw[i:end].decode("latin-1")
        m = re.match(r"HTTP/\S+\s+(\d+)", head)
        status = int(m.group(1)) if m else 0
        m = re.search(r"(?im)^content-type:\s*(.+)$", head)
        ctype = m.group(1).strip() if m else ""
        i = end + 4
    return status, url, ctype, raw[i:]


def get(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=(20, 240), stream=True, allow_redirects=True)
    except requests.exceptions.SSLError:
        return get_curl(url)
    buf = bytearray()
    for chunk in r.iter_content(1 << 16):
        buf += chunk
        if len(buf) > MAX_BYTES:
            break
    return r.status_code, r.url, r.headers.get("content-type", ""), bytes(buf)


def kind_of(ctype, data, url):
    if data[:5] == b"%PDF-":
        return "pdf"
    if "xml" in ctype and "html" not in ctype:
        return "xml"
    if "html" in ctype or data.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
        return "html"
    if "json" in ctype:
        return "json"
    return "bin"


def pdf_text(path):
    out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, timeout=900)
    txt = out.stdout.decode("utf-8", "replace")
    info = subprocess.run(["pdfinfo", path], capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
    m = re.search(r"Pages:\s+(\d+)", info)
    return txt, int(m.group(1)) if m else None


def html_text(data):
    soup = BeautifulSoup(data, "html.parser")
    for t in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "iframe", "svg"]):
        t.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    main = soup.find("main") or soup.find("article") or soup.body or soup
    txt = main.get_text("\n", strip=True)
    links = []
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith(("mailto:", "javascript:", "#")):
            continue
        links.append([a.get_text(" ", strip=True)[:150], h])
    return title, re.sub(r"\n{3,}", "\n\n", txt), links


def process(item, out, retry_failed):
    iid, url = item["id"], item["url"]
    mpath = os.path.join(out, "meta", iid + ".json")
    if os.path.exists(mpath):
        prev = json.load(open(mpath))
        if prev.get("ok") or not retry_failed:
            return prev
    attempts, chosen = [], None
    for via, u in [("direct", url)] + alt_urls(url):
        try:
            st, final, ctype, data = get(u)
        except Exception as e:  # timeout, DNS, reset
            attempts.append({"via": via, "url": u, "error": type(e).__name__ + ": " + str(e)[:160]})
            continue
        k = kind_of(ctype, data, u)
        # Challenge pages are small and say so near the top; long real pages can mention "captcha" etc. in passing.
        bot = k == "html" and len(data) < 40_000 and bool(BOT.search(data[:40_000].decode("utf-8", "replace")))
        attempts.append({"via": via, "url": u, "status": st, "bytes": len(data), "kind": k, "bot_page": bot})
        if st == 200 and data and not bot:
            chosen = (via, u, final, ctype, data, k)
            break
        if via == "direct" and st == 404:
            continue  # dead link: still try archive copies
    meta = {**item, "attempts": attempts, "ok": False, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if chosen:
        via, u, final, ctype, data, k = chosen
        ext = {"pdf": "pdf", "html": "html", "xml": "xml", "json": "json"}.get(k, "bin")
        raw = os.path.join(out, "raw", f"{iid}.{ext}")
        open(raw, "wb").write(data)
        txt, pages, title, links = "", None, "", []
        try:
            if k == "pdf":
                txt, pages = pdf_text(raw)
            elif k in ("html", "xml"):
                title, txt, links = html_text(data)
            elif k == "json":
                txt = data.decode("utf-8", "replace")
        except Exception as e:
            meta["convert_error"] = type(e).__name__ + ": " + str(e)[:200]
        flags = []
        if k == "pdf" and pages and len(txt.strip()) / max(pages, 1) < 300:
            flags.append("needs_ocr")
        if len(data) >= MAX_BYTES:
            flags.append("truncated_download")
        if k == "html" and len(txt) < 1500:
            flags.append("thin_page")
        header = (f"SOURCE_ID: {iid}\nURL: {url}\nFETCHED_FROM: {u} (via {via})\nTITLE: {item.get('title') or title}\n"
                  f"CATALOG: {item.get('part')} / {item.get('section')}\nLABEL: {item.get('label')}\n"
                  f"KIND: {k}  PAGES: {pages}  FLAGS: {','.join(flags) or '-'}\n" + "=" * 80 + "\n")
        open(os.path.join(out, "text", iid + ".txt"), "w").write(header + txt)
        if links:
            json.dump(links, open(os.path.join(out, "meta", iid + ".links.json"), "w"))
        meta.update(ok=True, via=via, fetched_url=u, final_url=final, content_type=ctype, kind=k, bytes=len(data),
                    sha256=hashlib.sha256(data).hexdigest(), pages=pages, chars=len(txt), page_title=title,
                    flags=flags, n_links=len(links))
    json.dump(meta, open(mpath, "w"), indent=1)
    with open(os.path.join(out, "log.jsonl"), "a") as f:
        f.write(json.dumps({"id": iid, "ok": meta["ok"], "via": meta.get("via"), "url": url}) + "\n")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest"); ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", default="")
    ap.add_argument("--retry-failed", action="store_true")
    a = ap.parse_args()
    for d in ("raw", "text", "meta"):
        os.makedirs(os.path.join(a.out, d), exist_ok=True)
    items = json.load(open(a.manifest))
    if a.only:
        keep = set(a.only.split(","))
        items = [i for i in items if i["id"] in keep]
    done = ok = 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(process, i, a.out, a.retry_failed): i for i in items}
        for fu in cf.as_completed(futs):
            done += 1
            try:
                m = fu.result()
                ok += bool(m.get("ok"))
                print(f"[{done}/{len(items)}] {'ok ' if m.get('ok') else 'BLOCKED'} {m['id']} {m.get('via','')} "
                      f"{m.get('kind','')} {m.get('pages') or ''} {futs[fu]['url'][:90]}", flush=True)
            except Exception as e:
                print(f"[{done}/{len(items)}] ERROR {futs[fu]['id']}: {e}", flush=True)
    print(f"done: {ok}/{len(items)} ok", flush=True)


if __name__ == "__main__":
    sys.exit(main())
