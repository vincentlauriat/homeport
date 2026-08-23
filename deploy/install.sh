#!/usr/bin/env bash
# Homeport installer — Debian/Ubuntu (systemd). Run as root from the repo root:
#
#   sudo ./deploy/install.sh
#
# Idempotent: re-run it after every `git pull` to update. It never overwrites your
# configuration in /etc/homeport.
set -euo pipefail

APP_DIR=/opt/homeport
CONFIG_DIR=/etc/homeport
DATA_DIR=/var/lib/homeport
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

[[ $EUID -eq 0 ]] || { echo "run me as root (sudo ./deploy/install.sh)"; exit 1; }
command -v systemctl >/dev/null || { echo "systemd is required"; exit 1; }
python3 -m venv --help >/dev/null 2>&1 || { echo "python3-venv is required (apt install python3-venv)"; exit 1; }

echo "==> System user"
id homeport >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin homeport

echo "==> Application code -> $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete --exclude venv --exclude .git --exclude data --exclude config "$REPO_DIR/" "$APP_DIR/"

echo "==> Python environment"
[[ -d "$APP_DIR/venv" ]] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade -r "$APP_DIR/requirements.txt"

# Le code appartient à root, pas au service : un Homeport compromis ne peut pas réécrire son
# propre code pour se rendre persistant. Le service n'a besoin que de lire et d'exécuter —
# tout ce qu'il écrit vit dans $DATA_DIR. Le chmod normalise ce que pip a pu poser en 640 :
# sans lui, root:root transformerait un mode restrictif en échec au démarrage.
chown -R root:root "$APP_DIR"
chmod -R u=rwX,go=rX "$APP_DIR"

echo "==> Configuration -> $CONFIG_DIR (existing files are kept)"
mkdir -p "$CONFIG_DIR"
for file in "$REPO_DIR"/config.example/*; do
  name="$(basename "$file")"
  [[ -e "$CONFIG_DIR/$name" ]] || install -m 644 "$file" "$CONFIG_DIR/$name"
done

echo "==> Data directory -> $DATA_DIR"
mkdir -p "$DATA_DIR"
chown homeport:homeport "$DATA_DIR"

echo "==> systemd unit"
install -m 644 "$REPO_DIR/deploy/homeport.service" /etc/systemd/system/homeport.service
systemctl daemon-reload
systemctl enable --now homeport.service

echo "==> Health check"
sleep 2
port="$(systemctl show homeport -p Environment | tr ' ' '\n' | sed -n 's/^HOMEPORT_PORT=//p')"
curl -fsS "http://localhost:${port:-80}/healthz" && echo
echo "==> OK — open http://$(hostname)/ and edit $CONFIG_DIR/services.yaml"
echo "    Optional next steps (see docs/): Docker socket proxy, restart actions (sudoers),"
echo "    NVMe wear timer, MQTT/Home Assistant."
