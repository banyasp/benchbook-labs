## National-security source: scope addendum (natsec_scope.v1)

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
- Doctrine manuals are not sources; do not draw on them.
