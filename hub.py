import threading
import time
import requests
import webbrowser
from flask import Flask, render_template, request

app = Flask(__name__)

# Tracker configuration
TRACKERS = [
    {"id": "rail", "name": "Rail Tracker", "port": 5001, "desc": "Live train locations and schedules in Finland.", "color": "#2f81f7"},
    {"id": "road", "name": "Road Tracker", "port": 5002, "desc": "Road maintenance vehicle tracking and task status.", "color": "#ffa500"},
    {"id": "marine", "name": "Marine Tracker", "port": 5003, "desc": "Maritime AIS vessel tracking (Optimized for performance).", "color": "#00f2ff"},
    {"id": "flight", "name": "Flight Tracker", "port": 5004, "desc": "Live aircraft tracking over Finland (OpenSky Network).", "color": "#ffae00"}
]

@app.route("/")
def index():
    return render_template("hub_index.html", trackers=TRACKERS)

@app.route("/shutdown_all", methods=["POST"])
def shutdown_all():
    """
    Terminates all running tracker processes by calling their respective shutdown endpoints.
    """
    for tracker in TRACKERS:
        try:
            url = f"http://127.0.0.1:{tracker['port']}/shutdown"
            requests.post(url, timeout=2)
        except Exception as e:
            print(f"Could not shutdown {tracker['name']}: {e}")
    
    def kill_hub():
        time.sleep(2)
        import os
        os._exit(0)
    
    threading.Thread(target=kill_hub).start()
    return "All trackers and Hub are shutting down..."

def open_browser(port):
    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:{port}")

if __name__ == "__main__":
    port = 5000
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    app.run(host="0.0.0.0", port=port)
