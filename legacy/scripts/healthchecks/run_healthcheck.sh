#!/bin/sh
# Wrapper to run service healthchecks with automatic service name detection
# Usage: run_healthcheck.sh /scripts/<service>.sh [test-email]

if [ -z "$1" ]; then
  echo "Usage: $0 /path/to/healthcheck.sh [test-email]"
  exit 2
fi

TARGET_SCRIPT="$1"

# Derive service name from target script filename
SERVICE_NAME=$(basename "$TARGET_SCRIPT" .sh)

# Default log path inside container (centralized logs directory)
LOG_DIR="/logs/${SERVICE_NAME}"
mkdir -p "$LOG_DIR" 2>/dev/null || true
LOG_PATH="${LOG_DIR}/healthcheck.log"

SCRIPT_DIR="$(dirname "$0")"

# Export so sourced utils can use them
export SERVICE_NAME LOG_PATH

# Source shared utilities
if [ -f "$SCRIPT_DIR/healthcheck_utils.sh" ]; then
  . "$SCRIPT_DIR/healthcheck_utils.sh"
else
  echo "healthcheck_utils.sh not found in $SCRIPT_DIR" >&2
fi

# If asked, just send a test email and exit
if [ "${2:-}" = "test-email" ]; then
  send_email "${SERVICE_NAME} healthcheck test" "This is a test email from ${SERVICE_NAME} healthcheck_wrapper"
  exit 0
fi

# Centralized retry/backoff for healthchecks
MAX_RETRIES=${MAX_RETRIES:-3}
BACKOFF_BASE=${BACKOFF_BASE:-2}
RETRY=0

run_probe() {
  # Run target script and return its exit code
  sh "$TARGET_SCRIPT"
  return $?
}

while [ "$RETRY" -le "$MAX_RETRIES" ]; do
  run_probe
  CODE=$?
  if [ "$CODE" -eq 0 ]; then
    log_event "healthy" "Healthcheck passed (attempt $RETRY)"
    exit 0
  fi

  # Non-zero means unhealthy or remediation requested
  log_event "probe_failed" "Healthcheck probe returned $CODE (attempt $RETRY)"
  RETRY=$((RETRY+1))
  if [ "$RETRY" -le "$MAX_RETRIES" ]; then
    # POSIX sh compatible: BACKOFF_BASE^RETRY via loop
    SLEEP_TIME=1
    i=0
    while [ "$i" -lt "$RETRY" ]; do
      SLEEP_TIME=$((SLEEP_TIME * BACKOFF_BASE))
      i=$((i + 1))
    done
    log_event "backoff" "Sleeping ${SLEEP_TIME}s before retry"
    sleep "$SLEEP_TIME"
  fi
done

log_event "unhealthy" "Max retries reached ($MAX_RETRIES); reporting unhealthy"
exit 1
