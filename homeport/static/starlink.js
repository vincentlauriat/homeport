// Page Starlink : statut de l'antenne, courbes 15 min tirées des buffers du dish,
// carte d'obstruction rendue pixel par pixel sur un canvas. Aucune dépendance.
"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";
const WIDTH = 600, HEIGHT = 140, PAD = 4;

function el(name, attrs) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

function mbps(bps) {
  return bps >= 1e8 ? Math.round(bps / 1e6) : Math.round(bps / 1e5) / 10;
}

function uptimeText(seconds) {
  const d = Math.floor(seconds / 86400), h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return T("starlink.uptime_dh", { d, h });
  if (h > 0) return T("starlink.uptime_hm", { h, m });
  return T("starlink.uptime_m", { m });
}

// Une ou deux séries sur le même repère ; l'aire n'est remplie que pour la première.
function drawSeries(svgId, seriesList, noteId, noteText) {
  const svg = document.getElementById(svgId);
  svg.replaceChildren();
  const all = seriesList.flatMap((s) => s.values).filter((v) => v !== null);
  if (all.length < 2) return;
  const min = Math.min(...all), max = Math.max(...all);
  const span = max - min || 1;
  const y = (v) => HEIGHT - PAD - ((v - min) / span) * (HEIGHT - 2 * PAD);

  seriesList.forEach((series, index) => {
    const n = series.values.length;
    if (n < 2) return;
    const x = (i) => PAD + (i / (n - 1)) * (WIDTH - 2 * PAD);
    const line = series.values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    if (index === 0) {
      svg.appendChild(el("polygon", {
        points: `${PAD},${HEIGHT - PAD} ${line} ${WIDTH - PAD},${HEIGHT - PAD}`,
        class: "hist-area",
      }));
    }
    svg.appendChild(el("polyline", { points: line, class: `hist-line${index ? " sl-line-alt" : ""}` }));
  });
  if (noteId) document.getElementById(noteId).textContent = noteText;
}

// Vue du ciel : chaque cellule est un pixel. snr < 0 = jamais utilisé (sombre),
// 0..1 = intensité du signal (bleu clair), exactement 0 = obstrué (rouge).
function drawMap(map) {
  if (!map || !map.rows || !map.snr.length) return;
  const canvas = document.getElementById("sl-map");
  canvas.width = map.cols;
  canvas.height = map.rows;
  const ctx = canvas.getContext("2d");
  const image = ctx.createImageData(map.cols, map.rows);
  map.snr.forEach((snr, i) => {
    const o = i * 4;
    if (snr < 0) {
      image.data[o] = 16; image.data[o + 1] = 20; image.data[o + 2] = 30; image.data[o + 3] = 255;
    } else if (snr === 0) {
      image.data[o] = 190; image.data[o + 1] = 50; image.data[o + 2] = 40; image.data[o + 3] = 255;
    } else {
      const v = Math.min(snr, 1);
      image.data[o] = 40 + 120 * v;
      image.data[o + 1] = 80 + 150 * v;
      image.data[o + 2] = 140 + 115 * v;
      image.data[o + 3] = 255;
    }
  });
  ctx.putImageData(image, 0, 0);
}

function kv(label, value) {
  const row = document.createElement("div");
  row.className = "sl-kv";
  const l = document.createElement("span");
  l.textContent = label;
  const v = document.createElement("b");
  v.textContent = value;
  row.append(l, v);
  return row;
}

function renderStatus(status) {
  const halo = document.getElementById("sl-halo");
  const stateText = document.getElementById("sl-state-text");
  if (!status) {
    halo.className = "wall-halo halo-warn";
    stateText.textContent = T("starlink.no_data");
    document.getElementById("sl-sub").textContent = "—";
    return;
  }
  halo.className = `wall-halo${status.online ? "" : " halo-down"}`;
  stateText.textContent = status.online
    ? T("starlink.online")
    : `${T("starlink.offline")} — ${T("starlink.outage_cause", { cause: status.outage_cause })}`;
  document.getElementById("sl-sub").textContent =
    [status.hardware, status.software, status.country].filter(Boolean).join(" · ");

  setTextContent("sl-latency", `${status.latency_ms} ms`);
  setTextContent("sl-drop", T("starlink.drop", { percent: (status.drop_rate * 100).toFixed(2) }));
  setTextContent("sl-down", `${mbps(status.downlink_bps)} Mb/s`);
  setTextContent("sl-up", `${mbps(status.uplink_bps)} Mb/s`);

  const obstruction = status.obstruction || {};
  setTextContent("sl-obstruction", `${(obstruction.fraction * 100).toFixed(2)} %`);
  setTextContent("sl-obstruction-note", obstruction.currently
    ? T("starlink.obstructed_now")
    : obstruction.avg_prolonged_s
      ? T("starlink.obstruction_avg", { seconds: obstruction.avg_prolonged_s })
      : T("starlink.clear_sky"));

  const gps = status.gps || {};
  setTextContent("sl-gps", T("starlink.gps_sats", { count: gps.sats }));
  setTextContent("sl-gps-note", gps.valid ? T("starlink.gps_valid") : T("starlink.gps_invalid"));
  setTextContent("sl-eth", status.eth_speed_mbps ? `${status.eth_speed_mbps} Mb/s` : "—");
  setTextContent("sl-snr", status.snr_above_noise_floor ? T("starlink.snr_ok") : T("starlink.snr_low"));

  const alerts = document.getElementById("sl-alerts");
  if (status.alerts && status.alerts.length) {
    alerts.hidden = false;
    alerts.replaceChildren();
    const div = document.createElement("div");
    div.className = "alert alert-warn";
    div.textContent = T("starlink.alerts_label", {
      alerts: status.alerts.map((a) => a.replaceAll("_", " ")).join(", "),
    });
    alerts.appendChild(div);
  } else {
    alerts.hidden = true;
  }

  const alignment = status.alignment || {};
  document.getElementById("sl-identity").replaceChildren(
    kv(T("starlink.hardware"), status.hardware || "—"),
    kv(T("starlink.software"), status.software || "—"),
    kv(T("starlink.country"), status.country || "—"),
    kv(T("starlink.uptime"), uptimeText(status.uptime_s)),
    kv(T("starlink.tilt"), `${alignment.tilt_deg}°`),
    kv(T("starlink.azimuth"), `${alignment.azimuth_deg}°`),
    kv(T("starlink.elevation"), `${alignment.elevation_deg}°`),
  );
}

function setTextContent(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

async function refresh() {
  let data;
  try {
    const r = await fetch("/api/starlink");
    if (!r.ok) return;
    data = await r.json();
  } catch { return; }

  if (!data.enabled) {
    document.getElementById("sl-sub").textContent = T("starlink.disabled");
    document.getElementById("sl-state-text").textContent = "—";
    return;
  }
  renderStatus(data.status);

  const history = data.history;
  if (history && history.latency_ms && history.latency_ms.length) {
    const lat = history.latency_ms;
    const avg = lat.reduce((a, b) => a + b, 0) / lat.length;
    drawSeries("sl-chart-latency", [{ values: lat }], "sl-chart-latency-note",
      T("hist.min_avg_max", { min: Math.min(...lat).toFixed(0), avg: avg.toFixed(0), max: Math.max(...lat).toFixed(0), unit: "ms" }));
    const down = history.downlink_bps.map((v) => v / 1e6);
    const up = history.uplink_bps.map((v) => v / 1e6);
    drawSeries("sl-chart-throughput", [{ values: down }, { values: up }], "sl-chart-throughput-note",
      `↓ max ${Math.max(...down).toFixed(0)} · ↑ max ${Math.max(...up).toFixed(1)} Mb/s`);
  }
  drawMap(data.map);

  document.getElementById("refreshed").textContent =
    T("reseau.refreshed", { time: new Date().toLocaleTimeString() });
}

refresh();
setInterval(() => { if (!document.hidden) refresh(); }, 10000);
