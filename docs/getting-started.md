# Getting started

## Requirements

- Debian, Ubuntu or Raspberry Pi OS with systemd
- Python 3.11+ and `python3-venv`
- Optional: Docker (container states), Tailscale (actions + peers), `avahi-utils`
  (mDNS device names), `nvme-cli` (SSD wear), Mosquitto (Home Assistant integration)

## Install

```bash
git clone https://github.com/vincentlauriat/homeport && cd homeport
sudo ./deploy/install.sh
```

The installer creates a `homeport` system user, a venv under `/opt/homeport`, copies the
example configuration to `/etc/homeport` (never overwriting yours), installs and starts
`homeport.service` on port 80. Re-run it after every `git pull` to update.

## Configure

Everything lives in `/etc/homeport/services.yaml` — one commented file, four sections
(`groups`, `health`, `actions`, `mqtt`). It is re-read on every request: edit, refresh
the page, done. Full reference: [configuration.md](configuration.md).

## Optional integrations

| Feature | What to do |
|---|---|
| Container states + CPU + logs | Start the read-only [socket proxy](../deploy/socket-proxy/) (`docker compose up -d`); the unit already points at it |
| Restart buttons | Declare `restartable: true` on services, set `actions.admin`, install [sudoers rules](../deploy/sudoers.example) |
| SSD wear | `install -m 755 deploy/nvme/homeport-nvme.sh /usr/local/bin/` + install the [service and timer](../deploy/nvme/), `systemctl enable --now homeport-nvme.timer` |
| Home Assistant | Enable the `mqtt:` section; credentials in `/etc/homeport/mqtt.env` (`HOMEPORT_MQTT_USERNAME=`, `HOMEPORT_MQTT_PASSWORD=`, root-only). Entities appear via MQTT discovery |
| French UI | `language: fr` at the top of the config |

## Demo mode

`HOMEPORT_DEMO=1` replaces every collector with realistic simulated data — no system access,
no background jobs. Perfect for trying the views or developing on a laptop.
