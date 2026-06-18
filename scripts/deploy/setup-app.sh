#!/usr/bin/env bash
# HIVE app setup on VPS (run after code + .env are in /opt/hive)
set -euo pipefail

HIVE_ROOT="${HIVE_ROOT:-/opt/hive}"
BACKEND="$HIVE_ROOT/backend"
FRONTEND="$HIVE_ROOT/frontend"

mkdir -p "$HIVE_ROOT/backend" "$HIVE_ROOT/frontend" "$HIVE_ROOT/logs" "$HIVE_ROOT/backups" "$HIVE_ROOT/shared"

if [[ ! -f "$BACKEND/.env" ]]; then
  echo "Missing $BACKEND/.env — copy from Mac first."
  exit 1
fi

cd "$BACKEND"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m playwright install chromium
./venv/bin/python -m playwright install-deps chromium || true

cd "$FRONTEND"
npm ci || npm install
npm run build

cp "$HIVE_ROOT/scripts/deploy/hive-backend.service" /etc/systemd/system/hive-backend.service
cp "$HIVE_ROOT/scripts/deploy/nginx-hive.conf" /etc/nginx/sites-available/hive.thiqos.com
ln -sf /etc/nginx/sites-available/hive.thiqos.com /etc/nginx/sites-enabled/hive.thiqos.com

systemctl daemon-reload
systemctl enable hive-backend
systemctl restart hive-backend
nginx -t && systemctl reload nginx

echo "✅ HIVE deployed. Configure SSL: certbot --nginx -d hive.thiqos.com"
