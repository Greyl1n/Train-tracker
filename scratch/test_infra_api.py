import requests
import json

HEADERS = {
    "User-Agent": "TrainTrackerFinland/4.0",
    "Digitraffic-User": "TrainTrackerFinland/4.0"
}

# Test the infra API for railway geometry
# Try the "radat" (railways) endpoint as GeoJSON
urls_to_test = [
    "https://rata.digitraffic.fi/infra-api/latest/radat.geojson",
    "https://rata.digitraffic.fi/infra-api/0.7/radat.geojson",
    "https://rata.digitraffic.fi/infra-api/latest/radat.json",
    "https://rata.digitraffic.fi/infra-api/latest/raiteet.geojson",
]

for url in urls_to_test:
    print(f"\n--- Testing: {url} ---")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                print(f"Type: {data.get('type', 'N/A')}")
                features = data.get("features", [])
                print(f"Features: {len(features)}")
                if features:
                    first = features[0]
                    geom = first.get("geometry", {})
                    print(f"Geometry type: {geom.get('type', 'N/A')}")
                    props = first.get("properties", {})
                    print(f"Property keys: {list(props.keys())[:10]}")
            elif isinstance(data, list):
                print(f"List length: {len(data)}")
                if data:
                    print(f"First item keys: {list(data[0].keys())[:10]}")
            break  # Stop on first success
        else:
            print(f"Response: {resp.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
