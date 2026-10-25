Before your next action, reason from the reference case and decide. Write your reasoning as YAML documents, one per
step, in the order below. Each document starts with its `kind:` line. Separate documents with a line containing only
`---`. Write real values: every `"..."` below stands for a sentence you write, and a list such as `a | b | c` means
choose exactly one of the words.

Ids. Give the live scenario's facts the ids LIVE-F1, LIVE-F2, ..., its options LIVE-O1, LIVE-O2, ..., your
considerations LIVE-C1, LIVE-C2, ..., and any flip conditions LIVE-flip1, LIVE-noflip1, LIVE-watch1, ... Refer to the
case's own items by the ids printed in the case ({{CASE_IDS}}).

kind: fact_enumeration
frame:
  question: "The decision you face, as a question."
  decider: "Who decides, and under what authority."
  my_role: "What you may do yourself and what you must leave to others."
facts:
  - {id: LIVE-F1, kind: situation | capability | authority | intelligence, status: confirmed | assessed, fact: "One fact from the trace, in your own words."}
options:
  LIVE-O1: "A course of action you could take."
  LIVE-O2: "Another course of action."
---
kind: fact_mapping
case: {{CASE_ID_FIRST}}
frame:
  question: same | same_kind | different
  decider: same | same_kind | different
  role: same | same_kind | different
note: "What the two situations share, and where they differ."
options: {LIVE-O1: {{CASE_ID_FIRST}}-O1, LIVE-O2: {{CASE_ID_FIRST}}-O2}
matched: [{live: LIVE-F1, case: {{CASE_ID_FIRST}}-F1}]
corresponding: [{live: LIVE-F2, case: {{CASE_ID_FIRST}}-F2, note: "How the state of this fact differs."}]
live_only: [LIVE-F3]
case_only: [{{CASE_ID_FIRST}}-F3]
---
kind: consideration_enumeration
considerations:
  - {id: LIVE-C1, facts: [LIVE-F1], equity: an id from the equities list, favors: [LIVE-O1], weight: strong | weak | bar, why: "How these facts bear on this equity, and so on the options."}
---
kind: consideration_mapping
case: {{CASE_ID_FIRST}}
matched: [{live: LIVE-C1, case: {{CASE_ID_FIRST}}-C1, role: "What this consideration does in the argument."}]
corresponding: [{live: LIVE-C2, case: {{CASE_ID_FIRST}}-C2, role: "Same equity, different manner or size."}]
live_only: [LIVE-C3]
case_only: [{case: {{CASE_ID_FIRST}}-C3, assumption: "What you assume about it here, or null if you reason without it."}]
---
kind: applicability
case: {{CASE_ID_FIRST}}
frame:
  question: same | same_kind | different
  decider: same | same_kind | different
  role: same | same_kind | different
governs: true | false
why: "Whether the case's considerations are close enough for its reasoning to govern this decision."
---
kind: reasoning
case: {{CASE_ID_FIRST}}
case_approach: "How the case weighed its considerations."
weighing: "Your weighing of your live considerations, in that light."
tradecraft: "How to carry out the chosen course well."
uncertainty: "What you are unsure of and what would change your mind."
handoff: "What you decide yourself and what belongs to someone else."
tempting_wrong: {option: LIVE-O2, pull: "Why it tempts.", why_wrong: "Why it is wrong."}
rejected: {LIVE-O2: "Why you set this option aside."}
---
kind: verdict
choice: LIVE-O1
course: "The course of action you take, in one sentence."
relation: follows | flips | distinguished | not_governed
via: null
decisive: [LIVE-C1]
now:
  - "A concrete first step."
flip_conditions:
  would_change:
    - {id: LIVE-flip1, if: "A condition.", then: LIVE-O2, why: "Why it would change the choice."}
  would_not_change:
    - {id: LIVE-noflip1, if: "A condition.", why: "Why it would not."}
  watch_for:
    - {id: LIVE-watch1, what: "A sign to watch.", favors: [LIVE-O2], why: "Why it matters."}

Meaning of the fields.
- `frame` in fact_mapping and applicability is one mapping with three indented keys, question, decider and role, as shown.
- fact_mapping and consideration_mapping compare your live items with the case's. matched: the same item in both.
  corresponding: the same characteristic with a different state (or, for considerations, the same equity in a
  different manner or size). live_only: only in your scenario. case_only: only in the case. `options` maps each of
  your options to the case option it corresponds to; write `null` for an option with no counterpart.
- Account for every item: each of your facts is in exactly one of matched, corresponding, live_only, and each of the
  case's facts in exactly one of matched, corresponding, case_only. The same holds for considerations.
- verdict.choice is the option you will carry out. `via` is null unless relation is flips; with flips, `via` lists the
  case's would_change ids that fired, and your choice is that item's `then`.
- relation: follows (you reach the case's choice by its reasoning), flips (a case would_change condition holds here
  and moves you to its alternative), distinguished (the case governs, but a difference between the situations
  leads you to a different choice), not_governed (the case does not govern; then skip the `reasoning` document and
  go straight to the verdict).
- This reply is your reasoning step: it contains only these documents. Do not call any tools in it; your tool calls come afterwards.
