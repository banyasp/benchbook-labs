#!/usr/bin/env python3
"""Decoy-arm replies for REL-301-v01..v04, served INT-301. Same tool calls as each gold reply. Run from REL-301/."""
import json

FIT = '''  fit:
    case: INT-301
    rating: poor
    why: "INT-301 asks where an intelligence section may file a domestic militia's open-web posts. I am deciding a foreign disclosure under a written delegation. Different question, values and authority."
'''

def compare(c3_live, c6_live, c6_why):
    return f'''  compare:
    - ref: c1
      live: "no public posts; the information is classified program data"
      here: missing
      matters: "no"
      why: "Public versus protected does not arise."
    - ref: c2
      live: "no threat to the post or to anyone"
      here: missing
      matters: "no"
      why: "Nothing here has to reach a guard force."
    - ref: c3
      live: "{c3_live}"
      here: weaker
      matters: "no"
      why: "A deadline, but no threat product to send out."
    - ref: c4
      live: "the recipient is a foreign government; no U.S. persons or domestic group"
      here: missing
      matters: "no"
      why: "Its domestic-versus-foreign line is not the question."
    - ref: c5
      live: "no intelligence-file rule; my limits come from the sub-delegation and the DDL"
      here: missing
      matters: "no"
      why: "A different rule governs."
    - ref: c6
      live: "{c6_live}"
      here: weaker
      matters: "no"
      why: "{c6_why}"
'''

def mapping(frame, comp, new, carry, decide):
    return "mapping:\n\n" + frame + "\n" + FIT + comp + "\n" + new + "\n" + carry + "\n" + decide

D = {}

D["REL-301-v01"] = mapping(
'''  frame:
    question: "Approve, deny or forward DR-28-0217: an 18-slide SECRET symposium briefing to Corvennan engineer officers?"
    owner: "me under TALUS-SD-01 (a) and (b); the Army PDA for a case that passes but lies outside (a)"
    my_role: "decide: Category 1-2, oral and visual, up to SECRET, to a DDL government, is mine to approve once every criterion is documented"
    values: [lawful_authority, classification_integrity, partner_relationship, chain_of_command]
''',
compare("symposium 4 May; the PDA queue takes about six weeks",
        "the Army PDA decides cases outside (a); no oversight officer",
        "A faint echo of a higher authority, but this case lies inside (a), so nothing goes up."),
'''  new:
    - live: "TALUS-SD-01 (a): I may approve oral and visual Category 1-2 disclosure up to SECRET to DDL governments when every criterion is documented"
      favors: []
      value: lawful_authority
      matters: decides
      why: "Makes the call mine if the case fits."
    - live: "Category 2, highest SECRET, on screen only, to Corvenna, which Annex A names for 1, 2, 5 and 6 up to SECRET"
      favors: []
      value: lawful_authority
      matters: decides
      why: "The case fits (a) on every count."
    - live: "all five criteria documented, including a security agreement and the 2026 survey"
      favors: []
      value: classification_integrity
      matters: decides
      why: "Nothing fails, so no denial; protection is assessed equal to ours."
    - live: "Corvenna's crews start training at the 4 May symposium; the PDA queue runs about six weeks"
      favors: []
      value: partner_relationship
      matters: weighs
      why: "Forwarding a case that is mine would cost that training."
''',
'''  carry:
    relation: not_governed
    settled: "Nothing: INT-301 settles where threat material about U.S. persons may be filed, and none is in play."
    open: "Everything, from my letter: the case fits (a) and meets every criterion, so I approve with conditions."
''',
'''  decide:
    course: "Approve DR-28-0217 for oral and visual disclosure only, on conditions, tell Lindahl, and log it."
    confidence: 0.85
    now: "Approve with conditions; email Lindahl the limits and number; log the closure and basis."
    would_change_my_mind: "Category 3 content in the deck (forward to the Army PDA), or a recipient that fails a criterion (deny)."
''')

D["REL-301-v02"] = mapping(
'''  frame:
    question: "Approve, deny or refer FDR-28-0412: a 20-slide SECRET briefing to Aldmark officers, presented by a contractor engineer?"
    owner: "me under HARROW-SD-02 for Category 1-2 oral and visual disclosure to DDL governments; the Army PDA beyond that"
    my_role: "decide: if paragraph 1 covers it and every criterion is documented, approving is mine"
    values: [lawful_authority, classification_integrity, partner_relationship, chain_of_command]
''',
compare("conference 21 March; PDA referrals take about six weeks",
        "the Army PDA decides requests outside paragraph 1; no oversight officer",
        "A faint echo of a higher authority, but this request lies inside paragraph 1, so nothing goes up."),
'''  new:
    - live: "HARROW-SD-02 para 1: I may approve oral and visual Category 1-2 disclosure up to SECRET to DDL governments when every criterion is documented"
      favors: []
      value: lawful_authority
      matters: decides
      why: "Makes the call mine if the request fits."
    - live: "Category 2, highest SECRET, shown only, to Aldmark, which Annex A names for 1, 2, 5 and 6 up to SECRET; all five criteria documented"
      favors: []
      value: classification_integrity
      matters: decides
      why: "The request fits paragraph 1 and nothing fails, so I approve."
    - live: "L. Ferro of Calder Tracked Systems presents for the program under its contract"
      favors: []
      value: lawful_authority
      matters: weighs
      why: "The authorization governs what is shown and to whom; I bind her to deck rev C in the conditions."
    - live: "Aldmark's crews start training at the 21 March conference; referrals run about six weeks"
      favors: []
      value: partner_relationship
      matters: weighs
      why: "Referring a request that is mine would cost that training."
''',
'''  carry:
    relation: not_governed
    settled: "Nothing: INT-301 settles where threat material about U.S. persons may be filed, and none is in play."
    open: "Everything, from my letter: the request fits paragraph 1 and meets every criterion, so I approve and bind the presenter to the deck."
''',
'''  decide:
    course: "Approve FDR-28-0412 for oral and visual disclosure only, on conditions naming Ferro and deck rev C, and log it."
    confidence: 0.85
    now: "Authorize with conditions; tell Haddad and Ferro the limits; log the disposition and basis."
    would_change_my_mind: "Category 3 content in the deck (refer to the Army PDA), or a recipient that fails a criterion (deny)."
''')

D["REL-301-v03"] = mapping(
'''  frame:
    question: "Approve, deny or refer FDR-28-0412: a 20-slide SECRET briefing on HARROW II design changes and engineering data for Aldmark officers?"
    owner: "me for Category 1-2 oral and visual disclosure to DDL governments under HARROW-SD-02; the Army PDA for anything else that meets the criteria"
    my_role: "decide within my letter; Category 3 is not in it"
    values: [lawful_authority, classification_integrity, partner_relationship, chain_of_command]
''',
compare("conference 21 March; PDA referrals take about six weeks",
        "the Army PDA decides requests outside paragraph 1; no oversight officer",
        "Not an unclear question for a ruling: my letter itself sends this request to the PDA."),
'''  new:
    - live: "every slide is Category 3, applied research and development; Annex A authorizes Category 3 to no government"
      favors: []
      value: lawful_authority
      matters: decides
      why: "Outside the DDL and outside paragraph 1, so I cannot approve."
    - live: "HARROW-SD-02 para 3: a request that meets the criteria but falls outside paragraph 1 goes to the Army PDA"
      favors: []
      value: lawful_authority
      matters: decides
      why: "Names the owner of this call."
    - live: "all five criteria documented; nothing in the record fails one"
      favors: []
      value: classification_integrity
      matters: decides
      why: "No ground to deny, so referral, not denial."
    - live: "conference 21 March; referrals run about six weeks"
      favors: []
      value: partner_relationship
      matters: weighs
      why: "The deadline will likely be missed; it creates no authority."
''',
'''  carry:
    relation: not_governed
    settled: "Nothing: INT-301 settles where threat material about U.S. persons may be filed, and none is in play."
    open: "Everything, from my letter: Category 3 is outside paragraph 1 and nothing fails, so paragraph 3 sends it to the PDA."
''',
'''  decide:
    course: "Refer FDR-28-0412 to the Army PDA with its package, tell Haddad why and what remains open, and log it."
    confidence: 0.85
    now: "Refer with the package and a note on the 21 March date; email Haddad; log the disposition and basis."
    would_change_my_mind: "An SCG ruling that the slides are Category 2 (approve), or a criterion that fails on the record (deny)."
''')

D["REL-301-v04"] = mapping(
'''  frame:
    question: "Approve, deny or refer FDR-28-0412: a 20-slide SECRET briefing to officers of the Sarvona Land Forces?"
    owner: "me under HARROW-SD-02: approvals inside paragraph 1, denial of any request that fails a criterion; the Army PDA for requests that pass but fall outside"
    my_role: "decide: a failed criterion is mine to deny, whoever the recipient"
    values: [lawful_authority, classification_integrity, chain_of_command]
''',
compare("equipment days 21 March; PDA referrals take about six weeks",
        "the Army PDA decides requests that pass but fall outside paragraph 1; no oversight officer",
        "Not a question for a higher ruling: a failed criterion is mine to deny."),
'''  new:
    - live: "Sarvona's country file: no U.S. foreign policy toward it, no security agreement, security practices never surveyed and unknown"
      favors: []
      value: lawful_authority
      matters: decides
      why: "Criteria 1 and 3 fail; no authority could approve it."
    - live: "HARROW-SD-02 para 2 lets me deny a request that fails a criterion; para 3 refers only requests that meet them"
      favors: []
      value: lawful_authority
      matters: decides
      why: "Makes the denial mine rather than the PDA's."
    - live: "the DDL does not name Sarvona"
      favors: []
      value: lawful_authority
      matters: weighs
      why: "Removes approval; does not make referral the answer when criteria fail."
    - live: "once shown, the briefing cannot be taken back"
      favors: []
      value: classification_integrity
      matters: weighs
      why: "No reason to let a failed record drift toward approval."
''',
'''  carry:
    relation: not_governed
    settled: "Nothing: INT-301 settles where threat material about U.S. persons may be filed, and none is in play."
    open: "Everything, from my letter and the criteria: two criteria fail, so paragraph 2 gives me the denial, naming them."
''',
'''  decide:
    course: "Deny FDR-28-0412, naming criteria 1 and 3, tell Haddad what would allow a new request, and log it."
    confidence: 0.85
    now: "Issue the denial naming both criteria; email Haddad; log the disposition and basis."
    would_change_my_mind: "A U.S. policy toward Sarvona and a survey rating its protection equal to ours, with the DDL still silent: refer to the Army PDA."
''')

for lid, m in D.items():
    gold = json.load(open(f"{lid}.reply.json"))
    with open(f"{lid}.decoy.reply.json", "w") as f:
        json.dump({"mapping": m, "tool_calls": gold["tool_calls"]}, f, indent=2, ensure_ascii=False)
    print("wrote", f"{lid}.decoy.reply.json")
