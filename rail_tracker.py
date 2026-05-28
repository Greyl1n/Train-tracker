import os
import time
import threading
import logging
import requests
import webbrowser
import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "TrainTrackerFinland/4.0 (Contact: markus.user@example.com)",
    "Digitraffic-User": "TrainTrackerFinland/4.0"
}

# Digitraffic API Endpoints - RAIL
DIGITRAFFIC_LOC_URL = "https://rata.digitraffic.fi/api/v1/train-locations/latest"
DIGITRAFFIC_METADATA_URL = "https://rata.digitraffic.fi/api/v1/metadata/stations"
DIGITRAFFIC_TRAINS_URL = "https://rata.digitraffic.fi/api/v1/live-trains"

FETCH_INTERVAL_TRAINS = 15
FETCH_INTERVAL_METADATA = 300 # 5 minutes

app = Flask(__name__)
app.config["SECRET_KEY"] = "rail-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

stations_cache = {}
trains_metadata = {}
latest_data_cache = []
history_data = {"times": [], "counts": []}
latest_stats_cache = {}

def fetch_stations():
    global stations_cache
    try:
        resp = requests.get(DIGITRAFFIC_METADATA_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        stations_cache = {s["stationShortCode"]: s["stationName"] for s in data}
        logger.info(f"Loaded {len(stations_cache)} stations.")
    except Exception as e:
        logger.error(f"Error fetching stations: {e}")

def fetch_train_metadata():
    global trains_metadata
    try:
        logger.info("Fetching initial train metadata...")
        resp = requests.get(DIGITRAFFIC_TRAINS_URL, headers=HEADERS, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            new_metadata = {}
            for t in data:
                t_num = str(t.get("trainNumber"))
                rows = t.get("timeTableRows", [])
                if len(rows) >= 2:
                    origin_code = rows[0].get("stationShortCode")
                    dest_code = rows[-1].get("stationShortCode")
                    new_metadata[t_num] = {
                        "origin": stations_cache.get(origin_code, origin_code),
                        "destination": stations_cache.get(dest_code, dest_code),
                        "trainType": t.get("trainType", ""),
                        "trainCategory": t.get("trainCategory", ""),
                        "commuterLineID": t.get("commuterLineID", ""),
                        "operatorShortCode": t.get("operatorShortCode", ""),
                        "departureDate": t.get("departureDate", "")
                    }
            trains_metadata = new_metadata
            logger.info(f"[OK] Metadata loaded for {len(trains_metadata)} trains.")
        else:
            logger.error(f"[ERR] Metadata API returned status {resp.status_code}")
    except Exception as e:
        logger.error(f"[ERR] Error fetching initial train metadata: {e}")

def metadata_update_loop():
    while True:
        socketio.sleep(FETCH_INTERVAL_METADATA)
        fetch_train_metadata()

def fetch_train_locations():
    global latest_data_cache
    logger.info("Background task started: fetch_train_locations")
    while True:
        try:
            resp = requests.get(DIGITRAFFIC_LOC_URL, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for train in data:
                    t_num = str(train.get("trainNumber"))
                    meta = trains_metadata.get(t_num)
                    if meta:
                        # Simplified category for coloring
                        cat = meta.get("trainCategory", "Unknown")
                        display_cat = "train"
                        if cat == "Commuter": display_cat = "metro"
                        elif cat == "Cargo": display_cat = "cargo"
                        elif cat in ["Shunting", "Locomotive"]: display_cat = "other"
                        
                        train.update({
                            "origin": meta.get("origin"),
                            "destination": meta.get("destination"),
                            "trainType": meta.get("trainType"),
                            "category": display_cat,
                            "speed": train.get("speed", 0),
                            "operatorShortCode": meta.get("operatorShortCode", ""),
                            "departureDate": meta.get("departureDate", ""),
                            "commuterLineID": meta.get("commuterLineID", ""),
                            "timestamp": train.get("timestamp", "")
                        })
                    else:
                        train.update({
                            "origin": "Unknown", "destination": "Unknown",
                            "trainType": "Unknown", "category": "other",
                            "speed": train.get("speed", 0),
                            "operatorShortCode": "Unknown",
                            "departureDate": "Unknown",
                            "commuterLineID": "",
                            "timestamp": train.get("timestamp", "")
                        })
                
                latest_data_cache = data
                
                # Update history & stats
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                history_data["times"].append(now_str)
                history_data["counts"].append(len(data))
                if len(history_data["times"]) > 60:
                    history_data["times"].pop(0)
                    history_data["counts"].pop(0)

                speeds = [t.get("speed", 0) for t in data if t.get("speed", 0) > 0]
                avg_speed = sum(speeds) / len(speeds) if speeds else 0
                max_speed = max(speeds) if speeds else 0
                categories = {}
                for t in data:
                    c = t.get("category", "other")
                    categories[c] = categories.get(c, 0) + 1
                
                global latest_stats_cache
                latest_stats_cache = {
                    "total": len(data),
                    "avg_speed": round(avg_speed, 1),
                    "max_speed": max_speed,
                    "categories": categories,
                    "history": history_data
                }

                socketio.emit("train_locations", data)
                socketio.emit("train_statistics", latest_stats_cache)
                logger.info(f"[TX] Emitted {len(data)} train locations and stats.")
        except Exception as e:
            logger.error(f"[ERR] Error in location fetcher: {e}")
        socketio.sleep(FETCH_INTERVAL_TRAINS)

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    if latest_data_cache:
        socketio.emit("train_locations", latest_data_cache, to=request.sid)
    if latest_stats_cache:
        socketio.emit("train_statistics", latest_stats_cache, to=request.sid)

@app.route("/")
def index():
    return render_template("rail_index.html")

@app.route("/shutdown", methods=["POST"])
def shutdown():
    logger.info("Shutdown requested.")
    def kill():
        time.sleep(2)
        os._exit(0)
    threading.Thread(target=kill).start()
    return "Shutting down Rail Tracker..."

if __name__ == "__main__":
    fetch_stations()
    fetch_train_metadata()
    socketio.start_background_task(metadata_update_loop)
    socketio.start_background_task(fetch_train_locations)
    port = 5001
    logger.info(f"Starting Rail Tracker on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
