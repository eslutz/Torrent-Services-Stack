#!/bin/sh
# qBittorrent healthcheck - verify web UI is responding
#
# Validates:
#  - Service is running and responding
#  - Web UI accessible (returns HTTP 200 or 403)

export SERVICE_NAME=qbittorrent
LOG_PATH=${LOG_PATH:-/logs/qbittorrent/healthcheck.log}
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null || true
SCRIPT_DIR="$(dirname "$0")"
. "$SCRIPT_DIR/healthcheck_utils.sh"

set -e

MAX_RESPONSE_TIME=$(resolve_max_response_time 8)

# qBittorrent requires auth but we check if port is listening and responsive
# A 403 response means service is running (just requires auth)
START=$(date +%s)
HTTP_CODE=$(wget --spider --server-response --timeout=10 http://localhost:8080/api/v2/app/version 2>&1 | grep "^  HTTP/" | tail -1 | awk '{print $2}' || echo "000")
END=$(date +%s)

# Accept 200 (success) or 403 (requires auth but service is running)
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "403" ]; then
  log_event "error" "qBittorrent not responding or returning error: HTTP $HTTP_CODE"
  exit 1
fi

# Check response time
RESPONSE_TIME=$((END - START))
if [ "$RESPONSE_TIME" -gt "$MAX_RESPONSE_TIME" ]; then
  log_event "error" "qBittorrent response too slow: ${RESPONSE_TIME}s (max ${MAX_RESPONSE_TIME}s)"
  exit 1
fi

log_event "healthy" "response_time=${RESPONSE_TIME}s, http_code=$HTTP_CODE"
exit 0
