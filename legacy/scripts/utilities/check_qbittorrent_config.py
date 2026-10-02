import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import Config, QBitClient

def main():
    config = Config()
    client = QBitClient(config.base_url, config.qbit_user, config.qbit_pass)
    
    print("Fetching preferences from qBittorrent...")
    prefs = client.get_preferences()
    
    if not prefs:
        print("Failed to fetch preferences.")
        return

    # Keys related to torrent file management
    keys_of_interest = [
        "auto_delete_mode",
        "preallocate_all",
        "incomplete_files_ext",
        "export_dir",
        "export_dir_fin",
        "temp_path",
        "save_path",
        "scan_dirs"
    ]
    
    print("\n--- Relevant Settings ---")
    for key, value in prefs.items():
        if key in keys_of_interest or "dir" in key or "path" in key or "delete" in key:
             print(f"{key}: {value}")

    print("\n--- All Settings (JSON) ---")
    print(json.dumps(prefs, indent=2))

if __name__ == "__main__":
    main()
