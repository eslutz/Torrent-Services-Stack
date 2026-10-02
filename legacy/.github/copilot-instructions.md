# Copilot Instructions for Torrent Services

## Naming Conventions

**Markdown files**: Use lowercase with hyphens as separators (e.g., `network-design.md`, `vpn-guide.md`). Exceptions: `README.md`, `SECURITY.md`, `CONTRIBUTING.md`.

## Setup Strategy

**Backup/Restore Approach**: This project uses a backup/restore strategy instead of programmatic configuration. Configure services manually via their web UIs, then use `scripts/utilities/backup_config.sh` to capture the known-good state. Restore on new hosts with `scripts/utilities/restore_config.sh`. See `scripts/utilities/SETUP_GUIDE.md` for complete instructions.

## Critical Architecture Patterns

**VPN Network Sharing**: qBittorrent uses `network_mode: "service:gluetun"` to share Gluetun's network namespace. Access qBit at `gluetun:8080` in service configs, not `qbittorrent:8080`.

**Health-Gated Startup**: Services wait for `service_healthy` before starting. Health checks verify real API responses (<5s latency), not just process existence. See `scripts/healthchecks/*.sh` for shell-based probes.

## Development Essentials

**Python Environment**: All Python scripts must be run using the virtual environment at the project root:
```bash
# Create venv (one-time setup)
python3 -m venv venv

# Install dependencies
venv/bin/pip install -r requirements.txt

# Run scripts
venv/bin/python3 scripts/*/script_name.py
```

**Tests**: Run with `venv/bin/pytest tests/` (min 60% coverage enforced). Test configuration is in `pyproject.toml` with `pythonpath = "."` for imports. Mirror `scripts/` structure. Use `unittest.mock` + `responses` for HTTP mocking. **Never lower coverage requirements to make tests pass** - fix or add tests instead.

**Env var pattern**: All Python scripts use `from common import load_env; load_env()` to support both Docker (service names) and host (localhost) execution.

## Docker Compose Patterns

**Resource limits**: Always use env vars with defaults: `mem_limit: ${SERVICE_MEM_LIMIT:-256m}`. Never hardcode.

**Security**: All services use `security_opt: [no-new-privileges:true]`, `init: true`, and 30s grace periods.

**Volume mounts**: Scripts are read-only (`:ro`), configs are bind mounts, ephemeral data uses named volumes (`gluetun-tmp`).

## Common Issues

- **Service won't start**: Check `docker ps --format "table {{.Names}}\t{{.Status}}"` for health status. Run health check manually: `docker exec <container> sh /scripts/<service>.sh`
- **Port forwarding**: Verify Gluetun port file: `docker exec gluetun cat /tmp/gluetun/forwarded_port`. Check Forwardarr logs: `docker logs forwardarr --tail 20`
- **Missing media files**: Run `venv/bin/python3 scripts/utilities/rescan_missing_media.py --search` to detect and re-download

See `scripts/setup/SETUP.md` for setup instructions and troubleshooting.
