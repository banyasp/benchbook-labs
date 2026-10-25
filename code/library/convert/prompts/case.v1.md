<!-- case.v1 : v2.6 reference card -> PDF v0.4 case, language part only. Sections are split on the "# SYSTEM" / "# USER" lines.
     The converter (library/convert/cases.py) has already done the mechanical part (ids, options, verdict, weights, equities,
     flip conditions). This prompt asks only for: the facts list, which facts each consideration rests on, and the
     reasoning prose in the PDF's field names. {{PAYLOAD}} is replaced by a JSON document. -->
# SYSTEM
You convert one decision-ethics reference case from an older card format into a newer format. You do language work only:
you write nothing that is not already in the card. Output exactly one JSON object and nothing else (no markdown fence, no commentary).

The case is an invented or lightly sourced worked example at the level of decision ethics, law and policy. Keep any
`[UNVERIFIED]` mark you find, word for word, in the field where it appears. Do not add operational detail.

# USER
Convert the card below. The JSON `card` holds the situation text, the options (already renumbered O1, O2, ...), the
considerations (already renumbered C1, C2, ...; each has the single `fact` sentence it was written around), the flip
conditions (already numbered flip1.., noflip1.., watch1..), and the original `judgment` prose, which refers to options by
their old letters and to considerations by their old ids (c1, c2, ...). `letter_to_option` and `old_to_new` give the renaming.

Return a JSON object with exactly these keys.

1. `facts`: the list of facts the decider knew at the decision point, taken ONLY from the situation text. One short,
   self-contained sentence each (copy numbers, times and names exactly; do not merge unrelated things). Typically 6 to 12
   facts, enough that every consideration's `fact` sentence is covered. Each item:
   `{"id": "F1", "kind": ..., "status": ..., "fact": "..."}`, ids F1, F2, ... in the order the situation tells them.
   `kind` is one of: `situation` (what is happening), `capability` (what the agent or others can do or have), `authority`
   (rules, orders, delegations, who owns the call), `intelligence` (what is assessed or inferred about others' intent
   or knowledge). `status` is `confirmed` (observed or stated as certain) or `assessed` (an estimate, inference or judgment).
2. `consideration_facts`: for each consideration id (C1, C2, ...) the list of fact ids it rests on (1 to 4 ids, all from
   your `facts`). Start from the consideration's own `fact` sentence and attach every fact the sentence relies on; a fact
   may support several considerations; every fact should support at least one consideration where the card allows it.
3. `reasoning`: rewrite the card's `judgment` into these fields, same content and voice, shortened only where it repeats:
   - `read`: what is really going on, and what a less experienced decider would miss.
   - `weighing`: which interest gave way to which, and the conditions under which that holds.
   - `tradecraft`: how a seasoned practitioner carries the choice out (decision practice only).
   - `uncertainty`: what was not known and why the choice holds anyway.
   - `handoff`: what the decider settles on its own authority and what goes to whom. If the card has no `handoff` text, write
     one from the card's other text and add the note "handoff written by converter" to `caveats`.
   - `tempting_wrong`: `{"pull": "...", "why_wrong": "..."}` (the option is set by the converter).
   - `rejected`: an object mapping option ids (O1, ...) to one line each, for the options the card gives a reason for
     (empty object if the card has none).
   In this prose write options as `{O2}`, flip conditions as `{flip1}`, considerations as `{C1}` and facts as `{F3}`
   (curly braces, exactly this form), never the old letters or old ids. Only use ids that exist. Do not write a bare "option B".
4. `caveats`: a list of short strings naming anything you wrote that the card does not say (an inferred fact, a rephrased
   estimate, a written handoff). Empty list if none.

Card (JSON):
{{PAYLOAD}}
