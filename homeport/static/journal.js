// Vue B — Le journal de la maison : verdict, récit, uniquement ce qui mérite attention.
// Coquille HTML statique + rendu client depuis /api/status (pattern /reseau).

const { setText, verdict, backupAge, startPolling } = window.RaspViews;

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};

function renderVerdict(data) {
  const v = verdict(data);
  const node = document.getElementById('j-verdict');
  node.textContent = v.text;
  node.className = `edit-verdict verdict-${v.level}`;
}

// La phrase narrative : composée des faits saillants disponibles, jamais de trou visible —
// un segment sans donnée est simplement omis.
function renderStory(data) {
  const parts = [];
  const s = data.summary;
  parts.push(s.up === s.total
    ? T('journal.story_services_all', { total: s.total })
    : T('journal.story_services_partial', { up: s.up, total: s.total }));

  const wan = data.wan;
  if (wan && wan.online) {
    parts.push(wan.outages_24h
      ? T('journal.story_wan_outages', { latency: wan.latency_ms, count: wan.outages_24h })
      : T('journal.story_wan_ok', { latency: wan.latency_ms }));
  } else if (wan && wan.online === false) {
    parts.push(T('journal.story_wan_down'));
  }

  const age = backupAge(data.health);
  if (age !== null) parts.push(T('journal.story_backup', { count: age }));

  const nvme = data.nvme;
  if (nvme && nvme.percent_used !== null && nvme.percent_used !== undefined) {
    parts.push(nvme.power_on_hours
      ? T('journal.story_ssd_hours', { pct: nvme.percent_used, hours: nvme.power_on_hours })
      : T('journal.story_ssd', { pct: nvme.percent_used }));
  }

  setText('j-story', parts.length ? `${parts.join(', ')}.` : '');
}

function renderAttention(data) {
  const container = document.getElementById('j-attention');
  const cards = [];

  for (const alert of ((data.health || {}).alerts || [])) {
    cards.push({ level: alert.level, title: alert.text });
  }

  for (const sf of data.status_files || []) {
    if (sf.level === 'up') continue;
    cards.push({ level: sf.level === 'down' ? 'down' : 'warn', title: sf.name, note: sf.message || '' });
  }
  container.hidden = cards.length === 0;
  container.replaceChildren(...cards.map((card) => {
    const box = el('div', `eatt eatt-${card.level}`);
    box.appendChild(el('h3', '', card.title));
    if (card.note) box.appendChild(el('p', '', card.note));
    return box;
  }));
}

function renderFacts(system) {
  setText('f-cpu', `${system.load.percent} %`);
  setText('f-cpu-note', T('journal.fact_cpu', { load: system.load.avg1, cores: system.load.cores }));
  setText('f-temp', system.temperature_c === null ? '—' : `${system.temperature_c} °C`);
  setText('f-temp-note', system.storage_temperature_c === null ? T('journal.fact_temp_cpu') : T('journal.fact_temp_both', { temp: system.storage_temperature_c }));
  setText('f-mem', `${system.memory.percent} %`);
  setText('f-mem-note', T('journal.fact_mem', { used: (system.memory.used_mb / 1024).toFixed(1), total: (system.memory.total_mb / 1024).toFixed(0) }));
  const root = (system.disks || []).find((d) => d.mount === '/');
  const ssd = (system.disks || []).find((d) => d.mount !== '/');
  if (root) {
    setText('f-disk', `${root.percent} %`);
    setText('f-disk-note', ssd ? T('journal.fact_disk_ssd', { pct: ssd.percent }) : T('journal.fact_disk'));
  }
}

function renderQuiet(data) {
  const rows = [];
  const wan = data.wan;
  if (wan) {
    const ip = data.public_ip ? ` · IP …${data.public_ip.ip.split('.').slice(2).join('.')}` : '';
    rows.push({
      k: T('net.internet'),
      v: wan.online === null ? '—' : wan.online
        ? `${wan.latency_ms} ms · ` + Tn('journal.coupure', wan.outages_24h || 0) + ip : T('net.offline'),
      level: wan.online ? 'ok' : '',
    });
  }
  const starlink = data.starlink;
  if (starlink) {
    rows.push({
      k: 'Starlink',
      v: starlink.online
        ? `${starlink.latency_ms} ms · ↓ ${Math.round(starlink.downlink_bps / 1e6)} Mb/s`
        : T('starlink.offline'),
      level: starlink.online ? 'ok' : '',
    });
  }
  const peers = ((data.network || {}).tailscale_peers || []);
  const online = peers.filter((p) => p.online).length;
  rows.push({ k: T('net.tailscale'), v: T('net.peers_online', { count: online }), level: online ? 'ok' : '' });

  const lan = ((data.network || {}).lan_neighbors || []).length;
  const fresh = ((data.network || {}).new_devices || {}).count || 0;
  rows.push({ k: T('net.lan_devices'), v: T('journal.lan_known', { count: lan, fresh }) });

  const power = (data.health || {}).throttling;
  if (power && power.available) {
    rows.push({
      k: T('health.power'),
      v: data.system.undervoltage ? T('health.power_undervoltage') : power.healthy ? T('journal.power_ok_boot') : power.since_boot.join(' · '),
      level: data.system.undervoltage ? '' : power.healthy ? 'ok' : '',
    });
  }
  const journal = (data.health || {}).journal;
  if (journal) {
    const top = (journal.by_source || [])[0];
    rows.push({
      k: T('health.journal_errors'),
      v: journal.counted ? `${journal.counted}${top ? ` · ${top.source.replace('.service', '')}` : ''}` : T('common.none'),
      level: journal.counted ? '' : 'ok',
    });
  }
  const images = (data.health || {}).images;
  if (images) rows.push({ k: T('health.images'), v: images.outdated ? T('health.images_outdated', { count: images.outdated }) : T('common.up_to_date'), level: images.outdated ? '' : 'ok' });

  const container = document.getElementById('j-quiet');
  container.replaceChildren(...rows.map(({ k, v, level }) => {
    const row = el('div', 'erow');
    row.appendChild(el('span', 'k', k));
    row.appendChild(el('span', `v${level ? ` ${level}` : ''}`, v));
    return row;
  }));
}

function renderServices(data) {
  // Disponibilité d'ensemble dans le titre de section, quand tout le monde la connaît.
  const pcts = [];
  for (const group of data.groups) for (const s of group.services) {
    if (s.availability) pcts.push(s.availability.uptime_pct);
  }
  const worst = pcts.length ? Math.min(...pcts) : null;
  setText('j-svc-title', worst === null ? T('journal.services')
    : worst >= 100 ? T('journal.services_avail_100')
    : T('journal.services_avail_worst', { pct: worst }));

  const container = document.getElementById('j-services');
  const parts = [];
  for (const group of data.groups) {
    for (const service of group.services) {
      const line = el('div', 'esvc');
      line.appendChild(el('span', `edot edot-${service.state}`));

      if (service.url) {
        const link = el('a', 'n', `${service.icon} ${service.name}`);
        link.href = service.url;
        line.appendChild(link);
      } else {
        line.appendChild(el('span', 'n', `${service.icon} ${service.name}`));
      }

      const bits = [];
      if (service.description) bits.push(service.description);
      if (service.cpu_percent !== null && service.cpu_percent !== undefined) bits.push(`CPU ${service.cpu_percent} %`);
      if (service.availability && service.availability.uptime_pct < 100) bits.push(T('svc.availability_7d', { pct: service.availability.uptime_pct }));
      line.appendChild(el('span', 'd', bits.join(' · ')));

      line.appendChild(el('span', 'a', service.uptime ? T('svc.started_ago', { uptime: service.uptime }) : ''));
      parts.push(line);
    }
  }
  container.replaceChildren(...parts);
}

function render(data) {
  setText('j-hostname', data.system.hostname);
  setText('j-date', new Date().toLocaleDateString(document.documentElement.lang, {
    weekday: 'long', day: 'numeric', month: 'long',
  }) + ', ' + new Date().toLocaleTimeString(document.documentElement.lang, { hour: '2-digit', minute: '2-digit' }));
  renderVerdict(data);
  renderStory(data);
  renderAttention(data);
  renderFacts(data.system);
  renderQuiet(data);
  renderServices(data);
}

startPolling(render);
