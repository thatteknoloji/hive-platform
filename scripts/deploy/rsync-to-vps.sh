#!/usr/bin/env bash
# Sync HIVE from Mac to VPS (excludes dev artifacts; keeps state/reports/talon_data/browser_profiles)
set -euo pipefail

VPS_HOST="${1:?Usage: ./rsync-to-vps.sh user@VPS_IP}"
HIVE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

rsync -avz --delete \
  --exclude '.git' \
  --exclude '.cache/' \
  --exclude '.tmp-hash-venv/' \
  --exclude 'node_modules' \
  --exclude 'frontend/node_modules/' \
  --exclude 'frontend/build' \
  --exclude 'backend/venv/' \
  --exclude 'backend/.env' \
  --exclude '.hive' \
  --exclude 'third_party' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "$HIVE_ROOT/" "$VPS_HOST:/opt/hive/"

echo ""
echo "Code synced. On VPS:"
echo "  scp backend/.env $VPS_HOST:/opt/hive/backend/.env"
echo "  ssh $VPS_HOST 'sudo -u hive bash /opt/hive/scripts/deploy/setup-app.sh'"
