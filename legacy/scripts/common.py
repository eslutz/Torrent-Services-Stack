import os
import json
import requests
import sys
import time

# Default timeout for HTTP requests in seconds
DEFAULT_TIMEOUT = 10

def load_env():
    """Load environment variables from .env file in the repository root."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # scripts/common.py -> root is ../
    root_dir = os.path.abspath(os.path.join(script_dir, "../"))
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
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]

                        if key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            print(f"Warning: Failed to load .env file: {e}")

def load_config(config_path=None):
    """Load configuration from a JSON file."""
    if not config_path:
        # Default to setup/setup.config.json for backward compatibility if needed,
        # or maybe we should require it.
        # Let's try to find setup.config.json relative to this file
        config_path = os.path.join(os.path.dirname(__file__), "setup", "setup.config.json")
    
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load config file {config_path}: {e}")
        sys.exit(1)

def log(msg, level="INFO"):
    """Print colored log messages."""
    colors = {
        "INFO": "\033[0;34m",
        "SUCCESS": "\033[0;32m",
        "WARNING": "\033[1;33m",
        "ERROR": "\033[0;31m",
        "NC": "\033[0m",
    }
    print(f"{colors.get(level, '')}[{level}] {msg}{colors['NC']}")

def get_api_key(env_var):
    """Get API key from environment variable."""
    api_key = os.environ.get(env_var)
    if not api_key:
        log(f"{env_var} not set in environment", "ERROR")
        sys.exit(1)
    return api_key

def get_headers(api_key, header_name="X-Api-Key"):
    """Get standard headers for API requests."""
    return {header_name: api_key, "Content-Type": "application/json"}

def wait_for_service(
    url,
    api_key,
    service_name,
    endpoint="/api/v3/system/status",
    header_name="X-Api-Key",
    max_retries=30,
    retry_delay=2,
):
    """Wait for a service to become available with detailed error reporting."""
    log(f"Waiting for {service_name} API...", "INFO")
    headers = get_headers(api_key, header_name)
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(f"{url}{endpoint}", headers=headers, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            log(f"{service_name} API is ready", "SUCCESS")
            return True
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout after {DEFAULT_TIMEOUT}s: {str(e)}"
        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection error: {str(e)}"
        except requests.exceptions.HTTPError as e:
            # Use the HTTPError's response attribute safely to avoid referencing an unbound variable
            resp = getattr(e, "response", None)
            status = resp.status_code if resp is not None else "unknown"
            last_error = f"HTTP {status}: {str(e)}"
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"

        if attempt % 5 == 0:
            log(
                f"Still waiting for {service_name} (attempt {attempt}/{max_retries}): {last_error}",
                "WARNING",
            )
        time.sleep(retry_delay)

    log(
        f"{service_name} not reachable after {max_retries} attempts. Last error: {last_error}",
        "ERROR",
    )
    sys.exit(1)

def disable_analytics(url, api_key, service_name, api_version="v3", header_name="X-Api-Key"):
    """Disable analytics for *arr services."""
    log("Checking analytics settings...", "INFO")
    headers = get_headers(api_key, header_name)
    config_url = f"{url}/api/{api_version}/config/host"

    try:
        resp = requests.get(config_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        config = resp.json()

        if config.get("analyticsEnabled") is False:
            log("Analytics already disabled", "SUCCESS")
            return

        log("Disabling analytics...", "INFO")
        config["analyticsEnabled"] = False

        resp = requests.put(config_url, headers=headers, json=config, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        log("Analytics disabled", "SUCCESS")

    except requests.exceptions.RequestException as e:
        log(f"Failed to disable analytics: {e}", "ERROR")

def configure_config_endpoint(
    url, api_key, endpoint, target_config, config_name, api_version="v3", header_name="X-Api-Key"
):
    """Generic function to configure a config endpoint (media management, naming, etc.)."""
    log(f"Configuring {config_name}...", "INFO")
    headers = get_headers(api_key, header_name)
    config_url = f"{url}/api/{api_version}/config/{endpoint}"

    if not target_config:
        return

    try:
        resp = requests.get(config_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        current_config = resp.json()

        needs_update = False
        for key, value in target_config.items():
            if key in current_config and current_config[key] != value:
                current_config[key] = value
                needs_update = True

        if needs_update:
            resp = requests.put(config_url, headers=headers, json=current_config, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            log(f"{config_name} configuration updated", "SUCCESS")
        else:
            log(f"{config_name} configuration already up to date", "SUCCESS")

    except requests.exceptions.RequestException as e:
        log(f"Failed to configure {config_name}: {e}", "ERROR")

def configure_root_folders(url, api_key, root_folders, api_version="v3", header_name="X-Api-Key"):
    """Configure root folders for *arr services."""
    log("Configuring Root Folders...", "INFO")
    headers = get_headers(api_key, header_name)
    rootfolder_url = f"{url}/api/{api_version}/rootfolder"

    try:
        response = requests.get(rootfolder_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        existing_folders = response.json()
        existing_paths = {f["path"]: f for f in existing_folders}
    except requests.exceptions.RequestException as e:
        log(f"Failed to get root folders: {e}", "ERROR")
        return

    for folder_config in root_folders:
        path = folder_config.get("path", "")
        if not path:
            log("Root folder configuration missing path", "ERROR")
            continue

        if path in existing_paths:
            log(f"Root folder {path} already exists", "SUCCESS")
            continue

        log(f"Adding root folder: {path}", "INFO")
        payload = {"path": path}

        try:
            response = requests.post(rootfolder_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            log(f"Root folder {path} created", "SUCCESS")
        except requests.exceptions.RequestException as e:
            error_msg = e.response.text if hasattr(e, "response") and e.response else str(e)
            log(f"Failed to create root folder {path}: {error_msg}", "ERROR")

def configure_download_clients(
    url, api_key, download_clients, api_version="v3", header_name="X-Api-Key"
):
    """Configure download clients for *arr services with improved error handling."""
    log("Configuring Download Clients...", "INFO")
    headers = get_headers(api_key, header_name)
    downloadclient_url = f"{url}/api/{api_version}/downloadclient"

    try:
        response = requests.get(downloadclient_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        existing_clients = response.json()
        existing_map = {c["name"]: c for c in existing_clients}
    except requests.exceptions.RequestException as e:
        log(f"Failed to get download clients: {e}", "ERROR")
        return

    for client_config in download_clients:
        name = client_config.get("name", "Unknown")
        log(f"Processing download client: {name}", "INFO")

        # Validate required fields
        if not all(key in client_config for key in ["protocol", "implementation"]):
            log(f"Download client {name} missing required configuration fields", "ERROR")
            continue

        fields = []
        missing_env_vars = []

        for field in client_config.get("fields", []):
            value = field.get("value")
            if "env" in field:
                env_val = os.environ.get(field["env"])
                if env_val:
                    value = env_val
                else:
                    missing_env_vars.append(field["env"])
                    log(
                        f"Environment variable {field['env']} not found for field {field['name']}",
                        "WARNING",
                    )

            fields.append({"name": field["name"], "value": value})

        if missing_env_vars:
            log(
                f"Download client {name} has missing environment variables: {', '.join(missing_env_vars)}",
                "WARNING",
            )

        payload = {
            "enable": True,
            "protocol": client_config["protocol"],
            "priority": client_config.get("priority", 1),
            "name": name,
            "implementation": client_config["implementation"],
            "implementationName": client_config["implementation"],
            "configContract": f"{client_config['implementation']}Settings",
            "fields": fields,
        }

        if name in existing_map:
            payload["id"] = existing_map[name]["id"]
            try:
                response = requests.put(
                    f"{downloadclient_url}/{payload['id']}",
                    headers=headers,
                    json=payload,
                    timeout=DEFAULT_TIMEOUT,
                )
                response.raise_for_status()
                log(f"Download client {name} updated", "SUCCESS")
            except requests.exceptions.RequestException as e:
                error_msg = e.response.text if hasattr(e, "response") and e.response else str(e)
                log(f"Failed to update {name}: {error_msg}", "ERROR")
        else:
            try:
                response = requests.post(
                    downloadclient_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT
                )
                response.raise_for_status()
                log(f"Download client {name} created", "SUCCESS")
            except requests.exceptions.RequestException as e:
                error_msg = e.response.text if hasattr(e, "response") and e.response else str(e)
                log(f"Failed to create {name}: {error_msg}", "ERROR")

class QBitClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.logged_in = False

    def login(self):
        if self.logged_in:
            return True
            
        url = f"{self.base_url}/api/v2/auth/login"
        data = {"username": self.username, "password": self.password}
        try:
            response = self.session.post(url, data=data)
            response.raise_for_status()
            if response.text == "Ok.":
                self.logged_in = True
                return True
        except Exception as e:
            print(f"Login error: {e}")
        return False

    def get_torrents(self, hashes=None):
        if not self.login(): return []
        url = f"{self.base_url}/api/v2/torrents/info"
        params = {}
        if hashes:
            params["hashes"] = hashes
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting torrents: {e}")
            return []

    def get_trackers(self, hash_val):
        if not self.login(): return []
        url = f"{self.base_url}/api/v2/torrents/trackers"
        params = {"hash": hash_val}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []

    def pause_torrent(self, hashes):
        if not self.login(): return
        url = f"{self.base_url}/api/v2/torrents/pause"
        self.session.post(url, data={"hashes": hashes})

    def resume_torrent(self, hashes):
        if not self.login(): return
        url = f"{self.base_url}/api/v2/torrents/resume"
        self.session.post(url, data={"hashes": hashes})

    def recheck_torrent(self, hashes):
        if not self.login(): return
        url = f"{self.base_url}/api/v2/torrents/recheck"
        self.session.post(url, data={"hashes": hashes})

    def reannounce_torrent(self, hashes):
        if not self.login(): return
        url = f"{self.base_url}/api/v2/torrents/reannounce"
        self.session.post(url, data={"hashes": hashes})

    def set_location(self, hashes, location):
        if not self.login(): return False
        url = f"{self.base_url}/api/v2/torrents/setLocation"
        response = self.session.post(url, data={"hashes": hashes, "location": location})
        return response.status_code == 200

    def delete_torrents(self, hashes, delete_files=False):
        if not self.login(): return
        url = f"{self.base_url}/api/v2/torrents/delete"
        data = {
            "hashes": hashes,
            "deleteFiles": "true" if delete_files else "false"
        }
        self.session.post(url, data=data)

    def add_torrent_file(self, file_path, save_path=None):
        if not self.login(): return False
        url = f"{self.base_url}/api/v2/torrents/add"
        files = {'torrents': open(file_path, 'rb')}
        data = {}
        if save_path:
            data['savepath'] = save_path
        try:
            self.session.post(url, files=files, data=data)
            return True
        except Exception as e:
            print(f"Error adding torrent: {e}")
            return False

    def get_preferences(self):
        if not self.login(): return {}
        url = f"{self.base_url}/api/v2/app/preferences"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting preferences: {e}")
            return {}

    def set_preferences(self, prefs):
        if not self.login(): return False
        url = f"{self.base_url}/api/v2/app/setPreferences"
        try:
            # qBittorrent expects 'json' parameter with JSON string
            self.session.post(url, data={"json": json.dumps(prefs)})
            return True
        except Exception as e:
            print(f"Error setting preferences: {e}")
            return False

    def create_category(self, category):
        if not self.login(): return False
        url = f"{self.base_url}/api/v2/torrents/createCategory"
        try:
            self.session.post(url, data={"category": category})
            return True
        except Exception as e:
            print(f"Error creating category {category}: {e}")
            return False

    def set_category_save_path(self, category, save_path):
        if not self.login(): return False
        url = f"{self.base_url}/api/v2/torrents/editCategory"
        try:
            self.session.post(url, data={"category": category, "savePath": save_path})
            return True
        except Exception as e:
            print(f"Error setting category save path: {e}")
            return False

    def get_categories(self):
        """Get all categories with their save paths."""
        if not self.login(): return {}
        url = f"{self.base_url}/api/v2/torrents/categories"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting categories: {e}")
            return {}

    def get_torrents(self, filter_by=None):
        """Get all torrents or filter by state (e.g., 'downloading', 'seeding')."""
        if not self.login(): return []
        url = f"{self.base_url}/api/v2/torrents/info"
        params = {"filter": filter_by} if filter_by else {}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting torrents: {e}")
            return []

    def pause_torrents(self, hashes):
        """Pause torrents by hash list."""
        if not self.login(): return False
        url = f"{self.base_url}/api/v2/torrents/pause"
        try:
            hash_string = "|".join(hashes) if isinstance(hashes, list) else hashes
            self.session.post(url, data={"hashes": hash_string})
            return True
        except Exception as e:
            print(f"Error pausing torrents: {e}")
            return False

    def resume_torrents(self, hashes):
        """Resume torrents by hash list."""
        if not self.login(): return False
        url = f"{self.base_url}/api/v2/torrents/resume"
        try:
            hash_string = "|".join(hashes) if isinstance(hashes, list) else hashes
            self.session.post(url, data={"hashes": hash_string})
            return True
        except Exception as e:
            print(f"Error resuming torrents: {e}")
            return False

    def set_torrent_category(self, hashes, category):
        """Set category for torrents."""
        if not self.login(): return False
        url = f"{self.base_url}/api/v2/torrents/setCategory"
        try:
            hash_string = "|".join(hashes) if isinstance(hashes, list) else hashes
            self.session.post(url, data={"hashes": hash_string, "category": category})
            return True
        except Exception as e:
            print(f"Error setting category: {e}")
            return False

class Config:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.root_dir = os.path.abspath(os.path.join(self.script_dir, "../"))
        self.env_path = os.path.join(self.root_dir, ".env")
        self.config_path = os.path.join(self.script_dir, "setup", "setup.config.json")
        
        self.env = self._load_env()
        self.settings = self._load_config()
        
        self.qbit_user = self.env.get("SERVICE_USER", "admin")
        self.qbit_pass = self.env.get("QBITTORRENT_PASSWORD")
        
        # Extract qBittorrent URL from settings or default
        # setup.config.json might not have qbittorrent section, so default to localhost:8080
        self.base_url = "http://localhost:8080"
        if "qbittorrent" in self.settings and "url" in self.settings["qbittorrent"]:
             self.base_url = self.settings["qbittorrent"]["url"]
        
        # These paths are specific to the host machine for troubleshooting scripts
        # We can default them or look for env vars
        self.bt_backup_path = os.environ.get("BT_BACKUP_PATH")
        self.default_save_path = os.environ.get("DEFAULT_SAVE_PATH", "/media/downloads")
        self.default_scan_path = os.environ.get("DEFAULT_SCAN_PATH")

    def _load_env(self):
        env_vars = {}
        if os.path.exists(self.env_path):
            with open(self.env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        env_vars[key.strip()] = value
        return env_vars

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return json.load(f)
        return {}
