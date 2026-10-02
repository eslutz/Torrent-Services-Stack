#!/bin/sh
# Tdarr healthcheck - verify API health and responsiveness
#
# Validates that Tdarr server API is enabled and responding on port 8266
# Falls back to web UI check if API is not available

export SERVICE_NAME=tdarr
LOG_PATH=${LOG_PATH:-/logs/tdarr/healthcheck.log}
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null || true
SCRIPT_DIR="$(dirname "$0")"
. "$SCRIPT_DIR/healthcheck_utils.sh"

set -e

MAX_RESPONSE_TIME=$(resolve_max_response_time 8)

# Try API endpoint first (port 8266)
API_URL="http://localhost:8266/api/v2/status"
WEBUI_URL="http://localhost:8265"

START=$(date +%s)
RESPONSE=$(wget -qO- --timeout=10 "$API_URL" 2>/dev/null || echo "")
END=$(date +%s)

if [ -n "$RESPONSE" ]; then
  # API is available - check response
  if ! echo "$RESPONSE" | grep -q '"status"'; then
    log_event "error" "Tdarr API returned invalid response"
    exit 1
  fi

  RESPONSE_TIME=$((END - START))
  if [ "$RESPONSE_TIME" -gt "$MAX_RESPONSE_TIME" ]; then
    log_event "error" "Tdarr API response too slow: ${RESPONSE_TIME}s (max ${MAX_RESPONSE_TIME}s)"
    exit 1
  fi

  log_event "healthy" "response_time=${RESPONSE_TIME}s (API check)"
else
  # API not available, try web UI
  START=$(date +%s)
  if wget --spider --timeout=10 "$WEBUI_URL" 2>/dev/null; then
    END=$(date +%s)
    RESPONSE_TIME=$((END - START))

    if [ "$RESPONSE_TIME" -gt "$MAX_RESPONSE_TIME" ]; then
      log_event "error" "Tdarr web UI response too slow: ${RESPONSE_TIME}s (max ${MAX_RESPONSE_TIME}s)"
      exit 1
    fi

    log_event "healthy" "response_time=${RESPONSE_TIME}s (web UI check)"
  else
    log_event "error" "Tdarr not responding on API or web UI"
    exit 1
  fi
fi

exit 0
