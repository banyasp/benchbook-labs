#!/usr/bin/env python3
"""Open-weight drafting backend for the Benchbook datagen pipeline.

complete(model, messages, temperature, max_tokens) picks a backend by model prefix:
  openrouter/<id>     OpenAI-compatible HTTPS to openrouter.ai; key from env OPENROUTER_API_KEY;
                      every request carries provider: {data_collection: "deny"}.
  bedrock/<modelId>   boto3 bedrock-runtime converse; region from env BENCHBOOK_AWS_REGION and
                      credentials from the profile named in env BENCHBOOK_AWS_PROFILE only. The default
                      credential chain is never used: this container's own AWS credentials are the
                      sandbox's, not Peter's. Exception (Peter, 2026-10-25): on the EC2 box, explicit
                      opt-in BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE=1 with region us-east-1 uses the instance
                      role, and only the role named in BENCHBOOK_AWS_INSTANCE_ROLE (default FiroInstanceRole).
  dry/<anything>      calls nothing: writes the prompt to disk and returns a placeholder.

Every call appends a record (model, family, time, prompt hash, stage, output path) to provenance.jsonl.
Allowlist: models.yaml `allowlist_mode: record` (default since 2026-10-25, Peter lifted the open-weight-only rule)
records per call whether the model is inside the allowlist (`allowlist` in provenance) and never refuses;
`enforce` restores refusing non-allowlisted models for training-bound stages.
`extra` passes backend-specific request fields (e.g. {"reasoning_effort": "high"} for gpt-oss).
boto3 and requests are imported only when used (urllib is the fallback for requests).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bbcommon import HERE  # noqa: E402

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_POLICY = {}


class LLMError(RuntimeError):
    pass


class ModelRefused(LLMError):
    pass


class RefusalError(LLMError):
    """The model declined the request: a content filter / guardrail stop reason, or a refusal-shaped reply.
    Recorded in provenance (`refusal: true`, `refusal_reason`). Callers catch this to save an incomplete record
    (design 4.3). It is NOT retried silently; see REFUSAL_HOOK for the (T2) fallback-router attachment point."""

    def __init__(self, reason, text="", model=None, stage=None):
        super().__init__(f"refusal ({reason}) from {model} at {stage}: {text[:160]!r}")
        self.reason, self.text, self.model, self.stage = reason, text, model, stage


# Stop reasons that mean a filter or guardrail, not the model, ended the reply.
REFUSAL_STOP_REASONS = {"content_filtered", "guardrail_intervened", "content_filter", "refusal"}
_REFUSAL_RE = re.compile(
    r"^\W*(i(?:'m| am)? (?:sorry|unable|afraid)|sorry,? (?:but )?i|i (?:can(?:'|no)t|cannot|won't|will not|am not able to|'m not able to)"
    r"|(?:unfortunately,? )?i (?:can(?:'|no)t|cannot) (?:help|assist|comply|provide|fulfil)|as an ai\b|i must decline|i can't (?:help|assist))",
    re.I)

# T2 hook, deliberately unset. The fallback router (design 4.2) applies ONLY to false-positive refusals of in-scope
# decision content. When implemented, set REFUSAL_HOOK = fn(err: RefusalError, model, messages, ctx) -> text | None;
# it must log both attempts and never be used for out-of-scope (operational technique) content.
REFUSAL_HOOK = None


def detect_refusal(text, stop_reason=None):
    """-> reason string or None. stop_reason: the backend's stop/finish reason."""
    if stop_reason and str(stop_reason).lower() in REFUSAL_STOP_REASONS:
        return f"stop_reason:{stop_reason}"
    t = (text or "").strip()
    if not t and stop_reason and str(stop_reason).lower() not in ("end_turn", "stop", "max_tokens", "length", "stop_sequence"):
        return f"empty reply with stop_reason:{stop_reason}"
    if t and len(t) < 600 and "{" not in t and _REFUSAL_RE.search(t):
        return "refusal-shaped reply"
    return None


def load_policy(path=None):
    p = Path(path) if path else HERE / "models.yaml"
    if str(p) not in _POLICY:
        _POLICY[str(p)] = yaml.safe_load(p.read_text())
    return _POLICY[str(p)]


def split_model(model):
    """'openrouter/openai/gpt-oss-120b' -> ('openrouter', 'openai/gpt-oss-120b')."""
    backend, _, bare = str(model).partition("/")
    if backend not in BACKENDS or not bare:
        raise ValueError(f"model `{model}` must look like openrouter/<id>, bedrock/<modelId> or dry/<anything>")
    return backend, bare


def family_of(model, policy=None):
    """(family, lineage) from the bare model id; unknown ids get `other:<vendor>`."""
    policy = policy or load_policy()
    low = split_model(model)[1].lower()
    for table in ("training_bound_families", "other_families"):
        for name, spec in policy[table].items():
            if re.search(spec["match"], low):
                return name, spec.get("lineage", name)
    vendor = "other:" + re.split(r"[/.]", low)[0]
    return vendor, vendor


def allowlist_status(model, policy=None) -> str:
    """'allowlisted' | 'outside-allowlist:<reason>' (recorded in provenance; never raises)."""
    try:
        check_allowed(model, True, policy, enforce=True)
        return "allowlisted"
    except ModelRefused as e:
        return f"outside-allowlist:{str(e).split(';')[0][:120]}"


def check_allowed(model, training_bound, policy=None, enforce=None):
    """In `enforce` mode, refuse non-allowlisted models for training-bound stages (dry/ never calls out, so it is
    exempt). In `record` mode (the default since 2026-10-25) this never raises."""
    policy = policy or load_policy()
    backend, bare = split_model(model)
    if enforce is None:
        enforce = policy.get("allowlist_mode", "enforce") == "enforce"
    if backend == "dry" or not training_bound or not enforce:
        return
    low = bare.lower()
    for pat in policy["refuse_when_training_bound"]:
        if re.search(pat, low):
            raise ModelRefused(f"{model} is refused for training-bound stages (matches `{pat}`); "
                               f"allowed families: {', '.join(policy['training_bound_families'])}")
    fam, _ = family_of(model, policy)
    if fam not in policy["training_bound_families"]:
        raise ModelRefused(f"{model}: family `{fam}` is not allowlisted for training-bound stages "
                           f"({', '.join(policy['training_bound_families'])})")


def check_critic(critic, drafters, policy=None):
    """The critic must come from a different model family (and lab lineage) than every drafter."""
    cf, cl = family_of(critic, policy)
    for d in drafters:
        df, dl = family_of(d, policy)
        if cf == df or cl == dl:
            raise ModelRefused(f"critic {critic} ({cf}/{cl}) shares a family with drafter {d} ({df}/{dl}); "
                               f"use a different family")


# --------------------------------------------------------------------------
# Backends: fn(bare_id, messages, temperature, max_tokens, ctx) -> (text, usage dict)
# --------------------------------------------------------------------------
def _post_json(url, headers, payload, timeout=300):
    """POST JSON; requests if it is installed, urllib otherwise. Retries 429/5xx and connection errors."""
    body = json.dumps(payload).encode()
    last = "no attempt"
    for i in range(4):
        try:
            try:
                import requests
                r = requests.post(url, headers=headers, data=body, timeout=timeout)
                status, text = r.status_code, r.text
            except ImportError:
                import urllib.error
                import urllib.request
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        status, text = resp.status, resp.read().decode()
                except urllib.error.HTTPError as e:
                    status, text = e.code, e.read().decode(errors="replace")
        except Exception as e:  # connection reset, timeout, DNS
            status, text = 0, f"{type(e).__name__}: {e}"
        if status == 200:
            return json.loads(text)
        last = f"HTTP {status}: {text[:300]}"
        if status not in (0, 429, 500, 502, 503, 504):
            break
        time.sleep(2 ** i)
    raise LLMError(f"OpenRouter request failed ({last})")


def _openrouter(bare, messages, temperature, max_tokens, ctx):
    extra = ctx.get("extra") or {}
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise LLMError("OPENROUTER_API_KEY is not set")
    payload = {"model": bare, "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
               "provider": {"data_collection": "deny"}, **extra}
    data = _post_json(OPENROUTER_URL, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, payload)
    try:
        ch = data["choices"][0]
        text = ch["message"]["content"] or ""
        ctx["stop_reason"] = ch.get("finish_reason")
        if ch["message"].get("refusal"):
            ctx["stop_reason"] = "refusal"
    except (KeyError, IndexError, TypeError):
        raise LLMError(f"unexpected OpenRouter response: {str(data)[:300]}")
    return text, data.get("usage") or {}


INSTANCE_ROLE_REGION = "us-east-1"


def _instance_role_session(boto3, region):
    """The EC2 instance role, only on explicit opt-in, only in us-east-1, only the expected role."""
    if region != INSTANCE_ROLE_REGION:
        raise LLMError(f"BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE is allowed only with region {INSTANCE_ROLE_REGION} (got {region})")
    want = os.environ.get("BENCHBOOK_AWS_INSTANCE_ROLE", "FiroInstanceRole")
    session = boto3.session.Session(region_name=region)
    creds = session.get_credentials()
    if creds is None or getattr(creds, "method", "") != "iam-role":
        raise LLMError(f"instance-role opt-in set, but credentials came from {getattr(creds, 'method', None)}; refusing")
    arn = session.client("sts").get_caller_identity()["Arn"]   # arn:aws:sts::<acct>:assumed-role/<role>/<instance>
    role = arn.split(":assumed-role/")[-1].split("/")[0] if ":assumed-role/" in arn else None
    if role != want:
        raise LLMError(f"instance role is `{role}`, expected `{want}` (BENCHBOOK_AWS_INSTANCE_ROLE); refusing")
    return session, f"instance-role:{role}"


def _bedrock(bare, messages, temperature, max_tokens, ctx):
    region, profile = os.environ.get("BENCHBOOK_AWS_REGION"), os.environ.get("BENCHBOOK_AWS_PROFILE")
    instance_role = os.environ.get("BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE") == "1"
    if not (region and (profile or instance_role)):
        raise LLMError("set BENCHBOOK_AWS_REGION and BENCHBOOK_AWS_PROFILE (or, on the EC2 box, "
                       "BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE=1); the default AWS credential chain is never used otherwise")
    try:
        import boto3
    except ImportError:
        raise LLMError("boto3 is not installed (pip install boto3)")
    if profile:
        try:
            session = boto3.session.Session(profile_name=profile, region_name=region)
            creds = session.get_credentials()
        except Exception as e:
            raise LLMError(f"AWS profile `{profile}` could not be loaded: {type(e).__name__}")
        if creds is None or getattr(creds, "method", "") in ("env", "iam-role", "container-role"):
            raise LLMError(f"profile `{profile}` did not resolve to its own credentials (got {getattr(creds, 'method', None)}); refusing")
        ctx["credential_source"] = f"profile:{profile}"
    else:
        session, ctx["credential_source"] = _instance_role_session(boto3, region)
    system = [{"text": m["content"]} for m in messages if m["role"] == "system"]
    convo = []
    for m in messages:
        if m["role"] == "system":
            continue
        if convo and convo[-1]["role"] == m["role"]:
            convo[-1]["content"].append({"text": m["content"]})
        else:
            convo.append({"role": m["role"], "content": [{"text": m["content"]}]})
    kwargs = {"system": system} if system else {}
    if ctx.get("extra"):    # e.g. gpt-oss {"reasoning_effort": "high"}
        kwargs["additionalModelRequestFields"] = ctx["extra"]
    resp = session.client("bedrock-runtime").converse(
        modelId=bare, messages=convo, inferenceConfig={"temperature": temperature, "maxTokens": max_tokens}, **kwargs)
    ctx["stop_reason"] = resp.get("stopReason")
    text = "".join(b.get("text", "") for b in (resp.get("output", {}).get("message", {}).get("content") or []))
    return text, resp.get("usage") or {}


def _dry(bare, messages, temperature, max_tokens, ctx):
    d = Path(ctx["dir"]) / "_dry"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{ctx['stage'] or 'call'}-{ctx['hash'][:10]}.prompt.md"
    path.write_text("\n\n".join(f"## {m['role']}\n\n{m['content']}" for m in messages) + "\n")
    ctx["dry_prompt"] = str(path)
    return f"```text\n[dry run: no model was called; the prompt is at {path}]\n```", {}


BACKENDS = {"openrouter": _openrouter, "bedrock": _bedrock, "dry": _dry}


# --------------------------------------------------------------------------
def prompt_hash(messages):
    return hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def complete(model, messages, temperature=0.7, max_tokens=4000, *, stage=None, out_path=None,
             training_bound=False, provenance=None, attempt=1, extra=None, refusal_check=True):
    """One chat completion. messages: [{role: system|user|assistant, content: str}]. Returns the text.
    Appends a provenance record to `provenance` (default: env BENCHBOOK_PROVENANCE or ./provenance.jsonl)."""
    check_allowed(model, training_bound)
    backend, bare = split_model(model)
    prov = Path(provenance or os.environ.get("BENCHBOOK_PROVENANCE") or "provenance.jsonl")
    prov.parent.mkdir(parents=True, exist_ok=True)
    fam, lineage = family_of(model)
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": model, "backend": backend,
           "family": fam, "lineage": lineage, "stage": stage, "training_bound": bool(training_bound),
           "attempt": attempt, "prompt_sha256": prompt_hash(messages), "out_path": str(out_path) if out_path else None,
           "temperature": temperature, "max_tokens": max_tokens, "allowlist": allowlist_status(model),
           **({"extra": extra} if extra else {})}
    ctx = {"stage": stage, "hash": rec["prompt_sha256"], "dir": prov.parent, "extra": extra}
    try:
        text, usage = BACKENDS[backend](bare, messages, temperature, max_tokens, ctx)
        rec["usage"] = usage
        if ctx.get("stop_reason"):
            rec["stop_reason"] = ctx["stop_reason"]
        reason = detect_refusal(text, ctx.get("stop_reason")) if refusal_check and backend != "dry" else None
        if reason:
            rec["refusal"] = True
            rec["refusal_reason"] = reason
            rec["reply_head"] = (text or "")[:200]
            raise RefusalError(reason, text, model, stage)
        if ctx.get("credential_source"):
            rec["credential_source"] = ctx["credential_source"]
        if ctx.get("dry_prompt"):
            rec["dry_prompt"] = ctx["dry_prompt"]
        return text
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        if isinstance(e, RefusalError) and REFUSAL_HOOK is not None:
            rec["refusal_hook"] = "invoked"
            alt = REFUSAL_HOOK(e, model, messages, ctx)      # T2 router; must record its own attempt
            if alt is not None:
                return alt
        raise
    finally:
        with open(prov, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a model id against the allowlist, or send it one prompt.\n\n" + __doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", help="openrouter/<id> | bedrock/<modelId> | dry/<anything>")
    ap.add_argument("--training-bound", action="store_true", help="apply the training-bound allowlist")
    ap.add_argument("--prompt", help="send this prompt and print the reply (otherwise only report family and allowlist status)")
    ap.add_argument("--provenance", help="provenance.jsonl path (default ./provenance.jsonl)")
    args = ap.parse_args(argv)
    try:
        fam, lin = family_of(args.model)
        check_allowed(args.model, args.training_bound)
        print(f"{args.model}: family {fam}, lineage {lin}, " + ("allowed for training-bound stages" if args.training_bound else "no training-bound check"))
        if args.prompt:
            print(complete(args.model, [{"role": "user", "content": args.prompt}], stage="cli",
                           training_bound=args.training_bound, provenance=args.provenance))
    except (LLMError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
