"""HarnessSettings: every knob of the harness in one value, so an eval run can log it and 2e can grid over it."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Literal

Mode = Literal["A", "B", "C", "Cprime"]
MODES = ("A", "B", "C", "Cprime")


@dataclass(frozen=True)
class HarnessSettings:
    mode: Mode = "B"                        # A thinking on | B thinking off | C structure inside <think> | Cprime C + prose
    analogical_prompt: bool = False         # add prompts/analogical.<ver>.md to the injection (cased arms only)
    injection_role: str = "user"            # role of the harness message (TRACE-FORMAT: user)
    injection_name: str = "benchbook"
    tool_messages: Literal["flattened", "native"] = "flattened"
    max_tokens: int | None = None           # None -> role("policy").get("max_tokens")
    seed: int | None = None                 # None -> role("policy").get("seed") (usually unset = random)
    temperature: float | None = None        # None -> role params (1.0, IBM's recommendation)
    top_p: float | None = None
    format_spec: str = "v1"                 # prompts/format.<v>.md
    format_variant: Literal["schema", "example"] = "schema"   # "example" -> prompts/format.<v>-example.md (optional file)
    analogical_version: str = "v1"
    modes_version: str = "v1"
    instructions_in: Literal["injection", "system"] = "injection"   # where format/method text goes
    model: str | None = None                # served-model-name override on the same server: "sft" = the LoRA adapter
    tokenizer: str = "ibm-granite/granite-4.2-8b"

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {self.mode!r}")

    def with_(self, **kw) -> "HarnessSettings":
        return replace(self, **kw)

    def to_dict(self) -> dict:
        return asdict(self)
