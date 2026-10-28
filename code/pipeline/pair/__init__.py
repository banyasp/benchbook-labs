"""pair (3c): all arms, balance, distance, gate. python -m pipeline.pair build|stats|gate-augmented|sync-traces|housekeeping-2f"""
from .build import build, pair_id, stats
from .channels import assign_channels, assign_recommended, assign_trace_plan
from .gate import gate_augmented
from .reorder import reorder          # retired in v2.4 (kept for the legacy records); build no longer calls it

__all__ = ["build", "stats", "pair_id", "reorder", "assign_channels", "assign_recommended", "assign_trace_plan", "gate_augmented"]
