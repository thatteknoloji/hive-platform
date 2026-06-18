#!/usr/bin/env bash
# HIVE — tam sistem kontrolü
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0
WARN=0

ok()   { echo "  ✓ $1"; PASS=$((PASS+1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }
warn() { echo "  ~ $1"; WARN=$((WARN+1)); }

check_url() {
  local label="$1" url="$2"
  if curl -sf --max-time 5 "$url" >/dev/null 2>&1; then
    ok "$label"
  else
    fail "$label ($url)"
  fi
}

echo "══════════════════════════════════════"
echo " HIVE Sistem Kontrolü"
echo "══════════════════════════════════════"
echo ""

echo "[Dosyalar]"
[[ -f "$ROOT/backend/.env" ]]        && ok "backend/.env"        || fail "backend/.env eksik"
[[ -x "$ROOT/backend/venv/bin/python" ]] && ok "Python venv"      || fail "Python venv eksik — cd backend && python3 -m venv venv && pip install -r requirements.txt"
[[ -d "$ROOT/frontend/node_modules" ]]   && ok "frontend node_modules" || warn "frontend node_modules yok — cd frontend && npm install"
[[ -f "$ROOT/backend/.env" ]] && grep -q "TAVILY_API_KEY=." "$ROOT/backend/.env" 2>/dev/null && ok "TAVILY_API_KEY set" || warn "TAVILY_API_KEY boş"
[[ -f "$ROOT/backend/.env" ]] && grep -q "EXA_API_KEY=." "$ROOT/backend/.env" 2>/dev/null     && ok "EXA_API_KEY set"     || warn "EXA_API_KEY boş"
echo ""

echo "[Servisler]"
check_url "Backend /health"          "http://127.0.0.1:4001/health"
check_url "Talon V2 /api/talon/health" "http://127.0.0.1:4001/api/talon/health"
HIVE_KEY="$(grep -E '^HIVE_API_KEY=' "$ROOT/backend/.env" 2>/dev/null | cut -d= -f2- || echo "supersifre123")"
if curl -sf --max-time 5 -H "X-API-Key: $HIVE_KEY" "http://127.0.0.1:4001/api/place-seo/health" 2>/dev/null | grep -q '"success"'; then
  ok "Place SEO Pipeline /api/place-seo/health"
else
  fail "Place SEO Pipeline — backend eski, bash scripts/stop-hive.sh && bash scripts/start-hive.sh"
fi
if curl -sf --max-time 20 -H "X-API-Key: supersifre123" "http://127.0.0.1:4001/api/storyforge-v3/health" 2>/dev/null | grep -q '"ready"'; then
  ok "StoryForge V3 health"
else
  fail "StoryForge V3 health (fastCRW/Ollama/WP)"
fi
check_url "Frontend panel"           "http://127.0.0.1:4000"
HIVE_KEY="$(grep -E '^HIVE_API_KEY=' "$ROOT/backend/.env" 2>/dev/null | cut -d= -f2- || echo "supersifre123")"
for ep in \
  "/api/mission-control/dashboard" \
  "/api/campaigns/dashboard" \
  "/api/serp-defense/dashboard" \
  "/api/authority-mesh/dashboard" \
  "/api/revenue-leads/dashboard" \
  "/api/publisher-hub/health" \
  "/api/executive-ai/dashboard"; do
  if curl -sf --max-time 60 -H "X-API-Key: $HIVE_KEY" "http://127.0.0.1:4001${ep}" >/dev/null 2>&1; then
    ok "Panel API ${ep}"
  else
    fail "Panel API ${ep} (timeout/404 — backend yeniden başlat)"
  fi
done
echo ""

echo "[Docker — opsiyonel]"
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "Docker daemon"
    if curl -sf --max-time 3 "http://127.0.0.1:8081/search?q=test&format=json" >/dev/null 2>&1 || \
       curl -sf --max-time 3 "http://127.0.0.1:8081" >/dev/null 2>&1; then
      ok "SearXNG (8081)"
    else
      warn "SearXNG kapalı — npm run docker:searxng ile başlat"
    fi
  else
    warn "Docker daemon kapalı"
  fi
else
  warn "Docker kurulu değil"
fi
echo ""

echo "[Testler]"
if [[ -x "$ROOT/backend/venv/bin/python" ]]; then
  cd "$ROOT/backend"
  if ./venv/bin/python -m pytest tests/test_talon_v2.py -q --tb=no 2>/dev/null; then
    ok "pytest test_talon_v2.py"
  else
    fail "pytest test_talon_v2.py"
  fi
fi
echo ""

echo "══════════════════════════════════════"
echo " Sonuç: $PASS OK | $WARN uyarı | $FAIL hata"
echo "══════════════════════════════════════"

if [[ $FAIL -gt 0 ]]; then
  echo ""
  echo "Başlatmak için: npm start  veya  bash scripts/start-hive.sh"
  exit 1
fi
exit 0
