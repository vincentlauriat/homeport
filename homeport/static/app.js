// Rafraîchissement en fond du tableau de bord.
// Le HTML initial est rendu côté serveur : ce script ne fait que remettre à jour les valeurs,
// il ne reconstruit jamais la page. Si le Pi devient injoignable, la dernière vue reste
// affichée et le pied de page indique depuis quand.

const REFRESH_MS = 5000;

const setText = (id, value) => {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
};

const setBar = (metricEl, percent) => {
  const bar = metricEl?.querySelector('.bar i');
  if (bar) bar.style.width = `${Math.min(percent, 100)}%`;
};

function applySystem(system) {
  const metrics = document.querySelectorAll('#metrics .metric');
  setText('m-cpu', `${system.load.percent} %`);
  setText('m-mem', `${system.memory.percent} %`);
  setText('m-temp', system.temperature_c === null ? '—' : `${system.temperature_c} °C`);
  setBar(metrics[0], system.load.percent);
  setBar(metrics[1], system.memory.percent);
  setBar(metrics[2], ((system.temperature_c ?? 0) / 85) * 100);

  const nvme = document.getElementById('m-nvme');
  if (nvme && system.storage_temperature_c !== null) {
    nvme.textContent = `${system.storage_temperature_c} °C`;
    const card = nvme.closest('.metric');
    setBar(card, (system.storage_temperature_c / 70) * 100);
    const note = card?.querySelector('.metric-note');
    if (note && system.fan_rpm) note.textContent = T('metric.fan', { rpm: system.fan_rpm });
  }

  const notes = document.querySelectorAll('#metrics .metric-note');
  if (notes[0]) notes[0].textContent = `${system.load.avg1} / ${system.load.cores} ${T('metric.cores')}`;
  if (notes[1]) notes[1].textContent = `${system.memory.used_mb} / ${system.memory.total_mb} ${T('unit.mib')}`;
}

function applyServices(groups) {
  for (const group of groups) {
    for (const service of group.services) {
      const card = document.querySelector(`.card[data-id="${service.id}"]`);
      if (!card) continue;
      // L'attribut `open` n'est jamais touché ici : une carte que l'utilisateur a repliée ou
      // dépliée à la main le reste jusqu'au prochain chargement complet de la page — le
      // rafraîchissement en fond ne doit pas lui reprendre la main.
      card.className = `card state-${service.state}`;

      const chip = card.querySelector('.chip');
      if (chip) {
        chip.className = `chip chip-${service.state}`;
        chip.textContent = service.state_label;
      }

      const rows = card.querySelectorAll('.mini-table tr');
      service.sources.forEach((src, i) => {
        const value = rows[i]?.querySelector('.mt-value');
        if (!value) return;
        value.className = `mt-value ${src.ok ? 'ok' : 'fail'}`;
        value.textContent = src.value;
      });

      const avail = card.querySelector('.avail-line');
      if (avail && service.availability) {
        avail.hidden = false;
        const a = service.availability;
        avail.textContent = T('svc.availability_7d', { pct: a.uptime_pct }) +
          (a.incidents ? ' · ' + T('svc.incidents', { count: a.incidents, minutes: a.longest_minutes }) : '');
      }

      const uptime = card.querySelector('.uptime');
      if (uptime && service.uptime) uptime.textContent = service.uptime;

      if (service.cpu_percent !== null && service.cpu_percent !== undefined) {
        const cpuVal = card.querySelector('.cpu-val');
        if (cpuVal) cpuVal.textContent = `${service.cpu_percent} %`;
        const cpuBar = card.querySelector('.cpu-line .bar i');
        if (cpuBar) cpuBar.style.width = `${Math.min(service.cpu_percent, 100)}%`;
      }
    }
  }
}

function applySummary(summary) {
  setText('count-up', summary.up);
  setText('count-warn', summary.warn);
  setText('count-down', summary.down);
}

function applyHealth(health) {
  if (!health) return;

  // Bandeau d'alertes
  const alerts = document.getElementById('alerts');
  if (alerts) {
    alerts.hidden = health.alerts.length === 0;
    alerts.innerHTML = health.alerts
      .map((a) => `<p class="alert alert-${a.level}"></p>`)
      .join('');
    // Le texte est inséré séparément : jamais d'HTML issu d'une source système.
    alerts.querySelectorAll('.alert').forEach((node, i) => {
      node.textContent = health.alerts[i].text;
    });
  }

  // Sauvegardes
  for (const backup of health.backups || []) {
    const card = document.querySelector(`[data-health="backup-${backup.id}"]`);
    if (!card) continue;
    const state = backup.state === 'never' ? 'down' : backup.state === 'warn' ? 'warn' : 'up';
    card.className = `health-card state-${state}`;
    card.querySelector('.health-value').textContent =
      backup.state === 'never' ? T('common.never') : backup.detail;
    card.querySelector('.health-note').textContent =
      backup.state === 'never'
        ? backup.path
        : `${backup.file.replace('homeserver-config-', '').replace('.tar.gz', '')} · ${backup.size_mb} Mio`;
  }

  // Paquets APT
  const apt = health.apt;
  if (apt) {
    setText('h-apt', T('health.apt_to_update', { count: apt.total }));
    const age = apt.lists_age_days === null ? '' : ' · ' + T('health.apt_lists_age', { count: apt.lists_age_days });
    setText('h-apt-note', T('health.apt_security', { count: apt.security }) + age);
    const card = document.querySelector('[data-health="apt"]');
    if (card) card.className = `health-card${apt.security ? ' state-warn' : apt.total ? '' : ' state-up'}`;
  }

  // Images Docker
  const images = health.images;
  if (images) {
    setText('h-img', T('health.images_outdated', { count: images.outdated }));
    setText('h-img-note', T('health.images_checked', { count: images.checked }));
    const card = document.querySelector('[data-health="images"]');
    if (card) card.className = `health-card${images.outdated ? ' state-warn' : ''}`;
  }

  // Alimentation et throttling
  const power = health.throttling;
  const powerCard = document.querySelector('[data-health="power"]');
  if (powerCard && power) {
    const undervoltage = health._undervoltage;
    const state = undervoltage ? 'down' : power.since_boot.length ? 'warn' : power.healthy ? 'up' : '';
    powerCard.className = `health-card${state ? ` state-${state}` : ''}`;
    setText('h-power', undervoltage ? T('health.power_undervoltage') : power.healthy ? T('health.power_ok') : T('health.power_incident'));
    setText(
      'h-power-note',
      power.since_boot.length ? power.since_boot.join(' · ') : T('health.power_no_incident')
    );
  }

  // Erreurs du journal
  const journal = health.journal;
  if (journal) {
    setText('h-journal', journal.counted);
    const sources = journal.by_source
      .map((s) => `${s.source.replace('.service', '')} ${s.count}`)
      .join(' · ');
    const muted = journal.muted ? ' · ' + T('health.journal_muted', { count: journal.muted }) : '';
    setText('h-journal-note', (sources || T('common.none')) + muted);
  }
}

function applyNvme(nvme) {
  // La carte n'est présente que si un premier relevé existait au chargement — le refresh met
  // à jour ses valeurs mais ne recrée pas la carte de zéro (voir index.html).
  if (!nvme || nvme.percent_used === null || nvme.percent_used === undefined) return;
  setText('m-wear', `${nvme.percent_used} %`);
  const card = document.getElementById('metric-wear');
  setBar(card, nvme.percent_used);
  const parts = [];
  if (nvme.written_gb !== null && nvme.written_gb !== undefined) parts.push(T('metric.written', { count: nvme.written_gb }));
  if (nvme.power_on_hours !== null && nvme.power_on_hours !== undefined) parts.push(`${nvme.power_on_hours} h`);
  if (parts.length) setText('m-wear-note', parts.join(' · '));
}

function applyWan(wan) {
  const card = document.querySelector('[data-network="wan"]');
  if (!card || !wan) return;
  card.hidden = false;
  card.classList.remove('state-up', 'state-down');
  if (wan.online === true) card.classList.add('state-up');
  if (wan.online === false) card.classList.add('state-down');
  setText('wan-value', wan.online === null ? '—'
    : wan.online ? T('net.online_latency', { latency: wan.latency_ms }) : T('wan.offline_f'));
  const ipSuffix = window.__publicIp ? ' · ' + T('net.ip', { ip: window.__publicIp }) : '';
  setText('wan-note', (wan.outages_24h
    ? Tn('net.outages_detail', wan.outages_24h) + ' · ' + T('index.outage_last', { count: wan.last_outage_minutes })
    : T('net.no_outage')) + ipSuffix);
}

function applyNetwork(network) {
  if (!network) return;

  const tailscaleEl = document.getElementById('net-tailscale');
  const peers = network.tailscale_peers || [];
  if (tailscaleEl) {
    tailscaleEl.innerHTML = peers.length
      ? peers.map((p) => `<span class="peer peer-${p.online ? 'online' : 'offline'}"></span>`).join('')
      : `<span class="health-note">${T('net.no_peer')}</span>`;
    tailscaleEl.querySelectorAll('.peer').forEach((node, i) => { node.textContent = peers[i].hostname; });
  }

  const neighbors = network.lan_neighbors || [];
  setText('net-lan-count', neighbors.length);
  const newBadge = document.getElementById('net-new-badge');
  if (newBadge) {
    const count = (network.new_devices || {}).count || 0;
    newBadge.hidden = count === 0;
    newBadge.textContent = count ? Tn('net.new', count) : '';
  }
  const list = document.getElementById('net-lan-list');
  if (list) {
    list.innerHTML = '';
    for (const n of neighbors) {
      const li = document.createElement('li');
      li.append(`${n.ip} `);
      const mac = document.createElement('span');
      mac.className = 'mac';
      mac.textContent = n.mac;
      li.appendChild(mac);
      list.appendChild(li);
    }
  }
}

// Trace une courbe simple dans un <svg> : pas de librairie de graphes, cohérent avec
// l'absence de dépendance front du reste du projet.
// `points` : [{ts, value}, ...]. L'abscisse suit le temps écoulé, pas l'index — un trou dans
// les données (redémarrage) ou une install fraîche avec peu de points ne doit pas étirer les
// échantillons sur toute la largeur comme s'ils couvraient bien 24 h.
function drawSparkline(svg, points, { min, max }) {
  if (!svg || points.length < 2) return;
  const w = 300, h = 60, pad = 4;
  const range = Math.max(max - min, 1e-6);
  const t0 = points[0].ts, span = Math.max(points[points.length - 1].ts - t0, 1);
  const path = points.map((p, i) => {
    const x = pad + ((p.ts - t0) / span) * (w - 2 * pad);
    const y = h - pad - ((p.value - min) / range) * (h - 2 * pad);
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  });
  svg.innerHTML =
    `<path d="${path.join(' ')}" fill="none" stroke="currentColor" stroke-width="2" ` +
    `stroke-linecap="round" stroke-linejoin="round" />`;
}

const HISTORY_REFRESH_MS = 60000;

async function refreshHistory() {
  try {
    const response = await fetch('/api/history?hours=24', { cache: 'no-store' });
    if (!response.ok) return;
    const samples = await response.json();
    if (samples.length < 2) return;

    drawSparkline(
      document.getElementById('chart-cpu'),
      samples.map((s) => ({ ts: s.ts, value: s.cpu_pct ?? 0 })),
      { min: 0, max: 100 }
    );
    drawSparkline(
      document.getElementById('chart-mem'),
      samples.map((s) => ({ ts: s.ts, value: s.mem_pct ?? 0 })),
      { min: 0, max: 100 }
    );

    const tempPoints = samples
      .filter((s) => s.temp_c !== null && s.temp_c !== undefined)
      .map((s) => ({ ts: s.ts, value: s.temp_c }));
    if (tempPoints.length >= 2) {
      const temps = tempPoints.map((p) => p.value);
      drawSparkline(
        document.getElementById('chart-temp'),
        tempPoints,
        { min: Math.min(...temps) - 2, max: Math.max(...temps) + 2 }
      );
    }
  } catch (error) {
    // Silencieux : un historique en retard n'est pas une panne à signaler comme /api/status.
  }
}


function applyStatusFiles(files) {
  for (const sf of files || []) {
    const card = document.querySelector(`[data-health="sf-${sf.id}"]`);
    if (!card) continue;
    card.className = `health-card state-${sf.level === 'up' ? 'up' : sf.level === 'down' ? 'down' : 'warn'}`;
    card.querySelector('.health-value').textContent = sf.age_hours !== null && sf.age_hours !== undefined
      ? T('common.ago_hours', { count: sf.age_hours }) : T('common.pending');
    card.querySelector('.health-note').textContent = sf.message || '';
  }
}

function applyUpdateBadge(update) {
  let chip = document.getElementById('update-chip');
  if (!update || !update.available) { if (chip) chip.hidden = true; return; }
  if (!chip) {
    chip = document.createElement('a');
    chip.id = 'update-chip';
    chip.className = 'update-chip';
    chip.href = 'https://github.com/vincentlauriat/homeport/releases';
    chip.target = '_blank';
    chip.rel = 'noopener';
    const footer = document.querySelector('footer');
    if (footer) footer.appendChild(chip); else return;
  }
  chip.hidden = false;
  chip.textContent = T('update.available', { latest: update.latest });
}

async function refresh() {
  const stamp = document.getElementById('refreshed');
  try {
    const response = await fetch('/api/status', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    applySystem(data.system);
    applyServices(data.groups);
    applySummary(data.summary);
    applyHealth({ ...data.health, _undervoltage: data.system.undervoltage });
    applyNvme(data.nvme);
    window.__publicIp = data.public_ip ? data.public_ip.ip : null;
    applyWan(data.wan);
    applyNetwork(data.network);
    applyStatusFiles(data.status_files);
    applyUpdateBadge(data.update);
    const time = new Date().toLocaleTimeString('fr-FR');
    if (stamp) stamp.textContent = T('common.refreshed_at', { time });
  } catch (error) {
    if (stamp) stamp.textContent = T('common.offline_kept', { error: error.message });
  }
}

// Logs d'un conteneur, chargés à la première ouverture du panneau. Le texte est du contenu
// système : toujours inséré via textContent, jamais en HTML.
function wireContainerLogs() {
  for (const details of document.querySelectorAll('.logs-detail')) {
    details.addEventListener('toggle', async () => {
      if (!details.open || details.dataset.loaded) return;
      details.dataset.loaded = '1';
      const pre = details.querySelector('.logs-pre');
      const name = details.dataset.container;
      try {
        const response = await fetch(`/api/logs/${encodeURIComponent(name)}?tail=100`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        pre.textContent = data.logs && data.logs.trim() ? data.logs : '(∅)';
      } catch (error) {
        pre.textContent = T('svc.restart_failed', { error: error.message });
        delete details.dataset.loaded; // permettre un nouvel essai à la prochaine ouverture
      }
    });
  }
}
wireContainerLogs();

// On ne sollicite le Pi que si l'onglet est visible.
setInterval(() => { if (!document.hidden) refresh(); }, REFRESH_MS);
setInterval(() => { if (!document.hidden) refreshHistory(); }, HISTORY_REFRESH_MS);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) { refresh(); refreshHistory(); }
});
refreshHistory();

// Actions authentifiées par identité Tailscale (chantier E). Les boutons n'apparaissent que
// si /api/whoami confirme l'admin sur le tailnet — le LAN garde une page purement lecture.
// Confirmation en deux temps (pas de dialogue bloquant) : premier clic arme, second exécute.
async function wireActions() {
  try {
    const response = await fetch('/api/whoami', { cache: 'no-store' });
    if (!response.ok || !(await response.json()).can_act) return;
  } catch { return; }

  for (const row of document.querySelectorAll('.action-row')) row.hidden = false;

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('.btn-restart');
    if (!button || button.disabled) return;
    const result = button.parentElement.querySelector('.action-result');

    if (!button.dataset.armed) {
      button.dataset.armed = '1';
      button.classList.add('armed');
      button.textContent = T('svc.restart_confirm');
      setTimeout(() => {
        delete button.dataset.armed;
        button.classList.remove('armed');
        button.textContent = T('svc.restart');
      }, 4000);
      return;
    }

    delete button.dataset.armed;
    button.classList.remove('armed');
    button.disabled = true;
    button.textContent = T('svc.restarting');
    try {
      const response = await fetch(`/api/actions/restart/${encodeURIComponent(button.dataset.service)}`,
        { method: 'POST' });
      result.textContent = response.ok ? T('svc.restarted') : T('svc.restart_failed', { error: response.status });
      result.className = `action-result ${response.ok ? 'ok' : 'fail'}`;
    } catch (error) {
      result.textContent = T('svc.restart_failed', { error: error.message });
      result.className = 'action-result fail';
    }
    button.disabled = false;
    button.textContent = T('svc.restart');
    setTimeout(() => { result.textContent = ''; }, 8000);
  });
}
wireActions();
