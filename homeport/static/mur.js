// Vue C — Le mur : tablette murale, chiffres géants lisibles à trois mètres.
// Coquille HTML statique + rendu client depuis /api/status (pattern /reseau).

const { setText, drawSpark, verdict, backupAge, startPolling } = window.RaspViews;

// Horloge locale — indépendante du sondage : elle bat même si le Pi ne répond plus.
function tickClock() {
  const now = new Date();
  setText('w-clock', now.toLocaleTimeString(document.documentElement.lang, { hour: '2-digit', minute: '2-digit' }));
  setText('w-date', now.toLocaleDateString(document.documentElement.lang, { weekday: 'long', day: 'numeric', month: 'long' }));
}
tickClock();
setInterval(tickClock, 10000);

const setCell = (id, big, small, foot, level) => {
  const cell = document.getElementById(id);
  if (!cell) return;
  cell.className = `wall-cell${level ? ` wall-${level}` : ''}`;
  const bigNode = cell.querySelector('.big');
  if (bigNode) {
    bigNode.textContent = big;
    if (small) {
      const suffix = document.createElement('small');
      suffix.textContent = ` ${small}`;
      bigNode.appendChild(suffix);
    }
  }
  const footNode = cell.querySelector('.foot');
  if (footNode) footNode.textContent = foot;
};

function render(data) {
  setText('w-hostname', data.system.hostname);

  const v = verdict(data);
  const halo = document.getElementById('w-halo');
  if (halo) halo.className = `wall-halo halo-${v.level}`;
  const state = document.getElementById('w-state');
  if (state) state.className = `wall-state state-${v.level}`;
  setText('w-state-text', `${data.system.hostname} — ${v.text.replace(/\.$/, '').toLowerCase()}`);

  const s = data.summary;
  const availAll = [];
  for (const group of data.groups) for (const svc of group.services) {
    if (svc.availability) availAll.push(svc.availability.uptime_pct);
  }
  const worst = availAll.length ? Math.min(...availAll) : null;
  setCell('w-services', `${s.up}`, `/ ${s.total}`,
    worst === null ? '' : (worst >= 100 ? T('wall.avail_100') : T('wall.avail_worst', { pct: worst })),
    s.down ? 'down' : s.warn ? 'warn' : 'ok');

  const wan = data.wan;
  if (wan) {
    setCell('w-internet',
      wan.online === null ? '—' : wan.online ? `${wan.latency_ms}` : T('net.offline'),
      wan.online ? 'ms' : '',
      wan.outages_24h ? Tn('net.outages_detail', wan.outages_24h) : T('net.no_outage'),
      wan.online ? 'ok' : wan.online === false ? 'down' : '');
  }

  const age = backupAge(data.health);
  const backups = ((data.health || {}).backups || []);
  const marks = backups.map((b) => `${b.name} ${b.state === 'ok' ? '✓' : '✗'}`).join(' · ');
  setCell('w-backup', age === null ? '—' : `${age}`, age === null ? '' : 'h',
    marks,
    age !== null && age < 30 ? 'ok' : 'warn');

  const apt = (data.health || {}).apt;
  if (apt) {
    setCell('w-updates', `${apt.security}`, T('wall.updates_security'),
      apt.total ? T('wall.updates_total', { count: apt.total }) : T('wall.updates_none'),
      apt.security ? 'warn' : 'ok');
  }

  const net = data.network || {};
  const lan = (net.lan_neighbors || []).length;
  const fresh = (net.new_devices || {}).count || 0;
  const peersOnline = (net.tailscale_peers || []).filter((p) => p.online).length;
  setCell('w-lan', `${lan}`, '',
    T('wall.lan_detail', { fresh, peers: peersOnline }),
    fresh ? 'warn' : '');

  // Pied : détails machine en petit.
  const sys = data.system;
  const nvme = data.nvme;
  const wear = nvme && nvme.percent_used !== null && nvme.percent_used !== undefined ? ' · ' + T('wall.ssd_wear', { pct: nvme.percent_used }) : '';
  setText('wf-ssd', sys.storage_temperature_c === null ? '' : T('wall.ssd', { temp: sys.storage_temperature_c }) + wear);
  setText('wf-mem', T('wall.mem', { pct: sys.memory.percent }));
  const power = (data.health || {}).throttling;
  setText('wf-power', sys.undervoltage ? T('wall.power_undervoltage')
    : power && power.available ? T('wall.power', { state: T(power.healthy ? 'health.power_ok' : 'health.power_incident') }) : '');
  setText('wf-ip', data.public_ip ? T('wall.public_ip', { ip: data.public_ip.ip }) : '');
  const starlink = data.starlink;
  setText('wf-starlink', !starlink ? ''
    : starlink.online
      ? T('wall.starlink', { latency: starlink.latency_ms, down: Math.round(starlink.downlink_bps / 1e6) })
      : `Starlink — ${T('starlink.offline')}`);
  const livebox = data.livebox;
  setText('wf-livebox', !livebox ? ''
    : livebox.online
      ? T('wall.livebox', { latency: livebox.latency_ms })
      : `Livebox — ${T(livebox.reachable ? 'livebox.wan_down' : 'livebox.offline')}`);

  // Le pied CPU de la cellule sparkline vient du statut, la courbe de /api/history.
  const cpuFoot = document.querySelector('#w-cpu .foot');
  if (cpuFoot) {
    const temp = sys.temperature_c === null ? '' : ` · ${sys.temperature_c} °C`;
    cpuFoot.textContent = `${sys.load.percent} %${window.__cpuPeak !== undefined ? ' · ' + T('wall.peak', { pct: window.__cpuPeak }) : ''}${temp}`;
  }
}

function renderHistory(samples) {
  if (samples.length < 2) return;
  const points = samples.map((sample) => ({ ts: sample.ts, value: sample.cpu_pct ?? 0 }));
  window.__cpuPeak = Math.round(Math.max(...points.map((p) => p.value)));
  drawSpark(document.getElementById('w-spark'), points, { min: 0, max: 100 }, 44);
}

startPolling(render, renderHistory);
