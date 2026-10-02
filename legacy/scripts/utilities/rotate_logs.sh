#!/bin/sh
# Log rotation script for healthcheck logs
# Rotates logs daily with date-based naming: healthcheck-YYYY.MM.DD.log
# Usage: Run as cron job or manually: ./rotate_logs.sh

set -e

LOG_DIR="/logs"
KEEP_DAYS=${LOG_KEEP_ROTATIONS:-7}

# Clean up old healthcheck logs (date-based files, no rotation needed)
if [ "$KEEP_DAYS" -gt 0 ]; then
  for service_dir in "$LOG_DIR"/*; do
    if [ -d "$service_dir" ]; then
      # Clean up old healthcheck-*.log files
      DELETED=$(find "$service_dir" -name "healthcheck-*.log" -type f -mtime +"$KEEP_DAYS" -delete -print 2>/dev/null | wc -l | tr -d ' ')
      if [ "$DELETED" -gt 0 ]; then
        service_name=$(basename "$service_dir")
        echo "  Deleted $DELETED old $service_name healthcheck log(s) older than $KEEP_DAYS days"
      fi

      # Clean up old events-*.log files
      DELETED=$(find "$service_dir" -name "events-*.log" -type f -mtime +"$KEEP_DAYS" -delete -print 2>/dev/null | wc -l | tr -d ' ')
      if [ "$DELETED" -gt 0 ]; then
        service_name=$(basename "$service_dir")
        echo "  Deleted $DELETED old $service_name events log(s) older than $KEEP_DAYS days"
      fi
    fi
  done
fi

# Clean up old application logs (date-based files created by stream_docker_logs.sh)
# These don't need rotation since they're already date-based, just cleanup
if [ "$KEEP_DAYS" -gt 0 ]; then
  for service_dir in "$LOG_DIR"/*; do
    if [ -d "$service_dir" ]; then
      service_name=$(basename "$service_dir")
      DELETED=$(find "$service_dir" -name "${service_name}-*.log" -type f -mtime +"$KEEP_DAYS" -delete -print 2>/dev/null | wc -l | tr -d ' ')
      if [ "$DELETED" -gt 0 ]; then
        echo "  Deleted $DELETED old $service_name application log(s) older than $KEEP_DAYS days"
      fi
    fi
  done
fi

echo "Log rotation complete (keeping last $KEEP_DAYS days)"
