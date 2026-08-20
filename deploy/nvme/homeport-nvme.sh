#!/usr/bin/env bash
# Relève le journal SMART du SSD NVMe et l'écrit là où Homeport peut le lire SANS privilège.
#
# Lancé par `homeport-nvme.timer` en root (voir deploy/). Le service web, lui, tourne sans droit
# et se contente de lire ce fichier JSON — il n'appelle jamais `nvme` ni `sudo` lui-même.
#
#   homeport-nvme.sh [fichier_de_sortie]
set -euo pipefail

OUT="${1:-/var/lib/homeport/nvme.json}"
DEV="${NVME_DEV:-/dev/nvme0}"

command -v nvme >/dev/null 2>&1 || { echo "nvme-cli absent" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

# Écriture atomique : on ne remplace le fichier lu par Homeport qu'une fois le relevé complet.
nvme smart-log "$DEV" -o json > "$tmp"
chmod 644 "$tmp"
mv "$tmp" "$OUT"
trap - EXIT
