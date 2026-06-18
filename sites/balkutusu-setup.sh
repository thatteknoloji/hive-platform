#!/bin/bash
# balkutusu.com only – UI fix, images, categories, subdomains
set -euo pipefail

WP='docker exec hive_wordpress wp'
THEME='hive-ultra-premium'
IMG_SRC='/tmp/watermark-images'
IMG_IMPORTED='/tmp/watermark-imported'

echo "=== 1) Tema tüm subsite'lere aktif ==="
BLOG_IDS=$($WP site list --field=blog_id --allow-root)
for bid in $BLOG_IDS; do
  URL=$($WP site list --field=url --blog_id="$bid" --allow-root 2>/dev/null | head -1)
  $WP theme activate "$THEME" --url="$URL" --allow-root 2>/dev/null || true
done
$WP theme enable "$THEME" --network --allow-root 2>/dev/null || true
echo "Tema aktif edildi."

echo "=== 2) Breadcrumb UI düzeltmesi ==="
FUNC='/opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/functions.php'
python3 << 'PY'
from pathlib import Path
p = Path("/opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/functions.php")
text = p.read_text(encoding="utf-8")
old = """function hive_breadcrumb(){
    echo '<nav class="hive-breadcrumb" aria-label="Breadcrumb"><ol>';
    echo '<li><a href="'.esc_url(home_url('/')).'">Ana Sayfa</a></li>';
    if(is_singular('companion_profile')){
        echo '<li><a href="'.esc_url(get_post_type_archive_link('companion_profile')).'">Profiller</a></li>';
        echo '<li aria-current="page">'.get_the_title().'</li>';
    }elseif(is_tax('companion_category')){
        $term=get_queried_object();
        echo '<li aria-current="page">'.$term->name.'</li>';
    }elseif(is_post_type_archive('companion_profile')){
        echo '<li aria-current="page">Profiller</li>';
    }elseif(is_front_page()){
        echo '<li aria-current="page">Ana Sayfa</li>';
    }else{
        echo '<li aria-current="page">'.wp_title('',false).'</li>';
    }
    echo '</ol></nav>';
}"""
new = """function hive_breadcrumb(){
    if (is_front_page()) {
        return;
    }
    $parts = array();
    $parts[] = '<a href="' . esc_url(home_url('/')) . '">' . esc_html__('Ana Sayfa', 'hive-ultra-premium') . '</a>';
    if (is_singular('companion_profile')) {
        $parts[] = '<a href="' . esc_url(get_post_type_archive_link('companion_profile')) . '">' . esc_html__('Profiller', 'hive-ultra-premium') . '</a>';
        $parts[] = '<span aria-current="page">' . esc_html(get_the_title()) . '</span>';
    } elseif (is_tax('companion_category')) {
        $term = get_queried_object();
        $parts[] = '<a href="' . esc_url(get_post_type_archive_link('companion_profile')) . '">' . esc_html__('Profiller', 'hive-ultra-premium') . '</a>';
        $parts[] = '<span aria-current="page">' . esc_html($term->name) . '</span>';
    } elseif (is_post_type_archive('companion_profile')) {
        $parts[] = '<span aria-current="page">' . esc_html__('Profiller', 'hive-ultra-premium') . '</span>';
    } else {
        $parts[] = '<span aria-current="page">' . esc_html(wp_get_document_title()) . '</span>';
    }
    echo '<nav class="hive-breadcrumb" aria-label="' . esc_attr__('Konum', 'hive-ultra-premium') . '"><div class="hive-breadcrumb-track">';
    echo implode('<span class="hive-breadcrumb-sep">›</span>', $parts);
    echo '</div></nav>';
}"""
if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("breadcrumb function updated")
else:
    print("breadcrumb already updated or pattern mismatch")
PY

CSS='/opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/style.css'
if ! grep -q 'hive-breadcrumb-track' "$CSS"; then
  sed -i 's/\.hive-breadcrumb ol { list-style: none;.*/.hive-breadcrumb-track { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; font-size: 0.85rem; color: var(--color-text-muted); }/' "$CSS" || true
  cat >> "$CSS" << 'CSSEOF'

.hive-breadcrumb-track a { color: var(--color-text-muted); text-decoration: none; }
.hive-breadcrumb-track a:hover { color: var(--color-accent); }
.hive-breadcrumb-track span[aria-current="page"] { color: var(--color-accent); font-weight: 600; }
.hive-breadcrumb-sep { opacity: 0.45; user-select: none; }
CSSEOF
fi
# bump cache buster
sed -i "s/Version: .*/Version: 1.1.1/" /opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/style.css 2>/dev/null || true

echo "=== 3) Watermark görselleri import ==="
mkdir -p "$IMG_IMPORTED"
: > "$IMG_IMPORTED/map.txt"
idx=0
for f in "$IMG_SRC"/*.webp; do
  [ -f "$f" ] || continue
  idx=$((idx+1))
  MID=$($WP media import "$f" --porcelain --allow-root 2>/dev/null || true)
  if [[ "$MID" =~ ^[0-9]+$ ]]; then
    echo "$idx=$MID" >> "$IMG_IMPORTED/map.txt"
    if [ $((idx % 20)) -eq 0 ]; then echo "  $idx görsel yüklendi"; fi
  fi
done
echo "Toplam watermark: $idx"

echo "=== 4) Profillere görsel ata ==="
MAPS=$(cat "$IMG_IMPORTED/map.txt")
COUNT=$(echo "$MAPS" | grep -c '=' || true)
if [ "$COUNT" -gt 0 ]; then
  PIDS=$($WP post list --post_type=companion_profile --field=ID --allow-root)
  i=0
  for pid in $PIDS; do
    i=$((i+1))
    line=$(echo "$MAPS" | sed -n "$(( (i % COUNT) + 1 ))p")
    mid=${line#*=}
    $WP post meta update "$pid" _thumbnail_id "$mid" --allow-root >/dev/null
  done
  echo "Profil thumbnail güncellendi: $(echo "$PIDS" | wc -w)"
fi

echo "=== 5) companion_category – mahalle + hizmet ==="
declare -A MAHALLE=(
  [kadinlar-denizi]="Kadınlar Denizi"
  [yilanciburnu]="Yılancı Burnu"
  [guvercinada]="Güvercinada"
  [davutlar]="Davutlar"
  [kusadasi-merkez]="Kuşadası Merkez"
  [turkmen]="Türkmen"
  [cumhuriyet]="Cumhuriyet"
  [hacifeyzullah]="Hacıfeyzullah"
  [camiatik]="Camiatik"
  [karaova]="Karaova"
  [guzelcamli]="Güzelçamlı"
  [yavansu]="Yavansu"
  [sogucak]="Soğucak"
  [camlik]="Çamlık"
)
HIZMETLER=(
  "anal-yapan:Anal Yapan"
  "oral-yapan:Oral Yapan"
  "vip-kadinlar:VIP Kadınlar"
  "ucuz-kadinlar:Ucuz Kadınlar"
  "24-saat-hizmet:24 Saat Hizmet"
  "otele-gelen:Otele Gelen"
  "eve-gelen:Eve Gelen"
  "masaj-yapan:Masaj Yapan"
  "partner-yapan:Partner Yapan"
  "cift-kadinlar:Çift Kadınlar"
  "grup-yapanlar:Grup Yapanlar"
)
CADDELER=(
  "ataturk-caddesi:Atatürk Caddesi"
  "istiklal-caddesi:İstiklal Caddesi"
  "liman-caddesi:Liman Caddesi"
  "barbaros-caddesi:Barbaros Caddesi"
)

for slug in "${!MAHALLE[@]}"; do
  name="${MAHALLE[$slug]}"
  $WP term create companion_category "$name" --slug="$slug" --allow-root 2>/dev/null || true
done

for slug in "${!MAHALLE[@]}"; do
  parent=$($WP term get companion_category "$slug" --field=term_id --allow-root 2>/dev/null || echo "")
  [ -n "$parent" ] || continue
  for entry in "${CADDELER[@]}"; do
    cslug="${entry%%:*}"
    cname="${entry##*:}"
    fullslug="${slug}-${cslug}"
    $WP term create companion_category "$cname" --slug="$fullslug" --parent="$parent" --allow-root 2>/dev/null || true
  done
  for entry in "${HIZMETLER[@]}"; do
    hslug="${entry%%:*}"
    hname="${entry##*:}"
    fullslug="${slug}-${hslug}"
    $WP term create companion_category "$hname" --slug="$fullslug" --parent="$parent" --allow-root 2>/dev/null || true
  done
done

echo "Kategori sayısı: $($WP term list companion_category --format=count --allow-root)"

echo "=== 6) Profillere rastgele kategori ata ==="
TERM_IDS=$($WP term list companion_category --field=term_id --allow-root | grep -v '^$')
PIDS=$($WP post list --post_type=companion_profile --field=ID --allow-root)
for pid in $PIDS; do
  tid=$(echo "$TERM_IDS" | shuf | head -1)
  t2=$(echo "$TERM_IDS" | shuf | head -1)
  $WP post term set "$pid" companion_category "$tid" "$t2" --allow-root 2>/dev/null || true
done

echo "=== 7) Subdomain oluştur ==="
SUBS=(
  vip-escort premium-escort luxury-escort elite-escort
  kadinlar-denizi yilanciburnu guvercinada davutlar merkez turkmen cumhuriyet hacifeyzullah camiatik karaova guzelcamli yavansu sogucak camlik
  anal-escort oral-escort otel-escort plaj-escort gece-escort 24saat-escort masaj-escort cift-escort grup-escort
  sarisin-escort esmer-escort kizil-escort uzun-boylu-escort zayif-escort dolgun-escort fit-escort minyon-escort
  genc-escort yetiskin-escort olgun-escort orta-yas-escort
  ingilizce-escort rusca-escort almanca-escort yabanci-escort ukraynali-escort moldovali-escort
  jakuzili-escort fantezi-escort roleplay-escort jakuzi-escort plaj-escort2 gece-hayati escort-rehberi
  kusadasi-escort aydin-escort izmir-escort bodrum-escort
)

created=0
for slug in "${SUBS[@]}"; do
  exists=$($WP site list --field=domain --allow-root | grep -c "^${slug}\.balkutusu\.com$" || true)
  if [ "$exists" -eq 0 ]; then
    title=$(echo "$slug" | tr '-' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2); print}' )
    $WP site create --slug="$slug" --title="${title} Kuşadası" --email=admin@balkutusu.com --allow-root 2>/dev/null && created=$((created+1)) || true
  fi
done
echo "Yeni subdomain: $created"
echo "Toplam site: $($WP site list --format=count --allow-root)"

# Tema yeni sitelere de
for bid in $($WP site list --field=blog_id --allow-root); do
  URL=$($WP site list --field=url --blog_id="$bid" --allow-root 2>/dev/null | head -1)
  $WP theme activate "$THEME" --url="$URL" --allow-root 2>/dev/null || true
done

$WP rewrite flush --allow-root
$WP cache flush --allow-root 2>/dev/null || true

echo "=== TAMAMLANDI ==="
echo "Profiller: $($WP post list --post_type=companion_profile --format=count --allow-root)"
echo "Kategoriler: $($WP term list companion_category --format=count --allow-root)"
echo "Siteler: $($WP site list --format=count --allow-root)"
