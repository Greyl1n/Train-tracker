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

# OpenSky API - Finland Bounding Box
# lamin, lomin, lamax, lomax
FINLAND_BBOX = {
    "lamin": 50.0,
    "lomin": 5.0,
    "lamax": 72.0,
    "lomax": 45.0
}
FLIGHT_API_URL = "https://opensky-network.org/api/states/all"
FETCH_INTERVAL = 15 # OpenSky allows ~10s for authenticated, ~60s for anonymous. 15s is a compromise.

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

latest_flights_cache = []
history_data = {"times": [], "counts": []}
latest_stats_cache = {}

def fetch_flight_data():
    global latest_flights_cache
    while True:
        try:
            params = {
                "lamin": FINLAND_BBOX["lamin"],
                "lomin": FINLAND_BBOX["lomin"],
                "lamax": FINLAND_BBOX["lamax"],
                "lomax": FINLAND_BBOX["lomax"]
            }
            # Headers to identify our app
            headers = {"User-Agent": "FinlandTrafficTracker/1.0"}
            
            resp = requests.get(FLIGHT_API_URL, params=params, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                states = data.get("states", [])
                
                enriched = []
                for s in states:
                    # OpenSky state vector format:
                    # 0: icao24, 1: callsign, 2: origin_country, 3: time_position, 4: last_contact, 
                    # 5: longitude, 6: latitude, 7: baro_altitude, 8: on_ground, 9: velocity, 
                    # 10: true_track, 11: vertical_rate, ...
                    
                    enriched.append({
                        "icao24": s[0],
                        "callsign": (s[1] or "Unknown").strip(),
                        "country": s[2],
                        "lon": s[5],
                        "lat": s[6],
                        "alt": s[7] or 0, # Meters
                        "on_ground": s[8],
                        "speed": (s[9] or 0) * 3.6, # m/s to km/h
                        "heading": s[10] or 0,
                        "v_rate": s[11] or 0
                    })
                
                latest_flights_cache = enriched
                
                # Update history & stats
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                history_data["times"].append(now_str)
                history_data["counts"].append(len(enriched))
                if len(history_data["times"]) > 60:
                    history_data["times"].pop(0)
                    history_data["counts"].pop(0)

                alts = [f.get("alt", 0) for f in enriched if f.get("alt", 0) > 0]
                avg_alt = sum(alts) / len(alts) if alts else 0
                max_alt = max(alts) if alts else 0
                
                speeds = [f.get("speed", 0) for f in enriched if f.get("speed", 0) > 0]
                avg_speed = sum(speeds) / len(speeds) if speeds else 0
                max_speed = max(speeds) if speeds else 0
                
                on_ground = sum(1 for f in enriched if f.get("on_ground"))
                airborne = len(enriched) - on_ground
                
                global latest_stats_cache
                latest_stats_cache = {
                    "total": len(enriched),
                    "avg_alt": round(avg_alt),
                    "max_alt": round(max_alt),
                    "avg_speed": round(avg_speed),
                    "max_speed": round(max_speed),
                    "status": {"Airborne": airborne, "On Ground": on_ground},
                    "history": history_data
                }

                socketio.emit("flight_locations", enriched)
                socketio.emit("flight_statistics", latest_stats_cache)
                logger.info(f"Emitted {len(enriched)} flights over Finland and stats.")
            elif resp.status_code == 429:
                logger.warning("OpenSky Rate Limit Hit. Waiting longer...")
                socketio.sleep(60)
            else:
                logger.error(f"Flight API Error: {resp.status_code}")
        except Exception as e:
            logger.error(f"Flight Data Error: {e}")
        
        socketio.sleep(FETCH_INTERVAL)

@socketio.on('connect')
def handle_connect():
    if latest_flights_cache:
        socketio.emit("flight_locations", latest_flights_cache, to=request.sid)
    if latest_stats_cache:
        socketio.emit("flight_statistics", latest_stats_cache, to=request.sid)

@app.route("/")
def index():
    return render_template("flight_index.html")

@app.route("/shutdown", methods=["POST"])
def shutdown():
    logger.info("Shutdown requested.")
    def kill():
        time.sleep(2)
        os._exit(0)
    threading.Thread(target=kill).start()
    return "Shutting down Flight Tracker..."

if __name__ == "__main__":
    socketio.start_background_task(fetch_flight_data)
    port = 5004
    logger.info(f"Starting Flight Tracker on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
