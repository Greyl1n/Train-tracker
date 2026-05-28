import requests

HEADERS = {"User-Agent": "TrainTrackerFinland/4.0", "Digitraffic-User": "TrainTrackerFinland/4.0"}

# Try requesting WGS84 via srsName parameter
urls = [
    "https://rata.digitraffic.fi/infra-api/latest/radat.geojson?srsName=crs:84",
    "https://rata.digitraffic.fi/infra-api/latest/radat.geojson?srsName=epsg:4326",
    "https://rata.digitraffic.fi/infra-api/0.7/radat.geojson?srsName=crs:84",
]

for url in urls:
    print(f"\n--- {url} ---")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            crs = data.get('crs', {})
            print(f"CRS: {crs}")
            feat = data['features'][0]
            first_coord = feat['geometry']['coordinates'][0][0]
            print(f"First coordinate: {first_coord}")
            if first_coord[0] < 100:
                print(">>> WGS84 coordinates!")
            else:
                print(">>> Still Finnish projection")
            break
    except Exception as e:
        print(f"Error: {e}")
