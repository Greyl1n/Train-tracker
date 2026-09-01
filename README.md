# Traffic Tracker Hub

Real-time traffic monitoring for Finland — tracking trains, road maintenance vehicles, maritime vessels, and aircraft. Built with Flask, Socket.IO, and Leaflet.js.

## Trackers

| Module | Port | Data Source | Description |
|--------|------|-------------|-------------|
| **Hub** | 5000 | — | Central portal linking all trackers with a shutdown-all button |
| **Rail** | 5001 | [Digitraffic Rata](https://rata.digitraffic.fi) | Live train locations, categories (commuter, cargo, long-distance), speeds |
| **Road** | 5002 | [Digitraffic Tie](https://tie.digitraffic.fi) | Maintenance vehicle tracking with task labels (ploughing, salting, etc.) |
| **Marine** | 5003 | [Digitraffic Meri](https://meri.digitraffic.fi) | AIS vessel positions, types, categories, and metadata |
| **Flight** | 5004 | [OpenSky Network](https://opensky-network.org) | Aircraft over Finland with altitude, speed, heading |

Each tracker provides a real-time map, live list, and statistics with time-series charts.

## 🚀 Standalone Monolith (GitHub Pages Deployment)

The project includes a unified standalone monolith application in [`index.html`](index.html) that runs **100% client-side in the browser** without requiring Python or Flask.

### How to Deploy to GitHub Pages in 3 Clicks:
1. Push this repository to your GitHub account:
   ```bash
   git add index.html
   git commit -m "Add GitHub Pages monolith tracker"
   git push origin main
   ```
2. Navigate to your repository on GitHub and open **Settings** → **Pages**.
3. Under **Build and deployment**:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main` (or your default branch)
   - **Folder**: `/ (root)`
4. Click **Save**. Within ~1 minute, your live tracker is active at `https://<your-username>.github.io/<repo-name>/`!

### Preview Monolith Locally
Simply open [`index.html`](index.html) in any modern browser, or run a local static web server:
```bash
python -m http.server 8000
```
Then visit [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Quick Start (Python Multi-Process Server)

```bash
pip install flask flask-socketio requests

# Launch all services
python launch_all.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) for the hub portal.

To launch individually:

```bash
python rail_tracker.py    # port 5001
python road_tracker.py    # port 5002
python marine_tracker.py  # port 5003
python flight_tracker.py  # port 5004
python hub.py             # port 5000
```

Click **Shut Down All Trackers** on the hub, or hit `Ctrl+C` in the `launch_all.py` terminal.

## Project Structure

```
Tracker/
├── index.html             # Standalone monolith web app (GitHub Pages ready)
├── hub.py                 # Central Flask app (port 5000)
├── rail_tracker.py        # Rail tracker (port 5001)
├── road_tracker.py        # Road maintenance tracker (port 5002)
├── marine_tracker.py      # Marine AIS tracker (port 5003)
├── flight_tracker.py      # Flight tracker (port 5004)
├── launch_all.py          # Launches all services simultaneously
├── templates/
│   ├── hub_index.html
│   ├── rail_index.html
│   ├── road_index.html
│   ├── marine_index.html
│   └── flight_index.html
├── archive/               # Historical versions
├── scratch/               # Development/testing scripts
└── walkthrough.md         # Dev notes on statistics features
```

## Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO
- **Frontend**: Leaflet.js (maps), Chart.js (time-series charts)
- **Real-time**: WebSocket via Socket.IO — clients receive live location and statistics updates as background threads poll the APIs
- **APIs**: [Digitraffic](https://www.digitraffic.fi) (rail, road, marine), [OpenSky Network](https://opensky-network.org) (flight)

## Credits & Data Sources

This project uses the following public data APIs:

- **Digitraffic** (`https://rata.digitraffic.fi`, `https://tie.digitraffic.fi`, `https://meri.digitraffic.fi`) — open data provided by the Finnish Transport Infrastructure Agency (Väylävirasto). Provides real-time train locations, road maintenance vehicle tracking, and maritime AIS vessel data. Licensed under [CC 4.0 BY](https://creativecommons.org/licenses/by/4.0/).
- **OpenSky Network** (`https://opensky-network.org/api`) — real-time aircraft position data from a community-driven network of ADS-B receivers. Data is provided under the [OpenSky License](https://opensky-network.org/about/data-license).

See the respective API documentation for usage limits and attribution requirements.

- **Map tiles** — [CartoDB](https://carto.com/attributions) provides the dark theme base map tiles (`{s}.basemaps.cartocdn.com/dark_all`). Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL).
