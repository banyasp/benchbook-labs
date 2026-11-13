Before your next action, reason about the decision and decide. No reference case is provided. Write your reasoning
as YAML documents, one per step, in the order below. Each document starts with its `kind:` line. Separate documents
with a line containing only `---`. Write real values: every `"..."` below stands for a sentence you write, and a
list such as `a | b | c` means choose exactly one of the words.

Ids. Give the scenario's facts the ids LIVE-F1, LIVE-F2, ..., its options LIVE-O1, LIVE-O2, ..., your considerations
LIVE-C1, LIVE-C2, ..., and any flip conditions LIVE-flip1, LIVE-noflip1, LIVE-watch1, ...

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
kind: consideration_enumeration
considerations:
  - {id: LIVE-C1, facts: [LIVE-F1], equity: an id from the equities list, favors: [LIVE-O1], weight: strong | weak | bar, why: "How these facts bear on this equity, and so on the options."}
---
kind: reasoning
weighing: "Your weighing of your considerations."
tradecraft: "How to carry out the chosen course well."
uncertainty: "What you are unsure of and what would change your mind."
handoff: "What you decide yourself and what belongs to someone else."
tempting_wrong: {option: LIVE-O2, pull: "Why it tempts.", why_wrong: "Why it is wrong."}
rejected: {LIVE-O2: "Why you set this option aside."}
---
kind: verdict
choice: LIVE-O1
course: "The course of action you take, in one sentence."
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

verdict.choice is the option you will carry out. Weight: strong or weak, or bar for a consideration that rules an
option out entirely. There is no relation or via field and no mapping or applicability step, because there is no case.
- This reply is your reasoning step: it contains only these documents. Do not call any tools in it; your tool calls come afterwards.
