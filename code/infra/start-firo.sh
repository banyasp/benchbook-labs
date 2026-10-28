#!/usr/bin/env bash
# Keep trying to start the "firo" GPU instance until AWS has capacity (2026-10-28).
#
#   bash start-firo.sh                              # try g6e.2xlarge every 30 s
#   bash start-firo.sh g6e.12xlarge g6e.2xlarge     # try these types in order each round (first = preferred)
#   INTERVAL=20 bash start-firo.sh ...              # change the wait between rounds
#   caffeinate -i bash start-firo.sh ...            # macOS: keep the laptop awake while it runs
#
# Needs the AWS CLI on this machine, signed in with permission to describe, start and modify the instance.
# Changing the instance type is only possible while it is stopped, which it is between failed attempts.
# The Elastic IP stays attached across stop/start, so the address doesn't change.
set -u
INSTANCE_ID="${INSTANCE_ID:-i-0cd27fbbd4cbb7ee5}"
REGION="${REGION:-us-east-1}"
INTERVAL="${INTERVAL:-30}"
TYPES=("$@")
[ ${#TYPES[@]} -eq 0 ] && TYPES=(g6e.2xlarge)

aws_ec2() { aws ec2 --region "$REGION" "$@"; }
field() { aws_ec2 describe-instances --instance-ids "$INSTANCE_ID" --query "Reservations[0].Instances[0].$1" --output text 2>/dev/null; }
notify() {
  echo "$(date +%T)  $1"
  command -v osascript >/dev/null && osascript -e "display notification \"$1\" with title \"firo\" sound name \"Glass\"" >/dev/null 2>&1
  command -v say >/dev/null && say "$1" >/dev/null 2>&1 &
}
done_ok() {
  local ip type
  ip=$(field PublicIpAddress); type=$(field InstanceType)
  notify "firo is running as $type at $ip"
  exit 0
}

command -v aws >/dev/null || { echo "The AWS CLI isn't installed (brew install awscli), or isn't on PATH."; exit 1; }
aws sts get-caller-identity >/dev/null 2>&1 || { echo "The AWS CLI isn't signed in (aws configure, or aws sso login)."; exit 1; }

echo "Trying to start $INSTANCE_ID in $REGION as: ${TYPES[*]} (every ${INTERVAL}s; Ctrl-C to stop)"
round=0
while true; do
  round=$((round + 1))
  state=$(field State.Name)
  case "$state" in
    running) done_ok ;;
    pending) echo "$(date +%T)  pending; waiting for running"
             aws_ec2 wait instance-running --instance-ids "$INSTANCE_ID" 2>/dev/null && done_ok
             continue ;;
    stopping|shutting-down) echo "$(date +%T)  $state; waiting"; sleep 10; continue ;;
    stopped) ;;
    *) echo "$(date +%T)  unexpected state '$state'; retrying"; sleep "$INTERVAL"; continue ;;
  esac

  for t in "${TYPES[@]}"; do
    cur=$(field InstanceType)
    if [ "$cur" != "$t" ]; then
      if ! out=$(aws_ec2 modify-instance-attribute --instance-id "$INSTANCE_ID" --instance-type "{\"Value\": \"$t\"}" 2>&1); then
        echo "$(date +%T)  round $round  $t: couldn't switch type: $(echo "$out" | tail -1)"; continue
      fi
    fi
    if out=$(aws_ec2 start-instances --instance-ids "$INSTANCE_ID" 2>&1); then
      echo "$(date +%T)  round $round  $t: start accepted; waiting for it to come up"
      # Capacity can still fail after the API accepts: the instance goes pending -> stopped.
      for _ in $(seq 1 24); do
        sleep 5
        s=$(field State.Name)
        [ "$s" = running ] && done_ok
        [ "$s" = stopped ] && { echo "$(date +%T)  $t: went back to stopped ($(field StateReason.Message))"; break; }
      done
    elif echo "$out" | grep -q InsufficientInstanceCapacity; then
      echo "$(date +%T)  round $round  $t: no capacity"
    elif echo "$out" | grep -qE "VcpuLimitExceeded|InstanceLimitExceeded"; then
      echo "$(date +%T)  round $round  $t: over your vCPU quota for G instances (request an increase in Service Quotas)"
    elif echo "$out" | grep -q IncorrectInstanceState; then
      echo "$(date +%T)  round $round  $t: instance not in a startable state yet"
    else
      echo "$(date +%T)  round $round  $t: $(echo "$out" | tail -1)"
    fi
  done
  sleep "$INTERVAL"
done
