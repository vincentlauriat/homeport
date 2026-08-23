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
  // setText ne réécrit que si la valeur change : la zone role="status" ne se réannonce donc
  // pas à chaque sondage.
  setText('j-verdict', v.text);
  document.getElementById('j-verdict-dot').className = `verdict-dot edot-${v.level}`;
}

// La phrase narrative : composée des faits saillants disponibles. Un fait qu'on ne sait pas
// lire se dit ; seul un fait qu'on n'a pas à dire s'omet — taire un WAN illisible laisserait
// croire qu'Internet va bien.
function renderStory(data) {
  const parts = [];
  const s = data.summary;
  parts.push(s.up === s.total
    ? T('journal.story_services_all', { total: s.total })
    : Tn('journal.story_services_partial', s.up, { up: s.up, total: s.total }));

  const wan = data.wan;
  if (wan && wan.online) {
    parts.push(wan.outages_24h
      ? T('journal.story_wan_outages', {
        latency: wan.latency_ms,
        outages: Tn('journal.coupure', wan.outages_24h),
      })
      : T('journal.story_wan_ok', { latency: wan.latency_ms }));
  } else if (wan && wan.online === false) {
    parts.push(T('journal.story_wan_down'));
  } else if (wan) {
    parts.push(T('journal.story_wan_unknown'));
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

// Ce qui mérite attention. Le service en panne y manquait : le verdict l'annonçait en une
// phrase, la liste des services le montrait quinze écrans plus bas, et le seul bloc dont le
// travail est de nommer les problèmes ne le nommait pas.
function renderAttention(data) {
  const container = document.getElementById('j-attention');
  const section = document.getElementById('j-attention-section');
  const cards = [];

  for (const group of data.groups || []) {
    for (const service of group.services) {
      if (service.state === 'up') continue;
      cards.push({
        level: service.state === 'down' ? 'down' : 'warn',
        title: `${T(`state.${service.state}`)} · ${service.name}`,
        note: service.description || '',
      });
    }
  }

  for (const alert of ((data.health || {}).alerts || [])) {
    cards.push({ level: alert.level, title: alert.text });
  }

  for (const sf of data.status_files || []) {
    if (sf.level === 'up') continue;
    cards.push({ level: sf.level === 'down' ? 'down' : 'warn', title: sf.name, note: sf.message || '' });
  }
  // Les pannes avant les dégradations : sur un bloc en grille, l'ordre est la seule
  // hiérarchie disponible.
  cards.sort((a, b) => (a.level === 'down' ? 0 : 1) - (b.level === 'down' ? 0 : 1));
  section.hidden = cards.length === 0;
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

// Le niveau se décide ligne par ligne, jamais par une règle mécanique : un appareil inconnu
// sur le réseau local et une Livebox injoignable ne pèsent pas le même poids, et peindre
// « en panne » sur ce qui n'est que notable est un faux signal — le contraire du service
// qu'on rend en teintant.
function renderQuiet(data) {
  const rows = [];
  const wan = data.wan;
  if (wan) {
    const ip = data.public_ip ? ` · IP …${data.public_ip.ip.split('.').slice(2).join('.')}` : '';
    rows.push({
      k: T('net.internet'),
      v: wan.online === null ? T('state.unknown') : wan.online
        ? `${wan.latency_ms} ms · ` + Tn('journal.coupure', wan.outages_24h || 0) + ip : T('net.offline'),
      level: wan.online === null ? 'warn' : wan.online ? 'ok' : 'down',
    });
  }
  const starlink = data.starlink;
  if (starlink) {
    rows.push({
      k: 'Starlink',
      v: starlink.online
        ? `${starlink.latency_ms} ms · ↓ ${Math.round(starlink.downlink_bps / 1e6)} Mb/s`
        : T('starlink.offline'),
      level: starlink.online ? 'ok' : 'down',
    });
  }
  const livebox = data.livebox;
  if (livebox) {
    rows.push({
      k: 'Livebox',
      v: livebox.online
        ? `${livebox.latency_ms} ms · ${(livebox.link_type || '?').toUpperCase()}`
        : T(livebox.reachable ? 'livebox.wan_down' : 'livebox.offline'),
      level: livebox.online ? 'ok' : 'down',
    });
  }
  const peers = ((data.network || {}).tailscale_peers || []);
  const online = peers.filter((p) => p.online).length;
  // Aucun pair joignable est notable, pas une panne : la maison tourne sans Tailscale.
  rows.push({ k: T('net.tailscale'), v: T('net.peers_online', { count: online }), level: online ? 'ok' : 'warn' });

  const lan = ((data.network || {}).lan_neighbors || []).length;
  const fresh = ((data.network || {}).new_devices || {}).count || 0;
  // Un décompte d'appareils connus n'est ni bon ni mauvais ; un nouvel arrivant mérite l'œil.
  rows.push({ k: T('net.lan_devices'), v: T('journal.lan_known', { count: lan, fresh }), level: fresh ? 'warn' : '' });

  const power = (data.health || {}).throttling;
  if (power && power.available) {
    rows.push({
      k: T('health.power'),
      v: data.system.undervoltage ? T('health.power_undervoltage') : power.healthy ? T('journal.power_ok_boot') : power.since_boot.join(' · '),
      // Sous-tension maintenant : panne. Événements depuis le boot : passé, donc notable.
      level: data.system.undervoltage ? 'down' : power.healthy ? 'ok' : 'warn',
    });
  }
  const journal = (data.health || {}).journal;
  if (journal) {
    const top = (journal.by_source || [])[0];
    rows.push({
      k: T('health.journal_errors'),
      v: journal.counted ? `${journal.counted}${top ? ` · ${top.source.replace('.service', '')}` : ''}` : T('common.none'),
      level: journal.counted ? 'warn' : 'ok',
    });
  }
  const images = (data.health || {}).images;
  // `available: false` — le proxy Docker a refusé la lecture des images. Zéro image périmée
  // sur zéro image lue n'est pas « à jour » : c'est « on ne sait pas ». Le test doit rester
  // sur `=== false`, le mode démo ne posant pas la clé.
  if (images) {
    rows.push({
      k: T('health.images'),
      v: images.available === false ? T('state.unknown')
        : images.outdated ? T('health.images_outdated', { count: images.outdated })
        : T('common.up_to_date'),
      level: images.available === false ? '' : images.outdated ? 'warn' : 'ok',
    });
  }

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
  let trouble = 0;
  for (const group of data.groups) {
    for (const service of group.services) {
      const line = el('div', 'esvc');
      // Le point ne dit son état qu'en couleur. Quand cet état n'est pas `up`, le mot le dit
      // en clair pour tout le monde ; quand il l'est, seul le lecteur d'écran l'entend —
      // quinze « Actif » à l'écran noieraient le seul qui compte.
      const dot = el('span', `edot edot-${service.state}`);
      dot.setAttribute('aria-hidden', 'true');
      const label = T(`state.${service.state}`);
      if (service.state === 'up') {
        line.append(dot, el('span', 'sr-only', `${label} · `));
      } else {
        trouble += 1;
        line.append(dot, el('span', `st st-${service.state}`, label));
      }

      if (service.url) {
        const link = el('a', 'n');
        const licon = el('span', '', service.icon);
        licon.setAttribute('aria-hidden', 'true');
        link.append(licon, ` ${service.name}`);
        link.href = service.url;
        line.appendChild(link);
      } else {
        const nspan = el('span', 'n');
        const nicon = el('span', '', service.icon);
        nicon.setAttribute('aria-hidden', 'true');
        nspan.append(nicon, ` ${service.name}`);
        line.appendChild(nspan);
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

  setText('j-services-summary', T('journal.services_show', { count: parts.length }));
  // On ouvre dès qu'un service sort de `up` — un problème ne se cache jamais derrière un
  // chevron. On ne referme qu'au premier rendu : au-delà, le pli appartient au lecteur, et
  // le lui reprendre toutes les cinq secondes serait insupportable.
  const wrap = document.getElementById('j-services-wrap');
  if (trouble) wrap.open = true;
  else if (!wrap.dataset.settled) wrap.open = false;
  wrap.dataset.settled = '1';
}

// Le lien avec le serveur, dit sous le verdict. `stale` garde les dernières données à l'écran
// en les datant ; `never` n'en a aucune à garder.
function renderLink(state, lastOk) {
  const node = document.getElementById('j-link');
  if (state === 'stale') {
    node.hidden = false;
    node.textContent = T('journal.link_stale', { time: lastOk.toLocaleTimeString() });
  } else if (state === 'never') {
    node.hidden = false;
    node.textContent = T('journal.link_never');
  } else {
    node.hidden = true;
  }
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

startPolling(render, null, renderLink);
