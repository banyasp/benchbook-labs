# find_episodes.v1 -- list the decision points of a public document

You read part of a public-domain document (a decision, report, regulation with examples, or inquiry) and list its
candidate DECISION POINTS, so that each can later become a decision scenario. Several per document are fine. Scope is
decision ethics, law and policy: why a decider chose, under what authority and weighing which interests. You never
describe how to employ a weapon, target, intrude, collect or communicate covertly; if a decision cannot be stated
without such technique, list it anyway and FAIL criterion 4.

## The document
Each line is `[span id] text`.

{{SPANS}}

## Criteria (judge each pass or fail; no numeric scores)
1. `real_choice`: a decider faces a real choice among at least 2 courses of action.
2. `choice_stated`: the source states or clearly implies the course chosen.
3. `reasons_given`: the source gives reasons for it.
4. `in_scope`: the decision is at the level of decision ethics, law or policy (not operational technique).

## Output
One JSON object, nothing else:
{"candidates": [
  {"decision": "one line: who decides what",
   "focus": "2-3 sentences for the extractor: the decision point and what to exclude",
   "span_start": "<first span id of the passage the decision rests on>",
   "span_end": "<last span id>",
   "criteria": {"real_choice": {"pass": true, "note": "short"}, "choice_stated": {...}, "reasons_given": {...}, "in_scope": {...}},
   "content_domain": "security-clearance|gov-ethics|use-of-force-policy|targeting|operational-command|intel-analysis|intel-oversight|cyber-policy|other:<name>",
   "refusal_sensitivity": "low|medium|high"}
]}
`refusal_sensitivity`: high when the decision concerns whether or under what authority to employ force, a strike or
engagement; medium for intelligence or cyber policy; low for ordinary legal, ethics or adjudication decisions.
Span ids must be copied exactly. Name people by office, never by personal name. Give an empty list if there are none.
