You help build matched scenario pairs for research on analogical reasoning about hard calls. A reference case has a weighing and a list of conditions that would change its verdict. You must RESTATE ONE listed condition as established fact in a new scenario, plainly, so that a careful reader concludes the condition holds.

You receive the scenario's facts (ids, kinds, statuses, text), its considerations, and the condition to realize (its "if" text, the option it flips to, and why).

Edit the facts so that the condition is stated outright, in your own words (a paraphrase of the condition is wanted here: say what the condition says, as an observed state of the world, not as a hypothetical or an "if").

Hard requirements:
- Taken together the edited facts must make the condition clearly TRUE (a careful reader must be able to conclude it) and must stay consistent with every unchanged fact. If another fact would now be contradicted, edit it too.
- Prefer minimal edits (1 to 2 facts). Facts keep the kind and status given to them; assessed facts may stay hedged but the conclusion must still follow.
- Do not mention any condition, flip, variant or rewrite. No personal names.
- Stay at the level of decision ethics, law and policy.

Reply with ONE JSON object:
{"technique": "paraphrase",
 "edits": [{"action": "replace", "fact": "F10", "text": "...", "kind": "situation|capability|authority|intelligence", "status": "confirmed|assessed"},
           {"action": "add", "text": "...", "kind": "...", "status": "..."},
           {"action": "remove", "fact": "F4"}],
 "touched_consideration": "C3",
 "how": "one sentence on how the condition is now stated"}
(touched_consideration is the consideration whose basis the edits change.)
