# National-security decision corpus (natsec), v1 — 2026-10-28

Source material for Benchbook decision episodes (design v2.4.1; build brief W8b). Built in Peter's Claude session
from his catalog `docs/natsec-decision-sources-v1.md`, every collection that catalog points to, and a doctrine
set Peter asked for ("doctrine manuals have a lot of value, assuming they're detailed enough to build a scenario").

**3,011 of 3,378 documents have text (about 295 M characters).** One text file per document.

## Layout

| Path | What |
|---|---|
| `text/<id>.txt` | Header (source id, URL, where it was fetched from, title, catalog section, kind, pages, flags), a line of `=`, then the full extracted text |
| `meta/<id>.json` | Fetch record: url, final url, `via`, HTTP status, sha256, bytes, pages, chars, flags, every attempt |
| `meta/<id>.links.json` | Links found on HTML pages (for further crawling) |
| `index.csv` | One row per manifest item, ok or not: id, collection, title, url, via, kind, pages, chars, flags |
| `blocked.csv` | Items with no text yet, with the last error: candidates for a manual browser download |
| `manifest.catalog.json` | The catalog's 244 links (ids `NS-…`) |
| `manifest.expansion.json` | 3,134 documents enumerated from the collections plus the doctrine set (ids `NX-…`) |

Ids are `NS-`/`NX-` + the first 8 hex digits of sha1(url), so they are stable across re-runs.

## What is in it

| Collection | With text / listed | Text |
|---|---|---|
| studies-in-intelligence | 1482 / 1482 | 54.4 M |
| jsou | 238 / 238 | 48.8 M |
| cia-csi-books | 109 / 109 | 28.0 M |
| call | 259 / 260 | 24.6 M |
| chilcot | 13 / 13 | 23.4 M |
| catalog Part A | 74 / 79 | 15.1 M |
| nsa-cch | 99 / 100 | 14.5 M |
| catalog Part D | 46 / 60 | 12.1 M |
| doctrine | 48 / 80 | 11.9 M |
| usaf-aib | 137 / 141 | 8.9 M |
| catalog Part B | 52 / 56 | 8.9 M |
| church | 6 / 6 | 8.8 M |
| catalog Part C | 45 / 49 | 7.7 M |
| cia-publications | 35 / 35 | 6.8 M |
| aup-csi | 5 / 6 | 5.3 M |
| ssci-commissions | 35 / 36 | 5.0 M |
| nsarchive-ablearcher | 63 / 63 | 2.8 M |
| walsh | 46 / 46 | 2.4 M |
| nsarchive-dia | 53 / 53 | 1.8 M |
| nsarchive-bop | 13 / 13 | 1.0 M |
| icrc-casebook | 48 / 260 | 0.9 M |
| uruzgan | 38 / 38 | 0.6 M |
| nsa-tonkin | 15 / 15 | 0.6 M |
| mwi-urban | 15 / 15 | 0.5 M |
| cia-kent | 8 / 8 | 0.2 M |
| nsa-pueblo | 15 / 15 | 0.2 M |
| aclu-drone | 5 / 5 | 0.0 M |
| nwc-monographs | 9 / 32 | 0.0 M |
| nwc-newport | 0 / 48 | 0.0 M |
| ndu-cases | 0 / 13 | 0.0 M |
| mcu-press | 0 / 4 | 0.0 M |

Collections: CIA Center for the Study of Intelligence (books and monographs; the publications packages; *Studies
in Intelligence* 1955–2026; Kent Center papers); NSA Center for Cryptologic History (+ the Gulf of Tonkin and
Pueblo releases); JSOU Press; CALL; USAF accident investigation boards; ICRC casebook; NSArchive briefing books
(Bay of Pigs, DIA sourcebook, Able Archer 83); the Uruzgan AR 15-6 (ACLU FOIA); ACLU drone documents; Church
Committee; the Walsh Iran-Contra report; Senate intelligence-related commissions (incl. Rockefeller); Chilcot;
MWI urban case studies; CSI staff rides and *In Contact!*; and doctrine (joint, Army, USMC, USAF, Navy, NATO/UK,
ROE and law of war, IC directives, released targeting-approval policy such as the 2013 PPG and 2017 PSP).

## Flags

- `needs_ocr`: a scanned PDF with no text layer; the text file has only its header. OCR is running in batches
  (`code/pipeline/ingest/corpus_ocr.py`); finished documents are re-committed with the flag `ocr`.
- `ocr`: text produced by tesseract (expect OCR noise). `alt_text`: text taken from an archive's OCR of the same
  document (e.g. archive.org's DTIC copy). `thin_page`: an HTML page with little text (often a landing page).

## Provenance and access

Fetched with an honest User-Agent (`benchbook-labs-research/0.1`), no spoofing or proxies (W8b). When a host refused,
the fetcher used a public archive copy (archive.org's DTIC collection, the Wayback Machine) and records it in
`via`. Two machines fetched: Peter's Claude workspace and his laptop (via the desktop app), since hosts block
differently. Raw files are kept off git: the permanent raw store is on Peter's Mac,
`Applications - Claude accessible/Extension Training/natsec-corpus/raw/`.

Regenerate: `python3 -I code/pipeline/ingest/corpus_fetch.py <manifest> <out> [--retry-failed] [--only ids]`, then
`corpus_ocr.py`, then `corpus_assemble.py data/corpus/natsec <build dirs…>`.

## Use rules

- **Private research corpus.** Most items are U.S. government works (public domain). Others (RAND, HRW, ICRC, NSArchive
  essays, news, journal articles, UK and NATO publications) are copyrighted: use them as source material for
  extracting decision episodes; don't redistribute or publish the text. Peter checks terms before training directly on any text.
- **Scope (design §4.2, brief W8b).** Episodes are extracted at the level of the decision: decider, options,
  equities, authority, legal standard, reasoning, outcome. Operational technique (weapon and munition selection,
  collateral-damage computations, sensor and attack procedures, intrusion or collection methods) is stripped and
  never appears in cards or traces. Doctrine-derived scenarios are tagged `doctrine-derived`.
- Some FOIA releases carry their original classification banners. They are officially released documents.

## Known gaps (see `blocked.csv`)

- ICRC casebook: 48 of 260 (the site blocks scripted access; archive copies missing).
- Naval War College Historical Monographs and Newport Papers, NDU case studies, MCU Press: their repositories
  refuse scripted downloads; a browser works.
- FAS IRP doctrine copies, jcs.mil joint publications, RAND reports: blocked.
- Not enumerated yet: Pueblo and Tonkin pages beyond the first; CIA Reading Room collections; FRUS (552 volumes,
  available as XML on GitHub); Airwars incident archive; Hoover wargaming archive; CAAF opinions; ICTY judgments.
