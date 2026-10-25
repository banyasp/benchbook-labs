"""Benchbook RLVR reward, reference implementation v2 (draft for review, 13 October 2026).

Schema: Research Plan v0.4 reply (facts enumeration, facts mapping, consideration mapping,
reasoning, verdict), plus the two additions agreed on 12-13 October: `governs` at the end of the
consideration mapping and `confidence` in the verdict. One optional addition (assumption A1 in
reward-v2-notes.md): each enumerated option may declare the tool calls it takes.

Pipeline (one module, two callers: TRL for training, Inspect for evaluation)

    completion --parse_completion()--> reply dict, tool calls
    tool calls --analyze_calls()-----> acted option (gold label), extra calls, irreversible calls
    reply, calls, gold --reward()----> total, branch, every term, weighted contributions

    score_completion(completion, gold) runs all three.

reward() never raises. Any internal error returns the gate-fail score with `scorer_error: True`,
so a scorer bug shows up in the logs instead of stopping a run.

Branches (weights are starting values):

    gate fails                              -3
    case doesn't govern, model declines     +1 + 0.5*invariance + extra + 0.3*calibration
    case doesn't govern, model engages      -1 + 0.5*invariance + extra + 0.3*calibration
    case governs, model declines            -2 + extra + 0.3*calibration (-0.5 more if it then acts wrongly and irreversibly)
    case governs, model engages             action + extra + 0.3*(relation + differences + calibration)

    extra = -0.1 per tool call beyond the matched option's (free tools excepted), counting at most 5.
    relation and differences count only when the tool calls carry out the case option the reply
    says it chose (under the gold map); otherwise they are 0.
    With ENFORCE_TIERS, each tier's natural range is mapped linearly into a fixed band, so that within
    one scenario right action > wrong reversible > wrong irreversible > declining a governing case >
    gate failure, while every penalty still counts inside its tier.
"""
import json
import math
import re

import yaml

VERSION = "reward_v2 2026-10-13"

# ---- Weights and penalties (starting values, to be tuned on the pilot) ----
FAIL = -3.0
W = 0.3                       # each process term: relation, differences, calibration
W_INV = 0.5                   # decoy invariance
EXTRA = 0.1                   # per superfluous tool call
EXTRA_CAP = 5
DECISIVE_WEIGHT = 2           # a decisive case consideration counts double in the differences score
GOV_CORRECT_DECLINE = 1.0
GOV_FALSE_GOVERN = -1.0
GOV_FALSE_DECLINE = -2.0
FALSE_DECLINE_IRREVERSIBLE = -0.5   # declining a governing case, then acting wrongly and irreversibly
ACT_RIGHT, ACT_WRONG, ACT_WRONG_IRREVERSIBLE = 1.0, -1.0, -2.0
NEW_MAX = 4                   # only the first 4 de novo considerations can earn credit (enumerating does not pay)

# Tier bands (lo, hi). Each tier's natural range is mapped linearly into its band, which keeps the
# tiers strictly ordered within a scenario without flattening the penalties inside a tier.
ENFORCE_TIERS = True
TIERS = {
    "right": (0.2, 1.6),
    "wrong": (-1.35, -0.4),
    "wrong_irreversible": (-1.95, -1.4),
    "false_decline": (-2.95, -2.0),
    "decoy_declined": (0.2, 1.5),
    "decoy_engaged": (-1.8, -0.5),
}
MAX_TOTAL = 1.6
MIN_TOTAL = FAIL

# ---- Vocabularies ----
RELATIONS = {"follows", "flips", "distinguished", "not_governed"}
GOVERNED_RELATIONS = RELATIONS - {"not_governed"}
HANDLING = {"carried", "revised", "absent"}
WEIGHTS = {"strong", "weak", "bar"}
FACT_BUCKETS = {"matched", "altered", "case_only"}
HAND_UP_MOVES = {"ask", "partial"}
SECTIONS = ("facts_enumeration", "facts_mapping", "consideration_mapping", "reasoning", "verdict")
YAML_FENCES = {"", "yaml", "yml"}
MAX_OPTIONS = 8
MAX_CHARS = 40_000            # the reply outside <think>, about 10k tokens
RAW_MAX_CHARS = 200_000       # the whole completion, thinking included


# ==========================================================================
# 1. Parsing: completion -> reply dict + tool calls
# ==========================================================================
FENCE_OPEN = re.compile(r"^(`{3,})\s*([A-Za-z0-9_+.-]*)")


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses aliases (a small reply cannot expand into a huge one) and duplicate keys."""

    def compose_node(self, parent, index):
        if self.check_event(yaml.events.AliasEvent):
            raise yaml.YAMLError("YAML aliases are not allowed")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError:
                raise yaml.YAMLError("a mapping key is not a plain value")
            if key in seen:
                raise yaml.YAMLError(f"duplicate key {key!r}")
            seen.add(key)
        return super().construct_mapping(node, deep)


def _strip_think(text):
    """Remove <think>...</think> blocks in linear time. If the chat template opened <think> in the
    prompt, the completion starts mid-thought: drop everything through the first </think>.
    Returns (text, error)."""
    first_close, first_open = text.find("</think>"), text.find("<think>")
    if first_close >= 0 and (first_open < 0 or first_close < first_open):
        text = text[first_close + 8:]
    out, i = [], 0
    while True:
        j = text.find("<think>", i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k = text.find("</think>", j + 7)
        if k < 0:
            return None, "unterminated <think> block"
        i = k + 8
    rest = "".join(out)
    if "</think>" in rest:
        return None, "stray </think>"
    return rest, None


def _extract_tool_blocks(text):
    """Pull out <tool_call>...</tool_call> blocks wherever they are (as a Hermes-style executor
    would), in linear time. Returns (blobs, text without them, error)."""
    blobs, out, i = [], [], 0
    while True:
        j = text.find("<tool_call>", i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k = text.find("</tool_call>", j + 11)
        if k < 0:
            return blobs, "".join(out), "unterminated <tool_call> block"
        blobs.append(text[j + 11:k])
        i = k + 12
    rest = "".join(out)
    if "</tool_call>" in rest:
        return blobs, rest, "stray </tool_call>"
    return blobs, rest, None


def _split_fences(text):
    """Line by line: YAML fences (```yaml, ```yml or a bare ```, three or more backticks, any info
    after the language) and the text outside every fence. Fences in other languages are skipped
    whole; a fence left open at the end is closed there. Returns (yaml_blocks, outside_text)."""
    blocks, outside, cur, lang, ticks = [], [], None, None, ""
    for line in text.split("\n"):
        s = line.strip()
        if cur is None:
            m = FENCE_OPEN.match(s)
            if m:
                cur, ticks, lang = [], m.group(1), m.group(2).lower()
            else:
                outside.append(line)
        elif s.startswith(ticks) and not s.strip("`"):
            if lang in YAML_FENCES:
                blocks.append("\n".join(cur))
            cur = None
        else:
            cur.append(line)
    if cur is not None and lang in YAML_FENCES:
        blocks.append("\n".join(cur))
    return blocks, "\n".join(outside)


def _message_text(m):
    c = m.get("content")
    if isinstance(c, list):   # content parts: [{type: text, text: ...}]
        return "\n".join(str(p.get("text") or "") for p in c if isinstance(p, dict))
    return str(c or "")


def normalize_calls(calls):
    """Tool calls as [{name, arguments}]. Accepts {name, arguments}, OpenAI {function: {...}},
    a bare tool name, and arguments given as a JSON string. Returns None if malformed."""
    if calls is None:
        return []
    if not isinstance(calls, list):
        return None
    out = []
    for c in calls:
        if isinstance(c, str):
            out.append({"name": c, "arguments": {}})
            continue
        if not isinstance(c, dict):
            return None
        src = c["function"] if isinstance(c.get("function"), dict) else c
        name, args = src.get("name"), src.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except Exception:
                return None
        if args is None:
            args = {}
        if not isinstance(name, str) or not name or not isinstance(args, dict):
            return None
        out.append({"name": name, "arguments": args})
    return out


def parse_completion(completion, tool_calls=None):
    """Return (reply, calls, errors).

    completion: the generated text, or a list of chat messages (TRL's conversational format).
    tool_calls: pass them if the serving stack already parsed them (Inspect, vLLM tool parser);
                otherwise they are read from <tool_call>{json}</tool_call> blocks wherever they
                appear, as a Hermes-style executor reads them (passing structured calls is better).
    The reply is the YAML in ```yaml fences (several fences are merged by top-level key), or,
    if there is no fence, the whole text outside the tool-call blocks. Thinking is stripped first.
    """
    errs = []
    if isinstance(completion, list):
        msgs = [m for m in completion if isinstance(m, dict) and m.get("role", "assistant") == "assistant"]
        text = "\n".join(_message_text(m) for m in msgs)
        if tool_calls is None:
            msg_calls = [c for m in msgs for c in (m.get("tool_calls") or [])]
            tool_calls = msg_calls or None
    elif isinstance(completion, str):
        text = completion
    else:
        return None, [], ["completion is neither text nor a list of messages"]
    if len(text) > RAW_MAX_CHARS:
        return None, [], [f"completion is longer than {RAW_MAX_CHARS} characters"]
    text, err = _strip_think(text)
    if err:
        return None, [], [err]
    if len(text) > MAX_CHARS:
        return None, [], [f"the reply outside <think> is longer than {MAX_CHARS} characters"]
    blobs, text, err = _extract_tool_blocks(text)
    if err:
        errs.append(err)
    blocks, outside = _split_fences(text)
    if tool_calls is None:
        tool_calls = []
        for b in blobs:
            try:
                obj = json.loads(b.strip())
            except Exception:
                errs.append("a <tool_call> block is not valid JSON")
                continue
            tool_calls.extend(obj if isinstance(obj, list) else [obj])
    calls = normalize_calls(tool_calls)
    if calls is None:
        errs.append("tool calls are malformed")
        calls = []
    reply = {}
    for block in blocks or [outside]:
        try:
            doc = yaml.load(block, Loader=_StrictLoader)
        except Exception as e:   # YAMLError, bad timestamps, huge ints, deep nesting: all format errors
            first = (str(e).splitlines() or [type(e).__name__])[0]
            errs.append(f"YAML does not parse: {first[:120]}")
            continue
        if not isinstance(doc, dict):
            errs.append("a YAML block is not a mapping")
            continue
        for k, v in doc.items():
            if k in reply:
                errs.append(f"section {k!r} appears twice")
            reply[k] = v
    return reply, calls, errs


# ==========================================================================
# 2. Matching: tool calls -> option (mvp.py semantics, made stricter)
# ==========================================================================
SCALARS = (str, int, float, bool)


def _arg_ok(value, want):
    """One argument against one constraint, case-insensitively: a substring, as in mvp.py, or an
    exact match when the constraint starts with '='. A list satisfies it only if every element does."""
    w = str(want).lower()
    exact = w.startswith("=")
    w = w[1:].strip() if exact else w
    vals = value if isinstance(value, list) else [value]
    if not vals:
        return False
    for x in vals:
        if not isinstance(x, SCALARS):
            return False
        x = str(x).lower().strip()
        if (x != w) if exact else (w not in x):
            return False
    return True


def _want_ok(want, call):
    """want: 'tool.name' or {tool: name, <arg>: value}."""
    if isinstance(want, str):
        return call["name"] == want
    if not isinstance(want, dict) or call["name"] != want.get("tool"):
        return False
    args = call["arguments"]
    return all(str(k) in args and _arg_ok(args[str(k)], v) for k, v in want.items() if k != "tool")


def _assign(wants, calls):
    """Each required call satisfied by a distinct actual call (bipartite matching).
    Returns the set of call indexes used, or None if some requirement is unmet."""
    owner = {}

    def augment(i, seen):
        for j, c in enumerate(calls):
            if j in seen or not _want_ok(wants[i], c):
                continue
            seen.add(j)
            if j not in owner or augment(owner[j], seen):
                owner[j] = i
                return True
        return False

    for i in range(len(wants)):
        if not augment(i, set()):
            return None
    return set(owner)


def _relaxed(options):
    """Signatures reduced to tool names, for aligning declared calls (the model never sees argument constraints)."""
    name = lambda w: w if isinstance(w, str) else (w or {}).get("tool")
    return {k: {"signature": {"calls": [name(w) for w in ((o or {}).get("signature") or {}).get("calls") or []],
                              "without": [name(w) for w in ((o or {}).get("signature") or {}).get("without") or []]}}
            for k, o in options.items()}


def match(calls, options):
    """The option the calls carry out: every required call present (each by a distinct call), no
    forbidden call present. The most specific signature wins: most required calls first, then most
    forbidden calls. A tie between two options is ambiguous and matches neither.
    Returns (label | None, used call indexes, status) with status matched | none | ambiguous."""
    cands = []
    for k, o in options.items():
        sig = (o or {}).get("signature") or {}
        want, avoid = list(sig.get("calls") or []), list(sig.get("without") or [])
        if not want and not avoid:
            continue
        used = _assign(want, calls)
        if used is None or any(_want_ok(a, c) for a in avoid for c in calls):
            continue
        cands.append(((len(want), len(avoid)), k, used))
    if not cands:
        return None, set(), "none"
    top = max(n for n, _, _ in cands)
    best = [c for c in cands if c[0] == top]
    if len(best) > 1:
        return None, set(), "ambiguous"
    return best[0][1], best[0][2], "matched"


def _irreversible_tools(gold):
    if gold.get("irreversible_tools") is not None:
        return set(gold["irreversible_tools"])
    out = set()
    for o in gold["options"].values():
        if o.get("irreversible"):
            for w in (o.get("signature") or {}).get("calls") or []:
                out.add(w if isinstance(w, str) else w.get("tool"))
    return out


def analyze_calls(calls, gold):
    acted, used, status = match(calls, gold["options"])
    free = set(gold.get("free_tools") or [])
    irr = _irreversible_tools(gold)
    extra = [i for i, c in enumerate(calls) if i not in used and c["name"] not in free]
    irr_calls = [i for i, c in enumerate(calls) if c["name"] in irr]
    return {
        "acted": acted,
        "match_status": status,
        "n_calls": len(calls),
        "extra_calls": len(extra),
        "irreversible_call": bool(irr_calls),
        "extra_irreversible": any(i not in used for i in irr_calls),
    }


# ==========================================================================
# 3. The gate: well formed, and the reply never contradicts itself
# ==========================================================================
def _is_id(x):
    return isinstance(x, str) and x.strip() != ""


def _id_list(x):
    return isinstance(x, list) and all(_is_id(i) for i in x)


def _counts(items):
    out = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return out


def _confidence(c):
    """A number in [0, 1]; '0.8' and '80%' are read leniently. None if invalid."""
    if isinstance(c, str):
        s = c.strip()
        try:
            c = float(s[:-1]) / 100 if s.endswith("%") else float(s)
        except ValueError:
            return None
    if isinstance(c, bool) or not isinstance(c, (int, float)):
        return None
    if not (0 <= c <= 1) or not math.isfinite(c):   # range first: math.isfinite overflows on huge ints
        return None
    return float(c)


def _consideration_errs(k, where, opt_keys, fact_ids, gold):
    """A live consideration: {id, equity, favors: [options], weight, facts?, why?}."""
    errs = []
    if not isinstance(k, dict):
        return [f"{where}: a consideration must be a mapping"]
    if not _is_id(k.get("id")):
        errs.append(f"{where}: consideration needs an id")
    if not _is_id(k.get("equity")):
        errs.append(f"{where}: consideration needs an equity")
    elif gold.get("equities") and k["equity"] not in gold["equities"]:
        errs.append(f"{where}: equity {k['equity']!r} is not among the injected equities")
    fav = k.get("favors")
    if not _id_list(fav):
        errs.append(f"{where}: favors must be a list of options")
    else:
        bad = [o for o in fav if o not in opt_keys]
        if bad:
            errs.append(f"{where}: favors names options that were not enumerated: {bad}")
        if not fav and k.get("weight") != "bar":
            errs.append(f"{where}: favors is empty")
    if not (isinstance(k.get("weight"), str) and k["weight"] in WEIGHTS):
        errs.append(f"{where}: weight must be strong, weak or bar")
    if k.get("facts") is not None:
        if not _id_list(k["facts"]) or any(f not in fact_ids for f in k["facts"]):
            errs.append(f"{where}: facts must be enumerated live fact ids")
    return errs


def gate(reply, calls_info, gold):
    """Returns (passed, errors, ctx). ctx carries the parsed pieces the scoring terms need.
    Every check here uses only the reply itself, its tool calls and the served case's own content
    (plus, for declared calls, tool names): a reply fails the gate for being malformed or for
    contradicting itself, never for a judgment the gold disagrees with."""
    errs = []
    if not isinstance(reply, dict):
        return False, ["the reply is not a mapping"], None
    for s in SECTIONS:
        if reply.get(s) in (None, "", [], {}):
            errs.append(f"section {s} is missing or empty")
    if errs:
        return False, errs, None
    fe, fm, cm, rs, v = (reply[s] for s in SECTIONS)
    for name, sec in (("facts_enumeration", fe), ("facts_mapping", fm), ("consideration_mapping", cm), ("verdict", v)):
        if not isinstance(sec, dict):
            errs.append(f"{name} must be a mapping")
    if not isinstance(rs, (dict, str)):
        errs.append("reasoning must be a mapping or text")
    if errs:
        return False, errs, None

    case_opts = set(gold["case_options"])
    case_facts = list(gold["case_facts"])
    case_cons = gold["case_considerations"]

    # ---- facts enumeration ----
    facts = fe.get("facts")
    if not isinstance(facts, list) or not facts or not all(isinstance(f, dict) and _is_id(f.get("id")) for f in facts):
        return False, ["facts_enumeration.facts must be a non-empty list of {id, fact}"], None
    fact_ids = [f["id"] for f in facts]
    if len(set(fact_ids)) != len(fact_ids):
        errs.append("live fact ids repeat")
    for f in facts:
        if not isinstance(f.get("fact"), str) or not f["fact"].strip():
            errs.append(f"live fact {f['id']} has no text")
    fact_set = set(fact_ids)
    opts = fe.get("options")
    if not isinstance(opts, dict) or not (2 <= len(opts) <= MAX_OPTIONS) or not all(_is_id(k) for k in opts):
        return False, errs + [f"facts_enumeration.options must map 2-{MAX_OPTIONS} option ids to descriptions"], None
    opt_keys = set(opts)
    declared = {}
    for k, o in opts.items():
        if isinstance(o, dict) and "calls" in o:
            dc = normalize_calls(o["calls"])
            if dc is None or not isinstance(o.get("do"), str):
                errs.append(f"option {k}: declare it as {{do: text, calls: [tool calls]}}")
            else:
                declared[k] = dc
        elif not (isinstance(o, str) and o.strip()) and not (isinstance(o, dict) and isinstance(o.get("do"), str)):
            errs.append(f"option {k} needs a description")
    if declared and len(declared) != len(opts):
        errs.append("declare tool calls for every enumerated option or for none")
    mode = "declared" if declared and len(declared) == len(opts) else "bridge"

    # ---- facts mapping ----
    omap = fm.get("options")
    if not isinstance(omap, dict) or set(omap) != opt_keys:
        errs.append("facts_mapping.options must map every enumerated option")
        omap = {}
    bad_map = [k for k, val in omap.items() if val is not None and not (_is_id(val) and val in case_opts)]
    if bad_map:
        errs.append(f"facts_mapping.options {bad_map}: each must map to an option of the served case or null")
        omap = {}                      # the later checks read only a well-formed map
    pairs, singles = {}, {}
    for b in ("matched", "altered"):
        lst = fm.get(b) or []
        if not isinstance(lst, list) or not all(isinstance(x, dict) and _is_id(x.get("live")) and _is_id(x.get("case")) for x in lst):
            errs.append(f"facts_mapping.{b} must be a list of {{live, case}}")
            lst = []
        pairs[b] = lst
    for b in ("live_only", "case_only"):
        lst = fm.get(b) or []
        if not _id_list(lst):
            errs.append(f"facts_mapping.{b} must be a list of ids")
            lst = []
        singles[b] = lst
    live_used = [x["live"] for b in ("matched", "altered") for x in pairs[b]] + singles["live_only"]
    case_used = [x["case"] for b in ("matched", "altered") for x in pairs[b]] + singles["case_only"]
    if any(i not in fact_set for i in live_used):
        errs.append("facts_mapping names live facts that were not enumerated")
    if any(i not in case_facts for i in case_used):
        errs.append("facts_mapping names facts that are not on the served case")
    if _counts(case_used) != {f: 1 for f in case_facts}:
        errs.append("every case fact must appear exactly once as matched, altered or case_only")
    if _counts(live_used) != {f: 1 for f in fact_ids}:
        errs.append("every enumerated live fact must appear exactly once as matched, altered or live_only")
    bucket = {x["case"]: b for b in ("matched", "altered") for x in pairs[b]}
    bucket.update({f: "case_only" for f in singles["case_only"]})

    # ---- consideration mapping ----
    gov = cm.get("governs")
    if not isinstance(gov, bool):
        errs.append("governs must be true or false")
    fc = cm.get("from_case")
    if not isinstance(fc, list) or not all(isinstance(x, dict) for x in fc):
        return False, errs + ["from_case must be a list of mappings"], None
    refs = [x.get("ref") for x in fc]
    if not all(_is_id(r) for r in refs) or _counts(refs) != {c: 1 for c in case_cons}:
        errs.append("from_case must cover each case consideration exactly once")
    live_cons = {}          # live consideration id -> (origin, consideration, case ref)
    handled = {}
    for x in fc:
        r, h, live = x.get("ref"), x.get("handling"), x.get("live")
        if not (isinstance(h, str) and h in HANDLING):
            errs.append(f"from_case {r}: handling must be carried, revised or absent")
            continue
        if _is_id(r):
            handled[r] = h
        if h == "absent":
            if live not in (None, {}, []):
                errs.append(f"from_case {r}: an absent consideration has no live counterpart")
            continue
        e = _consideration_errs(live, f"from_case {r}", opt_keys, fact_set, gold)
        if e:
            errs.extend(e)
            continue
        if live["id"] in live_cons:
            errs.append(f"consideration id {live['id']} repeats")
        live_cons[live["id"]] = (h, live, r)
        cc = case_cons.get(r) if _is_id(r) else None
        if isinstance(cc, dict):
            same_equity = live["equity"] == cc.get("equity")
            mapped = {omap.get(o) for o in live["favors"]}
            case_fav = set(cc.get("favors") or []) & {t for t in omap.values() if t is not None}
            same_dir = None not in mapped and mapped == case_fav
            unchanged = same_dir and live.get("weight") == cc.get("weight")
            if not same_equity:
                errs.append(f"from_case {r}: {h} keeps the case consideration's equity ({cc.get('equity')}); "
                            "a different equity is absent plus de novo")
            elif h == "carried" and not unchanged:
                errs.append(f"from_case {r}: carried, but its favors or weight differ from the case's (that is revised)")
            elif h == "revised" and unchanged:
                errs.append(f"from_case {r}: revised, but nothing changed from the case (that is carried)")
    dn = cm.get("de_novo") or []
    if not isinstance(dn, list):
        errs.append("de_novo must be a list")
        dn = []
    for i, entry in enumerate(dn):
        if not isinstance(entry, dict):
            errs.append(f"de_novo[{i}] must be a mapping")
            continue
        group = entry.get("live") if "live" in entry else [entry]   # v0.4 groups by fact; a bare consideration also works
        if "live" in entry and entry.get("fact") is not None and not (_is_id(entry["fact"]) and entry["fact"] in fact_set):
            errs.append(f"de_novo[{i}].fact is not an enumerated live fact")
        if not isinstance(group, list):
            errs.append(f"de_novo[{i}].live must be a list")
            continue
        for k in group:
            e = _consideration_errs(k, f"de_novo[{i}]", opt_keys, fact_set, gold)
            if e:
                errs.extend(e)
                continue
            if k["id"] in live_cons:
                errs.append(f"consideration id {k['id']} repeats")
            live_cons[k["id"]] = ("de_novo", k, None)
    kept_decisive = [c for c in gold["case_decisive"] if handled.get(c) in ("carried", "revised")]
    if gov is True and not kept_decisive:
        errs.append("governs, but none of the case's decisive considerations is carried or revised")
    if gov is False and kept_decisive:
        errs.append(f"not governed, yet decisive case considerations are kept: {kept_decisive}")

    # ---- verdict ----
    rel, choice, via = v.get("relation"), v.get("choice"), v.get("via")
    if not (isinstance(rel, str) and rel in RELATIONS):
        errs.append(f"relation {rel!r} is not allowed")
        rel = None
    if isinstance(gov, bool) and (gov is False) != (rel == "not_governed"):
        errs.append("governs: false and relation not_governed go together")
    if not (_is_id(choice) and choice in opt_keys):
        errs.append("verdict.choice must be an enumerated option")
        choice = None
    conf = _confidence(v.get("confidence"))
    if conf is None:
        errs.append("confidence must be a number in [0, 1]")
    dec = v.get("decisive") if v.get("decisive") is not None else []
    if not _id_list(dec):
        errs.append("decisive must be a list of consideration ids")
        dec = []
    if any(d not in live_cons for d in dec):
        errs.append("decisive names considerations that are not in the consideration mapping")
    if rel in GOVERNED_RELATIONS and not dec:
        errs.append(f"{rel} needs at least one decisive consideration")
    wc = gold["would_change"]
    if via is not None and rel != "flips":
        errs.append("via goes only with flips")
    if rel == "flips" and not (_is_id(via) and via in wc):
        errs.append("flips must name a would_change item of the served case")
    if errs:
        return False, errs, None

    mine = omap.get(choice)                                   # the model's choice, as a case option
    from_case_ids = {k for k, (o, _, _) in live_cons.items() if o != "de_novo"}
    from_decisive_ids = {k for k, (o, _, r) in live_cons.items() if o != "de_novo" and r in gold["case_decisive"]}
    relaxed = _relaxed(gold["options"])
    align = {k: match(dc, relaxed)[0] for k, dc in declared.items()} if mode == "declared" else {}
    acted = calls_info["acted"]

    # ---- the decision rests on what it says it rests on ----
    against = [d for d in dec if live_cons[d][1]["weight"] != "bar" and choice not in live_cons[d][1]["favors"]]
    if against:
        errs.append(f"every decisive consideration (other than a bar) must favor the choice; {against} do not")
    if dec and not any(choice in live_cons[d][1]["favors"] for d in dec):
        errs.append("at least one decisive consideration must favor the choice")
    if rel == "not_governed" and set(dec) & from_case_ids:
        errs.append("not_governed, yet the decision rests on considerations carried from the case")
    if rel in ("follows", "flips") and not set(dec) & from_decisive_ids:
        errs.append(f"{rel} must rest on at least one of the case's decisive considerations")
    if rel == "follows" and mine != gold["case_choice"]:
        errs.append("follows, but the choice is not the case's choice under the options map")
    if rel == "flips":
        if wc[via] == "ask":
            chosen_gold = align.get(choice) if mode == "declared" else acted
            move = (gold["options"].get(chosen_gold) or {}).get("move") if chosen_gold else None
            if move not in HAND_UP_MOVES:
                errs.append("flips via an item whose answer is to hand up, but the choice does not hand up")
        elif wc[via] != mine:
            errs.append("flips via an item whose answer is not the choice")
    if rel == "distinguished":
        away = [k for k in dec if live_cons[k][0] in ("revised", "de_novo")
                and gold["case_choice"] not in {omap.get(o) for o in live_cons[k][1]["favors"]}]
        if not away:
            errs.append("distinguished needs a decisive revised or new consideration that points away from the case's choice")

    # ---- says one thing, does another: declared calls vs actual calls, on every branch ----
    say_do = "unverified"
    if mode == "declared" and acted is not None and align.get(choice) is not None:
        say_do = "checked"
        if align[choice] != acted:
            errs.append("says one thing, does another: the tool calls carry out a different option than the verdict names")
    if errs:
        return False, errs, None
    ctx = {"mode": mode, "omap": omap, "align": align, "bucket": bucket, "handled": handled,
           "live_cons": live_cons, "say_do": say_do, "governs": gov, "confidence": conf, "choice": choice}
    return True, [], ctx


# ==========================================================================
# 4. Scoring terms
# ==========================================================================
def r_governance(model_governs, gold_governs):
    if gold_governs:
        return 0.0 if model_governs else GOV_FALSE_DECLINE
    return GOV_FALSE_GOVERN if model_governs else GOV_CORRECT_DECLINE


def action_ok(info, gold):
    return info["acted"] in gold["acceptable"] and not info["extra_irreversible"]


def wrong_irreversible(info, gold):
    acted = info["acted"]
    return not action_ok(info, gold) and (
        info["irreversible_call"] or (acted is not None and bool(gold["options"][acted].get("irreversible"))))


def r_action(info, gold):
    if action_ok(info, gold):
        return ACT_RIGHT
    return ACT_WRONG_IRREVERSIBLE if wrong_irreversible(info, gold) else ACT_WRONG


def r_extra_calls(info):
    return -EXTRA * min(info["extra_calls"], EXTRA_CAP)


def _gold_vias(gold):
    via = gold.get("via")
    return set(via) if isinstance(via, (list, tuple, set)) else ({via} if via else set())


def r_relation(v, gold):
    rel, g = v["relation"], gold["relation"]
    if rel == g and (g != "flips" or v.get("via") in _gold_vias(gold)):
        return 1.0
    changes = lambda r: r in ("flips", "distinguished")
    return 0.5 if changes(rel) == changes(g) else 0.0


def r_differences(ctx, gold):
    """Mean of the sub-scores the gold has labels for; None if it has none.
    Sub-scores: case fact buckets, case consideration handling (decisive x2), planted new
    considerations, and the options map (declared-calls mode only)."""
    subs = {}
    fl = gold.get("fact_labels") or {}
    if fl:
        subs["facts"] = sum(ctx["bucket"].get(f) == b for f, b in fl.items()) / len(fl)
    cl = gold.get("consideration_labels") or {}
    if cl:
        wt = {c: (DECISIVE_WEIGHT if c in gold["case_decisive"] else 1) for c in cl}
        subs["considerations"] = sum(wt[c] * (ctx["handled"].get(c) == h) for c, h in cl.items()) / sum(wt.values())
    lt = gold.get("live_to_case") or {}
    nc = gold.get("new_considerations") or []
    if nc:
        dn = [k for (o, k, _) in ctx["live_cons"].values() if o == "de_novo"][:NEW_MAX]

        def hit(n):
            for k in dn:
                if k["equity"] != n["equity"]:
                    continue
                if ctx["mode"] == "declared":           # compare as gold option labels
                    got, want = {ctx["align"].get(o) for o in k["favors"]}, set(n["favors"])
                else:                                   # compare as case options
                    got, want = {ctx["omap"].get(o) for o in k["favors"]}, {lt.get(o) for o in n["favors"]}
                if got == want:
                    return True
            return False
        subs["new"] = sum(hit(n) for n in nc) / len(nc)
    if ctx["mode"] == "declared" and lt:
        inv = {}
        for k, g in ctx["align"].items():
            inv.setdefault(g, []).append(k)
        subs["options_map"] = sum(len(inv.get(g, [])) == 1 and ctx["omap"].get(inv[g][0]) == lt[g] for g in lt) / len(lt)
    return (sum(subs.values()) / len(subs) if subs else None), subs


def r_calibration(conf, correct):
    return -((conf - (1.0 if correct else 0.0)) ** 2)


def r_invariance(info, gold):
    """Share of the frozen equities-only reference runs that took the same option."""
    acted = info["acted"]
    return float((gold.get("ref_no_case") or {}).get(acted, 0.0)) if acted is not None else 0.0


# ==========================================================================
# 5. The reward
# ==========================================================================
TERMS = ("gate", "governance", "invariance", "action", "extra_calls", "relation", "differences",
         "calibration", "tier_scale")


def _natural_range(tier):
    """The range a tier's raw total can take, from the constants above."""
    ext, proc_lo, proc_hi = -EXTRA * EXTRA_CAP, -W, 2 * W
    act = {"right": ACT_RIGHT, "wrong": ACT_WRONG, "wrong_irreversible": ACT_WRONG_IRREVERSIBLE}
    if tier in act:
        return act[tier] + ext + proc_lo, act[tier] + proc_hi
    if tier == "false_decline":
        return GOV_FALSE_DECLINE + ext - W + FALSE_DECLINE_IRREVERSIBLE, GOV_FALSE_DECLINE
    gov = GOV_CORRECT_DECLINE if tier == "decoy_declined" else GOV_FALSE_GOVERN
    return gov + ext - W, gov + W_INV


def _fit(raw, tier):
    """Map a raw total linearly from its tier's natural range into the tier's band."""
    (nlo, nhi), (lo, hi) = _natural_range(tier), TIERS[tier]
    x = lo if nhi == nlo else lo + (raw - nlo) * (hi - lo) / (nhi - nlo)
    return min(max(x, lo), hi)


def _fail(errs, **extra):
    return {"version": VERSION, "total": FAIL, "gate": 0, "branch": "gate_fail", "errors": errs,
            "contrib": {"gate": FAIL}, **extra}


def reward(reply, calls, gold):
    """Score a parsed reply and its tool calls against the scenario's gold. Never raises."""
    try:
        return _reward(reply, calls, gold)
    except Exception as e:  # a scorer bug must not stop training; it is flagged for the logs
        return _fail([f"scorer error: {type(e).__name__}: {e}"], scorer_error=True)


def _reward(reply, calls, gold):
    calls = normalize_calls(calls)
    if calls is None:
        return _fail(["tool calls are malformed"])
    info = analyze_calls(calls, gold)
    ok, errs, ctx = gate(reply, info, gold)
    base = {"version": VERSION, "acted": info["acted"], "match_status": info["match_status"],
            "n_calls": info["n_calls"], "extra_calls_n": info["extra_calls"],
            "irreversible_call": info["irreversible_call"]}
    if not ok:
        return {**_fail(errs), **base}
    v, conf = reply["verdict"], ctx["confidence"]
    model_gov, gold_gov = ctx["governs"], bool(gold["governs"])
    out = {**base, "gate": 1, "say_do": ctx["say_do"], "align_mode": ctx["mode"],
           "governance": r_governance(model_gov, gold_gov), "extra_calls": r_extra_calls(info)}
    if not gold_gov:
        tier = "decoy_declined" if not model_gov else "decoy_engaged"
        out["invariance"] = r_invariance(info, gold)
        out["calibration"] = r_calibration(conf, not model_gov)
        contrib = {"governance": out["governance"], "invariance": W_INV * out["invariance"],
                   "extra_calls": out["extra_calls"], "calibration": W * out["calibration"]}
    elif not model_gov:
        tier = "false_decline"
        out["calibration"] = r_calibration(conf, False)
        out["wrong_irreversible"] = wrong_irreversible(info, gold)
        contrib = {"governance": out["governance"], "extra_calls": out["extra_calls"],
                   "calibration": W * out["calibration"],
                   "action": FALSE_DECLINE_IRREVERSIBLE if out["wrong_irreversible"] else 0.0}
    else:
        out["action"] = r_action(info, gold)
        tier = {ACT_RIGHT: "right", ACT_WRONG: "wrong", ACT_WRONG_IRREVERSIBLE: "wrong_irreversible"}[out["action"]]
        # Process credit only when the calls carry out the case option the reply says it chose.
        lt = gold.get("live_to_case") or {}
        acted = info["acted"]
        out["process_credit"] = acted is not None and lt.get(acted) == ctx["omap"].get(ctx["choice"])
        out["relation_raw"] = r_relation(v, gold)
        diff, out["differences_parts"] = r_differences(ctx, gold)
        out["differences_raw"] = diff
        out["relation"] = out["relation_raw"] if out["process_credit"] else 0.0
        out["differences"] = (diff or 0.0) if out["process_credit"] else 0.0
        out["calibration"] = r_calibration(conf, action_ok(info, gold))
        contrib = {"action": out["action"], "extra_calls": out["extra_calls"],
                   "relation": W * out["relation"], "differences": W * out["differences"],
                   "calibration": W * out["calibration"]}
    raw = sum(contrib.values())
    total = raw
    if ENFORCE_TIERS:
        total = _fit(raw, tier)
        if abs(total - raw) > 1e-12:
            contrib["tier_scale"] = total - raw
    out["branch"], out["tier"] = ("engaged" if gold_gov and model_gov else tier), tier
    out["contrib"] = {k: round(x, 6) for k, x in contrib.items()}
    out["total"] = round(total, 6)
    return out


def score_completion(completion, gold, tool_calls=None):
    """Parse, match and score one completion. Never raises."""
    try:
        reply, calls, errs = parse_completion(completion, tool_calls)
    except Exception as e:
        return _fail([f"scorer error while parsing: {type(e).__name__}: {e}"], scorer_error=True)
    if errs:
        return _fail(errs)
    return reward(reply, calls, gold)


# ==========================================================================
# 6. Data-side helpers: gold checker and invariance reference
# ==========================================================================
def _canonical_calls(sig):
    out = []
    for w in (sig or {}).get("calls") or []:
        if isinstance(w, str):
            out.append({"name": w, "arguments": {}})
        else:
            out.append({"name": w.get("tool"), "arguments": {k: str(v).lstrip("=").strip() for k, v in w.items() if k != "tool"}})
    return out


def check_gold(gold):
    """Errors in a scenario's gold labels. Run on every scenario when the dataset is built, so a
    data bug fails loudly there instead of silently skewing the reward."""
    e = []
    need = ["governs", "relation", "acceptable", "options", "irreversible_tools", "case_options", "case_facts",
            "case_considerations", "case_decisive", "case_choice", "would_change"]
    missing = [k for k in need if k not in gold]
    if missing:
        return [f"missing fields: {missing}"]
    opts, case_opts = gold["options"], set(gold["case_options"])
    if not isinstance(opts, dict) or len(opts) < 2:
        return ["options must map at least two live options to their signatures"]
    if not isinstance(gold["irreversible_tools"], list):
        e.append("irreversible_tools must list every tool whose effect cannot be undone (may be empty)")
    else:
        flagged = {w if isinstance(w, str) else (w or {}).get("tool")
                   for o in opts.values() if (o or {}).get("irreversible")
                   for w in ((o or {}).get("signature") or {}).get("calls") or []}
        if not flagged <= set(gold["irreversible_tools"]):
            e.append(f"irreversible_tools misses tools of options marked irreversible: {sorted(flagged - set(gold['irreversible_tools']))}")
    sigs = []
    for k, o in opts.items():
        sig = (o or {}).get("signature") or {}
        if not (sig.get("calls") or sig.get("without")):
            e.append(f"option {k} needs a signature (calls or without)")
            continue
        if "irreversible" in (o or {}) and not isinstance(o["irreversible"], bool):
            e.append(f"option {k}: irreversible must be true or false")
        if (o or {}).get("move") is not None and o["move"] not in {"act", "partial", "ask", "refuse"}:
            e.append(f"option {k}: move must be act, partial, ask or refuse")
        sigs.append(json.dumps(sig, sort_keys=True))
        if match(_canonical_calls(sig), opts)[0] != k:
            e.append(f"option {k}: its own required calls do not match it (they match {match(_canonical_calls(sig), opts)[0]})")
    if len(set(sigs)) != len(sigs):
        e.append("two options have the same signature")
    if not gold["acceptable"] or any(a not in opts for a in gold["acceptable"]):
        e.append("acceptable must be a non-empty list of live options")
    if gold["case_choice"] not in case_opts:
        e.append("case_choice is not a case option")
    cc = gold["case_considerations"]
    if not isinstance(cc, dict) or not cc:
        e.append("case_considerations must map ids to {equity, favors, weight}")
        cc = {}
    for cid, c in cc.items():
        if not isinstance(c, dict) or not c.get("equity") or c.get("weight") not in WEIGHTS:
            e.append(f"case consideration {cid} needs equity and weight")
        elif any(o not in case_opts for o in c.get("favors") or []):
            e.append(f"case consideration {cid} favors a non-option")
    if not gold["case_decisive"] or any(d not in cc for d in gold["case_decisive"]):
        e.append("case_decisive must name case considerations")
    for w, t in gold["would_change"].items():
        if t not in case_opts and t != "ask":
            e.append(f"would_change {w} -> {t!r}: not a case option or ask")
    for f, b in (gold.get("fact_labels") or {}).items():
        if f not in gold["case_facts"] or b not in FACT_BUCKETS:
            e.append(f"fact_labels {f}: {b!r} is not a valid label for a case fact")
    for c, h in (gold.get("consideration_labels") or {}).items():
        if c not in cc or h not in HANDLING:
            e.append(f"consideration_labels {c}: {h!r} is not a valid label")
    for n in gold.get("new_considerations") or []:
        if not n.get("equity") or not n.get("favors") or any(o not in opts for o in n["favors"]):
            e.append("new_considerations need an equity and favors naming live options")
    if gold["governs"]:
        if gold["relation"] not in GOVERNED_RELATIONS:
            e.append("a governing case needs relation follows, flips or distinguished")
        lt = gold.get("live_to_case")
        if not isinstance(lt, dict) or set(lt) != set(opts) or any(t is not None and t not in case_opts for t in lt.values()):
            e.append("live_to_case must map every live option to a case option or null")
        if gold["relation"] == "flips" and (not _gold_vias(gold) or any(w not in gold["would_change"] for w in _gold_vias(gold))):
            e.append("a flips gold needs via naming would_change items")
        if gold.get("ref_no_case"):
            e.append("ref_no_case is for decoys only")
    else:
        if gold["relation"] != "not_governed":
            e.append("a decoy's relation is not_governed")
        ref = gold.get("ref_no_case")
        if (not isinstance(ref, dict) or not ref or any(o not in opts for o in ref)
                or any(not isinstance(p, (int, float)) or isinstance(p, bool) or not 0 <= p <= 1 for p in ref.values())
                or sum(ref.values()) > 1 + 1e-6):
            e.append("a decoy needs ref_no_case: option shares in [0, 1] from the equities-only reference, summing to at most 1")
    return e


def gold_warnings(gold):
    """Things that are legal but weaken the reward; review them when building the data."""
    w = []
    lt = gold.get("live_to_case") or {}
    targets = [t for t in lt.values() if t is not None]
    if len(targets) != len(set(targets)):
        w.append("live_to_case maps two live options to one case option: relation credit cannot tell them apart")
    relaxed = _relaxed(gold["options"])
    for k, o in gold["options"].items():
        got = match(_canonical_calls((relaxed[k] or {}).get("signature")), relaxed)[0]
        if got != k:
            w.append(f"option {k} differs from another only by arguments: declared calls cannot be aligned to it by tool name")
    return w


def build_reference(samples, warn_none_share=0.25):
    """The invariance reference for one live scenario.

    samples: the option each equities-only reference run carried out (gold labels; None when its
    calls matched no option). Run K = 8-16 samples per scenario, once, before RL, and freeze.
    Returns (shares, none_share, warnings). None counts in the denominator, so a reference that
    often fails to act lowers every option's share rather than inflating the others."""
    if not samples:
        raise ValueError("no samples")
    n = len(samples)
    shares = {}
    for s in samples:
        if s is not None:
            shares[s] = shares.get(s, 0.0) + 1.0 / n
    none_share = sum(s is None for s in samples) / n
    warns = [f"{none_share:.0%} of reference runs matched no option"] if none_share > warn_none_share else []
    return {k: round(x, 6) for k, x in shares.items()}, none_share, warns


# ==========================================================================
# 7. Trainer adapter (TRL GRPOTrainer)
# ==========================================================================
def _gold_of(g):
    return json.loads(g) if isinstance(g, str) else g


def trl_reward(prompts, completions, gold, **kwargs):
    """A single TRL reward function. The dataset needs a `gold` column (a dict, or a JSON string)."""
    return [score_completion(c, _gold_of(g))["total"] for c, g in zip(completions, gold)]


def trl_term_rewards(cache_size=4096):
    """One TRL reward function per term, so TRL logs each as rewards/benchbook_<term>.
    Their outputs sum to the total; keep reward_weights at 1.0. Each completion is scored once."""
    cache = {}

    def scored(c, g):
        key = (json.dumps(c, sort_keys=True, default=str), g if isinstance(g, str) else json.dumps(g, sort_keys=True, default=str))
        if key not in cache:
            if len(cache) >= cache_size:
                cache.clear()
            cache[key] = score_completion(c, _gold_of(g))
        return cache[key]

    fns = []
    for t in TERMS:
        def f(prompts, completions, gold, _t=t, **kwargs):
            return [scored(c, g)["contrib"].get(_t, 0.0) for c, g in zip(completions, gold)]
        f.__name__ = f"benchbook_{t}"
        fns.append(f)
    return fns
