import requests
import json
from collections import Counter

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
        print(f"Number of features: {len(features)}")
        
        # Check geometry types
        geom_types = Counter()
        for feat in features:
            geom_types[feat["geometry"]["type"]] += 1
        print(f"\nGeometry types: {dict(geom_types)}")
        
        # Check what the coordinates look like for each type
        for gtype in geom_types:
            for feat in features:
                if feat["geometry"]["type"] == gtype:
                    coords = feat["geometry"]["coordinates"]
                    print(f"\n{gtype} sample coordinates (first 3):")
                    if gtype == "Point":
                        print(f"  {coords}")
                    elif gtype == "LineString":
                        print(f"  Length: {len(coords)} points")
                        for c in coords[:3]:
                            print(f"  {c}")
                    elif gtype == "MultiLineString":
                        print(f"  {len(coords)} lines")
                        for c in coords[0][:3]:
                            print(f"  {c}")
                    break
        
        # Check property keys
        if features:
            print(f"\nProperty keys: {list(features[0]['properties'].keys())}")
            
        # Check if vehicleType exists
        has_vehicle_type = sum(1 for f in features if "vehicleType" in f.get("properties", {}))
        print(f"\nFeatures with vehicleType: {has_vehicle_type}/{len(features)}")
        
        # Check speed field
        has_speed = sum(1 for f in features if "speed" in f.get("properties", {}))
        print(f"Features with speed: {has_speed}/{len(features)}")
        
except Exception as e:
    print(f"Error: {e}")
