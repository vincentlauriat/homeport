// Vue A — Salle de contrôle : dense, deux colonnes, tout visible sans défiler.
// Coquille HTML statique + rendu client depuis /api/status (pattern /reseau).

const { setText, setBar, drawSpark, backupAge, startPolling } = window.RaspViews;

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};

const setPill = (id, value, level) => {
  const pill = document.getElementById(id);
  if (!pill) return;
  pill.querySelector('b').textContent = value;
  pill.className = `cpill${level ? ` cpill-${level}` : ''}`;
};

function renderPills(data) {
  const s = data.summary;
  setPill('p-services', `${s.up}/${s.total}`, s.down ? 'down' : s.warn ? 'warn' : 'up');

  const wan = data.wan;
  setPill('p-internet', !wan || wan.online === null ? '—'
    : wan.online ? `${wan.latency_ms} ms` : T('net.offline'),
    !wan || wan.online === null ? '' : wan.online ? 'up' : 'down');

  const age = backupAge(data.health);
  setPill('p-backup', age === null ? '—' : `${age} h`, age === null ? '' : age < 30 ? 'up' : 'warn');

  const alerts = ((data.health || {}).alerts || []).length;
  setPill('p-alerts', alerts, alerts ? 'warn' : 'up');

  const apt = (data.health || {}).apt;
  setPill('p-apt', apt ? apt.security : '—', apt && apt.security ? 'warn' : apt ? 'up' : '');
}

function renderMachine(system, nvme) {
  setText('v-cpu', `${system.load.percent} %`);
  setBar('b-cpu', system.load.percent);
  setText('v-mem', `${system.memory.percent} %`);
  setBar('b-mem', system.memory.percent);
  setText('v-temp', system.temperature_c === null ? '—' : `${system.temperature_c} °C`);
  setBar('b-temp', ((system.temperature_c ?? 0) / 85) * 100);
  setText('v-ssd', system.storage_temperature_c === null ? '—' : `${system.storage_temperature_c} °C`);
  setBar('b-ssd', ((system.storage_temperature_c ?? 0) / 70) * 100);

  if (nvme && nvme.percent_used !== null && nvme.percent_used !== undefined) {
    document.getElementById('row-wear').hidden = false;
    setText('v-wear', `${nvme.percent_used} %`);
    setBar('b-wear', Math.max(nvme.percent_used, 1));
  }

  const root = (system.disks || []).find((d) => d.mount === '/');
  if (root) {
    setText('v-disk', `${root.percent} %`);
    setBar('b-disk', root.percent);
  }
}

// Lignes clé/valeur d'un panneau — reconstruites à chaque cycle (peu d'éléments, listes
// de longueur variable : plus simple et plus sûr que de rapprocher des lignes existantes).
function renderKv(containerId, rows) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.replaceChildren(...rows.map(({ k, v, level }) => {
    const row = el('div', 'ckv');
    row.appendChild(el('span', 'k', k));
    row.appendChild(el('span', `v${level ? ` ${level}` : ''}`, v));
    return row;
  }));
}

function renderHealth(data) {
  const h = data.health || {};
  const rows = [];
  for (const backup of h.backups || []) {
    rows.push({
      k: T('health.backup', { name: backup.name }),
      v: backup.state === 'never' ? T('common.never') : backup.detail,
      level: backup.state === 'never' ? 'down' : backup.state === 'warn' ? 'warn' : 'ok',
    });
  }
  for (const sf of data.status_files || []) {
    rows.push({
      k: sf.name,
      v: sf.age_hours !== null && sf.age_hours !== undefined
        ? T('common.ago_hours', { count: sf.age_hours }) : (sf.message || T('common.pending')),
      level: sf.level === 'up' ? 'ok' : sf.level === 'down' ? 'down' : 'warn',
    });
  }
  if (h.apt) {
    rows.push({
      k: T('health.apt'),
      v: h.apt.total ? T('health.apt_detail', { total: h.apt.total, security: h.apt.security }) : T('common.up_to_date'),
      level: h.apt.security ? 'warn' : 'ok',
    });
  }
  if (h.images) {
    rows.push({ k: T('health.images'), v: h.images.outdated ? T('health.images_outdated', { count: h.images.outdated }) : T('common.up_to_date'), level: h.images.outdated ? 'warn' : 'ok' });
  }
  const power = h.throttling;
  if (power && power.available) {
    rows.push({
      k: T('health.power'),
      v: data.system.undervoltage ? T('health.power_undervoltage') : power.healthy ? T('health.power_ok') : power.since_boot.join(' · '),
      level: data.system.undervoltage ? 'down' : power.healthy ? 'ok' : 'warn',
    });
  }
  if (h.journal) {
    rows.push({ k: T('health.journal_errors'), v: `${h.journal.counted}`, level: h.journal.counted ? '' : 'ok' });
  }
  renderKv('c-health', rows);
}

function renderNetwork(data) {
  const rows = [];
  const wan = data.wan;
  if (wan) {
    const ip = data.public_ip ? ' · ' + T('net.ip', { ip: data.public_ip.ip }) : '';
    rows.push({
      k: T('net.internet'),
      v: wan.online === null ? '—' : wan.online ? T('net.online_latency', { latency: wan.latency_ms }) + ip : T('net.offline'),
      level: wan.online ? 'ok' : wan.online === false ? 'down' : '',
    });
    rows.push({
      k: T('net.outages_24h'),
      v: wan.outages_24h ? `${wan.outages_24h} · ` + T('net.last_outage', { count: wan.last_outage_minutes }) : T('common.none'),
      level: wan.outages_24h ? 'warn' : 'ok',
    });
  }
  const starlink = data.starlink;
  if (starlink) {
    const mbps = (bps) => Math.round(bps / 1e6);
    rows.push({
      k: 'Starlink',
      v: starlink.online
        ? T('net.online_latency', { latency: starlink.latency_ms }) + ` · ↓ ${mbps(starlink.downlink_bps)} · ↑ ${mbps(starlink.uplink_bps)} Mb/s`
        : T('starlink.offline'),
      level: starlink.online ? 'ok' : 'down',
    });
  }
  const net = data.network || {};
  const peers = net.tailscale_peers || [];
  const online = peers.filter((p) => p.online);
  rows.push({
    k: T('net.tailscale'),
    v: online.length ? online.map((p) => p.hostname).join(' · ') : T('net.peers_online', { count: 0 }),
    level: online.length ? 'ok' : '',
  });
  const lan = (net.lan_neighbors || []).length;
  const fresh = (net.new_devices || {}).count || 0;
  rows.push({ k: T('net.lan_devices'), v: `${lan}${fresh ? ' · ' + Tn('net.new', fresh) : ''}`, level: fresh ? 'warn' : '' });
  renderKv('c-network', rows);

  // La ligne « Appareils LAN » mène à l'inventaire — recréée à chaque cycle par renderKv.
  const last = document.querySelector('#c-network .ckv:last-child .v');
  if (last) {
    const link = el('a', 'ctrl-link', ' ' + T('net.inventory_link'));
    link.href = '/reseau';
    last.appendChild(link);
  }
  // Idem pour la ligne Starlink → sa page détaillée.
  if (data.starlink) {
    const rows = document.querySelectorAll('#c-network .ckv .k');
    for (const key of rows) {
      if (key.textContent !== 'Starlink') continue;
      const link = el('a', 'ctrl-link', ' ' + T('starlink.detail_link'));
      link.href = '/starlink';
      key.parentElement.querySelector('.v').appendChild(link);
    }
  }
}

function renderServices(groups) {
  const container = document.getElementById('c-services');
  if (!container) return;
  const parts = [];
  for (const group of groups) {
    parts.push(el('h3', 'ctrl-grp', group.name));
    const table = el('table', 'ctrl-svc');
    for (const service of group.services) {
      const row = el('tr', `ctrl-row state-${service.state}`);

      const name = el('td', 'name');
      name.appendChild(el('span', `cdot cdot-${service.state}`));
      if (service.url) {
        const link = el('a', '');
        const licon = el('span', '', service.icon);
        licon.setAttribute('aria-hidden', 'true');
        link.append(licon, ` ${service.name}`);
        link.href = service.url;
        name.appendChild(link);
      } else {
        const nicon = el('span', '', service.icon);
        nicon.setAttribute('aria-hidden', 'true');
        name.append(nicon, ` ${service.name}`);
      }
      row.appendChild(name);

      row.appendChild(el('td', 'desc', service.description || ''));

      const cpu = el('td', 'cpu');
      if (service.cpu_percent !== null && service.cpu_percent !== undefined) {
        const bar = el('div', 'bar');
        const fill = el('i');
        fill.style.width = `${Math.min(service.cpu_percent, 100)}%`;
        bar.appendChild(fill);
        cpu.appendChild(bar);
        cpu.appendChild(el('span', 'cpu-num', `${service.cpu_percent} %`));
      }
      row.appendChild(cpu);

      const avail = service.availability;
      row.appendChild(el('td', 'avail', avail ? `${avail.uptime_pct} %` : ''));
      row.appendChild(el('td', 'up', service.uptime || ''));

      table.appendChild(row);
    }
    parts.push(table);
  }
  container.replaceChildren(...parts);
}

function render(data) {
  setText('c-hostname', data.system.hostname);
  setText('c-sub', T('hero.subtitle', { uptime: data.system.uptime.human }));
  renderPills(data);
  renderMachine(data.system, data.nvme);
  renderHealth(data);
  renderNetwork(data);
  renderServices(data.groups);
}

function renderHistory(samples) {
  if (samples.length < 2) return;
  drawSpark(
    document.getElementById('c-spark'),
    samples.map((s) => ({ ts: s.ts, value: s.cpu_pct ?? 0 })),
    { min: 0, max: 100 },
    34
  );
}

startPolling(render, renderHistory);
