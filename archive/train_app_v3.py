import os
import time
import threading
import logging
import requests
import webbrowser
import signal
from flask import Flask, render_template
from flask_socketio import SocketIO

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "TrainTrackerFinland/2.0 (Contact: markus.user@example.com)"
}

DIGITRAFFIC_LOC_URL = "https://rata.digitraffic.fi/api/v1/train-locations/latest"
DIGITRAFFIC_METADATA_URL = "https://rata.digitraffic.fi/api/v1/metadata/stations"
DIGITRAFFIC_TRAINS_URL = "https://rata.digitraffic.fi/api/v1/live-trains"
FETCH_INTERVAL_SECONDS = 20

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "change-this")
app.config['TEMPLATES_AUTO_RELOAD'] = True

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Cache for station names and train metadata
stations_cache = {}
trains_metadata = {}

def fetch_stations():
    """Fetch station names mapping from Digitraffic."""
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
    """Fetch general train info to get origin, destination, and other metadata."""
    global trains_metadata
    while True:
        try:
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
                logger.info(f"Updated metadata for {len(trains_metadata)} trains.")
        except Exception as e:
            logger.error(f"Error fetching train metadata: {e}")
        
        socketio.sleep(600)

def fetch_train_locations():
    """Background task to fetch live locations and merge with comprehensive metadata."""
    logger.info("Background task started: fetch_train_locations")
    while True:
        try:
            resp = requests.get(DIGITRAFFIC_LOC_URL, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                match_count = 0
                for train in data:
                    t_num = str(train.get("trainNumber"))
                    meta = trains_metadata.get(t_num)
                    if meta:
                        train["origin"] = meta.get("origin", "Unknown")
                        train["destination"] = meta.get("destination", "Unknown")
                        train["trainType"] = meta.get("trainType", "Unknown")
                        train["trainCategory"] = meta.get("trainCategory", "Unknown")
                        train["commuterLineID"] = meta.get("commuterLineID", "")
                        train["operatorShortCode"] = meta.get("operatorShortCode", "Unknown")
                        train["departureDate"] = meta.get("departureDate", "Unknown")
                        match_count += 1
                    else:
                        train["origin"] = "Unknown"
                        train["destination"] = "Unknown"
                        train["trainType"] = "Unknown"
                        train["trainCategory"] = "Unknown"
                        train["commuterLineID"] = ""
                        train["operatorShortCode"] = "Unknown"
                        train["departureDate"] = "Unknown"
                
                socketio.emit("train_locations", data)
                logger.info(f"Emitted {len(data)} trains ({match_count} matched)")
            elif resp.status_code == 429:
                logger.warning("Throttled (429).")
                socketio.sleep(30)
        except Exception as e:
            logger.error(f"Error in fetcher: {e}")

        socketio.sleep(FETCH_INTERVAL_SECONDS)

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected.")
    socketio.emit("connection_status", {"status": "connected", "train_count": len(trains_metadata)})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected.")

@app.route("/")
def index():
    return render_template("index_v3.html")

@app.route("/shutdown", methods=["POST"])
def shutdown():
    logger.info("Shutdown requested via API.")
    def shutdown_server():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=shutdown_server, daemon=True).start()
    return "Shutting down..."

def open_browser(port):
    """Opens the web browser automatically."""
    time.sleep(2)
    url = f"http://127.0.0.1:{port}"
    logger.info(f"Opening browser at {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    fetch_stations()
    
    socketio.start_background_task(fetch_train_metadata)
    socketio.start_background_task(fetch_train_locations)
    
    port = int(os.environ.get("PORT", 5002))
    
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    logger.info(f"Starting server on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
