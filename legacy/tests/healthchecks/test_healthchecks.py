import os
import stat
import subprocess
from pathlib import Path
from typing import Optional


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _make_mock_bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    # Mock ip to claim tun0 exists
    _write_executable(
        bin_dir / "ip",
        """#!/bin/sh
if [ "$1" = "link" ] && [ "$2" = "show" ] && [ "$3" = "tun0" ]; then
  exit 0
fi
exit 1
""",
    )

    # Mock wget to return service-specific responses
    _write_executable(
        bin_dir / "wget",
        """#!/bin/sh
# Extract the last argument (URL) without using bash-only features
url=""
for arg in "$@"; do
  url="$arg"
done

case "$url" in
  http://localhost:8000/v1/vpn/status)
    echo '{"status":"running"}'
    ;;
  http://localhost:8000/v1/openvpn/portforwarded)
    echo '{"port":51820}'
    ;;
  http://localhost:8080/api/v2/app/version)
    echo "  HTTP/1.1 200 OK"
    ;;
  http://localhost:9696/api/v1/health)
    echo '[{"type":"ok"}]'
    ;;
  http://localhost:9696/ping)
    echo '{"status":"OK"}'
    ;;
  http://localhost:8989/api/v3/health)
    echo '[{"type":"ok"}]'
    ;;
  http://localhost:8989/ping)
    echo '{"status":"OK"}'
    ;;
  http://localhost:7878/api/v3/health)
    echo '[{"type":"ok"}]'
    ;;
  http://localhost:7878/ping)
    echo '{"status":"OK"}'
    ;;
  http://localhost:6767/api/system/status)
    echo '{"version":"1.2.3"}'
    ;;
  http://localhost:6767/)
    echo "  HTTP/1.1 200 OK"
    ;;
  http://localhost:5656/metrics)
    echo "  HTTP/1.1 200 OK"
    ;;
  http://localhost:8266/api/v2/status)
    echo '{"status":"running"}'
    ;;
  http://localhost:8000/health)
    echo '{"status":"ok"}'
    ;;
  http://localhost:5055/api/v1/status)
    echo '{"version":"1.33.2"}'
    ;;
  *)
    echo "  HTTP/1.1 200 OK"
    ;;
esac
exit 0
""",
    )

    return bin_dir


def _run_script(script: str, tmp_path: Path, extra_env: Optional[dict] = None):
    env = os.environ.copy()
    env["PATH"] = f"{_make_mock_bin(tmp_path)}:{env['PATH']}"
    if extra_env:
        env.update(extra_env)

    result = subprocess.run(
        [script],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
    )
    return result


def test_gluetun_healthcheck(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/healthchecks/gluetun.sh"
    result = _run_script(str(script), tmp_path, {"LOG_PATH": str(tmp_path / "healthcheck.log")})
    assert result.returncode == 0, result.stderr or result.stdout
    assert "healthy" in result.stdout


def test_qbittorrent_healthcheck(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/healthchecks/qbittorrent.sh"
    result = _run_script(str(script), tmp_path, {"LOG_PATH": str(tmp_path / "healthcheck.log")})
    assert result.returncode == 0, result.stderr or result.stdout
    assert "healthy" in result.stdout


def test_prowlarr_healthcheck_api_mode(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/healthchecks/prowlarr.sh"
    result = _run_script(
        str(script),
        tmp_path,
        {"PROWLARR_API_KEY": "test", "LOG_PATH": str(tmp_path / "healthcheck.log")},
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "healthy" in result.stdout


def test_sonarr_healthcheck_api_mode(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/healthchecks/sonarr.sh"
    result = _run_script(
        str(script),
        tmp_path,
        {"SONARR_API_KEY": "test", "LOG_PATH": str(tmp_path / "healthcheck.log")},
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "healthy" in result.stdout


def test_radarr_healthcheck_api_mode(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/healthchecks/radarr.sh"
    result = _run_script(
        str(script),
        tmp_path,
        {"RADARR_API_KEY": "test", "LOG_PATH": str(tmp_path / "healthcheck.log")},
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "healthy" in result.stdout


def test_bazarr_healthcheck_api_mode(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/healthchecks/bazarr.sh"
    result = _run_script(
        str(script),
        tmp_path,
        {"BAZARR_API_KEY": "test", "LOG_PATH": str(tmp_path / "healthcheck.log")},
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "healthy" in result.stdout
