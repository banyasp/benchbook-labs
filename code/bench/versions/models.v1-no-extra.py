"""Role -> model routing. Every Benchbook component asks for a *role* ("policy", "judge_choice", "converter"),
never a model id, so swapping a model is one line in config/models.yaml (or one env var for one run).

    from bench.models import role, complete
    cfg = role("converter")                      # RoleConfig(model="bedrock/...", temperature=0.2, ...)
    text = complete("converter", messages)       # routed by the backend prefix, logged to provenance

    python -m bench.models                       # print the roles in effect (after env overrides)

Backends: vllm/ (OpenAI-compatible local server), openrouter/, bedrock/ and dry/ (through code/datagen/llm.py,
which owns the allowlist and provenance), stub/ (offline; callers that need a stub answer pass `stub=`).
Judges need token probabilities, so scorers use role("judge_*") for the model id and make their own
logprob requests; complete() returns text only.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(os.environ.get("BENCHBOOK_MODELS_CONFIG", ROOT / "config" / "models.yaml"))
BACKENDS = ("vllm", "openrouter", "bedrock", "dry", "stub")


@dataclass
class RoleConfig:
    name: str
    model: str
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def backend(self) -> str:
        return self.model.partition("/")[0]

    @property
    def bare(self) -> str:
        return self.model.partition("/")[2]

    def get(self, key, default=None):
        return self.params.get(key, default)


def _coerce(v: str):
    try:
        return yaml.safe_load(v)
    except yaml.YAMLError:
        return v


def load_config(path: Path | None = None) -> dict:
    return yaml.safe_load(Path(path or CONFIG).read_text())


def role(name: str, config: dict | None = None) -> RoleConfig:
    cfg = config or load_config()
    roles = cfg.get("roles") or {}
    if name not in roles:
        raise KeyError(f"role `{name}` is not in {CONFIG} (roles: {', '.join(roles)})")
    params = dict(roles[name])
    env = f"BENCHBOOK_MODEL_{name.upper()}"
    if os.environ.get(env):
        params["model"] = os.environ[env]
    for k, v in os.environ.items():
        if k.startswith(env + "__"):
            params[k[len(env) + 2:].lower()] = _coerce(v)
    model = params.pop("model")
    if model.partition("/")[0] not in BACKENDS or not model.partition("/")[2]:
        raise ValueError(f"role `{name}`: model `{model}` must be <backend>/<id>, backend one of {BACKENDS}")
    return RoleConfig(name, model, params)


def _bedrock_env(cfg: dict):
    """Translate config/models.yaml's bedrock block into the env vars code/datagen/llm.py reads."""
    b = cfg.get("bedrock") or {}
    if b.get("region"):
        os.environ.setdefault("BENCHBOOK_AWS_REGION", b["region"])
    if b.get("allow_instance_role"):
        os.environ.setdefault("BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE", "1")
        if b.get("instance_role"):
            os.environ.setdefault("BENCHBOOK_AWS_INSTANCE_ROLE", b["instance_role"])


def _llm():
    sys.path.insert(0, str(ROOT / "code" / "datagen"))
    import llm  # noqa: E402  (code/datagen/llm.py)
    return llm


def complete(role_name: str, messages: list[dict], *, stage: str | None = None, out_path=None,
             stub: str | None = None, **overrides) -> str:
    """One chat completion for a role. overrides replace config params for this call (temperature, max_tokens...).
    For vllm/ the extra keys `chat_template_kwargs` and `top_p` are passed through."""
    cfg = load_config()
    r = role(role_name, cfg)
    p = {**r.params, **overrides}
    prov = Path(os.environ.get("BENCHBOOK_PROVENANCE") or ROOT / cfg.get("provenance", "results/provenance.jsonl"))
    if r.backend == "stub":
        if stub is None:
            raise ValueError(f"role `{role_name}` is a stub/ model; the caller must pass stub=<text>")
        return stub
    if r.backend == "vllm":
        return _vllm(r, messages, p, prov, stage)
    _bedrock_env(cfg)
    return _llm().complete(r.model, messages, p.get("temperature", 0.7), p.get("max_tokens", 4000), stage=stage or role_name,
                           out_path=out_path, training_bound=bool(p.get("training_bound")), provenance=prov)


def _vllm(r: RoleConfig, messages, p, prov: Path, stage):
    import json
    import time
    from openai import OpenAI

    llm = _llm()
    client = OpenAI(base_url=p.get("base_url", "http://localhost:8000/v1"), api_key="unused")
    extra = {k: p[k] for k in ("chat_template_kwargs",) if k in p}
    t0 = time.time()
    resp = client.chat.completions.create(model=r.bare, messages=messages, temperature=p.get("temperature", 1.0),
                                          top_p=p.get("top_p", 1.0), max_tokens=p.get("max_tokens", 4000),
                                          seed=p.get("seed"), extra_body=extra or None)
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": r.model, "role": r.name, "backend": "vllm",
           "stage": stage, "prompt_sha256": llm.prompt_hash(messages), "seconds": round(time.time() - t0, 2),
           "usage": resp.usage.model_dump() if resp.usage else None}
    prov.parent.mkdir(parents=True, exist_ok=True)
    with open(prov, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return resp.choices[0].message.content or ""


def main():
    cfg = load_config()
    print(f"config: {CONFIG}")
    for name in cfg.get("roles") or {}:
        r = role(name, cfg)
        extras = ", ".join(f"{k}={v}" for k, v in r.params.items())
        print(f"  {name:16} {r.model:40} {extras}")


if __name__ == "__main__":
    main()
