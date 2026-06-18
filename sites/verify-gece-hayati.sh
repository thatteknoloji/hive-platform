#!/bin/bash
# 180 gece hayatı rehberi kanıtı
URL="${WP_URL:-https://balkutusu.com}"
echo "=== Gece Hayatı Rehber Sayısı ==="
TOTAL=$(curl -sk "${URL}/wp-json/wp/v2/gece_hayati?per_page=1" -D - -o /dev/null 2>/dev/null | grep -i x-wp-total | awk '{print $2}' | tr -d '\r')
echo "Toplam: ${TOTAL:-?}"
echo ""
echo "=== İlk 5 örnek ==="
curl -sk "${URL}/wp-json/wp/v2/gece_hayati?per_page=5&_fields=id,slug,link,title" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    print(p['id'], p['slug'], p['link'])
"
echo ""
echo "=== Arşiv ==="
echo "${URL}/gece-hayati/"
