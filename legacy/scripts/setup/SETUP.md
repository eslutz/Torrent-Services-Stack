# Torrent Services Setup Guide

This guide covers two setup scenarios:
1. **Fresh Installation** - Setting up services from scratch
2. **Restore from Backup** - Restoring a previous configuration

---

## Prerequisites

Before starting, ensure you have:

- **Docker** and **Docker Compose** installed
- **VPN credentials** (ProtonVPN WireGuard or OpenVPN)
- **Indexer credentials** (e.g., IPTorrents cookie)
- **Media storage** directory created with proper permissions

---

## Quick Start: Restore from Backup

If you have an existing backup, this is the fastest path:

```bash
# 1. Clone repository (if new host)
git clone https://github.com/eslutz/Torrent-Services-Stack.git
cd Torrent-Services

# 2. Restore configuration
./scripts/utilities/restore_config.sh ./backups/20251222_143000

# 3. Wait for services to start (~30 seconds)
docker compose ps

# 4. Complete manual UI restores (see output instructions)
# - Sonarr: http://localhost:8989 → System → Backup → Restore
# - Radarr: http://localhost:7878 → System → Backup → Restore
# - Prowlarr: http://localhost:9696 → System → Backup → Restore
# - Bazarr: http://localhost:6767 → System → Backup → Restore

# 5. Verify all services are healthy
docker compose ps
```

**Total Time:** ~5 minutes (30s automated + 2-3 minutes for 4 UI clicks)

---

## Fresh Installation (No Backup)

### Step 1: Configure Environment Variables

Create a `.env` file with your configuration:

```bash
cp .env.example .env  # If example exists, otherwise create from scratch
```

#### Required Variables

Edit `.env` with your values:

```bash
# VPN Configuration (ProtonVPN WireGuard example)
VPN_TYPE=wireguard
WIREGUARD_PRIVATE_KEY=your_private_key_here
WIREGUARD_ADDRESSES=10.2.0.2/32
SERVER_COUNTRIES=Switzerland
VPN_SERVICE_PROVIDER=protonvpn

# Media Paths (adjust to your system)
TORRENT_MEDIA_DIR=/path/to/your/media  # e.g., /mnt/media or /Users/you/media
DATA_DIR=/media                        # Internal container path (usually don't change)

# Service Credentials
SERVICE_USER=admin
SERVICE_PASSWORD=your_secure_password_here
QBITTORRENT_PASSWORD=your_qbit_password_here

# Indexer Credentials (example for IPTorrents)
IPTORRENTS_COOKIE=your_iptorrents_cookie_here

# Port Configuration (defaults shown - adjust if needed)
SONARR_PORT=8989
RADARR_PORT=7878
PROWLARR_PORT=9696
BAZARR_PORT=6767
QBITTORRENT_PORT=8080
GLUETUN_PORT=8000

# User/Group IDs (run `id` in terminal to find yours)
PUID=1000
PGID=1000
```

#### Optional Variables

```bash
# Monitoring (Prometheus exporters)
ENABLE_MONITORING=false

# Windows/macOS Host (for monitoring only)
HOST_PROJECT_DIR=/Users/you/Docker/Torrent-Services
```

### Step 2: Start Services

```bash
# Start all services in detached mode
docker compose up -d

# Monitor startup logs (Ctrl+C to exit)
docker compose logs -f

# Check service health (wait until all show "healthy")
docker compose ps
```

**Expected startup time:** 2-5 minutes for all services to reach `healthy` state.

### Step 3: Initial Service Configuration

Since you don't have a backup, you'll configure each service manually through their web interfaces. This becomes your "known-good state" that you'll back up later.

#### 3.1 Gluetun (VPN)

Verify VPN connection:

```bash
# Check Gluetun logs for successful connection
docker logs gluetun --tail 20

# Should see: "ip 203.0.113.42" (your VPN IP)
```

No manual configuration needed—everything is in `.env`.

#### 3.2 qBittorrent

1. Open http://localhost:8080
2. Login with credentials from `.env`:
   - Username: `admin`
   - Password: `QBITTORRENT_PASSWORD` value
3. Go to **Settings** (gear icon) → **Downloads**:
   - Default Save Path: `/media/downloads`
   - Keep incomplete torrents in: `/media/downloads/incomplete`
   - Enable: "Create subfolder for torrents with multiple files"
4. Go to **BitTorrent**:
   - Enable: "Use DHT"
   - Protocol encryption: "Require encryption"
5. **Create categories** (right-click Category list):
   - `movies` → Save path: `/media/downloads/movies`
   - `tv shows` → Save path: `/media/downloads/tv`
6. Click **Save**

#### 3.3 Prowlarr (Indexer Management)

1. Open http://localhost:9696
2. **First-time authentication setup:**
   - Username: `SERVICE_USER` from `.env`
   - Password: `SERVICE_PASSWORD` from `.env`
3. Go to **Settings** → **General**:
   - Authentication: "Forms (Login page)"
4. Go to **Indexers** → **Add Indexer**:
   - Search for your indexers (e.g., "IPTorrents")
   - Configure with credentials (e.g., cookie from `.env`)
   - Set priority and tags as desired
5. Go to **Settings** → **Apps** → **Add Application**:
   - Add Sonarr:
     - Prowlarr Server: `http://localhost:9696`
     - Sonarr Server: `http://sonarr:8989`
     - API Key: (get from Sonarr → Settings → General)
   - Add Radarr:
     - Prowlarr Server: `http://localhost:9696`
     - Radarr Server: `http://radarr:7878`
     - API Key: (get from Radarr → Settings → General)

#### 3.4 Sonarr (TV Shows)

1. Open http://localhost:8989
2. **First-time authentication:**
   - Username/Password: `SERVICE_USER`/`SERVICE_PASSWORD` from `.env`
3. Go to **Settings** → **Media Management**:
   - Enable: "Use Hardlinks instead of Copy"
   - Enable: "Import Extra Files" (srt, sub)
   - Episode naming format: (set your preference)
4. Go to **Settings** → **Download Clients** → **Add** → **qBittorrent**:
   - Name: `qBittorrent`
   - Host: `gluetun` (important: not "qbittorrent"!)
   - Port: `8080`
   - Username: `admin`
   - Password: `QBITTORRENT_PASSWORD` from `.env`
   - Category: `tv shows`
5. Add **Root Folder**:
   - Settings → Media Management → Root Folders → Add
   - Path: `/media/tv`

#### 3.5 Radarr (Movies)

Same process as Sonarr, but:
- URL: http://localhost:7878
- Download client category: `movies`
- Root folder: `/media/movies`

#### 3.6 Bazarr (Subtitles)

1. Open http://localhost:6767
2. **Initial setup wizard:**
   - Username/Password: `SERVICE_USER`/`SERVICE_PASSWORD` from `.env`
   - Connect to Sonarr/Radarr (use API keys from those services)
3. Go to **Settings** → **Providers**:
   - Add subtitle providers (OpenSubtitles, Subscene, etc.)
   - Configure with credentials if required
4. Go to **Settings** → **Languages**:
   - Add language profiles (e.g., English)

### Step 4: Create Your First Backup

Once all services are configured and working:

```bash
# Create backup of your "known-good state"
./scripts/utilities/backup_config.sh

# Output: ./backups/20251222_143000/
```

**Store this backup safely!** You can now restore this exact configuration on any new host.

---

## Creating Regular Backups

Services automatically create scheduled backups, but manual backups are recommended:

### Automated Schedule

Services create backups in these locations:
- **Sonarr**: `config/sonarr/Backups/scheduled/` (daily)
- **Radarr**: `config/radarr/Backups/scheduled/` (daily)
- **Prowlarr**: `config/prowlarr/Backups/scheduled/` (daily)
- **Bazarr**: `config/bazarr/backup/` (daily)

These are automatically included when you run `backup_config.sh`.

### Manual Backup

Create a backup anytime:

```bash
# Default location (./backups/)
./scripts/utilities/backup_config.sh

# Custom location
./scripts/utilities/backup_config.sh /path/to/external/backup
```

### Backup Best Practices

1. **Before major changes:** Back up before upgrading containers or changing settings
2. **Regular schedule:** Weekly backups recommended (monthly minimum)
3. **Off-site storage:** Copy backups to external drive or cloud storage
4. **Test restores:** Periodically verify backups work by testing restore process

---

## Migrating to a New Host

### Method 1: Backup/Restore (Recommended)

On old host:
```bash
./scripts/utilities/backup_config.sh /path/to/external/drive
```

On new host:
```bash
# 1. Clone repository
git clone https://github.com/eslutz/Torrent-Services-Stack.git
cd Torrent-Services

# 2. Copy backup from external drive to ./backups/

# 3. Restore
./scripts/utilities/restore_config.sh ./backups/20251222_143000

# 4. Update .env for host-specific paths
nano .env  # Adjust TORRENT_MEDIA_DIR to match new host

# 5. Restart services
docker compose down
docker compose up -d
```

### Method 2: Direct Config Copy

If both hosts are accessible simultaneously:

```bash
# On old host
tar -czf torrent-services-config.tar.gz config/ .env

# Transfer to new host (scp, rsync, etc.)
scp torrent-services-config.tar.gz newhost:/path/to/Torrent-Services/

# On new host
cd Torrent-Services
tar -xzf torrent-services-config.tar.gz
docker compose up -d
```

---

## Troubleshooting

### Services Won't Start

**Check health status:**
```bash
docker compose ps
```

**View logs:**
```bash
# All services
docker compose logs

# Specific service
docker logs gluetun
docker logs qbittorrent
docker logs sonarr
```

**Common issues:**
- **VPN connection failed:** Check `WIREGUARD_PRIVATE_KEY` in `.env`
- **Permission errors:** Verify `PUID`/`PGID` match your user (`id` command)
- **Port conflicts:** Another service using ports 8080, 8989, etc.

### Can't Access Service UIs

**Check service is healthy:**
```bash
docker compose ps | grep healthy
```

**Check port mappings:**
```bash
docker compose ps
# Should show: 0.0.0.0:8989->8989/tcp
```

**Firewall issues:**
```bash
# macOS
sudo pfctl -d  # Disable firewall temporarily to test

# Linux
sudo ufw status
sudo ufw allow 8989/tcp  # Example for Sonarr
```

### qBittorrent Connection Fails

**Sonarr/Radarr can't connect to qBittorrent:**

1. Verify you're using `gluetun` as hostname, NOT `qbittorrent`:
   - Settings → Download Clients → qBittorrent
   - Host: `gluetun` (port: `8080`)

2. Check qBittorrent is accessible through Gluetun:
```bash
docker exec sonarr curl -I http://gluetun:8080
# Should return: HTTP/1.1 200 OK
```

### Restore Fails

**Missing .env.backup:**
```bash
# Check backup directory contents
ls -la ./backups/20251222_143000/

# Must contain .env.backup file
```

**Permission denied on config directories:**
```bash
# Fix ownership
sudo chown -R $(id -u):$(id -g) config/
```

### Port Forwarding Not Working

**Check Gluetun port file:**
```bash
docker exec gluetun cat /tmp/gluetun/forwarded_port
# Should show a port number (e.g., 54322)
```

**Verify qBittorrent is using forwarded port:**
1. Open qBittorrent UI: http://localhost:8080
2. Settings → Connection → Port used for incoming connections
3. Should match Gluetun's forwarded port

**Check Forwardarr logs:**
```bash
docker logs forwardarr --tail 20
# Should show successful port updates
```

---

## Service-Specific Notes

### Bazarr API Reliability

Bazarr's API doesn't always persist settings reliably. If settings don't save:

1. Use **UI-based configuration** instead of API
2. Verify settings saved: Settings → General → Save → Restart container
3. Check config file directly: `config/bazarr/config/config.yaml`

### qBittorrent Categories

Categories must be created after authentication is set up. If categories are missing:

1. Right-click category list in UI
2. Add category → Set save path
3. Or restore from backup (includes categories)

### API Key Changes

If you regenerate API keys (e.g., after security incident):

1. Update `.env` with new keys
2. Update inter-service connections:
   - Prowlarr → Apps → Edit Sonarr/Radarr → New API key
   - Bazarr → Settings → Sonarr/Radarr → New API key
3. Restart affected services

---

## Reference: Service URLs & Ports

| Service | Default URL | Purpose |
|---------|-------------|---------|
| **Sonarr** | http://localhost:8989 | TV show management |
| **Radarr** | http://localhost:7878 | Movie management |
| **Prowlarr** | http://localhost:9696 | Indexer management |
| **Bazarr** | http://localhost:6767 | Subtitle management |
| **qBittorrent** | http://localhost:8080 | Torrent client |
| **Gluetun** | http://localhost:8000 | VPN + control server |

---

## Next Steps

After successful setup:

1. **Configure quality profiles** in Sonarr/Radarr
2. **Add TV shows/movies** to your library
3. **Test automatic downloads** by manually searching in Prowlarr
4. **Set up backup schedule** (weekly recommended)
5. **Review logs** periodically for errors: `docker compose logs -f`

For advanced configuration, see:
- [docker-compose.yml](../../docker-compose.yml) - Service definitions
- [.env.example](../../.env.example) - All available environment variables
- [healthchecks/HEALTHCHECKS.md](../healthchecks/HEALTHCHECKS.md) - Health check details
- [utilities/UTILITIES.md](../utilities/UTILITIES.md) - Utility scripts reference

---

## Getting Help

**Before asking for help:**
1. Check service logs: `docker logs <service_name>`
2. Verify all services are healthy: `docker compose ps`
3. Review this troubleshooting section
4. Check the service's own documentation

**Common resources:**
- [Sonarr Wiki](https://wiki.servarr.com/sonarr)
- [Radarr Wiki](https://wiki.servarr.com/radarr)
- [Prowlarr Wiki](https://wiki.servarr.com/prowlarr)
- [Bazarr Wiki](https://wiki.bazarr.media/)
- [qBittorrent Manual](https://github.com/qbittorrent/qBittorrent/wiki)
- [Gluetun Wiki](https://github.com/qdm12/gluetun-wiki)
