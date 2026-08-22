// Page Livebox : état WAN de la box Orange lu par /api/livebox — collecteur sysbus
// sans secret, sparkline des latences HTTP mesurées par le serveur. Aucune dépendance.
"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";
const WIDTH = 600, HEIGHT = 140, PAD = 4;

function el(name, attrs) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
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

function drawLatency(values) {
  const svg = document.getElementById("lbx-chart");
  svg.replaceChildren();
  if (!values || values.length < 2) return;
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const x = (i) => PAD + (i / (values.length - 1)) * (WIDTH - 2 * PAD);
  const y = (v) => HEIGHT - PAD - ((v - min) / span) * (HEIGHT - 2 * PAD);
  const line = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  svg.appendChild(el("polygon", {
    points: `${PAD},${HEIGHT - PAD} ${line} ${WIDTH - PAD},${HEIGHT - PAD}`,
    class: "hist-area",
  }));
  svg.appendChild(el("polyline", { points: line, class: "hist-line" }));
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  setText("lbx-chart-note", T("hist.min_avg_max", {
    min: min.toFixed(1), avg: avg.toFixed(1), max: max.toFixed(1), unit: "ms",
  }));
}

function renderStatus(status) {
  const halo = document.getElementById("lbx-halo");
  if (!status) {
    halo.className = "wall-halo halo-warn";
    setText("lbx-state-text", T("livebox.no_data"));
    setText("lbx-sub", "—");
    return;
  }
  halo.className = `wall-halo${status.online ? "" : " halo-down"}`;
  setText("lbx-state-text", status.online
    ? T("livebox.online")
    : status.reachable ? T("livebox.wan_down") : T("livebox.offline"));
  setText("lbx-sub", [status.model, status.firmware].filter(Boolean).join(" · ") || "—");

  setText("lbx-link", status.link_type ? status.link_type.toUpperCase() : "—");
  setText("lbx-link-note", status.link_state === "up" ? T("livebox.link_up") : (status.link_state || "—"));
  setText("lbx-gpon", status.gpon_state || "—");
  setText("lbx-gpon-note", status.last_error && status.last_error !== "None"
    ? status.last_error : T("livebox.no_error"));
  setText("lbx-conn", status.connection_state === "Bound" ? T("livebox.bound") : (status.connection_state || "—"));
  setText("lbx-conn-note", status.protocol ? T("livebox.protocol", { protocol: status.protocol }) : "—");
  setText("lbx-ipv6", status.connection_state_ipv6 === "Bound" ? T("livebox.bound") : (status.connection_state_ipv6 || "—"));
  setText("lbx-ipv6-note", " ");
  setText("lbx-latency", status.latency_ms === null ? "—" : `${status.latency_ms} ms`);

  document.getElementById("lbx-identity").replaceChildren(
    kv(T("livebox.model"), status.model || "—"),
    kv(T("livebox.firmware"), status.firmware || "—"),
    kv(T("livebox.serial"), status.serial || "—"),
  );
}

async function refresh() {
  let data;
  try {
    const r = await fetch("/api/livebox");
    if (!r.ok) return;
    data = await r.json();
  } catch { return; }

  if (!data.enabled) {
    setText("lbx-sub", T("livebox.disabled"));
    setText("lbx-state-text", "—");
    return;
  }
  renderStatus(data.status);
  if (data.status && data.status.latency_history) drawLatency(data.status.latency_history);

  setText("refreshed", T("reseau.refreshed", { time: new Date().toLocaleTimeString() }));
}

refresh();
setInterval(() => { if (!document.hidden) refresh(); }, 15000);
