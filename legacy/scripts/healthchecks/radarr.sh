#!/bin/sh
# Radarr healthcheck - verify API health with fallback to ping
#
# Two-tier validation strategy:
# 1. Without API key (initial deployment):
#    - Service is running and responding
#
export SERVICE_NAME=radarr
LOG_PATH=${LOG_PATH:-/logs/radarr/healthcheck.log}
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null || true
SCRIPT_DIR="$(dirname "$0")"
. "$SCRIPT_DIR/healthcheck_utils.sh"

set -e

MAX_RESPONSE_TIME=$(resolve_max_response_time 8)

# If API key is available, use detailed health check
if [ -n "$RADARR_API_KEY" ]; then
  HEALTH_URL="http://localhost:7878/api/v3/health"

  START=$(date +%s)
  RESPONSE=$(wget -qO- --timeout=10 --header="X-Api-Key: $RADARR_API_KEY" "$HEALTH_URL" 2>/dev/null || echo "")
  END=$(date +%s)

  if [ -z "$RESPONSE" ]; then
    log_event "error" "Radarr API not responding"
    exit 1
  fi

  # Check for error or warning conditions
  if echo "$RESPONSE" | grep -q '"type":"error"'; then
    log_event "error" "Radarr health check failed: service reported errors"
    exit 1
  fi

  RESPONSE_TIME=$((END - START))
  if [ "$RESPONSE_TIME" -gt "$MAX_RESPONSE_TIME" ]; then
    log_event "error" "Radarr API response too slow: ${RESPONSE_TIME}s (max ${MAX_RESPONSE_TIME}s)"
    exit 1
  fi

  log_event "healthy" "response_time=${RESPONSE_TIME}s (API check)"
else
  # Fallback to simple ping check
  HEALTH_URL="http://localhost:7878/ping"

  START=$(date +%s)
  RESPONSE=$(wget -qO- --timeout=10 "$HEALTH_URL" 2>/dev/null || echo "")
  END=$(date +%s)

  if [ -z "$RESPONSE" ]; then
    log_event "error" "Radarr not responding"
    exit 1
  fi

  if ! echo "$RESPONSE" | grep -q '"status".*:.*"OK"'; then
    log_event "error" "Radarr returned invalid response: $RESPONSE"
    exit 1
  fi

  RESPONSE_TIME=$((END - START))
  if [ "$RESPONSE_TIME" -gt "$MAX_RESPONSE_TIME" ]; then
    log_event "error" "Radarr response too slow: ${RESPONSE_TIME}s (max ${MAX_RESPONSE_TIME}s)"
    exit 1
  fi

  log_event "healthy" "response_time=${RESPONSE_TIME}s (ping check)"
fi

exit 0
