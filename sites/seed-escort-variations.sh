#!/bin/bash
# Kuşadası escort varyasyon kategorileri + subdomain + rastgele ilan atama
set -euo pipefail

WP='docker exec hive_wordpress wp'
URL='https://balkutusu.com'

VARIATIONS=(
  "turk-escort:Kuşadası Türk Escort"
  "rus-escort:Kuşadası Rus Escort"
  "ukraynali-escort:Kuşadası Ukraynalı Escort"
  "moldovali-escort:Kuşadası Moldovalı Escort"
  "yabanci-escort:Kuşadası Yabancı Escort"
  "beyaz-rus-escort:Kuşadası Beyaz Rus Escort"
  "gurcu-escort:Kuşadası Gürcü Escort"
  "romen-escort:Kuşadası Romen Escort"
  "bulgar-escort:Kuşadası Bulgar Escort"
  "kazak-escort:Kuşadası Kazak Escort"
  "ingilizce-escort:Kuşadası İngilizce Escort"
  "rusca-escort:Kuşadası Rusça Escort"
  "almanca-escort:Kuşadası Almanca Escort"
  "arapca-escort:Kuşadası Arapça Escort"
  "fransizca-escort:Kuşadası Fransızca Escort"
  "vip-escort:Kuşadası VIP Escort"
  "premium-escort:Kuşadası Premium Escort"
  "luks-escort:Kuşadası Lüks Escort"
  "luxury-escort:Kuşadası Luxury Escort"
  "elite-escort:Kuşadası Elite Escort"
  "ucuz-escort:Kuşadası Ucuz Escort"
  "genc-escort:Kuşadası Genç Escort"
  "yetiskin-escort:Kuşadası Yetişkin Escort"
  "olgun-escort:Kuşadası Olgun Escort"
  "orta-yas-escort:Kuşadası Orta Yaş Escort"
  "sarisin-escort:Kuşadası Sarışın Escort"
  "esmer-escort:Kuşadası Esmer Escort"
  "kizil-escort:Kuşadası Kızıl Escort"
  "kumral-escort:Kuşadası Kumral Escort"
  "uzun-boylu-escort:Kuşadası Uzun Boylu Escort"
  "minyon-escort:Kuşadası Minyon Escort"
  "dolgun-escort:Kuşadası Dolgun Escort"
  "fit-escort:Kuşadası Fit Escort"
  "zayif-escort:Kuşadası Zayıf Escort"
  "anal-escort:Kuşadası Anal Escort"
  "oral-escort:Kuşadası Oral Escort"
  "otel-escort:Kuşadası Otel Escort"
  "plaj-escort:Kuşadası Plaj Escort"
  "gece-escort:Kuşadası Gece Escort"
  "24saat-escort:Kuşadası 24 Saat Escort"
  "masaj-escort:Kuşadası Masaj Escort"
  "cift-escort:Kuşadası Çift Escort"
  "grup-escort:Kuşadası Grup Escort"
  "eve-gelen-escort:Kuşadası Eve Gelen Escort"
  "otele-gelen-escort:Kuşadası Otele Gelen Escort"
  "jakuzili-escort:Kuşadası Jakuzili Escort"
  "fantezi-escort:Kuşadası Fantezi Escort"
  "vip-model:Kuşadası VIP Model Escort"
  "premium-model:Kuşadası Premium Model Escort"
  "kusadasi-escort:Kuşadası Escort"
  "aydin-escort:Kuşadası Aydın Escort"
  "ege-escort:Kuşadası Ege Escort"
)

echo "=== 1) Mahalle kategorilerini işaretle ==="
MAHALLE_SLUGS="kadinlar-denizi yilanciburnu guvercinada davutlar kusadasi-merkez turkmen cumhuriyet hacifeyzullah camiatik karaova guzelcamli yavansu sogucak camlik"
for mslug in $MAHALLE_SLUGS; do
  tid=$($WP term get companion_category "$mslug" --field=term_id --allow-root --url="$URL" 2>/dev/null || true)
  [ -n "$tid" ] && $WP term meta update "$tid" hive_cat_group mahalle --allow-root --url="$URL" 2>/dev/null || true
done

echo "=== 2) Escort tip kategorileri oluştur ==="
created=0
for entry in "${VARIATIONS[@]}"; do
  slug="${entry%%:*}"
  name="${entry##*:}"
  tid=$($WP term list companion_category --slug="$slug" --field=term_id --allow-root --url="$URL" 2>/dev/null | head -1)
  if [ -z "$tid" ]; then
    tid=$($WP term create companion_category "$name" --slug="$slug" --allow-root --url="$URL" --porcelain 2>/dev/null || true)
    created=$((created + 1))
  fi
  [ -n "$tid" ] && $WP term meta update "$tid" hive_cat_group escort_tip --allow-root --url="$URL" 2>/dev/null || true
done
echo "Yeni escort tip kategori: $created"

echo "=== 3) Subdomain oluştur (eksikler) ==="
subs=0
for entry in "${VARIATIONS[@]}"; do
  slug="${entry%%:*}"
  name="${entry##*:}"
  exists=$($WP site list --field=domain --allow-root --url="$URL" | grep -c "^${slug}\.balkutusu\.com$" || true)
  if [ "$exists" -eq 0 ]; then
    $WP site create --slug="$slug" --title="$name" --email=admin@balkutusu.com --allow-root 2>/dev/null && subs=$((subs + 1)) || true
  fi
done
echo "Yeni subdomain: $subs"

echo "=== 4) Tema subdomainlere ==="
$WP theme enable hive-ultra-premium --network --allow-root 2>/dev/null || true
for bid in $($WP site list --field=blog_id --allow-root --url="$URL"); do
  su=$($WP site list --field=url --blog_id="$bid" --allow-root --url="$URL" 2>/dev/null | head -1)
  [ -n "$su" ] && $WP theme activate hive-ultra-premium --url="$su" --allow-root 2>/dev/null || true
done

echo "=== 5) Rastgele ilan ata (escort tipleri + subdomain eşleşmeleri) ==="
$WP eval '
$pids = get_posts(array(
  "post_type"      => "companion_profile",
  "posts_per_page" => -1,
  "fields"         => "ids",
  "post_status"    => "publish",
));
if (!$pids) { echo "profil yok\n"; return; }

$slugs = array(
  "turk-escort","rus-escort","ukraynali-escort","moldovali-escort","yabanci-escort",
  "beyaz-rus-escort","gurcu-escort","romen-escort","bulgar-escort","kazak-escort",
  "ingilizce-escort","rusca-escort","almanca-escort","arapca-escort","fransizca-escort",
  "vip-escort","premium-escort","luks-escort","luxury-escort","elite-escort","ucuz-escort",
  "genc-escort","yetiskin-escort","olgun-escort","orta-yas-escort",
  "sarisin-escort","esmer-escort","kizil-escort","kumral-escort","uzun-boylu-escort",
  "minyon-escort","dolgun-escort","fit-escort","zayif-escort",
  "anal-escort","oral-escort","otel-escort","plaj-escort","gece-escort",
  "24saat-escort","masaj-escort","cift-escort","grup-escort",
  "eve-gelen-escort","otele-gelen-escort","jakuzili-escort","fantezi-escort",
  "vip-model","premium-model","kusadasi-escort","aydin-escort","ege-escort",
);

$assigned = 0;
foreach ($slugs as $slug) {
  $term = get_term_by("slug", $slug, "companion_category");
  if (!$term) continue;
  $shuffled = $pids;
  shuffle($shuffled);
  $n = rand(8, 14);
  foreach (array_slice($shuffled, 0, $n) as $pid) {
    wp_set_object_terms((int) $pid, (int) $term->term_id, "companion_category", true);
    $assigned++;
  }
}

$sites = get_sites(array("number" => 600));
foreach ($sites as $site) {
  if ((int) $site->blog_id === 1) continue;
  $slug = str_replace(".balkutusu.com", "", $site->domain);
  $term = get_term_by("slug", $slug, "companion_category");
  if (!$term) continue;
  $shuffled = $pids;
  shuffle($shuffled);
  $n = rand(8, 14);
  foreach (array_slice($shuffled, 0, $n) as $pid) {
    wp_set_object_terms((int) $pid, (int) $term->term_id, "companion_category", true);
    $assigned++;
  }
}
echo "ilan atama: $assigned\n";
' --allow-root --url="$URL"

$WP rewrite flush --allow-root --url="$URL"
echo "=== Bitti ==="
echo "Escort tip kategori: $($WP term list companion_category --format=count --allow-root --url=$URL)"
echo "Siteler: $($WP site list --format=count --allow-root --url=$URL)"
