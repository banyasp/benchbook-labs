"""render gates (design §8.4): locate, leak scan (ids, labels, menu shape, gold, card A-parts), person names."""
from __future__ import annotations

import re

from bench.schema import Case

VERBATIM_WORDS = 8

_TOK = re.compile(r"[a-z0-9']+")
STOP = set("a an the of to and or in on at for with by from as is are was were be been it its this that these those "
           "not no if then than so we you they he she i our your their his her will would can could should may might "
           "do does did has have had into over under after before about up out per".split())


def tokens(s: str) -> list[str]:
    return _TOK.findall(s.lower())


def ngrams(s: str, n: int = VERBATIM_WORDS) -> set[tuple[str, ...]]:
    t = tokens(s)
    return {tuple(t[i:i + n]) for i in range(len(t) - n + 1)}


def longest_run(a: str, b: str) -> int:
    x, y = tokens(a), tokens(b)
    best, prev = 0, [0] * (len(y) + 1)
    for i in range(1, len(x) + 1):
        cur = [0] * (len(y) + 1)
        for j in range(1, len(y) + 1):
            if x[i - 1] == y[j - 1]:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def _strs(o) -> list[str]:
    """All strings in a nested value (for the A part of a card)."""
    if o is None or isinstance(o, bool):
        return []
    if isinstance(o, str):
        return [o]
    if isinstance(o, dict):
        return [s for v in o.values() for s in _strs(v)]
    if isinstance(o, (list, tuple)):
        return [s for v in o for s in _strs(v)]
    if hasattr(o, "model_dump"):
        return _strs(o.model_dump(by_alias=True))
    return []


def a_part_texts(case: Case) -> dict[str, str]:
    """The A part of a card: considerations (equity, why: the Phi), reasoning, verdict, flip conditions, lesson,
    limits. Facts (F) are excluded by design (restyle/self/augmented cards restate the trace's facts)."""
    parts = {
        "considerations": [(c.equity, c.why) for c in case.considerations],
        "reasoning": case.reasoning, "verdict": case.verdict, "flip_conditions": case.flip_conditions,
        "lesson": case.lesson, "limits": case.limits,
    }
    return {k: "\n".join(_strs(v)) for k, v in parts.items()}


# ------------------------------------------------------------------ ids / schema words
ID_PAT = re.compile(r"(\bLIVE-[A-Z]\d+|\bREF\d+(?:-[A-Za-z]\d+)?\b|\bDR-[A-Z0-9]+-\d+|\b[FOC]\d{1,2}\b|\bflip\d+\b|"
                    r"\b[Oo]ption\s+[A-D0-9]\b|\b(?:gold|planted|irreversible|equities|equity|consideration)\b)")


def id_leaks(messages: list[dict], skip_first: bool = False) -> list[str]:
    out = set()
    for i, m in enumerate(messages):
        c = m.get("content") or ""
        for x in [c] + [str(tc.get("arguments")) for tc in m.get("tool_calls") or []]:
            out |= {mm.group(0) for mm in ID_PAT.finditer(x)}
    return sorted(out)


# ------------------------------------------------------------------ menu shape
LIST_LINE = re.compile(r"^\s*(?:[-*•]|\(?[A-Za-z0-9]{1,2}[.)])\s+\S", re.M)
MENU_WORDS = re.compile(r"\b(options|choices|alternatives|courses of action)\s*(?::|are|include)|"
                        r"\b(?:\([a-c]\)|\b[a-c]\))\s.*\b(?:\([b-d]\)|\b[b-d]\))\s", re.I)


def _mentions(case: Case, opt_ids: list[str], text: str) -> set[str]:
    """Options whose wording is substantially present in a stretch of text (content-word overlap)."""
    t = set(tokens(text)) - STOP
    hit = set()
    for o in opt_ids:
        w = set(tokens(case.options[o].do)) - STOP
        if w and len(w & t) / len(w) >= 0.6:
            hit.add(o)
    return hit


def menu_problems(messages: list[dict], opt_spans: list[tuple[str, int, int, int]], case: Case) -> list[str]:
    """opt_spans: (local option id, message, start, end). Flags: >=3 options in one message (located or by wording),
    a bullet/number/letter list or an options-colon phrase in a message that carries >=2 options."""
    probs = []
    opt_ids = list(case.options)
    for k, m in enumerate(messages):
        c = m.get("content") or ""
        located = {o for o, mi, *_ in opt_spans if mi == k}
        # sentence windows: any 2 sentences (a window of 3) carrying 3 options is an enumeration
        sents = re.split(r"(?<=[.!?;])\s+|\n+", c)
        by_words = set()
        for i in range(len(sents)):
            by_words |= _mentions(case, opt_ids, " ".join(sents[i:i + 3])) if len(_mentions(
                case, opt_ids, " ".join(sents[i:i + 3]))) >= 3 else set()
        allm = located | by_words
        if len(allm) >= 3:
            probs.append(f"message {k} carries {len(allm)} options")
        if len(located) >= 2 and (len(LIST_LINE.findall(c)) >= 3 or MENU_WORDS.search(c)):
            probs.append(f"message {k} has {len(located)} options in list shape")
        elif MENU_WORDS.search(c) and len(_mentions(case, opt_ids, c)) >= 2:
            probs.append(f"message {k} is menu-shaped")
    return probs


# ------------------------------------------------------------------ person names
TITLES = (r"(?:Mr|Mrs|Ms|Mx|Dr|Prof|Capt|Cpt|Col|Lt|Maj|Sgt|Cpl|Gen|Cmdr|Adm|Det|Sen|Pvt|Rev|Doctor|Professor|"
          r"Captain|Colonel|Lieutenant|Sergeant|Detective|Judge|Senator|Admiral)")
TITLE_NAME = re.compile(rf"\b{TITLES}\.?\s+([A-Z][a-z]{{2,}})")
ROLE_WORDS = {"advocate", "general", "operations", "officer", "commander", "staff", "supervisor", "desk", "office",
              "department", "division", "team", "section", "command", "center", "centre", "unit", "review", "board"}
INITIAL_NAME = re.compile(r"\b[A-Z]\.\s?[A-Z][a-z]{2,}\b")
FIRST_NAMES = set("""james john robert michael william david richard joseph thomas charles christopher daniel matthew anthony
donald steven paul andrew joshua kenneth kevin brian george timothy ronald edward jason jeffrey ryan jacob gary nicholas eric
jonathan stephen larry justin scott brandon benjamin samuel gregory alexander patrick raymond jack dennis jerry tyler aaron
jose adam nathan henry douglas zachary peter kyle walter ethan jeremy harold keith christian roger noah gerald carl terry
sean austin arthur lawrence jesse dylan bryan joe jordan billy bruce albert willie gabriel logan alan juan wayne roy ralph
randy eugene vincent russell elijah louis bobby philip johnny
mary patricia jennifer linda elizabeth barbara susan jessica sarah karen lisa nancy betty margaret sandra ashley kimberly
emily donna michelle carol amanda melissa deborah stephanie rebecca sharon laura cynthia kathleen amy shirley angela helen
anna brenda pamela nicole samantha katherine emma ruth christine catherine debra rachel carolyn janet virginia maria heather
diane julie joyce victoria kelly christina lauren joan evelyn judith megan cheryl andrea hannah jacqueline martha gloria
teresa ann sara madison frances kathryn janice jean abigail alice julia judy sophia denise amber danielle marilyn beverly
natalie theresa diana brittany doris kayla alexis lori priya fatima ahmed mohammed muhammad ali omar hassan ibrahim yusuf
ivan dmitri sergei olga natasha vladimir wei chen li ming hiroshi yuki carlos miguel luis pedro diego sofia isabella
""".split())
FIRST_SURNAME = re.compile(r"\b([A-Z][a-z]+)\s+(?:[A-Z]\.\s+)?([A-Z][a-z]{2,}(?:-[A-Z][a-z]+)?)\b")
HANDLE_SPLIT = re.compile(r"[\s_.\-@]+")


def person_names(messages: list[dict]) -> list[str]:
    found = set()
    for m in messages:
        c = m.get("content") or ""
        found |= {x.group(0) for x in TITLE_NAME.finditer(c) if x.group(1).lower() not in ROLE_WORDS}
        found |= {x.group(0) for x in INITIAL_NAME.finditer(c)}
        for x in FIRST_SURNAME.finditer(c):
            if x.group(1).lower() in FIRST_NAMES:
                found.add(x.group(0))
        for w in re.findall(r"\b[A-Z][a-z]+\b", c):           # a bare given name, e.g. a sign-off or a greeting
            if w.lower() in FIRST_NAMES:
                found.add(w)
        for part in HANDLE_SPLIT.split(str(m.get("name") or "")):
            if part.lower() in FIRST_NAMES:
                found.add(f"name:{m.get('name')}")
    return sorted(found)


# ------------------------------------------------------------------ card A-part leak
def card_leaks(messages: list[dict], cards: list[Case]) -> list[dict]:
    body = "\n".join(str(m.get("content") or "") for m in messages) + "\n" + "\n".join(
        str(tc.get("arguments")) for m in messages for tc in m.get("tool_calls") or [])
    grams = ngrams(body)
    out = []
    for c in cards:
        for part, text in a_part_texts(c).items():
            hit = grams & ngrams(text)
            if hit:
                out.append({"card": c.id, "part": part, "run": " ".join(sorted(hit)[0])})
    return out


def option_text_leaks(messages: list[dict], case: Case) -> list[dict]:
    """Option labels (the scenario's wording of each course of action) copied into the trace, incl. the gold's."""
    body = "\n".join(str(m.get("content") or "") for m in messages)
    out = []
    for oid, o in case.options.items():
        n = longest_run(o.do, body)
        if n >= VERBATIM_WORDS:
            out.append({"option": oid, "run_words": n, "gold": oid == case.verdict.choice})
    return out
