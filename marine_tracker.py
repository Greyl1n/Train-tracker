import os
import time
import threading
import logging
import requests
import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "MarineTrackerFinland/1.0", "Digitraffic-User": "MarineTrackerFinland/1.0"}
MARINE_LOC_URL = "https://meri.digitraffic.fi/api/ais/v1/locations"
MARINE_META_URL = "https://meri.digitraffic.fi/api/ais/v1/vessels"
FETCH_INTERVAL = 60

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

vessels_metadata = {}
latest_data_cache = []
history_data = {"times": [], "counts": []}
latest_stats_cache = {}

def categorize_vessel(code):
    if 70 <= code <= 79: return "Cargo"
    if 80 <= code <= 89: return "Cargo" # Tankers are often grouped with Cargo or kept separate
    if 60 <= code <= 69: return "Commercial" # Passenger
    if code in [40, 50]: return "Commercial"
    if code in [36, 37]: return "Private"
    return "Other"

def get_ship_type_name(code):
    """Fallback ship type names based on AIS codes."""
    if not code: return "Unknown"
    if 30 <= code <= 39: return "Fishing"
    if 40 <= code <= 49: return "High Speed Craft"
    if 50 <= code <= 59: return "Special Craft"
    if 60 <= code <= 69: return "Passenger"
    if 70 <= code <= 79: return "Cargo"
    if 80 <= code <= 89: return "Tanker"
    if code == 31: return "Tug"
    if code == 32: return "Sailing"
    return f"Type {code}"

def fetch_marine_metadata():
    global vessels_metadata
    while True:
        try:
            logger.info("Fetching marine metadata...")
            resp = requests.get(MARINE_META_URL, headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                new_meta = {}
                for v in data:
                    mmsi = str(v.get("mmsi"))
                    if not mmsi: continue
                    ship_code = v.get("shipType", 0)
                    new_meta[mmsi] = {
                        "name": v.get("name", "Unknown").strip() or "Unknown",
                        "shipType": v.get("shipTypeEn") or get_ship_type_name(ship_code),
                        "category": categorize_vessel(ship_code),
                        "callSign": v.get("callSign", "N/A"),
                        "destination": v.get("destination", "N/A")
                    }
                vessels_metadata = new_meta
                logger.info(f"Metadata updated for {len(vessels_metadata)} vessels.")
                # If we succeeded, we can wait 24h
                socketio.sleep(86400)
            else:
                logger.warning(f"Metadata API returned status {resp.status_code}")
                socketio.sleep(60) # Retry soon
        except Exception as e:
            logger.error(f"Meta Error: {e}")
            socketio.sleep(60) # Retry soon

def fetch_marine_data():
    global latest_data_cache
    while True:
        try:
            resp = requests.get(MARINE_LOC_URL, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                features = resp.json().get("features", [])
                enriched = []
                for feat in features:
                    mmsi = str(feat["properties"].get("mmsi"))
                    meta = vessels_metadata.get(mmsi, {})
                    enriched.append({
                        "mmsi": mmsi,
                        "lat": feat["geometry"]["coordinates"][1],
                        "lon": feat["geometry"]["coordinates"][0],
                        "name": meta.get("name", "Unknown Vessel"),
                        "shipType": meta.get("shipType", "Unknown"),
                        "category": meta.get("category", "Other"),
                        "speed": feat["properties"].get("sog", 0),
                        "heading": feat["properties"].get("heading", "N/A"),
                        "timestamp": feat["properties"].get("timestampExternal", "N/A"),
                        "callSign": meta.get("callSign", "N/A"),
                        "destination": meta.get("destination", "N/A")
                    })
                latest_data_cache = enriched
                
                # Update history & stats
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                history_data["times"].append(now_str)
                history_data["counts"].append(len(enriched))
                if len(history_data["times"]) > 60:
                    history_data["times"].pop(0)
                    history_data["counts"].pop(0)

                speeds = [v.get("speed", 0) for v in enriched if v.get("speed", 0) > 0]
                avg_speed = sum(speeds) / len(speeds) if speeds else 0
                max_speed = max(speeds) if speeds else 0
                categories = {}
                for v in enriched:
                    c = v.get("category", "Other")
                    categories[c] = categories.get(c, 0) + 1
                
                global latest_stats_cache
                latest_stats_cache = {
                    "total": len(enriched),
                    "avg_speed": round(avg_speed * 1.852, 1), # Store as km/h
                    "max_speed": round(max_speed * 1.852, 1),
                    "categories": categories,
                    "history": history_data
                }

                socketio.emit("marine_locations", enriched)
                socketio.emit("marine_statistics", latest_stats_cache)
                logger.info(f"Emitted {len(enriched)} vessels and stats.")
        except Exception as e: logger.error(f"Data Error: {e}")
        socketio.sleep(FETCH_INTERVAL)

@socketio.on('connect')
def handle_connect():
    if latest_data_cache:
        socketio.emit("marine_locations", latest_data_cache, to=request.sid)
    if latest_stats_cache:
        socketio.emit("marine_statistics", latest_stats_cache, to=request.sid)

@app.route("/")
def index():
    return render_template("marine_index.html")

@app.route("/shutdown", methods=["POST"])
def shutdown():
    logger.info("Shutdown requested.")
    def kill():
        time.sleep(2)
        os._exit(0)
    threading.Thread(target=kill).start()
    return "Shutting down Marine Tracker..."

if __name__ == "__main__":
    socketio.start_background_task(fetch_marine_metadata)
    socketio.start_background_task(fetch_marine_data)
    port = 5003
    logger.info(f"Starting Marine Tracker on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
