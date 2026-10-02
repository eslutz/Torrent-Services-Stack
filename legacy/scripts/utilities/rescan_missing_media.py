#!/usr/bin/env python3
"""
Rescan Sonarr/Radarr libraries and trigger searches for missing media.

Usage:
    python3 scripts/utilities/rescan_missing_media.py                    # Rescan both services
    python3 scripts/utilities/rescan_missing_media.py --search           # Rescan and search for missing
    python3 scripts/utilities/rescan_missing_media.py --service sonarr   # Sonarr only
    python3 scripts/utilities/rescan_missing_media.py --service radarr   # Radarr only
"""

import os
import sys
import requests
import argparse
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import load_env, log, get_api_key, get_headers

load_env()

SONARR_URL = os.environ.get("SONARR_URL", "http://localhost:8989")
RADARR_URL = os.environ.get("RADARR_URL", "http://localhost:7878")


def trigger_command(url, api_key, command_name, **kwargs):
    """Send a command to Sonarr/Radarr API."""
    headers = get_headers(api_key)
    payload = {"name": command_name, **kwargs}

    try:
        resp = requests.post(f"{url}/api/v3/command", headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        command_id = resp.json().get("id")
        log(f"✓ Triggered: {command_name} (Command ID: {command_id})", "SUCCESS")
        return command_id
    except Exception as e:
        log(f"✗ Failed to trigger {command_name}: {e}", "ERROR")
        return None


def check_command_status(url, api_key, command_id):
    """Check the status of a command."""
    headers = get_headers(api_key)

    try:
        resp = requests.get(f"{url}/api/v3/command/{command_id}", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("status"), data.get("message", "")
    except Exception as e:
        log(f"Failed to check command status: {e}", "WARNING")
        return None, str(e)


def get_missing_items(url, api_key, item_type="series"):
    """Get list of items with missing files."""
    headers = get_headers(api_key)
    endpoint = "/api/v3/wanted/missing" if item_type == "series" else "/api/v3/movie"

    try:
        resp = requests.get(f"{url}{endpoint}", headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if item_type == "series":
            records = data.get("records", [])
            return len(records), records
        else:
            # For Radarr, filter movies without files
            movies = [m for m in data if not m.get("hasFile")]
            return len(movies), movies
    except Exception as e:
        log(f"Failed to get missing items: {e}", "ERROR")
        return 0, []


def rescan_sonarr(api_key, search_missing=False):
    """Rescan Sonarr library and optionally search for missing episodes."""
    log("\n" + "=" * 50, "INFO")
    log("SONARR RESCAN", "INFO")
    log("=" * 50, "INFO")

    # 1. Get current missing count
    log("\n📊 Checking current status...", "INFO")
    missing_count, _ = get_missing_items(SONARR_URL, api_key, "series")
    log(f"Missing episodes before rescan: {missing_count}", "INFO")

    # 2. Trigger full library rescan
    log("\n🔄 Triggering full library rescan...", "INFO")
    cmd_id = trigger_command(SONARR_URL, api_key, "RescanSeries")

    if cmd_id:
        # Wait for completion
        log("⏳ Waiting for rescan to complete (this may take a few minutes)...", "INFO")
        for attempt in range(60):  # Wait up to 5 minutes
            status, msg = check_command_status(SONARR_URL, api_key, cmd_id)
            if status == "completed":
                log(f"✓ Rescan completed successfully!", "SUCCESS")
                if msg:
                    log(f"   Details: {msg}", "INFO")
                break
            elif status == "failed":
                log(f"✗ Rescan failed: {msg}", "ERROR")
                return
            elif status in ["queued", "started"]:
                # Show progress every 10 seconds
                if attempt % 2 == 0:
                    log(f"   Still processing... ({attempt * 5}s elapsed)", "INFO")
            time.sleep(5)
        else:
            log("⚠ Rescan is still running (timed out waiting)", "WARNING")
            log(
                "   Check System → Tasks in the Sonarr UI to monitor progress",
                "INFO",
            )

    # 3. Check new missing count
    log("\n📊 Re-checking status...", "INFO")
    time.sleep(2)
    new_missing_count, missing_items = get_missing_items(SONARR_URL, api_key, "series")
    log(f"Missing episodes after rescan: {new_missing_count}", "INFO")

    if new_missing_count < missing_count:
        diff = missing_count - new_missing_count
        log(f"✓ Found {diff} previously missing episodes!", "SUCCESS")
    elif new_missing_count > missing_count:
        diff = new_missing_count - missing_count
        log(f"⚠ Detected {diff} additional missing episodes", "WARNING")

    # 4. Optionally trigger automatic search
    if search_missing and new_missing_count > 0:
        log(f"\n🔍 Searching for {new_missing_count} missing episodes...", "INFO")
        search_cmd_id = trigger_command(SONARR_URL, api_key, "MissingEpisodeSearch")
        if search_cmd_id:
            log("   Search queued - check System → Tasks for progress", "SUCCESS")
            log("   This may take 30+ minutes depending on number of episodes", "INFO")
    elif new_missing_count == 0:
        log("\n✓ All episodes accounted for! No missing files.", "SUCCESS")


def rescan_radarr(api_key, search_missing=False):
    """Rescan Radarr library and optionally search for missing movies."""
    log("\n" + "=" * 50, "INFO")
    log("RADARR RESCAN", "INFO")
    log("=" * 50, "INFO")

    # 1. Get current missing count
    log("\n📊 Checking current status...", "INFO")
    missing_count, _ = get_missing_items(RADARR_URL, api_key, "movie")
    log(f"Missing movies before rescan: {missing_count}", "INFO")

    # 2. Trigger full library rescan
    log("\n🔄 Triggering full library rescan...", "INFO")
    cmd_id = trigger_command(RADARR_URL, api_key, "RescanMovie")

    if cmd_id:
        # Wait for completion
        log("⏳ Waiting for rescan to complete (this may take a few minutes)...", "INFO")
        for attempt in range(60):  # Wait up to 5 minutes
            status, msg = check_command_status(RADARR_URL, api_key, cmd_id)
            if status == "completed":
                log(f"✓ Rescan completed successfully!", "SUCCESS")
                if msg:
                    log(f"   Details: {msg}", "INFO")
                break
            elif status == "failed":
                log(f"✗ Rescan failed: {msg}", "ERROR")
                return
            elif status in ["queued", "started"]:
                # Show progress every 10 seconds
                if attempt % 2 == 0:
                    log(f"   Still processing... ({attempt * 5}s elapsed)", "INFO")
            time.sleep(5)
        else:
            log("⚠ Rescan is still running (timed out waiting)", "WARNING")
            log(
                "   Check System → Tasks in the Radarr UI to monitor progress",
                "INFO",
            )

    # 3. Check new missing count
    log("\n📊 Re-checking status...", "INFO")
    time.sleep(2)
    new_missing_count, missing_items = get_missing_items(RADARR_URL, api_key, "movie")
    log(f"Missing movies after rescan: {new_missing_count}", "INFO")

    if new_missing_count < missing_count:
        diff = missing_count - new_missing_count
        log(f"✓ Found {diff} previously missing movies!", "SUCCESS")
    elif new_missing_count > missing_count:
        diff = new_missing_count - missing_count
        log(f"⚠ Detected {diff} additional missing movies", "WARNING")

    # 4. Optionally trigger automatic search
    if search_missing and new_missing_count > 0:
        log(f"\n🔍 Searching for {new_missing_count} missing movies...", "INFO")
        search_cmd_id = trigger_command(RADARR_URL, api_key, "MissingMoviesSearch")
        if search_cmd_id:
            log("   Search queued - check System → Tasks for progress", "SUCCESS")
            log("   This may take 10+ minutes depending on number of movies", "INFO")
    elif new_missing_count == 0:
        log("\n✓ All movies accounted for! No missing files.", "SUCCESS")


def main():
    parser = argparse.ArgumentParser(
        description="Rescan Sonarr/Radarr libraries and search for missing media",
        epilog="""
Examples:
  %(prog)s                          # Rescan both services, report only
  %(prog)s --search                 # Rescan and auto-search for missing
  %(prog)s --service sonarr         # Rescan Sonarr only
  %(prog)s --service radarr --search # Rescan and search Radarr only
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--service",
        choices=["sonarr", "radarr", "both"],
        default="both",
        help="Which service to rescan (default: both)",
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="Automatically search for missing media after rescan",
    )

    args = parser.parse_args()

    log("\n" + "=" * 50, "INFO")
    log("MEDIA LIBRARY RESCAN UTILITY", "INFO")
    log("=" * 50, "INFO")
    log(f"Service: {args.service.upper()}", "INFO")
    log(f"Auto-search: {'YES' if args.search else 'NO'}", "INFO")

    try:
        if args.service in ["sonarr", "both"]:
            sonarr_api_key = get_api_key("SONARR_API_KEY")
            rescan_sonarr(sonarr_api_key, args.search)

        if args.service in ["radarr", "both"]:
            if args.service == "both":
                log("\n", "INFO")  # Add spacing between services
            radarr_api_key = get_api_key("RADARR_API_KEY")
            rescan_radarr(radarr_api_key, args.search)

        log("\n" + "=" * 50, "SUCCESS")
        log("✓ RESCAN COMPLETE!", "SUCCESS")
        log("=" * 50, "SUCCESS")
        log("\nℹ️  Monitor ongoing tasks:", "INFO")
        log("   Sonarr: http://localhost:8989/system/tasks", "INFO")
        log("   Radarr: http://localhost:7878/system/tasks", "INFO")

    except KeyboardInterrupt:
        log("\n\n⚠ Interrupted by user", "WARNING")
        sys.exit(130)
    except Exception as e:
        log(f"\n✗ Unexpected error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
