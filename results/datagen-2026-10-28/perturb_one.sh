#!/usr/bin/env bash
# All perturb ops for one source scenario, in order; one log per scenario.
sid="$1"; log="results/datagen-2026-10-28/logs/perturb-${sid//[@\/]/_}.log"
P=".venv/bin/python -m pipeline.perturb"
items=$(.venv/bin/python -c "
import random,sys; from pipeline.store import Store
X=Store().scenario('$sid'); ids=[w.id for w in X.case.flip_conditions.would_change]
random.Random('$sid').shuffle(ids); print(' '.join(ids[:2]))")
{
  $P restyle --scenario "$sid" || echo "FAIL restyle $sid"
  for it in $items; do $P flip --scenario "$sid" --item "$it" || echo "FAIL flip $it $sid"; done
  $P add-fact --scenario "$sid" || echo "FAIL add_fact $sid"
  $P revise-card --scenario "$sid" || echo "FAIL revise_card $sid"
} > "$log" 2>&1
echo "done $sid: $(grep -c '^restyle:\|^flip:\|^add_fact:\|^revise_card:' "$log") ok, $(grep -c '^FAIL' "$log") failed"
