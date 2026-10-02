#!/usr/bin/env python3
"""
VPN Speed Test & Diagnostic Tool

This script performs a connectivity and speed test from inside a Docker container
(default: qbittorrent) to verify VPN functionality and performance.

Features:
- Verifies VPN IP masking (Host IP vs Container IP).
- Runs Download and Upload speed tests using curl.
- Uses JSON output from curl for precise speed measurement.
- Supports CLI arguments for customization.
"""

import sys
import os
import subprocess
import json
import argparse
import time
import requests

# Add parent directory to sys.path to import common
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common import load_env

# Load environment variables
load_env()

# Constants
DEFAULT_CONTAINER = "qbittorrent"
DEFAULT_DL_SIZE = "100MB"
DEFAULT_UL_SIZE = "25MB"

# Speedtest Servers
SERVER_TELE2 = {
    "name": "Tele2 (Global/Europe)",
    "dl_template": "http://speedtest.tele2.net/{size}.zip",
    "ul": "http://speedtest.tele2.net/upload.php"
}

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
BLUE = '\033[0;34m'
NC = '\033[0m' # No Color

class VPNSpeedTest:
    def __init__(self, container_name, json_output=False):
        self.container_name = container_name
        self.json_output = json_output
        self.results = {
            "timestamp": time.time(),
            "container": container_name,
            "vpn_status": "unknown",
            "host_ip": None,
            "container_ip": None,
            "location": {},
            "download": {"speed_mbps": 0, "status": "failed"},
            "upload": {"speed_mbps": 0, "status": "failed"}
        }

    def log(self, message, end="\n", color=None):
        """Print message if not in JSON output mode."""
        if not self.json_output:
            if color:
                print(f"{color}{message}{NC}", end=end, flush=True)
            else:
                print(message, end=end, flush=True)

    def _run_docker_cmd(self, cmd_list, capture_output=True, text=True, stream_stderr=False):
        """Execute a command inside the docker container."""
        full_cmd = ["docker", "exec"]
        if stream_stderr:
            full_cmd.append("-t")
        full_cmd.append(self.container_name)
        full_cmd.extend(cmd_list)
        
        if capture_output:
            stdout_dest = subprocess.PIPE
            stderr_dest = subprocess.PIPE if not stream_stderr else None
        else:
            stdout_dest = None
            stderr_dest = None

        try:
            return subprocess.run(
                full_cmd,
                stdout=stdout_dest,
                stderr=stderr_dest,
                text=text,
                check=False
            )
        except Exception as e:
            if not self.json_output:
                print(f"{RED}Docker execution error: {e}{NC}")
            return None

    def check_container(self):
        """Verify container is running."""
        res = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        if self.container_name not in res.stdout.splitlines():
            if self.json_output:
                print(json.dumps({"error": f"Container {self.container_name} not running"}))
            else:
                print(f"{RED}Error: Container '{self.container_name}' is not running.{NC}")
            sys.exit(1)

    def get_host_ip(self):
        """Fetch Host Public IP."""
        try:
            r = requests.get("https://ipinfo.io/json", timeout=5)
            if r.status_code == 200:
                data = r.json()
                self.results["host_ip"] = data.get("ip")
                return data.get("ip")
        except Exception:
            pass
        return None

    def get_container_ip(self):
        """Fetch Container Public IP via curl inside docker."""
        # Using curl inside container to hit ipinfo
        cmd = ["curl", "-s", "https://ipinfo.io/json"]
        res = self._run_docker_cmd(cmd)
        if res and res.returncode == 0:
            try:
                data = json.loads(res.stdout)
                self.results["container_ip"] = data.get("ip")
                self.results["location"] = {
                    "city": data.get("city"),
                    "country": data.get("country"),
                    "org": data.get("org")
                }
                return data
            except json.JSONDecodeError:
                pass
        return None

    def run_download_test(self, size_str):
        """Run download speed test."""
        url = SERVER_TELE2["dl_template"].format(size=size_str)
        self.log(f"Download ({size_str}):")
        
        # curl command:
        # -L: Follow redirects
        # -o /dev/null: Discard output
        # -#: Progress bar (stderr)
        # -w '%{json}': Output stats as JSON (stdout)
        # --max-time 180: Timeout after 3 minutes
        cmd = ["curl", "-L", "-o", "/dev/null", "-#", "-w", "%{json}", "--max-time", "180", url]
        
        start = time.time()
        # Stream stderr to show progress bar, capture stdout for JSON
        res = self._run_docker_cmd(cmd, stream_stderr=not self.json_output)
        elapsed = time.time() - start

        if res and res.returncode == 0:
            try:
                data = json.loads(res.stdout)
                # speed_download is in bytes/second
                speed_bps = data.get("speed_download", 0)
                speed_mbps = (speed_bps * 8) / 1_000_000
                
                self.results["download"] = {
                    "speed_mbps": round(speed_mbps, 2),
                    "time_seconds": round(elapsed, 2),
                    "size": size_str,
                    "status": "success"
                }
                self.log(f"Result: {GREEN}{speed_mbps:.2f} Mbps{NC} [{int(elapsed)}s]")
                return
            except json.JSONDecodeError:
                pass
        
        self.log("Result: " + f"{RED}Failed{NC}")

    def run_upload_test(self, size_str):
        """Run upload speed test."""
        self.log(f"Upload ({size_str}):")
        
        # 1. Create dummy file
        # Parse size (e.g., "25MB" -> 25)
        try:
            size_mb = int(''.join(filter(str.isdigit, size_str)))
        except ValueError:
            size_mb = 10 # fallback

        # Use dd to create file in /tmp
        setup_cmd = ["dd", "if=/dev/zero", "of=/tmp/speedtest_ul.tmp", "bs=1M", f"count={size_mb}", "status=none"]
        self._run_docker_cmd(setup_cmd)

        # 2. Upload with curl
        url = SERVER_TELE2["ul"]
        cmd = ["curl", "-T", "/tmp/speedtest_ul.tmp", "-o", "/dev/null", "-#", "-w", "%{json}", "--max-time", "180", url]
        
        start = time.time()
        res = self._run_docker_cmd(cmd, stream_stderr=not self.json_output)
        elapsed = time.time() - start

        # 3. Cleanup
        self._run_docker_cmd(["rm", "/tmp/speedtest_ul.tmp"])

        if res and res.returncode == 0:
            try:
                data = json.loads(res.stdout)
                # speed_upload is in bytes/second
                speed_bps = data.get("speed_upload", 0)
                speed_mbps = (speed_bps * 8) / 1_000_000
                
                self.results["upload"] = {
                    "speed_mbps": round(speed_mbps, 2),
                    "time_seconds": round(elapsed, 2),
                    "size": size_str,
                    "status": "success"
                }
                self.log(f"Result: {GREEN}{speed_mbps:.2f} Mbps{NC} [{int(elapsed)}s]")
                return
            except json.JSONDecodeError:
                pass

        self.log("Result: " + f"{RED}Failed{NC}")

    def run(self, dl_size, ul_size):
        try:
            self.check_container()
            
            if not self.json_output:
                print("==========================================")
                print(f"VPN Speed Test: {self.container_name}")
                print("==========================================")
                print("\n--- 🔒 VPN Status ---")

            # IP Checks
            host_ip = self.get_host_ip()
            container_data = self.get_container_ip()
            container_ip = container_data.get("ip") if container_data else None

            if not self.json_output:
                print(f"Host IP:      {host_ip}")
                print(f"Container IP: {container_ip}")

            if host_ip and container_ip:
                if host_ip != container_ip:
                    self.results["vpn_status"] = "secure"
                    if not self.json_output:
                        print(f"Status:       {GREEN}SECURE (IPs differ){NC}")
                        loc = self.results["location"]
                        print(f"Location:     {loc.get('city')}, {loc.get('country')} ({loc.get('org')})")
                else:
                    self.results["vpn_status"] = "leaking"
                    if not self.json_output:
                        print(f"Status:       {RED}WARNING: IPs match! VPN might be down.{NC}")
            else:
                self.results["vpn_status"] = "error"
                if not self.json_output:
                    print(f"Status:       {YELLOW}Could not verify IPs{NC}")

            # Speed Tests
            if not self.json_output:
                print("\n--- 🚀 Speed Test ---")
            
            self.run_download_test(dl_size)
            self.run_upload_test(ul_size)

            if not self.json_output:
                print("\n==========================================")
            else:
                print(json.dumps(self.results, indent=2))
        except KeyboardInterrupt:
            if not self.json_output:
                print(f"\n{RED}Test cancelled by user.{NC}")
            sys.exit(130)

def main():
    parser = argparse.ArgumentParser(description="Run VPN speed test inside a Docker container.")
    parser.add_argument("--container", default=DEFAULT_CONTAINER, help=f"Container name (default: {DEFAULT_CONTAINER})")
    parser.add_argument("--dl-size", default=DEFAULT_DL_SIZE, help=f"Download size (default: {DEFAULT_DL_SIZE})")
    parser.add_argument("--ul-size", default=DEFAULT_UL_SIZE, help=f"Upload size (default: {DEFAULT_UL_SIZE})")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()

    tester = VPNSpeedTest(args.container, args.json)
    tester.run(args.dl_size, args.ul_size)

if __name__ == "__main__":
    main()

