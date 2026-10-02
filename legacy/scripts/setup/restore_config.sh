#!/usr/bin/env bash
#
# Restore Torrent Services Configuration
#
# Restores service configuration from a backup created by backup_config.sh
#
# Usage: ./scripts/utilities/restore_config.sh <backup_directory>
#
# Process:
# 1. Stop all services
# 2. Restore .env and config files
# 3. Start services
# 4. Print instructions for manual UI restore steps
#
# Note: Sonarr/Radarr/Prowlarr/Bazarr require one manual UI click each to restore

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check for backup directory argument
if [ -z "$1" ]; then
    echo -e "${RED}[ERROR]${NC} Usage: $0 <backup_directory>"
    echo ""
    echo "Example:"
    echo "  $0 ./backups/20251222_143000"
    echo ""
    exit 1
fi

BACKUP_DIR="$1"

# Validate backup directory
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Torrent Services Configuration Restore${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}[INFO]${NC} Restoring from: $BACKUP_DIR"
echo ""

# Check for required files
REQUIRED_FILES=(".env.backup")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$BACKUP_DIR/$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo -e "${RED}[ERROR]${NC} Missing required backup files:"
    for file in "${MISSING_FILES[@]}"; do
        echo -e "  - $file"
    done
    echo ""
    echo "This may not be a valid backup directory."
    exit 1
fi

# Confirm restore action
echo -e "${YELLOW}[WARNING]${NC} This will:"
echo "  1. Stop all Docker containers"
echo "  2. Overwrite your current .env file"
echo "  3. Replace service configurations"
echo "  4. Restart containers"
echo ""
read -p "Continue with restore? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo -e "${BLUE}[INFO]${NC} Restore cancelled by user"
    exit 0
fi

# Step 0: Stop services
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 1: Stopping Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

docker compose down
echo -e "${GREEN}[SUCCESS]${NC} All services stopped"
echo ""

# Step 1: Restore .env
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 2: Restoring Configuration Files${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cp "$BACKUP_DIR/.env.backup" .env
echo -e "${GREEN}[SUCCESS]${NC} Restored .env (secrets and API keys)"

# Step 2: Restore service configs
mkdir -p config/{sonarr,radarr,prowlarr,bazarr,qbittorrent,gluetun}

# Sonarr/Radarr/Prowlarr - Stage backups for manual UI restore
for service in sonarr radarr prowlarr; do
    BACKUP_FILE="$BACKUP_DIR/${service}_backup.zip"
    if [ -f "$BACKUP_FILE" ]; then
        # Copy to Backups directory where service can find it
        RESTORE_DIR="config/$service/Backups/manual_restore"
        mkdir -p "$RESTORE_DIR"
        cp "$BACKUP_FILE" "$RESTORE_DIR/"
        echo -e "${GREEN}[SUCCESS]${NC} Staged $service backup for UI restore"
    else
        echo -e "${YELLOW}[WARNING]${NC} No $service backup found - skipping"
    fi
done

# Bazarr - Stage backup for manual UI restore
BAZARR_BACKUP="$BACKUP_DIR/bazarr_backup.zip"
if [ -f "$BAZARR_BACKUP" ]; then
    mkdir -p config/bazarr/restore
    cp "$BAZARR_BACKUP" config/bazarr/restore/
    echo -e "${GREEN}[SUCCESS]${NC} Staged Bazarr backup for UI restore"
else
    echo -e "${YELLOW}[WARNING]${NC} No Bazarr backup found - skipping"
fi

# qBittorrent - Direct restore (no UI step needed)
QBIT_BACKUP="$BACKUP_DIR/qbittorrent_backup.tar.gz"
if [ -f "$QBIT_BACKUP" ]; then
    mkdir -p config/qbittorrent/qBittorrent
    tar -xzf "$QBIT_BACKUP" -C config/qbittorrent/qBittorrent
    echo -e "${GREEN}[SUCCESS]${NC} Restored qBittorrent torrents and config"
else
    echo -e "${YELLOW}[WARNING]${NC} No qBittorrent backup found - skipping"
fi

# Tdarr - Direct restore
TDARR_BACKUP="$BACKUP_DIR/tdarr_backup.tar.gz"
if [ -f "$TDARR_BACKUP" ]; then
    mkdir -p config/tdarr
    tar -xzf "$TDARR_BACKUP" -C config
    echo -e "${GREEN}[SUCCESS]${NC} Restored Tdarr configuration"
else
    echo -e "${YELLOW}[WARNING]${NC} No Tdarr backup found - skipping"
fi

# Jellyseerr - Direct restore
JELLYSEERR_BACKUP="$BACKUP_DIR/jellyseerr_backup.tar.gz"
if [ -f "$JELLYSEERR_BACKUP" ]; then
    mkdir -p config/jellyseerr
    tar -xzf "$JELLYSEERR_BACKUP" -C config
    echo -e "${GREEN}[SUCCESS]${NC} Restored Jellyseerr configuration"
else
    echo -e "${YELLOW}[WARNING]${NC} No Jellyseerr backup found - skipping"
fi

# Unpackerr - Skip (env-vars only, no config directory)
# NOTE: Unpackerr is configured entirely via UN_* environment variables.
# No config directory exists, so nothing to restore.
echo -e "${BLUE}[INFO]${NC} Unpackerr uses env-vars only (no config to restore)"

# Gluetun
GLUETUN_SERVERS="$BACKUP_DIR/gluetun_servers.json"
if [ -f "$GLUETUN_SERVERS" ]; then
    mkdir -p config/gluetun
    cp "$GLUETUN_SERVERS" config/gluetun/servers.json
    echo -e "${GREEN}[SUCCESS]${NC} Restored Gluetun server list"
fi

# Setup config (legacy - may not be needed)
SETUP_CONFIG="$BACKUP_DIR/setup.config.json"
if [ -f "$SETUP_CONFIG" ]; then
    mkdir -p scripts/setup
    cp "$SETUP_CONFIG" scripts/setup/setup.config.json
    echo -e "${GREEN}[SUCCESS]${NC} Restored setup configuration"
fi

# Step 3: Start services
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 3: Starting Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

docker compose up -d

echo -e "${GREEN}[SUCCESS]${NC} Services starting..."
echo ""

# Wait a moment for services to initialize
sleep 5

# Step 4: Manual restore instructions
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Step 4: Manual UI Restore Required${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "The following services require a manual restore step via their web UI:"
echo ""

# Check which services need manual restore
MANUAL_SERVICES=()
for service in sonarr radarr prowlarr; do
    if [ -f "$BACKUP_DIR/${service}_backup.zip" ]; then
        MANUAL_SERVICES+=("$service")
    fi
done
if [ -f "$BACKUP_DIR/bazarr_backup.zip" ]; then
    MANUAL_SERVICES+=("bazarr")
fi

if [ ${#MANUAL_SERVICES[@]} -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS]${NC} No manual steps required - all services restored automatically"
else
    # Get ports from .env
    source .env 2>/dev/null || true

    SONARR_PORT="${SONARR_PORT:-8989}"
    RADARR_PORT="${RADARR_PORT:-7878}"
    PROWLARR_PORT="${PROWLARR_PORT:-9696}"
    BAZARR_PORT="${BAZARR_PORT:-6767}"

    echo "For each service below:"
    echo "  1. Wait for service to be healthy (check with: docker compose ps)"
    echo "  2. Open the service URL in your browser"
    echo "  3. Navigate to: System → Backup"
    echo "  4. Find the backup file in the list"
    echo "  5. Click the 'Restore' button (service will restart automatically)"
    echo ""

    for service in "${MANUAL_SERVICES[@]}"; do
        case $service in
            sonarr)
                echo -e "${YELLOW}► Sonarr:${NC} http://localhost:$SONARR_PORT"
                ;;
            radarr)
                echo -e "${YELLOW}► Radarr:${NC} http://localhost:$RADARR_PORT"
                ;;
            prowlarr)
                echo -e "${YELLOW}► Prowlarr:${NC} http://localhost:$PROWLARR_PORT"
                ;;
            bazarr)
                echo -e "${YELLOW}► Bazarr:${NC} http://localhost:$BAZARR_PORT"
                ;;
        esac
    done

    echo ""
    echo -e "${BLUE}[INFO]${NC} Tip: You can check service health with:"
    echo -e "  ${YELLOW}docker compose ps${NC}"
    echo ""
fi

# Step 5: Verification
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 5: Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "After completing manual UI restores (if any), verify:"
echo ""
echo "  1. All services are healthy:"
echo -e "     ${YELLOW}docker compose ps${NC}"
echo ""
echo "  2. qBittorrent shows your torrents:"
echo -e "     ${YELLOW}http://localhost:${QBITTORRENT_PORT:-8080}${NC}"
echo ""
echo "  3. Inter-service connections work:"
echo "     - Prowlarr can sync to Sonarr/Radarr"
echo "     - Sonarr/Radarr can connect to qBittorrent"
echo "     - Bazarr can connect to Sonarr/Radarr"
echo ""
echo -e "${GREEN}[SUCCESS] Restore process complete${NC}"
echo ""
echo "See scripts/utilities/SETUP_GUIDE.md for troubleshooting help."
echo ""
