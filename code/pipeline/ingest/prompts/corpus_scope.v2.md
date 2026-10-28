## National-security corpus source: scope addendum (corpus_scope.v2; from corpus_scope.v1, 2026-10-28)

This source records a military or national-security decision. Extract the DECISION and nothing else. Scope: decision
ethics, law and policy. The scenario trains judgment about whether, who, and on what authority; it never trains how a
weapon is employed or how a target is found.

### Keep (decision level)
- Who decided, by office or role only (for example "the regional commander", "the strike cell", "the ship's commanding
  officer", "the investigating officer", "the convening authority"). Never personal names, call signs or unit-member names.
- The options actually open at the decision point, including options offered and declined (for example "the pilots
  offered a show of force; the commander declined").
- The equities in tension: force protection, civilian harm, mission, legitimacy, lawful authority.
- The authority and the legal standard in play: rules of engagement and their conditions (for example an imminent-threat
  condition), delegation of approval authority ("approval authority had been delegated to the brigade"), distinction,
  proportionality, precautions, positive identification as a legal or ROE threshold.
- Facts about what the deciders believed or were told, at the level of a sentence ("the strike cell assessed that civilians
  were likely present", "the track was assessed as hostile on the basis of the information the crew held").
- The stated reasoning of the decider and of the reviewing authority, the outcome, and the review findings.
- For findings that conflict (majority and dissent, investigator and convening authority, a later reversal): the outcome is
  the convening or final authority's finding; keep the disagreement as a recorded dispute (verdict basis `contested` where
  the source itself records real disagreement).

### Strip (do not write these, even as background or as a fact)
- Munition, warhead and fuze selection or settings; weapon types, designations and weights.
- Collateral-damage-estimation mechanics: methodology, tiers, levels, cut-off values, radii, distances, casualty models.
- Sensor and ISR procedures: what sensor was pointed where, how tracks or targets were located, held, cued or designated,
  collection or pattern-of-life method, IFF and radar technique.
- Attack geometry and tactics: headings, altitudes, approaches, release parameters, sequencing of passes, aimpoints, routes.
- Targeting-cycle procedure steps and checklists, brief formats, and anything else that reads as how to employ a weapon or
  find a target.
- Intelligence and security technique: how sources are recruited, run or communicated with; collection, surveillance,
  interception, intrusion or exploitation methods; cryptologic or technical collection detail; covert-communication or
  concealment methods; handling of seized devices. Keep that an activity happened and under what authority, never how.
Replace a stripped detail by its decision-level consequence in a few words ("the aircraft engaged", "the weapon was
selected by the strike cell") or omit it. If the decision cannot be stated without such a detail, do not extract the episode:
return the refusal object `{"skip": "technique", "reason": "<one line, no technique>"}`.

### Language and style
- If the source is not in English (for example German), write the scenario in English and state in `provenance_note` that
  the text was translated from the source language by the extractor (R60). Keep legal terms of art accurate; do not add
  detail the source lacks.
- No source-narration phrases ("the report says", "according to the inquiry", "the document states"). State facts and
  reasons as facts and reasons, attributed to the office that held them when attribution matters.
- Quote spans only for decision-level content; a span whose text is mostly technique is not cited.

### The options: the alternatives the decider actually had
- List the genuine courses of action a reasonable decider in this position had at the decision point: **three or four
  where the source's situation supports them** (for example approve, approve with conditions or limits, defer to obtain
  more information, refer to a higher authority, decline), and two only when the situation genuinely allowed only two.
- Each option is a complete course of action, plausible and distinct; none is a straw man, and none is invented beyond
  what the situation allowed. Options the source mentions as considered, proposed, offered or declined belong in the set.
- The source's real outcome (`real_option`) is one of them. Do not phrase the decision point as "whether to X" with only
  X and not-X when the source shows other courses were open.

### The real outcome (`real_option`) and its basis
- When the source, a later inquiry or the source's own assessment judges the decision (it was wrong, a failure, should
  have gone otherwise), `real_option` is the course that judgment endorses as what the decider SHOULD have done, and
  `basis_statement` names the office or work that judged it. Otherwise `real_option` is the course the decider took, with
  the decider's own stated reasoning.
- If the source is doctrine (a manual, directive or policy), the scenario is the situation the doctrine frames and
  `real_option` is the course the doctrine requires or recommends there; the doctrine's stated factors are the reasoning.
