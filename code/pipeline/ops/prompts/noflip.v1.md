You edit a structured decision scenario (one JSON object) for a benchmark that tests reasoning by analogy. You get the
case and one of its `would_not_change` items `{id, if, why}`: the case says that even if the `if` were true, the right
choice would stay the same. Produce the variant in which the `if` condition IS true. The verdict does not change.

Change only what the condition requires:
- Facts: edit or add at most two facts so that the condition holds as a plain fact of the situation, before the
  decision. Do not state that any decision was made and do not state an outcome. Keep every other fact, with the same
  ids (a new fact takes the next free id).
- Situation: adjust the sentences that the changed facts touch, nothing else.
- Considerations: keep every id, `equity`, `favors` and `weight` EXACTLY. You may add the changed or new fact ids to
  the `facts` of a consideration they bear on, and adjust that consideration's `why` to mention them.
- Reasoning: keep the weighing and its balance; add at most one or two sentences acknowledging the new fact and why it
  does not change the choice (use the item's `why`). Keep tempting_wrong and rejected unless they must mention it.
- Verdict: unchanged (`choice`, `basis`, `decisive`).
- Flip conditions: remove the realized `would_not_change` item (it is now part of the situation); keep every other
  item unchanged.
- Lesson and limits: unchanged.

Same keys and nesting as the input (omit `id`, `library` and `status`). Same decision-level constraints: no weapons
employment, targeting, intrusion, surveillance or collection technique. Return the JSON object only.
