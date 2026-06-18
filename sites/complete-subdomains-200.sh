#!/bin/bash
# balkutusu.com – subdomain sayısını en az 200'e tamamla + tema + ana site link widget
set -euo pipefail

WP='docker exec hive_wordpress wp'
TARGET=200
THEME='hive-ultra-premium'
MAIN='https://balkutusu.com'

echo "=== Mevcut site sayısı ==="
TOTAL=$($WP site list --format=count --allow-root)
SUBS=$((TOTAL - 1))
echo "Toplam: $TOTAL (subdomain: $SUBS)"

if [ "$SUBS" -ge "$TARGET" ]; then
  echo "Hedef zaten karşılandı: $SUBS >= $TARGET subdomain"
else
  NEED=$((TARGET - SUBS))
  echo "Oluşturulacak: $NEED subdomain"
  i=1
  created=0
  while [ "$created" -lt "$NEED" ]; do
    slug="portal-${i}"
    exists=$($WP site list --field=domain --allow-root | grep -c "^${slug}\.balkutusu\.com$" || true)
    if [ "$exists" -eq 0 ]; then
      title=$(echo "$slug" | tr '-' ' ' | awk '{for(j=1;j<=NF;j++) $j=toupper(substr($j,1,1)) substr($j,2); print}')
      $WP site create --slug="$slug" --title="${title} Kuşadası" --email=admin@balkutusu.com --allow-root 2>/dev/null && created=$((created+1)) && echo "  + $slug.balkutusu.com"
    fi
    i=$((i + 1))
    [ "$i" -gt 500 ] && break
  done
  echo "Yeni oluşturulan: $created"
fi

echo "=== Tema tüm sitelere ==="
for bid in $($WP site list --field=blog_id --allow-root); do
  URL=$($WP site list --field=url --blog_id="$bid" --allow-root 2>/dev/null | head -1)
  [ -n "$URL" ] && $WP theme activate "$THEME" --url="$URL" --allow-root 2>/dev/null || true
done
$WP theme enable "$THEME" --network --allow-root 2>/dev/null || true

if [ "${SKIP_PORTAL_PAGES:-0}" != "1" ]; then
  echo "=== Subdomain ana-portal sayfası (ilk 30 site, hızlı) ==="
  n=0
  for bid in $($WP site list --field=blog_id --allow-root); do
    [ "$bid" = "1" ] && continue
    [ "$n" -ge 30 ] && break
    URL=$($WP site list --field=url --blog_id="$bid" --allow-root 2>/dev/null | head -1)
    [ -z "$URL" ] && continue
    SLUG=$($WP site list --field=domain --blog_id="$bid" --allow-root 2>/dev/null | sed 's/\.balkutusu\.com$//')
    CONTENT="<p><strong>${SLUG} Kuşadası Escort</strong></p><p>Ana portal: <a href=\"${MAIN}\"><strong>balkutusu.com</strong></a></p><p><a href=\"${MAIN}\">Bal Kutusu Ana Siteye Git</a></p>"
    PAGE_ID=$($WP post list --post_type=page --name=ana-portal --field=ID --url="$URL" --allow-root 2>/dev/null | head -1)
    if [ -z "$PAGE_ID" ]; then
      $WP post create --post_type=page --post_status=publish --post_title="Ana Portal" --post_name=ana-portal --post_content="$CONTENT" --url="$URL" --allow-root >/dev/null 2>&1 || true
    fi
    n=$((n + 1))
  done
  echo "Ana-portal sayfası: $n site"
fi

$WP rewrite flush --allow-root 2>/dev/null || true
echo "=== Bitti ==="
echo "Siteler: $($WP site list --format=count --allow-root)"
