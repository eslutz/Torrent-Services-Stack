#!/bin/sh
# Shared utilities for healthcheck scripts
# Provides: log_event(), send_notification()

# Email configuration (SMTP via msmtp)
EMAIL_TO=${EMAIL_TO:-}
SMTP_HOST=${SMTP_HOST:-smtp.mail.me.com}
SMTP_PORT=${SMTP_PORT:-587}
SMTP_USER=${SMTP_USER:-}
SMTP_PASSWORD=${SMTP_PASSWORD:-}
SMTP_FROM=${SMTP_FROM:-}

# Rate limiting configuration
NOTIFICATION_COOLDOWN=${NOTIFICATION_COOLDOWN:-300}  # 5 minutes default
NOTIFICATION_STATE_DIR=${NOTIFICATION_STATE_DIR:-/tmp/notification_state}
mkdir -p "$NOTIFICATION_STATE_DIR" 2>/dev/null || true

# Log rotation configuration
LOG_KEEP_ROTATIONS=${LOG_KEEP_ROTATIONS:-7}  # Keep logs for N days

resolve_max_response_time() {
  DEFAULT_VALUE="$1"

  if [ -n "${MAX_RESPONSE_TIME:-}" ]; then
    echo "$MAX_RESPONSE_TIME"
    return 0
  fi

  case "${HEALTHCHECK_TIMEOUT_SECONDS:-}" in
    ''|*[!0-9]*)
      echo "$DEFAULT_VALUE"
      return 0
      ;;
  esac

  CALC=$((HEALTHCHECK_TIMEOUT_SECONDS / 3))
  if [ "$CALC" -lt 1 ]; then
    CALC=1
  fi

  echo "$CALC"
  return 0
}

get_dated_log_file() {
  LOG_FILE="$1"
  TODAY=$(date '+%Y.%m.%d')
  LOG_DIR=$(dirname "$LOG_FILE")
  LOG_BASE=$(basename "$LOG_FILE" .log)
  echo "${LOG_DIR}/${LOG_BASE}-${TODAY}.log"
}

rotate_log_if_needed() {
  LOG_FILE="$1"

  # Get today's date-based log file
  TODAY=$(date '+%Y.%m.%d')
  LOG_DIR=$(dirname "$LOG_FILE")
  LOG_BASE=$(basename "$LOG_FILE" .log)
  DATED_LOG="${LOG_DIR}/${LOG_BASE}-${TODAY}.log"

  # Create dated log file if it doesn't exist
  if [ ! -f "$DATED_LOG" ]; then
    touch "$DATED_LOG"

    # Clean up old logs beyond retention period
    if [ "$LOG_KEEP_ROTATIONS" -gt 0 ]; then
      find "$LOG_DIR" -name "${LOG_BASE}-*.log" -type f -mtime +"$LOG_KEEP_ROTATIONS" -delete 2>/dev/null || true
    fi
  fi

  # Return the dated log file path
  echo "$DATED_LOG"
}

log_event() {
  EVENT="$(date '+%Y-%m-%d %H:%M:%S %Z') {\"service\": \"${SERVICE_NAME:-unknown}\", \"event\": \"$1\", \"details\": \"$2\"}"
  if [ -n "${LOG_PATH:-}" ]; then
    DATED_LOG=$(rotate_log_if_needed "$LOG_PATH")
    echo "$EVENT" >> "$DATED_LOG"
  fi
  echo "$EVENT"
  if [ "$1" = "error" ] || [ "$1" = "unhealthy" ]; then
    send_notification "${SERVICE_NAME:-healthcheck} health: $1" "$2"
  fi
}

should_send_notification() {
  NOTIFICATION_KEY="$1"
  STATE_FILE="${NOTIFICATION_STATE_DIR}/${NOTIFICATION_KEY}"
  CURRENT_TIME=$(date +%s)

  # Check if notification was recently sent
  if [ -f "$STATE_FILE" ]; then
    LAST_SENT=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
    TIME_DIFF=$((CURRENT_TIME - LAST_SENT))

    if [ "$TIME_DIFF" -lt "$NOTIFICATION_COOLDOWN" ]; then
      REMAINING=$((NOTIFICATION_COOLDOWN - TIME_DIFF))
      echo "$(date '+%Y-%m-%d %H:%M:%S %Z') {\"service\": \"${SERVICE_NAME:-unknown}\", \"event\": \"notification_throttled\", \"details\": \"Throttled: $NOTIFICATION_KEY (${REMAINING}s remaining)\"}"
      return 1
    fi
  fi

  # Update state file with current timestamp
  echo "$CURRENT_TIME" > "$STATE_FILE"
  return 0
}

send_notification() {
  TITLE="$1"
  BODY="$2"
  USE_HTML="${3:-true}"  # Default to HTML emails

  # Skip if email not configured
  if [ -z "$EMAIL_TO" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASSWORD" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S %Z') {\"service\": \"${SERVICE_NAME:-unknown}\", \"event\": \"notification_skipped\", \"details\": \"Email not configured (missing EMAIL_TO, SMTP_USER, or SMTP_PASSWORD)\"}"
    return 0
  fi

  # Generate notification key for deduplication (sanitize title)
  NOTIFICATION_KEY=$(echo "${TITLE}" | tr -cs '[:alnum:]' '_' | tr '[:upper:]' '[:lower:]')

  # Check rate limit
  if ! should_send_notification "$NOTIFICATION_KEY"; then
    return 0
  fi

  MAX_RETRIES=3
  BACKOFF_BASE=2
  ATTEMPT=1

  while [ "$ATTEMPT" -le "$MAX_RETRIES" ]; do
    # Create msmtp config in temp file
    MSMTP_CONFIG=$(mktemp)
    cat > "$MSMTP_CONFIG" << EOF
defaults
auth on
tls on
tls_starttls on
tls_certcheck on
logfile /dev/null
timeout 15

account default
host $SMTP_HOST
port $SMTP_PORT
from $SMTP_FROM
user $SMTP_USER
password $SMTP_PASSWORD
EOF
    chmod 600 "$MSMTP_CONFIG"

    # Send email using msmtp
    if command -v msmtp >/dev/null 2>&1; then
      if [ "$USE_HTML" = "true" ]; then
        # Build HTML email with proper structure
        EMAIL_CONTENT=$(printf '%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n%s' \
          "To: ${EMAIL_TO}" \
          "From: ${SMTP_FROM}" \
          "Subject: [Torrent Services] ${TITLE}" \
          "MIME-Version: 1.0" \
          "Content-Type: text/html; charset=utf-8" \
          "<!DOCTYPE html>
<html>
<head>
<style>body{font-family:Arial,sans-serif;line-height:1.6;color:#333;max-width:800px;margin:0 auto;padding:20px}h2{color:#d32f2f;margin-bottom:10px}.info{background:#f5f5f5;padding:15px;border-left:4px solid #1976d2;margin:15px 0}.footer{margin-top:30px;padding-top:15px;border-top:1px solid #ddd;color:#666;font-size:0.9em}pre{white-space:pre-wrap;word-wrap:break-word}</style>
</head>
<body>
<h2>${TITLE}</h2>
<div class='info'>
${BODY}
</div>
<div class='footer'>
<p><strong>Sent from:</strong> ${SERVICE_NAME:-healthcheck}</p>
<p><strong>Timestamp:</strong> $(date -Iseconds)</p>
</div>
</body>
</html>")
      else
        # Plain text email
        EMAIL_CONTENT=$(printf '%s\r\n%s\r\n%s\r\n%s\r\n\r\n%s\n\n--\nSent from: %s\nTimestamp: %s' \
          "To: ${EMAIL_TO}" \
          "From: ${SMTP_FROM}" \
          "Subject: [Torrent Services] ${TITLE}" \
          "Content-Type: text/plain; charset=utf-8" \
          "${BODY}" \
          "${SERVICE_NAME:-healthcheck}" \
          "$(date -Iseconds)")
      fi

      EMAIL_RESULT=$(printf "%s" "$EMAIL_CONTENT" | msmtp -C "$MSMTP_CONFIG" "$EMAIL_TO" 2>&1)
      EXIT_CODE=$?
      rm -f "$MSMTP_CONFIG"

      if [ $EXIT_CODE -eq 0 ]; then
        echo "$(date -Iseconds) {\"service\": \"${SERVICE_NAME:-unknown}\", \"event\": \"notification_sent\", \"details\": \"Email sent: $TITLE\"}"
        return 0
      fi

      echo "$(date -Iseconds) {\"service\": \"${SERVICE_NAME:-unknown}\", \"event\": \"notification_retry_failed\", \"details\": \"Attempt $ATTEMPT failed: $EMAIL_RESULT\"}"
    else
      rm -f "$MSMTP_CONFIG"
      echo "$(date -Iseconds) {\"service\": \"${SERVICE_NAME:-unknown}\", \"event\": \"notification_failed\", \"details\": \"msmtp not available to send: $TITLE\"}"
      return 1
    fi

    # Exponential backoff
    SLEEP_TIME=1
    i=0
    while [ "$i" -lt "$ATTEMPT" ]; do
      SLEEP_TIME=$((SLEEP_TIME * BACKOFF_BASE))
      i=$((i + 1))
    done
    sleep "$SLEEP_TIME"
    ATTEMPT=$((ATTEMPT+1))
  done

  echo "$(date -Iseconds) {\"service\": \"${SERVICE_NAME:-unknown}\", \"event\": \"notification_failed\", \"details\": \"All retries failed for: $TITLE\"}"
  return 1
}

# Legacy alias for backward compatibility
send_email() {
  send_notification "$@"
}

return 0
