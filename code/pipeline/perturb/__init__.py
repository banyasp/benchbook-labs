"""2f P2 perturb: restyle, flip, add_fact, revise_card. Each op(X, store, rng) -> (X', partial); partial = gold M_{C,T} etc.

`PairRecord(id=..., **partial)` is valid once an id is added (pair/ does that). Run: python -m pipeline.perturb --help
"""
from .add_fact import add_fact
from .common import OperatorError, RefusalError, set_complete
from .condition import condition_holds
from .revise_card import revise_card
from .flip import flip
from .io import load_partial, save_result
from .restyle import restyle

OPERATORS = {"restyle": restyle, "flip": flip, "add_fact": add_fact, "revise_card": revise_card}
__all__ = ["restyle", "flip", "add_fact", "revise_card", "condition_holds", "RefusalError", "OPERATORS", "OperatorError", "set_complete", "save_result", "load_partial"]
