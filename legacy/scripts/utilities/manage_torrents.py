import argparse
import sys
import os
import glob
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import Config, QBitClient

def fix_paths(client, config):
    torrents = client.get_torrents()
    count = 0
    for t in torrents:
        # Logic from fix_paths_bulk.py
        # If save_path is wrong, we might need to delete and re-add or setLocation
        # The previous script deleted and re-added from backup.
        # But setLocation is safer if the torrent is still in the list.
        
        # Check if path is invalid (e.g. /downloads/incomplete)
        current_path = t['save_path']
        if current_path != config.default_save_path:
             # Only fix if it looks like the old bad path or user explicitly wants to normalize
             if "/downloads/" in current_path and "/media/" not in current_path:
                 print(f"Fixing path for {t['name']}...")
                 client.set_location(t['hash'], config.default_save_path)
                 count += 1
    print(f"Fixed paths for {count} torrents.")

def recheck_all(client):
    torrents = client.get_torrents()
    hashes = "|".join([t['hash'] for t in torrents])
    if hashes:
        print(f"Rechecking {len(torrents)} torrents...")
        client.recheck_torrent(hashes)

def announce_all(client):
    torrents = client.get_torrents()
    hashes = "|".join([t['hash'] for t in torrents])
    if hashes:
        print(f"Reannouncing {len(torrents)} torrents...")
        client.reannounce_torrent(hashes)

def delete_broken(client, delete_files=False):
    torrents = client.get_torrents()
    stalled = [t for t in torrents if t['state'] in ['stalledDL', 'metaDL']]
    hashes_to_delete = []
    
    print(f"Analyzing {len(stalled)} stalled torrents...")
    for t in stalled:
        trackers = client.get_trackers(t['hash'])
        has_working = any(tr['status'] == 2 for tr in trackers)
        
        if not has_working:
            print(f"Marking for deletion: {t['name']}")
            hashes_to_delete.append(t['hash'])
            
    if hashes_to_delete:
        print(f"Deleting {len(hashes_to_delete)} torrents...")
        client.delete_torrents("|".join(hashes_to_delete), delete_files)
    else:
        print("No broken torrents found.")

def add_missing(client, config, scan_path=None):
    target_path = scan_path if scan_path else config.default_scan_path
    
    if not target_path:
        print("Error: No scan path provided and no default configured.")
        return

    if not os.path.exists(target_path):
        print(f"Scan path not found: {target_path}")
        return

    print(f"Scanning {target_path} for .torrent files...")
    files = glob.glob(os.path.join(target_path, "*.torrent"))
    
    if not files:
        print("No .torrent files found.")
        return

    print(f"Found {len(files)} .torrent files. Adding them...")
    
    count = 0
    for fpath in files:
        if client.add_torrent_file(fpath, config.default_save_path):
            count += 1
    
    print(f"Processed {count} .torrent files.")
        # We don't know if it was new or not without checking hash, but this ensures they are added.
    
    print(f"Processed {len(files)} .torrent files.")

def main():
    parser = argparse.ArgumentParser(description="Manage torrents")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("fix-paths", help="Fix save paths for torrents")
    subparsers.add_parser("recheck", help="Force recheck all torrents")
    subparsers.add_parser("announce", help="Force reannounce all torrents")
    
    del_parser = subparsers.add_parser("delete-broken", help="Delete stalled torrents with no working trackers")
    del_parser.add_argument("--delete-files", action="store_true", help="Also delete files on disk")
    
    add_parser = subparsers.add_parser("add-missing", help="Scan folder and add missing torrents")
    add_parser.add_argument("--path", help="Path to scan for .torrent files (overrides default)")
    
    args = parser.parse_args()
    
    config = Config()
    client = QBitClient(config.base_url, config.qbit_user, config.qbit_pass)
    
    if args.command == "fix-paths":
        fix_paths(client, config)
    elif args.command == "recheck":
        recheck_all(client)
    elif args.command == "announce":
        announce_all(client)
    elif args.command == "delete-broken":
        delete_broken(client, args.delete_files)
    elif args.command == "add-missing":
        add_missing(client, config, args.path)

if __name__ == "__main__":
    main()
