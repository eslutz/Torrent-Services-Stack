#!/usr/bin/env bash
#
# Backup Torrent Services Configuration
#
# Creates a timestamped backup directory containing:
# - Service-native backup ZIPs (Sonarr/Radarr/Prowlarr/Bazarr)
# - qBittorrent torrent state and configuration
# - Environment variables (.env)
# - Setup configuration (setup.config.json)
# - Gluetun server list (if customized)
#
# Usage: ./scripts/utilities/backup_config.sh [output_directory]

set -e  # Exit on error

# Default backup location
BACKUP_BASE="${1:-./backups}"
BACKUP_DIR="$BACKUP_BASE/$(date +%Y%m%d_%H%M%S)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Torrent Services Configuration Backup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}[INFO]${NC} Creating backup at: $BACKUP_DIR"
echo ""

# 1. Backup .env file (contains all secrets)
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/.env.backup"
    echo -e "${GREEN}[SUCCESS]${NC} Backed up .env (secrets and API keys)"
else
    echo -e "${RED}[ERROR]${NC} No .env file found - cannot create backup"
    exit 1
fi

# 2. Backup service-native backups
echo ""
echo -e "${BLUE}[INFO]${NC} Backing up service configurations..."

# Sonarr/Radarr/Prowlarr - Copy latest scheduled backup
for service in sonarr radarr prowlarr; do
    BACKUP_PATH="config/$service/Backups/scheduled"
    if [ -d "$BACKUP_PATH" ]; then
        LATEST=$(find "$BACKUP_PATH" -maxdepth 1 -name '*.zip' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
        if [ -n "$LATEST" ]; then
            cp "$LATEST" "$BACKUP_DIR/${service}_backup.zip"
            FILENAME=$(basename "$LATEST")
            echo -e "${GREEN}[SUCCESS]${NC} Backed up $service: $FILENAME"
        else
            echo -e "${YELLOW}[WARNING]${NC} No $service backup found in $BACKUP_PATH"
        fi
    else
        echo -e "${YELLOW}[WARNING]${NC} $service backup directory not found"
    fi
done

# Bazarr - Copy latest backup
BAZARR_BACKUP_PATH="config/bazarr/backup"
if [ -d "$BAZARR_BACKUP_PATH" ]; then
    BAZARR_LATEST=$(find "$BAZARR_BACKUP_PATH" -maxdepth 1 -name '*.zip' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    if [ -n "$BAZARR_LATEST" ]; then
        cp "$BAZARR_LATEST" "$BACKUP_DIR/bazarr_backup.zip"
        FILENAME=$(basename "$BAZARR_LATEST")
        echo -e "${GREEN}[SUCCESS]${NC} Backed up Bazarr: $FILENAME"
    else
        echo -e "${YELLOW}[WARNING]${NC} No Bazarr backup found in $BAZARR_BACKUP_PATH"
    fi
else
    echo -e "${YELLOW}[WARNING]${NC} Bazarr backup directory not found"
fi

# 3. Backup qBittorrent (no native backup system)
echo ""
echo -e "${BLUE}[INFO]${NC} Backing up qBittorrent configuration..."

QBIT_CONFIG_DIR="config/qbittorrent/qBittorrent"
if [ -d "$QBIT_CONFIG_DIR" ]; then
    # Create tar of BT_backup (torrent state) and qBittorrent.conf (preferences)
    tar -czf "$BACKUP_DIR/qbittorrent_backup.tar.gz" \
        -C config/qbittorrent/qBittorrent \
        BT_backup \
        config/qBittorrent.conf \
        2>/dev/null || true

    if [ -f "$BACKUP_DIR/qbittorrent_backup.tar.gz" ]; then
        SIZE=$(du -h "$BACKUP_DIR/qbittorrent_backup.tar.gz" | cut -f1)
        echo -e "${GREEN}[SUCCESS]${NC} Backed up qBittorrent torrents and config ($SIZE)"
    else
        echo -e "${YELLOW}[WARNING]${NC} Failed to create qBittorrent backup"
    fi
else
    echo -e "${YELLOW}[WARNING]${NC} qBittorrent config directory not found"
fi

# 4. Backup Gluetun (minimal - only servers.json if customized)
echo ""
GLUETUN_SERVERS="config/gluetun/servers.json"
if [ -f "$GLUETUN_SERVERS" ]; then
    cp "$GLUETUN_SERVERS" "$BACKUP_DIR/gluetun_servers.json"
    echo -e "${GREEN}[SUCCESS]${NC} Backed up Gluetun server list"
else
    echo -e "${BLUE}[INFO]${NC} No custom Gluetun server list found (using defaults)"
fi

# 5. Backup Tdarr (configs and server data)
echo ""
echo -e "${BLUE}[INFO]${NC} Backing up Tdarr configuration..."

TDARR_CONFIG_DIR="config/tdarr"
if [ -d "$TDARR_CONFIG_DIR" ]; then
    # Create tar of Tdarr config directories
    tar -czf "$BACKUP_DIR/tdarr_backup.tar.gz" \
        -C config \
        tdarr/server \
        tdarr/configs \
        2>/dev/null || true

    if [ -f "$BACKUP_DIR/tdarr_backup.tar.gz" ]; then
        SIZE=$(du -h "$BACKUP_DIR/tdarr_backup.tar.gz" | cut -f1)
        echo -e "${GREEN}[SUCCESS]${NC} Backed up Tdarr configuration ($SIZE)"
    else
        echo -e "${YELLOW}[WARNING]${NC} Failed to create Tdarr backup"
    fi
else
    echo -e "${YELLOW}[WARNING]${NC} Tdarr config directory not found"
fi

# 6. Backup Overseerr
echo ""
OVERSEERR_CONFIG_DIR="config/overseerr"
if [ -d "$OVERSEERR_CONFIG_DIR" ]; then
    tar -czf "$BACKUP_DIR/overseerr_backup.tar.gz" \
        -C config \
        overseerr \
        2>/dev/null || true

    if [ -f "$BACKUP_DIR/overseerr_backup.tar.gz" ]; then
        SIZE=$(du -h "$BACKUP_DIR/overseerr_backup.tar.gz" | cut -f1)
        echo -e "${GREEN}[SUCCESS]${NC} Backed up Overseerr configuration ($SIZE)"
    else
        echo -e "${YELLOW}[WARNING]${NC} Failed to create Overseerr backup"
    fi
else
    echo -e "${YELLOW}[WARNING]${NC} Overseerr config directory not found"
fi

# 8. Unpackerr - Skip (env-vars only, no config directory)
# NOTE: Unpackerr is configured entirely via UN_* environment variables.
# No config directory exists, so nothing to back up.
echo ""
echo -e "${BLUE}[INFO]${NC} Unpackerr uses env-vars only (no config to back up)"

# 9. Backup setup configuration
echo ""
SETUP_CONFIG="scripts/setup/setup.config.json"
if [ -f "$SETUP_CONFIG" ]; then
    cp "$SETUP_CONFIG" "$BACKUP_DIR/setup.config.json"
    echo -e "${GREEN}[SUCCESS]${NC} Backed up setup configuration"
else
    echo -e "${YELLOW}[WARNING]${NC} No setup.config.json found"
fi

# 10. Create backup manifest
echo ""
echo -e "${BLUE}[INFO]${NC} Creating backup manifest..."

cat > "$BACKUP_DIR/MANIFEST.txt" << EOF
Torrent Services Backup
Created: $(date)
Hostname: $(hostname)
Docker Compose Project: $(basename "$(pwd)")

Contents:
- .env.backup (secrets, API keys, credentials)
- sonarr_backup.zip (series library, indexers, settings)
- radarr_backup.zip (movie library, indexers, settings)
- prowlarr_backup.zip (indexer definitions, sync settings)
- bazarr_backup.zip (subtitle providers, language profiles)
- qbittorrent_backup.tar.gz (torrent state, categories, preferences)
- tdarr_backup.tar.gz (transcode flows, nodes, settings)
- jellyseerr_backup.tar.gz (request management, user settings)
- gluetun_servers.json (VPN server list - if customized)
- setup.config.json (legacy programmatic setup config)

Note: Unpackerr is configured via environment variables only (no config directory).

To restore this backup:
./scripts/utilities/restore_config.sh $BACKUP_DIR

See SETUP_GUIDE.md for detailed instructions.
EOF

echo -e "${GREEN}[SUCCESS]${NC} Created backup manifest"

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}[SUCCESS] Backup Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Location: ${BLUE}$BACKUP_DIR${NC}"
echo -e "Total Size: ${BLUE}$TOTAL_SIZE${NC}"
echo ""
echo -e "To restore: ${YELLOW}./scripts/utilities/restore_config.sh $BACKUP_DIR${NC}"
echo -e "View manifest: ${YELLOW}cat $BACKUP_DIR/MANIFEST.txt${NC}"
echo ""
