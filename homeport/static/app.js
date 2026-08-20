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
    if (note && system.fan_rpm) note.textContent = `ventilateur ${system.fan_rpm} tr/min`;
  }

  const notes = document.querySelectorAll('#metrics .metric-note');
  if (notes[0]) notes[0].textContent = `${system.load.avg1} / ${system.load.cores} cœurs`;
  if (notes[1]) notes[1].textContent = `${system.memory.used_mb} / ${system.memory.total_mb} Mio`;
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
        avail.textContent = `${a.uptime_pct} % sur 7 j` +
          (a.incidents ? ` · ${a.incidents} incident(s) · max ${a.longest_minutes} min` : '');
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
      backup.state === 'never' ? 'jamais' : backup.detail;
    card.querySelector('.health-note').textContent =
      backup.state === 'never'
        ? backup.path
        : `${backup.file.replace('homeserver-config-', '').replace('.tar.gz', '')} · ${backup.size_mb} Mio`;
  }

  // Paquets APT
  const apt = health.apt;
  if (apt) {
    setText('h-apt', `${apt.total} à mettre à jour`);
    const age = apt.lists_age_days === null ? '' : ` · listes vieilles de ${apt.lists_age_days} j`;
    setText('h-apt-note', `${apt.security} de sécurité${age}`);
    const card = document.querySelector('[data-health="apt"]');
    if (card) card.className = `health-card${apt.security ? ' state-warn' : apt.total ? '' : ' state-up'}`;
  }

  // Images Docker
  const images = health.images;
  if (images) {
    setText('h-img', `${images.outdated} obsolète(s)`);
    setText('h-img-note', `${images.checked} image(s) comparée(s) au registre`);
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
    setText('h-power', undervoltage ? 'sous-tension' : power.healthy ? 'saine' : 'incident');
    setText(
      'h-power-note',
      power.since_boot.length ? power.since_boot.join(' · ') : 'aucun incident depuis le démarrage'
    );
  }

  // Erreurs du journal
  const journal = health.journal;
  if (journal) {
    setText('h-journal', journal.counted);
    const sources = journal.by_source
      .map((s) => `${s.source.replace('.service', '')} ${s.count}`)
      .join(' · ');
    const muted = journal.muted ? ` · ${journal.muted} bruit ignoré` : '';
    setText('h-journal-note', (sources || 'aucune') + muted);
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
  if (nvme.written_gb !== null && nvme.written_gb !== undefined) parts.push(`${nvme.written_gb} Go écrits`);
  if (nvme.power_on_hours !== null && nvme.power_on_hours !== undefined) parts.push(`${nvme.power_on_hours} h`);
  if (parts.length) setText('m-wear-note', parts.join(' · '));
}

function applyOffsite(offsite) {
  // Même contrat que la carte NVMe : le refresh met à jour les valeurs, le rendu initial
  // (présence de la carte, classe d'état) vient du serveur.
  const card = document.querySelector('[data-health="offsite"]');
  if (!card || !offsite) return;
  card.hidden = false;
  card.classList.remove('state-up', 'state-warn', 'state-down');
  if (offsite.status === 'ok' && offsite.age_hours !== null && offsite.age_hours < 48) {
    card.classList.add('state-up');
  } else if (offsite.status === 'error') {
    card.classList.add('state-down');
  } else {
    card.classList.add('state-warn');
  }
  setText('offsite-value', offsite.age_hours !== null && offsite.age_hours !== undefined
    ? `il y a ${offsite.age_hours} h` : 'en attente');
  const note = offsite.snapshots
    ? `${offsite.snapshots} snapshot(s) sur offsite${offsite.verified_ok ? ' · restauration vérifiée' : ''}`
    : (offsite.message || '');
  setText('offsite-note', note);
}

function applyWan(wan) {
  const card = document.querySelector('[data-network="wan"]');
  if (!card || !wan) return;
  card.hidden = false;
  card.classList.remove('state-up', 'state-down');
  if (wan.online === true) card.classList.add('state-up');
  if (wan.online === false) card.classList.add('state-down');
  setText('wan-value', wan.online === null ? '—'
    : wan.online ? `en ligne · ${wan.latency_ms} ms` : 'coupée');
  const ipSuffix = window.__publicIp ? ` · IP ${window.__publicIp}` : '';
  setText('wan-note', (wan.outages_24h
    ? `${wan.outages_24h} coupure(s) sur 24 h · dernière : ${wan.last_outage_minutes} min`
    : 'aucune coupure sur 24 h') + ipSuffix);
}

function applyNetwork(network) {
  if (!network) return;

  const tailscaleEl = document.getElementById('net-tailscale');
  const peers = network.tailscale_peers || [];
  if (tailscaleEl) {
    tailscaleEl.innerHTML = peers.length
      ? peers.map((p) => `<span class="peer peer-${p.online ? 'online' : 'offline'}"></span>`).join('')
      : '<span class="health-note">aucun pair</span>';
    tailscaleEl.querySelectorAll('.peer').forEach((node, i) => { node.textContent = peers[i].hostname; });
  }

  const neighbors = network.lan_neighbors || [];
  setText('net-lan-count', neighbors.length);
  const newBadge = document.getElementById('net-new-badge');
  if (newBadge) {
    const count = (network.new_devices || {}).count || 0;
    newBadge.hidden = count === 0;
    newBadge.textContent = count ? `${count} nouveau${count > 1 ? 'x' : ''}` : '';
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
    applyOffsite(data.offsite);
    window.__publicIp = data.public_ip ? data.public_ip.ip : null;
    applyWan(data.wan);
    applyNetwork(data.network);
    const time = new Date().toLocaleTimeString('fr-FR');
    if (stamp) stamp.textContent = `actualisé à ${time}`;
  } catch (error) {
    if (stamp) stamp.textContent = `hors ligne — dernière mise à jour conservée (${error.message})`;
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
        pre.textContent = data.logs && data.logs.trim() ? data.logs : '(aucune ligne de log)';
      } catch (error) {
        pre.textContent = `impossible de charger les logs (${error.message})`;
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
      button.textContent = 'Confirmer ?';
      setTimeout(() => {
        delete button.dataset.armed;
        button.classList.remove('armed');
        button.textContent = 'Redémarrer';
      }, 4000);
      return;
    }

    delete button.dataset.armed;
    button.classList.remove('armed');
    button.disabled = true;
    button.textContent = 'Redémarrage…';
    try {
      const response = await fetch(`/api/actions/restart/${encodeURIComponent(button.dataset.service)}`,
        { method: 'POST' });
      result.textContent = response.ok ? 'redémarré ✓' : `échec (${response.status})`;
      result.className = `action-result ${response.ok ? 'ok' : 'fail'}`;
    } catch (error) {
      result.textContent = `échec (${error.message})`;
      result.className = 'action-result fail';
    }
    button.disabled = false;
    button.textContent = 'Redémarrer';
    setTimeout(() => { result.textContent = ''; }, 8000);
  });
}
wireActions();
