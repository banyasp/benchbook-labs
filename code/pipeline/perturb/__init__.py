"""2f P2 perturb: restyle, flip, add_fact. Each op(X, store, rng) -> (X', partial); partial = gold M_{C,T} etc.

`PairRecord(id=..., **partial)` is valid once an id is added (pair/ does that). Run: python -m pipeline.perturb --help
"""
from .add_fact import add_fact
from .common import OperatorError, set_complete
from .flip import flip
from .io import load_partial, save_result
from .restyle import restyle

OPERATORS = {"restyle": restyle, "flip": flip, "add_fact": add_fact}
__all__ = ["restyle", "flip", "add_fact", "OPERATORS", "OperatorError", "set_complete", "save_result", "load_partial"]
