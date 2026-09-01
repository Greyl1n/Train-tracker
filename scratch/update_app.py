import json

with open('embedded_flights.json', 'r', encoding='utf-8') as f:
    embedded_json = f.read()

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace CartoDB tiles with Esri Dark Gray tiles
carto_old = """    // Dark matter tiles
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(map);"""

esri_new = """    // Free, high-performance dark tiles (Esri Dark Gray Canvas Base + Labels, no API key required)
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
      attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
      maxZoom: 16
    }).addTo(map);

    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}", {
      attribution: '',
      maxZoom: 16
    }).addTo(map);"""

if carto_old in content:
    content = content.replace(carto_old, esri_new)
    print("Replaced CartoDB tiles with Esri Dark Gray tiles!")
else:
    print("Warning: CartoDB snippet not found or already replaced.")

# 2. Add INITIAL_FLIGHTS definition before appState
target_appstate = """    // Cached raw data
    const appState = {
      stations: {},
      trainMetadata: {},
      railTrains: [],
      hslVehicles: {},
      roadVehicles: [],
      marineMetadata: {},
      marineVessels: [],
      flightPlanes: []
    };"""

replacement_appstate = f"""    // Pre-loaded real flight snapshot (guarantees flights are visible immediately even under file:/// or CORS restrictions)
    const INITIAL_FLIGHTS = {embedded_json};

    // Cached raw data
    const appState = {{
      stations: {{}},
      trainMetadata: {{}},
      railTrains: [],
      hslVehicles: {{}},
      roadVehicles: [],
      marineMetadata: {{}},
      marineVessels: [],
      flightPlanes: INITIAL_FLIGHTS.slice()
    }};"""

if target_appstate in content:
    content = content.replace(target_appstate, replacement_appstate)
    print("Added INITIAL_FLIGHTS pre-loaded dataset!")
else:
    print("Warning: target_appstate not found or already replaced.")

# 3. Update fetchFlightData
old_fetch_flight = """    // --- E. FLIGHT DATA (OpenSky Network via CORS Proxy) ---
    async function fetchFlightData() {
      showLoader();
      try {
        // Finland BBox: lamin=59.0, lomin=19.0, lamax=70.5, lomax=32.0
        const targetUrl = `https://opensky-network.org/api/states/all?lamin=59.0&lomin=19.0&lamax=70.5&lomax=32.0`;
        const proxyUrl = `https://corsproxy.io/?url=${encodeURIComponent(targetUrl)}`;

        let res;
        try {
          res = await fetch(proxyUrl);
        } catch (e) {
          // Fallback to allorigins if primary proxy fails
          res = await fetch(`https://api.allorigins.win/raw?url=${encodeURIComponent(targetUrl)}`);
        }

        if (!res.ok) throw new Error("Flight proxy status: " + res.status);
        const data = await res.json();
        const states = data.states || [];

        const enriched = states.map(s => {
          // 0: icao24, 1: callsign, 2: country, 5: lon, 6: lat, 7: baro_alt, 8: on_ground, 9: velocity, 10: heading
          const speed = Math.round((s[9] || 0) * 3.6);
          const alt = Math.round(s[7] || 0);
          return {
            id: 'flight-' + s[0],
            type: 'flight',
            icao24: s[0],
            callsign: (s[1] || 'Unknown').trim(),
            country: s[2] || 'Unknown',
            lon: s[5],
            lat: s[6],
            alt: alt,
            onGround: Boolean(s[8]),
            speed: speed,
            heading: Math.round(s[10] || 0)
          };
        }).filter(f => f.lat && f.lon);

        appState.flightPlanes = enriched;
        updateFlightMarkers(enriched);
        recordHistory('flight', enriched.length);
        if (currentMode === 'flight' || currentMode === 'all') {
          renderUI();
        }
      } catch (err) {
        console.warn("Flight fetch notice (rate limits or proxy):", err);
      } finally {
        hideLoader();
      }
    }"""

new_fetch_flight = """    // --- E. FLIGHT DATA (Local flights.json / OpenSky API) ---
    async function fetchFlightData() {
      showLoader();
      try {
        let loaded = false;

        // 1. Try local flights.json (ideal for GitHub Pages and local servers, zero CORS issues)
        try {
          const res = await fetch(`./flights.json?_t=${Date.now()}`);
          if (res.ok) {
            const data = await res.json();
            const states = data.states || [];
            if (states.length > 0) {
              const enriched = states.map(s => ({
                id: 'flight-' + s[0],
                type: 'flight',
                icao24: s[0],
                callsign: (s[1] || 'Unknown').trim(),
                country: s[2] || 'Unknown',
                lon: s[5],
                lat: s[6],
                alt: Math.round(s[7] || 0),
                onGround: Boolean(s[8]),
                speed: Math.round((s[9] || 0) * 3.6),
                heading: Math.round(s[10] || 0)
              })).filter(f => f.lat && f.lon);

              appState.flightPlanes = enriched;
              loaded = true;
            }
          }
        } catch (e) {
          // Local fetch can be blocked under file:/// protocol in Chrome/Edge
        }

        // 2. Direct fetch fallback (if deployed behind proxy or CORS extension)
        if (!loaded) {
          try {
            const targetUrl = `https://opensky-network.org/api/states/all?lamin=59.0&lomin=19.0&lamax=70.5&lomax=32.0`;
            const res = await fetch(targetUrl);
            if (res.ok) {
              const data = await res.json();
              const states = data.states || [];
              if (states.length > 0) {
                appState.flightPlanes = states.map(s => ({
                  id: 'flight-' + s[0],
                  type: 'flight',
                  icao24: s[0],
                  callsign: (s[1] || 'Unknown').trim(),
                  country: s[2] || 'Unknown',
                  lon: s[5],
                  lat: s[6],
                  alt: Math.round(s[7] || 0),
                  onGround: Boolean(s[8]),
                  speed: Math.round((s[9] || 0) * 3.6),
                  heading: Math.round(s[10] || 0)
                })).filter(f => f.lat && f.lon);
                loaded = true;
              }
            }
          } catch (err) {
            // CORS restricted on browser
          }
        }

        updateFlightMarkers(appState.flightPlanes);
        recordHistory('flight', appState.flightPlanes.length);
        if (currentMode === 'flight' || currentMode === 'all') {
          renderUI();
        }
      } catch (err) {
        console.warn("Flight fetch notice:", err);
      } finally {
        hideLoader();
      }
    }"""

if old_fetch_flight in content:
    content = content.replace(old_fetch_flight, new_fetch_flight)
    print("Replaced fetchFlightData with local flights.json + fallback logic!")
else:
    print("Warning: old_fetch_flight not found.")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html fully updated!")
