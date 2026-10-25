# Benchbook v7 prototype: report, round 1 (2026-09-29)

Written by the implementation agent; saved by the lead because the agent's tool could not write report files.
Implements `drafts/SPEC-v7-v1.md`. Nothing under `src/` or `review/` was modified.

## Tests
`./run_tests.sh` summary line: **`73 passed in 43.08s`**

| Test | Status | Covers |
|---|---|---|
| RT-1 n-ary lumping | pass, FIXED | compromise decomposes into PREP proceed + DEP route; a new DEP-A factor is compared only with the precedent's DEP-A factors |
| RT-2 three outcomes -> "unprecedented" | pass, FIXED | binary issues: DEP bounded, PREP settled |
| RT-3 off-point cliff | pass, FIXED | one or two equal substitutions both stay analogous (retain) |
| RT-4 catalog detail silences a distinction | pass, FIXED | per-equity: need_now stays uncovered; the M2 lint fires on the reversed equity order |
| RT-5 DOHA-F-07 + A20b2 -> grant | pass, FIXED | no longer settled on grant; F-01 is distinguished |
| RT-6 reason-rung convention | pass, CHANGED / STILL OPEN | convention stated and enforced (reason rung <= observed rung); which rung "sufficed" is still an author judgment |
| RT-7a doubled distinctions | pass, FIXED | one stem, DEP-B2@likely |
| RT-7b flip composition | pass, FIXED | near-miss cards plus route precedence give route(authorize) |
| RH-1 hollowing | pass, FIXED | hollow < partial honest < honest |
| RH-2 withholding pays | pass, FIXED | pi must be a distribution; honest pi maximises expected r_act + w_cal*r_cal on a grid |
| RH-3 whole casebook / gold-fixed primary | pass, CHANGED | harness uses served cards only |
| RH-4 unpriced flag | pass, CHANGED / partly OPEN | malformed flag fails G; false flag costs fixed k(T2) plus the route's k; break-even P(tags right) < 0.80 (was 0.855) |
| RH-6 may_act from gold | pass, FIXED | gate comes from the model's conditions; a hallucinated trigger departs (-9); WHO is scored |
| m1 no G | pass, FIXED | unknown ID, broken closure or inconsistent verdict give r_fail = -20 |
| m2 two p* | pass, FIXED | one p_star, imported by the reward; 0.8718 |
| (b) AUT-101 end to end | pass (4 tests) | gold plan reproduced from gold tags; with x1 applied, DEP becomes proceed A (binding) |
| (c) AUT-001 vs the v6 mapping | pass | new-against set collapses to DEP-B2 at rung likely; v6 mapping F1 = 1.0 |
| (d) monotonicity fuzz | pass (4 catalogs) | 5,000 random probes per catalog (AUT, VEP, SEC-F+doctrine, FISC) |
| (e) hollowing | pass (2 weight sets) | hollow max 0.57/0.49/1.05 vs honest min 1.21/1.27/2.17 (start weights) |
| (f) permutation invariance | pass | 18 scenarios; every composed action unchanged; oracle reward gap exactly 0 |
| (g) revised precedent | pass (4 tests) | served revised -> proceed; stale restatement: evaluation routes, training G = 0; decoy swap changes the action |
| Validator / schema / lints | pass (27) | all 21 files validate; each lint fires on a seeded defect |

## DOHA (leave-one-out over all 10, SEAD 4 catalog)

| Solver | Decided | Correct | One-tag changes | Wrong autonomous acts |
|---|---|---|---|---|
| v2 | 4/10 | 4/4 | 33/200 | 4/200 |
| v3 | 3/10 | 3/3 | 31/200 | 2/200 |
| v2 + doctrine | 5/10 | 5/5 | 40/230 | 3/230 |
| v3 + doctrine | 3/10 | 3/3 | 32/230 | 1/230 |

Baselines: count of A-side tags 10/10 (9/10 leave-one-out threshold); 1-NN 8/10.

## Ambiguities resolved (marked CHOICE in code)
1. Scaled strengths: a string rung value overrides listed equities; a dict rung value gives per-equity strengths.
2. Null-level roles (none, recommend) cannot act at all; delegations still grant.
3. Untiered permissive class is T0; tier floors apply only to tags on the same issue.
4. Contingent atoms come from inactive delegations.
5. `unreachable: <holder>` on conditions links unreachability to holders.
6. Issues in play = issues with a tag, a served card, a pi, a flag or a contested label.
7. Off point judged at stem level; coverage at the reason's stated rung.
8. Stability: uncertain conditions handled per delegation class; U* = items whose low and high extremes each yield stability.
9. rejected / known_at_decision:false / credibility_only facts add no tags; `found` in a situation is a warning.
10. Orders exclude factors on both sides (literal reading); an order confers no authority.
11. Mirror faces close upward; per-dimension flag.
12. Route flips apply when added tags present and removed tags absent; applicable route card beats a settled outcome.
13. Units are record-local.
14. r_read = (F + 0.25 S + 0.25 Q)/1.5.
15. Empty r_cmp = 0.
16. Flag cost applies per unmatched flag.
17. Gold kinds act / resolve / route; route on resolve costs -k (+rho if right); `resolution.hidden_resolution` added.
18. Mapping taken already parsed (dict); text grammar not implemented.
19. Pilot conversion details (claimed -> reported; placeholder confidence).

## Amendments proposed
A1 stakes tier from the issue (max over both sides) — implemented.
A2 unsettled issue with an out-of-role side routes (authorize); no pi -> route recommend null — implemented.
A3 conditions in a flip's change become requires/forbids on the near-miss card — implemented.
A4 near-miss cards need ceteris-paribus scope or lower rank (AUT-001 flip cards settle AUT-101 on hold) — not implemented.
A5 use effective strength for new-against distinctions (switch NEW_AGAINST_EFFECTIVE, off by default); DOHA with it: 3/10, 28/200, 2/200; with doctrine 4/10, 36/230, 1/230.
A6 route on a resolvable item costs -k (+rho).
A7 score or drop the SETTLE label and contingent atoms.
A8 small gaps (NONE, DEP-B9, unreachable:, hidden_resolution, f4 confidence; restrict order exclusions to factors against the directed side).

## Open issues
1. Perception dominates real-data errors (every remaining wrong act is one over-tag of a dispositive mitigator).
2. Circularity of judge-perception tags (count and 1-NN beat the solver).
3. Cross-record near-miss conflicts (A4).
4. Coupling violations reported, not acted on; mirror "same fact" approximate; DOHA per-allegation units absent.
5. RT-6 rung convention remains an authoring risk.
