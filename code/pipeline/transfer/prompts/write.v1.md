You turn a sketched SISTER scenario into a full structured decision scenario (one JSON object) for a benchmark that
tests reasoning by analogy. The sister is a cross-domain transfer of an ANCHOR scenario: its facts come from a
different national-security sub-domain, but its considerations are the SAME. It will be shown to an AI agent as a
reference case (a worked precedent), so it must read as a complete, credible worked decision in its own domain.

You get the anchor's full case (JSON) and the sketch. Return the sister's case as JSON with exactly the anchor case's
keys and nesting (omit `id`, `library` and `status`):

- `title`; `setting` (place, date or period, organization; invented organizations are fine; roles, never personal
  names); `decider`; `agent`; `agent_role` (same value as the anchor's); `situation` (4-8 sentences describing the
  situation AT the decision point: no outcome, no hint of the answer); `question` ("What should ... do ...?").
- `options`: the SAME option ids as the anchor. Each sister option corresponds to the anchor option with the same id,
  as in the sketch's option map. `do` is one plain, complete course of action with no justification. Keep `move` and
  `irreversible` of the corresponding anchor option, and `to` when the move is ask.
- `facts`: 6-10 atomic facts `{id: F1.., kind: situation|capability|authority|intelligence, status: confirmed|assessed,
  fact}` in the sister's domain, as the record stood BEFORE the decision. Together they must carry every consideration.
  No fact may say that this decision was already made or carried out (by the agent, its role or its decider), and no
  fact may state what happened afterwards. No fact restates a consideration's conclusion. Make them specific and
  credible (units, procedures, document types, stakes), at the decision level only.
- `considerations`: the SAME ids, `equity` ids, `favors` and `weight` as the anchor. Do not add, drop or reweight any.
  `facts` lists the sister fact ids that carry it. `why` re-expresses the anchor's reason in the sister's terms
  without stating the verdict.
- `reasoning`: same structure as the anchor's (read, weighing, tradecraft, uncertainty, handoff, tempting_wrong
  {option, pull, why_wrong}, rejected {option id: reason}). Re-express the anchor's reasoning in the sister's domain.
  The weighing follows the anchor's weighing step for step. Do not add new arguments or reach a different balance.
- `verdict`: the SAME `choice`, `basis` and `decisive` as the anchor.
- `flip_conditions`: map each anchor item into the sister's domain; keep the ids and the `then` options.
- `lesson`, `limits`: re-expressed for the sister's domain (keep any provenance sub-fields the anchor has).

Stay at the level of decision ethics, law, policy and judgment. No weapons employment, targeting, intrusion,
surveillance or collection technique, and no operational how-to: a capability may exist and acting may reveal it, but
never say how it works. Return the JSON object only.
