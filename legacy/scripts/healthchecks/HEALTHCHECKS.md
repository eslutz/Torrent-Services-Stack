# Healthchecks & Notifications

## Overview
This folder contains healthcheck scripts for all services (*arr, qBittorrent, Gluetun, etc.) and shared utilities for logging/notification. It includes a Docker events email notifier (used by the `health-monitor` container) that alerts when containers become unhealthy or stop.

## Health Check Configuration

### Intervals & Timeouts
Health check intervals are set pragmatically based on service criticality:

Script response time limits are derived from the Docker timeout:

$$
	ext{MAX\_RESPONSE\_TIME} = \left\lfloor \frac{\text{HEALTHCHECK\_TIMEOUT\_SECONDS}}{3} \right\rfloor
$$

| Service | Interval | Timeout | Grace Period | Rationale |
|---------|----------|---------|--------------|----------|
| Gluetun | 2m | 60s | 180s | VPN gateway protection |
| qBittorrent | 5m | 60s | 240s | Torrent engine (needs time to save state) |
| Prowlarr | 5m | 60s | 300s | Indexer API with retry/backoff |
| Sonarr | 5m | 60s | 300s | Media manager API with retry/backoff |
| Radarr | 5m | 60s | 300s | Media manager API with retry/backoff |
| Bazarr | 5m | 60s | 330s | Subtitle API with retry/backoff |
| Tdarr | 5m | 60s | 420s | Transcode service slow startup |
| Jellyseerr | 5m | 60s | 420s | Node service slow startup |
| Unpackarr | 5m | 20s | 180s | Wrapper health endpoint |
| Torarr | 5m | 20s | 360s | Tor bootstrap time |
| Forwardarr | 1m | 30s | 120s | Quick port sync required |

**Design Philosophy:**
- **Architectural protection first**: qBittorrent uses `network_mode: service:gluetun` for IP protection
- **Health checks are secondary**: Catch rare failures, not constant validation
- **Pragmatic intervals**: Non-critical services don't need constant validation (5min is sufficient)
- **Hardcoded values**: Better than configurable complexity for health checks
- **Safety margin**: Timeouts allow for retry/backoff and slower startup (roughly 20-60s headroom)

### Autoheal Circuit Breaker
- **Enabled**: `DEFAULT_STOP=true`, `MAX_RETRIES=2`
- **Purpose**: Prevents infinite restart loops
- **Behavior**: After 2 failed restart attempts, container remains stopped until manual intervention
 - **Startup buffer**: Autoheal waits 600s before monitoring to reduce startup flapping

## Email Notifications (health-monitor)

### Enhanced Notifications
`docker_events_notifier.sh` provides detailed email alerts with:
- **Health check output**: Last check result and exit code
- **Root cause analysis**: Explains what happened (timeout, exceeded grace period, etc.)
- **Previous state**: Shows health status before failure
- **Next steps**: Actionable debugging guidance
- **Local time**: All timestamps in EST/EDT for easy log correlation

### Event Monitoring
- Listens to Docker container events: `unhealthy`, `die`, `stop`, `kill`, `oom`
- Monitors Autoheal restarts via `/logs/autoheal/log.json`
- Filters normal shutdowns (user-initiated `docker compose down/restart`)
- Rate limiting: 300s cooldown between notifications per container

### Configuration
- SMTP via environment variables in `.env`:
  - `EMAIL_TO` (recipient), `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- Healthcheck timeouts via `.env`:
  - `GLUETUN_HEALTHCHECK_TIMEOUT_SECONDS`, `QBITTORRENT_HEALTHCHECK_TIMEOUT_SECONDS`,
    `PROWLARR_HEALTHCHECK_TIMEOUT_SECONDS`, `SONARR_HEALTHCHECK_TIMEOUT_SECONDS`,
    `RADARR_HEALTHCHECK_TIMEOUT_SECONDS`, `BAZARR_HEALTHCHECK_TIMEOUT_SECONDS`,
    `TDARR_HEALTHCHECK_TIMEOUT_SECONDS`, `JELLYSEERR_HEALTHCHECK_TIMEOUT_SECONDS`
- Logs written to `/logs/health-monitor/events.log`
- The `health-monitor` service installs `msmtp` + `jq`, mounts the Docker socket read-only

### Email Alert Example
```
Subject: ⚠️ qBittorrent unhealthy (health check timeout)

=== Container Health Alert ===
Container: qbittorrent
Event: unhealthy
Time: 2026-01-09 14:37:42 EST

--- Health Check Details ---
Last Check: 2026-01-09 14:37:12 EST
Exit Code: -1 (Health check timed out)
Output: [none - check didn't complete]

Previous State: healthy
New State: unhealthy

--- Root Cause Analysis ---
The health check process didn't complete within Docker's timeout window.
This typically indicates system resource pressure (CPU/disk I/O).

--- Health Check Configuration ---
Interval: 5m0s
Timeout: 60s
Retries: 3
Start Period: 240s

--- Next Steps ---
1. Check system resources: docker stats qbittorrent
2. Review recent logs: docker logs qbittorrent --tail 50
3. Verify qBittorrent is responsive: curl -I http://gluetun:8080
4. If persists, autoheal will restart (max 2 attempts)
```

## Per-Service Healthchecks
- Each service uses `run_healthcheck.sh` with its specific script (e.g., `sonarr.sh`, `radarr.sh`)
- Shared helpers for logging/email live in `healthcheck_utils.sh`
- All timestamps use local time format: `YYYY-MM-DD HH:MM:SS TZ`

## Metrics Export

- Run `metrics_exporter.sh` to generate Prometheus metrics from healthcheck logs:
  ```sh
  sh /scripts/healthchecks/metrics_exporter.sh > /config/healthcheck_metrics.prom
  ```
- Example metrics:
  ```
  healthcheck_healthy_total{service="bazarr"} 42
  healthcheck_unhealthy_total{service="bazarr"} 3
  healthcheck_remediation_requested_total{service="bazarr"} 2
  healthcheck_dry_run_total{service="bazarr"} 1
  healthcheck_status{service="bazarr"} 1
  ```
- Scrape `/config/healthcheck_metrics.prom` with Prometheus node exporter or custom scrape config.

## Email Notification
- All notification emails are sent to the address in the `EMAIL_TO` environment variable (set in `.env`).
- To change the recipient, update `EMAIL_TO` in `.env` and restart the monitor container.

## Troubleshooting

### Health Check Timeouts
**Symptoms:** Container marked `unhealthy`, health check exit code `-1`

**Causes:**
- Heavy disk I/O preventing check from completing
- System resource pressure (CPU/memory)
- Healthcheck command exceeded its timeout window

**Solutions:**
- Check system resources: `docker stats`
- Verify service response time: `docker exec <container> sh /scripts/healthchecks/<service>.sh`
- Review timeout settings in `docker-compose.yml` (20-60s typical depending on service)

### Container Force Kills (Exit Code 137)
**Symptoms:** Container receives SIGKILL (signal 9), exit code 137

**Causes:**
- Exceeded `stop_grace_period` during shutdown
- Docker sent SIGTERM, waited for grace period, then force killed
- Service didn't respond to SIGTERM in time

**Solutions:**
- Increase `stop_grace_period` in `docker-compose.yml` (qBittorrent: 120s, others: 30s)
- Check logs for slow shutdown operations
- Verify service responds to SIGTERM gracefully

### Autoheal Infinite Loops
**Symptoms:** Container repeatedly restarting, never reaching healthy state

**Causes:**
- Underlying service issue not resolved by restart
- Health check too strict or misconfigured
- Resource exhaustion

**Solutions:**
- Circuit breaker enabled: after 2 retries, container stops
- Check `docker logs autoheal` for restart history
- Review health check logic in `scripts/healthchecks/<service>.sh`
- Fix root cause before manually restarting

### Email Notifications Not Received
**Symptoms:** Events logged but no email alerts

**Causes:**
- SMTP credentials incorrect
- Rate limiting (300s cooldown per container)
- Email filtered to spam

**Solutions:**
- Test email manually: `docker exec health-monitor sh /scripts/healthchecks/docker_events_notifier.sh`
- Verify SMTP settings in `.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- Check `/logs/health-monitor/events.log` for email send attempts
- Add sender to email whitelist

### Logs & Diagnostics
- **Health check logs:** `/logs/<service>/healthcheck.log`
- **Event logs:** `/logs/health-monitor/events.log`
- **Autoheal logs:** `/logs/autoheal/log.json`
- **Container stdout:** `docker logs <container>`
- **Health status:** `docker compose ps` or `docker inspect <container> --format='{{.State.Health.Status}}'`
