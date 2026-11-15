#!/usr/bin/env bash
# 2026-11-15 (R98, Peter): rescore every allpairs-scoring-v3 run with v4 (option exact-text pre-pass).
# Each run's details/ is copied to versions/details-scoring-v3 first; rescore_run copies samples.jsonl to versions/.
cd /home/ubuntu/benchbook-labs
export PYTHONPATH=code
for f in $(find results -name samples.jsonl -not -path "*/versions/*" | sort); do
  d=$(dirname "$f")
  v=$(head -1 "$f" | python3 -c "import sys,json;print((json.loads(sys.stdin.read()).get('scoring') or {}).get('version'))" 2>/dev/null)
  [ "$v" = "allpairs-scoring-v3" ] || continue
  mkdir -p "$d/versions"; [ -d "$d/versions/details-scoring-v3" ] || cp -r "$d/details" "$d/versions/details-scoring-v3"
  echo "== $d"; .venv/bin/python -m eval.allpairs rescore --run "$d" | python3 -c "import sys,json;d=json.load(sys.stdin);d.pop('scoring');print(json.dumps(d))"
done
