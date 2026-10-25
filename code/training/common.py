"""Shared bits of the training scripts: policy model resolution (via bench.models only), tiny CPU smoke model,
smoke data."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TOKENIZER_FOR_SMOKE_ROLE = "policy"


def load_config(path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def policy_hf_id(cfg: dict, role_name: str = "policy") -> str:
    """HF repo id of the model the role serves. Model ids come from `bench.models.role` only: the role gives the
    served name (e.g. vllm/granite-4.2-8b); the HF id is looked up in this order:
      1. role param `hf_id` (suggested addition to config/models.yaml, not present today),
      2. cfg["hf_ids"][<served name>] (the training config's one-line map),
    and training fails loudly if neither exists (no silent default model)."""
    from bench.models import role
    r = role(role_name)
    if r.get("hf_id"):
        return r.get("hf_id")
    m = (cfg.get("hf_ids") or {}).get(r.bare)
    if not m:
        raise KeyError(f"no HF id for role `{role_name}` model `{r.model}`: add `hf_id:` to its role in "
                       f"config/models.yaml or `{r.bare}: <org/name>` under hf_ids in the training config")
    return m


def load_tokenizer(name: str):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(name)


def tiny_model(vocab_size: int, seed: int = 0):
    """A random 2-layer Granite (same architecture and chat-template tokenizer as the policy), ~7M parameters,
    built from a config: no download, runs on CPU."""
    import torch
    from transformers import GraniteConfig, GraniteForCausalLM
    torch.manual_seed(seed)
    cfg = GraniteConfig(vocab_size=vocab_size, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                        num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=4096,
                        tie_word_embeddings=False)
    return GraniteForCausalLM(cfg).float()


def smoke_golden(tokenizer, n: int = 4) -> list[dict]:
    """Synthetic golden records for CPU smokes: a short chat-templated prompt + the PDF journalist reply.
    (Test fixtures only; never training data.)"""
    fx = Path(__file__).resolve().parents[1] / "bench" / "fixtures" / "pdf_example"
    reply = (fx / "journalist.reply.yaml").read_text()
    reply = reply[reply.index("kind: fact_enumeration"):]      # drop the fixture's comment header
    out = []
    for i in range(n):
        msgs = [{"role": "system", "content": "EQUITIES: civilian_life, mission_effect (smoke)"},
                {"role": "user", "content": f"TRACE {i}: a decision point.\nCASE REF1: ...\nDecide."}]
        prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        out.append({"id": f"smoke-{i}", "prompt_text": prompt, "prefill": "", "completion": reply, "meta": {}})
    return out


def force_cpu():
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
