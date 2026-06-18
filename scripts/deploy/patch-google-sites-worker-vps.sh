#!/usr/bin/env bash
# Deploy google_sites_worker.py fix to VPS and run verification.
set -euo pipefail

HIVE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$HIVE_ROOT/backend/.env"
WORKER="$HIVE_ROOT/backend/app/moduller/google_sites_worker.py"
HOST="${VPS_HOST:-$(grep '^VPS_HOST=' "$ENV_FILE" | cut -d= -f2-)}"
USER="${VPS_SSH_USER:-$(grep '^VPS_SSH_USER=' "$ENV_FILE" | cut -d= -f2-)}"
PASS="${VPS_SSH_PASS:-$(grep '^VPS_SSH_PASS=' "$ENV_FILE" | cut -d= -f2-)}"
REMOTE="${USER}@${HOST}"

SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
SSH="sshpass -p $PASS ssh ${SSH_OPTS[*]} $REMOTE"
SCP="sshpass -p $PASS scp ${SSH_OPTS[*]}"

echo "==> Uploading google_sites_worker.py to $REMOTE"
$SCP "$WORKER" "$REMOTE:/opt/hive/backend/app/moduller/google_sites_worker.py"

echo "==> Remote verify + restart + health + process task"
$SSH bash -s <<'REMOTE'
set -euo pipefail
cd /opt/hive/backend

python3 -m py_compile app/moduller/google_sites_worker.py
echo "py_compile: OK"

systemctl restart hive-backend
sleep 8

KEY="$(grep '^HIVE_API_KEY=' .env | cut -d= -f2-)"

echo ""
echo "=== HEALTH ==="
curl -i -H "X-API-Key: $KEY" http://127.0.0.1:4001/api/google-sites/health

TASK_ID="gsw-f415377e6c"
pkill -f chrome || true
pkill -f chromium || true
sleep 2

echo ""
echo "=== PROCESS TASK $TASK_ID ==="
curl -s -X POST \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"task_id\":\"$TASK_ID\"}" \
  http://127.0.0.1:4001/api/google-sites/process-task | python3 -m json.tool

echo ""
echo "=== DEBUG LOGS ==="
ls -lah app/logs/google_sites_debug/ || true
REMOTE

echo ""
echo "Done."
