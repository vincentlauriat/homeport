#!/usr/bin/env bash
# Relève la pression thermique macOS et l'écrit là où Homeport peut le lire SANS privilège.
#
# Lancé par le LaunchDaemon `com.vincentlauriat.homeport.thermal` en root (voir deploy/macos/) —
# `powermetrics` exige root. Le service web, lui, tourne sans droit et se contente de lire ce
# fichier (collectors/thermal_pressure.py) — il n'appelle jamais `powermetrics` ni `sudo`
# lui-même. Même patron que le timer NVMe (deploy/nvme/homeport-nvme.sh).
#
# Le chemin de sortie est un ARGUMENT OBLIGATOIRE, jamais dérivé de $HOME : un LaunchDaemon
# root a pour $HOME /var/root, pas celui de la personne qui a installé Homeport.
#
#   homeport-thermal.sh <fichier_de_sortie>
set -euo pipefail

OUT="${1:?usage: homeport-thermal.sh <fichier_de_sortie>}"

mkdir -p "$(dirname "$OUT")"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

# Écriture atomique : on ne remplace le fichier lu par Homeport qu'une fois le relevé complet.
# Le sampler est `thermal`, pas `smc` (inexistant sur les Mac récents) ni `--show-all` (bien
# plus lourd que nécessaire) — vérifié en root sur un Mac17,3 avant d'écrire ce script.
powermetrics -i1 -n1 --samplers thermal > "$tmp"
chmod 644 "$tmp"
mv "$tmp" "$OUT"
trap - EXIT
