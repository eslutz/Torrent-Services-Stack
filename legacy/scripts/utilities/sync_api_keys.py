#!/usr/bin/env python3
"""
Sync and validate API keys between services.

This script validates and syncs Prowlarr API keys to Sonarr/Radarr indexers.
"""

import os
import sys
import requests
from pathlib import Path


def log(msg, level="INFO"):
    """Print colored log messages."""
    colors = {
        "INFO": "\033[0;34m",
        "SUCCESS": "\033[0;32m",
        "WARNING": "\033[1;33m",
        "ERROR": "\033[0;31m",
    }
    end = "\033[0m"
    print(f"{colors.get(level, '')}[{level}] {msg}{end}")


def load_env():
    """Load environment variables from .env file in the repository root."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, "../../"))
    env_path = os.path.join(root_dir, ".env")

    if os.path.exists(env_path):
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]

                        if key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            print(f"Warning: Failed to load .env file: {e}")


def update_env_file(key_name, api_key):
    """Update .env file with an API key."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, "../../"))
    env_path = Path(root_dir) / ".env"

    if not env_path.exists():
        log(".env file not found", "ERROR")
        return False

    try:
        with open(env_path, "r") as f:
            lines = f.readlines()

        # Check if key already exists
        key_exists = False
        updated_lines = []

        for line in lines:
            if line.strip().startswith(f"{key_name}="):
                key_exists = True
                # Update the existing line
                updated_lines.append(f'{key_name}="{api_key}"\n')
                log(f"Updated existing {key_name} in .env", "SUCCESS")
            else:
                updated_lines.append(line)

        if not key_exists:
            # Add the key at the end, checking for trailing newline
            if updated_lines and not updated_lines[-1].endswith('\n'):
                updated_lines.append('\n')
            updated_lines.append(f'{key_name}="{api_key}"\n')
            log(f"Added {key_name} to .env", "SUCCESS")

        # Write back to file
        with open(env_path, "w") as f:
            f.writelines(updated_lines)

        return True

    except Exception as e:
        log(f"Error updating .env file: {e}", "ERROR")
        return False


load_env()

PROWLARR_API_KEY = os.environ.get("PROWLARR_API_KEY")
SONARR_API_KEY = os.environ.get("SONARR_API_KEY")
RADARR_API_KEY = os.environ.get("RADARR_API_KEY")

# Use localhost if running from host, or container names if running inside docker network
SONARR_URL = "http://localhost:8989"
RADARR_URL = "http://localhost:7878"


def fix_indexers(app_name, base_url, app_api_key, correct_prowlarr_key):
    """Fix Prowlarr indexers in Sonarr/Radarr."""
    log(f"Checking {app_name} indexers...", "INFO")

    headers = {"X-Api-Key": app_api_key}
    try:
        resp = requests.get(f"{base_url}/api/v3/indexer", headers=headers)
        resp.raise_for_status()
        indexers = resp.json()
    except Exception as e:
        log(f"Failed to get indexers from {app_name}: {e}", "ERROR")
        return

    count = 0
    for indexer in indexers:
        # Check if it's a Prowlarr indexer
        fields = indexer.get("fields", [])
        url_field = next((f for f in fields if f["name"] == "baseUrl"), None)
        api_field = next((f for f in fields if f["name"] == "apiKey"), None)

        is_prowlarr = False
        if url_field and "prowlarr" in str(url_field.get("value", "")).lower():
            is_prowlarr = True

        if is_prowlarr:
            current_key = api_field.get("value") if api_field else None
            if current_key != correct_prowlarr_key:
                log(f"Updating API key for indexer: {indexer['name']}", "INFO")
                if api_field:
                    api_field["value"] = correct_prowlarr_key
                else:
                    log(f"Skipping {indexer['name']} - no apiKey field found", "WARNING")
                    continue

                try:
                    # Update the indexer
                    update_resp = requests.put(
                        f"{base_url}/api/v3/indexer/{indexer['id']}",
                        headers=headers,
                        json=indexer
                    )
                    update_resp.raise_for_status()

                    # Test the indexer
                    log(f"Testing indexer: {indexer['name']}", "INFO")
                    test_resp = requests.post(
                        f"{base_url}/api/v3/indexer/test",
                        headers=headers,
                        json=indexer
                    )

                    if test_resp.status_code == 200:
                        log(f"Indexer {indexer['name']} test PASSED", "SUCCESS")
                        count += 1
                    else:
                        log(f"Indexer {indexer['name']} test FAILED: {test_resp.text}", "ERROR")

                except Exception as e:
                    log(f"Failed to update/test {indexer['name']}: {e}", "ERROR")

    if count > 0:
        log(f"Updated {count} indexers in {app_name}", "SUCCESS")
    else:
        log(f"No indexers needed updating in {app_name}", "INFO")


if __name__ == "__main__":
    print("=" * 60)
    log("Prowlarr API Key Sync and Validation", "INFO")
    print("=" * 60)
    print()

    # Sync Prowlarr keys to Sonarr/Radarr
    if not PROWLARR_API_KEY:
        log("PROWLARR_API_KEY missing - cannot sync indexers", "ERROR")
        sys.exit(1)

    if SONARR_API_KEY:
        fix_indexers("Sonarr", SONARR_URL, SONARR_API_KEY, PROWLARR_API_KEY)
    else:
        log("SONARR_API_KEY missing", "WARNING")

    if RADARR_API_KEY:
        fix_indexers("Radarr", RADARR_URL, RADARR_API_KEY, PROWLARR_API_KEY)
    else:
        log("RADARR_API_KEY missing", "WARNING")

    print()
    log("API key sync complete", "SUCCESS")
