#!/usr/bin/env bash
# HIVE — ücretsiz domain/backlink provider kurulumu (Namecheap/DataForSEO yerine)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[HIVE]${NC} $*"; }
warn()  { echo -e "${YELLOW}[HIVE]${NC} $*"; }

info "Ücretsiz SEO provider kurulumu..."

if command -v npm >/dev/null 2>&1; then
  info "agent-domain-service-mcp kontrol..."
  npx -y agent-domain-service-mcp --help >/dev/null 2>&1 || warn "agent-domain-service-mcp yüklenemedi — whois/DNS fallback kullanılacak"
  info "dataseo-mcp kontrol..."
  npx -y dataseo-mcp --help >/dev/null 2>&1 || warn "dataseo-mcp yüklenemedi — dataseo_integration fallback kullanılacak"
else
  warn "npm yok — MCP provider'lar atlandı (whois/DNS + dataseo_integration çalışır)"
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  info "OpenSEO Docker başlatılıyor (port 3001)..."
  docker rm -f openseo 2>/dev/null || true
  docker run -d --name openseo -p 3001:3000 --restart unless-stopped ghcr.io/openseo/openseo:latest 2>/dev/null || \
    warn "OpenSEO image çekilemedi — dataseo_free fallback kullanılacak"
  sleep 3
  if curl -sf http://localhost:3001/api/health >/dev/null 2>&1; then
    info "OpenSEO hazır ✓ (http://localhost:3001)"
  else
    warn "OpenSEO henüz yanıt vermiyor — panel yine de dataseo_free ile çalışır"
  fi
else
  warn "Docker yok — OpenSEO atlandı (dataseo_integration fallback)"
fi

info "Backend smoke test..."
cd "$ROOT/backend"
./venv/bin/python -c "
from app.moduller.free_provider_clients import check_domain, get_backlinks, provider_health
print('health', provider_health())
print('domain', check_domain('example.com'))
bl = get_backlinks('example.com', limit=3)
print('backlinks', bl.get('provider'), len(bl.get('links',[])))
"

info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "  Namecheap / DataForSEO gerekmez"
info "  Domain: MCP → whois → DNS"
info "  Backlink: OpenSEO → DataSEO MCP → dataseo_free"
info "  Panel: Expired Domain, Backlink Hunter, Competitor Hijacker"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "Hazır"
