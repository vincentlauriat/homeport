#!/usr/bin/env bash
# Sauvegarde de la configuration domotique de `raspcorse` — v2 (2026-08-22).
#
# Déclenché par `raspcorse-backup.timer` (quotidien, 03:30 + délai aléatoire, Persistent=true).
# Installé à /usr/local/bin/raspcorse-backup.sh, exécuté en root.
#
# Trois destinations :
#   1. /mnt/ssd/backups                  (NVMe)  — 14 archives, l'historique de travail
#   2. /var/backups/raspcorse               (eMMC/SD) — 3 archives, filet si le NVMe meurt
#   3. raspyellow:/mnt/ssd/backups/offsite-raspcorse — 7 archives HORS SITE via Tailscale SSH
#      (copie croisée entre les deux maisons ; non bloquant si le site distant est injoignable)
#
# Les bases recorder (*.db) et les logs sont exclus : configuration, pas historique.
set -uo pipefail
BACKUP_DIR="${BACKUP_DIR:-/mnt/ssd/backups}"
MIRROR_DIR="${MIRROR_DIR:-/var/backups/raspcorse}"
RETENTION="${RETENTION:-14}"
MIRROR_RETENTION="${MIRROR_RETENTION:-3}"
PEER="${PEER:-raspyellow.sable-qilin.ts.net}"
OFFSITE_DIR="/mnt/ssd/backups/offsite-raspcorse"
OFFSITE_RETENTION="${OFFSITE_RETENTION:-7}"
# Fichier d'état lu par Homeport (tuile « Sauvegarde hors-site ») — reflète la copie croisée
# réelle vers le peer, remplace l'ancien suivi restic→minicorse.
OFFSITE_STATUS_FILE="${OFFSITE_STATUS_FILE:-/mnt/ssd/homeport-data/offsite.json}"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -o BatchMode=yes"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$BACKUP_DIR/raspcorse-config-$STAMP.tar.gz"
mkdir -p "$BACKUP_DIR"

# Ne retenir que les chemins réellement présents (robustesse aux évolutions de stack)
SSD_CANDIDATES=(homeassistant mosquitto/config mosquitto/data eufy-security-ws socket-proxy hermes homeport homeport-data)
ROOT_CANDIDATES=(etc/homeport var/lib/homeport)
SSD_ITEMS=(); for p in "${SSD_CANDIDATES[@]}"; do [ -e "/mnt/ssd/$p" ] && SSD_ITEMS+=("$p"); done
ROOT_ITEMS=(); for p in "${ROOT_CANDIDATES[@]}"; do [ -e "/$p" ] && ROOT_ITEMS+=("$p"); done

tar czf "$OUT" \
  --warning=no-file-changed \
  --exclude="homeassistant/config/*.db" \
  --exclude="homeassistant/config/*.db-wal" \
  --exclude="homeassistant/config/*.db-shm" \
  --exclude="homeassistant/config/home-assistant.log*" \
  --exclude="homeassistant/config/tts" \
  --exclude="homeassistant/config/deps" \
  --exclude="zigbee2mqtt/log" \
  -C /mnt/ssd "${SSD_ITEMS[@]}" \
  $( [ ${#ROOT_ITEMS[@]} -gt 0 ] && echo -C / "${ROOT_ITEMS[@]}" )
rc=$?
if [ "$rc" -ge 2 ]; then echo "ERREUR tar (code $rc)" >&2; exit "$rc"; fi
tar tzf "$OUT" >/dev/null || { echo "Archive corrompue: $OUT" >&2; exit 1; }
ls -1t "$BACKUP_DIR"/raspcorse-config-*.tar.gz 2>/dev/null | tail -n +$((RETENTION+1)) | xargs -r rm -f

# --- Miroir local (support physique distinct) --------------------------------
mirror_status="miroir OK"
if mkdir -p "$MIRROR_DIR" && cp -pf "$OUT" "$MIRROR_DIR/" && sync; then
  if ! tar tzf "$MIRROR_DIR/$(basename "$OUT")" >/dev/null 2>&1; then
    rm -f "$MIRROR_DIR/$(basename "$OUT")"
    mirror_status="ECHEC miroir : copie illisible, supprimée"
  else
    ls -1t "$MIRROR_DIR"/raspcorse-config-*.tar.gz 2>/dev/null | tail -n +$((MIRROR_RETENTION+1)) | xargs -r rm -f
  fi
else
  mirror_status="ECHEC miroir : copie impossible vers $MIRROR_DIR"
fi

# --- Copie hors site croisée (via Tailscale SSH, NON bloquante) ---------------
offsite_status="hors-site OK vers $PEER"
if scp $SSH_OPTS -q "$OUT" "vincent@$PEER:$OFFSITE_DIR/" 2>/dev/null \
   && ssh $SSH_OPTS "vincent@$PEER" "tar tzf '$OFFSITE_DIR/$(basename "$OUT")' >/dev/null && ls -1t $OFFSITE_DIR/raspcorse-config-*.tar.gz 2>/dev/null | tail -n +$((OFFSITE_RETENTION+1)) | xargs -r rm -f" 2>/dev/null; then
  mkdir -p "$(dirname "$OFFSITE_STATUS_FILE")" 2>/dev/null || true
  printf '{"status":"ok","message":"hors-site → %s","last_ts":%s}\n' "$PEER" "$(date +%s)" > "$OFFSITE_STATUS_FILE" 2>/dev/null || true
else
  offsite_status="ECHEC hors-site vers $PEER (site distant injoignable ?) — non bloquant"
  echo "$offsite_status" >&2
  mkdir -p "$(dirname "$OFFSITE_STATUS_FILE")" 2>/dev/null || true
  printf '{"status":"error","message":"echec hors-site vers %s"}\n' "$PEER" > "$OFFSITE_STATUS_FILE" 2>/dev/null || true
fi

echo "Sauvegarde OK : $OUT ($(du -h "$OUT" | cut -f1)) · $mirror_status · $offsite_status"
case "$mirror_status" in ECHEC*) echo "$mirror_status" >&2; exit 1 ;; esac
