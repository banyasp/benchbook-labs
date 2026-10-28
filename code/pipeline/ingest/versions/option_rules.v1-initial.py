"""Code validators for extract_fq.v2 (design v2.4.1 5.1; brief W4; risks R6, R33, R40, R58).

Every function returns a list of error strings (empty = ok) that go straight back to the model on retry.

  option_errors(options)      no justification; complete one-sentence courses of action; matched form and length
  opposite_errors(fq)         >= 2 `act` options with opposite dispositions, or a stated reason (tag `no-opposite`)
  name_errors(texts, source)  no personal names (titles + surname, given-name + surname, initials, names harvested
                              from the source's own "Title Surname" mentions); offices/organizations allowlisted
  narration_errors(texts)     no "The source emphasizes..." style narration (R40)
"""
from __future__ import annotations

import re

# ------------------------------------------------------------------ justification
JUSTIFY_RE = re.compile(
    r"\b(because|since|in order to|so as to|to ensure|so that|given that|given the|due to|owing to|in light of|"
    r"in view of|considering that|on the grounds|on the basis that|as a result of|thereby|which (?:shows|ensures|demonstrates|means)|"
    r"as it (?:is|was|would)|as he|as she|as they|in recognition of|reflecting)\b", re.I)


def justification_hits(text: str) -> list[str]:
    return sorted({m.group(1).lower() for m in JUSTIFY_RE.finditer(text or "")})


# ------------------------------------------------------------------ matched form
_DET = {"the", "a", "an", "this", "that", "these", "those", "his", "her", "their", "its"}


def _form(do: str) -> str:
    """Coarse grammatical shape: 'subject' (starts with a determiner/noun phrase) or 'verb' (starts with a verb-like word)."""
    w = (do.strip().split() or [""])[0].lower().strip(",.;:")
    if w in _DET or w.endswith("'s"):
        return "subject"
    return "verb"


def option_errors(options: dict) -> list[str]:
    errs = []
    forms = {}
    for k, v in options.items():
        do = (v.get("do") or "").strip()
        if not do:
            continue
        hits = justification_hits(do)
        if hits:
            errs.append(f"{k}: option text contains justification ({', '.join(hits)}); state only what is done, by whom, to what end; "
                        "reasons do not belong in options")
        n = len(do.split())
        if n < 6:
            errs.append(f"{k}: option is a fragment ({n} words); write a complete course of action (who does what, to what end)")
        if re.search(r"[.!?]\s+[A-Z]", do):
            errs.append(f"{k}: option has more than one sentence; use exactly one sentence")
        if do.endswith("?"):
            errs.append(f"{k}: option must be a statement of an action, not a question")
        if do[:1].islower():
            errs.append(f"{k}: option starts lower-case (fragment); write a complete sentence")
        forms[k] = _form(do)
    if len(set(forms.values())) > 1:
        errs.append(f"options are not in matched grammatical form ({forms}); start every option with the same kind of "
                    "phrase (all 'The <office> <verb>s ...' or all imperative-style verbs)")
    return errs


# ------------------------------------------------------------------ opposite disposition (R58)
OPPOSITES = [
    {"grant", "restore", "approve", "permit", "allow", "authorize", "authorise", "disclose", "release", "reinstate", "accept",
     "continue", "affirm", "uphold", "engage", "proceed", "waive", "clear", "admit", "fund", "retain", "confirm", "sustain",
     "reveal", "share", "publish", "attack", "strike"},
    {"deny", "revoke", "reject", "prohibit", "forbid", "refuse", "decline", "withhold", "suspend", "terminate", "dismiss",
     "overturn", "reverse", "disapprove", "disallow", "cancel", "withdraw", "discharge", "classify", "conceal", "abort",
     "cease", "stop", "hold", "bar", "remove", "withdrawal", "restrict"},
]


def _side(word: str) -> int | None:
    w = re.sub(r"(s|ed|ing|d)$", "", (word or "").strip().lower())
    for i, side in enumerate(OPPOSITES):
        for cand in side:
            if w == cand or w == re.sub(r"(s|ed|ing|d)$", "", cand) or (word or "").strip().lower() == cand:
                return i
    return None


def opposite_errors(fq: dict) -> list[str]:
    """>= 2 `act` options with different, opposite dispositions; or `no_opposite_reason` (then the scenario is tagged)."""
    opts = fq.get("options") or {}
    reason = (fq.get("no_opposite_reason") or "").strip()
    acts = {k: (v.get("disposition") or "").strip().lower() for k, v in opts.items() if v.get("move") == "act"}
    for k, v in opts.items():
        if not (v.get("disposition") or "").strip():
            return [f"{k}: give `disposition`, the one-word verb of the option (grant, deny, disclose, withhold, ...)"]
    pair = fq.get("opposite_pair") or []
    if len(acts) >= 2:
        sides = {k: _side(d) for k, d in acts.items()}
        if {0, 1} <= set(sides.values()):                 # known antonym sides both present
            return []
        declared = len(pair) == 2 and all(p in acts for p in pair) and acts[pair[0]] != acts[pair[1]]
        if declared and not any(sides[p] is not None and sides[p] == sides[pair[1 - i]] for i, p in enumerate(pair)):
            return []                                     # unfamiliar words, but a declared pair with differing dispositions
    if reason:
        if len(reason.split()) < 6:
            return ["no_opposite_reason is too short to be a real explanation"]
        return []
    if len(acts) < 2:
        return ["the option set needs at least TWO `act` options with opposite dispositions (grant vs deny; disclose vs withhold) "
                f"(R58); you have act options {sorted(acts)}. Add the opposite disposition as an `act` option, or, if the decision "
                "truly has no opposite act, explain in `no_opposite_reason`"]
    return [f"the `act` options {acts} are not opposite dispositions (e.g. grant vs deny, disclose vs withhold); make one the "
            "opposite of the other, or explain in `no_opposite_reason`"]


def no_opposite(fq: dict) -> bool:
    return bool((fq.get("no_opposite_reason") or "").strip()) and not fq.get("opposite_pair")


# ------------------------------------------------------------------ personal names
TITLES = (r"Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Judge|Justice|Sen|Senator|Rep|Representative|Gov|Governor|Mayor|Gen|General|Col|Colonel|Maj|Major|"
          r"Capt|Captain|Lt|Lieutenant|Cmdr|Commander|Sgt|Sergeant|Adm|Admiral|Cpl|Pvt|Hon|Sir|President|Secretary|Director|"
          r"Commissioner|Officer|Agent|Inspector|Chairman|Chairwoman|Minister|Ambassador|Attorney|Counsel|Supervisor|Manager|Mister")
# title + Capitalized surname, where the surname is not itself an office/organization word
TITLE_NAME_RE = re.compile(rf"\b(?:{TITLES})\.?\s+(?:[A-Z]\.\s*)*([A-Z][a-zA-Z'\-]+)\b")
INITIALS_RE = re.compile(r"\b[A-Z]\.\s?(?:[A-Z]\.\s?)*[A-Z][a-z]{2,}\b")
# words that follow a title but are offices, organizations or common sentence words, not surnames
OFFICE_WORDS = {w.lower() for w in """
Advocate Administrative Individual Judge Justice Department Office Officer Agency Board Court Committee Commission Council Counsel
Security Energy Defense State Government Federal General Attorney Inspector Director Secretary Minister Chairman Manager Supervisor
Ethics Hearing Hearings Personnel Appeals Review Panel Staff Unit Command Force Army Navy Air Marine Corps Service Services Bureau
Division Branch Section Act Code Regulation Guideline Order Policy The A An This That Of For In On At To By And Or Not No If When
Employee Employees Official Officials Agent Agents Representative Senator Governor Mayor President Prime Ambassador Commander
Chief Deputy Assistant Associate Senior Junior Acting Special Under Vice Executive Administrator Examiner Reviewer Adjudicator
Authority Authorities Contractor Applicant Respondent Petitioner Witness Witnesses Clearance Access Cleared Classified Public
Ministry Parliament Congress Senate House Bundestag Nation Nations National United Kingdom Canadian German Afghan Iraqi American
""".split()}
ORG_WORDS = {w.lower() for w in """
Department Office Agency Board Court Committee Commission Council Act Code Regulation Guideline Bureau Service Army Navy Air Force
Corps Command Ministry Federal United States National Security Energy Defense Government Hearings Appeals Personnel Ethics
Administrative Judge Individual January February March April May June July August September October November December
Monday Tuesday Wednesday Thursday Friday Saturday Sunday Section Part Title Chapter Subpart Executive Order Rule Rules Manual
Directive Instruction Policy Standard Standards Supreme Circuit District Inspector General Counsel Attorney Secretary
Special Operations Joint Staff Chiefs Intelligence Central Agency Treasury Justice Homeland State House Senate Congress
""".split()}

# a modest list of common given names; "<Given> <Capitalized>" mid-sentence is flagged
FIRST_NAMES = {n.lower() for n in """
James John Robert Michael William David Richard Joseph Thomas Charles Christopher Daniel Matthew Anthony Mark Donald Steven Paul
Andrew Joshua Kenneth Kevin Brian George Timothy Ronald Edward Jason Jeffrey Ryan Jacob Gary Nicholas Eric Jonathan Stephen Larry
Justin Scott Brandon Benjamin Samuel Gregory Alexander Frank Patrick Raymond Jack Dennis Jerry Tyler Aaron Jose Adam Nathan Henry
Douglas Zachary Peter Kyle Walter Ethan Jeremy Harold Keith Christian Roger Noah Gerald Carl Terry Sean Austin Arthur Lawrence
Jesse Dylan Bryan Joe Jordan Billy Bruce Albert Willie Gabriel Logan Alan Juan Wayne Roy Ralph Randy Eugene Vincent Russell Elijah
Louis Bobby Philip Johnny Mary Patricia Jennifer Linda Elizabeth Barbara Susan Jessica Sarah Karen Lisa Nancy Betty Margaret Sandra
Ashley Kimberly Emily Donna Michelle Carol Amanda Dorothy Melissa Deborah Stephanie Rebecca Sharon Laura Cynthia Kathleen Amy Angela
Shirley Anna Brenda Pamela Emma Nicole Helen Samantha Katherine Christine Debra Rachel Carolyn Janet Catherine Maria Heather Diane
Ruth Julie Olivia Joyce Virginia Victoria Kelly Lauren Christina Joan Evelyn Judith Megan Andrea Cheryl Hannah Jacqueline Martha
Gloria Teresa Ann Sara Madison Frances Kathryn Janice Jean Abigail Alice Julia Judy Sophia Grace Denise Amber Doris Marilyn Danielle
Beverly Isabella Theresa Diana Natalie Brittany Charlotte Marie Kayla Alexis Lori Klaus Georg Hans Wolfgang Mohammed Ahmed Ali
Omar Hassan Abdul Ivan Sergei Dmitri Vladimir Oleg Yuri Wei Li Chen Raj Priya
""".split()}
CAP_SEQ_RE = re.compile(r"\b([A-Z][a-z]{1,}(?:[-'][A-Z]?[a-z]+)?)((?:\s+[A-Z][a-z]{1,}(?:[-'][A-Z]?[a-z]+)?){1,2})\b")


def source_surnames(source_text: str) -> set[str]:
    """Surnames the source itself introduces with a title ('Col. Klein', 'Judge Smith')."""
    out = set()
    for m in TITLE_NAME_RE.finditer(source_text or ""):
        w = m.group(1)
        if w.lower() not in OFFICE_WORDS and w.lower() not in ORG_WORDS and len(w) > 2:
            out.add(w)
    return out


def name_errors(texts: dict[str, str], source_text: str = "", allow: set[str] | None = None) -> list[str]:
    """texts: {field path: string}. Flags personal names; people must be named by office."""
    allow = {a.lower() for a in (allow or set())}
    harvest = source_surnames(source_text)
    errs = []
    for path, t in texts.items():
        if not t:
            continue
        found = set()
        for m in TITLE_NAME_RE.finditer(t):
            w = m.group(1)
            if w.lower() not in OFFICE_WORDS and w.lower() not in ORG_WORDS and w.lower() not in allow:
                found.add(m.group(0).strip())
        for m in INITIALS_RE.finditer(t):
            found.add(m.group(0).strip())
        for m in CAP_SEQ_RE.finditer(t):
            first, rest = m.group(1), m.group(2).split()
            if first.lower() in FIRST_NAMES and first.lower() not in allow and rest[0].lower() not in ORG_WORDS:
                # a leading sentence-start given-name-like word (e.g. "Mark", "Will") still needs a capitalized follower; accept
                found.add(m.group(0).strip())
        for s in harvest:
            if re.search(rf"\b{re.escape(s)}\b", t) and s.lower() not in allow:
                found.add(s)
        for f in sorted(found):
            errs.append(f"{path}: personal name `{f}`; name people only by office or role (the Administrative Judge, the Individual, the Commander)")
    return errs


# ------------------------------------------------------------------ source narration (R40)
_SUBJ = r"(?:the |this |that )?(?:source|sources|document|decision|opinion|report|ruling|text|passage|record|judge's decision|authors?|writer|inquiry|board's report|finding|findings|article|case|decision-maker's decision)"
_VERB = (r"(?:emphasi[sz]es?|emphasi[sz]ed|notes?|noted|states?|stated|stresses|stressed|observes?|observed|explains?|explained|highlights?|highlighted|"
         r"makes? clear|made clear|indicates?|indicated|says|said|points? out|pointed out|reasons?|concludes?|concluded|finds?|found|"
         r"recogni[sz]es?|acknowledges?|underscores?|underlines?|suggests?|reports?|reported|describes?|described|treats?|considers?|illustrates?|shows?|teaches)")
NARRATION_RE = re.compile(rf"\b{_SUBJ}\s+(?:also |further |again |additionally |repeatedly |expressly |explicitly )?{_VERB}\b|"
                          r"\baccording to (?:the |this )(?:source|document|decision|opinion|report|ruling|text|passage|record)\b|"
                          r"\b(?:as|per) (?:the |this )(?:source|document|decision|opinion|report) (?:states|notes|says)\b|"
                          r"\bin (?:the|this) (?:source|document|opinion|passage)\b", re.I)


def narration_hits(text: str) -> list[str]:
    return sorted({m.group(0).strip().lower() for m in NARRATION_RE.finditer(text or "")})


def narration_errors(texts: dict[str, str]) -> list[str]:
    errs = []
    for path, t in texts.items():
        h = narration_hits(t)
        if h:
            errs.append(f"{path}: source-narration phrase ({'; '.join(h)}); state the content itself, never talk about the source")
    return errs


def strip_narration(text: str) -> str:
    """Last-resort cleanup for rendered prose: drop a leading 'The source emphasizes that' clause and re-capitalize.
    (Extraction rejects instead; this is for code that must clean already-stored prose.)"""
    m = re.match(rf"\s*{_SUBJ}\s+{_VERB}\s+(?:that\s+)?", text, re.I)
    if not m:
        return text
    rest = text[m.end():]
    return rest[:1].upper() + rest[1:]
