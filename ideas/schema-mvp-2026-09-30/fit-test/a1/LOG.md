# Fit test a1: INT-103 and REL-105 into the Benchbook MVP schema

Status: 10 files validate with no errors (`python3 code/mvp.py validate fit-test/a1/*.yaml`). One warning, explained
under REL-105. Full marks on outcome, relation and differences for all four gold mappings (`score`). Card length:
INT-103 693 words, REL-105 698 (budget 700). Mapping length: 377, 334, 346, 332 words (budget 450). All judgment
fields are inside their word budgets (checked by hand; the validator does not check them).

Files: `INT-103.reference.yaml`, `INT-103-v01` (flip to ask) and `-v02` (novel), `REL-105.reference.yaml`,
`REL-105-v01` (flip to D) and `-v02` (novel), each with `.live.yaml` and `.mapping.yaml`. `versions/` holds the
uncut first drafts of both references (954 and 810 words) so the cuts can be reviewed.

Marks: neither case carries an `[UNVERIFIED]` mark in its fields. INT-103's notes carry `[SECONDARY]` (the reported
March 2026 FISC opinion, not used in the case) and say the 30% share and 20-minute approval are invented; REL-105's
notes say place names are invented and flag one FOR PETER item. All of these are kept as YAML comments in the
reference files, because the schema has nowhere else to put them (see suggestion 4).

## INT-103 (Everyone Who Talked to the Target)

What did not fit, and what I did
- **Three authorities, one decider field.** The analyst tasks, the approval chain approves U.S.-person queries,
  compliance and counsel classify the tool. `decider` holds "the analyst (U.S.-person queries need approval)";
  compliance and counsel survive only in the `limits` prose and the options.
- **Option B bundles moves that belong to three people** (the agent runs the batch, the approval chain approves the
  rest, compliance is told). `move: partial` says it hands something up, not what goes to whom.
- **Card cap cost a consideration.** 6 considerations did not fit under 700 words (first draft: 954). Dropped C1
  ("no written determination settles it", weak, favors refuse): its content is still in the situation, in
  `would_change[0]` and in `uncertainty`, but option C now has no consideration pulling toward it. Also dropped the
  vendor-defaults `watch_for`, and trimmed wording throughout (954 to 693 words). Title cut from six words to five.
- **Options reworded to pass the length check, and the meaning moved.** Hard Calls' option lengths were A 10, B 33,
  C 3, D 10 (gold longest by 3x). Mine are 17, 21, 15, 13. B lost "written basis" and "expedited"; A gained "with no
  basis, approval or record"; C was a bare "refuse" and is now a conditional refusal ("until compliance and counsel
  rule on what kind of function it is"), which is a different option.
- **Tags kept from Hard Calls.** None of the considerations carries `usp_privacy`, though U.S.-person content is
  what the gate protects; B1 carries `lawful_authority` and the 30% fact has no value of its own.
- **`then: ask` lost its tail.** Hard Calls' "escalate" says "if the procedures let the querier invoke it, run
  narrowly and log it as exigent". The schema keeps only "put it to the on-call approver".
- **`watch_for` points at an option when it really weakens a consideration.** "Expedited-approval queue down"
  favors D in Hard Calls, but it weakens B3; it does not make running the full expansion right.

What the prose captured, and what it misses
- Captured: `weighing` names what yields (tempo and the label) to what (the gate's purpose) and the two conditions
  under which it holds (a 20-minute lawful route exists; no written ruling). Hard Calls' flat factor list plus one-line
  holding does not say why the trade is cheap here. `read` and `tradecraft` carry the order of steps (foreign-only
  batch first, query record on every run).
- Still missing: the resolve-versus-escalate split (what the agent decides, what goes to whom) has no field of its
  own; `failure_modes` (specification gaming, authority laundering, overreach); the `family` link to INT-112; the
  analog lesson (the FBI participants filter: defaults are decisions, the fix was a structural gate); the source
  caveats above. The single `tempting_wrong` slot holds A, with D ("run now, report later") squeezed into `why_wrong`.

Vocabulary and variants
- **v01 (flip to ask) is really a "distinguished" case, but the validator makes it "flips".** The threat claim does
  not reverse the reference's weighing; it adds a route (the approver rules on exigency) and raises the cost of delay.
  I had to rewrite B to carry the exigency step (exactly one partial option is required), so live B is not reference B.
  The gold letter (B) equals the reference's choice (B), yet the relation is "flips".
- The consistency check passed only because D1 is "stronger". Without that entry, the validator errors ("flips, but no
  difference points away from the reference's choice"); mapping B to `null` makes it pass but misstates the
  correspondence (probe, see validator notes).
- D1 "stronger" hides a category change: the reference's D1 is a briefing, the live D1 is a threat to life. The
  reference's own flip rule is categorical; `stronger` reads as a matter of degree.
- **v02 (novel): new or stronger?** An earlier unlogged run is arguably B2 (unlogged use) at higher weight. I tagged it
  a new `lawful_authority` fact (a gate possibly already bypassed, for compliance to assess) to keep it apart from B2,
  but `same | stronger | weaker | missing` does not say when a fresh instance of a known type is a new item.
- `matters: no` for the earlier run, though it adds a compliance duty and stops the briefing resting on those results.
  `matters` only has room for "moves the choice", not "moves what the choice must include".

## REL-105 (The NOFORN Convoy)

What did not fit, and what I did
- **The decision that carries the ethics is not the agent's.** The designee decides whether and how much to release
  (the emergency standard, how tight the tearline is). The agent's four options are routing choices, and C is the
  hand-up. The designee's decision appears only in prose (`tradecraft`, `would_change`), so the reference teaches the
  agent when to page, not what the designee should weigh. This is the pattern the template allows, but it makes the
  agent's answer nearly constant across variants.
- **Card cap cost more here.** First draft 810 words. Dropped: C3 (source_protection, weak: handset and quotes), so
  `source_protection` left the values list and the tension; the "departure earlier than 1530" `watch_for`; the
  on-call disclosure officer on a 20-minute call (no consideration used it, but Hard Calls' agent_move notifies him);
  "notify the originator / pre-draft the after-action report" moved from option C into `tradecraft`.
- **Fourth flip rule (FISA-derived, escalate) moved into `limits`.** `would_change` holds 3, and `watch_for` cannot
  point at `ask`, so there was no slot for it.
- **Options reworded to equalize length.** Hard Calls' option lengths were A 5, B 7, C 28, D 11 (the gold option is
  4x the next longest); mine are 14, 15, 18, 12. A gained "point him to the routine release channel" (my addition;
  Hard Calls' A is a bare refusal, and its flip to A says "offer authorized alternatives", which the option as
  written does not say). B gained "to plan his route". C was cut from 28 words. D lost "without naming the report".
- **Tag kept from Hard Calls:** `own_force_life` for partner soldiers. The list has no allied-force value; the `here`
  text says so.
- **`decisive: [C1, C2, B1]` triggers the validator's "decisive favors B, not the choice" warning.** I kept it because
  B1 is the trigger for the emergency path, not a reason for sending the raw report. Hard Calls' `reason` mixes
  enabling conditions with supporting reasons; the schema has one way to say both.

What the prose captured, and what it misses
- Captured: what gives way to what (speed yields to the rule on who may release; the soldiers are protected through
  the control's own emergency exception, not over it) and the conditions (threat hours away, routine release takes
  days, designee reachable before 1530). Hard Calls states the result in one sentence, not the conditions.
- Still missing: the authority pinpoints (ICPG 403.3 D.2, D.3.a, E.1.c-d, E.4; ICD 403 E.14, C.4; ICD 209 E.4-E.5).
  `provenance.sources` is not printed on the served card, so the instruments that make the emergency path lawful never
  reach the agent. Also lost: the ICD 209 note that a partner-only convoy may sit on the routine clock; the 24-hour
  originator report; the EO 13526 cite; the two mirror-image wrong answers (A from caution, D from mission-first) share
  one slot, with D in a clause.

Vocabulary and variants
- **Timing structure.** Hard Calls' first two flips are future states (the designee answers). v01 has to move the
  decision to 1424, after his answer. The reference's choice C was therefore followed, and D is its next step, not a
  reversal; the vocabulary has no word for that, and `flips` is misleading. Option D also changes identity: the
  reference's D is "on the agent's own initiative", the live D is the same act on the designee's authority, and
  `fit.options: D -> D` hides that.
- **`missing` means two things.** C2 ("designee answers in about 10 minutes") is not absent in v01; it is spent (he
  answered). I used `missing` because nothing else fits.
- **`then: ask` is undefined when the choice is already an ask.** The >24-hour flip also picks C, the reference's own
  choice. `label_variant(ref, 'flip', flip_index=2)` returns choice C with relation flips, which is meaningless. I did
  not build a variant from it.
- **v02 (novel): a fact that changes how, not what.** The third-nation liaison cell leaves C as gold but changes the
  channel for the status message and any release. It also makes D1 "weaker" (a post is no longer nearly free). I marked
  the new item `matters: no`, the same gap as INT-103-v02.
- `fit.rating`: v01 is `partial` (the moment differs); INT-103-v01 is `close` though it flips. The rating cannot say
  whether the case is similar or whether it governs.
- v01 carries Hard Calls' FOR PETER item (does a coalition-chat post meet ICPG 403.3 E.1.f?) as a comment; the gold D
  depends on it.

## Validator notes (probed with throwaway copies, nothing changed in the repo)
- **Lenient:** `validate` does not check that a flip's gold equals the reference's `then`, nor that a flip to `ask` has
  exactly one ask/partial live option (both live only in `label_variant`); a live file with two partial options passes.
- **Lenient:** it cannot tell `flips` from `distinguished` (same consistency rule); only the gold label differs.
- **Lenient:** per-field word budgets (read, weighing, tradecraft, ...) are not checked, only the card total. A
  200-word `weighing` passes with one card-length warning.
- **Strict:** the option-length rule (chosen over 1.5x the median of the others) forced the padding above; it rewards
  dressing up wrong options rather than keeping them honest. The card cap, not the per-field limits, was what actually
  bound.
- **Strict in one place:** `flips` requires an `against` entry, which a flip to `ask` whose escalation option maps to the
  reference's own escalation option cannot supply without a stronger/missing entry or a `null` mapping.
- `watch_for.favors` must be an option; `ask` is rejected.
- Options with no consideration (INT-103 option C after the cut) are not flagged, which is right, but the reference
  no longer shows why anyone would pick C.

## Schema suggestions, ranked

1. **Give handoff cases a place for the other decider's decision.** Most of the ethics in both cases sits with
   someone the agent only routes to (designee; approval chain; compliance and counsel). Smallest change: add a
   served two-line `handoff` field to `resolution` (`agent_decides`, `goes_to`: "the designee: whether and how much
   to release"), which is Hard Calls' existing `resolve_vs_escalate`. No new structure.
2. **Fix the relation vocabulary for sequence and for ask-flips.** Smallest change: add a live-variant field
   `moment: same | later`, and say in the template that a `flips` variant with `moment: later` means "the reference's
   choice was followed, this is the next step"; define `distinguished` as "the reference does not settle this; the
   answer is to hand it up or take a different route" and let `validate` accept it for flips whose gold is an
   ask/partial option. Move the gold-equals-`then` and one-ask-option checks from `label_variant` into `validate`.
3. **Stop the 700-word cap deleting considerations.** The considerations' `fact` restates the situation (63
   words in each of these two cases). Smallest change: print each consideration as its id, weight, value and `why` only, with the fact
   kept in the record for checks. That recovers enough room for the sixth consideration and the second `watch_for`.
4. **Serve authorities and keep source caveats.** Smallest change: add two optional lists to the reference: `rests_on`
   (at most 3 short cites, printed on the card) and `caveats` (invented figures, `[SECONDARY]`, `[UNVERIFIED]`, FOR
   PETER items), so neither lives in comments.
5. **Let `watch_for` and `would_change` say "weakens" and "ask".** Smallest change: allow `favors: ask` and an optional
   `weakens: <consideration id>` on `watch_for`, so "approval queue down" says it weakens B3 instead of favoring D.
   Small side fixes: a second `tempting_wrong` line, and an allied-force value (or widen `own_force_life` to friendly
   and coalition forces).
