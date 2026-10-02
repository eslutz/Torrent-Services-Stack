# Utility Scripts

## manage_storage.py

This script automates the process of adding or removing storage volumes for the torrent services stack. It handles configuration updates across Docker, environment variables, and the applications themselves.

### Features

*   **Automated Configuration**: Updates `.env` and `docker-compose.yml` to mount new drives.
*   **Service Integration**: Adds/Removes root folders in Sonarr and Radarr.
*   **qBittorrent Management**: Updates save paths and migrates active/incomplete downloads to the new storage location.
*   **Zero Downtime**: Automatically restarts containers to apply volume changes.

### Usage

**Add a New Drive**

Provide the absolute path to the mount point on the host machine. The script will automatically assign it a mount point inside the containers (e.g., `/media2`, `/media3`).

```bash
python3 scripts/utilities/manage_storage.py --path /Volumes/NewDrive --action add
```

**Remove a Drive**

Provide the same path used when adding the drive.

```bash
python3 scripts/utilities/manage_storage.py --path /Volumes/NewDrive --action remove
```

### Workflow

**On Add:**
1.  **Environment**: Scans `.env` for the next available `DATA_DIR_X` index and adds the new path.
2.  **Docker**: Updates `docker-compose.yml` to mount the new path to `qbittorrent`, `sonarr`, `radarr`, and `bazarr`.
3.  **Restart**: Restarts containers to apply the new mounts.
4.  **Apps**:
    *   Adds the new TV path to Sonarr.
    *   Adds the new Movies path to Radarr.
    *   Updates qBittorrent to save new downloads to the new drive.
    *   Moves any **incomplete/active** downloads to the new drive to prevent filling up the old storage.

**On Remove:**
1.  **Environment**: Removes the corresponding `DATA_DIR_X` variable from `.env`.
2.  **Docker**: Removes the volume mount from `docker-compose.yml`.
3.  **Restart**: Restarts containers.
4.  **Apps**:
    *   Removes the root folder from Sonarr and Radarr.
    *   Reverts qBittorrent save paths to the default `/media`.
    *   Moves any **incomplete/active** downloads back to `/media`.

## vpn_speedtest.py

This script performs a manual VPN sanity check and throughput test from inside the qBittorrent container. It compares the host's public IP with the container's public IP to confirm VPN egress and runs a download/upload speed test.

### Features

*   **VPN Verification**: Compares Host IP vs Container IP to ensure traffic is routed through the VPN.
*   **Precision Speed Test**: Uses `curl`'s internal JSON metrics for accurate throughput measurement (no text parsing).
*   **JSON Output**: Supports `--json` flag for machine-readable output, useful for monitoring dashboards.
*   **Customizable**: CLI arguments to specify container name and test file sizes.

### Usage

**Standard Run:**

```bash
python3 scripts/utilities/vpn_speedtest.py
```

**Custom Options:**

```bash
# Test with larger files or different container
python3 scripts/utilities/vpn_speedtest.py --dl-size 1GB --ul-size 50MB --container gluetun
```

**JSON Output (for automation):**

```bash
python3 scripts/utilities/vpn_speedtest.py --json
```

**Example Output:**

```text
==========================================
VPN Speed Test: qbittorrent
==========================================

--- 🔒 VPN Status ---
Host IP:      1.2.3.4
Container IP: 5.6.7.8
Status:       SECURE (IPs differ)
Location:     Amsterdam, NL (Mullvad)

--- 🚀 Speed Test ---
Download (100MB):  850.50 Mbps [1s]
Upload (25MB):    120.20 Mbps [2s]

==========================================
```

## check_torrent_status.py

View the status of your torrents directly from the terminal.

### Usage

*   **List all torrents:**
    ```bash
    python3 scripts/utilities/check_torrent_status.py
    ```

*   **Inspect a specific torrent:**
    ```bash
    python3 scripts/utilities/check_torrent_status.py inspect --query "Matrix"
    ```

*   **Analyze stalled torrents:**
    ```bash
    python3 scripts/utilities/check_torrent_status.py stalled
    ```

## manage_torrents.py

Perform actions to fix or manage torrents.

### Usage

*   **Fix Save Paths:**
    Updates torrents with incorrect paths (e.g., `/downloads/incomplete`) to the default save path.
    ```bash
    python3 scripts/utilities/manage_torrents.py fix-paths
    ```

*   **Delete Broken Torrents:**
    Deletes stalled torrents that have no working trackers.
    ```bash
    python3 scripts/utilities/manage_torrents.py delete-broken
    ```

## rescan_missing_media.py

Rescan Sonarr/Radarr libraries to detect missing files and optionally trigger automatic searches to re-download them.

### Features

*   **Detects Missing Media**: Compares database records against actual files on disk
*   **Progress Tracking**: Shows before/after missing counts and waits for completion
*   **Automatic Search**: Optionally queues downloads for missing episodes/movies
*   **Selective Service**: Can target Sonarr, Radarr, or both

### Usage

> **Note:** Use `venv/bin/python3` instead of `python3` when running locally outside Docker.

*   **Rescan both services (detect only):**
    ```bash
    venv/bin/python3 scripts/utilities/rescan_missing_media.py
    ```

*   **Rescan and auto-search for missing:**
    ```bash
    venv/bin/python3 scripts/utilities/rescan_missing_media.py --search
    ```

*   **Rescan only Sonarr:**
    ```bash
    venv/bin/python3 scripts/utilities/rescan_missing_media.py --service sonarr --search
    ```

*   **Rescan only Radarr:**
    ```bash
    venv/bin/python3 scripts/utilities/rescan_missing_media.py --service radarr --search
    ```

### When to Use

*   Files deleted from disk but still marked as downloaded in Sonarr/Radarr
*   After restoring from backup
*   After moving media between drives
*   Periodic maintenance to verify library integrity

### Alternative Methods

**UI Method:**
- **Sonarr:** System → Tasks → Scan Library Files → Run, then Wanted → Missing → Search All
- **Radarr:** System → Tasks → Update Movie Library → Run, then Movies → Missing → Search All

**API Method:**
```bash
# Load environment variables first
source .env

# Sonarr: Rescan library
curl -X POST "http://localhost:8989/api/v3/command" \
  -H "X-Api-Key: $SONARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "RescanSeries"}'

# Sonarr: Search for missing (after rescan completes)
curl -X POST "http://localhost:8989/api/v3/command" \
  -H "X-Api-Key: $SONARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "MissingEpisodeSearch"}'

# Radarr: Rescan library
curl -X POST "http://localhost:7878/api/v3/command" \
  -H "X-Api-Key: $RADARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "RescanMovie"}'

# Radarr: Search for missing (after rescan completes)
curl -X POST "http://localhost:7878/api/v3/command" \
  -H "X-Api-Key: $RADARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "MissingMoviesSearch"}'
```

### Prevention Settings

Enable these to automatically detect missing files:

**Sonarr:** Settings → Media Management
- ✓ Scan Series Folder After Refresh
- ✓ Rescan Series Folder After Refresh
- ✓ Unmonitor Deleted Episodes

**Radarr:** Settings → Media Management
- ✓ Scan Movie Folder
- ✓ Rescan Movie Folder After Refresh
- ✓ Unmonitor Deleted Movies

## check_qbittorrent_config.py

Dumps the current qBittorrent preferences to the console. Useful for verifying settings or debugging configuration issues.

### Usage

```bash
python3 scripts/utilities/check_qbittorrent_config.py
```

## sync_api_keys.py

Syncs and validates API keys between services. This script handles:
1. **Prowlarr → Sonarr/Radarr**: Validates and updates Prowlarr API keys in indexers
2. **Environment Validation**: Ensures all required API keys are present

### Usage

```bash
python3 scripts/utilities/sync_api_keys.py
```

The script will:
1. Validate Prowlarr API key exists in `.env`
2. Sync Prowlarr API keys to Sonarr/Radarr indexers
3. Test each updated indexer to ensure proper connectivity

### When to Use

- When Prowlarr API keys need to be synced to Sonarr/Radarr
- After adding new indexers in Prowlarr
- For troubleshooting API authentication issues
- When restoring from backup

## start_tdarr_node.sh

Automatically starts additional Tdarr transcode nodes with unique auto-generated names. Eliminates the need to manually specify project names or track node IDs.

### Features

- **Auto-generated unique names**: Uses timestamp + random number for container/node names
- **Configurable resources**: Set CPU/GPU workers, memory limits, and CPU limits per node
- **No manual tracking**: Each node gets a globally unique identifier
- **Easy to use**: Single command to add more transcode capacity

### Usage

**Start with defaults:**
```bash
./scripts/utilities/start_tdarr_node.sh
```

**Start with custom settings:**
```bash
# More CPU workers and memory
./scripts/utilities/start_tdarr_node.sh --cpu-workers 4 --mem-limit 4g

# Enable GPU transcoding
./scripts/utilities/start_tdarr_node.sh --gpu-workers 1 --cpus 4.0

# Full customization
./scripts/utilities/start_tdarr_node.sh \
  --cpu-workers 4 \
  --gpu-workers 1 \
  --mem-limit 4g \
  --cpus 4.0
```

### Default Values

- CPU Workers: 2
- GPU Workers: 0
- Memory Limit: 2g
- CPU Limit: 2.0

### Output

The script displays:
- Generated container name (e.g., `tdarr-node-1735436789123`)
- Node ID used by Tdarr server
- Configuration settings
- Commands to view logs or stop the node

## manage_tdarr_nodes.sh

Manages running Tdarr nodes - list, stop specific nodes, or stop all additional nodes.

### Features

- **List all nodes**: View all running Tdarr transcode nodes
- **Stop specific node**: Stop a node by container name or unique ID
- **Stop all nodes**: Stop all additional nodes (keeps main node running)
- **Safe operations**: Properly cleans up docker-compose resources

### Usage

**List all running nodes:**
```bash
./scripts/utilities/manage_tdarr_nodes.sh list
# or just
./scripts/utilities/manage_tdarr_nodes.sh
```

**Stop a specific node:**
```bash
# Using the unique ID from the list command
./scripts/utilities/manage_tdarr_nodes.sh stop 1735436789123

# Or using full container name
./scripts/utilities/manage_tdarr_nodes.sh stop tdarr-node-1735436789123
```

**Stop all additional nodes:**
```bash
./scripts/utilities/manage_tdarr_nodes.sh stop-all
```
This will prompt for confirmation before stopping all nodes. The main `tdarr-node` container remains running.

### When to Use

- **Add nodes**: When transcode queue is growing and you need more processing power
- **Remove nodes**: When queue is empty or you want to free up system resources
- **Monitor**: Check which nodes are running and their status
- **Maintenance**: Clean up nodes that are no longer needed

### Workflow Example

```bash
# 1. Start a few nodes during high activity
./scripts/utilities/start_tdarr_node.sh
./scripts/utilities/start_tdarr_node.sh --cpu-workers 4
./scripts/utilities/start_tdarr_node.sh --cpu-workers 4

# 2. Check what's running
./scripts/utilities/manage_tdarr_nodes.sh list

# 3. Stop a specific node when done
./scripts/utilities/manage_tdarr_nodes.sh stop 1735436789123

# 4. Or stop all additional nodes
./scripts/utilities/manage_tdarr_nodes.sh stop-all
```

