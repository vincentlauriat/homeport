#!/usr/bin/env bash
# Homeport updater — run as root from the repo clone:
#
#   sudo ./deploy/update.sh
#
# Pulls the latest release code (fast-forward only: your clone must be clean), re-runs the
# idempotent installer (venv deps, unit, /etc/homeport untouched), restarts the service and
# verifies /healthz. Your configuration and data are never modified.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Pulling latest code"
git fetch --tags origin
git pull --ff-only origin main

echo "==> Re-running installer"
"$REPO_DIR/deploy/install.sh"

echo "==> Done — $(curl -fsS http://localhost/healthz 2>/dev/null || echo 'check the service: systemctl status homeport')"
