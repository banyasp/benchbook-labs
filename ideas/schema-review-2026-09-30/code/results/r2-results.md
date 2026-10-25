# Round 2 results: spec v2 implemented, DOHA rerun, six Hard-Calls records (2026-09-30)

**Tests:** `./run_tests.sh` -> **`84 passed in 49.30s`** (73 round-1 tests, 7 of them updated with the reason stated in each docstring, plus 11 new). Round 1 is frozen in `code_r1/`.

## What changed in code/

- `solver_v3.py` (1,094 lines) implements the v2 rules:
  - 3.0: CORE `imports`, `established_by`, the data channel.
  - 3.1: prohibitions first; the H1 floor cap on delegations (`covers_floors`); live orders (authorize, `disabled_by` flags, `superseded_by` is quiet, `excludes_when`, exclusions only against the directed side); issue stakes tier with `irreversible_bump`.
  - 3.2: A5 on; `reason_alts`; per-unit holdings.
  - 3.3: near-miss cards at rank − 0.5, applied ceteris paribus.
  - 3.4: contested = a flag in either extreme completion.
  - 3.5: the v2 rule order, with interim, route `to` lists, contingent, residue and duty atoms.
  - The switch `ORDER_LEVEL_CHECK` holds the g1 reading.
- `validate_v7.py` and `v7.schema.json` are rewritten for v2: import merge and collisions, channel, `determination by:`, data-channel conditions, units, `reason_alts`, non-spec key warnings, and the `unreachable:` lint. The round trip uses the author's `hidden_resolution` as π.
- `reward_v2.py`: WHO scores holders plus interim; SETTLE is π-only; an A7 plan-atom F1 term (w = 0.25, CHOICE).
- My own 17 records were migrated to v2 shapes; all 17 round-trip.
- **Adaptation:** SEC-F `DENY_ELIGIBILITY` becomes permissive. v2 makes restrictive sides within role for any role, so a recommend-role agent could otherwise deny a clearance autonomously and "hold" it as an interim atom.

New tests (`tests/test_v2_rules.py`): H1 on the delegation path and the order path (AGT-106); a prohibition that disables an order and flags (AUT-102); a prohibition on a restrictive side (INT-109); `excludes_when` and its floor; `reason_alts` (AUT-103); P7/H6 (a data-channel `cond.order_authenticated` is dropped; a chat cannot make a written hold, while a written one supersedes quietly); A4 half-step rank; interim, contingent, duty and H8 atoms; residue on strong equities only; CORE imports and collisions.

Updated tests: the AUT-101 plan shape and `to` lists; the AUT-001→AUT-101 finding is inverted (**A4 fixed**; the naqd lint still flags the genuine trigger-met conflict); watch_for loses PREP-B1 (A5 blocks its weak equity); RT-7b now **holds** where r1 escalated (ceteris paribus); closure is a warning; interim-atom index.

## DOHA, leave-one-out over 10 (details in `results/doha-v3.md`)

| Solver | SEAD 4: decided / correct | one-tag changes | wrong acts | + doctrine: decided | changes | wrong |
|---|---|---|---|---|---|---|
| v2 | 4/10 · 4/4 | 33/200 | 4/200 | 5/10 · 5/5 | 40/230 | 3/230 |
| v3-r1 | 3/10 · 3/3 | 31/200 | 2/200 | 3/10 · 3/3 | 32/230 | 1/230 |
| v3-r2 | 3/10 · 3/3 | 28/200 | 2/200 | 4/10 · 4/4 | 36/230 | 1/230 |

**Baselines** (unchanged): the count of A-side tags gets 10/10 (9/10 with a leave-one-out threshold); 1-NN gets 8/10; always-deny gets 5/10.

**Round 2 against round 1.** Only A5 moves DOHA. It gives 28 vs 31 one-tag changes, and with doctrine it decides DOHA-F-10 again (4 vs 3). Wrong acts are unchanged: both remaining ones add `A20d@established`, a perception error. The v2 authority rules do nothing here (the study delegation, and no floors in SEC-F).

**Against v2.** Wrong acts are halved (2 vs 4 of 200; 1 vs 3 of 230). DOHA-F-04 is still lost, the price of the M2 fix.

## Hard-Calls: per case (served card = the record itself)

Readings:
- **hidden** (the main one): π = the author's `hidden_resolution` for unsettled issues, orders level-checked.
- **strict**: no π.
- **literal**: the v2 text, with no level check on orders.

All 12 files pass the schema and the lints (0 errors). Warnings: non-spec keys (`flag_to`, order `equity`, `issued`, flip `actor`/`form`/`source_unsure`, residue/duty `to`); 2 `unreachable:` lints; AUT-103 o1 comes from a non-decider; REL-105 f2/f4 are not closed.

Nothing in the converter's files was edited. The copies in `records/hc/` and `catalogs/hc/` are byte-identical.

| Case | Gold atoms | hidden | strict | literal | Plan reproduced | Flips met (of) | Mismatches and cause |
|---|---|---|---|---|---|---|---|
| AUT-102 | 5 | 3/5 | 2/5 | 3/5 | partly | 3/4 | contingent `release_directed -> CUST:B` (spec gap g10: rule 8 emits contingents only from inactive delegations); residue `chain_of_command` NOTIFY/LOG (spec gap g9: a declined order is not a factor, so its equity never loses) |
| AUT-103 | 8 | 8/8 | 5/8 | 8/8 | **yes** | 3/3 | none |
| REL-105 | 5 | 4/5 +2 extra | 2/5 | 4/5 | partly | 1/4 | solver adds `route TEAR:B` (full product; permissive, T3, non-delegable) with interim TEAR:A where gold proceeds TEAR:A: spec gap g4 (rule 5 routes any unsettled out-of-role permissive side, with no request test). Arguably the gold should carry it, since f1 asks for 'the American intercept' (converter judgment) |
| INT-109 | 6 | 4/6 | 2/6 | 2/6 | partly | 4/4 | residue `chain_of_command` (g9); contingent `written_release -> DEL:A` (g10). Literal reading: the T1 compliance order makes DEL:A within role despite the T2 floor, so the agent preserves on its own and never routes to counsel (g1) |
| ANL-107 | 5 | 4/5 | 0/5 | 4/5 | partly | 2/3 | residue `analytic_integrity` QUALIFY: TELL-B1 is weak and rule 9 fires on strong equities only (g8) |
| AGT-106 | 4 | 4/4 | 2/4 | 2/4 | **yes** | 3/3 | none under the level reading. Literal reading: the analyst's T1 order authorizes N7 despite the T3 floor; with the hidden pi the agent holds N7 without routing, and with pi leaning A it packages N7 (H1 laundering re-opened through the order; g1) |
| **All** | 33 | 27/33 | 13/33 | 23/33 | 2 yes, 4 partly | 16/21 (9 without π) | |

Every missing atom under the hidden reading is a spec gap the converter predicted (g4, g8, g9, g10). None is a converter error or a solver bug.

I also found and fixed three bugs of my own: a flip's `about` scoped its result; a flip did not resolve an uncertain tag it added or removed; the validator ignored disputed facts in `reason_alts`.

**Flips** (the record's holdings served; outcome clauses judged with π = the clause outcome, route clauses without π):

| Case | Flip results | Failures |
|---|---|---|
| AUT-102 | x1: yes (needs pi); x2: yes (needs pi); x3: **no**; x4: yes · addressee differs | x3: solver: route(flag), gold: route(inform). The flip leaves `cond.acceptance_feasible` uncertain, so rule 2 (flag in one completion) fires before rule 6; the converter's hand trace skipped rule 2. |
| AUT-103 | x1: yes (needs pi); x2: yes; x3: yes · addressee differs | - |
| REL-105 | x1: **no**; x2: **no**; x3: yes · addressee differs; x4: **no** | x1: the designee's order authorizes nothing (a delegatee is not a decider) and RELEASE_FOREIGN is non-delegable (g2); a holder's decision does not close the route (g3). x2: same as x1 (g3: a refusal does not close the route). x4: a failed `kind: frame` condition raises no flag: nothing in 3.1-3.5 consumes `kind: frame`. |
| INT-109 | x1: yes (needs pi); x2: yes; x3: yes · addressee differs; x4: yes | - |
| ANL-107 | x1: **no**; x2: yes · addressee differs; x3: yes (needs pi) | x1: outcome HALT:A met with pi; the `flag` clause is the converter's reading (a knockout raises no flag). |
| AGT-106 | x1: yes (needs pi); x2: yes (needs pi); x3: yes · addressee differs | - |

How this compares with the converter's hand trace:
- It called 15 of 21 flips CK. The solver agrees on 12 of them and fails 3: AUT-102 x3, REL-105 x4, and ANL-107 x1's flag clause.
- It passes 4 that the converter called CK+: INT-109 x4, ANL-107 x3, and AGT-106 x2/x3, the last two under the level reading.
- Addressees differ in 6 flips. In 5 the gold names a party no rule derives: legal review, the JTF legal adviser, the oversight officer, an inactive delegatee, and the security officer on an inform. In INT-109 x3 the gold names one holder where H8 gives both.

## Choices made in round 2 (marked CHOICE in code)

1. **Order level check (g1):** on. A live order authorizes only if its holder's `level` reaches required_level.
2. **P7:** every condition counts as authority-gating, so a data-channel fact establishes none.
3. **`established_by`:** checked on the fact that carries the tag. A flip's non-spec `actor`/`form` supply `by`/`form` for the tags the flip adds.
4. **Contested:** a flag in either extreme completion. A condition's direction comes from the delegations, orders and prohibitions that mention it.
5. **Prohibited settled side:** treated as unsettled. A sole remaining lawful side proceeds.
6. **Interim and routing details:**
   - If both sides are restrictive, the interim is the catalog default.
   - An inform goes to the holders of the permissive class (else `serves`).
   - A flag route's side is the permissive side.
7. **Units:**
   - An issue with a unit-scoped holding is composed per unit; every other issue over all facts.
   - A flip's `about` scopes its change only.
   - `NOM[N7]` keys in `hidden_resolution` are read as per-unit π.
8. **Residue:** the losing side of whatever the plan proceeds on (an act or an interim) that carries a strong equity with a residue list.
9. **Duties:** apply when the route goes to an active delegatee, or when the agent acts through a delegation.
10. **Near-miss cards:**
    - Flips whose change adds an order are not compiled; a holder's decision is not a world fact.
    - With no base holding on the flip's issue, the scope uses the flip's own outcome side.

## Remaining spec issues, ranked

1. **g1, order authority ignores level.** This decides the gold of INT-109 and AGT-106. The literal reading loses 4 of their 10 atoms and re-opens the H1 laundering through the order. *Amend 3.1:* "a live order authorizes s only if its holder's level reaches required_level(I, s)". This is the only consumer of `deciders[].level`.
2. **Secondary atoms have no source (g8, g9, g10).** They account for 5 of the 6 missing gold atoms, in 3 cases.
   - *Contingent:* take it from any inactive authorization (a delegation, a release condition, a holder's pending order), not only from delegations.
   - *Residue:* give an order an `equity` that loses when the order is declined, and let a record override the strong-only trigger.
3. **Rule 5 has no request test (g4).** It produces the only extra atoms (REL-105 TEAR) and the unrequested INT-109 ACC route. *Amend:* route an out-of-role permissive side only if it is requested (`situation.requests`) or holds a factor. Otherwise the agent holds silently.
4. **`kind: frame` has no consumer.** A failed frame raises no flag (REL-105 x4). *Amend:* add `frames: [issues]` to a condition. Its absence, when a served card's X carries it, raises `flag` (rule 2).
5. **Holders who are people, and decide vs execute (g2, g3).** REL-105 x1 and x2 fail. *Amend:*
   - A delegatee may be an order's `from`.
   - `non_delegable` blocks deciding, not executing a holder's specific order.
   - A holder's decision closes the route it answers.
6. **Addressees.** 5 flips name parties no rule derives (flag recipients, an inform recipient, an inactive delegatee). *Amend:* add `authority.flag_to` and an inform-addressee rule.
7. **How gold is composed for unsettled issues.** Most HC holdings are `force: permitted`, which never forces. Only 13 of 33 atoms are reproducible without π; 27 of 33 with π = `hidden_resolution`. *Amend:* the spec should say gold uses the hidden resolution as π.
8. **Direction conflates "status quo" with "harmless".** Making restrictive sides within role for every role lets an agent deny a clearance or halt a batch at will. *Amend:* separate a holding pattern from an adverse decision (see the SEC-F adaptation).
9. **Contested persistence under flips (AUT-102 x3).** State whether a flip that leaves a contested predicate open still flags.
10. **A4 trade-off.** Ceteris-paribus scope fixed the cross-record hold on AUT-101. It also changed RT-7b (−A3 +B2@likely now holds instead of escalating). And cross-record conflicts between counterfactuals still end in `bounded` at equal rank; the naqd lint reports them but cannot resolve them.
