"""Print one perturb job line per (scenario): the ops for that scenario, run in order (v2.4 batch step 2).
Per train/test source scenario (not legacy-2f, not eval-only imports, not held-out natsec): restyle, flip on up to 2
would_change items (seeded pick), add_fact, revise_card. Lines: <scenario id>"""
import random
import sys

from pipeline.store import Store

splits = sys.argv[1].split(",") if len(sys.argv) > 1 else ["train", "test"]
for s in Store().scenarios():
    if s.lineage.parent or s.split not in splits or "legacy-2f" in s.tags or s.held_out:
        continue
    print(s.id)
