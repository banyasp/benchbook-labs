# Live scenario SEC-F-LIVE-001 (synthetic, re-situated)

**What this is.** A synthetic case file and work queue for an adjudication-support agent. It is re-situated from a real, public, redacted DOHA decision, ISCR Case No. 25-00861 (2026-08-31, granted; `cases/DOHA-F-03.yaml`). The applicant, family, employer, creditors, places, account numbers and amounts are invented or shifted, and dates are moved three years later. The fact pattern is preserved. Nothing here is a real record.

**What the agent sees:** `inbox/` (4 items; `Q1` is the assignment) and `case-file/` (11 items), 4,497 words in total. **What it never sees:** this README and `salience.yaml`.

**Task (from Q1):** draft a bench memo for ISCR 28-01317 with findings per SOR subparagraph, the disqualifying and mitigating conditions that apply, the whole-person analysis, and a grant or deny recommendation with a confidence. Flag post-hearing items for the judge. `agent_role: recommend`: the agent recommends and the judge decides.

**Gold.** The R-gold is the real outcome, A (grant). With gold tags the solver returns *bounded* (see `../heldout-results.md`), so this is a residual-judgment item: the agent must resolve it and state a confidence. Two flags are expected: (1) the CVP alert is post-record and reports the same account as SOR 1.c; (2) the Northgate letter settles a different account from SOR 1.f. `a_gold` in `salience.yaml` is left empty for Peter to fill in blind.

**Noise.** Measured by `../tools/check_salience.py`: 17% of words sit in decision-relevant spans (83% non-relevant). Counted at line level, including near-miss material, the relevant share is 23% (77% non-relevant). Both are a little noisier than the 60–75% target.

**Conventions borrowed** (from the pilot decisions and the public SF-86): SOR allegation wording ("As of the date of this Statement of Reasons ..."); GE/AE exhibit numbering; FORM, SCA, PFS and CBR abbreviations; SF-86 items 26.3, 26.5 and 26.7 quoted verbatim from the form; "DoD Continuous Vetting Program (CVP)" alerts; "personal subject interview". IRS transcript codes (150, 806, 971, 276, 196, 670) follow public IRS usage; the pilot did not check them against the IRS code manual. **[UNVERIFIED]**
