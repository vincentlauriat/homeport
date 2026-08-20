# Configuration reference

One file: `/etc/homeport/services.yaml` (or `$HOMEPORT_CONFIG_DIR/services.yaml`).
Re-read on every request — no restart needed. Start from
[config.example/services.yaml](../config.example/services.yaml), which documents every field
inline.

## Top level

| Key | Default | Meaning |
|---|---|---|
| `language` | `en` | UI language (`en` or `fr`); `HOMEPORT_LANG` overrides |
| `groups` | — | The services, grouped for display |
| `health` | `{}` | Machine-health monitoring options |
| `actions` | `admin: ~` | Who may act (see [security-model.md](security-model.md)) |
| `mqtt` | `enabled: false` | Home Assistant publishing |

## A service

```yaml
- id: homeassistant          # unique, used in URLs and availability history
  name: Home Assistant
  icon: "🏠"                 # any emoji
  description: one line under the name
  docker: homeassistant      # container name (needs the socket proxy)
  systemd: ha.service        # and/or a systemd unit
  probe: {type: http, port: 8123, path: /manifest.json}   # or {type: tcp, port: N}
  link: {port: 8123, path: /, scheme: http}   # makes the tile clickable
  restartable: true          # show the restart button to the admin (needs sudoers)
```

States combine: all sources agree up → **running**; all down → **stopped**; disagreement →
**degraded**. A `.timer` unit automatically shows its next/last run.

## health

```yaml
health:
  backups:                   # newest file matching pattern must be younger than warn_after_days
    - {id: config, name: Config backup, path: /var/backups, pattern: "*.tar.gz", warn_after_days: 2}
  journal: {since: "24 hours ago", ignore: [noisy-unit]}
  disks: ["/", "/srv"]       # mount points on the metric tiles (default: ["/"])
  intervals: {network: 60, wan: 60, public_ip: 3600}   # seconds; 0 disables a job
  history: {retention_days: 7}
```

## Status files

Bridge any privileged job (offsite backup, replication, certificate renewal…) to the
dashboard: the job writes a small JSON where Homeport can read it, Homeport shows a health
card, raises an alert when it goes wrong or stale, and publishes an MQTT sensor
(`{id}_age`, hours).

```yaml
health:
  status_files:
    - id: offsite
      name: Offsite backup
      path: /var/lib/homeport/offsite.json
      warn_after_hours: 48     # optional: alert when the last success is older
```

The file's contract (every field optional except `status`):

```json
{"status": "ok",                  // "ok" | "pending" | "error"
 "message": "one line for humans",
 "last_ts": 1787217794}           // unix time of the last success (or last_snapshot_ts)
```

`error` shows red; `pending`, a missing/unreadable file, or an overdue `ok` show amber.

## Environment variables

| Variable | Default | |
|---|---|---|
| `HOMEPORT_CONFIG_DIR` | `/etc/homeport` (or `./config` in dev) | |
| `HOMEPORT_DATA_DIR` | `/var/lib/homeport` (or `./data`) | SQLite + JSON drops |
| `HOMEPORT_DB_PATH`, `HOMEPORT_NVME_PATH` | inside `DATA_DIR` | individual overrides |
| `HOMEPORT_DOCKER_HOST` | `unix:///var/run/docker.sock` in dev, `tcp://127.0.0.1:2375` in the unit | |
| `HOMEPORT_PORT` | `80` (in the unit) | |
| `HOMEPORT_LANG` | — | overrides `language` |
| `HOMEPORT_DEMO` | — | `1` = simulated data |
| `HOMEPORT_MQTT_USERNAME` / `_PASSWORD` | — | via `/etc/homeport/mqtt.env` |
