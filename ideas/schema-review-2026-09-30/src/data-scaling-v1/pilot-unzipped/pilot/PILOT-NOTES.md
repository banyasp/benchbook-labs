# Pilot notes: real DOHA Guideline F decisions → Benchbook data

*2026-09-29. One agent session, about 33 minutes of wall-clock time from the first fetch to the FISC cases (sandbox clock, `timing.log`). Working folder: `/home/claude/data-scaling/pilot/`.*

## Result in brief

The procedure works end to end on real, post-cutoff public records.

- 80 DOHA hearing decisions dated **Aug 3–Sep 11, 2026** were fetched as full text. Ten Guideline F decisions (5 grants, 5 denials) were converted to schema-valid cases.
- SEAD 4 ¶¶ 18–20 became a catalog. Each condition text is machine-verified against the OCR of the official PDF and, for 16 of 20 texts, against the same wording quoted in independent DOHA decisions.
- The unmodified solver ran on a 6/4 split. **3 of 4 held-out items were decided by precedent and all 3 matched the judge. The 4th (a grant) came out bounded.** This result is weak evidence, for three reasons given below.
- A 15-item, 4,497-word live scenario was re-situated from the bounded item, with a verified salience manifest.
- Three FISC query incidents were converted as a second domain.

Every decision used is dated after my own training cutoff (June 2026) and after the stated cutoffs of current open models.

## Procedure as run

1. **Access probe.** `curl` with a bare user agent got HTTP 403 (Akamai) from `doha.ogc.osd.mil` and from both `dni.gov` hosts. WebFetch reached single DOHA pages, but it returns model-summarized text with a 125-character quote cap, which is unusable for verbatim work. **The fix was sending full browser headers** (User-Agent, Accept, Accept-Language, Sec-Fetch-Mode/Site/Dest, Upgrade-Insecure-Requests). DOHA listings, DOHA decision PDFs and the SEAD 4 PDF then all returned 200. DOE OHA (`energy.gov`) is open to plain curl, and its article pages carry case number, date, disposition, judge and guideline tags. It was not needed as the fallback, but it is the cheapest label source (see recommendation 1). `sgp.fas.org` returned an AWS WAF challenge (202, empty body) and `cdse.edu` returned 403.
2. **SEAD 4.** Downloaded https://archive.dni.gov/files/NCSC/documents/Regulations/SEAD-4-Adjudicative-Guidelines-U.pdf (md5 `b9fa3721…`; identical from www.dni.gov). The PDF is a 27-page scan with no text layer. Ran `pdftoppm -r 300 -gray` and `tesseract --psm 6` per page, then read App. A ¶ 1(d), ¶ 2(a)–(h) and ¶¶ 18–20.
3. **Catalog (`catalog-F.yaml`).** Options A (favorable) and B (unfavorable). Default B, quoting ¶ 2(b) and ¶ 1(d). Seven equities. Nine B-factors (¶ 19(a)–(i)). Eleven A-factors (¶ 20(a)–(g)), with conjunctive conditions split into prongs under different equities (20(b), (c) and (e)) and 20(d) as a two-step scale (`initiated`, `established`). A three-factor **doctrine extension** (BX1 late remediation, BX2 reliance on statutes of limitation, AX1 remediation before the SCA) is kept separate and sourced to Appeal Board language quoted inside the pilot decisions. Five tagging rules. Every judgment is marked `author: draft`.
4. **Quote verification.** A script checks the 22 catalog quotes against the OCR (22 of 22 match). A second, independent check found 16 of the 20 condition texts verbatim in the 80 DOHA decisions. The four not found (19(g), 19(h), 19(i), 20(f): affluence and gambling) are not quoted anywhere in the sample.
5. **Crawl.** Parsed the 2026 listing (606 FileIds). Fetched the 80 highest FileIds (the most recently posted) with a 2-second delay and ran `pdftotext -layout` on each.
6. **Classify** (`tools/classify.py`, regex). Case number, date, guidelines from the Formal Findings, outcome from the Conclusion. 50 decisions were flagged F. Reading showed at least 2 false positives (ISCR 24-02233 is H/E; 25-00899 is B), so ≥ 48 are F, with 8 grants, 39 denials and 1 unparsed. The F grant rate is about 17%.
7. **Select** 5 grants and 5 denials for pattern diversity: pandemic unemployment, overspending, taxes plus caregiving, a medical emergency discharged in bankruptcy, overseas job loss, identity theft with non-filing, unpaid student loans, deliberate non-filing, years of non-filing cured by an offer in compromise, and repeat bankruptcies with a Guideline E cross-finding.
8. **Read lean** (`tools/lean.py`). Stripping the Policies section, the AG ¶ 18 and ¶ 2(d) boilerplate and exhibit citations cuts reading by roughly 30–60%.
9. **Convert** (`cases/DOHA-F-01…10.yaml`, ≤ 350 words each).
   - Tags follow the judge's findings.
   - For grants, the `reason` is the conditions the judge says apply. For denials, it is the B-factors the judge leaves unmitigated.
   - `reason_cite` gives a page and a verbatim anchor.
   - `flip_rules` come only from decision text: split formal findings, "may be able to qualify … in the future", and warning language.
   - `watch_for` comes from the whole-person and credibility passages.
   - Each case carries a `conversion.misfits` list.
10. **Validate** (`tools/validate_cases.py`). IDs exist in the catalog; `reason ⊆ facts`; the anchor is verbatim and on the cited page; single-quoted fragments are verbatim; the case block is ≤ 350 words. The script builds `cases-all.yaml`.
11. **Held-out** (`run_heldout.py`, which imports the unmodified `solver_v2.py`). Run 1 uses SEAD 4 only; run 2 adds the doctrine extension; run 3 is a sensitivity run with one equity per factor. Each run also has a leave-one-out pass and two baselines (always deny, and 1-NN by Jaccard on tags). Output: `heldout-results.md`.
12. **Live scenario** (`live-scenario/`). Built from the bounded held-out item (DOHA-F-03). The re-situation map is in `salience.yaml`. 15 items; salience spans are verbatim-checked and the noise share is measured (`tools/check_salience.py`).
13. **Optional FISC.** The April 21, 2022 opinion has a text layer. The incident list is on pp. 26–29. Built a mini-catalog (the querying standard's three prongs) and three cases, with quotes verified and OCR errors bracketed.

## Time per step (sandbox wall clock)

| Step | Minutes |
|---|---|
| Access probe, SEAD 4 fetch and OCR | 6.1 |
| Crawl 80, classify, read 11 decisions (10 used + 1 reserve) | 5.0 |
| Catalog written and verified | 4.1 |
| Draft 10 cases | 2.9 (0.2–0.4 each) |
| Validate and fix | 1.0 |
| Held-out runner and results | 0.9 (plus about 2 for the sensitivity run and interpretation) |
| Live scenario (15 items), salience manifest, README | 7.9 |
| FISC (3 cases and catalog) | 1.4 |
| **Total** | **≈ 33** |

**Per-case conversion by the LLM** was about 0.5 min of reading share, 0.2–0.4 min of drafting and 0.1 min of validation, **≈ 1 minute of machine time**. The human time is what matters (next section).

## What broke

- **Access.** Without full headers every .mil and dni.gov fetch failed. WebFetch looked like it worked but cannot quote. *Lesson:* test for verbatim-capable access first.
- **A self-contradictory decision.** ISCR 25-01260 (DOHA-F-09) concludes "it is clearly consistent with the interests of national security … to grant or continue Applicant's national security eligibility … Eligibility for access to classified information is denied." The Formal Findings say AGAINST. A regex on the Conclusion's first clause would mislabel it.
- **Decision-internal inconsistencies.** ISCR 25-00861 gives "approximately $54,000" but itemizes about $41,600. It also names the debt-program accounts as 1.c/1.f in one paragraph and 1.c/1.e in the SOR list.
- **The classifier.** At least 2 of the 50 F flags are false positives, and 5 of 80 outcomes did not parse. Gold labels must come from Formal Findings, with human confirmation.
- **My own conversion errors, caught by the scripts:**
  - a wrong counsel field (typed "retained"; the decision says pro se);
  - two cases over the word cap;
  - one paraphrase inside quote marks ("does not recognize"; the decision says not "knowledgeable of the details of this account");
  - a FISC phrase reconstructed from a redacted, garbled line and presented as a quote;
  - one wrong page citation (p. 37 for p. 39);
  - two YAML syntax errors;
  - a placeholder `minutes` value typed before measuring.

  Every one was fixed. **None would have been caught without the checkers.**
- **Anchors that span a page footer fail** (page numbers interrupt the text). Keep anchors within one page.
- **A solver semantics issue.** `analyse()` treats a distinction as downplayed if *any* of its equities is substituted. DOHA-F-04's correct "analogous → grant" depends on this: A20d@established was downplayed through `responsible_conduct` while nothing covered `current_burden`. With one equity per factor, F-04 becomes bounded.
- **Circularity.** Tags taken from the judge's findings nearly encode the verdict. That is fine for exemplars and fatal for a held-out test.

## Schema misfits, ranked by how often they bit

1. **Unnamed or partially applied mitigators (5 of 10 cases).** Two judges granted without naming any ¶ 20 subparagraph (F-01, F-05). Others found 20(b) "partially" (F-07, F-09, F-10), and the scale step of 20(d) ("albeit recently" in F-04 vs "too soon" in F-10) is judge-dependent. The reason set is then the converter's inference.
2. **Credibility and temporal judgments (6 of 10).** "Implausible and unpersuasive" (F-06), "candid, sincere, forthcoming" (F-03), a FORM case where credibility could not be assessed but a promise was still called "credible" (F-04), and "not … at this time" / "may well be able to" (F-06, F-09, F-10). These decide cases but live only in `watch_for`.
3. **Allegation-level structure and cross-guideline findings (6 of 10).** Split formal findings: one unmitigated allegation outweighed nine mitigated ones (F-09). A tax year was found for the applicant while the next was found against (F-06). An old bankruptcy was found for him inside a denial (F-08). Guideline E rode alongside F (F-10: the SCA omission was mitigated, a pattern of rule violations was not). The case schema has one outcome and one reason set.

Also seen:
- Appeal Board doctrine that is not in SEAD 4 (timing of remediation, statutes of limitation, garnishment is not good faith, documentation required). This motivated the extension.
- Conditions the judge left unargued (19(b) unwillingness fits F-07, F-08 and F-10 on the facts, but no judge cited it).
- Use-limited facts (unalleged conduct counts for credibility only).
- Legal-status resolutions (a bankruptcy discharge counted as "otherwise resolve").

## What the LLM did well and poorly

**Well:**
- Locating the dispositive sentence.
- Mapping named ¶ conditions to catalog IDs (near-deterministic when the judge cites them).
- Separating allegation-level outcomes.
- Writing short, faithful holdings.
- Noticing doctrine the catalog lacks.
- Re-situating a record while keeping its pattern.
- Producing varied noise documents in several genres.

**Poorly, or only safely with checkers:**
- **Inferring reasons** where the judge names none: plausible but unverifiable.
- **Scale calls** (initiated vs established).
- **Quote hygiene:** paraphrases drift inside quote marks, and redacted or garbled text gets "repaired".
- **Metadata filled from expectation** rather than read (the counsel field).
- **Tagging what the judge did not find** (19(b)). A rule prevented it here; an unconstrained extractor would over-tag.
- **Texture that shifts the facts.** One invented scenario detail sent 401(k) money to the father's care and was removed. Invented texture has to be audited against the pattern.

## Human review time per case (single labeler; estimate, not measured)

Formula: 0.4 × decision words ÷ 250 wpm + 4 min, plus 2 min above 5,000 words. The reviewer reads the Analysis and Formal Findings, skims the facts, checks tags, reason and flip rules, and signs.

- 7–9 min for the 1,900–3,050-word decisions (8 of 10).
- 17–21 min for the two long ones (6,800 and 9,500 words).
- **Mean ≈ 10 min, median ≈ 8 min.**
- The live scenario takes ≈ 30–45 min to review (4,500 words plus the salience manifest), and ≈ 10 min to write a blind A-gold label first.
- At 300 cases: ≈ 50 h if every case is reviewed in full; **≈ 20–25 h** if two independent extractors plus the script gates route only disagreements and a 15–20% audit to the reviewer.

## Five recommendations for scaling to ~300 DOHA/DOE cases

1. **Harvest gold from structure, not prose, and add DOE for free labels.**
   - Parse each subparagraph's "For/Against Applicant" line and the paragraph-level finding. Treat the Conclusion only as a cross-check, and queue any disagreement (as in 25-01260).
   - DOE OHA article pages give disposition, judge and guideline tags without parsing, and curl reaches them directly.
   - Restrict held-out items to decisions dated after the base model's cutoff. DOHA posts about 600 a year, and in this sample about 60% involve Guideline F, so 300 post-cutoff F decisions is about half a year of output.
2. **Split the two tagging modes and never mix them.**
   - *Judge-perception* tags (from the findings) are for exemplars.
   - *Record-perception* tags are produced blind from a neutralized pre-decision record by the model under test. Only these make the held-out test informative.
   - Automate neutralization from the Findings of Fact (strip "established", "credible", "mitigated"), then re-situate as in `live-scenario/`.
3. **Fix the schema where the misfits cluster, then measure coverage by leave-one-out.**
   - (a) Decide per-equity vs any-equity downplay in `analyse()`.
   - (b) Add per-allegation units: an outcome and reason per SOR subparagraph, rolled up by rule.
   - (c) Keep the doctrine layer as named, sourced factors (timing, statutes of limitation, garnishment, documentation).
   - (d) Calibrate scale steps for 20(d) and a "partial" step for 20(b) from about 30 labeled cases.
   - (e) Add a `credibility: {finding, basis}` slot and a `use_limited` flag on facts.
   - Report LOO coverage (share decided by precedent) and accuracy after each change. Here it was 4/10 (SEAD 4), 5/10 (with doctrine) and 3/10 (one equity per factor), all correct.
4. **Stratify, because grants are scarce.** Only about 17% of F decisions in the crawl were grants, and a grant precedent binds only for its mitigator combination.
   - Sample by pattern (tax non-filing, tax non-payment, bankruptcy, medical debt, student loans, overspending, identity theft, gambling) × outcome, and aim for ≥ 8 grants per pattern.
   - Pull DOHA Appeal Board reversals and remands as *contested* items (two trained adjudicators disagreed on the same record).
   - Keep a 1-NN baseline in every table. This pilot could not separate the solver from it.
5. **Make verification mechanical and keep the human for judgment.**
   - Two extractors from different model families.
   - Script gates on every anchor and quote (verbatim, correct page), `reason ⊆ facts`, catalog IDs, word caps, and privacy rules: drop diagnoses, disability ratings and criminal specifics; re-situate quasi-identifiers.
   - The review queue holds disagreements, a 15% audit, and every held-out item, labeled blind for A-gold before R-gold is revealed.
   - Keep a hashed local mirror of every PDF (80 decisions ≈ 27 MB) and crawl politely (≥ 2 s between requests).

## Privacy and hygiene notes

- All sources are official public releases: DOHA decisions (redacted), the SEAD 4 PDF from dni.gov, and the FISC opinion as released by ODNI on intelligence.gov. No leaked material was used.
- Case files paraphrase at the level of the published decision. Specific diagnoses (DOHA-F-05), disability ratings (DOHA-F-09) and criminal specifics (DOHA-F-10) were deliberately left out.
- The live scenario invents every person, company, account number and place. Real agency and form names appear only as conventions, and the folder README marks it as synthetic.
- Raw decision PDFs and texts are in `raw/` for provenance only. They should not leave Peter's machine in bulk.
