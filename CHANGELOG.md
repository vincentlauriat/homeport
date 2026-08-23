# Changelog

## Unreleased

- **Docker image freshness works again — it never did behind the socket proxy.** The check
  built its own client against `/var/run/docker.sock` instead of using the configured
  transport, so on any host reaching Docker through the read-only proxy the call failed and
  the feature quietly reported itself unavailable. It now uses the same transport as the rest
  of the Docker integration. A proxy refusal is an HTTP 403 rather than an exception, so
  images that cannot be read are reported as unknown instead of passing for locally built
  ones, and when none can be read the feature says so rather than returning a list that
  claims a check nobody ran. The bundled socket-proxy config now allows image reads
  (`IMAGES: 1`); `POST` stays refused, so nothing can be built, pulled or removed through it.

- **The application code now belongs to root, not to the service** — the installer used to
  hand `/opt/homeport` to the `homeport` user, so a compromised Homeport process could
  rewrite its own code and survive a restart. The tree is now owned by root and readable
  only; everything the service writes already lives in the data directory. The unit adds
  `ReadOnlyPaths=/opt/homeport` so the guarantee holds even if a deployment forgets the
  ownership.

## v0.6.2

- **A skip link on every view** — the navigation puts nine tabs before the content, so a
  keyboard user crossed all of them on each page load. The first thing focus reaches is
  now a link straight to the content; it stays out of sight until focused.
- **The design record matches what ships** — the amber used for degraded and the card
  hairlines were darkened for contrast without the change reaching DESIGN.md, so the
  document and the stylesheet disagreed on four colours. The document now records the
  measured values.
- The project page uses the same focus ring as the app.

## v0.6.1

- **Service state no longer depends on colour alone** — in the Journal list and the Control
  table the state dot was a bare span: a screen reader announced the service name and
  nothing about its health. Each dot is now hidden from assistive tech and paired with the
  translated state label, and the amber used for *degraded* was darkened so it clears the
  3:1 contrast floor for graphical objects (it sat at 2.2:1).
- **Card edges are easier to see** — with drop shadows gone, the hairline is the only thing
  separating a card from the page; it was faint enough to disappear for low-vision readers.
- **Lighter screenshots on the project page** — served as WebP with a PNG fallback, 468 KB
  down to 184 KB.

## v0.6.0

- **New visual identity** — an editorial black-and-white frame punctuated by narrative
  pastel blocks replaces the previous "Harbormaster's Desk" look: white canvas, ink text,
  hairlines instead of drop shadows, pill-shaped actions, and the current tab rendered as
  a filled ink pill. Service states keep a dedicated saturated triad that never mixes with
  the pastel palette — the pastel narrates, the saturated signals.
- **Fonts are now embedded** — Inter and JetBrains Mono ship as variable woff2 subsets
  served by Homeport itself (176 KB total, SIL OFL licences included). Nothing is fetched
  from a CDN; the offline-strict rule still holds.
- **Metric bars were invisible and now work again** — since v0.5.0 the server-rendered
  Classic view set an inline width on the bar fill while the stylesheet pinned it at
  `transform: scaleX(0)`, so no bar ever showed. The template now emits the transform,
  matching the JavaScript-driven views.
- **Chinese is no longer offered** — the interface ships in English and French only. A
  browser still carrying the old `homeport_lang=zh` cookie falls back to the server
  language instead of rendering a half-translated page.

## v0.5.1

- **Security hardening** — a same-origin (anti-CSRF) check now guards the restart and
  Wake-on-LAN endpoints, every response carries security headers (Content-Security-Policy
  with `frame-ancestors 'none'`, `X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`), the admin's Tailscale identity is no longer exposed to unauthenticated
  LAN readers, and the OpenAPI/Swagger docs are off unless `HOMEPORT_DOCS=1`.
- **Logbook records successful backups** — a backup that stays healthy used to produce no
  logbook entry at all; each new backup file now logs a `backup.ok` event with the filename.
- **Off-site backup tile** — the "Sauvegarde hors-site" tile reflects the real cross-site
  backup (config copied to the other house's Pi over Tailscale SSH) via a status file the
  backup script writes, instead of an unrelated, uninitialised mechanism.

## v0.5.0

- **Livebox module** — a sysbus collector polls the box directly (no credentials needed
  on the Livebox W7), with a dedicated `/livebox` page, a status row in every view,
  `livebox.up` / `livebox.down` events in the logbook, and en/fr/zh translations.
- **Mobile navigation** — the view-switch nav scrolls in place with the current tab
  centered; zero horizontal overflow at 320/390 px on all views.
- **Accessibility** — aria-labels on the `/reseau` device controls, `<main>` landmarks on
  four views, a single h1 on `/journal`, 44 px touch targets for prefs/summary/net-name
  links on coarse pointers.
- **Performance** — metric bars animate with `transform: scaleX` instead of `width`.
- **Demo fix** — `/api/history` samples are re-anchored on the real clock (charts used to
  draw off-window).

## v0.4.0

- **Three languages** — Chinese (Simplified) joins English and French, and every browser
  can pick its own language from the footer selector (cookie; the server config stays the
  default and still drives MQTT sensor names). Status labels and alerts follow too.
- **Light / dark / auto theme** — a footer selector forces light or dark per browser
  (localStorage, applied before first paint), "auto" keeps following the system.

- **Logbook view** (`/livre-de-bord`) — the major events of the server's life on a
  day-grouped timeline: service state transitions, Internet outages and recoveries,
  public-IP changes, new LAN devices, admin restarts/wakes, boots, under-voltage,
  temperature peaks and backup slips. Backed by a dedicated `events` table (1-year
  retention) fed by transition detectors on the existing background loops; admin actions
  are merged at read time. Filter by family and period, drill into container logs inline.

## v0.3.3

- **Uniform headers** — every page now shows the same top-left identity (anchor + your
  server's hostname, linking home from sub-pages) and the header keeps a constant height
  across pages. The Control and Journal headers were bespoke; sub-pages said "Homeport"
  instead of the hostname.
- **Static asset cache-busting** — CSS/JS URLs now carry the release version, so browsers
  pick up new code on every update without a hard refresh (stale JS could previously hide
  freshly shipped features).

## v0.3.2

- **Uniform view switcher** — the navigation bar now renders identically on every page
  (the Journal header leaked its small-caps styling into it).
- **Starlink in every view** — the Control network panel gets a Starlink row (with a link
  to the full page), the Journal "network & health" section a Starlink line, and the
  Wall footer a Starlink summary. The three views now cover everything the classic page shows.

## v0.3.1

- **Global navigation** — every page now carries the full view switcher (Classic, Control,
  Journal, Wall, Network, History, and Starlink when the module is enabled): the network,
  history and Starlink pages were only reachable through small in-card links, and had no
  obvious way back home.

## v0.3.0

- **Starlink module** — talks to the dish's gRPC API (192.168.100.1:9200) with a minimal
  protobuf wire codec, no grpcio: simplified card on the dashboard (state, latency,
  throughput, obstruction) and a full `/starlink` page with latency/throughput charts from
  the dish's 15-minute ring buffers, the sky obstruction map, GPS, alignment and alerts.
- New MQTT sensors when the module is enabled: `starlink_online`, `starlink_latency`,
  `starlink_down`, `starlink_up`, `starlink_obstruction`.
- Opt-in via a top-level `starlink:` section in `services.yaml` (`enabled: true`).
- New dependency: `h2` (HTTP/2 cleartext, prior knowledge).

## v0.2.0

- **Status files** — bridge any privileged job (offsite backup, replication…) to the
  dashboard: a JSON contract, a health card on every view, alerts when stale or failing,
  and an MQTT sensor (`{id}_age`).
- **MQTT identity follows `base_topic`** — discovery topics and `unique_id`s derive from
  your configured base topic, so several Homeport instances can share a broker and an
  instance migrating from another dashboard can keep its Home Assistant entities.
- MQTT sensor names are localized (en/fr).

## v0.1.0 — first public release

Extracted from a private Raspberry Pi dashboard project and generalized: any Debian/Linux
with systemd, conditional collectors, FHS paths, i18n (en/fr), demo mode, installer, docs.
