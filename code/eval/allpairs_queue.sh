#!/bin/bash
# Run the all-pairs grids one after another on the local vLLM server, each to completion:
#   grid (X1 x X2 + k control samples) -> confirm (one random successful X2 != X1 per X1, k fresh samples)
#   -> report.md + matrix.csv + per_x1.csv -> figures -> commit + push (samples, report, figures; raw replies stay on the box).
# A run whose grid process is already running (e.g. B2) is waited for, not restarted. Resumable: re-running this script
# skips samples already in each run's samples.jsonl.
#
#   nohup bash code/eval/allpairs_queue.sh B2 C1 D1 > logs/allpairs-queue.log 2>&1 &
set -u
cd "$(dirname "$0")/../.."
export PYTHONPATH=code
PY=.venv/bin/python
for RUN in "$@"; do
  D=results/allpairs/$RUN
  echo "=== $RUN $(date -u +%FT%TZ)"
  if pgrep -f "eval.allpairs run --run $D" >/dev/null; then
    echo "grid already running; waiting"
    while pgrep -f "eval.allpairs run --run $D" >/dev/null; do sleep 60; done
  fi
  if [ -f "$D/config.json" ]; then
    $PY -m eval.allpairs run --run "$D" --concurrency 24 >> "$D/run.log" 2>&1        # finishes anything left
  else
    $PY -m eval.allpairs run --run "$D" --x1 "$D/x1.txt" -k 8 --max-tokens 12000 --concurrency 24 >> "$D/run.log" 2>&1
  fi
  echo "grid done $(date -u +%FT%TZ)"
  $PY -m eval.allpairs confirm --run "$D" --concurrency 24 >> "$D/run.log" 2>&1
  echo "confirm done $(date -u +%FT%TZ)"
  $PY -m eval.allpairs_report --run "$D" > /dev/null
  $PY -m eval.allpairs_plots --run "$D"
  # raw replies and judge matrices stay on the box (.gitignore); only samples, reports and figures are committed
  git add "$D/config.json" "$D/x1.txt" "$D/samples.jsonl" "$D/report.md" "$D/matrix.csv" "$D/per_x1.csv" \
          "$D/figures" "$D"/manifest.*.json "$D"/confirm-picks.*.json 2>/dev/null
  [ -f "$D/x2.txt" ] && git add "$D/x2.txt"
  [ -d "$D/versions" ] && git add "$D/versions"
  git commit -q -m "All-pairs grid $RUN complete: grid + confirm, report and figures

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q
  echo "=== $RUN committed $(date -u +%FT%TZ)"
done
echo "QUEUE DONE $(date -u +%FT%TZ)"
