#!/usr/bin/env bash
# Production health check for hive.thiqos.com
set -euo pipefail

DOMAIN="${HIVE_DOMAIN:-https://hive.thiqos.com}"
API_KEY="${HIVE_API_KEY:-}"
EMAIL="${HIVE_ADMIN_EMAIL:-}"
PASSWORD="${HIVE_ADMIN_PASSWORD:-}"
FAIL=0

ok() { echo "✅ $*"; }
bad() { echo "❌ $*"; FAIL=1; }

if systemctl is-active --quiet hive-backend 2>/dev/null; then
  ok "hive-backend service active"
else
  bad "hive-backend service not active"
fi

if curl -sf --max-time 5 http://127.0.0.1:4001/health >/dev/null; then
  ok "backend /health local"
else
  bad "backend /health local"
fi

if curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$DOMAIN/" | grep -q 200; then
  ok "frontend $DOMAIN 200"
else
  bad "frontend $DOMAIN"
fi

ROBOTS=$(curl -sI --max-time 10 "$DOMAIN/" | tr -d '\r' | grep -i x-robots-tag || true)
if echo "$ROBOTS" | grep -qi noindex; then
  ok "X-Robots-Tag noindex"
else
  bad "X-Robots-Tag missing"
fi

if [[ -n "$API_KEY" ]]; then
  if curl -sf --max-time 15 -H "X-API-Key: $API_KEY" "$DOMAIN/api/mission-control/health" >/dev/null; then
    ok "API proxy + key auth"
  else
    bad "API proxy / mission-control health"
  fi
fi

if [[ -n "$EMAIL" && -n "$PASSWORD" ]]; then
  TOKEN=$(curl -sf --max-time 15 -X POST "$DOMAIN/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || true)
  if [[ -n "$TOKEN" ]]; then
    ok "login flow"
    if curl -sf --max-time 15 -H "Authorization: Bearer $TOKEN" "$DOMAIN/api/auth/me" | grep -q authenticated; then
      ok "JWT /api/auth/me"
    else
      bad "JWT /api/auth/me"
    fi
  else
    bad "login flow"
  fi
fi

if [[ -d /opt/hive/backend/venv ]]; then
  if /opt/hive/backend/venv/bin/python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print(p.chromium.executable_path); p.stop()" 2>/dev/null; then
    ok "playwright chromium"
  else
    bad "playwright chromium"
  fi
fi

df -h / | tail -1 | awk '{print "Disk:", $5, "used on", $1}'
free -h | awk '/Mem:/ {print "Memory:", $3 "/" $2}'

exit $FAIL
