// Boîte à outils partagée des trois vues v1.0 (/controle, /journal, /mur).
// Chaque vue fournit un render(data) ; la boucle de sondage, le format et les sparklines
// sont ici pour n'exister qu'une fois. Aucune donnée système n'est insérée en HTML :
// toujours textContent.

window.RaspViews = (() => {
  const REFRESH_MS = 5000;
  const HISTORY_REFRESH_MS = 60000;

  const setText = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  };

  const setBar = (id, percent) => {
    const bar = document.getElementById(id);
    if (bar) bar.style.width = `${Math.min(Math.max(percent, 0), 100)}%`;
  };

  // Sparkline avec aire remplie — abscisse proportionnelle au temps écoulé, comme app.js :
  // un trou (redémarrage) ne doit pas étirer les échantillons sur toute la largeur.
  const drawSpark = (svg, points, { min, max }, height) => {
    if (!svg || points.length < 2) return;
    const w = 300, h = height, pad = 2;
    const range = Math.max(max - min, 1e-6);
    const t0 = points[0].ts, span = Math.max(points[points.length - 1].ts - t0, 1);
    const coords = points.map((p) => {
      const x = pad + ((p.ts - t0) / span) * (w - 2 * pad);
      const y = h - pad - ((p.value - min) / range) * (h - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const first = coords[0].split(',')[0], last = coords[coords.length - 1].split(',')[0];
    svg.innerHTML =
      `<polygon points="${first},${h} ${coords.join(' ')} ${last},${h}" class="spark-fill"/>` +
      `<polyline points="${coords.join(' ')}" class="spark-line"/>`;
  };

  // Verdict global : le pire état visible l'emporte. Utilisé par les vues B et C.
  const verdict = (data) => {
    const s = data.summary;
    const alerts = ((data.health || {}).alerts || []).length;
    if (s.down) return { level: 'down', text: Tn('journal.verdict_down', s.down) };
    if (s.warn) return { level: 'warn', text: Tn('journal.verdict_warn', s.warn) };
    if (alerts) return { level: 'warn', text: T('journal.verdict_almost') };
    return { level: 'up', text: T('journal.verdict_ok') };
  };

  // Âge de la sauvegarde la plus récente (SSD/SD), en texte court — les deux vues denses
  // l'affichent en chiffre, le détail vient de health.backups.
  const backupAge = (health) => {
    const dated = ((health || {}).backups || []).filter((b) => b.age_days !== null && b.age_days !== undefined);
    if (!dated.length) return null;
    return Math.round(Math.min(...dated.map((b) => b.age_days)) * 24);
  };

  const updateBadge = (update) => {
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
  };

  const startPolling = (render, renderHistory) => {
    const stamp = document.getElementById('refreshed');
    const refresh = async () => {
      try {
        const response = await fetch('/api/status', { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        render(data);
        updateBadge(data.update);
        if (stamp) stamp.textContent = T('common.refreshed_at', { time: new Date().toLocaleTimeString() });
      } catch (error) {
        if (stamp) stamp.textContent = T('common.offline_kept', { error: error.message });
      }
    };
    const refreshHistory = async () => {
      if (!renderHistory) return;
      try {
        const response = await fetch('/api/history?hours=24', { cache: 'no-store' });
        if (response.ok) renderHistory(await response.json());
      } catch { /* l'historique en retard n'est pas une panne */ }
    };
    refresh();
    refreshHistory();
    setInterval(() => { if (!document.hidden) refresh(); }, REFRESH_MS);
    setInterval(() => { if (!document.hidden) refreshHistory(); }, HISTORY_REFRESH_MS);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) { refresh(); refreshHistory(); }
    });
  };

  return { setText, setBar, drawSpark, verdict, backupAge, startPolling };
})();
