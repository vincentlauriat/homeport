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

// Trois vérités que le code confondait en deux : la tuile est à jour, la tuile signale un
// problème, ou la source n'existe pas sur cette machine. « Graceful absence » veut que le
// troisième cas disparaisse, pas qu'il porte un avertissement ambre — accuser un foyer de
// ne pas sauvegarder alors qu'il n'a jamais rien configuré est un mensonge, pas une alerte.
const hideCell = (id) => {
  const cell = document.getElementById(id);
  if (cell) cell.hidden = true;
};

// `word` est passé par l'appelant, jamais dérivé de `level` : les cinq tuiles n'ont pas le
// même `warn`. Services dégradés, sauvegarde en retard, mises à jour en attente et nouveaux
// appareils sont quatre choses différentes — les étiqueter toutes « Dégradé » serait aussi
// faux que de n'afficher aucun mot.
const setCell = (id, big, small, foot, level, word) => {
  const cell = document.getElementById(id);
  if (!cell) return;
  cell.hidden = false;
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
  if (footNode && footNode.textContent !== String(foot)) footNode.textContent = foot;
  // L'état ne peut pas tenir à la seule couleur du chiffre (WCAG 1.4.1) : le reste de l'app
  // associe couleur et mot depuis la v0.6.1, le Mur avait été oublié. Le mot est VISIBLE,
  // pas `sr-only` — celui qui traverse la pièce ne se sert pas d'un lecteur d'écran.
  const stateNode = cell.querySelector('.cell-state');
  if (stateNode) {
    const label = (level === 'warn' || level === 'down') && word ? word : '';
    if (stateNode.textContent !== label) stateNode.textContent = label;
    stateNode.hidden = !label;
  }
};

// Le lien avec le serveur, rendu à la distance de lecture. Un texte de 13 px dans le pied
// suffit sur un écran qu'on consulte ; ici, le halo passe au gris, les chiffres se
// désaturent (CSS, via `data-link` sur <body>) et la ligne qui répond à « est-ce que tout
// va bien ? » dit qu'elle ne sait plus. Sans cela le Mur affiche un vert périmé pendant des
// heures pendant que l'horloge, indépendante du sondage, certifie une fraîcheur inexistante.
function onLink(state, lastOk) {
  if (state === 'ok' || state === 'loading') return;  // render() reprend la main
  const wrap = document.getElementById('w-state');
  const halo = document.getElementById('w-halo');
  if (wrap) wrap.className = 'wall-state state-unknown';
  if (halo) halo.className = 'wall-halo halo-unknown';
  setText('w-state-text', state === 'never'
    ? T('wall.offline_never')
    : T('wall.offline_since', {
      time: lastOk.toLocaleTimeString(document.documentElement.lang, { hour: '2-digit', minute: '2-digit' }),
    }));
}

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
    s.down ? 'down' : s.warn ? 'warn' : 'ok',
    s.down ? T('state.down') : T('state.warn'));

  const wan = data.wan;
  if (!wan) hideCell('w-internet');
  else {
    setCell('w-internet',
      // Arrondi à l'entier : sur un chiffre de 48 px relu toutes les 5 s, une décimale qui
      // apparaît et disparaît fait sauter la largeur du bloc — exactement le scintillement
      // que `tabular-nums` cherchait à supprimer.
      wan.online === null ? '—' : wan.online ? `${Math.round(wan.latency_ms)}` : T('net.offline'),
      wan.online ? 'ms' : '',
      wan.outages_24h ? Tn('net.outages_detail', wan.outages_24h) : T('net.no_outage'),
      wan.online ? 'ok' : wan.online === false ? 'down' : '',
      T('wall.mark_offline'));
  }

  const age = backupAge(data.health);
  const backups = ((data.health || {}).backups || []);
  // Aucune sauvegarde déclarée : la tuile disparaît. Elle ne devient ambre que si des
  // sauvegardes existent et qu'elles ont vieilli — un défaut réel, pas une absence.
  if (!backups.length) hideCell('w-backup');
  else {
    const marks = backups.map((b) => `${b.name} ${b.state === 'ok' ? '✓' : '✗'}`).join(' · ');
    setCell('w-backup', age === null ? '—' : `${age}`, age === null ? '' : 'h',
      marks,
      age !== null && age < 30 ? 'ok' : 'warn',
      T('wall.mark_late'));
  }

  const apt = (data.health || {}).apt;
  if (!apt) hideCell('w-updates');
  else {
    setCell('w-updates', `${apt.security}`, T('wall.updates_security'),
      apt.total ? T('wall.updates_total', { count: apt.total }) : T('wall.updates_none'),
      apt.security ? 'warn' : 'ok',
      T('wall.mark_pending'));
  }

  const net = data.network || {};
  const lan = (net.lan_neighbors || []).length;
  const fresh = (net.new_devices || {}).count || 0;
  const peersOnline = (net.tailscale_peers || []).filter((p) => p.online).length;
  // Unité dans le slot principal comme les cinq autres tuiles : un chiffre géant sans unité
  // n'est pas lisible de loin, il est juste grand.
  setCell('w-lan', `${lan}`, T('wall.lan_devices'),
    T('wall.lan_detail', { fresh, peers: peersOnline }),
    fresh ? 'warn' : '',
    T('wall.mark_new'));

  // Pied : détails machine en petit.
  const sys = data.system;
  const nvme = data.nvme;
  const wear = nvme && nvme.percent_used !== null && nvme.percent_used !== undefined ? ' · ' + T('wall.ssd_wear', { pct: nvme.percent_used }) : '';
  setText('wf-ssd', sys.storage_temperature_c === null ? '' : T('wall.ssd', { temp: sys.storage_temperature_c }) + wear);
  setText('wf-mem', T('wall.mem', { pct: sys.memory.percent }));
  const power = (data.health || {}).throttling;
  setText('wf-power', sys.undervoltage ? T('wall.power_undervoltage')
    : power && power.available ? T('wall.power', { state: T(power.healthy ? 'health.power_ok' : 'health.power_incident') }) : '');
  // Ni IP publique, ni Starlink, ni Livebox dans ce pied. Le Mur est l'écran le plus exposé
  // du produit — allumé en permanence dans une pièce partagée, visible des invités,
  // photographiable — et le seul qui affichait l'IP publique en clair, alors que le produit
  // masque par ailleurs l'identité LAN. Ces trois informations restent sur Contrôle, Réseau
  // et leurs vues dédiées, où l'écran n'est pas permanent et le texte se lit de près.

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

startPolling(render, renderHistory, onLink);
