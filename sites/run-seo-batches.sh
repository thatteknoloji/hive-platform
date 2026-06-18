#!/bin/bash
# Tüm kategorilere GEO SEO içerik — 500'lük batch
set -euo pipefail
cd /opt/thiqos/apps/hive/sites
BATCH=500
OFFSET=0
TOTAL=$(docker exec hive_wordpress wp term list companion_category --format=count --allow-root --url=https://balkutusu.com)
echo "Toplam kategori: $TOTAL"
while [ "$OFFSET" -lt "$TOTAL" ]; do
  echo "=== SEO offset $OFFSET ==="
  python3 generate-seo-content.py --categories-only --offset "$OFFSET" --limit-cats "$BATCH" || true
  OFFSET=$((OFFSET + BATCH))
  sleep 2
done
echo "SEO batch tamam"
