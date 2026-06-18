#!/usr/bin/env bash
# HIVE — tek komutla backend + frontend (+ opsiyonel Docker SearXNG)
set -euo pipefail

# macOS — malloc stack logging uyarılarını sustur (Python/node child process'ler için)
unset MallocStackLogging MallocStackLoggingNoCompact 2>/dev/null || true

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT/.hive"
LOG_DIR="$PID_DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[HIVE]${NC} $*"; }
warn()  { echo -e "${YELLOW}[HIVE]${NC} $*"; }
error() { echo -e "${RED}[HIVE]${NC} $*"; }

port_busy() {
  lsof -Pi ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

wait_url() {
  local url="$1" label="$2" max="${3:-40}"
  for ((i=1; i<=max; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      info "$label hazır ✓"
      return 0
    fi
    sleep 1
  done
  warn "$label zaman aşımı — log: $LOG_DIR"
  return 1
}

# --- .env kontrol ---
if [[ ! -f "$ROOT/backend/.env" ]]; then
  warn "backend/.env yok — .env.example'dan kopyalanıyor"
  cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
  warn "backend/.env dosyasını düzenleyip key'leri ekleyin"
fi

run_detached() {
  local logname="$1"
  shift
  if command -v setsid >/dev/null 2>&1; then
    setsid env -u MallocStackLogging -u MallocStackLoggingNoCompact "$@" >> "$LOG_DIR/${logname}.log" 2>&1 &
  else
    nohup env -u MallocStackLogging -u MallocStackLoggingNoCompact "$@" >> "$LOG_DIR/${logname}.log" 2>&1 &
  fi
  echo $!
}

# --- Backend ---
place_seo_ready() {
  local key
  key="$(grep -E '^HIVE_API_KEY=' "$ROOT/backend/.env" 2>/dev/null | cut -d= -f2- || echo "supersifre123")"
  curl -sf --max-time 3 -H "X-API-Key: $key" "http://127.0.0.1:4001/api/place-seo/health" 2>/dev/null \
    | grep -q '"Mekan SEO Content Pipeline"'
}

if port_busy 4001; then
  if place_seo_ready; then
    warn "Backend zaten çalışıyor (port 4001)"
  else
    warn "Backend eski sürümde — yeniden başlatılıyor (yeni modül route'ları yok)..."
    kill_port() {
      local pids
      pids="$(lsof -Pi ":4001" -sTCP:LISTEN -t 2>/dev/null || true)"
      [[ -n "$pids" ]] && echo "$pids" | xargs kill 2>/dev/null || true
      sleep 1
    }
    kill_port
    cd "$ROOT/backend"
    pid="$(run_detached backend ./venv/bin/python run.py)"
    echo "$pid" > "$PID_DIR/backend.pid"
    wait_url "http://127.0.0.1:4001/health" "Backend"
  fi
else
  info "Backend başlatılıyor (port 4001)..."
  cd "$ROOT/backend"
  pid="$(run_detached backend ./venv/bin/python run.py)"
  echo "$pid" > "$PID_DIR/backend.pid"
  wait_url "http://127.0.0.1:4001/health" "Backend"
fi

# --- Frontend ---
if port_busy 4000; then
  warn "Frontend zaten çalışıyor (port 4000)"
else
  info "Frontend başlatılıyor (port 4000)..."
  cd "$ROOT/frontend"
  if [[ ! -d node_modules ]]; then
    info "npm install çalıştırılıyor..."
    npm install --silent
  fi
  pid="$(run_detached frontend env BROWSER=none npm start)"
  echo "$pid" > "$PID_DIR/frontend.pid"
  wait_url "http://127.0.0.1:4000" "Frontend" 90
fi

# --- Docker SearXNG (opsiyonel) ---
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    info "Docker SearXNG kontrol ediliyor..."
    docker compose -f "$ROOT/docker-compose.seo-tools.yml" up -d searxng 2>/dev/null || \
      warn "SearXNG başlatılamadı (Tavily/Exa yine çalışır)"
    if port_busy 8081; then
      info "SearXNG hazır (port 8081) ✓"
    fi
    docker compose -f "$ROOT/docker-compose.seo-tools.yml" up -d crw 2>/dev/null || \
      warn "fastCRW başlatılamadı — StoryForge V3 için: npm run docker:crw"
    if port_busy 3000; then
      info "fastCRW hazır (port 3000) ✓"
    fi
  else
    warn "Docker kurulu ama daemon kapalı — SearXNG atlandı"
    warn "  → Docker Desktop'ı aç veya: docker compose -f docker-compose.seo-tools.yml up -d searxng"
  fi
else
  warn "Docker yok — SearXNG atlandı (Tavily/Exa/Autocomplete yine çalışır)"
fi

# --- Health özeti ---
info "Sağlık kontrolü..."
echo ""
curl -sf "http://127.0.0.1:4001/health" 2>/dev/null | python3 -m json.tool 2>/dev/null || true
echo ""
curl -sf "http://127.0.0.1:4001/api/talon/health" 2>/dev/null | python3 -m json.tool 2>/dev/null || true
echo ""
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "  Panel:    http://localhost:4000"
info "  API:      http://localhost:4001"
info "  Docs:     http://localhost:4001/docs"
info "  Talon:    http://localhost:4000/talon"
info "  Durdur:   npm run stop  veya  bash scripts/stop-hive.sh"
info "  Kontrol:  npm run check"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
