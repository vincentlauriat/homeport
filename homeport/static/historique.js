// Page Historique : courbes SVG dessinées à la main (aucune dépendance, comme le reste),
// coupures Internet surimprimées en bandes rouges — la corrélation se voit, elle ne se déduit pas.
"use strict";

let windowHours = 24;

const SVG_NS = "http://www.w3.org/2000/svg";
const WIDTH = 600, HEIGHT = 140, PAD = 4;

function el(name, attrs) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

function drawChart(svgId, samples, field, outages, windowStart, windowEnd) {
  const svg = document.getElementById(svgId);
  svg.replaceChildren();
  const points = samples.filter((s) => s[field] !== null && s[field] !== undefined);
  if (points.length < 2) return null;

  const values = points.map((s) => s[field]);
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const x = (ts) => PAD + ((ts - windowStart) / (windowEnd - windowStart)) * (WIDTH - 2 * PAD);
  const y = (v) => HEIGHT - PAD - ((v - min) / span) * (HEIGHT - 2 * PAD);

  // Bandes de coupure Internet d'abord (sous la courbe).
  for (const outage of outages) {
    const start = Math.max(outage.start_ts, windowStart);
    const end = Math.min(outage.start_ts + outage.minutes * 60, windowEnd);
    if (end <= windowStart || start >= windowEnd) continue;
    svg.appendChild(el("rect", {
      x: x(start), y: 0, width: Math.max(x(end) - x(start), 2), height: HEIGHT,
      class: "hist-outage",
    }));
  }

  // Aire sous la courbe puis la courbe elle-même.
  const line = points.map((s) => `${x(s.ts).toFixed(1)},${y(s[field]).toFixed(1)}`).join(" ");
  const first = points[0], last = points[points.length - 1];
  svg.appendChild(el("polygon", {
    points: `${x(first.ts).toFixed(1)},${HEIGHT - PAD} ${line} ${x(last.ts).toFixed(1)},${HEIGHT - PAD}`,
    class: "hist-area",
  }));
  svg.appendChild(el("polyline", { points: line, class: "hist-line" }));

  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  return { min, max, avg };
}

function note(id, stats, unit) {
  document.getElementById(id).textContent = stats
    ? `min ${stats.min.toFixed(1)} · moy ${stats.avg.toFixed(1)} · max ${stats.max.toFixed(1)} ${unit}`
    : "pas encore assez de mesures";
}

async function refresh() {
  let samples, outages;
  try {
    const [h, o] = await Promise.all([
      fetch(`/api/history?hours=${windowHours}`),
      fetch(`/api/outages?hours=${windowHours}`),
    ]);
    if (!h.ok || !o.ok) return;
    samples = await h.json();
    outages = (await o.json()).outages;
  } catch { return; }

  const now = Math.floor(Date.now() / 1000);
  const windowStart = now - windowHours * 3600;

  note("hist-cpu-note", drawChart("hist-cpu", samples, "cpu_pct", outages, windowStart, now), "%");
  note("hist-mem-note", drawChart("hist-mem", samples, "mem_pct", outages, windowStart, now), "%");
  note("hist-temp-note", drawChart("hist-temp", samples, "temp_c", outages, windowStart, now), "°C");
  note("hist-nvme-note", drawChart("hist-nvme", samples, "nvme_temp_c", outages, windowStart, now), "°C");

  const label = windowHours === 24 ? "24 heures" : windowHours === 72 ? "3 jours" : "7 jours";
  document.getElementById("hist-summary").textContent =
    `${samples.length} mesures sur ${label} · ${outages.length} coupure(s) Internet`;
  document.getElementById("refreshed").textContent =
    `actualisé ${new Date().toLocaleTimeString("fr-FR")}`;
}

document.getElementById("windows").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-hours]");
  if (!button) return;
  windowHours = Number(button.dataset.hours);
  for (const b of document.querySelectorAll("#windows button")) {
    b.classList.toggle("active", b === button);
  }
  refresh();
});

refresh();
setInterval(() => { if (!document.hidden) refresh(); }, 60000);
