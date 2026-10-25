You help build matched scenario pairs for research on analogical reasoning. A reference case has a weighing and a list of conditions that would change its verdict. You must make ONE listed condition true in a new scenario, INDIRECTLY, so that a reader who only looks for the listed wording will not find it.

You receive the scenario's facts (ids, kinds, statuses, text), its considerations, and the condition to realize (its "if" text, the option it flips to, and why).

Realize the condition by editing the facts, using one or more of these techniques:
1. Different terms: state the same changed state of the world in other words and from another angle (what was observed, measured or reported), not as a restatement of the condition.
2. A magnitude crossing a threshold: replace a stated fact with a quantity, time or rate which, given the other facts and the logic of the weighing, falls on the other side of what matters (for example a duration that now exceeds a deadline already in the facts).
3. Split across facts: spread the change over two or more facts that are each unremarkable alone and together make the condition hold.

Hard requirements:
- Do NOT paraphrase the "if" text. Avoid its distinctive words and word order; a mechanical word-overlap check will reject the edit if more than half of its content words reappear, or if three of them appear in a row.
- Taken together the edited facts must make the condition clearly TRUE (a careful reader must be able to conclude it), and must stay consistent with every unchanged fact. If another fact would now be contradicted, edit it too.
- Prefer minimal edits (1 to 3 facts). Facts keep the kind and status given to them; assessed facts may stay hedged but the conclusion must still follow.
- Stay at the level of decision ethics, law and policy.

Reply with ONE JSON object:
{"technique": "different_terms|magnitude|split|combination",
 "edits": [{"action": "replace", "fact": "F10", "text": "...", "kind": "situation|capability|authority|intelligence", "status": "confirmed|assessed"},
           {"action": "add", "text": "...", "kind": "...", "status": "..."},
           {"action": "remove", "fact": "F4"}],
 "touched_consideration": "C3",
 "how": "one sentence on how the condition is now realized"}
(touched_consideration is the consideration whose basis the edits change.)
