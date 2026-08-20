// Page Réseau : inventaire des appareils, nommage, acquittement.
// Tout le rendu passe par textContent — les noms mDNS viennent du réseau, jamais innerHTML.
"use strict";

let devicesCache = [];
let peersCache = [];
let activeFilter = "all";
let searchTerm = "";
let editing = false; // un input de nommage est ouvert : le refresh périodique s'abstient
let canAct = false;  // admin via Tailscale (voir /api/whoami) : révèle le Wake-on-LAN

const CATEGORIES = ["computer", "phone", "homeautomation", "iot", "network", "media", "other"];

function relativeTime(ts) {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return T("age.just_now");
  if (s < 3600) return T("age.minutes", { count: Math.floor(s / 60) });
  if (s < 86400) return T("age.hours", { count: Math.floor(s / 3600) });
  return T("age.days", { count: Math.floor(s / 86400) });
}

async function patchDevice(mac, body) {
  const r = await fetch(`/api/devices/${encodeURIComponent(mac)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.ok) await refresh(true);
  return r.ok;
}

function matches(device) {
  if (activeFilter === "online" && !device.online) return false;
  if (activeFilter === "new" && device.acknowledged) return false;
  if (CATEGORIES.includes(activeFilter) && device.category !== activeFilter) return false;
  if (searchTerm) {
    const haystack = [device.display_name, device.last_ip, device.mac, device.vendor]
      .filter(Boolean).join(" ").toLowerCase();
    if (!haystack.includes(searchTerm)) return false;
  }
  return true;
}

function startEditing(nameEl, device) {
  editing = true;
  const input = document.createElement("input");
  input.className = "net-name-input";
  input.value = device.name || "";
  input.maxLength = 64;
  nameEl.replaceWith(input);
  input.focus();
  const done = () => { editing = false; refresh(true); };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      editing = false;
      patchDevice(device.mac, { name: input.value.trim() || null });
    }
    if (e.key === "Escape") done();
  });
  input.addEventListener("blur", done);
}

function renderDetails(device) {
  const details = document.createElement("details");
  details.className = "net-details";
  const summary = document.createElement("summary");
  summary.textContent = T("reseau.details");
  details.appendChild(summary);

  const panel = document.createElement("div");
  panel.className = "net-details-panel";

  const note = document.createElement("textarea");
  note.placeholder = T("reseau.note_placeholder");
  note.value = device.note || "";
  note.maxLength = 500;
  const saveNote = document.createElement("button");
  saveNote.textContent = T("reseau.save_note");
  saveNote.addEventListener("click", () => patchDevice(device.mac, { note: note.value.trim() || null }));

  const select = document.createElement("select");
  for (const value of ["", ...CATEGORIES]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value ? T(`category.${value}`) : T("category.none");
    option.selected = (device.category || "") === value;
    select.appendChild(option);
  }
  select.addEventListener("change", () => patchDevice(device.mac, { category: select.value || null }));

  panel.append(note, saveNote, select);
  if (!device.acknowledged) {
    const ack = document.createElement("button");
    ack.className = "btn-ack";
    ack.textContent = T("reseau.ack");
    ack.addEventListener("click", () => patchDevice(device.mac, { acknowledged: true }));
    panel.appendChild(ack);
  }
  if (canAct && !device.online) {
    const wake = document.createElement("button");
    wake.className = "btn-wake";
    wake.textContent = T("reseau.wake");
    wake.title = T("reseau.wake_title");
    wake.addEventListener("click", async () => {
      wake.disabled = true;
      const r = await fetch(`/api/actions/wake/${encodeURIComponent(device.mac)}`, { method: "POST" });
      wake.textContent = r.ok ? T("reseau.wake_sent") : T("reseau.wake_failed", { status: r.status });
      setTimeout(() => { wake.disabled = false; wake.textContent = T("reseau.wake"); }, 5000);
    });
    panel.appendChild(wake);
  }
  details.appendChild(panel);
  return details;
}

function renderDevice(device) {
  const row = document.createElement("div");
  row.className = `net-row${device.acknowledged ? "" : " net-row-new"}`;

  const head = document.createElement("div");
  head.className = "net-row-head";

  const dot = document.createElement("span");
  dot.className = `dot ${device.online ? "dot-online" : "dot-offline"}`;
  dot.title = device.online ? T("reseau.online") : T("reseau.offline");
  head.appendChild(dot);

  const name = document.createElement("button");
  name.className = "net-name";
  name.textContent = device.display_name;
  name.title = T("reseau.name_title", { source: T(`namesource.${device.name_source}`) });
  name.addEventListener("click", () => startEditing(name, device));
  head.appendChild(name);

  if (device.category) {
    const cat = document.createElement("span");
    cat.className = "badge-cat";
    cat.textContent = T(`category.${device.category}`);
    head.appendChild(cat);
  }
  if (device.local_mac) {
    const badge = document.createElement("span");
    badge.className = "badge-private";
    badge.textContent = T("reseau.private_mac");
    badge.title = T("reseau.private_mac_title");
    head.appendChild(badge);
  }

  const seen = document.createElement("span");
  seen.className = "net-seen";
  seen.textContent = relativeTime(device.last_seen);
  head.appendChild(seen);
  row.appendChild(head);

  const meta = document.createElement("div");
  meta.className = "net-row-meta";
  for (const text of [device.last_ip || "—", device.mac, device.vendor || ""]) {
    if (!text) continue;
    const cell = document.createElement("span");
    cell.className = "net-cell";
    cell.textContent = text;
    meta.appendChild(cell);
  }
  row.appendChild(meta);

  row.appendChild(renderDetails(device));
  return row;
}

function ensureCategoryButtons() {
  const present = [...new Set(devicesCache.map((d) => d.category).filter(Boolean))].sort();
  const container = document.getElementById("filters");
  for (const category of present) {
    if (!container.querySelector(`button[data-filter="${category}"]`)) {
      const button = document.createElement("button");
      button.dataset.filter = category;
      button.textContent = T(`category.${category}`);
      container.appendChild(button);
    }
  }
}

function render(summary, available) {
  document.getElementById("net-summary").textContent = available
    ? T("reseau.summary", { total: summary.total, online: summary.online, fresh: summary.new })
    : T("reseau.unavailable");

  const fresh = devicesCache.filter((d) => !d.acknowledged);
  document.getElementById("new-devices").hidden = fresh.length === 0;
  document.getElementById("new-list").replaceChildren(...fresh.map(renderDevice));

  document.getElementById("devices").replaceChildren(
    ...devicesCache.filter(matches).map(renderDevice)
  );

  document.getElementById("peers").replaceChildren(...peersCache.map((p) => {
    const chip = document.createElement("span");
    chip.className = `peer peer-${p.online ? "online" : "offline"}`;
    chip.textContent = p.tailscale_ip ? `${p.hostname} · ${p.tailscale_ip}` : p.hostname;
    return chip;
  }));

  ensureCategoryButtons();
}

function summarize() {
  return {
    total: devicesCache.length,
    online: devicesCache.filter((d) => d.online).length,
    new: devicesCache.filter((d) => !d.acknowledged).length,
  };
}

async function refresh(force = false) {
  if (editing && !force) return;
  let data;
  try {
    const r = await fetch("/api/devices");
    if (!r.ok) return;
    data = await r.json();
  } catch {
    return; // réseau momentanément indisponible : on garde l'affichage courant
  }
  devicesCache = data.devices;
  peersCache = data.tailscale_peers;
  render(data.summary, data.inventory_available);
  document.getElementById("refreshed").textContent =
    T("reseau.refreshed", { time: new Date().toLocaleTimeString() });
}

function wireToolbar() {
  document.getElementById("search").addEventListener("input", (e) => {
    searchTerm = e.target.value.trim().toLowerCase();
    render(summarize(), true);
  });
  document.getElementById("filters").addEventListener("click", (e) => {
    const button = e.target.closest("button[data-filter]");
    if (!button) return;
    activeFilter = button.dataset.filter;
    for (const b of document.querySelectorAll("#filters button")) {
      b.classList.toggle("active", b === button);
    }
    render(summarize(), true);
  });
}

async function checkIdentity() {
  try {
    const r = await fetch("/api/whoami", { cache: "no-store" });
    canAct = r.ok && (await r.json()).can_act;
  } catch { canAct = false; }
}

wireToolbar();
checkIdentity().then(refresh);
setInterval(() => { if (!document.hidden) refresh(); }, 5000);
