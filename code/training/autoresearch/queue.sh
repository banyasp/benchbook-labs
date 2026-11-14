#!/usr/bin/env bash
# Autoresearch queue runner (2026-11-14). Runs trials from the queue file one at a time until it is empty, then
# restarts the plain Granite vLLM server. Lines are appended while it runs (the loop in program.md decides the next
# trial from the last results); a line is moved to queue.done when its trial starts.
#
#   nohup bash code/training/autoresearch/queue.sh [wait_pid] > logs/autoresearch-queue.log 2>&1 &
#
# Queue line:  <name> | <desc> | <run_trial args, e.g. --set train.learning_rate=2e-4 [--full]>
# Lines starting with # are skipped. Create the file STOP next to the queue to stop after the current trial.
cd /home/ubuntu/benchbook-labs
export PYTHONPATH=code
Q=results/sft/autoresearch/queue.txt
DONE=results/sft/autoresearch/queue.done
STOP=results/sft/autoresearch/STOP
say() { echo "$(date -u +%FT%TZ) $*"; }
touch "$Q" "$DONE"
if [ -n "$1" ]; then say "waiting for pid $1"; while kill -0 "$1" 2>/dev/null; do sleep 60; done; fi
bash code/inference/serve.sh --stop >/dev/null 2>&1; bash code/inference/serve_compare.sh --stop >/dev/null 2>&1
sleep 15
say "vLLM stopped; GPU: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader)"
while true; do
  [ -f "$STOP" ] && { say "STOP file found"; break; }
  line=$(grep -v '^\s*#' "$Q" | grep -v '^\s*$' | head -1)
  [ -z "$line" ] && { say "queue empty"; break; }
  # move the line to queue.done before running, so a crash never re-runs it
  python3 - "$Q" "$line" <<'EOF'
import sys
p, line = sys.argv[1], sys.argv[2]
L = open(p).read().splitlines()
L.remove(line)
open(p, "w").write("".join(x + "\n" for x in L))
EOF
  echo "$(date -u +%FT%TZ) $line" >> "$DONE"
  name=$(echo "$line" | cut -d'|' -f1 | xargs); desc=$(echo "$line" | cut -d'|' -f2 | xargs)
  args=$(echo "$line" | cut -d'|' -f3-)
  say "start $name: $desc ($args)"
  eval .venv/bin/python -m training.autoresearch.run_trial --name "\"$name\"" --desc "\"$desc\"" $args
  say "end $name rc=$?"
done
bash code/inference/serve.sh && say "granite server restarted (no adapter)"
say "queue runner done"
