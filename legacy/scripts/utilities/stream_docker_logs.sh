#!/bin/sh
set -eu

# Stream Docker logs to files for multiple containers
# This script monitors Docker containers and writes their logs to date-based files

LOGS_DIR="/logs"
KEEP_DAYS=${LOG_KEEP_ROTATIONS:-7}

# Container name and log directory pairs (space-separated)
CONTAINERS="
gluetun:gluetun
qbittorrent:qbittorrent
prowlarr:prowlarr
sonarr:sonarr
radarr:radarr
bazarr:bazarr
tdarr-server:tdarr
jellyseerr:jellyseerr
forwardarr:forwardarr
torarr:torarr
unpackarr:unpackarr
autoheal:autoheal
events-notifier:events-notifier
"

# Function to get current date-based log file
get_current_log_file() {
    log_dir="$1"
    service_name="$2"
    today=$(date '+%Y.%m.%d')
    echo "$LOGS_DIR/$log_dir/${service_name}-${today}.log"
}

# Function to clean up old log files
cleanup_old_logs() {
    log_dir="$1"
    service_name="$2"

    if [ "$KEEP_DAYS" -gt 0 ]; then
        find "$LOGS_DIR/$log_dir" -name "${service_name}-*.log" -type f -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true
    fi
}

# Function to stream logs for a single container
stream_container_logs() {
    container_name="$1"
    log_dir="$2"
    service_name="$log_dir"  # Use log directory name as service name

    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting log stream for $container_name -> $log_dir/"

    # Ensure log directory exists
    mkdir -p "$LOGS_DIR/$log_dir"

    # Track last seen container since timestamp for incremental logs
    last_timestamp=""

    # Stream logs with timestamps, follow mode, and restart on container restart
    while true; do
        if docker ps --format '{{.Names}}' | grep -q "^${container_name}\$"; then
            # Get current log file (may change daily)
            current_log=$(get_current_log_file "$log_dir" "$service_name")

            # Container is running, stream logs
            if [ -z "$last_timestamp" ]; then
                # First run or after reconnect - get only recent logs
                docker logs --timestamps --since 1m "$container_name" >> "$current_log" 2>&1 || true
            fi

            # Follow logs continuously, checking for date change every line
            docker logs -f --timestamps "$container_name" 2>&1 | while IFS= read -r line; do
                # Re-check current log file on each iteration (date may have changed)
                log_file=$(get_current_log_file "$log_dir" "$service_name")
                # Write to the current date's log file
                echo "$line" >> "$log_file"
            done || true

            # Reconnection message
            reconnect_log=$(get_current_log_file "$log_dir" "$service_name")
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Container $container_name stopped or restarted, reconnecting..." >> "$reconnect_log"
            cleanup_old_logs "$log_dir" "$service_name"
        else
            # Container not running, wait and retry
            sleep 5
        fi
    done
}

# Start background processes for each container
echo "Starting log streaming..."
for pair in $CONTAINERS; do
    [ -z "$pair" ] && continue
    container=$(echo "$pair" | cut -d: -f1)
    logdir=$(echo "$pair" | cut -d: -f2)
    stream_container_logs "$container" "$logdir" &
done

# Count running background jobs
num_containers=$(echo "$CONTAINERS" | grep -c ":")

echo "Log streaming started for $num_containers containers"
echo "Logs are being written to $LOGS_DIR/<service>/docker.log"
echo "Press Ctrl+C to stop"

# Wait for all background processes
wait
