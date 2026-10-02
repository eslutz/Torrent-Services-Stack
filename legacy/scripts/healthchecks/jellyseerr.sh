#!/bin/sh
# Jellyseerr healthcheck - verify API health and responsiveness
#
# Validates that Jellyseerr is responding on port 5055

export SERVICE_NAME=jellyseerr
LOG_PATH=${LOG_PATH:-/logs/jellyseerr/healthcheck.log}
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null || true
SCRIPT_DIR="$(dirname "$0")"
. "$SCRIPT_DIR/healthcheck_utils.sh"

set -e

MAX_RESPONSE_TIME=$(resolve_max_response_time 8)

# Check status endpoint
STATUS_URL="http://localhost:5055/api/v1/status"

START=$(date +%s)
RESPONSE=$(wget -qO- --timeout=10 "$STATUS_URL" 2>/dev/null || echo "")
END=$(date +%s)

if [ -z "$RESPONSE" ]; then
  log_event "error" "Jellyseerr not responding"
  exit 1
fi

# Check for valid JSON response with version field
if ! echo "$RESPONSE" | grep -q '"version"'; then
  log_event "error" "Jellyseerr returned invalid response: $RESPONSE"
  exit 1
fi

RESPONSE_TIME=$((END - START))
if [ "$RESPONSE_TIME" -gt "$MAX_RESPONSE_TIME" ]; then
  log_event "error" "Jellyseerr response too slow: ${RESPONSE_TIME}s (max ${MAX_RESPONSE_TIME}s)"
  exit 1
fi

log_event "healthy" "response_time=${RESPONSE_TIME}s (API check)"

exit 0
