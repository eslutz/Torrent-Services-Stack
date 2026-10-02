# Log Management

This document describes the log management system for the Torrent Services stack.

## Overview

The project uses two types of logs:

1. **Healthcheck Logs**: Custom health check scripts output to `./logs/<service>/healthcheck.log`
2. **Application Logs**: Docker container logs streamed to `./logs/<service>/docker.log`

## Healthcheck Logs

### Format

Healthcheck logs use date-based naming:

- Current log: `healthcheck-YYYY.MM.DD.log` (includes today's date)
- Older logs: `healthcheck-YYYY.MM.DD.log` (previous dates)

**Example:**
```
logs/gluetun/healthcheck-2026.01.10.log  ← Today's log
logs/gluetun/healthcheck-2026.01.09.log  ← Yesterday's log
logs/gluetun/healthcheck-2026.01.08.log  ← 2 days ago
```

### Rotation

Logs are written directly to date-based files. At midnight, a new log file with the new date is automatically created. The rotation logic in `scripts/healthchecks/healthcheck_utils.sh`:

- Writes directly to `healthcheck-YYYY.MM.DD.log`
- New file created automatically when date changes
- Cleans up logs older than `$LOG_KEEP_ROTATIONS` days (default: 7)

### Configuration

Set retention in your `.env` file:

```bash
# Number of days to keep rotated logs
LOG_KEEP_ROTATIONS=7
```

### Manual Rotation

The rotation script only handles cleanup of old logs, not rotation (since logs are already date-based):

```bash
./scripts/utilities/rotate_logs.sh
```

## Application Logs

### Live Streaming

The `log-streamer` container continuously streams Docker logs from all services to individual date-based files in real-time.

**Container**: `log-streamer`
**Script**: `scripts/utilities/stream_docker_logs.sh`
**Output**: `./logs/<service>/<service>-YYYY.MM.DD.log`

### Features

- **Real-time streaming**: Logs are written continuously with < 1 second latency
- **Automatic reconnection**: Reconnects if containers restart
- **Date-based rotation**: New log file created automatically at midnight
- **Automatic cleanup**: Old logs removed after `LOG_KEEP_ROTATIONS` days (default: 7)
- **Timestamps**: All logs include Docker's native timestamps

### Viewing Live Logs

```bash
# Tail live logs from any service (use today's date)
tail -f logs/gluetun/gluetun-$(date '+%Y.%m.%d').log
tail -f logs/qbittorrent/qbittorrent-$(date '+%Y.%m.%d').log
tail -f logs/prowlarr/prowlarr-$(date '+%Y.%m.%d').log

# Or use a wildcard to get the latest
tail -f logs/gluetun/gluetun-*.log

# Or view directly from Docker
docker logs -f gluetun
```

### Service Mapping

| Container Name | Log Directory |
|---------------|---------------|
| gluetun | logs/gluetun/ |
| qbittorrent | logs/qbittorrent/ |
| prowlarr | logs/prowlarr/ |
| sonarr | logs/sonarr/ |
| radarr | logs/radarr/ |
| bazarr | logs/bazarr/ |
| tdarr-server | logs/tdarr/ |
| jellyseerr | logs/jellyseerr/ |
| forwardarr | logs/forwardarr/ |
| torarr | logs/torarr/ |
| unpackarr | logs/unpackarr/ |
| autoheal | logs/autoheal/ |
| events-notifier | logs/health-monitor/ |

## Troubleshooting

### Healthcheck logs not rotating

Check the healthcheck script is running:

```bash
docker exec <container> sh /scripts/healthchecks/<service>.sh
```

### Application logs not updating

Check the log-streamer container:

```bash
# Verify container is running
docker ps --format "table {{.Names}}\t{{.Status}}" | grep log-streamer

# Check streaming processes
docker exec log-streamer ps aux | grep "docker logs"

# Check log-streamer logs
docker logs log-streamer --tail 50
```

### High disk usage

Adjust retention in `.env`:

```bash
LOG_KEEP_ROTATIONS=3  # Keep only 3 days of healthcheck logs
```

For Docker's internal logs, adjust in `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"  # Reduce from 10MB to 5MB
    max-file: "3"    # Reduce from 3 to 2 files
```

Then recreate containers:

```bash
docker-compose up -d --force-recreate
```

## Log Analysis

### Search across all logs

```bash
# Search for errors in all healthcheck logs
grep -r "ERROR" logs/*/healthcheck*.log

# Search for errors in all application logs
grep -r "ERROR" logs/*/*.log --include="*-2026.*.log"

# Search in today's application logs
TODAY=$(date '+%Y.%m.%d')
grep -r "ERROR" logs/*/*-${TODAY}.log

# Find failed health checks
grep -r "FAIL" logs/*/healthcheck*.log
```

### Count log sizes

```bash
# Total size of all logs
du -sh logs/

# Size per service
du -sh logs/*/

# Find largest logs
du -h logs/*/*.log | sort -h | tail -10
```
