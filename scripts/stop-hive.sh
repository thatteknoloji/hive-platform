#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT/.hive"

kill_pid() {
  local name="$1" pidfile="$PID_DIR/$2"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "[HIVE] $name durduruldu (PID $pid)"
    fi
    rm -f "$pidfile"
  fi
}

kill_port() {
  local port="$1" label="$2"
  local pids
  pids="$(lsof -Pi ":$port" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill 2>/dev/null || true
    echo "[HIVE] $label (port $port) durduruldu"
  fi
}

kill_pid "Backend"  "backend.pid"
kill_pid "Frontend" "frontend.pid"
kill_port 4001 "Backend"
kill_port 4000 "Frontend"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker compose -f "$ROOT/docker-compose.seo-tools.yml" stop searxng 2>/dev/null || true
  echo "[HIVE] SearXNG durduruldu (opsiyonel)"
fi

echo "[HIVE] Tamamlandı."
