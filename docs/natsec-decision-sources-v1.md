# National-Security Decision Sources: Link Catalog (v1, 2026-10-27)

## What this is

A list of public online sources of **real national-security decision episodes**, gathered for the Benchbook (Extension Training) corpus. A usable episode has:
- a decider
- the options available
- a tension between equities
- ideally the decision taken, the stated reasoning and the outcome

Peter wants operational and tactical military decisions, including weapons employment and targeting, plus intelligence-agency decisions. He reviews sources himself and decides what goes in. Do not filter on content.

## How the list was built

- **Part A** comes from the Sep 2026 data-scaling research. The full set of roughly 400 links is in the Mac folder `Applications - Claude accessible/Extension Training/`:
  - `data-scaling-v1/research/B-natsec-evals-and-case-libraries.md`
  - `data-scaling-v1/research/C-adjudicated-decisions.md`
  - `data-scaling-v1/research/D-authentic-noise-corpora.md`
  - `research/18-natsec-decision-formats.md`
  - `scenarios/hard-calls-v1/research/*.md`
  - The 150-row catalog with license and fit columns, but no URLs, is `data-scaling-v1/source-catalog.csv`.
- **Parts B–D** come from three web-research passes on 2026-10-27.

## Status tags

- **[V]** opened and content confirmed.
- **[T]** existence confirmed from a listing or title page, but the item was not opened.
- **[U]** unverified: blocked, 404, or seen only in search results.

## Access notes for a scraping agent

These hosts often return 403 to curl or scripts but open in a browser or WebFetch:
- media.defense.gov, apps.dtic.mil, nsa.gov
- dni.gov, intelligence.gov, senate.gov
- rand.org, esd.whs.mil, doctrine.af.mil
- armyupress.army.mil, history.army.mil, usni.org, nytimes.com

Other blocks:
- DOHA and cdse.edu PDFs block automated clients. Get permission or bulk access before scaling.
- The CIA FOIA Reading Room was in maintenance on 2026-10-27.

Scanned or heavily redacted items need OCR. They are marked **(OCR)**.

---

## Part A: Earlier list (Sep 2026 research)

### A1. Military academies and doctrine
- **USNA *Ethics for Leadership* casebook (ELJO, 2009 ed.).** Stockdale Center casebook of officer ethical dilemmas. [V] https://www.usna.edu/Ethics/_files/documents/ELJO2009.pdf
- **Army CAPE case studies (2016 snapshot).** Ethics cases with facilitator "book answers"; captured from cape.army.mil by the UNT web archive. [V] https://webarchive.library.unt.edu/web/20161021000807mp_/http://cape.army.mil/case-studies
- **CALL Handbook 11-33, ch. 2.** Joint-community observation and lessons-learned format. [V] https://www.globalsecurity.org/military/library/report/call/call_11-33-ch2.htm
- **CALL 00-4, ch. 2.** Decision support for executing pre-wargamed decisions quickly during operations. [V] https://www.globalsecurity.org/military/library/report/call/call_00-4_ch2.htm
- **Operational Law Handbook 2022 (JAG School).** ROE and law-of-war reference; not a case library. [V] https://tile.loc.gov/storage-services/service/ll/llmlp/2022_Operational_Law_Handbook/2022_Operational_Law_Handbook.pdf
- **Law of Armed Conflict Deskbook 2013.** 260 pp. [V] https://tile.loc.gov/storage-services/service/ll/llmlp/LOAC-Deskbook-2013/LOAC-Deskbook-2013.pdf
- **DoD Law of War Manual (2015, updated 2023).** The official copy may 403. [T] https://media.defense.gov/2023/Jul/31/2003271432/-1/-1/0/dod-law-of-war-manual-june-2015-updated-july%202023.pdf; archive.org mirror [V] https://archive.org/details/dod-law-of-war-manual-june-2015-updated-july-2023
- **ADP 5-0, The Operations Process.** [V] https://irp.fas.org/doddir/army/adp5_0.pdf
- **ADP 6-0, Mission Command.** [V] https://irp.fas.org/doddir/army/adp6_0.pdf
- **NATO JALLC Lessons Learned Handbook (4th ed., 2022).** [V] https://www.jallc.nato.int/application/files/4416/5781/2017/JALLC_LL_Handbook_Update_-_4th_Edition_FINAL_14072022.pdf

### A2. Operational incidents with investigations
- **USS *Vincennes* / Iran Air 655 (1988), Fogarty formal investigation.** [V] https://apps.dtic.mil/sti/pdfs/ADA203577.pdf (also https://archive.org/details/DTIC_ADA203577)
- **Patriot fratricides (2003), Defense Science Board task force summary (2005).** [V] https://www.govinfo.gov/content/pkg/GOVPUB-D-PURL-LPS66633/pdf/GOVPUB-D-PURL-LPS66633.pdf
- **Kunduz MSF hospital strike (2015), CENTCOM summary via Public Intelligence.** [V] https://publicintelligence.net/centcom-kunduz-hospital-attack/
- **Kunduz (2016) vs. Kabul (2021) investigations.** Just Security analysis by Eugene Fidell. [V] https://www.justsecurity.org/78914/the-missing-kabul-drone-strike-report/
- **Kabul drone strike (2021).** Air Force IG briefing citing "confirmation bias." [V] https://www.airandspaceforces.com/confirmation-bias-cited-in-erroneous-strike-that-killed-10-civilians-in-afghanistan/
- **Brereton / IGADF Afghanistan Inquiry (Australia, public redacted release).** [V] https://www.defence.gov.au/sites/default/files/2021-10/IGADF-Afghanistan-Inquiry-Public-Release-Version.pdf
- **Baha Mousa Public Inquiry (UK, 2011).** [V] https://www.gov.uk/government/publications/the-baha-mousa-public-inquiry-report
- **NTSB report on the USS *Fitzgerald* collision (MAR-20/02).** 50 pp. [V] https://www.ntsb.gov/investigations/AccidentReports/Reports/MAR2002.pdf
- **USAF accident investigation boards index.** Air & Space Forces Magazine; includes about 55 MQ-1/MQ-9/RQ-4 reports. [V] https://www.airandspaceforces.com/docs/type/accident/
- **EP-3 collision and crew detainment (2001).** Naval History and Heritage Command. [V] https://www.history.navy.mil/research/archives/Collections/ncdu-det-206/2001/ep-3-collision--crew-detainment-and-homecoming.html
- **World Central Kitchen convoy strike (2024).** Australia's Special Adviser (Binskin) report. [V] https://www.dfat.gov.au/sites/default/files/special-advisers-public-report-israels-response-wck-strikes-august-2024.pdf
- ***United States v. Behenna*, 71 M.J. 228 (CAAF 2012).** Law-of-war self-defense case. [V] https://www.armfor.uscourts.gov/newcaaf/opinions/2011SepTerm/12-0030.pdf
- **CAAF opinions index.** [V] https://www.armfor.uscourts.gov/newcaaf/opinions.htm
- **CAAF digest, obedience to orders.** [V] https://www.armfor.uscourts.gov/digest/IIIB16.htm
- **ICTY *Gotovina & Markač* appeal judgment summary.** Artillery targeting; the conviction was reversed on appeal. [V] https://www.icty.org/x/cases/gotovina/acjug/en/121116_summary.pdf
- **ICTY cases index.** [V] https://www.icty.org/en/cases/key-figures-cases
- **ICRC casebook, *How Does Law Protect in War?*** About 95 cases and no answer key. [V] https://casebook.icrc.org/
- **ICRC casebook entry on Gotovina.** [V] https://casebook.icrc.org/case-study/icty-prosecutor-v-gotovina-and-markac
- **Laconia Order (1942), uboat.net account.** [V] https://uboat.net/ops/laconia.htm
- **Nuremberg judgment on Dönitz.** Avalon Project. [V] https://avalon.law.yale.edu/imt/juddoeni.asp
- **DoD annual civilian-casualty report (NDAA §1057), 2024.** [V] https://policy.defense.gov/Portals/11/Documents/CHMR/TAB%20B-2024_1057_Report_final.pdf
- **RCFP page on the Azmat Khan civilian-casualty FOIA litigation.** [V] https://www.rcfp.org/azmat-khan-civilian-casualties/

### A3. Wargames and crisis decisions
- **Hoover Wargaming & Crisis Simulation Initiative archive.** Historical games and materials from the 1920s on. [V] https://wargaming.hoover.org/
- **PROUD PROPHET 1983 (Hoover entry).** [V] https://wargaming.hoover.org/view/ark:/54723/h3fb4wz0q/proud-prophet-game-1983
- **PROUD PROPHET, DoD FOIA release.** [V] https://www.esd.whs.mil/Portals/54/Documents/FOID/Reading%20Room/MDR_Releases/FY12/12-M-1487.pdf
- **SIGMA war games (1964).** Wikipedia summary. [V] https://en.wikipedia.org/wiki/Sigma_war_games
- **Able Archer 83 sourcebook (National Security Archive).** Over 1,000 pages. [V] https://nsarchive.gwu.edu/project/able-archer-83-sourcebook
- **PFIAB report on the 1983 war scare (1990).** [V] https://nsarchive.gwu.edu/document/33591-document-4-authoritative-presidents-foreign-intelligence-advisory-board-report
- **JFK White House recordings (Miller Center).** [V] https://millercenter.org/kennedy-secret-white-house-recordings-collection-specifications
- **FRUS (Foreign Relations of the United States), full XML on GitHub.** 552 volumes; raw files fetch. [V] https://github.com/HistoryAtState/frus
  - Raw file pattern: https://raw.githubusercontent.com/HistoryAtState/frus/master/volumes/{VOLUME_ID}.xml
  - Catalog of volume IDs: https://history.state.gov/api/v1/catalog/all
- **Schneider et al., Taiwan Strait crisis wargame with practitioners vs. LLMs.** [V] https://arxiv.org/abs/2403.03407; repo https://github.com/ancorso/LLMWargaming
- **Lamparth et al., "Measuring Free-Form Decision-Making Inconsistency of LMs in Military Crisis Simulations."** [V] https://arxiv.org/abs/2410.13204
- **Rivera et al., EscalAItion.** Eight-nation LLM-agent escalation simulation. [V] https://arxiv.org/abs/2401.03408; code https://github.com/jprivera44/EscalAItion
- **Snow Globe (IQT Labs).** LLM wargaming. [V] https://arxiv.org/abs/2404.11446; code https://github.com/IQTLabs/snowglobe
- **CSIS Critical Foreign Policy Decisions Benchmark.** [V] https://www.csis.org/programs/futures-lab/projects/critical-foreign-policy-decisions-benchmark; paper https://arxiv.org/abs/2503.06263

### A4. Intelligence agencies
- **CIA *Studies in Intelligence*, 1992–present.** [V] https://www.cia.gov/resources/csi/studies-in-intelligence/
- ***Studies in Intelligence* archive, 1955–2004.** [V] https://www.cia.gov/resources/csi/studies-in-intelligence/archives/
- ***Studies in Intelligence* article index (third-party Google Sheet).** [V] https://open-int.blog/2023/02/26/studies-in-intelligence-article-index/
- ***Studies in Intelligence* 70-1 (Mar 2026), unclassified extracts.** [V] https://www.cia.gov/resources/csi/static/UNCLASSIFIED-Extracts-Studies-in-Intelligence-70-1-Mar2026.pdf
- **CIA *Tradecraft Primer* (2009).** [V] https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf
- **Zulauf, "Safeguarding Objectivity in Intelligence Analysis" (*Studies in Intelligence* 65:3).** [V] https://www.cia.gov/resources/csi/static/Article-Zulauf-SafeguardingObjectivityInIntelligenceAnalysis.pdf
- **NSA, "Skunks, Bogies, Silent Hounds, and the Flying Fish: The Gulf of Tonkin Mystery."** [V] https://www.nsa.gov/portals/75/documents/news-features/declassified-documents/gulf-of-tonkin/articles/release-1/rel1_skunks_bogies.pdf
- **NSA, USS *Pueblo* Cryptologic/Cryptographic Damage Assessment.** [V] https://www.nsa.gov/portals/75/documents/news-features/declassified-documents/uss-pueblo/damage-assessments/Cryptologic-Cryptographic_Damage_Assessment.pdf
- **CDSE espionage case studies.** Real espionage, disclosure and insider cases. [V] https://securityawareness.dcsa.mil/cdse/case-studies/index.php; bulk XML https://securityawareness.dcsa.mil/cdse/case-studies/data/casestudies.xml
- **PERSEREC, *Espionage and Other Compromises of National Security*, 1975–2008.** [V] https://www.justsecurity.org/wp-content/uploads/2022/10/Espionage-and-Other-Compromises-of-National-Security-Case-Summaries-from-1975-2008-Defense-Personnel-Security-Research-Center-November-02-2009.pdf
- **SSCI report on prewar Iraq intelligence (S. Rept. 108-301, 2004).** [V] https://www.intelligence.senate.gov/sites/default/files/publications/108301.pdf
- **Robb–Silberman WMD Commission report (2005).** 619 pp. [V] https://www.govinfo.gov/content/pkg/GPO-WMD/pdf/GPO-WMD.pdf
- **Camp Chapman attack (2009).** CBS on Panetta's "systemic failures" statement. [V] https://www.cbsnews.com/news/chief-systemic-failures-led-to-7-cia-deaths/
- **DOHA security-clearance decisions.** Adjudicated cases with stated reasoning. [V] https://doha.ogc.osd.mil/Industrial-Security-Program/Industrial-Security-Clearance-Decisions/
  - Hearing decisions: https://doha.ogc.osd.mil/Industrial-Security-Program/Industrial-Security-Clearance-Decisions/ISCR-Hearing-Decisions/
  - Appeal Board: https://doha.ogc.osd.mil/Industrial-Security-Program/Industrial-Security-Clearance-Decisions/DOHA-Appeal-Board/
- **DOE Office of Hearings and Appeals, security cases.** [V] https://www.energy.gov/oha/listings/security-cases
- **FISC public filings.** [V] https://www.fisc.uscourts.gov/public-filings
- **FISC Section 702 certification opinion (2022).** [V] https://www.intelligence.gov/assets/documents/702-documents/declassified/21/2021_FISC_Certification_Opinion.pdf
- **28th Section 702 Joint Assessment.** Compliance incidents. [V] https://www.intelligence.gov/assets/documents/702-documents/declassified/28th_Joint_Assessment_for_PUBLIC_1.15.25.pdf
- **ISCAP declassification appeal decisions.** [V] https://www.archives.gov/declassification/iscap/decisions
- **NSA IG letter to Sen. Grassley (LOVEINT cases).** [V] https://www.nsa.gov/portals/75/documents/news-features/press-room/statements/grassley-letter.pdf
- **ISC report, *Detainee Mistreatment and Rendition 2001–2010* (UK, 2018).** [V] https://isc.independent.gov.uk/wp-content/uploads/2021/01/20180628-HC1113-Report-Detainee-Mistreatment-and-Rendition-2001-10.pdf

### A5. Case libraries (partly paywalled)
- **Harvard Kennedy School Case Program.** [V] https://case.hks.harvard.edu/ (licensing FAQ https://case.hks.harvard.edu/faq/)
- **Georgetown ISD case studies.** Diplomacy cases, about $450 each. [V] https://casestudies.isd.georgetown.edu

---

## Part B: Operational and tactical military (academies, Army, Navy, SOF, Marines)

### B1. Best finds: decision, reasoning and outcome stated, free PDFs
- ***66 Stories of Battle Command* (CGSC Press, 2000).** 66 first-person commander stories, mostly from NTC rotations, each giving situation, decision, reasoning, outcome and lesson, with a theme index. These are training-center events, not combat. Closest match to the schema. [V] https://apps.dtic.mil/sti/pdfs/ADA446651.pdf
- ***16 Cases of Mission Command* (CSI Press, 2nd ed., 2013).** 16 historical cases, corps to squad: Pea Ridge, Little Round Top, the Nile, Eben-Emael, Nijmegen, Bastogne, the Thunder Run, Tarin Kowt, Ranch House, among others. Each closes with analysis against the six mission-command principles. Cases 1–4 were read in full. [V] https://www.airforcespecialtactics.af.mil/Portals/80/SixteenCasesOfMissionCommand.pdf
- **CALL *Hard Lessons* (21-07, 2021).** Modeled on *66 Stories*; decisions faced by battalion and brigade sergeants major. Landing page [V] https://www.army.mil/article/246699/21_07_hard_lessons; PDF [T] https://api.army.mil/e2/c/downloads/2021/05/21/fc9adf0f/21-07.pdf
- **NWC, *The Battle of Savo Island: Strategical and Tactical Analysis, Part I* (Bates, 1950).** Hour-by-hour account with a lessons chapter assessing commanders' decisions. [V] https://apps.dtic.mil/sti/pdfs/ADA003037.pdf
  - Related NWC analyses, not opened: [T] https://apps.dtic.mil/sti/pdfs/ADA003030.pdf, https://apps.dtic.mil/sti/pdfs/ADA003028.pdf
- **CSI, *The Battle of Wanat* study (2010).** Long forensic narrative. Landing page [V] https://www.army.mil/article/48006/The_Battle_of_Wanat_Study; archived PDF [T] https://webarchive.library.unt.edu/web/20161027021444mp_/http://www.benning.army.mil/Library/content/Wanat.pdf
- **CSI Staff Ride Handbook, Dade's Battle (vol. 11).** Example of the staff-ride format: stand-by-stand decision points, discussion questions and vignettes. [V] https://apps.dtic.mil/sti/pdfs/ADA591723.pdf
- **ONI Combat Narratives (WWII), e.g. Savo Island.** 21 published and 13 unpublished campaign accounts. [V] https://ibiblio.org/hyperwar/USN/USN-CN-Savo/USN-CN-Savo-Fwd.html

### B2. Worth browsing
- **JSOU Press publications.** 251 free PDFs with no login. [V] https://www.jsou.edu/Press/Publications. Case-style titles, not opened [T]:
  - *Echoes of Little Bighorn*: https://www.jsou.edu/Press/PublicationDashboard/306
  - *Mazar-e Sharif*: https://www.jsou.edu/Press/PublicationDashboard/15
  - *Task Force Viking, Northern Iraq 2003*: https://www.jsou.edu/Press/PublicationDashboard/57
  - *Military Innovation in War: Task Force 714*: https://www.jsou.edu/Press/PublicationDashboard/81
  - *Block by Block* (Baghdad): https://www.jsou.edu/Press/PublicationDashboard/187
  - *One Valley at a Time*: https://www.jsou.edu/Press/PublicationDashboard/199
  - *Village Stability Operations*: https://www.jsou.edu/Press/PublicationDashboard/26
  - *In Denied Areas* (SOE/Jedburghs): https://www.jsou.edu/Press/PublicationDashboard/263
  - Lord's Resistance Army hunt / Somalia lessons: https://www.jsou.edu/Press/PublicationDashboard/108, https://www.jsou.edu/Press/PublicationDashboard/114
  - Ethics and moral-injury items: /30, /226, /246 (opened; short commentary), /272, /273 under https://www.jsou.edu/Press/PublicationDashboard/
- **MWI Urban Warfare Project (West Point).** 14 urban case studies, e.g. Mogadishu, Sadr City 2008, Hue, Aachen, Fallujah I and II, Marawi, Mosul, Kyiv, Shusha, Mumbai. They lean toward lessons rather than decision episodes. Hub [V] https://mwi.westpoint.edu/urban-warfare-project/; example [V] https://mwi.westpoint.edu/urban-case-study-9-the-battle-of-mogadishu/
- **MWI Contemporary Battlefield Assessments.** Analytic, not decision episodes. [V] https://mwi.westpoint.edu/mwi-research/battlefield-assessments/
- **USASOC History Office, *Veritas* journal.** Mixed; some operational narratives with decision analysis, e.g. Lang Vei 1968 and Just Cause. Sample issue [V] https://arsof-history.org/pdf/v15n1.pdf; site [V] https://arsof-history.org
- **CALL publications catalog.** Case-style items include *Achieving Unity of Effort: A Case Study in Leadership* (2019), *Defense of the Cajun Bayou* (20-16), *Fighting with Afghan Fists* (2019) and *Musicians of Mars IV* (20-08). [V] https://www.army.mil/tllm-army. The items themselves were not opened [T] and may be NTC composites.
- **CALL *Leader Development in Contact* (21-04).** Mostly TTPs. Landing page [V] https://www.army.mil/article/246691/21_04_leader_development_in_contact_handbook; PDF [T] https://api.army.mil/e2/c/downloads/2021/05/21/10e49a30/21-04.pdf
- **NWC Historical Monographs.** 32 volumes. Relevant: HM 22 (fleet-vs-fleet operations in the Pacific), HM 27 (European waters), HM 28 (Eccles Java Sea diary), HM 6 (*Angel on the Yardarm*). [V] https://digital-commons.usnwc.edu/usnwc-historical-monographs
- **NWC Newport Papers.** 48+ titles, mostly strategy and policy. [V] https://digital-commons.usnwc.edu/usnwc-newport-papers/
- **CMH, *Tip of the Spear: U.S. Army Small-Unit Action in Iraq, 2004–2007*.** history.army.mil blocks bots; get it via a browser. Pointer [V] https://tacticalnotebook.substack.com/p/tactical-case-studies
- **Marine Corps University Press catalog (open access).** Includes *A Game of Hare & Hounds*, *Phase Line Attila* and *Khaos Company*. [V] https://www.usmcu.edu/Portals/218/2021%20MCUP%20Publications%20Catalog_1.pdf

### B3. Scenarios with book answers but no real outcomes (useful for live scenarios, not gold)
- **Marine Corps Gazette TDG collection.** About 200 tactical decision games; mostly members-only. [T] https://www.mca-marines.org/professional-development/tdg-collection/
  - Old collection, 1989 on: [T] https://www.mca-marines.org/magazine-category/tdg-collection-old/page/16/
  - Example with published solution: [V] https://www.mca-marines.org/gazette/tactical-decision-game-94-6/
- **MCA Ethical Decision Games.** Premium members only. [U] https://www.mca-marines.org/decision-making-exercises/ethical-decision-games/
- **MCA Case Studies.** Premium members only. [U] https://www.mca-marines.org/decision-making-exercises/case-studies/
- **TECOM Leader Focused Decision Games.** Possibly restricted. [T] https://www.tecom.marines.mil/Units/Divisions/Range-and-Training-Programs-Division/LFDG/
- **The Company Leader TDGs.** 23 TDGs and 7 Junior Tactician exercises, no solutions, plus about 18 links to other collections. [V] https://companyleader.themilitaryleader.com/tdg/
- **USNA Stockdale Center ethics simulations (VEILS).** Seven Flash-era interactive films. [V] https://www.usna.edu/Ethics/publications/dilemmas.php
  - The one military scenario, *Incident in the Gulf*, facilitator guide: [V] https://www.usna.edu/Ethics/_files/documents/Incident_in_the_Gulf_Facilitator_Guide.pdf

### B4. Thin, or blocked to the agents (try in a browser)
- **Army University Press / CSI Press.** Art of War Papers and Staff Ride Handbooks; blocked. [U] https://www.armyupress.army.mil. The CARL digital library is JavaScript-only [T]: https://cgsc.contentdm.oclc.org/
- **Archived CAPE case packages.** [U] https://webarchive.library.unt.edu/web/20161021000807mp_/http://cape.army.mil/case-studies/packages
- **NHHC publications.** Blocked. [U] https://www.history.navy.mil
- **Thin or not useful:**
  - West Point Center for Junior Officers [V] https://usma.edu/research/west-point-werx/center-for-junior-officers
  - Combating Terrorism Center [V] https://ctc.westpoint.edu
  - West Point history atlases, maps only [V] https://dhc.westpoint.edu/atlases/
  - CIMSEC [V] https://cimsec.org
  - Small Wars Journal [V] https://smallwarsjournal.com
  - USSOCOM 2010 Fact Book [V] https://apps.dtic.mil/sti/pdfs/ADA532654.pdf
  - Air University leadership case guide [V] https://fairchild-mil.libguides.com/Leadership_Case_Studies
  - Air University ethical leadership lesson plan [T] https://www.airuniversity.af.mil/Portals/10/GCPME/Documents/FCE/Lesson%20Plans/Ethical%20Leadership-10%20May%202022.pdf
- **Print only:** *Ethics for the Junior Officer: Selected Cases from Current Military Experience* (Naval Institute Press, 2nd ed., 2001).

---

## Part C: Intelligence agencies

### C1. CIA
- **CSI Books & Monographs.** About 60 free PDFs; roughly 12–15 are decision cases with reasoning and outcomes. [V] https://www.cia.gov/resources/csi/books-and-monographs/
- ***Unheeded Warning of War: Why Policymakers Ignored the 1990 Yugoslavia Estimate*.** The warning call, dissemination and leak, policymaker inaction, outcome and lessons. [V] https://www.cia.gov/resources/csi/static/75ca22531faf720b31ff82f353d79301/Unheeded-Warning-Yugoslavia.pdf
- ***The 2007 NIE on Iran's Nuclear Intentions and Capabilities*.** The NIC's decision to redo the estimate, NIB approval, the decision to declassify the key judgments, the public reaction. [V] https://www.cia.gov/resources/csi/static/a6c09ab8eb00a08b8ba5ad1a5055f527/2007-Iran-Nuclear-Intentions.pdf
- ***CIA and the Vietnam Policymakers: Three Episodes, 1962–68* (Ford).** McCone sending back NIE 53-63, CIA caution on the Diem coup, and Tet. [V] https://www.cia.gov/resources/csi/static/1768c7c6f5560bafdc7c57afc7b0f1d6/CIA-and-the-Vietnam-Policymakers.pdf
- ***US Intelligence and the Polish Crisis 1980–81*.** Warning and deterrence decisions, why Solidarity was not alerted, Kuklinski's reporting. [V] https://www.cia.gov/resources/csi/static/0a25844b9fb8ff820b503d139b3e7d00/US-Intelligence-and-the-Polish-Crisis-1980-1981.pdf
- ***Predicting the Soviet Invasion of Afghanistan*.** Dated analytic calls, including a dissent, and the failure debate. [V] https://www.cia.gov/resources/csi/static/e8fa84316547f220a8432d3e1d9830af/Predicting-the-Soviet-Invasion-of-Afghanistan.pdf
- ***A Cold War Conundrum: The 1983 Soviet War Scare*.** [V] https://www.cia.gov/resources/csi/static/4f74a357a4372cc542944cd39e5e30bc/Cold-War-Conundrum.pdf
- ***The Agency and the Hill*.** About 370 pp on oversight, covert-action notification, Church and Iran-Contra; only the table of contents was read. [V] https://www.cia.gov/resources/csi/static/c2bbf1d2a5d7ee65af651f57ff784ac4/The-Agency-and-Hill.pdf
- **Other CSI titles worth pulling [T]:**
  - *CIA Documents on the Cuban Missile Crisis*
  - *At Cold War's End*
  - *Intentions and Capabilities*
  - *CIA Assessments of the Soviet Union: The Record Versus the Charges*
  - *The CIA and the U-2 Program*
  - *Voices from the Station* (Saigon evacuation)
  - *On the Front Lines of the Cold War* (Berlin; its PDF link points to a cover image)
  - *Sharing Secrets with Lawmakers*
  - *Curing Analytic Pathologies*
  - *Directors of Central Intelligence as Leaders*
- **Warner, "Lessons Unlearned: The CIA's Internal Probe of the Bay of Pigs Affair."** The IG survey against the operators' rebuttal; a clean decision episode. [V] https://www.cia.gov/resources/csi/static/Internal-Probe-Bay-Pigs.pdf
- **CIA official Bay of Pigs history (NSArchive EBB 353).** Volumes 2–4, the Kirkpatrick IG survey and planning memos. [V] https://nsarchive2.gwu.edu/NSAEBB/NSAEBB353/; also [V] https://archive.org/details/BayOfPigsOfficialCIAHistory
- **CIA presidents-and-intelligence publication packages.** 35 items, each declassified documents plus an essay; only page 1 was retrievable. [V] https://www.cia.gov/resources/publications/publications-list/
  - Example: *President Nixon and the Role of Intelligence in the 1973 Arab-Israeli War*. [V] https://www.cia.gov/resources/publications/president-nixon-and-the-role-of-intelligence-in-the-1973-arab-israeli-war/
  - Also listed [T]: *Intelligence and the Camp David Accords*, *Bosnia, Intelligence, and the Clinton Presidency*, *Preparing for Martial Law* (Kuklinski), *Ronald Reagan: Intelligence and the End of the Cold War*
- ***Betrayal in Berlin* (Berlin Tunnel).** [T] https://www.cia.gov/resources/csi/static/BetrayalinBerlin.pdf
- **CIA FOIA Reading Room special collections.** Under maintenance on 2026-10-27; retry later. The CS Historical Papers are the decision-rich ones; the PDBs are short briefs.
  - [U] https://www.cia.gov/readingroom/collection/presidents-daily-brief-1961-1969
  - CSHP-150, Berlin Tunnel 1952–56: [U] https://www.cia.gov/readingroom/document/cia-rdp01-00569r000100050015-1
  - Berlin Tunnel: [U] https://www.cia.gov/readingroom/document/01225490
- **Kent Center Occasional Papers.** Essays, not cases.
  - Davis, *Strategic Warning*: [V] https://apps.dtic.mil/sti/pdfs/ADA526569.pdf
  - [T] https://www.cia.gov/resources/csi/static/Kent-Profession-Intel-Analysis.pdf
  - [T] https://www.cia.gov/resources/csi/static/Kent-Final-Thoughts-Analyst-Policymaker-Relations.pdf

### C2. NSA
- **Center for Cryptologic History, Historical Publications.** About 90 PDFs on media.defense.gov; browser needed. [V] https://www.nsa.gov/History/Cryptologic-History/Historical-Publications/
- **Johnson & Hatch, *NSA and the Cuban Missile Crisis*.** SIGINT reporting and dissemination decisions. [V] https://media.defense.gov/2022/Oct/11/2003093697/-1/-1/0/CUBAN%20MISSILE%20CRISIS_2022_10_04.PDF
- **Other titles on the same listing [T]:**
  - *West Wind Clear: Cryptology and the Winds Message Controversy*
  - *Pearl Harbor Revisited*
  - *So Power Can Be Brought into Play* (Pusan Perimeter)
  - *Eavesdropping on Hell*
  - *NSA Directors: The Selection and Confirmation Process*
  - *Ninety Years of Assessing Civilian Cryptologic Performance*
- ***Cryptologic Quarterly*, e.g. 2024-01.** [T] https://media.defense.gov/2025/Jul/09/2003750271/-1/-1/0/CRYPTOLOGIC_QUARTERLY_2024_01_FINAL.PDF
- **Johnson, *American Cryptology during the Cold War, 1945–1989*, Books I–IV.** Book III (1972–80) covers the oversight period. Heavily redacted. [V] https://theblackvault.com/documentarchive/american-cryptology-during-the-cold-war-1945-1989; also [V] https://archive.org/details/cold_war_iii-nsa
- **Gulf of Tonkin declassified release.** SIGINT reports, chronologies and oral histories. [V] https://www.nsa.gov/News-Features/Declassified-Documents/Gulf-of-Tonkin/
- **Cryptologic Almanac 50th Anniversary Series (Black Vault).** [T] https://www.theblackvault.com/documentarchive/cryptologic-almanac-50th-anniversary-series

### C3. DIA, NRO, NGA, NIU, ODNI
- **NSArchive DIA Declassified Sourcebook (EBB 534).** About 53 documents, 1961–2015: the 1978 Iran assessment ("no threat to the stability of the Shah's rule"), the CURVEBALL fabricator memo, the Ana Montes IG review. [V] https://nsarchive2.gwu.edu/NSAEBB/NSAEBB534-DIA-Declassified-Sourcebook/
- **Petersen, *The Vietnam Cauldron: Defense Intelligence in the War for Southeast Asia* (DIA, 2012).** Includes the order-of-battle controversy. [V] https://purl.stanford.edu/nh783yy6908
- **NRO, *Directors of the National Reconnaissance Office at 50 Years*.** 16 short profiles, each with a major decision. [V] https://www.nro.gov/Portals/65/documents/history/csnr/leaders/DNRO_monograph_Sep2012.pdf
- **NIU Press.** Thin; no list visible. [T] https://www.ni-u.edu/ni-press/; *After the Wars* eBook [T] https://ni-u.edu/wp-content/uploads/2023/09/After-the-Wars-eBook.pdf
- **NGA.** Thin. *NPIC* history book promo: [V] https://trajectorymagazine.com/the-history-of-npic/

### C4. Commission and inquiry reports
- **9/11 Commission Report.** Warning, information sharing, "the wall," the Aug 2001 PDB. 585 pp. [V] https://www.govinfo.gov/content/pkg/GPO-911REPORT/pdf/GPO-911REPORT.pdf
- **Senate Intelligence Committee index of intelligence-related commissions.** [V] https://www.intelligence.senate.gov/resources/intelligence-related-commissions/
- **Chilcot / Iraq Inquiry, Vol. IV, Iraq's WMD.** JIC judgments with their reasoning; 616 pp; Open Government Licence. [V] https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/535415/The_Report_of_the_Iraq_Inquiry_-_Volume_IV.pdf; landing page https://www.gov.uk/government/publications/the-report-of-the-iraq-inquiry
- **Butler Review (UK, 2004, HC 898).** 216 pp. [V] https://statewatch.org/wp-content/uploads/2026/04/butler-report.pdf. Not the 16-page 2005 implementation paper "wmdreview.pdf".
- **Church Committee final reports, Books I–VI.** Book III has domestic case studies; Book IV covers foreign and military intelligence.
  - [V] https://archive.org/details/ChurchCommittee_FullReport
  - [V] https://archive.org/details/ChurchCommittee
  - Book III contents: [V] https://www.aarclibrary.org/publib/church/reports/book3/contents.htm
  - Senate copy: [U] https://www.intelligence.senate.gov/wp-content/uploads/2024/08/sites-default-files-94755-i.pdf
- **Iran-Contra, Walsh Final Report.** One chapter per person (Casey, Gates, Clair George, Clarridge, Fiers…). Best compliance and ethics source. [V] https://irp.fas.org/offdocs/walsh/
- **SSCI Iraq Phase II reports (2006–08), press release.** Full texts not linked. [V] https://www.intelligence.senate.gov/press/senate-intelligence-committee-unveils-final-phase-ii-reports-prewar-iraq-intelligence

### C5. Educational casebooks
- **Beebe & Pherson, *Cases in Intelligence Analysis*, 2nd ed. (CQ Press, 2014).** 17 cases. Commercial. [V] https://www.sagepub.com/shop/buy-a-book/cases-in-intelligence-analysis-2-242321
- **Grønning & Stenslie (eds.), *Contemporary Intelligence Warning Cases* (Edinburgh UP, 2024).** 16 cases, each classed as Type A (intelligence failure) or Type B (failure to act on warning). Commercial. CSI review: [V] https://www.cia.gov/resources/csi/static/Review-Contemporary-Intelligence-Warning-Cases-June-2025.pdf
- **NDU case studies.** 14 free policy cases, e.g. Nixon renouncing biological weapons; none on intelligence. [V] https://digitalcommons.ndu.edu/case-studies
- ***Journal of Strategic Security* (open access).** Mine by article. [V] https://digitalcommons.usf.edu/jss/
- **Thin:** Harvard Belfer Intelligence Project [V] https://www.belfercenter.org/programs/intelligence-project. Nothing free was found from Mercyhurst or JMU.

---

## Part D: Weapons employment, fires and targeting

### D1. Strike and friendly-fire investigations
- **Kunduz tanker strike (4 Sep 2009), Bundestag inquiry report, Drucksache 17/7400.** 580 pp, German, searchable text.
  - Part 2 §B (pp. 39–88): narrative, including Col. Klein's decision, his rejection of the pilots' offered show of force, and the ROE "imminent threat" discussion.
  - Part 3 (p. 169 on): committee evaluation.
  - Part 4 (pp. 213–414): factional dissents.
  - Part 6 (p. 429): lessons learned.
  - [V] https://dserver.bundestag.de/btd/17/074/1707400.pdf
  - Coalition "Lessons Learned" position paper (partisan, about 1,500 words): [V] https://dserver.bundestag.de/btd/17/CD07400/Dokumente/Dokument%20020b.pdf
- **Tarnak Farm (2002), Canadian Board of Inquiry, full text.** Parts I–V and Annexes A–K; Annex I is the radio transcript; Part IV covers blame. [V] https://www.globalsecurity.org/military/library/report/2002/tarmak_content_e.htm (pages tarmak_fr-N_e.htm)
  - Official partial executive summary: [T] https://publications.gc.ca/collections/Collection/D2-138-2002E.pdf
- **Harim, Syria (5–6 Nov 2014), AR 15-6 civilian-casualty investigation.** 77 pp. CENTCOM commander authorization, removal from the no-strike list, target validation board. Heavily redacted. [V] https://documents.theblackvault.com/documents/wartime/HarimSyriaCIVCAS.pdf; Airwars copy [V] https://archive-2025.airwars.org/wp-content/uploads/2022/05/33f211120650b542.pdf
- **Farah/Granai (4 May 2009), USCENTCOM unclassified executive summary.** 13 pp. Day strikes compliant; night B-1B strikes broke the Tactical Directive. [V] https://www.airandspaceforces.com/PDF/SiteCollectionDocuments/Reports/2009/June%202009/Day22/uscentcom_farah061809.pdf
  - Write-up: [V] https://airandspaceforces.com/thefarahreport
- **Mosul al-Jadida (17 Mar 2017), AR 15-6 executive summary (BG Isler).** Weapon and fuze choice, approval by the strike cell, 105 civilian deaths. [V] https://www.centcom.mil/MEDIA/NEWS-ARTICLES/News-Article-View/Article/1193707/executive-summary-of-the-investigation-of-the-alleged-civilian-casualty-inciden/
- **Al Jinah mosque strike (16 Mar 2017), investigating officer's briefing transcript (BG Bontrager).** Protected status never cleared, shift handoffs, weak red-team check. [V] https://airwars.org/transcript-of-al-jinah-investigation-briefing
- **Uruzgan (21 Feb 2010), AR 15-6 via ACLU FOIA.** 28 parts, including interview transcripts on the Predator feed and the decision chain. Scanned and redacted (OCR).
  - Part 2: [V] https://www.aclu.org/documents/uruzgan-investigation-part-2-28-pp25-32
  - Part 5: [V] https://aclu.org/documents/uruzgan-investigation-part-5-28
  - PDF pattern: https://assets.aclu.org/live/uploads/document/foia/drone_uruzgan_attachtabA_part_NN_FOIA_10-0218.pdf (part 2 has the suffix `_pp25-32`)
  - ACLU index: [T] https://www.aclu.org/foia-collection/targeted-killing-foia-database
  - Outcome summary: [V] https://www.stripes.com/news/middle-east/report-faults-drone-crews-in-attack-that-killed-afghan-civilians-1.104815
- **USS *Stark* (17 May 1987), Sharp formal investigation with endorsement chain (JAGMAN, FOIA).** 58 pp, rough OCR. [V] https://documents2.theblackvault.com/documents/navy/USSSTARK-NAVYJAG.pdf
  - Vlahos, "The Stark Report," *Proceedings* (1988): [V] https://www.usni.org/magazines/proceedings/1988/may/stark-report
  - HASC staff report: [U] https://catalog.hathitrust.org/Record/002771140
- **1994 Black Hawk shootdown over Iraq.** The accident board's report is not online.
  - GAO review of the board (GAO/OSI-98-4): [V] https://www.govinfo.gov/content/pkg/GAOREPORTS-OSI-98-4/html/GAOREPORTS-OSI-98-4.htm
  - GAO testimony: [V] https://www.govinfo.gov/content/pkg/GAOREPORTS-T-OSI-98-13/pdf/GAOREPORTS-T-OSI-98-13.pdf
- **Tillman, DoD IG review (2007).** Mostly about post-incident handling; the shooters' decisions appear through the three Army investigations, which are not public.
  - [V] https://media.defense.gov/2018/Aug/16/2001955054/-1/-1/1/TILLMAN_REDACTED_WEB_0307-1.PDF
  - Army action on the review: [V] https://www.army.mil/article/4232/army_announces_results_of_further_review_of_reports_related_to_death_of_cpl_patrick_tillman
- **Baghuz (18 Mar 2019), Gen. Garrett's independent review, executive summary.** 2 pp. This is a FORSCOM review for SecDef, not a DoD IG report. [V] https://media.defense.gov/2022/May/17/2002999192/-1/-1/1/EXECUTIVE-SUMMARY-INDEPENDENT-REVIEW-OF-18-MARCH-2019-CIVILIAN-CASUALTY-INCIDENT-IN-BAGHUZ-SYRIA.PDF
- **Azizabad (Aug 2008).** Thin; no primary investigation text.
  - CENTCOM release: [V] https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/Article/903519/coalition-aug-22-actions-in-afghanistan-justified/
  - HRW critique: [V] https://www.hrw.org/news/2009/01/15/afghanistan-us-investigation-airstrike-deaths-deeply-flawed
  - HRW, *Troops in Contact*: [T] https://www.hrw.org/report/2008/09/08/troops-contact/airstrikes-and-civilian-deaths-afghanistan
- **2003 A-10 fratricide on UK Household Cavalry (LCoH Hull).** Thin.
  - UK MoD Board of Inquiry: [U] https://web.archive.org/web/20070214003804/http://www.mod.uk/NR/rdonlyres/887DE696-1DB9-4512-AF8E-2ECFED455356/0/boi_lcpl_hull.pdf
  - Cockpit-video transcript study: [U] https://web.archive.org/web/20160310173902/http://repository.liv.ac.uk/2005800/
  - Background: [V] https://en.wikipedia.org/wiki/190th_Fighter_Squadron,_Blues_and_Royals_friendly_fire_incident

### D2. Air power and fires case studies
- **Bucknam, *Responsibility of Command: How UN and NATO Commanders Influenced Airpower over Bosnia* (AU Press, 2003).** About 400 pp: the Udbina strike, target approval in Deliberate Force, collateral-damage trade-offs. [V] https://apps.dtic.mil/sti/pdfs/ADA415991.pdf
- **ICTY OTP Final Report on the NATO bombing of Yugoslavia (2000).** Grdelica train (with pilot reasoning), Djakovica convoy, RTS building, Chinese embassy. [V] https://www.icty.org/en/node/5389
- **HRW, *Civilian Deaths in the NATO Air Campaign* (2000).** Incident case studies. [V] https://www.hrw.org/reports/2000/nato/index.htm
- **Operation Anaconda, three studies:**
  - *Operation ANACONDA: An Air Power Perspective* (HQ USAF, 2005), 135 pp: [V] https://apps.dtic.mil/sti/pdfs/ADA495248.pdf
  - Kugler, *Operation Anaconda: Lessons for Joint Operations* (NDU, 2009), 73 pp: [V] https://www.govinfo.gov/content/pkg/GOVPUB-D5_400-PURL-gpo135804/pdf/GOVPUB-D5_400-PURL-gpo135804.pdf
  - *Operation Anaconda in Afghanistan: A Case Study of Adaptation in Battle* (NDU, 2007), 27 pp: [V] https://apps.dtic.mil/sti/pdfs/ADA463075.pdf
- **RAND (Tarini et al.), *The Air War Against the Islamic State* (2021).** Chapter 5 covers deliberate-targeting cases and the delegation of engagement authority. [V] https://apps.dtic.mil/sti/pdfs/AD1122427.pdf
- **RAND, *Understanding Civilian Harm in Raqqa* (RR-A753-1, 2022).** 138 pp plus annex. [V] https://www.rand.org/pubs/research_reports/RRA753-1.html
- **RAND, Lambeth, *Air Power Against Terror* (MG-166-1, 2006).** CENTCOM target-approval bottleneck; Anaconda. [V] https://www.rand.org/pubs/monographs/MG166-1.html
- **RAND, Lambeth, *NATO's Air War for Kosovo* (MR-1365, 2001).** [V] https://www.rand.org/pubs/monograph_reports/MR1365.html
- **RAND, Hosmer, *The Conflict over Kosovo* (MR-1351, 2001).** [V] https://apps.dtic.mil/sti/pdfs/ADA393238.pdf
- **RAND, Mueller (ed.), *Precision and Purpose: Airpower in the Libyan Civil War* (RR-676, 2015).** 466 pp. [V] https://www.rand.org/pubs/research_reports/RR676.html; DTIC copy https://apps.dtic.mil/sti/tr/pdf/ADA624687.pdf
- **Shaw, *Collateral Damage and the United States Air Force* (SAAS, 1997).** Al-Firdos, Just Cause, Linebacker. [V] https://apps.dtic.mil/sti/pdfs/ADA391809.pdf
- **Kindley, "Why Won't You Drop, Damn You!?" (OEF targeting, 2003).** Anecdotal vignettes. [V] https://apps.dtic.mil/sti/pdfs/ADA422702.pdf
- **Corum, *Inflated by Air* (AWC, 1998).** [V] https://apps.dtic.mil/sti/pdfs/ADA399072.pdf
- **Rabun, *Close Air Support Since 9/11: Implications for Urban Operations* (SAMS, 2020).** Anaconda and Fallujah. [V] https://apps.dtic.mil/sti/pdfs/AD1159721.pdf

### D3. Targeting doctrine (frameworks, not cases)
- **CJCSI 3160.01, No-Strike and the Collateral Damage Estimation Methodology (2009).** 101 pp, FOUO, released to the ACLU. [V] https://assets.aclu.org/live/uploads/document/foia/drone_dod_3160_01.pdf
- **Joint Staff briefing, "Joint Targeting Cycle and CDM" (2009).** 47 slides. [V] https://assets.aclu.org/live/uploads/document/foia/drone_dod_ACLU_DRONES_JOINT_STAFF_SLIDES_1-47_2.pdf
- **CJCSI 3160.01B (2015), DoD FOIA reading room.** [V] https://www.esd.whs.mil/Portals/54/Documents/FOID/Reading%20Room/Joint_Staff/16-F-0427_Damage_Estimate_Methodology.pdf
- **JP 3-60, Joint Targeting (2018).** [V] https://www.esd.whs.mil/Portals/54/Documents/FOID/Reading%20Room/Joint_Staff/21-F-0520_JP_3-60_9-28-2018.pdf
- **AFDP 3-60, Targeting.** [V] https://www.doctrine.af.mil/Portals/61/documents/AFDP_3-60/3-60-AFDP-TARGETING.pdf
- **NATO AJP-3.9(B), Allied Joint Doctrine for Joint Targeting (2021).** 126 pp. [V] https://assets.publishing.service.gov.uk/media/618e7da28fa8f5037ffaa03f/AJP-3.9_EDB_V1_E.pdf
- **FM 3-60, Army Targeting (2023).** Landing page [V] https://digitalcommons.unl.edu/usarmyfieldmanuals/33; PDF [U] https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=1032&context=usarmyfieldmanuals
- **AP I Art. 57, precautions in attack (ICRC IHL database).** [V] https://ihl-databases.icrc.org/en/ihl-treaties/api-1977/article-57

### D4. Civilian-casualty records
- **Airwars incident archive.** Each incident record links declassified assessments; the monthly reports give one-line reasons. Example [V] https://airwars.org/civilian-casualties/cs560-march-8-2017; example monthly-report PDF [V] https://archive-2025.airwars.org/wp-content/uploads/2022/05/9c0cce9c9048f7c3.pdf
- **CENTCOM / CJTF-OIR monthly CIVCAS report (May 2017).** [V] https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/Article/1239870/combined-joint-task-force-operation-inherent-resolve-monthly-civilian-casualty/
- **NYT "The Civilian Casualty Files" (Khan, 2021).** No bulk public archive.
  - [U] https://www.nytimes.com/interactive/2021/us/civilian-casualty-files.html
  - FOIA complaint: [T] https://www.rcfp.org/wp-content/uploads/2021/10/2021-09-30-Khan-v.-Department-of-Defense-complaint.pdf

---

## Known gaps (searched, not found)
- The 1994 Black Hawk accident board report itself.
- The Army Tillman AR 15-6 investigations.
- The Azizabad Callan report text.
- The NATO/ISAF Kunduz summary.
- The USAF Hull investigation.
- A CALL fires or targeting handbook with vignettes.
- A free, text-based collection of ethics or ROE decision cases. Stockdale, CAPE and the MCA ethical decision games are thin or gated.
