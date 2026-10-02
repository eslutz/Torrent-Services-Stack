#!/bin/sh
# Prometheus metrics exporter for healthcheck events
# Usage: sh metrics_exporter.sh > /config/healthcheck_metrics.prom

LOG_DIR="/config"

# Find all healthcheck logs
find "$LOG_DIR" -type f -name healthcheck.log | while IFS= read -r LOG; do
  SERVICE=$(echo "$LOG" | awk -F/ '{print $(NF-2)}')
  HEALTHY=$(grep -c '"event": "healthy"' "$LOG")
  UNHEALTHY=$(grep -c '"event": "unhealthy"' "$LOG")
  REMED=$(grep -c '"event": "remediation_requested"' "$LOG")
  DRYRUN=$(grep -c '"event": "dry_run"' "$LOG")
  echo "healthcheck_healthy_total{service=\"$SERVICE\"} $HEALTHY"
  echo "healthcheck_unhealthy_total{service=\"$SERVICE\"} $UNHEALTHY"
  echo "healthcheck_remediation_requested_total{service=\"$SERVICE\"} $REMED"
  echo "healthcheck_dry_run_total{service=\"$SERVICE\"} $DRYRUN"
  LAST=$(grep '"event":' "$LOG" | tail -1)
  if echo "$LAST" | grep -q '"event": "healthy"'; then
    echo "healthcheck_status{service=\"$SERVICE\"} 1"
  else
    echo "healthcheck_status{service=\"$SERVICE\"} 0"
  fi
  echo "# HELP healthcheck_status 1=healthy, 0=unhealthy"
  echo "# TYPE healthcheck_status gauge"
  echo "# TYPE healthcheck_healthy_total counter"
  echo "# TYPE healthcheck_unhealthy_total counter"
  echo "# TYPE healthcheck_remediation_requested_total counter"
  echo "# TYPE healthcheck_dry_run_total counter"
  echo ""
done
