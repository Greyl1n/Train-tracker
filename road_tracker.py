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

HEADERS = {"User-Agent": "RoadTrackerFinland/1.0", "Digitraffic-User": "RoadTrackerFinland/1.0"}
DIGITRAFFIC_ROAD_URL = "https://tie.digitraffic.fi/api/maintenance/v1/tracking/routes/latest"
FETCH_INTERVAL = 60

# Map task codes to human-readable Finnish road maintenance tasks
TASK_LABELS = {
    "LEVELLING_GRAVEL_ROAD_SURFACE": "Gravel Levelling",
    "PAVING": "Paving",
    "PATCHING": "Patching",
    "SALTING": "Salting",
    "SANDING": "Sanding",
    "PLOUGHING_AND_SLUSH_REMOVAL": "Snow Ploughing",
    "BRUSHING": "Brushing",
    "DITCHING": "Ditching",
    "DUST_BINDING_OF_GRAVEL_ROAD_SURFACE": "Dust Binding",
    "MECHANICAL_CUT": "Mechanical Cut",
    "CLEANSING_OF_BRIDGES": "Bridge Cleaning",
    "LINE_SANDING": "Line Sanding",
    "COMPACTION_BY_ROLLING": "Rolling",
    "CRACK_FILLING": "Crack Filling",
    "TRANSFER_OF_SNOW": "Snow Transfer",
    "ROAD_MARKINGS": "Road Markings",
    "CLIENTS_QUALITY_CONTROL": "Quality Control",
    "HEATING": "Heating",
    "LOWERING_OF_PERMAFROST": "Permafrost Lowering",
    "FILLING_OF_GRAVEL_ROAD_SHOULDERS": "Shoulder Filling",
    "ROAD_STATE_CHECKING": "Road Inspection",
    "OTHER": "Other",
    "UNKNOWN": "Unknown Task"
}

app = Flask(__name__)
app.config["SECRET_KEY"] = "road-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

latest_data_cache = []
history_data = {"times": [], "counts": []}
latest_stats_cache = {}

def format_task(task_code):
    """Convert API task code to human-readable label."""
    return TASK_LABELS.get(task_code, task_code.replace("_", " ").title())

def fetch_road_data():
    global latest_data_cache
    while True:
        try:
            resp = requests.get(DIGITRAFFIC_ROAD_URL, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                features = resp.json().get("features", [])
                vehicles = []
                for feat in features:
                    props = feat.get("properties", {})
                    geom = feat.get("geometry", {})
                    coords = geom.get("coordinates", [])
                    
                    # Handle Point geometry
                    if geom.get("type") == "Point" and len(coords) >= 2:
                        lat, lon = coords[1], coords[0]
                    else:
                        continue  # Skip non-point geometries
                    
                    raw_tasks = props.get("tasks", [])
                    readable_tasks = [format_task(t) for t in raw_tasks]
                    
                    vehicles.append({
                        "id": props.get("id"),
                        "lat": lat,
                        "lon": lon,
                        "domain": props.get("domain", "unknown"),
                        "source": props.get("source", "Unknown"),
                        "tasks": readable_tasks,
                        "direction": props.get("direction", 0),
                        "timestamp": props.get("time") or props.get("created", "")
                    })
                latest_data_cache = vehicles
                
                # Update history & stats
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                history_data["times"].append(now_str)
                history_data["counts"].append(len(vehicles))
                if len(history_data["times"]) > 60:
                    history_data["times"].pop(0)
                    history_data["counts"].pop(0)

                tasks_count = {}
                for v in vehicles:
                    for t in v.get("tasks", []):
                        tasks_count[t] = tasks_count.get(t, 0) + 1
                # Get top 5 tasks
                top_tasks = dict(sorted(tasks_count.items(), key=lambda item: item[1], reverse=True)[:5])

                domains_count = {}
                for v in vehicles:
                    d = v.get("domain", "unknown")
                    domains_count[d] = domains_count.get(d, 0) + 1

                global latest_stats_cache
                latest_stats_cache = {
                    "total": len(vehicles),
                    "tasks": top_tasks,
                    "domains": domains_count,
                    "history": history_data
                }

                socketio.emit("road_locations", vehicles)
                socketio.emit("road_statistics", latest_stats_cache)
                logger.info(f"[TX] Emitted {len(vehicles)} road vehicles and stats.")
        except Exception as e:
            logger.error(f"[ERR] Road Fetch Error: {e}")
        socketio.sleep(FETCH_INTERVAL)

@socketio.on('connect')
def handle_connect():
    if latest_data_cache:
        socketio.emit("road_locations", latest_data_cache, to=request.sid)
    if latest_stats_cache:
        socketio.emit("road_statistics", latest_stats_cache, to=request.sid)

@app.route("/")
def index():
    return render_template("road_index.html")

@app.route("/shutdown", methods=["POST"])
def shutdown():
    logger.info("Shutdown requested.")
    def kill():
        time.sleep(2)
        os._exit(0)
    threading.Thread(target=kill).start()
    return "Shutting down Road Tracker..."

if __name__ == "__main__":
    socketio.start_background_task(fetch_road_data)
    port = 5002
    logger.info(f"Starting Road Tracker on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
