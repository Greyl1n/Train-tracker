import requests
import json

HEADERS = {"User-Agent": "TrainTrackerFinland/4.0", "Digitraffic-User": "TrainTrackerFinland/4.0"}

resp = requests.get("https://rata.digitraffic.fi/infra-api/latest/radat.geojson", headers=HEADERS, timeout=15)
data = resp.json()

print(f"Type: {data.get('type')}")
print(f"Features: {len(data.get('features', []))}")

# Check CRS if present
if 'crs' in data:
    print(f"CRS: {json.dumps(data['crs'], indent=2)}")
else:
    print("CRS: Not specified in response")

# Check actual coordinate values of first feature
feat = data['features'][0]
geom = feat['geometry']
print(f"\nGeometry type: {geom['type']}")

# Get first few coordinates
if geom['type'] == 'MultiLineString':
    first_line = geom['coordinates'][0]
    print(f"Number of lines: {len(geom['coordinates'])}")
    print(f"First line points: {len(first_line)}")
    print(f"First 3 coordinates:")
    for c in first_line[:3]:
        print(f"  {c}")
    print(f"\nCoordinate range check:")
    all_x = [p[0] for line in geom['coordinates'] for p in line]
    all_y = [p[1] for line in geom['coordinates'] for p in line]
    print(f"  X range: {min(all_x):.2f} to {max(all_x):.2f}")
    print(f"  Y range: {min(all_y):.2f} to {max(all_y):.2f}")
    
    if min(all_x) > 100:
        print("\n  >>> COORDINATES ARE IN FINNISH PROJECTION (EPSG:3067), NOT WGS84!")
        print("  >>> Leaflet expects WGS84 (lon ~20-30, lat ~60-70 for Finland)")
    else:
        print("\n  >>> Coordinates appear to be in WGS84")

# Also check response headers for CORS
print(f"\nResponse headers:")
for h in ['Access-Control-Allow-Origin', 'Content-Type']:
    print(f"  {h}: {resp.headers.get(h, 'NOT SET')}")
