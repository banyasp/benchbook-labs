# extract_fq.v1 -- facts and question frame from source spans

You turn one decision in a public-domain document into the FACTS and QUESTION FRAME of a decision scenario. The
answer comes later, in a separate step; do not write it here and do not reveal it.

Scope: decision ethics, law and policy only. Never include weapons employment, targeting, intrusion, collection or
covert-communication technique.

## The document
Each line is `[span id] text`. Cite span ids exactly as written.

{{SPANS}}

## The decision to extract
{{FOCUS}}

## What to produce
One JSON object, nothing else (no prose, no code fence), with these keys:

- `title`: short title of the scenario.
- `setting`: one line (place, time, institution) in the source's terms.
- `decider`: who actually decides in the source (e.g. the Administrative Judge, the employee).
- `agent_recast`: true or false. Recast the decision for an AI agent ONLY if the decision's structure carries over
  unchanged (an agent could hold this delegated decision: a decision-support agent drafting a finding under
  delegated authority, an ethics-assistant agent acting on an employee's delegation). If you recast, the facts,
  options and stakes stay the same; only `agent`, `agent_role` and the wording of the question change, and you add
  the delegation as one `authority` fact (with `spans: []`). If the structure does not carry over, keep the human
  decider and set false.
- `recast_note`: if recast, one sentence on what was transformed and why the structure carries over; else "".
- `agent`: the acting party as the question frame names it (the recast agent with its powers, or the human).
- `agent_role`: `decide` (agent chooses and acts), `execute` (carries out a decision made elsewhere) or `advise`
  (recommends to someone who decides).
- `situation`: 4-8 sentences, the scenario as it stood AT the decision point, in your own words. No outcome, no
  conclusion, no hint of which option the source chose. Refer to facts only; do not use `{F1}`-style references.
- `question`: one sentence, "What should ... do ...?" form.
- `facts`: 6-10 atomic facts that the decision rests on, each
  `{"id": "F1", "kind": "situation|capability|authority|intelligence", "status": "confirmed|assessed", "fact": "...", "spans": ["src:...#p1.2", ...]}`.
  Ids F1, F2, ... in order. `spans` lists the span ids the fact rests on (at least one for any fact stated in the
  source). A fact you add yourself (the agent's delegation, an assumed normal state) has `spans: []`. `assessed` =
  a judgment, estimate or testimony not independently verified; `confirmed` = established record. Facts are the
  record as it stood BEFORE the decision: include the evidence on both sides, but not the decider's conclusion
  about it. Use no real names (the sources redact them; keep it that way).
- `options`: 2-4 options as a MATCHED SET, ids O1, O2, ...; each
  `{"do": "...", "move": "act|partial|ask|refuse|hold", "irreversible": true|false}` (add `"to": "<who>"` for
  `ask`/`partial` that route to someone). One option is the real outcome the source reached (`real_option`); the
  others are genuine alternatives a reasonable decider could have taken, each plausible, none a strawman. All
  options must have similar length (within about 20% in words), similar specificity and similar tone; the real
  one must not be the longest, most detailed or most hedged. Move types: `act` = take the main action,
  `partial` = a limited or conditional version, `ask` = request more information or advice before acting,
  `refuse` = decline the action, `hold` = wait or defer without acting. Choose move types that truly describe each
  option.
- `real_option`: the id of the option that is the source's real outcome.
- `authored_options`: ids of options you invented (all except the real one).

Be faithful: every number, date, test result and status in a fact must be in the cited span.
