"""2f P2 pair: derived pairs + decoys from the store, balanced (hand-up cap, gold option positions). python -m pipeline.pair build|stats"""
from .build import build, pair_id, stats
from .reorder import reorder

__all__ = ["build", "stats", "pair_id", "reorder"]
