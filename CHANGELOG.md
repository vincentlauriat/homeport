# Changelog

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
