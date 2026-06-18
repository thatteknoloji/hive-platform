#!/bin/bash
# Balkutusu.com — tema dosyalarını canlıya gönder (HIVE panel hariç)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
THEME_LOCAL="$ROOT/sites/wp-content/themes/hive-ultra-premium"
REMOTE="root@13.140.138.135"
REMOTE_THEME="/opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium"
PASS="${VPS_SSH_PASS:-Fadafx35}"

if [ ! -d "$THEME_LOCAL" ]; then
  echo "Tema klasörü yok: $THEME_LOCAL"
  exit 1
fi

echo "🚀 Tema canlıya gönderiliyor → balkutusu.com"

if ! command -v sshpass &>/dev/null; then
  echo "sshpass yok — brew install sshpass veya manuel scp kullan"
  exit 1
fi

sshpass -p "$PASS" rsync -avz --delete \
  -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
  "$THEME_LOCAL/" \
  "$REMOTE:$REMOTE_THEME/"

echo "✅ Tema dosyaları kopyalandı"

sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$REMOTE" bash << 'EOF'
set -e
if docker ps --format '{{.Names}}' | grep -q hive_wordpress; then
  docker exec hive_wordpress wp cache flush --allow-root 2>/dev/null || true
  echo "✅ WP cache temizlendi"
else
  echo "ℹ️  hive_wordpress container yok — dosyalar kopyalandı"
fi
EOF

echo "🌐 Canlı site: https://www.balkutusu.com"
