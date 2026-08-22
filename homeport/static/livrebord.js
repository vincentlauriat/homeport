// Vue Livre de bord : la chronique des événements, peuplée par /api/events.
// Tout le texte passe par T() (i18n) et le DOM est construit par el() — jamais d'innerHTML
// avec des données mesurées (identités Tailscale, noms mDNS…).

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};

// Familles de filtre → préfixes de kind pour /api/events.
const FAMILIES = {
  all: null,
  services: 'service.',
  network: 'internet.,ip.,device.',
  actions: 'action.',
  machine: 'boot,power.,temp.,backup.',
};

const LANG = document.documentElement.lang || 'en';
const fmtTime = new Intl.DateTimeFormat(LANG, { hour: '2-digit', minute: '2-digit' });
const fmtDay = new Intl.DateTimeFormat(LANG, { weekday: 'long', day: 'numeric', month: 'long' });

let days = 7;
let family = 'all';
const serviceNames = {};
const serviceContainers = {};

async function loadServiceIndex() {
  // Mapping id → nom affiché / conteneur, pour des phrases lisibles et le drill-down logs.
  try {
    const status = await (await fetch('/api/status')).json();
    for (const group of status.groups || []) {
      for (const svc of group.services || []) {
        serviceNames[svc.id] = svc.name || svc.id;
        serviceContainers[svc.id] = svc.container || null;
      }
    }
  } catch { /* sans mapping, les ids bruts restent lisibles */ }
}

function sentence(event) {
  const key = `ev.${event.kind}`;
  const subject = serviceNames[event.subject] || event.subject;
  const text = T(key, { subject });
  // Kind inconnu (version plus récente du serveur) : la clé nue serait cryptique.
  return text === key ? `${event.kind} — ${subject}` : text;
}

function dayLabel(date, today, yesterday) {
  const key = date.toDateString();
  if (key === today) return T('logbook.today');
  if (key === yesterday) return T('logbook.yesterday');
  return fmtDay.format(date);
}

function logsDetail(container) {
  const wrap = el('details', 'logs-detail lb-logs');
  wrap.appendChild(el('summary', '', T('logbook.show_logs')));
  const pre = el('pre', 'logs-pre');
  let loaded = false;
  wrap.addEventListener('toggle', async () => {
    if (!wrap.open || loaded) return;
    loaded = true;
    pre.textContent = '…';
    try {
      const data = await (await fetch(`/api/logs/${encodeURIComponent(container)}?tail=100`)).json();
      pre.textContent = data.logs || T('logbook.logs_error');
    } catch {
      pre.textContent = T('logbook.logs_error');
    }
    wrap.appendChild(pre);
  });
  return wrap;
}

function render(events) {
  const root = document.getElementById('lb-days');
  root.replaceChildren();
  document.getElementById('lb-summary').textContent =
    T('logbook.summary', { count: events.length, days });

  if (!events.length) {
    root.appendChild(el('p', 'lb-empty', T('logbook.empty')));
    return;
  }

  const now = new Date();
  const today = now.toDateString();
  const yesterday = new Date(now.getTime() - 86400_000).toDateString();

  let currentKey = null;
  let list = null;
  for (const event of events) {
    const date = new Date(event.ts * 1000);
    if (date.toDateString() !== currentKey) {
      currentKey = date.toDateString();
      const day = el('section', 'lb-day');
      day.appendChild(el('h2', '', dayLabel(date, today, yesterday)));
      list = el('div', 'lb-list');
      day.appendChild(list);
      root.appendChild(day);
    }
    const row = el('div', 'lb-row');
    row.appendChild(el('span', 'lb-time', fmtTime.format(date)));
    row.appendChild(el('span', `edot edot-${event.severity}`));
    const text = el('span', 'lb-text');
    text.appendChild(el('b', '', sentence(event)));
    if (event.detail) text.appendChild(el('span', 'lb-detail', ` · ${event.detail}`));
    row.appendChild(text);
    const container = event.kind.startsWith('service.') && serviceContainers[event.subject];
    if (container) row.appendChild(logsDetail(container));
    list.appendChild(row);
  }
}

async function refresh() {
  const prefixes = FAMILIES[family];
  const url = `/api/events?days=${days}&limit=500${prefixes ? `&kinds=${encodeURIComponent(prefixes)}` : ''}`;
  try {
    const data = await (await fetch(url)).json();
    render(data.events || []);
    document.getElementById('refreshed').textContent = new Date().toLocaleTimeString(LANG);
  } catch { /* prochaine tentative au tick suivant */ }
}

function wireFilters(id, attr, apply) {
  document.getElementById(id).addEventListener('click', (e) => {
    const button = e.target.closest('button');
    if (!button) return;
    for (const b of button.parentElement.children) b.classList.toggle('active', b === button);
    apply(button.dataset[attr]);
    refresh();
  });
}

wireFilters('lb-families', 'family', (v) => { family = v; });
wireFilters('lb-periods', 'days', (v) => { days = Number(v); });

loadServiceIndex().then(refresh);
setInterval(() => { if (!document.hidden) refresh(); }, 60000);
