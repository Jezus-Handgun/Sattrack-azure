"use strict";

// One colour per constellation, used on the map, skyplot, chips, table and chart.
const COLORS = {
  gps: "#2563eb",
  galileo: "#f59e0b",
  glonass: "#dc2626",
  beidou: "#16a34a",
  stations: "#7c3aed",
  total: "#111827",
};
const NAMES = { gps: "GPS", galileo: "Galileo", glonass: "GLONASS", beidou: "BeiDou", total: "Razem" };
const GNSS = ["gps", "galileo", "glonass", "beidou"];
const ISS_NORAD = 25544;
const REFRESH_MAP_MS = 5000;
const REFRESH_VISIBLE_MS = 30000;

const $ = (id) => document.getElementById(id);
const fmtTime = new Intl.DateTimeFormat("pl-PL", { hour: "2-digit", minute: "2-digit" });
const fmtDay = new Intl.DateTimeFormat("pl-PL", { weekday: "short", day: "2-digit", month: "2-digit" });

const state = {
  group: "gps",
  groups: [],
  markers: new Map(), // norad_id -> L.circleMarker
  selected: null, // norad_id
  point: null, // {lat, lon}
  chart: null,
};

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

function esc(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function td(text, cls = "") {
  return `<td class="${cls}">${esc(String(text))}</td>`;
}

function dot(key) {
  return `<span class="dot" style="background:${COLORS[key]}"></span>`;
}

function ago(iso) {
  const min = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
  if (min < 60) return `${min} min temu`;
  const h = Math.floor(min / 60);
  if (h < 48) return `${h} h ${min % 60} min temu`;
  return `${Math.floor(h / 24)} dni temu`;
}

// ---------- user bar ----------

async function loadUser() {
  try {
    const me = await getJSON("/api/me");
    if (me.mode !== "local" && me.name) {
      $("user-name").textContent = me.name;
      $("logout").hidden = false;
      return;
    }
  } catch {
    // no /api/me or no auth headers: local mode
  }
  $("user-name").textContent = "Tryb lokalny (bez logowania)";
}

// ---------- live map ----------

const map = L.map("map", { worldCopyJump: true, minZoom: 2, preferCanvas: true }).setView([35, 15], 2);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 12,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

const satLayer = L.layerGroup().addTo(map);
const trackLayer = L.layerGroup().addTo(map);
const pointMarker = L.marker([0, 0], { title: "Punkt pomiaru" });

function markerStyle(norad) {
  const selected = norad === state.selected;
  return {
    radius: selected ? 9 : 6,
    color: selected ? "#111827" : "#ffffff",
    weight: selected ? 3 : 1.5,
    fillColor: COLORS[state.group],
    fillOpacity: 0.95,
  };
}

async function refreshSatellites() {
  const group = state.group;
  const sats = await getJSON(`/api/satellites?group=${group}`);
  if (group !== state.group) return; // group changed while loading
  const seen = new Set();
  for (const s of sats) {
    seen.add(s.norad_id);
    let m = state.markers.get(s.norad_id);
    if (!m) {
      m = L.circleMarker([s.lat, s.lon], { bubblingMouseEvents: false, ...markerStyle(s.norad_id) });
      m.bindTooltip("");
      m.on("click", () => selectSatellite(s.norad_id));
      m.addTo(satLayer);
      state.markers.set(s.norad_id, m);
    }
    m.setLatLng([s.lat, s.lon]);
    m.setTooltipContent(esc(s.name));
    m.sat = s;
    if (s.norad_id === state.selected) showSatPanel(s);
  }
  for (const [id, m] of state.markers) {
    if (!seen.has(id)) {
      satLayer.removeLayer(m);
      state.markers.delete(id);
    }
  }
  state.markers.get(ISS_NORAD)?.bringToFront(); // docked vehicles share its position
}

function showSatPanel(s) {
  $("sat-name").textContent = s.name;
  $("sat-norad").textContent = s.norad_id;
  $("sat-alt").textContent = `${s.alt_km.toLocaleString("pl-PL", { maximumFractionDigits: 0 })} km`;
  $("sat-speed").textContent = `${s.speed_km_s.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} km/s`;
  $("sat-pos").textContent = `${s.lat.toFixed(2)}°, ${s.lon.toFixed(2)}°`;
  $("sat-panel").hidden = false;
}

// Split the track where it crosses the antimeridian so Leaflet doesn't draw a line across the map.
function splitTrack(points) {
  const segments = [[]];
  for (let i = 0; i < points.length; i++) {
    if (i > 0 && Math.abs(points[i].lon - points[i - 1].lon) > 180) segments.push([]);
    segments.at(-1).push([points[i].lat, points[i].lon]);
  }
  return segments;
}

async function selectSatellite(norad) {
  const previous = state.selected;
  state.selected = norad;
  for (const id of [previous, norad]) state.markers.get(id)?.setStyle(markerStyle(id));
  const detail = await getJSON(`/api/satellites/${norad}`);
  if (state.selected !== norad) return;
  showSatPanel(detail);
  trackLayer.clearLayers();
  L.polyline(splitTrack(detail.track), { color: COLORS[detail.group], weight: 2.5, dashArray: "6 4" }).addTo(trackLayer);
}

function clearSelection() {
  const previous = state.selected;
  state.selected = null;
  state.markers.get(previous)?.setStyle(markerStyle(previous));
  trackLayer.clearLayers();
  $("sat-panel").hidden = true;
}

function showDataAge() {
  const g = state.groups.find((x) => x.key === state.group);
  if (!g) return;
  $("data-age").textContent = g.fetched_at
    ? `Dane orbitalne: ${ago(g.fetched_at)} (CelesTrak)`
    : `Dane orbitalne: snapshot, epoka ${ago(g.newest_epoch)}`;
}

async function loadGroups() {
  state.groups = await getJSON("/api/groups");
  $("group").innerHTML = state.groups
    .map((g) => `<option value="${g.key}">${esc(g.label)} – ${g.count}</option>`)
    .join("");
  $("group").value = state.group;
  showDataAge();
}

$("group").addEventListener("change", async (e) => {
  state.group = e.target.value;
  clearSelection();
  satLayer.clearLayers();
  state.markers.clear();
  showDataAge();
  await refreshSatellites();
});
$("sat-close").addEventListener("click", clearSelection);

// ---------- observation point: skyplot, table, chart, passes ----------

function skyXY(elevation, azimuth) {
  const r = (100 * (90 - elevation)) / 90; // centre = zenith, r = 100 = horizon
  const a = (azimuth * Math.PI) / 180;
  return [r * Math.sin(a), -r * Math.cos(a)];
}

function drawSkyplot(data) {
  const maskR = (100 * (90 - data.min_elevation)) / 90;
  let svg = `<circle class="horizon" r="100"/>`;
  for (const el of [30, 60]) {
    const r = (100 * (90 - el)) / 90;
    svg += `<circle class="grid" r="${r}"/><text x="2" y="${-r - 2}">${el}°</text>`;
  }
  svg += `<circle class="mask" r="${maskR}"><title>Maska elewacji ${data.min_elevation}°</title></circle>`;
  svg += `<line class="grid" x1="0" y1="-100" x2="0" y2="100"/><line class="grid" x1="-100" y1="0" x2="100" y2="0"/>`;
  svg += `<text class="cardinal" x="0" y="-106" text-anchor="middle">N</text>`;
  svg += `<text class="cardinal" x="110" y="4" text-anchor="middle">E</text>`;
  svg += `<text class="cardinal" x="0" y="116" text-anchor="middle">S</text>`;
  svg += `<text class="cardinal" x="-110" y="4" text-anchor="middle">W</text>`;
  for (const s of data.satellites) {
    const [x, y] = skyXY(s.elevation_deg, s.azimuth_deg);
    svg += `<circle class="sat" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5" fill="${COLORS[s.constellation]}">`;
    svg += `<title>${esc(s.name)} – el. ${s.elevation_deg.toFixed(0)}°, az. ${s.azimuth_deg.toFixed(0)}°</title></circle>`;
  }
  $("skyplot").innerHTML = svg;
}

function showVisible(data) {
  $("counts").innerHTML = [...GNSS, "total"]
    .map((k) => `<span class="chip">${dot(k)}${NAMES[k]} <b>${data.counts[k]}</b></span>`)
    .join("");
  drawSkyplot(data);
  $("visible-time").textContent =
    `Stan na ${fmtTime.format(new Date(data.time))} · ${data.lat.toFixed(4)}°, ${data.lon.toFixed(4)}°`;
  $("visible-body").innerHTML = data.satellites
    .map(
      (s) =>
        `<tr>${td(s.name)}<td>${dot(s.constellation)} ${NAMES[s.constellation]}</td>` +
        `${td(s.elevation_deg.toFixed(1) + "°", "num")}${td(s.azimuth_deg.toFixed(1) + "°", "num")}</tr>`,
    )
    .join("");
  for (const el of document.querySelectorAll(".mask-value")) el.textContent = `${data.min_elevation}°`;
}

function showTimeline(data) {
  const labels = data.times.map((t) => fmtTime.format(new Date(t)));
  const datasets = [...GNSS, "total"].map((k) => ({
    label: NAMES[k],
    data: data.counts[k],
    borderColor: COLORS[k],
    backgroundColor: COLORS[k],
    borderWidth: k === "total" ? 3 : 2,
    pointRadius: 0,
    tension: 0.25,
  }));
  if (state.chart) {
    state.chart.data.labels = labels;
    state.chart.data.datasets = datasets;
    state.chart.update();
    return;
  }
  state.chart = new Chart($("timeline"), {
    type: "line",
    data: { labels, datasets },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: {
        x: { ticks: { maxTicksLimit: 13 } },
        y: { beginAtZero: true, title: { display: true, text: "Liczba satelitów" } },
      },
    },
  });
}

function showPasses(data) {
  if (!data.passes.length) {
    $("passes-body").innerHTML = `<tr><td colspan="5" class="muted">Brak przelotów w tym czasie</td></tr>`;
    return;
  }
  $("passes-body").innerHTML = data.passes
    .map((p) => {
      const rise = new Date(p.rise);
      return (
        `<tr>${td(fmtDay.format(rise))}${td(fmtTime.format(rise))}` +
        `${td(fmtTime.format(new Date(p.culmination)))}${td(p.max_elevation_deg.toFixed(0) + "°", "num")}` +
        `${td(fmtTime.format(new Date(p.set)))}</tr>`
      );
    })
    .join("");
}

async function refreshVisible() {
  const { lat, lon } = state.point;
  showVisible(await getJSON(`/api/visible?lat=${lat}&lon=${lon}`));
}

async function setPoint(lat, lon) {
  state.point = { lat, lon };
  $("lat").value = lat.toFixed(4);
  $("lon").value = lon.toFixed(4);
  pointMarker.setLatLng([lat, lon]).addTo(map);
  const q = `lat=${lat}&lon=${lon}`;
  await Promise.all([
    refreshVisible(),
    getJSON(`/api/visibility-timeline?${q}`).then(showTimeline),
    getJSON(`/api/passes/${ISS_NORAD}?${q}`).then(showPasses),
  ]);
}

map.on("click", (e) => {
  const lon = ((((e.latlng.lng + 180) % 360) + 360) % 360) - 180; // map may be panned past ±180
  setPoint(e.latlng.lat, lon);
});

$("point-form").addEventListener("submit", (e) => {
  e.preventDefault();
  setPoint(Number($("lat").value), Number($("lon").value));
});

// ---------- start ----------

async function start() {
  loadUser();
  await loadGroups();
  await refreshSatellites();
  const initial = await getJSON("/api/visible"); // server default point (Chorzów)
  await setPoint(initial.lat, initial.lon);

  setInterval(() => document.hidden || refreshSatellites().catch(console.error), REFRESH_MAP_MS);
  setInterval(() => document.hidden || refreshVisible().catch(console.error), REFRESH_VISIBLE_MS);
}

start().catch(console.error);
