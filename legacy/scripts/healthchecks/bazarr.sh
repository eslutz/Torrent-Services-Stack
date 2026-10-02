#!/bin/sh
# Bazarr healthcheck - verify API health with fallback to web check
#
# Two-tier validation strategy:
# 1. Without API key (initial deployment):
#    - Service is running and responding
#    - Web interface returns HTTP 200

export SERVICE_NAME=bazarr
LOG_PATH=${LOG_PATH:-/logs/bazarr/healthcheck.log}
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null || true
SCRIPT_DIR="$(dirname "$0")"
. "$SCRIPT_DIR/healthcheck_utils.sh"

set -e

MAX_RESPONSE_TIME=$(resolve_max_response_time 8)

# If API key is available, use detailed health check
if [ -n "$BAZARR_API_KEY" ]; then
  HEALTH_URL="http://localhost:6767/api/system/status"

  START=$(date +%s)
  RESPONSE=$(wget -qO- --timeout=10 --header="X-Api-Key: $BAZARR_API_KEY" "$HEALTH_URL" 2>/dev/null || echo "")
  END=$(date +%s)

  if [ -z "$RESPONSE" ]; then
    log_event "error" "Bazarr API not responding"
    exit 1
  fi

  # Validate response contains expected JSON fields
  if ! echo "$RESPONSE" | grep -q "version"; then
    log_event "error" "Bazarr API returned invalid response"
    exit 1
  fi

  RESPONSE_TIME=$((END - START))
  if [ "$RESPONSE_TIME" -gt "$MAX_RESPONSE_TIME" ]; then
    log_event "error" "Bazarr API response too slow: ${RESPONSE_TIME}s (max ${MAX_RESPONSE_TIME}s)"
    exit 1
  fi

  log_event "healthy" "response_time=${RESPONSE_TIME}s (API check)"
else
  # Fallback to simple web interface check
  HEALTH_URL="http://localhost:6767/"

  START=$(date +%s)
  HTTP_CODE=$(wget --spider --server-response --timeout=10 "$HEALTH_URL" 2>&1 | grep "^  HTTP/" | tail -1 | awk '{print $2}' || echo "000")
  END=$(date +%s)

  if [ "$HTTP_CODE" != "200" ]; then
    log_event "error" "Bazarr not responding: HTTP $HTTP_CODE"
    exit 1
  fi

  RESPONSE_TIME=$((END - START))
  if [ "$RESPONSE_TIME" -gt "$MAX_RESPONSE_TIME" ]; then
    log_event "error" "Bazarr response too slow: ${RESPONSE_TIME}s (max ${MAX_RESPONSE_TIME}s)"
    exit 1
  fi

  log_event "healthy" "response_time=${RESPONSE_TIME}s (web check)"
fi


exit 0
