"""condition_holds: the strict condition verifier (the flip's model check), public so pair/render (W2) can run it on
X' back-flip `if` text against X's rendered trace. Behaviour unchanged: same prompt (verify_condition.md), same strictness.
"""
from __future__ import annotations

from .common import Ctx, OperatorError, complete, parse_json


def fact_lines(facts) -> str:
    return "\n".join(f"{f['id']} [{f['kind']}, {f['status']}]: {f['fact']}" for f in facts)


def _text(x) -> str:
    if isinstance(x, str):
        return x
    case = getattr(x, "case", x)                       # Scenario -> Case
    if hasattr(case, "dump"):
        case = case.dump()
    if isinstance(case, dict) and "facts" in case:
        return fact_lines(case["facts"])
    raise TypeError("trace_text_or_scenario must be a string, a Scenario/Case or a dict with `facts`")


def condition_holds(if_text: str, trace_text_or_scenario, *, ctx: Ctx | None = None, role: str = "perturber", tries: int = 2,
                    step_id: str = "flip.verify") -> dict:
    """-> {"holds": bool, "why": str}. Strict: true only when a careful reader must conclude the condition from the
    given text (a rendered trace, a scenario's facts, or any string). Raises OperatorError if the check cannot run."""
    user = "FACTS:\n" + _text(trace_text_or_scenario) + f"\n\nCONDITION: {if_text}"
    if ctx is not None:
        v, _ = ctx.ask(role, "verify", "verify_condition", user, lambda o: _check(o), tries=tries, step_id=step_id)
        return v
    from .common import prompt
    sys_text, _ = prompt("verify_condition")
    msgs = [{"role": "system", "content": sys_text}, {"role": "user", "content": user}]
    last = None
    for _ in range(tries):
        try:
            return _check(parse_json(complete(role, msgs, stage="perturb.condition_holds")))
        except ValueError as e:
            last = e
    raise OperatorError(f"condition_holds: no valid reply after {tries} attempts: {last}")


def _check(o):
    if not isinstance(o, dict) or not isinstance(o.get("holds"), bool):
        raise ValueError('reply must be {"holds": true|false, "why": "..."}')
    return o
