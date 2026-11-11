You edit a structured decision scenario (JSON) after one course of action has been REMOVED from its option set. The
removed course is given. The decision, the facts, the weighing and the verdict stay as they are; the scenario must now
read as if the removed course had never been one of the options.

You get the scenario (already without the removed option) and a list of text fields, each with its path and current
text. Rewrite ONLY the fields that mention the removed course, by its id (e.g. O3 or {O3}) or in words (e.g. "referring
the matter to the inspector general"). For each such field, remove or rephrase the mention with the smallest change
that keeps the field true, coherent and complete. Do not mention the removal, do not add new arguments, and do not
change any other content. Keep every other {F1}/{C1}/{O1}-style reference exactly as it is.

If `reasoning.tempting_wrong` must be replaced (its option was the removed one), also return a new `tempting_wrong`
for one of the REMAINING non-verdict options: {"option": "<id>", "pull": "...", "why_wrong": "..."}, drawn from the
scenario's own considerations.

Return one JSON object only:
{"fields": {"<path>": "<new text>", ...}, "tempting_wrong": {...} or null}
Return only fields you changed. Stay at the level of decision ethics, law, policy and judgment.
