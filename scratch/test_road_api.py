import requests
import json

HEADERS = {
    "User-Agent": "RoadTrackerFinland/1.0",
    "Digitraffic-User": "RoadTrackerFinland/1.0"
}
DIGITRAFFIC_ROAD_URL = "https://tie.digitraffic.fi/api/maintenance/v1/tracking/routes/latest"

try:
    resp = requests.get(DIGITRAFFIC_ROAD_URL, headers=HEADERS, timeout=20)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        features = data.get("features", [])
        print(f"Number of road vehicles: {len(features)}")
        if len(features) > 0:
            print("First vehicle entry sample:")
            print(json.dumps(features[0], indent=2))
except Exception as e:
    print(f"Error: {e}")
