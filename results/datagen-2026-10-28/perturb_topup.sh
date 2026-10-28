#!/usr/bin/env bash
# v2.4 batch step 2b: re-run only the missing perturb ops per source scenario (after the structural-retry and Φ-count
# repairs), and the full op set on the held-out natsec scenarios. 8 scenarios in parallel.
cd "$(dirname "$0")/../.."
. ~/.config/benchbook/env; export PYTHONPATH=code BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE=1
.venv/bin/python - <<'PY' > results/datagen-2026-10-28/topup-jobs.txt
import random
from collections import defaultdict
from pipeline.store import Store
st = Store(); sc = st.scenarios()
kids = defaultdict(list)
for s in sc:
    if s.lineage.parent and "legacy-2f" not in s.tags:
        kids[s.lineage.parent].append(s)
for s in sc:
    if s.lineage.parent or s.split not in ("train", "test") or "legacy-2f" in s.tags:
        continue
    ops = {k.lineage.operator for k in kids[s.id]}
    fired = {str((k.lineage.detail or {}).get("via", "")).split("/")[-1] for k in kids[s.id] if k.lineage.operator == "flip"}
    ids = [w.id for w in s.case.flip_conditions.would_change]; random.Random(s.id).shuffle(ids)
    jobs = [] if "restyle" in ops else ["restyle"]
    jobs += [f"flip:{i}" for i in ids[:2] if i not in fired and sum(k.lineage.operator == "flip" for k in kids[s.id]) < min(2, len(ids))]
    jobs += [] if "add_fact" in ops else ["add_fact"]
    jobs += [] if "revise_card" in ops else ["revise_card"]
    if jobs:
        print(s.id, " ".join(jobs))
PY
wc -l < results/datagen-2026-10-28/topup-jobs.txt
cat results/datagen-2026-10-28/topup-jobs.txt | xargs -P 8 -L 1 bash -c '
sid="$0"; log="results/datagen-2026-10-28/logs/topup-${sid//[@\/]/_}.log"; P=".venv/bin/python -m pipeline.perturb"
for j in "$@"; do case "$j" in
  restyle) $P restyle --scenario "$sid" ;; add_fact) $P add-fact --scenario "$sid" ;;
  revise_card) $P revise-card --scenario "$sid" ;; flip:*) $P flip --scenario "$sid" --item "${j#flip:}" ;;
esac >> "$log" 2>&1 || echo "FAIL $j $sid" >> "$log"; done
echo "done $sid: $(grep -c "^FAIL" "$log") failed of $#"'
