"""Generation: the raw prompt (chat template applied by us) goes to vLLM's /v1/completions.

Why not /v1/chat/completions: the chat endpoint cannot be told to continue a partial assistant `<think>` (it drops or
re-renders it, and Granite's template strips thinking from history). Rendering ourselves makes the model input exact,
inspectable (Episode.prompt_text) and identical across modes. `Completion.raw_text` = prefill + generated text, so
bench.schema.parse_reply(raw_text) works for every mode, and the faithfulness hook can continue from edited text.

Thread/async safe: no shared mutable state except the provenance file (appended under a lock).
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from bench import models
from bench.schema import split_think

from .episode import Episode
from .settings import HarnessSettings

_LOCK = threading.Lock()
EOS = "<|im_end|>"


@dataclass
class Completion:
    content: str                 # text after </think> (or the whole reply if the model never opened one)
    reasoning: str               # text inside <think>
    raw_text: str                # prefill/think opener + generated text: feed this to parse_reply
    usage: dict
    seconds: float
    finish_reason: str | None
    generated: str = ""          # only the newly generated text (raw_text minus the prefill/partial)
    request: dict = field(default_factory=dict)


# ------------------------------------------------------------------ transport (monkeypatched in tests)
def _post(url: str, payload: dict, timeout: float) -> dict:
    r = httpx.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


async def _apost(url: str, payload: dict, timeout: float) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(url, json=payload)
        r.raise_for_status()
        return r.json()


# ------------------------------------------------------------------ request building
TURN_MARKERS = ["\n[assistant]", "\n[tool", "\n[user", "\n[system"]


def _request(prompt: str, settings: HarnessSettings, role_name: str, seed):
    cfg = models.role(role_name)
    if cfg.backend != "vllm":
        raise ValueError(f"the harness needs a vllm/ role (raw /v1/completions); {role_name} is {cfg.model}")
    p = cfg.params
    payload = {
        "model": cfg.bare, "prompt": prompt,
        "max_tokens": settings.max_tokens or p.get("max_tokens", 12000),
        "temperature": settings.temperature if settings.temperature is not None else p.get("temperature", 1.0),
        "top_p": settings.top_p if settings.top_p is not None else p.get("top_p", 1.0),
        # Flattened traces: the model tends to continue the transcript after its reply ("[assistant] -> msg.send(...)",
        # even invented "[tool ...]" results). Stop at the next turn marker (integration smoke, 2026-10-25).
        "stop": [EOS] + (TURN_MARKERS if settings.tool_messages == "flattened" else []),
        "add_special_tokens": False,        # the template already wrote every special token
        "skip_special_tokens": False,       # keep </think> if the tokenizer marks it special
    }
    s = seed if seed is not None else (settings.seed if settings.seed is not None else p.get("seed"))
    if s is not None:
        payload["seed"] = s
    url = p.get("base_url", "http://localhost:8000/v1").rstrip("/") + "/completions"
    return cfg, url, payload


def _finish(resp: dict, start: str, t0: float, cfg, payload, ep_meta, stage) -> Completion:
    ch = resp["choices"][0]
    gen = ch.get("text", "")
    if gen.endswith(EOS):
        gen = gen[: -len(EOS)]
    raw = start + gen
    think, outside = split_think(raw)
    secs = round(time.time() - t0, 2)
    usage = resp.get("usage") or {}
    _log(cfg, payload, secs, usage, ch.get("finish_reason"), ep_meta, stage)
    return Completion(content=outside.strip(), reasoning=think, raw_text=raw, usage=usage, seconds=secs,
                      finish_reason=ch.get("finish_reason"), generated=gen,
                      request={k: v for k, v in payload.items() if k != "prompt"})


def _log(cfg, payload, secs, usage, finish, meta, stage):
    cfgfile = models.load_config()
    import os
    prov = Path(os.environ.get("BENCHBOOK_PROVENANCE") or models.ROOT / cfgfile.get("provenance", "results/provenance.jsonl"))
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": cfg.model, "role": cfg.name,
           "backend": "vllm", "stage": stage, "endpoint": "completions",
           "prompt_sha256": hashlib.sha256(payload["prompt"].encode()).hexdigest(), "seconds": secs, "usage": usage,
           "finish_reason": finish, "seed": payload.get("seed"), "max_tokens": payload["max_tokens"],
           "scenario": meta.get("scenario"), "arm": meta.get("arm"), "mode": (meta.get("settings") or {}).get("mode")}
    line = json.dumps(rec) + "\n"
    with _LOCK:
        prov.parent.mkdir(parents=True, exist_ok=True)
        with open(prov, "a") as f:
            f.write(line)


# ------------------------------------------------------------------ public API
def _partial_start(ep: Episode, partial: str) -> str:
    """A partial may be given with or without the think opener; it must start with one in the end."""
    return partial if partial.lstrip().startswith("<think") else ep.opener + partial


def run_episode(ep: Episode, settings: HarnessSettings, role: str = "policy", *, seed=None, timeout: float = 3600) -> Completion:
    cfg, url, payload = _request(ep.prompt_text, settings, role, seed)
    t0 = time.time()
    return _finish(_post(url, payload, timeout), ep.prefill, t0, cfg, payload, ep.meta, "harness")


async def arun_episode(ep: Episode, settings: HarnessSettings, role: str = "policy", *, seed=None, timeout: float = 3600) -> Completion:
    cfg, url, payload = _request(ep.prompt_text, settings, role, seed)
    t0 = time.time()
    return _finish(await _apost(url, payload, timeout), ep.prefill, t0, cfg, payload, ep.meta, "harness")


def continue_episode(ep: Episode, settings: HarnessSettings, partial: str, role: str = "policy", *, seed=None,
                     timeout: float = 3600) -> Completion:
    """Faithfulness hook: continue from `partial`, the assistant text so far (possibly edited), same mechanism as
    run_episode. `partial` is the assistant text including any think opener (a raw_text prefix); if it does not start
    with `<think` the episode's opener is prepended. raw_text of the result = partial + new text."""
    start, prompt = _continuation(ep, partial)
    cfg, url, payload = _request(prompt, settings, role, seed)
    t0 = time.time()
    return _finish(_post(url, payload, timeout), start, t0, cfg, payload, ep.meta, "harness-continue")


async def acontinue_episode(ep: Episode, settings: HarnessSettings, partial: str, role: str = "policy", *, seed=None,
                            timeout: float = 3600) -> Completion:
    start, prompt = _continuation(ep, partial)
    cfg, url, payload = _request(prompt, settings, role, seed)
    t0 = time.time()
    return _finish(await _apost(url, payload, timeout), start, t0, cfg, payload, ep.meta, "harness-continue")


def _continuation(ep: Episode, partial: str) -> tuple[str, str]:
    start = _partial_start(ep, partial)
    if not start.startswith(ep.opener):
        raise ValueError(f"partial must start with the episode's think opener {ep.opener!r} (or with no <think> at all)")
    return start, ep.generation_prompt + start[len(ep.opener):]
