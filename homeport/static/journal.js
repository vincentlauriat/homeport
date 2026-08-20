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
    ? `Les ${s.total} services tournent`
    : `${s.up} service(s) sur ${s.total} tournent`);

  const wan = data.wan;
  if (wan && wan.online) {
    parts.push(`Internet répond en ${wan.latency_ms} ms${wan.outages_24h ? ` (${wan.outages_24h} coupure(s) sur 24 h)` : ' sans coupure depuis hier'}`);
  } else if (wan && wan.online === false) {
    parts.push('Internet est coupé');
  }

  const age = backupAge(data.health);
  if (age !== null) parts.push(`la maison a été sauvegardée il y a ${age} h`);

  const nvme = data.nvme;
  if (nvme && nvme.percent_used !== null && nvme.percent_used !== undefined) {
    parts.push(`le SSD est à ${nvme.percent_used} % d'usure${nvme.power_on_hours ? ` après ${nvme.power_on_hours} heures` : ''}`);
  }

  setText('j-story', parts.length ? `${parts.join(', ')}.` : '');
}

function renderAttention(data) {
  const container = document.getElementById('j-attention');
  const cards = [];

  for (const alert of ((data.health || {}).alerts || [])) {
    cards.push({ level: alert.level, title: alert.text });
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
  setText('f-cpu-note', `CPU · ${system.load.avg1} / ${system.load.cores} cœurs`);
  setText('f-temp', system.temperature_c === null ? '—' : `${system.temperature_c} °C`);
  setText('f-temp-note', system.storage_temperature_c === null ? 'CPU' : `CPU · SSD ${system.storage_temperature_c} °C`);
  setText('f-mem', `${system.memory.percent} %`);
  setText('f-mem-note', `mémoire · ${(system.memory.used_mb / 1024).toFixed(1)} / ${(system.memory.total_mb / 1024).toFixed(0)} Gio`);
  const root = (system.disks || []).find((d) => d.mount === '/');
  const ssd = (system.disks || []).find((d) => d.mount !== '/');
  if (root) {
    setText('f-disk', `${root.percent} %`);
    setText('f-disk-note', ssd ? `disque / · SSD ${ssd.percent} %` : 'disque /');
  }
}

function renderQuiet(data) {
  const rows = [];
  const wan = data.wan;
  if (wan) {
    const ip = data.public_ip ? ` · IP …${data.public_ip.ip.split('.').slice(2).join('.')}` : '';
    rows.push({
      k: 'Internet',
      v: wan.online === null ? '—' : wan.online
        ? `${wan.latency_ms} ms · ${wan.outages_24h || 0} coupure(s)${ip}` : 'coupé',
      level: wan.online ? 'ok' : '',
    });
  }
  const peers = ((data.network || {}).tailscale_peers || []);
  const online = peers.filter((p) => p.online).length;
  rows.push({ k: 'Tailscale', v: `${online} pair(s) en ligne`, level: online ? 'ok' : '' });

  const lan = ((data.network || {}).lan_neighbors || []).length;
  const fresh = ((data.network || {}).new_devices || {}).count || 0;
  rows.push({ k: 'Appareils LAN', v: `${lan} connus · ${fresh} nouveau(x)` });

  const power = (data.health || {}).throttling;
  if (power && power.available) {
    rows.push({
      k: 'Alimentation',
      v: data.system.undervoltage ? 'sous-tension' : power.healthy ? 'saine depuis le boot' : power.since_boot.join(' · '),
      level: data.system.undervoltage ? '' : power.healthy ? 'ok' : '',
    });
  }
  const journal = (data.health || {}).journal;
  if (journal) {
    const top = (journal.by_source || [])[0];
    rows.push({
      k: 'Erreurs journal 24 h',
      v: journal.counted ? `${journal.counted}${top ? ` · ${top.source.replace('.service', '')}` : ''}` : 'aucune',
      level: journal.counted ? '' : 'ok',
    });
  }
  const images = (data.health || {}).images;
  if (images) rows.push({ k: 'Images Docker', v: images.outdated ? `${images.outdated} obsolète(s)` : 'à jour', level: images.outdated ? '' : 'ok' });

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
  setText('j-svc-title', worst === null ? 'Les services'
    : worst >= 100 ? 'Les services — 100 % de disponibilité sur 7 jours'
    : `Les services — au pire ${worst} % de disponibilité sur 7 jours`);

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
      if (service.availability && service.availability.uptime_pct < 100) bits.push(`${service.availability.uptime_pct} % sur 7 j`);
      line.appendChild(el('span', 'd', bits.join(' · ')));

      line.appendChild(el('span', 'a', service.uptime ? `démarré il y a ${service.uptime}` : ''));
      parts.push(line);
    }
  }
  container.replaceChildren(...parts);
}

function render(data) {
  setText('j-hostname', data.system.hostname);
  setText('j-date', new Date().toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long',
  }) + ', ' + new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }));
  renderVerdict(data);
  renderStory(data);
  renderAttention(data);
  renderFacts(data.system);
  renderQuiet(data);
  renderServices(data);
}

startPolling(render);
