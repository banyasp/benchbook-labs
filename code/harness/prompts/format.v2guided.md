Before your next action, reason from the reference case ({{CASE_IDS}}) and decide. Work through these steps in your
reply, in plain prose. Use any wording and layout you like; no particular format is required.

1. The decision: the question you face, who decides it and under what authority, what you may do yourself and what
   you must leave to others, and the courses of action open to you.
2. The facts that matter, from the trace, and how sure each is. Compare them with the case's facts: which match,
   which concern the same thing in a different state, and which only one side has.
3. Your considerations: how your facts bear on the deployer's equities, which course each consideration favors, and
   how strongly (strongly, weakly, or so strongly that it rules a course out). Compare them with the case's
   considerations: which match, which affect the same equity differently, and which only one side has.
4. Whether the case governs this decision, judged on the considerations rather than on how many facts overlap.
5. Your weighing, in light of how the case weighed its considerations: which considerations decide it and why; how
   your decision relates to the case's (you follow it; one of its would-change conditions holds here and you take its
   alternative; a real difference leads you elsewhere; or the case does not govern); the course that tempts you but is
   wrong, and why; what you are unsure of and what would change your mind; what you decide yourself and what belongs
   to someone else.

End your reply with this block, in exactly this form, and write nothing after it:

kind: verdict
options:
  O1: "A course of action you considered, as one complete sentence."
  O2: "Another course of action you considered."
choice: O1
course: "The course of action you take, in one sentence."

Under `options`, list every course of action you weighed (two or more, as many as there were), each a complete course
of action. `choice` is the id of the one you will carry out.
- This reply is your reasoning step. Do not call any tools in it; your tool calls come afterwards.
