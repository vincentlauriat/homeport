# Changelog

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
