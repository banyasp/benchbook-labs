"""Technique checker (W8b, design §4.2): a conservative screen over extracted scenario text for weapon-employment /
targeting-technique content that must be stripped. The held-out natsec domain trains the *decision* (who decided, options,
equities, authority, legal standard, reasoning, outcome), never how a weapon is employed or a target found.

    check(text)          -> list[Flag]            Flag(category, severity, match, start, end)
    scan_scenario(obj)   -> list[(path, Flag)]    walks every string in a dict/list (scenario JSON)
    is_clean(text)       -> bool                  no "strip" flags
    python -m pipeline.ingest.technique_check <file.json|file.txt>

Severity: "strip" = remove or generalise the sentence (munition/fuze, CDE mechanics, sensor procedure, geometry, procedure
steps); "review" = platform/system designations a human or the extractor should confirm are needed for the decision
(e.g. "F-15 pilots" in a fratricide). Decision-level vocabulary (strike, ROE, civilian casualties, proportionality,
authorization, show of force, positive identification, imminent threat ...) is never flagged. Over-flagging is the
intended failure direction; the cost is a stripped sentence, not a leak.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass

_I = re.IGNORECASE


@dataclass(frozen=True)
class Flag:
    category: str
    severity: str  # strip | review
    match: str
    start: int
    end: int


def _r(p: str, flags=_I) -> re.Pattern:
    return re.compile(p, flags)


RULES: list[tuple[str, str, re.Pattern]] = [
    # --- munition, fuze, warhead -----------------------------------------------------------------------------
    ("munition", "strip", _r(r"\b(?:GBU|AGM|AIM|BLU|CBU|MK|Mk|MOAB|JDAM|SDB|PGM)[-\s]?\d{1,3}[A-Z]?(?:/[A-Z])?\b", 0)),
    ("munition", "strip", _r(r"\b(?:JDAM|Hellfire|Paveway|Maverick|Brimstone|Tomahawk|Harpoon|Exocet|Sidewinder|Sparrow|AMRAAM|"
                             r"Javelin|Griffin|Spike|Excalibur|HIMARS|GMLRS|bunker[- ]?buster|thermobaric|"
                             r"daisy[- ]?cutter|Rockeye|Mavericks?)\b")),
    ("munition", "strip", _r(r"\b(?:laser|GPS|INS|radar|TV|electro-?optically|infrared)[- ]guided\s+(?:bomb|missile|munition|rocket|weapon)s?\b")),
    ("munition", "strip", _r(r"\b(?:cluster|fragmentation|penetrator|general[- ]purpose|incendiary|white phosphorus|depleted uranium)\s+"
                             r"(?:bomb|munition|submunition|warhead|round|projectile)s?\b")),
    ("munition", "strip", _r(r"\b\d[\d,]*[- ]?(?:lb|lbs|pound|pounds|kg|kilogram|kilograms)\b[-\s]*(?:class\s+)?(?:bomb|warhead|munition|"
                             r"weapon|GBU|JDAM|Mk|round)?")),
    ("munition", "strip", _r(r"\b(?:\d{2}|\d{3})\s?(?:mm|millimet(?:er|re))\s+(?:cannon|gun|round|shell|howitzer|autocannon)s?\b")),
    ("fuze", "strip", _r(r"\b(?:fuz(?:e|ing|ed)|fuse[sd]?\s+(?:setting|delay|option))s?\b.*?(?:delay|instantaneous|proximity|airburst|"
                         r"point[- ]detonat|setting)|\b(?:delay(?:ed)?|instantaneous|proximity|impact|point[- ]detonating)\s+fuz(?:e|es|ing)\b")),
    ("fuze", "strip", _r(r"\b(?:air[- ]?burst|point[- ]detonat\w*|warhead\s+(?:type|size|yield)|net explosive (?:weight|quantity)|"
                         r"explosive (?:yield|weight|charge size)|fuz(?:e|ing) (?:selection|setting|option))")),
    ("munition", "strip", _r(r"\b(?:weapon|munition|ordnance|warhead)\s+(?:selection|choice|type|load[- ]?out|mix)\b|\bweaponeering\b")),
    # --- collateral damage estimation mechanics --------------------------------------------------------------
    ("cde", "strip", _r(r"\bcollateral[- ]damage[- ]estimat\w*|\bCDE\b|\bCDM\b|\bCDEM\b|\bCDE\s+level|\bCDE\s+tier|\btier\s+[1-5]\s+CDE|"
                        r"\bnon[- ]?combatant casualty cut[- ]?off(?: value)?|\bNCV\b|\bFSCM\b|\bcollateral damage (?:methodolog|model|assessment tool)\w*|"
                        r"\bblast (?:radius|effects? radius)|\bhazard (?:distance|radius|area)|\bdanger[- ]close|\bminimum safe distance|"
                        r"\bsafe[- ]separation|\bfragmentation (?:pattern|radius|footprint)|\bprobability of (?:kill|damage|incidental)\b|\bCEP\b|"
                        r"\bcircular error probable|\bPk\b|\bPcd\b|\bcasualty (?:estimat\w+|prediction) (?:method|model|tool|table)")),
    # --- sensor / ISR procedure ------------------------------------------------------------------------------
    ("isr", "strip", _r(r"\b(?:FLIR|FMV|full[- ]motion video|SIGINT|MASINT|GEOINT|IMINT|HUMINT collection|laser (?:designat\w+|spot|illuminat\w+)|"
                        r"targeting pod|sniper pod|LITENING|synthetic[- ]aperture|SAR imagery|infrared (?:sensor|camera|imagery)|thermal (?:sensor|imagery|camera)|"
                        r"sensor (?:tasking|operator|footprint|cueing|slew\w*)|pattern[- ]of[- ]life (?:collection|analysis|methodolog\w+)|"
                        r"collection (?:plan|asset|tasking|technique)s?|orbit(?:ing)? (?:the|at|over)|loiter(?:ing)? (?:pattern|altitude|orbit)|"
                        r"camera (?:zoom|field of view)|video feed (?:latency|lag)|geolocat\w+ (?:technique|method|procedure)|"
                        r"target (?:acquisition|tracking) (?:radar|mode|procedure)|track[- ]while[- ]scan|fire[- ]control (?:radar|solution))\b")),
    ("isr", "review", _r(r"\b(?:IFF\s+Mode\s+(?:I{1,3}V?|[1-5]\w?)|Mode\s+(?:I{1,3}|IV|[1-5])\s+(?:squawk|IFF|code|response|interrogat\w+)|"
                         r"squawk(?:ing|ed)?\s+Mode|interrogat\w+\s+(?:the )?(?:track|contact)|ESM\s+(?:signature|emission)|emitter\s+(?:library|signature))\b")),
    # --- attack geometry and tactics -------------------------------------------------------------------------
    ("geometry", "strip", _r(r"\battack\s+(?:heading|geometry|axis|profile|run|vector|azimuth|angle)\b|\b(?:run[- ]in|bomb(?:ing)? run|dive[- ]?bomb\w*|"
                             r"roll[- ]in|pop[- ]?up (?:attack|manoeuvre|maneuver)|strafing run|low[- ]level (?:attack|ingress)|off[- ]axis|"
                             r"release (?:point|altitude|heading|parameters|envelope)|weapon(?:s)? (?:release|employment) (?:envelope|parameters|zone)|"
                             r"ingress (?:route|heading|axis)|egress (?:route|heading)|standoff (?:range|distance)|angle of (?:attack|impact|descent)|"
                             r"impact (?:angle|point|azimuth)|aim[- ]?point|desired mean point of impact|DMPI|MPI)\b")),
    ("geometry", "strip", _r(r"\b(?:heading|bearing|azimuth)\s+(?:of\s+)?(?:0|1|2|3)?\d{1,2}\b(?:\s*degrees)?|\b(?:at|from|above|below)\s+(?:an altitude of\s+)?\d[\d,]*\s*(?:feet|ft|AGL|MSL)\b\b|"
                             r"\b(?:altitude|elevation)\s+of\s+\d[\d,]*\s*(?:feet|ft|meters|metres)\b|\bflight\s+level\s+\d+\b|\b\d{1,3}\s*degrees?\s+(?:off|from)\s+(?:the\s+)?(?:target|axis|heading|north)\b")),
    # --- targeting-cycle procedure steps ---------------------------------------------------------------------
    ("procedure", "strip", _r(r"\bF2T2EA\b|\bfind[, ]+fix[, ]+(?:track[, ]+)?(?:target[, ]+)?(?:engage|finish)\b|\bkill[- ]chain\b|\bdynamic[- ]targeting (?:cell|process|cycle|procedure)s?\b|"
                             r"\btarget(?:ing)?[- ]cycle (?:step|phase|procedure)s?\b|\btarget (?:folder|nomination (?:process|procedure)|development (?:process|procedure))\b|"
                             r"\bnine[- ]?line\b|\b9[- ]?line\b|\bCAS (?:check[- ]?in|briefing|brief)\b|\btalk[- ]?on\b|\bcheck[- ]in (?:brief|format)\b|"
                             r"\bweapon[- ]target (?:pairing|assignment)\b|\bjoint target list\b|\bJTL\b|\btarget(?:ing)? (?:checklist|worksheet)\b|"
                             r"\bstep\s+\d+\s+of\s+the\s+(?:targeting|engagement|fire)\b|\bengagement (?:sequence|procedure|checklist)\b|"
                             r"\bsteps? (?:to|for) (?:locate|find|geolocate|identify and engage|engage|kill)\b")),
    ("procedure", "strip", _r(r"\bhow (?:to|do you|does one|would one) (?:employ|deliver|drop|fire|launch|guide|aim|locate|find|track|target)\b")),
    # --- platform / system designations: review (needed in fratricide / identification cases, not elsewhere) -----
    ("platform", "review", _r(r"\b(?:AC|AH|UH|CH|MH|HH|MQ|RQ|EA|EC|FA|KC|EP|E)-\d{1,3}[A-Z]?\b|\bAWACS\b(?:\s+(?:Spectre|Spooky|Apache|Reaper|Predator|Hawkeye|Hercules|Gunship))?", 0)),
    ("platform", "review", _r(r"\b(?:A|B|C|F|T|P|S|U)-\d{1,3}[A-Z]?\b(?!/)", 0)),
    ("platform", "review", _r(r"\b(?:Predator|Reaper|Global Hawk|Apache|Spectre|Spooky|Warthog|Hornet|Tornado|Harrier|Aegis|Phalanx|Patriot battery|"
                              r"Patriot (?:fire unit|engagement|launcher)|PAC-\d|SM-\d|Standard Missile|Stinger|MANPADS)\b")),
]


def check(text: str) -> list[Flag]:
    out: list[Flag] = []
    for cat, sev, rx in RULES:
        for m in rx.finditer(text or ""):
            if m.group(0).strip():
                out.append(Flag(cat, sev, m.group(0).strip(), m.start(), m.end()))
    out.sort(key=lambda f: (f.start, f.category))
    return out


def is_clean(text: str) -> bool:
    return not any(f.severity == "strip" for f in check(text))


def _walk(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")


def scan_scenario(obj) -> list[tuple[str, Flag]]:
    return [(p, f) for p, s in _walk(obj) for f in check(s)]


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    raw = open(argv[0], encoding="utf-8").read()
    try:
        hits = scan_scenario(json.loads(raw))
    except ValueError:
        hits = [("", f) for f in check(raw)]
    for p, f in hits:
        print(f"{f.severity:6} {f.category:9} {p}: {f.match!r}")
    return 1 if any(f.severity == "strip" for _, f in hits) else 0


if __name__ == "__main__":
    sys.exit(main())
