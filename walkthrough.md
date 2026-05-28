# Walkthrough: Adding Statistics and History Tabs

I have successfully added a "Statistics & History" tab to all four trackers (Rail, Marine, Flight, and Road). This allows users to easily toggle between the real-time active list of vehicles and an aggregated statistical view with historical trends.

## 1. Backend Updates (Data Aggregation)
Instead of relying on external history APIs (which are often rate-limited or unavailable), the Python backend for each tracker now natively tracks history and computes statistics locally in real-time.

*   **`rail_tracker.py`**: Now computes total active trains, average speed, max speed, and a breakdown of train categories (e.g., Cargo, Commuter). It maintains a rolling history of total trains for the past hour and emits this via the `train_statistics` WebSocket event.
*   **`marine_tracker.py`**: Computes total vessels, average speed (converted to km/h), max speed, and a breakdown by vessel type (e.g., Cargo, Passenger). Emits via the `marine_statistics` WebSocket event.
*   **`flight_tracker.py`**: Calculates total flights, average altitude, max speed, and counts for airborne vs. grounded aircraft. Emits via the `flight_statistics` WebSocket event.
*   **`road_tracker.py`**: Computes total active maintenance vehicles, extracts the top 5 maintenance tasks being performed (e.g., Salting, Ploughing), and counts active vehicles per domain. Emits via the `road_statistics` WebSocket event.

## 2. Frontend Updates (UI & Charts)
All four `*_index.html` frontend templates have been updated to support the new features:
*   **Tabs Integration**: A sleek CSS tab menu was added to the sidebar allowing users to switch between "Live List" and "Statistics".
*   **Statistics Panel**: When activated, the "Live List" is hidden, and a new structured statistics panel is displayed containing data grids for the computed statistics.
*   **Chart.js Integration**: [Chart.js](https://www.chartjs.org/) was imported via CDN to render smooth, responsive line charts. Each tracker now features a "Vehicles Over Time" line chart that updates dynamically as new data streams in via WebSockets.

The new UI perfectly matches the existing premium dark-mode aesthetic with custom accent colors mapping to each tracker's primary color (e.g., Blue for Rail, Orange for Road, Cyan for Marine, Yellow for Flight).

## How to Test
1.  Run `python launch_all.py` (if not already running).
2.  Open any of the tracker web interfaces.
3.  Click the "Statistics" tab in the top left sidebar.
4.  Observe the live-updating numeric statistics and the line chart charting active vehicles over time!
