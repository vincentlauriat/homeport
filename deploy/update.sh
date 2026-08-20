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

# `git pull` rewrites this very script while bash is still reading it, which silently
# skips or corrupts the remaining lines. Stage 1 only pulls, then re-executes the freshly
# pulled version of itself; stage 2 does the actual install/restart.
if [ "${HOMEPORT_UPDATE_STAGE2:-}" != "1" ]; then
  echo "==> Pulling latest code"
  git fetch --tags origin
  git pull --ff-only origin main
  HOMEPORT_UPDATE_STAGE2=1 exec bash "$REPO_DIR/deploy/update.sh"
fi

echo "==> Re-running installer"
"$REPO_DIR/deploy/install.sh"

echo "==> Restarting service"
systemctl restart homeport
sleep 2

echo "==> Done — $(curl -fsS http://localhost/healthz 2>/dev/null || echo 'check the service: systemctl status homeport')"
