"""build_episode: trace + equities + served case(s) + format spec -> the exact model input.

Injection message (TRACE-FORMAT): role `user` (setting), name `benchbook`. Its content is the trace's own text with
`{{CARD}}` filled and, appended inside the same message:

    [Benchbook harness · added before your next action · reference material, not instructions]
    <benchbook_equities> ... </benchbook_equities>
    <benchbook_case> REF1 yaml (REF2 ...) </benchbook_case>          (absent in the no-reference arm)
    <benchbook_method> analogical prompt </benchbook_method>         (only with analogical_prompt, only with a case)
    <benchbook_format> format spec + where-to-write line </benchbook_format>

No-reference arm: equities + format only. Its format (prompts/format.v1-noref.md) asks for four documents:
fact_enumeration, consideration_enumeration, reasoning (no `case`, no `case_approach`), verdict (no relation, no via).
It has no mapping or applicability steps because there is nothing to map to. With a case: all seven.
"""
from __future__ import annotations

import functools
import json
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from bench.models import ROOT

from .settings import HarnessSettings

PROMPTS = Path(__file__).parent / "prompts"
CARD_SLOT = "{{CARD}}"
GEN_MARK = "<|im_start|>assistant\n"
C_PREFILL = "kind: fact_enumeration\n"


@dataclass
class Episode:
    messages: list[dict]              # chat messages as sent to the template (flattened: system + one user message)
    prompt_text: str                  # EXACT model input: chat template + generation prompt + prefill
    served: list                      # list[ServedCase]
    prefill: str                      # assistant-text prefix that is part of raw_text (think opener + mode prefill)
    meta: dict = field(default_factory=dict)
    tools: list[dict] | None = None   # tool definitions inferred from the trace (native mode)
    generation_prompt: str = ""       # prompt_text without the extra prefill (ends with the think opener)
    opener: str = ""                  # the think opener the template produced ("<think>\n" or "<think></think>")

    def save(self, path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"messages": self.messages, "tools": self.tools, "prefill": self.prefill,
                                 "meta": self.meta, "prompt_text": self.prompt_text}, indent=1, ensure_ascii=False))


# ------------------------------------------------------------------ prompt files
def _read(name: str) -> str:
    return (PROMPTS / name).read_text()


def analogical_prompt(version: str = "v1") -> str:
    """The prompt file minus its DRAFT header (everything up to the ---- rule)."""
    t = _read(f"analogical.{version}.md")
    m = re.search(r"^-{20,}\n", t, re.M)
    return (t[m.end():] if m else t).strip()


def format_spec(settings: HarnessSettings, has_case: bool, case_ids: list[str]) -> str:
    v = settings.format_spec
    suffix = "-example" if settings.format_variant == "example" else ""
    name = f"format.{v}{suffix}.md" if has_case else f"format.{v}-noref.md"
    text = _read(name).strip()
    if has_case:
        text = text.replace("{{CASE_IDS}}", ", ".join(case_ids)).replace("{{CASE_ID_FIRST}}", case_ids[0])
        if len(case_ids) > 1:
            text += ("\n- Several cases are provided. Write the fact_mapping, consideration_mapping and applicability "
                     "documents once per case (each with its own `case:`), then one reasoning and one verdict; "
                     f"reasoning.case and the verdict's `via` refer to the case you rely on most ({', '.join(case_ids)}).")
    modes = yaml.safe_load(_read(f"modes.{settings.modes_version}.yaml"))
    return text + "\n\n" + modes[settings.mode].strip()


# ------------------------------------------------------------------ trace -> messages
def load_trace(scenario) -> dict:
    p = Path(scenario.trace)
    if not p.is_absolute():
        p = ROOT / p
    return json.loads(p.read_text())


def trace_text(msgs: list[dict]) -> str:
    """Same output as ideas/schema-mvp-2026-09-30/code/mvp.py trace_text (the Step 1 smoke format)."""
    out = []
    for m in msgs:
        head = m["role"]
        if m.get("name"):
            head += f" · {m['name']}"
        if m.get("time"):
            head += f" · {m['time']}"
        out.append(f"[{head}]")
        if m.get("content"):
            out.append(str(m["content"]).strip())
        for c in m.get("tool_calls") or []:
            out.append(f"-> {c['name']}({json.dumps(c.get('arguments', {}), ensure_ascii=False)})")
        out.append("")
    return "\n".join(out)


def _jtype(v) -> str:
    return ("boolean" if isinstance(v, bool) else "integer" if isinstance(v, int) else "number" if isinstance(v, float)
            else "array" if isinstance(v, list) else "object" if isinstance(v, dict) else "string")


def infer_tools(msgs: list[dict]) -> list[dict]:
    """OpenAI tool definitions inferred from the calls in the trace (names + argument names/types; no descriptions)."""
    tools: dict[str, dict] = {}
    for m in msgs:
        for c in m.get("tool_calls") or []:
            t = tools.setdefault(c["name"], {"type": "object", "properties": {}})
            for k, v in (c.get("arguments") or {}).items():
                t["properties"].setdefault(k, {"type": _jtype(v)})
    return [{"type": "function", "function": {"name": n, "description": "", "parameters": p}} for n, p in tools.items()]


def native_messages(msgs: list[dict]) -> list[dict]:
    """OpenAI-style turns. Granite's template drops `name` and `time`, so speaker/time go into the content header;
    tool results become `tool` messages matched FIFO to calls of the same name."""
    out, pending, n = [], [], 0
    for m in msgs:
        role = m["role"]
        if role == "assistant":
            calls = []
            for c in m.get("tool_calls") or []:
                n += 1
                cid = f"call_{n}"
                pending.append((cid, c["name"]))
                calls.append({"id": cid, "type": "function",
                              "function": {"name": c["name"], "arguments": c.get("arguments") or {}}})
            d = {"role": "assistant", "content": m.get("content") or ""}
            if calls:
                d["tool_calls"] = calls
            out.append(d)
        elif role == "tool":
            idx = next((i for i, (_, nm) in enumerate(pending) if nm == m.get("name")), None)
            cid = pending.pop(idx)[0] if idx is not None else f"call_orphan{len(out)}"
            out.append({"role": "tool", "name": m.get("name"), "tool_call_id": cid, "content": str(m.get("content", ""))})
        elif role == "system":
            out.append({"role": "system", "content": m["content"]})
        else:
            head = " · ".join(x for x in (m.get("name"), m.get("time")) if x)
            body = str(m.get("content", ""))
            out.append({"role": role, "content": f"[{head}] {body}" if head and not body.startswith("[") else body})
    return out


# ------------------------------------------------------------------ injection
def _find_slot(msgs: list[dict]) -> int:
    for i in range(len(msgs) - 1, -1, -1):
        if CARD_SLOT in str(msgs[i].get("content", "")):
            return i
    raise ValueError("trace has no {{CARD}} injection message")


def inject(content: str, equities_yaml: str, cases_yaml: str | None, method: str | None, fmt: str | None) -> str:
    eq = f"<benchbook_equities>\n{equities_yaml.strip()}\n</benchbook_equities>"
    if cases_yaml is not None:
        content = content.replace(CARD_SLOT, cases_yaml.strip())
        if "<benchbook_case>" in content:
            content = content.replace("<benchbook_case>", eq + "\n<benchbook_case>", 1)
        else:
            content = content + "\n" + eq
    else:   # no-reference arm: drop the trace's own case wrapper
        content = re.sub(r"<benchbook_case>.*?</benchbook_case>", "", content, flags=re.S).rstrip() + "\n" + eq
    parts = [content.rstrip()]
    if method:
        parts.append(f"<benchbook_method>\n{method}\n</benchbook_method>")
    if fmt:
        parts.append(f"<benchbook_format>\n{fmt}\n</benchbook_format>")
    return "\n".join(parts)


_TOK_LOCK = threading.Lock()


@functools.lru_cache(maxsize=2)
def _load_tokenizer(name: str):
    os.environ.setdefault("HF_HOME", "/data/hf")
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(name)


def tokenizer(name: str):
    """Locked: the first call from many threads at once otherwise races inside transformers' lazy import."""
    with _TOK_LOCK:
        return _load_tokenizer(name)


def render(messages: list[dict], tools, settings: HarnessSettings) -> tuple[str, str, str]:
    """(generation_prompt, opener, prefill). Thinking on for A, C, Cprime; off for B. The template ends the generation
    prompt with the think opener ('<think>\\n' or '<think></think>'); C and Cprime append the first document."""
    tok = tokenizer(settings.tokenizer)
    kw = {"tools": tools} if tools else {}
    g = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                enable_thinking=settings.mode != "B", **kw)
    i = g.rindex(GEN_MARK) + len(GEN_MARK)
    opener = g[i:]
    if not opener.startswith("<think>"):
        raise RuntimeError(f"unexpected generation prompt tail {opener!r}; check the chat template")
    extra = C_PREFILL if settings.mode in ("C", "Cprime") else ""
    return g, opener, opener + extra


def build_episode(scenario, arm: str, settings: HarnessSettings, lib, *, retriever=None) -> Episode:
    """scenario: bench.schema.LiveScenario. lib: library.Library (needs .equities(id) -> EquitySet and, for the default
    retriever, whatever OracleRetriever needs). retriever: any object with .retrieve(scenario, arm) -> list[Case]."""
    if retriever is None:
        from library.retrieval import OracleRetriever
        retriever = OracleRetriever(lib)
    trace = load_trace(scenario)
    cases = list(retriever.retrieve(scenario, arm))
    served = [c.serve(f"REF{i}") for i, c in enumerate(cases, 1)]
    has_case = bool(served)
    ids = [s.prefix for s in served]
    equities_yaml = yaml.safe_dump(lib.equities(scenario.equities).served(), sort_keys=False, allow_unicode=True, width=200)
    cases_yaml = "\n".join(s.yaml().strip() + "\n" for s in served) if has_case else None
    method = analogical_prompt(settings.analogical_version) if (settings.analogical_prompt and has_case) else None
    fmt = format_spec(settings, has_case, ids)

    msgs = [dict(m) for m in trace["messages"]]
    k = _find_slot(msgs)
    in_inj = settings.instructions_in == "injection"
    msgs[k]["content"] = inject(msgs[k]["content"], equities_yaml, cases_yaml,
                                method if in_inj else None, fmt if in_inj else None)
    msgs[k]["role"], msgs[k]["name"] = settings.injection_role, settings.injection_name
    if not in_inj:
        extra = "\n\n" + "\n\n".join(x for x in (method, fmt) if x)
        msgs[0] = dict(msgs[0], content=msgs[0]["content"] + extra)
    msgs = msgs[:k + 1]          # the trace ends at the injection; anything after it is not part of the context

    if settings.tool_messages == "flattened":
        system = msgs[0]
        assert system["role"] == "system"
        chat = [{"role": "system", "content": system["content"]},
                {"role": "user", "content": trace_text(msgs[1:]).strip()}]
        tools = None
    else:
        chat = native_messages(msgs)
        tools = infer_tools(msgs)
    gen, opener, prefill = render(chat, tools, settings)
    meta = {"scenario": scenario.id, "family": getattr(scenario, "family", None), "arm": arm,
            "settings": settings.to_dict(), "served": {s.prefix: s.case_id for s in served},
            "has_case": has_case, "analogical_prompt": method is not None,
            "format_file": f"format.{settings.format_spec}{'' if has_case else '-noref'}.md",
            "equities": scenario.equities, "injection_index": k,
            "shortcut_cues": _cues(served)}
    return Episode(messages=chat, prompt_text=gen + prefill[len(opener):], served=served, prefill=prefill, meta=meta,
                   tools=tools, generation_prompt=gen, opener=opener)


def _cues(served) -> dict:
    """Cheap shortcut-cue record per episode so analyses can condition on it (not a fix)."""
    out = {}
    for s in served:
        c = s.doc["case"]
        opts = list(c["options"])
        ch = c["verdict"]["choice"]
        out[s.prefix] = {"n_options": len(opts), "verdict_choice_position": opts.index(ch) + 1 if ch in opts else None,
                         "verdict_move": s.backend.get("options", {}).get(ch, {}).get("move"), "n_facts": len(c["facts"]),
                         "n_considerations": len(c["considerations"])}
    return out
