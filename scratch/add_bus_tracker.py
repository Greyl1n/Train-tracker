import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add --bus-color to :root
old_root = """      --rail-color: #2f81f7;
      --road-color: #ffa500;"""
new_root = """      --rail-color: #2f81f7;
      --bus-color: #007ac9;
      --road-color: #ffa500;"""
assert old_root in content, "Root vars not found!"
content = content.replace(old_root, new_root)

# 2. Add mode-btn styling for bus
old_btn_style = """.mode-btn.active[data-mode="rail"] { background: var(--rail-color); }"""
new_btn_style = """.mode-btn.active[data-mode="rail"] { background: var(--rail-color); }
    .mode-btn.active[data-mode="bus"] { background: var(--bus-color); color: #fff; }"""
assert old_btn_style in content, "Btn style not found!"
content = content.replace(old_btn_style, new_btn_style)

# 3. Add marker-badge styling for bus
old_badges = """.marker-badge.train { background: var(--rail-color); }
    .marker-badge.metro { background: #af52de; }
    .marker-badge.tram { background: #3fb950; }
    .marker-badge.cargo { background: #ffa500; }
    .marker-badge.other { background: #6e7681; }"""
new_badges = """.marker-badge.train { background: var(--rail-color); }
    .marker-badge.metro { background: #af52de; }
    .marker-badge.tram { background: #3fb950; }
    .marker-badge.cargo { background: #ffa500; }
    .marker-badge.other { background: #6e7681; }
    .marker-badge.bus { background: var(--bus-color); }
    .marker-badge.trunk { background: #ff6319; }
    .marker-badge.foli { background: #fdb913; color: #0d1117; border-color: #0d1117; }"""
assert old_badges in content, "Badges not found!"
content = content.replace(old_badges, new_badges)

# 4. Add Bus button after Rail in mode-nav
old_nav = """        <button class="mode-btn active" data-mode="rail" onclick="switchMode('rail')">🚆 Rail</button>
        <button class="mode-btn" data-mode="road" onclick="switchMode('road')">🚜 Road</button>"""
new_nav = """        <button class="mode-btn active" data-mode="rail" onclick="switchMode('rail')">🚆 Rail</button>
        <button class="mode-btn" data-mode="bus" onclick="switchMode('bus')">🚌 Bus</button>
        <button class="mode-btn" data-mode="road" onclick="switchMode('road')">🚜 Road</button>"""
assert old_nav in content, "Mode nav buttons not found!"
content = content.replace(old_nav, new_nav)

# 5. Add trunkLines and bus intervals in CONFIG
old_config = """      intervals: {
        rail: 15000,
        road: 60000,
        marine: 60000,
        flight: 25000,
        cleanupHSL: 30000
      },"""
new_config = """      intervals: {
        rail: 15000,
        bus: 15000,
        road: 60000,
        marine: 60000,
        flight: 25000,
        cleanupHSL: 30000
      },
      trunkLines: ['20', '30', '40', '500', '510', '520', '530', '550', '560', '570', '600'],"""
assert old_config in content, "CONFIG intervals not found!"
content = content.replace(old_config, new_config)

# 6. Add bus to activeFilters
old_filters = """    const activeFilters = {
      rail: new Set(['train', 'metro', 'tram', 'cargo', 'other']),
      road: new Set(['all']),
      marine: new Set(['Cargo', 'Commercial', 'Private', 'Other']),
      flight: new Set(['airborne', 'ground']),
      all: new Set(['rail', 'road', 'marine', 'flight'])
    };"""
new_filters = """    const activeFilters = {
      rail: new Set(['train', 'metro', 'tram', 'cargo', 'other']),
      bus: new Set(['all', 'hsl', 'foli', 'trunk']),
      road: new Set(['all']),
      marine: new Set(['Cargo', 'Commercial', 'Private', 'Other']),
      flight: new Set(['airborne', 'ground']),
      all: new Set(['rail', 'bus', 'road', 'marine', 'flight'])
    };"""
assert old_filters in content, "activeFilters not found!"
content = content.replace(old_filters, new_filters)

# 7. Add bus to historyData
old_hist = """    const historyData = {
      rail: { times: [], counts: [] },
      road: { times: [], counts: [] },
      marine: { times: [], counts: [] },
      flight: { times: [], counts: [] },
      all: { times: [], counts: [] }
    };"""
new_hist = """    const historyData = {
      rail: { times: [], counts: [] },
      bus: { times: [], counts: [] },
      road: { times: [], counts: [] },
      marine: { times: [], counts: [] },
      flight: { times: [], counts: [] },
      all: { times: [], counts: [] }
    };"""
assert old_hist in content, "historyData not found!"
content = content.replace(old_hist, new_hist)

# 8. Add busVehicles to appState
old_appstate = """      marineMetadata: {},
      marineVessels: [],
      flightPlanes: INITIAL_FLIGHTS.slice()
    };"""
new_appstate = """      marineMetadata: {},
      marineVessels: [],
      flightPlanes: INITIAL_FLIGHTS.slice(),
      busVehicles: {}
    };"""
assert old_appstate in content, "appState not found!"
content = content.replace(old_appstate, new_appstate)

# 9. Add bus to layerGroups
old_layers = """      hsl: L.layerGroup().addTo(map),
      road: L.layerGroup(),"""
new_layers = """      hsl: L.layerGroup().addTo(map),
      bus: L.layerGroup(),
      road: L.layerGroup(),"""
assert old_layers in content, "layerGroups not found!"
content = content.replace(old_layers, new_layers)

# 10. Add bus to markers
old_markers = """    const markers = {
      rail: {},
      hsl: {},
      road: {},
      marine: {},
      flight: {}
    };"""
new_markers = """    const markers = {
      rail: {},
      hsl: {},
      bus: {},
      road: {},
      marine: {},
      flight: {}
    };"""
assert old_markers in content, "markers not found!"
content = content.replace(old_markers, new_markers)

# 11. Add HSL bus MQTT handling and Föli bus fetcher
old_hsl = """            const mode = message.destinationName.split('/')[5]; // metro or tram
            const id = `hsl-${vp.veh}`;"""

new_hsl = """            const mode = message.destinationName.split('/')[5]; // metro, tram, or bus
            
            if (mode === 'bus') {
              const line = vp.desi || "??";
              const id = `hsl-bus-${vp.veh}`;
              const isTrunk = CONFIG.trunkLines.includes(line);
              const speed = Math.round((vp.spd || 0) * 3.6);
              const dl = vp.dl !== undefined ? vp.dl : 0;
              const delayStr = dl > 60 ? `+${Math.round(dl/60)}m late` : dl < -60 ? `${Math.round(Math.abs(dl)/60)}m early` : 'On time';
              const route = `${isTrunk ? '🟠 Trunk ' : ''}Bus Line ${line}`;

              const item = {
                id,
                type: 'bus',
                region: 'hsl',
                isTrunk,
                line,
                veh: vp.veh,
                route,
                operator: vp.oper ? `Operator #${vp.oper}` : 'HSL',
                speed,
                lat: vp.lat,
                lon: vp.long,
                heading: vp.hdg || 0,
                delay: dl,
                delayStr,
                timestamp: Date.now()
              };

              appState.busVehicles[id] = item;
              updateBusMarker(item);
              return;
            }

            const id = `hsl-${vp.veh}`;"""
assert old_hsl in content, "HSL MQTT handler not found!"
content = content.replace(old_hsl, new_hsl)

# 12. Add HSL MQTT bus subscription and bus cleanup
old_sub = """            client.subscribe("/hfp/v2/journey/ongoing/vp/metro/#");
            client.subscribe("/hfp/v2/journey/ongoing/vp/tram/#");"""
new_sub = """            client.subscribe("/hfp/v2/journey/ongoing/vp/metro/#");
            client.subscribe("/hfp/v2/journey/ongoing/vp/tram/#");
            client.subscribe("/hfp/v2/journey/ongoing/vp/bus/#");"""
assert old_sub in content, "HSL MQTT subscriptions not found!"
content = content.replace(old_sub, new_sub)

# Also add stale bus cleanup
old_cleanup = """        setInterval(() => {
          const now = Date.now();
          Object.keys(appState.hslVehicles).forEach(id => {
            if (now - appState.hslVehicles[id].timestamp > 45000) {
              if (markers.hsl[id]) {
                layerGroups.hsl.removeLayer(markers.hsl[id]);
                delete markers.hsl[id];
              }
              delete appState.hslVehicles[id];
            }
          });
        }, CONFIG.intervals.cleanupHSL);"""

new_cleanup = """        setInterval(() => {
          const now = Date.now();
          // Cleanup stale metro/tram
          Object.keys(appState.hslVehicles).forEach(id => {
            if (now - appState.hslVehicles[id].timestamp > 45000) {
              if (markers.hsl[id]) {
                layerGroups.hsl.removeLayer(markers.hsl[id]);
                delete markers.hsl[id];
              }
              delete appState.hslVehicles[id];
            }
          });
          // Cleanup stale buses
          Object.keys(appState.busVehicles).forEach(id => {
            if (now - appState.busVehicles[id].timestamp > 45000) {
              if (markers.bus[id]) {
                layerGroups.bus.removeLayer(markers.bus[id]);
                delete markers.bus[id];
              }
              delete appState.busVehicles[id];
            }
          });
          recordHistory('bus', Object.keys(appState.busVehicles).length);
          if (currentMode === 'bus' || currentMode === 'all') renderUI();
        }, CONFIG.intervals.cleanupHSL);"""
assert old_cleanup in content, "cleanupHSL not found!"
content = content.replace(old_cleanup, new_cleanup)

# 13. Insert updateBusMarker and fetchFoliBuses functions before Road fetcher
road_fetch_marker = "    // --- C. ROAD MAINTENANCE DATA ---"
bus_functions = """    // --- B2. BUS MARKERS & TURKU (FÖLI) SIRI API ---
    function updateBusMarker(b) {
      const pos = [b.lat, b.lon];
      const isSelected = selectedVehicleId === b.id;
      const badgeClass = b.isTrunk ? 'trunk' : b.region === 'foli' ? 'foli' : 'bus';

      if (!markers.bus[b.id]) {
        const icon = L.divIcon({
          className: 'custom-div-icon',
          html: `<div class="marker-badge ${badgeClass}" style="font-size:0.58rem; width:26px; height:26px;">${b.line}</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13]
        });

        const m = L.marker(pos, { icon })
          .bindPopup(`
            <div class="popup-title" style="color:${b.isTrunk ? '#ff6319' : b.region === 'foli' ? '#fdb913' : 'var(--bus-color)'}">
              🚌 ${b.route}
            </div>
            <div class="popup-content-text">
              Region: <b>${b.region === 'hsl' ? 'Helsinki Metropolitan (HSL)' : 'Turku Region (Föli)'}</b><br/>
              Vehicle: #${b.veh}<br/>
              ${b.speed ? `Speed: <b>${b.speed} km/h</b><br/>` : ''}
              Schedule: <b>${b.delayStr}</b> (${b.delay > 0 ? '+' : ''}${b.delay}s)<br/>
              ${b.origin ? `From: ${b.origin}<br/>` : ''}
              ${b.destination ? `To: ${b.destination}<br/>` : ''}
              Operator: ${b.operator}<br/>
              Updated: ${new Date(b.timestamp).toLocaleTimeString()}
            </div>
          `);

        m.on('click', () => selectVehicle(b.id));
        markers.bus[b.id] = m;
        layerGroups.bus.addLayer(m);
      } else {
        markers.bus[b.id].setLatLng(pos);
      }
    }

    async function fetchFoliBuses() {
      try {
        const res = await fetch("https://data.foli.fi/siri/vm");
        if (!res.ok) return;
        const json = await res.json();
        const vehicles = json.result?.vehicles || {};
        const now = Date.now();

        Object.values(vehicles).forEach(v => {
          if (!v.latitude || !v.longitude) return;
          const line = v.publishedlinename || v.lineref || "??";
          const id = `foli-bus-${v.vehicleref || Math.random()}`;
          const dl = v.delaysecs || 0;
          const delayStr = dl > 60 ? `+${Math.round(dl/60)}m late` : dl < -60 ? `${Math.round(Math.abs(dl)/60)}m early` : 'On time';
          const route = `${v.originname || 'Turku'} → ${v.destinationname || 'Destination'}`;

          const item = {
            id,
            type: 'bus',
            region: 'foli',
            isTrunk: false,
            line,
            veh: v.vehicleref,
            operator: 'Föli Turku',
            route: `Line ${line}: ${route}`,
            origin: v.originname || '',
            destination: v.destinationname || '',
            speed: 0,
            lat: v.latitude,
            lon: v.longitude,
            heading: 0,
            delay: dl,
            delayStr,
            timestamp: now
          };

          appState.busVehicles[id] = item;
          updateBusMarker(item);
        });

        recordHistory('bus', Object.keys(appState.busVehicles).length);
        if (currentMode === 'bus' || currentMode === 'all') {
          renderUI();
        }
      } catch (err) {
        console.warn("Föli bus fetch notice:", err);
      }
    }

"""
assert road_fetch_marker in content, "Road fetch marker not found!"
content = content.replace(road_fetch_marker, bus_functions + road_fetch_marker)

# 14. Update totalAll calculation in recordHistory
old_record_all = """        const totalAll = appState.railTrains.length + Object.keys(appState.hslVehicles).length +
                         appState.roadVehicles.length + appState.marineVessels.length + appState.flightPlanes.length;"""
new_record_all = """        const totalAll = appState.railTrains.length + Object.keys(appState.hslVehicles).length +
                         Object.keys(appState.busVehicles).length +
                         appState.roadVehicles.length + appState.marineVessels.length + appState.flightPlanes.length;"""
assert old_record_all in content, "recordHistory totalAll not found!"
content = content.replace(old_record_all, new_record_all)

# 15. Update switchMode layers and colors
old_switch_all = """      if (mode === 'all') {
        if (!map.hasLayer(layerGroups.tracks)) map.addLayer(layerGroups.tracks);
        if (!map.hasLayer(layerGroups.rail)) map.addLayer(layerGroups.rail);
        if (!map.hasLayer(layerGroups.hsl)) map.addLayer(layerGroups.hsl);
        if (!map.hasLayer(layerGroups.road)) map.addLayer(layerGroups.road);
        if (!map.hasLayer(layerGroups.marine)) map.addLayer(layerGroups.marine);
        if (!map.hasLayer(layerGroups.flight)) map.addLayer(layerGroups.flight);
      } else {"""

new_switch_all = """      if (mode === 'all') {
        if (!map.hasLayer(layerGroups.tracks)) map.addLayer(layerGroups.tracks);
        if (!map.hasLayer(layerGroups.rail)) map.addLayer(layerGroups.rail);
        if (!map.hasLayer(layerGroups.hsl)) map.addLayer(layerGroups.hsl);
        if (!map.hasLayer(layerGroups.bus)) map.addLayer(layerGroups.bus);
        if (!map.hasLayer(layerGroups.road)) map.addLayer(layerGroups.road);
        if (!map.hasLayer(layerGroups.marine)) map.addLayer(layerGroups.marine);
        if (!map.hasLayer(layerGroups.flight)) map.addLayer(layerGroups.flight);
      } else {
        if (mode === 'bus') {
          if (!map.hasLayer(layerGroups.bus)) map.addLayer(layerGroups.bus);
        } else {
          if (map.hasLayer(layerGroups.bus)) map.removeLayer(layerGroups.bus);
        }"""
assert old_switch_all in content, "switchMode all not found!"
content = content.replace(old_switch_all, new_switch_all)

# Colors in switchMode
old_colors = """      const colors = {
        rail: 'var(--rail-color)',
        road: 'var(--road-color)',
        marine: 'var(--marine-color)',
        flight: 'var(--flight-color)',
        all: '#00f2ff'
      };"""
new_colors = """      const colors = {
        rail: 'var(--rail-color)',
        bus: 'var(--bus-color)',
        road: 'var(--road-color)',
        marine: 'var(--marine-color)',
        flight: 'var(--flight-color)',
        all: '#00f2ff'
      };"""
assert old_colors in content, "colors in switchMode not found!"
content = content.replace(old_colors, new_colors)

# 16. Update setupFilters for bus
old_filters_setup = """      if (currentMode === 'marine') {"""
new_filters_setup = """      if (currentMode === 'bus') {
        const items = [
          { id: 'all', label: 'All Buses' },
          { id: 'hsl', label: 'Helsinki (HSL)' },
          { id: 'foli', label: 'Turku (Föli)' },
          { id: 'trunk', label: '🟠 Trunk Lines' }
        ];
        items.forEach(item => {
          const chip = document.createElement('div');
          chip.className = `filter-chip ${activeFilters.bus.has(item.id) ? 'active' : ''}`;
          chip.textContent = item.label;
          chip.onclick = () => {
            if (activeFilters.bus.has(item.id)) activeFilters.bus.delete(item.id);
            else activeFilters.bus.add(item.id);
            chip.classList.toggle('active');
            renderUI();
          };
          container.appendChild(chip);
        });
      } else if (currentMode === 'marine') {"""
assert old_filters_setup in content, "setupFilters not found!"
content = content.replace(old_filters_setup, new_filters_setup)

# 17. Update getVisibleItems for bus
old_visible_bus = """      if (currentMode === 'road' || currentMode === 'all') {"""
new_visible_bus = """      if (currentMode === 'bus' || currentMode === 'all') {
        const buses = Object.values(appState.busVehicles).filter(b => {
          if (currentMode === 'bus') {
            if (activeFilters.bus.has('trunk') && b.isTrunk) return true;
            if (activeFilters.bus.has(b.region)) return true;
            if (activeFilters.bus.has('all')) return true;
            return false;
          }
          if (query && !(`${b.line} ${b.route} ${b.veh} ${b.region}`).toLowerCase().includes(query)) return false;
          return true;
        });
        list = list.concat(buses);
      }

      if (currentMode === 'road' || currentMode === 'all') {"""
assert old_visible_bus in content, "getVisibleItems not found!"
content = content.replace(old_visible_bus, new_visible_bus)

# 18. Titles in renderUI
old_titles = """      const titles = {
        rail: '🚆 Rail Tracker',
        road: '🚜 Road Maintenance',
        marine: '🚢 Marine AIS Tracker',
        flight: '✈️ Flight Tracker',
        all: '🌐 All Traffic Combined'
      };"""
new_titles = """      const titles = {
        rail: '🚆 Rail Tracker',
        bus: '🚌 Bus Tracker Finland',
        road: '🚜 Road Maintenance',
        marine: '🚢 Marine AIS Tracker',
        flight: '✈️ Flight Tracker',
        all: '🌐 All Traffic Combined'
      };"""
assert old_titles in content, "titles in renderUI not found!"
content = content.replace(old_titles, new_titles)

# 19. Item rendering in renderLiveList
old_item_render = """        } else if (item.type === 'road') {"""
new_item_render = """        } else if (item.type === 'bus') {
          const regionBadge = item.region === 'hsl' ? 'HSL Helsinki' : 'Föli Turku';
          const trunkBadge = item.isTrunk ? '<span class=\"badge-pill\" style=\"background:rgba(255,99,25,0.2);color:#ff6319;font-weight:700;\">Trunk Line</span>' : '';
          el.innerHTML = `
            <div class=\"vehicle-top\">
              <div class=\"vehicle-title\" style=\"color:${item.isTrunk ? '#ff6319' : item.region === 'foli' ? '#fdb913' : 'var(--bus-color)'}\">
                🚌 ${item.route}
              </div>
              <div class=\"vehicle-speed\">${item.delayStr}</div>
            </div>
            <div class=\"vehicle-sub\">${regionBadge} • Vehicle #${item.veh}${item.speed ? ` • ${item.speed} km/h` : ''}</div>
            <div class=\"vehicle-meta\">
              <span class=\"badge-pill\">${regionBadge}</span>
              ${trunkBadge}
              <span class=\"badge-pill\">${item.operator}</span>
            </div>
          `;
        } else if (item.type === 'road') {"""
assert old_item_render in content, "renderLiveList item.type road not found!"
content = content.replace(old_item_render, new_item_render)

# 20. selectVehicle marker groups
old_select_groups = """      for (const group of ['rail', 'hsl', 'road', 'marine', 'flight']) {"""
new_select_groups = """      for (const group of ['rail', 'hsl', 'bus', 'road', 'marine', 'flight']) {"""
assert old_select_groups in content, "selectVehicle groups not found!"
content = content.replace(old_select_groups, new_select_groups)

# 21. Statistics rendering in renderStatistics
old_stats_render = """      if (currentMode === 'rail') {"""
new_stats_render = """      if (currentMode === 'bus') {
        const buses = Object.values(appState.busVehicles);
        const total = buses.length;
        const hslCount = buses.filter(b => b.region === 'hsl').length;
        const foliCount = buses.filter(b => b.region === 'foli').length;
        const trunkCount = buses.filter(b => b.isTrunk).length;
        const onTimeCount = buses.filter(b => b.delay >= -60 && b.delay <= 120).length;
        const punctuality = total ? Math.round((onTimeCount / total) * 100) : 100;

        document.getElementById('stat-main-title').textContent = 'Total Active Buses';
        document.getElementById('stat-main-value').textContent = total;
        document.getElementById('stat-sec1-title').textContent = 'Punctuality';
        document.getElementById('stat-sec1-value').innerHTML = `${punctuality}<span style=\"font-size:0.75rem;font-weight:400\">% on-time</span>`;
        document.getElementById('stat-sec2-title').textContent = 'Trunk Lines';
        document.getElementById('stat-sec2-value').textContent = trunkCount;

        breakdownEl.innerHTML = `
          <div><b>Helsinki Region (HSL):</b> ${hslCount}</div>
          <div><b>Turku Region (Föli):</b> ${foliCount}</div>
          <div><b style=\"color:#ff6319;\">🟠 Orange Trunk Lines:</b> ${trunkCount}</div>
          <div><b>On Time (-1m to +2m):</b> ${onTimeCount}</div>
          <div style=\"margin-top:8px;font-size:0.72rem;color:var(--text-muted);border-top:1px solid var(--border);padding-top:6px;\">
            Streamed live from <b>HSL Real-Time MQTT</b> & <b>Föli SIRI API</b>. Compatible with Digitransit.
          </div>
        `;
      } else if (currentMode === 'rail') {"""
assert old_stats_render in content, "renderStatistics rail not found!"
content = content.replace(old_stats_render, new_stats_render)

# 22. Statistics all mode update in renderStatistics
old_stats_all = """        const totalRail = appState.railTrains.length + Object.keys(appState.hslVehicles).length;
        const totalRoad = appState.roadVehicles.length;
        const totalMarine = appState.marineVessels.length;
        const totalFlight = appState.flightPlanes.length;
        const grandTotal = totalRail + totalRoad + totalMarine + totalFlight;"""

new_stats_all = """        const totalRail = appState.railTrains.length + Object.keys(appState.hslVehicles).length;
        const totalBus = Object.keys(appState.busVehicles).length;
        const totalRoad = appState.roadVehicles.length;
        const totalMarine = appState.marineVessels.length;
        const totalFlight = appState.flightPlanes.length;
        const grandTotal = totalRail + totalBus + totalRoad + totalMarine + totalFlight;"""
assert old_stats_all in content, "stats all not found!"
content = content.replace(old_stats_all, new_stats_all)

# Statistics all mode breakdown
old_stats_breakdown = """          <div><b style="color:var(--rail-color)">🚆 Rail & Transit:</b> ${totalRail}</div>
          <div><b style="color:var(--road-color)">🚜 Road Maintenance:</b> ${totalRoad}</div>"""

new_stats_breakdown = """          <div><b style="color:var(--rail-color)">🚆 Rail & Transit:</b> ${totalRail}</div>
          <div><b style="color:var(--bus-color)">🚌 Buses (HSL & Föli):</b> ${totalBus}</div>
          <div><b style="color:var(--road-color)">🚜 Road Maintenance:</b> ${totalRoad}</div>"""
assert old_stats_breakdown in content, "stats all breakdown not found!"
content = content.replace(old_stats_breakdown, new_stats_breakdown)

# 23. Chart colors for bus
old_chart_colors = """      const colors = {
        rail: { border: '#2f81f7', bg: 'rgba(47, 129, 247, 0.12)' },
        road: { border: '#ffa500', bg: 'rgba(255, 165, 0, 0.12)' },"""
new_chart_colors = """      const colors = {
        rail: { border: '#2f81f7', bg: 'rgba(47, 129, 247, 0.12)' },
        bus: { border: '#007ac9', bg: 'rgba(0, 122, 201, 0.15)' },
        road: { border: '#ffa500', bg: 'rgba(255, 165, 0, 0.12)' },"""
assert old_chart_colors in content, "chart colors not found!"
content = content.replace(old_chart_colors, new_chart_colors)

# 24. Add fetchFoliBuses to triggerRefresh and init
old_refresh = """    function triggerRefresh() {
      fetchRailLocations();
      fetchRoadData();
      fetchMarineLocations();
      fetchFlightData();
    }"""
new_refresh = """    function triggerRefresh() {
      fetchRailLocations();
      fetchFoliBuses();
      fetchRoadData();
      fetchMarineLocations();
      fetchFlightData();
    }"""
assert old_refresh in content, "triggerRefresh not found!"
content = content.replace(old_refresh, new_refresh)

# In init():
old_init_calls = """        fetchRailLocations(),
        fetchRoadData(),"""
new_init_calls = """        fetchRailLocations(),
        fetchFoliBuses(),
        fetchRoadData(),"""
assert old_init_calls in content, "init calls not found!"
content = content.replace(old_init_calls, new_init_calls)

# In init() setInterval:
old_interval = """      setInterval(fetchRailLocations, CONFIG.intervals.rail);
      setInterval(fetchRoadData, CONFIG.intervals.road);"""
new_interval = """      setInterval(fetchRailLocations, CONFIG.intervals.rail);
      setInterval(fetchFoliBuses, CONFIG.intervals.bus);
      setInterval(fetchRoadData, CONFIG.intervals.road);"""
assert old_interval in content, "setInterval not found!"
content = content.replace(old_interval, new_interval)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: index.html updated with Bus Tracker!")
