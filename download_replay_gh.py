import os
import sys
import time
import bz2
import requests

def download_file(url, filename, target_dir):
    local_filename = os.path.join(target_dir, filename)
    print(f"[DOWNLOAD] Fetching from: {url}")
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
        print(f"[DOWNLOAD] Finished downloading: {filename}")
        return local_filename
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return None

def extract_and_finalize(bz2_path, match_id, target_dir):
    output_dem = os.path.join(target_dir, f"{match_id}.dem")
    print(f"[EXTRACT] Decompressing {bz2_path} to {output_dem}...")
    try:
        with bz2.BZ2File(bz2_path) as fr, open(output_dem, 'wb') as fw:
            fw.write(fr.read())
        print("[EXTRACT] Success! Unpacked .dem file created.")
        if os.path.exists(bz2_path):
            os.remove(bz2_path)
        return True
    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("[CRITICAL] Error: No Match ID provided. Usage: python script.py <match_id>")
        sys.exit(1)
        
    match_id = sys.argv[1].strip()
    
    replay_dir = os.path.join(os.getcwd(), 'workspace_replay')
    os.makedirs(replay_dir, exist_ok=True)
    
    api_url = f"https://api.opendota.com/api/matches/{match_id}"
    print(f"--- Starting Core Downloader for Match: {match_id} ---")
    
    replay_url = None
    
    try:
        res = requests.get(api_url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            replay_url = data.get("replay_url")
            
            if not replay_url and data.get("cluster") and data.get("replay_salt"):
                print("[LOG] Replay_url was null but Cluster and Salt found! Reconstructing Valve URL...")
                replay_url = f"http://replay{data.get('cluster')}.valve.net/570/{match_id}_{data.get('replay_salt')}.dem.bz2"
    except Exception as e:
        print(f"[WARNING] Initial API request failed: {e}")

    if not replay_url:
        print("[LOG] Match is not parsed yet. Sending Parse Request to OpenDota...")
        parse_url = f"https://api.opendota.com/api/request/{match_id}"
        try: 
            requests.post(parse_url, timeout=10)
        except: 
            pass
        
        for attempt in range(1, 3):
            print(f"[LOG] Waiting 15 seconds (Attempt {attempt}/2) for parsing...")
            time.sleep(15)
            
            try:
                res = requests.get(api_url, timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    replay_url = data.get("replay_url")
                    
                    if not replay_url and data.get("cluster") and data.get("replay_salt"):
                        replay_url = f"http://replay{data.get('cluster')}.valve.net/570/{match_id}_{data.get('replay_salt')}.dem.bz2"
                    
                    if replay_url:
                        print("[LOG] Success! Link obtained after parse.")
                        break
            except Exception as e:
                print(f"[WARNING] API check failed during wait: {e}")
                pass

    if replay_url:
        filename = replay_url.split("/")[-1]
        temp_file = download_file(replay_url, filename, replay_dir)
        if temp_file:
            success = extract_and_finalize(temp_file, match_id, replay_dir)
            if success:
                print("\n[FINISH] Replay downloaded and processed successfully!")
                sys.exit(0)
                
    print("\n[CRITICAL ERROR] Failed to fetch replay. Replay might be expired on Valve servers.")
    sys.exit(1)

if __name__ == "__main__":
    main()
