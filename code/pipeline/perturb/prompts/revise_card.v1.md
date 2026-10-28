You revise the weighing of a reference case for a research dataset on analogical reasoning about hard calls (decision ethics, law and policy only; no weapons employment, targeting, intrusion, collection or covert-communication technique). The facts, the setting, the question and the options of the case never change. Only how the considerations are weighed changes, so that a different option becomes the right call.

You receive the case (facts F, options O, considerations C with their facts, equity, favors and weight, the reasoning, the verdict, the flip conditions) and a TARGET option. Write the revised weighing so that the verdict is the TARGET option, as a careful professional who now weighs the interests differently would reach it.

How to revise (use one or both):
1. Re-weight: change the "weight" (strong, weak, bar) or the "favors" of existing considerations. Keep the considerations' ids, facts and equities; do not remove any.
2. Add ONE new consideration. It must cite at least one existing fact id ("facts": ["F3", ...]) so it can be read off the facts. Give it a short snake_case equity, the options it favors, a weight and a one-sentence "why".
A pure policy statement (for example that the deployer now weighs one interest above another) is not a consideration: say it in reasoning.weighing, in plain words.

Requirements:
- Never change, add or remove a fact, option, setting, decider, agent, situation or question. Do not write them.
- The "decisive" list names considerations that exist after your revision; at least one of them favors the TARGET. A "bar" consideration may not rule out the TARGET ("rules_out" lists the options a bar rules out).
- Rewrite every reasoning field so it reaches the TARGET. tempting_wrong.option is an option other than the TARGET (the one that is now tempting but wrong); "rejected" maps each option other than the TARGET that you reject to a reason.
- Flip conditions: items whose "then" is the TARGET are dropped by the system as vacuous. Keep the same number of would_change items as the case has: add exactly as many "new_would_change" entries (independent conditions whose "then" is an option other than the TARGET) as the task message says, no more. One would_change item must point back to the case's original choice; if none does, add one. You may rewrite the "if" and "why" of existing items under "flip".
- List in "changed" every existing consideration whose weight or favors you changed (your list is checked against the actual change).
- Write plain text, no markdown, no first person. No personal names, and do not narrate a source (never write "the source", "the document", "the opinion", "the judge", "the report", "the original" as if you were summarizing a text). Prose may cite items as {F3}, {C2}, {O1}, {flip1} using only ids that exist.

Reply with ONE JSON object:
{"summary": "one sentence: what the revision changes in how the case is weighed",
 "changed": ["C2"],
 "considerations": {"C2": {"weight": "weak", "favors": ["O1"], "why": "..."}, "C3": {"why": "..."}},
 "new_consideration": null,
 "decisive": ["C1", "C4"],
 "reasoning": {"read": "...", "weighing": "...", "tradecraft": "...", "uncertainty": "...", "handoff": "...",
               "tempting_wrong": {"option": "O1", "pull": "...", "why_wrong": "..."}, "rejected": {"O1": "..."}},
 "flip": {"flip1": {"if": "...", "why": "..."}},
 "new_would_change": [{"if": "...", "then": "O2", "why": "..."}],
 "lesson": "...", "limits": "..."}
"considerations" gives, for each existing consideration you touch, any of weight, favors, rules_out and why (a rewritten "why" for every consideration whose weight or favors changed). "new_consideration" is null or {"facts": [...], "equity": "...", "favors": [...], "weight": "...", "why": "..."}.
