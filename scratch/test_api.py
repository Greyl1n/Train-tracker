import requests
import json

HEADERS = {
    "User-Agent": "TrainTrackerFinland/4.0 (Contact: markus.user@example.com)",
    "Digitraffic-User": "TrainTrackerFinland/4.0"
}
DIGITRAFFIC_LOC_URL = "https://rata.digitraffic.fi/api/v1/train-locations/latest"

DIGITRAFFIC_TRAINS_URL = "https://rata.digitraffic.fi/api/v1/live-trains"

print("\n--- Testing Live Trains Metadata ---")
DIGITRAFFIC_STATIONS_URL = "https://rata.digitraffic.fi/api/v1/metadata/stations"

print("\n--- Testing Stations Metadata ---")
try:
    resp = requests.get(DIGITRAFFIC_LOC_URL, headers=HEADERS, timeout=10)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Number of trains: {len(data)}")
        null_locs = [t for t in data if t.get("location") is None]
        print(f"Number of trains with null location: {len(null_locs)}")
        if len(data) > 0:
            print("First train entry sample:")
            print(json.dumps(data[0], indent=2))
except Exception as e:
    print(f"Error: {e}")
