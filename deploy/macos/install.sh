#!/usr/bin/env bash
# Homeport installer — macOS (launchd), périmètre "santé machine" (voir PLAN.md : pas de
# Docker, de services supervisés, de réseau LAN/Tailscale, de Starlink/Livebox sur cette
# instance — redondant avec le Pi qui couvre déjà le même réseau).
#
# À exécuter en tant qu'utilisateur normal (PAS root) depuis la racine du dépôt :
#
#   ./deploy/macos/install.sh
#
# Le script demande sudo lui-même, pour la seule partie qui en a besoin : le LaunchDaemon
# root qui relève la pression thermique (`powermetrics` l'exige). Le service principal, lui,
# tourne sous l'utilisateur courant, sans aucun privilège — même séparation que le timer NVMe
# root / service web non privilégié sur les Pi.
#
# Idempotent : re-lancer après un `git pull` recharge les deux services avec le code à jour.
set -euo pipefail

[[ "$(uname)" == "Darwin" ]] || { echo "macOS uniquement — voir deploy/install.sh pour Linux"; exit 1; }
[[ $EUID -ne 0 ]] || { echo "ne pas lancer en root — le script demande sudo lui-même si besoin"; exit 1; }
python3 -m venv --help >/dev/null 2>&1 || { echo "python3 (avec venv) est requis"; exit 1; }

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
APP_SUPPORT="$HOME/Library/Application Support/Homeport"
APP_DIR="$APP_SUPPORT/app"
CONFIG_DIR="$APP_SUPPORT/config"
DATA_DIR="$APP_SUPPORT/data"
LOG_DIR="$APP_SUPPORT/logs"
PORT="${HOMEPORT_PORT:-8080}"

echo "==> Application code -> $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete --exclude venv --exclude .git --exclude data --exclude config "$REPO_DIR/" "$APP_DIR/"

echo "==> Python environment"
[[ -d "$APP_DIR/venv" ]] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade -r "$APP_DIR/requirements.txt"

echo "==> Configuration -> $CONFIG_DIR (fichiers existants conservés)"
mkdir -p "$CONFIG_DIR"
for file in "$REPO_DIR"/config.example/*; do
  name="$(basename "$file")"
  [[ -e "$CONFIG_DIR/$name" ]] || install -m 644 "$file" "$CONFIG_DIR/$name"
done

echo "==> Répertoires de données et journaux -> $DATA_DIR, $LOG_DIR"
mkdir -p "$DATA_DIR" "$LOG_DIR"

echo "==> LaunchAgent (service principal, sous $(whoami), sans root)"
AGENT_LABEL="com.vincentlauriat.homeport"
AGENT_PLIST="$HOME/Library/LaunchAgents/$AGENT_LABEL.plist"
mkdir -p "$(dirname "$AGENT_PLIST")"
sed \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  -e "s|__CONFIG_DIR__|$CONFIG_DIR|g" \
  -e "s|__DATA_DIR__|$DATA_DIR|g" \
  -e "s|__LOG_DIR__|$LOG_DIR|g" \
  -e "s|__PORT__|$PORT|g" \
  "$REPO_DIR/deploy/macos/com.vincentlauriat.homeport.plist" > "$AGENT_PLIST"
launchctl unload "$AGENT_PLIST" 2>/dev/null || true
launchctl load "$AGENT_PLIST"

echo "==> LaunchDaemon (pression thermique, root — powermetrics l'exige)"
sudo install -m 755 "$REPO_DIR/deploy/macos/homeport-thermal.sh" /usr/local/bin/homeport-thermal.sh
DAEMON_LABEL="com.vincentlauriat.homeport.thermal"
DAEMON_PLIST="/Library/LaunchDaemons/$DAEMON_LABEL.plist"
sed -e "s|__THERMAL_PATH__|$DATA_DIR/thermal_pressure.txt|g" \
  "$REPO_DIR/deploy/macos/com.vincentlauriat.homeport.thermal.plist" \
  | sudo tee "$DAEMON_PLIST" >/dev/null
sudo launchctl unload "$DAEMON_PLIST" 2>/dev/null || true
sudo launchctl load "$DAEMON_PLIST"

echo "==> Health check"
sleep 2
curl -fsS "http://localhost:${PORT}/healthz" && echo
echo "==> OK — open http://localhost:${PORT}/ and edit $CONFIG_DIR/services.yaml"
