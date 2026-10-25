# Hard Calls — 100 national-security scenarios for the Benchbook (v1, 2026-09-28)

Readable, commentable version: Claude Doc "Hard Calls: 100 National-Security Scenarios for the Benchbook"
https://claude.ai/code/artifact/adb49132-0800-4016-83b1-22653ed0a1ab
(Overview tab: summary, legend, the Sept 2026 landscape, cross-cutting patterns, per-area index; one tab per area; Open questions tab.)

## What's here
| Path | What it is |
| --- | --- |
| `hard-calls-cases.yaml` | All 100 case sketches, one list, schema below. The data layer. |
| `hard-calls-cases.jsonl` | Same, one JSON object per line. |
| `hard-calls-index.csv` | id, title, area, tier, agent_role, outcome, holding_basis, agent_move, failure_modes, holding. |
| `cases/AUT.md … AGT.md` | Rendered markdown per area (same content as the doc tabs). |
| `research/01–07` | The seven research strands (~78k words): authorities with verbatim quotes and URLs, precedents, primitives, seeds, [UNVERIFIED] lists. |
| `source-v1-2026-09-28.zip` | Everything used to build v1: research, drafts/v1 (drafter output), drafts/v2 (reviewed), review logs, drafting/review briefs, render script, checker. |
| `source-v1.1-2026-09-28-audit-fixes.zip` | drafts/v3 (v2 plus the independent audit's fixes; the current case files are built from v3) and the audit log. |

## Areas (IDs start at 101 so they never collide with AUT-001, VEP-001, VEP-004)
AUT 24 (autonomy, fires, law of war) · INT 13 (collection, civil liberties) · REL 13 (disclosure, tearlines, classification) · SEC 8 (infosec in the classification/insider sense) · ANL 18 (analysis, HUMINT, deception, influence) · OVS 13 (authorities, oversight, personnel) · AGT 11 (agent-native).
87 tactical, 10 operational, 3 strategic. Holding basis: 93 recommended, 5 settled, 2 contested.

## Case schema (maps onto benchbook-sections-v4)
`id, title, seed, tier, setting, agent, agent_role (none|recommend|execute|decide), decided_by, situation, options {A,B,…},
factors [{id, means, favors, equity, support (strong|weak), scale?}], outcome, holding, holding_basis (settled|recommended|contested),
reason [factor IDs], agent_move (act|ask|refuse|partial — …), resolve_vs_escalate, flip_rules [{change (+X|-X|new), if, then (option|escalate), why}],
watch_for [{what, favors}], downplay_trap, tempting_wrong_answer, failure_modes [fixed vocabulary], family, authorities [{cite,url}], analog [{name,lesson,url}], notes`

Factor IDs follow your convention (the letter is the option favored). Equities use a 28-term canonical list (see source zip, DRAFT-BRIEF.md). There is no per-area factor catalog yet: factor IDs are local to each case, so building catalogs (merging equivalent factors across cases) is the next step before running solver_v2.

Uses for the training design: flip rules → Distinguish scenarios; `downplay_trap` → Downplay-trap scenarios; the "case families" table on the doc's Overview → Bounded/open scenarios; `failure_modes` → eval tags.

## How it was made
7 research agents (Sonnet/Opus) → 8+3 drafters (Opus) → 10 reviewers (Sonnet) who opened every cited URL, corrected quotes and facts, and pressure-tested logic (review logs in the zip) → lead consistency pass → render.

## Known gaps
- **Cyber operations are not covered.** Drafting of that sub-area was stopped twice by a safety filter; it was not pushed through. The 14 cyber seeds remain in `research/04-cyber-infosec.md` §4. Information security is covered in its classification/insider sense (SEC).
- **AUT-107, AUT-108, AUT-109** are in these files but not in the doc's AUT tab (a filter stopped that insertion).
- 66 "FOR PETER" decisions and 77 [UNVERIFIED] items are listed in the doc's Open questions tab and in each case's `notes`.
- Several .mil primaries (DoDD 3000.09, parts of the Law of War Manual host, DoDM 5200.01) returned 403; mirrors used are named in the cites.
