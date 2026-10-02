import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import Config, QBitClient

def print_table(headers, rows):
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
    
    # Print header
    header_str = " | ".join(f"{h:<{w}}" for h, w in zip(headers, widths))
    print(header_str)
    print("-" * len(header_str))
    
    # Print rows
    for row in rows:
        print(" | ".join(f"{str(val):<{w}}" for val, w in zip(row, widths)))

def check_all(client):
    torrents = client.get_torrents()
    if not torrents:
        print("No torrents found.")
        return

    headers = ["Name", "State", "Progress", "Issue"]
    rows = []
    
    for t in torrents:
        issue = ""
        if t['state'] == 'error':
            issue = t.get('error_type', 'Generic Error')
        elif t['state'] in ['stalledDL', 'metaDL']:
            issue = "Stalled"
        elif t['state'] == 'missingFiles':
            issue = "Missing Files"
            
        rows.append([
            t['name'][:50],
            t['state'],
            f"{t['progress']*100:.1f}%",
            issue
        ])
    
    print_table(headers, rows)

def inspect_torrent(client, query):
    torrents = client.get_torrents()
    target = None
    for t in torrents:
        if t['hash'] == query or query.lower() in t['name'].lower():
            target = t
            break
            
    if not target:
        print(f"Torrent not found: {query}")
        return

    print(f"\n--- Inspecting: {target['name']} ---")
    print(f"Hash: {target['hash']}")
    print(f"State: {target['state']}")
    print(f"Progress: {target['progress']*100:.1f}%")
    print(f"Save Path: {target['save_path']}")
    print(f"Content Path: {target['content_path']}")
    print(f"Download Speed: {target['dlspeed']}")
    print(f"Seeds: {target['num_seeds']} (Total: {target['num_complete']})")
    print(f"Peers: {target['num_leechs']} (Total: {target['num_incomplete']})")
    
    print("\nTrackers:")
    trackers = client.get_trackers(target['hash'])
    for tr in trackers:
        print(f"  URL: {tr['url']}")
        print(f"  Status: {tr['status']}")
        print(f"  Message: {tr['msg']}")
        print(f"  Peers: {tr['num_peers']}")
        print("-" * 20)

def analyze_stalled(client):
    torrents = client.get_torrents()
    stalled = [t for t in torrents if t['state'] in ['stalledDL', 'metaDL']]
    
    print(f"Found {len(stalled)} stalled torrents.\n")
    
    headers = ["Name", "Seeds", "Peers", "Tracker Status"]
    rows = []

    for t in stalled:
        seeds = f"{t['dlspeed']}/{t['num_seeds']} ({t['num_complete']})"
        peers = f"{t['num_leechs']} ({t['num_incomplete']})"
        
        trackers = client.get_trackers(t['hash'])
        tracker_msg = "No trackers"
        if trackers:
            working = [tr for tr in trackers if tr['status'] == 2]
            if working:
                tracker_msg = f"Working ({len(working)})"
            else:
                tracker_msg = trackers[0].get('msg', 'Unknown')
                if not tracker_msg:
                    tracker_msg = f"Status: {trackers[0]['status']}"
        
        rows.append([t['name'][:50], seeds, peers, tracker_msg])
        
    print_table(headers, rows)

def main():
    parser = argparse.ArgumentParser(description="Check torrent status")
    parser.add_argument("action", choices=["all", "inspect", "stalled"], default="all", nargs="?", help="Action to perform")
    parser.add_argument("--query", "-q", help="Hash or name for inspection")
    
    args = parser.parse_args()
    
    config = Config()
    client = QBitClient(config.base_url, config.qbit_user, config.qbit_pass)
    
    if args.action == "all":
        check_all(client)
    elif args.action == "inspect":
        if not args.query:
            print("Error: --query is required for inspect")
            return
        inspect_torrent(client, args.query)
    elif args.action == "stalled":
        analyze_stalled(client)

if __name__ == "__main__":
    main()
