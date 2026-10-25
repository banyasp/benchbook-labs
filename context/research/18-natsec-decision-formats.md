# 18 — National-Security Decision-Making Formats: Verified Source Notes

Research pass for a structured "case" schema in which an agent reasons by analogy from a precedent case at a decision point (e.g., a Vulnerabilities Equities Process disclose/retain decision; an autonomous vessel's leave-before-recovery decision). All sources below are public/unclassified. Each item gives citation, verified URL, quoted/extracted fields, and one sentence on what the case schema should borrow. Where a document could not be directly opened (server blocked automated fetch), that is stated plainly and the best available substitute/triangulation is given instead.

Date of this research pass: 2026-09-27/28.

---

## 1. Vulnerabilities Equities Policy and Process for the United States Government (Charter, Nov 15, 2017)

**Citation:** The White House, *Vulnerabilities Equities Policy and Process for the United States Government*, Unclassified Charter, November 15, 2017.

**Verified working URLs (directly fetched, content confirmed):**
- https://nsarchive.gwu.edu/sites/default/files/documents/5626625/The-White-House-Vulnerabilities-Equities-Policy.pdf (National Security Archive mirror of the actual charter PDF — this is the one I opened and quoted from below)
- Landing/context page: https://nsarchive.gwu.edu/document/17688-white-house-vulnerabilities-equities-policy
- Alternate mirror (PDF, not independently re-verified line-by-line but same document): https://assets.documentcloud.org/documents/4224051/External-Unclassified-VEP-Charter-FINAL.pdf (DocumentCloud/Lawfare)
- Alternate mirror: https://info.publicintelligence.net/US-VulnerabilitiesEquityPolicy.pdf

**Presumption/primary focus favoring disclosure (Section 1, Purpose) — verbatim:**
> "The primary focus of this policy is to prioritize the public's interest in cybersecurity and to protect core Internet infrastructure, information systems, critical infrastructure systems, and the U.S. economy through the disclosure of vulnerabilities discovered by the USG, absent a demonstrable, overriding interest in the use of the vulnerability for lawful intelligence, law enforcement, or national security purposes."

**Equities Review Board (ERB) — who sits on it (Section 4.1):** Representatives from OMB, ODNI, Treasury, State, DOJ (including FBI/NCIJTF), DHS (including NCCIC/USSS), Energy, DoD (including NSA, CYBERCOM, DC3), Commerce, and CIA. Process oversight sits with the VEP Director — described as the Special Assistant to the President and Cybersecurity Coordinator at the NSC — who "will be responsible for ensuring effective implementation" of the process. The charter does not name a single formal "chair" of the ERB distinct from this NSC-based VEP Director role; decisions are reached through the ERB's consensus/escalation procedure rather than a unilateral chair vote.

**NSA's role — Executive Secretariat (Section 4.2) — verbatim:**
> "The NSA will support VEP governance by serving as the Executive Secretariat for the VEP, acting at all times under the authority, direction, and control of the Secretary of Defense."
Its functions are administrative/coordinating: maintaining records and facilitating information flow, discussions, and determinations among ERB members — the charter is explicit that in this function NSA must remain "neutral and independent," i.e., the Secretariat is a process-support role, not a decision-making vote in itself.

**Re-review interval for restricted ("retained") vulnerabilities (Section 5.2.5) — verbatim:**
> "reassessed annually by the ERB until dissemination is accomplished, the vulnerability is publicly known, or the vulnerability is otherwise mitigated"

**Annex B — Equity Considerations (full headings and representative questions, verbatim quotes):**

- **Part 1 — Defensive Equity Considerations**
  - *1.A Threat Considerations:* "Where is the product used? How widely is it used?" / "How broad is the range of products or versions affected?" / "Are threat actors likely to exploit this vulnerability, if it were known to them?"
  - *1.B Vulnerability Considerations:* "What access must a threat actor possess to exploit this vulnerability?" / "Is exploitation of this vulnerability alone sufficient to cause harm?" / "How likely is it that threat actors will discover or acquire knowledge of this vulnerability?"
  - *1.C Impact Considerations:* "How much do users rely on the security of the product?" / "How severe is the vulnerability? What are the potential consequences of exploitation?" / "What access or benefit does a threat actor gain by exploiting this vulnerability?" / "What is the likelihood that adversaries will reverse engineer a patch?" / "Will enough USG information systems, U.S. businesses and/or consumers actually install the patch?"
  - *1.D Mitigation Considerations:* "Can the product be configured to mitigate this vulnerability?" / "Are impacts of this vulnerability mitigated by existing best-practice guidance?" / "If the vulnerability is disclosed, how likely is it that the vendor will develop and release a patch?" / "If a patch is released, how likely is it to be applied to vulnerable systems?" / "Can exploitation of this vulnerability by threat actors be detected by USG?"

- **Part 2 — Intelligence, Law Enforcement, and Operational Equity Considerations**
  - *2.A Operational Value Considerations:* "Can this vulnerability be exploited to support intelligence collection, cyber operations, or law enforcement?" / "What is the demonstrated value of this vulnerability for intelligence collection, cyber operations, and/or law enforcement?" / "What is its potential (future) value?" / "What is the operational effectiveness of this vulnerability?"
  - *2.B Operational Impact Considerations:* "Does exploitation of this vulnerability provide specialized operational value against cyber threat actors?" / "Do alternative means exist to realize the operational benefits?" / "Would disclosing this vulnerability reveal any intelligence sources or methods?"

- **Part 3 — Commercial Equity Considerations:** "If USG knowledge of this vulnerability were to be revealed, what risks could that pose for USG relationships with industry?"

- **Part 4 — International Partnership Equity Considerations:** "If USG knowledge of this vulnerability were to be revealed, what risks could that pose for USG international relations?"

**What newer/post-2017 material to flag (not independently verified in this pass — noted, not confirmed):** Public reporting (EFF, Lawfare, and others) has described refinements to VEP practice since 2017, and the FY2018/FY2021 NDAAs added statutory reporting requirements for the VEP; I did not open or verify any post-2017 charter revision text in this pass, so no specific post-2017 changes are asserted here as verified — only the 2017 charter above is confirmed firsthand.

**What a case schema should borrow:** The four-part "equity" taxonomy (defensive / intelligence-operational / commercial / international-partnership) is a ready-made multi-stakeholder tradeoff frame for any disclose-vs-retain decision node, and the mandatory annual re-review clause is a clean template field for "decision revisit cadence" that keeps a retain-decision from being treated as permanent.

---

## 2. ICD 203, Analytic Standards (ODNI)

**Citation:** Office of the Director of National Intelligence, *Intelligence Community Directive 203: Analytic Standards*, effective January 2, 2015 (supersedes June 21, 2007 version).

**Verified working URL (directly fetched, content confirmed):** https://archive.dni.gov/files/documents/ICD/ICD-203.pdf
(Current ODNI URL https://www.odni.gov/files/documents/ICD/ICD-203.pdf 302-redirects to the archive.dni.gov URL above — both resolve to the same document. Additional mirror, not independently reopened: https://irp.fas.org/dni/icd/icd-203.pdf)

**Analytic Standards list (5 core standards + 9 tradecraft standards):**
Core standards: Objective; Independent of political consideration; Timely; Based on all available sources of intelligence; and Implements Analytic Tradecraft Standards. The 9 tradecraft standards are:
1. Properly describes quality and credibility of underlying sources, data, and methodologies
2. Properly expresses and explains uncertainties associated with major analytic judgments
3. Properly distinguishes between underlying intelligence and analysts' assumptions and judgments
4. Incorporates analysis of alternatives
5. Demonstrates relevance to U.S. national security
6. Uses clear and logical argumentation
7. Explains change to or consistency of analytic judgments
8. Makes accurate judgments and assessments
9. Incorporates effective visual information where appropriate

**Likelihood/probability expression table (verified):**

| Percentage range | Terms |
|---|---|
| 01–05% | almost no chance / remote |
| 05–20% | very unlikely / highly improbable |
| 20–45% | unlikely / improbable |
| 45–55% | roughly even chance / roughly even odds |
| 55–80% | likely / probable |
| 80–95% | very likely / highly probable |
| 95–99% | almost certain(ly) / nearly certain |

**Confidence levels (low/moderate/high):** ICD 203 requires that products using a "confidence level" (e.g., "high confidence") in a judgment do so as a *separate* dimension from the likelihood/probability language above, and instructs analysts not to combine a confidence level and a likelihood expression in the same sentence in a way that conflates the two. (I confirmed this rule exists in the document; I was not able to extract a single clean verbatim sentence defining what distinguishes "low" from "moderate" from "high" confidence beyond the general description that confidence reflects the scope/quality/corroboration of the underlying reporting and the analyst's reasoning — flagging this as a partial verification: the *existence and function* of the three-tier scale is confirmed, the precise defining prose was not captured verbatim.)

**What a case schema should borrow:** A closed vocabulary for two orthogonal fields — `likelihood` (7-point verbal-probability scale with numeric anchors) and `confidence` (low/moderate/high, kept separate from likelihood) — gives the case schema calibrated, non-conflatable uncertainty fields for both the precedent case's original judgment and the agent's own forecast at the decision point.

---

## 3. CIA, *A Tradecraft Primer: Structured Analytic Techniques for Improving Intelligence Analysis* (March 2009)

**Citation:** U.S. Government/Central Intelligence Agency, Center for the Study of Intelligence, *A Tradecraft Primer: Structured Analytic Techniques for Improving Intelligence Analysis*, March 2009.

**Verified working URL (directly fetched, content confirmed):** https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf

**One-line descriptions (verbatim from the document):**
- **Key Assumptions Check:** "List and review the key working assumptions on which fundamental judgments rest."
- **Indicators or Signposts of Change:** "Periodically review a list of observable events or trends to track events, monitor targets, spot emerging trends, and warn of unanticipated change."
- **Analysis of Competing Hypotheses:** "Identification of alternative explanations (hypotheses) and evaluation of all evidence that will disconfirm rather than confirm hypotheses."
- **"What If?" Analysis:** "Assumes that an event has occurred with potential (negative or positive) impact and explains how it might come about."
- **High-Impact/Low-Probability Analysis:** "Highlights a seemingly unlikely event that would have major policy consequences if it happened."

**What a case schema should borrow:** These five techniques map directly onto case-schema fields — Key Assumptions Check → a `stated_assumptions[]` field attached to the precedent's original decision; Indicators/Signposts → a `watch_indicators[]` field that could trigger re-review (pairs naturally with VEP's annual-reassessment clause above); ACH → a required `alternative_hypotheses[]` array scored against disconfirming evidence rather than confirming evidence; High-Impact/Low-Probability → a dedicated `tail_risk` field distinct from the main likelihood estimate, so low-probability catastrophic branches (e.g., capture of sensitive technology) aren't averaged away.

---

## 4. U.S. Army planning doctrine — ADP 5-0 and ADP 6-0

**Citations:**
- Headquarters, Department of the Army, *ADP 5-0: The Operations Process*, July 2019 (supersedes ADP 5-0 May 2012 and ADRP 5-0).
- Headquarters, Department of the Army, *ADP 6-0: Mission Command: Command and Control of Army Forces*, July 2019.

**Verified working URLs (directly fetched, content confirmed):**
- ADP 5-0: https://irp.fas.org/doddir/army/adp5_0.pdf
- ADP 6-0: https://irp.fas.org/doddir/army/adp6_0.pdf
- (Current official Army Publishing Directorate copies also located but not independently re-fetched in this pass: https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN18126-ADP_5-0-000-WEB-3.pdf and https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN34403-ADP_6-0-000-WEB-3.pdf)

**Commander's Critical Information Requirement (CCIR) — verbatim from ADP 5-0, para. 12:**
> "Commanders use CCIRs to focus information collection on the relevant information they need to make critical decisions throughout the conduct of operations. The two components of CCIRs are friendly force information requirements and priority intelligence requirements."
(Note: ADP 5-0 names but does not itself re-define PIR/FFIR as standalone glossary entries — those formal definitions live in JP 3-0/JP 5-0 and ADP 2-0. I did not independently re-verify the exact JP 3-0 wording — commonly cited as "an information requirement identified by the commander as being critical to facilitating timely decision-making" — by opening JP 3-0 itself in this pass, so that exact phrasing should be treated as a well-known paraphrase, not a directly-confirmed quote, until a JP 3-0/5-0 PDF is opened directly.)

**Decision point — verbatim (ADP 5-0 glossary, sourced to JP 5-0):**
> "A point in space or time the commander or staff anticipate making a key decision concerning a specific course of action. (JP 5-0)"

**Decision support matrix — description (verified via a secondary Army CALL/doctrine source, not ADP 5-0's own glossary, which does not define it):**
A decision support matrix (DSM) is a written (typically one-page) staff product — the tabular counterpart to the graphic decision support template (DST) — that lists each decision point, its location/trigger (often tied to a Named Area of Interest), the friendly/enemy conditions that must be met, the available actions/options, and the responsible unit, so the commander and staff can execute a pre-wargamed decision quickly during operations. Source for this description: https://www.globalsecurity.org/military/library/report/call/call_00-4_ch2.htm ("Improving Flexibility, Command, and Control With the Decision Support Matrix," U.S. Army Center for Army Lessons Learned). I was not able to open ADP 5-0/FM 6-0's own glossary definition of "decision support matrix" directly (FM 6-0's glossary section was not reachable in full through the fetch tool), so this field is triangulated rather than quoted from the primary source itself — flagged accordingly.

**Commander's intent — verbatim (ADP 6-0, para. 1-45):**
> "The commander's intent is a clear and concise expression of the purpose of the operation and the desired military end state that supports mission command, provides focus to the staff, and helps subordinate and supporting commanders act to achieve the commander's desired results without further orders, even when the operation does not unfold as planned."

**What a case schema should borrow:** `decision_point` (a discrete space/time trigger for a key choice), `ccir` (the small set of facts that would change the decision, split into "about the adversary/environment" = PIR and "about our own force/asset" = FFIR), and `commander's_intent` (an explicit purpose + end-state statement that lets a downstream agent act correctly even off-script) are exactly the three fields a case schema needs to let an agent recognize *that* it's at a decision point, *what* information should drive the choice, and *what* the precedent's guiding purpose was — independent of the specific branch chosen. The decision support matrix format (trigger → conditions → options → owner) is a strong template for the schema's `options[]` array at each decision point.

---

## 5. Lessons-learned formats — Joint (CJCSI/CJCSM 3150.25 series) and NATO

**Joint Lessons Learned Program citation:** Chairman of the Joint Chiefs of Staff, *CJCSI 3150.25H, Joint Lessons Learned Program (JLLP)*, and its associated manual *CJCSM 3150.25C*, which govern the Joint Lessons Learned Information System (JLLIS).

**URLs located (see verification caveat below):**
- https://www.jcs.mil/Portals/36/Documents/Library/Manuals/CJCSM%203150.25C.pdf
- https://www.jcs.mil/Portals/36/Documents/Library/Instructions/CJCSI%203150.25H%20CH%201.pdf
- https://www.jcs.mil/Portals/36/Documents/Doctrine/jlld/cjcsi3150_25.pdf

**Verification caveat (stated plainly):** All three jcs.mil URLs above returned an HTTP 403 (Akamai bot-protection block) to the automated fetch tool on every attempt in this session, despite being publicly listed/indexed and presumably viewable in an ordinary browser. **I could not directly open or quote the CJCSI/CJCSM 3150.25 text itself in this pass.** As the closest verifiable substitute, I opened a U.S. Army Center for Army Lessons Learned (CALL) handbook (mirrored by GlobalSecurity.org) that describes the standard **joint community** observation format side-by-side with the Army's and NATO's formats:

**Joint community observation format (verified, quoted from CALL handbook via GlobalSecurity.org mirror):** https://www.globalsecurity.org/military/library/report/call/call_11-33-ch2.htm
> "Topic/Issue: The title of the observation. Observation: One sentence explaining the observation. Discussion: The major analysis of the problem supported by facts and examples. Recommendations: A list of recommended corrective actions supported by the discussion. Implications/Lessons: A statement of what happens if the recommendations are not adopted."
This source presents the format as the joint community's own but does not itself cite CJCSI 3150.25 by number as the format's origin — so the *field names* (Topic/Issue, Observation, Discussion, Recommendations, Implications/Lessons) are verified via this secondary source; the specific instruction-number attribution to CJCSI/CJCSM 3150.25 is not independently confirmed in this pass.

**NATO Lessons Learned format ("ODCR") — verified, directly fetched:**
- URL: https://www.jallc.nato.int/application/files/4416/5781/2017/JALLC_LL_Handbook_Update_-_4th_Edition_FINAL_14072022.pdf (*The NATO Lessons Learned Handbook*, Joint Analysis and Lessons Learned Centre (JALLC), 4th Edition update)
- Format: **Observation, Discussion, Conclusion, Recommendation (ODCR)**, per Bi-SC Directive 080-006, Lessons Learned. Field definitions (quoted, p. 27–28):
  - **Observation:** "What happened? This should be a brief description of the issue to be avoided/improved or the success (good practice) to be repeated. Be sure to stick to the facts!"
  - **Discussion:** "What was supposed to happen and what actually happened? Include the context (where/when/who) and discuss why the issue/success occurred."
  - **Conclusion:** "What was the main reason, the root cause for why this issue/success happened? What can be learned from this?"
  - **Recommendation:** "What Remedial Actions do you recommend should be implemented to avoid/improve the issue or repeat the success in future?"
  - The handbook states entries into the NATO Lessons Learned Portal (NLLP) "must take" this ODCR format.

**What a case schema should borrow:** The two formats are near-identical in spirit and combine cleanly into one case-schema record: `observation` (what happened, facts only), `discussion` (context + why), `conclusion/root_cause` (NATO's addition — explicitly separating "why" from "what should follow" is valuable and the Joint format lacks it), `recommendation` (corrective action), and `implications` (Joint format's addition — consequence of *not* adopting the recommendation, useful for a case schema that wants to state the stakes of ignoring the precedent).

---

## 6. DoD Directive 3000.09, *Autonomy in Weapon Systems* (as amended Jan 25, 2023)

**Citation:** U.S. Department of Defense, *DoD Directive 3000.09, Autonomy in Weapon Systems*, originally issued November 21, 2012, updated/reissued January 25, 2023.

**URL located:** https://www.esd.whs.mil/portals/54/documents/dd/issuances/dodd/300009p.pdf

**Verification caveat:** This esd.whs.mil URL returned an HTTP 403 to the automated fetch tool on repeated attempts, so I could not open the primary PDF directly in this pass. As a secondary, cross-checking source I fetched the Wikipedia article on the directive, which itself quotes and cites the primary document:

**Verified (via Wikipedia, secondary source, itself sourced to the directive):** https://en.wikipedia.org/wiki/Department_of_Defense_Directive_3000.09
> "Autonomous and semi-autonomous weapon systems will be designed to allow commanders and operators to exercise appropriate levels of human judgment over the use of force."
Effective/reissue date confirmed as January 25, 2023.

Because I was not able to open the primary PDF directly, I am flagging this quote as verified-via-secondary-source rather than directly confirmed against the primary text — the phrase is extremely widely and consistently quoted (it is the directive's best-known sentence), which increases confidence, but per the task's verification standard it should be treated as one step removed from a direct open of the PDF.

**What a case schema should borrow:** A single, durable normative constraint field — `human_judgment_requirement` — that a case can carry independent of the specific decision made (i.e., not "was a human in the loop for *this* choice" but "what standard of human judgment does policy require to be *designable into* the system regardless of outcome") is a useful schema field for any case involving an autonomous or semi-autonomous platform (directly relevant to the autonomous-vessel example case).

---

## 7. Public precedents — protecting sensitive technology from capture

### (a) USS Pueblo seizure, January 23, 1968

**Sources:**
- NSA Center for Cryptologic History, *Cryptologic/Cryptographic Damage Assessment* (declassified), directly fetched and verified: https://www.nsa.gov/portals/75/documents/news-features/declassified-documents/uss-pueblo/damage-assessments/Cryptologic-Cryptographic_Damage_Assessment.pdf

**Verified facts (quoted/extracted):**
1. Emergency destruction of classified cryptologic material and four types of cryptographic equipment (KL-47, KW-7, KWR-37, KG-14) plus keying material, manuals, and COMSEC publications took place over "a 20 to 40 minute period immediately prior to the boarding" by North Korean forces, using burning in trash cans, attempted jettison of weighted bags (only one succeeded), laundry bags/mattress covers as substitute weighted bags, tearing/scattering documents, and fire axes/sledgehammers against equipment racks — the assessment describes the effort as accomplished "in almost total confusion and in a highly disorganized fashion."
2. Assessed document compromise: an estimated **50–80 percent** of classified documents were captured intact or reconstructable by North Korea.
3. Assessed equipment destruction: only **about 5 percent** of the cryptographic equipment was destroyed beyond repair or usefulness — the rest was captured largely intact. The damage assessment characterizes the resulting compromise of cryptologic information as "without precedence in U.S. cryptologic history."

### (b) EP-3 collision/landing at Hainan Island, April 1, 2001

**Source:** Naval History and Heritage Command, directly fetched and verified: https://www.history.navy.mil/research/archives/Collections/ncdu-det-206/2001/ep-3-collision--crew-detainment-and-homecoming.html

**Verified facts (quoted/extracted):**
1. The crew began emergency destruction of classified intelligence material and equipment as soon as the decision was made to make an emergency landing on Hainan (per the source: "as soon as LT Osborn made the call to land on Hainan").
2. Despite these efforts, the source states plainly that "the Chinese were still able to gather a large amount of material from the aircraft" — i.e., destruction was assessed as incomplete/only partially successful, though this source does not itemize exact methods (the widely reported detail that crew used hot coffee/water and physical force against equipment is corroborated elsewhere in the historical record — e.g., contemporaneous press and the Navy's oral-history collection referenced on this same page under "Emergency Destruction of Classified Material and Equipment" — but I did not independently open a primary source that itemizes the coffee/water method in this pass, so that specific detail is noted as commonly reported rather than directly verified here).

**What a case schema should borrow (both precedents):** Both cases show the same structural shape useful for a "sensitive-technology-under-threat-of-capture" decision node: (i) a hard time window between decision and capture (20–40 minutes for Pueblo) that should be a schema field (`time_to_compromise`), (ii) a partial/incomplete destruction outcome even under procedure (5% and "a large amount... gathered," respectively) that argues for treating "destruction succeeds" as a probabilistic outcome, not a binary the case can assume, and (iii) a documented institutional damage assessment produced *after* the event that closely resembles the lessons-learned ODCR/Observation-Discussion-Recommendation format in §5 — i.e., these two precedents are good raw material to run *through* the lessons-learned schema fields rather than being a separate format of their own.

---

## Consolidated URL list

1. VEP Charter (primary, verified): https://nsarchive.gwu.edu/sites/default/files/documents/5626625/The-White-House-Vulnerabilities-Equities-Policy.pdf
   Context page: https://nsarchive.gwu.edu/document/17688-white-house-vulnerabilities-equities-policy
   Mirror: https://assets.documentcloud.org/documents/4224051/External-Unclassified-VEP-Charter-FINAL.pdf
2. ICD 203 (verified): https://archive.dni.gov/files/documents/ICD/ICD-203.pdf (redirect target of https://www.odni.gov/files/documents/ICD/ICD-203.pdf)
3. CIA Tradecraft Primer (verified): https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf
4. ADP 5-0 (verified): https://irp.fas.org/doddir/army/adp5_0.pdf
   ADP 6-0 (verified): https://irp.fas.org/doddir/army/adp6_0.pdf
   Decision support matrix, secondary source (verified): https://www.globalsecurity.org/military/library/report/call/call_00-4_ch2.htm
5. Joint lessons-learned format, secondary source (verified): https://www.globalsecurity.org/military/library/report/call/call_11-33-ch2.htm
   CJCSI/CJCSM 3150.25 primary URLs located but blocked (403, not opened): https://www.jcs.mil/Portals/36/Documents/Library/Manuals/CJCSM%203150.25C.pdf ; https://www.jcs.mil/Portals/36/Documents/Library/Instructions/CJCSI%203150.25H%20CH%201.pdf
   NATO Lessons Learned Handbook (verified): https://www.jallc.nato.int/application/files/4416/5781/2017/JALLC_LL_Handbook_Update_-_4th_Edition_FINAL_14072022.pdf
6. DoDD 3000.09 primary URL located but blocked (403, not opened): https://www.esd.whs.mil/portals/54/documents/dd/issuances/dodd/300009p.pdf
   Secondary/cross-check (verified): https://en.wikipedia.org/wiki/Department_of_Defense_Directive_3000.09
7. USS Pueblo, NSA damage assessment (verified): https://www.nsa.gov/portals/75/documents/news-features/declassified-documents/uss-pueblo/damage-assessments/Cryptologic-Cryptographic_Damage_Assessment.pdf
   EP-3/Hainan, Naval History and Heritage Command (verified): https://www.history.navy.mil/research/archives/Collections/ncdu-det-206/2001/ep-3-collision--crew-detainment-and-homecoming.html
