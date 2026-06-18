#!/bin/bash
# balkutusu.com – kategori ağacını sıfırla, profil isimlerini düzelt, index güncelle
set -euo pipefail

WP='docker exec hive_wordpress wp'
URL='https://balkutusu.com'

echo "=== 1–2) Tüm kategorileri sil ve yeniden kur ==="
for round in 1 2 3 4 5; do
  IDS=$($WP term list companion_category --field=term_id --allow-root --url="$URL" 2>/dev/null)
  [ -z "$IDS" ] && break
  for id in $IDS; do
    $WP term delete companion_category "$id" --allow-root --url="$URL" 2>/dev/null || true
  done
done

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
  $WP term create companion_category "$name" --slug="$slug" --allow-root --url="$URL" 2>/dev/null || true
done

while IFS=$'\t' read -r parent_id mslug; do
  [ "$parent_id" = "term_id" ] && continue
  for entry in "${CADDELER[@]}"; do
    cslug="${entry%%:*}"; cname="${entry##*:}"
    $WP term create companion_category "$cname" --slug="${mslug}-${cslug}" --parent="$parent_id" --allow-root --url="$URL" 2>/dev/null || true
  done
  for entry in "${HIZMETLER[@]}"; do
    hslug="${entry%%:*}"; hname="${entry##*:}"
    $WP term create companion_category "$hname" --slug="${mslug}-${hslug}" --parent="$parent_id" --allow-root --url="$URL" 2>/dev/null || true
  done
done < <($WP term list companion_category --parent=0 --fields=term_id,slug --allow-root --url="$URL")
echo "Kategori sayısı: $($WP term list companion_category --format=count --allow-root --url="$URL")"

echo "=== 3) Kategoriler sayfası ==="
PAGE_ID=$($WP post list --post_type=page --name=kategoriler --field=ID --allow-root --url="$URL" 2>/dev/null | head -1)
if [ -z "$PAGE_ID" ]; then
  $WP post create --post_type=page --post_status=publish --post_title="Kategoriler" --post_name=kategoriler --allow-root --url="$URL" --porcelain
else
  echo "Kategoriler sayfası mevcut: $PAGE_ID"
fi

echo "=== 4) Profil isimleri (rakamsız + nickname) ==="
python3 << 'PY'
import random, re, subprocess
WP = ["docker", "exec", "hive_wordpress", "wp", "--allow-root", "--url=https://balkutusu.com"]
BASE = ["Selin", "Elif", "Deniz", "Ayşe", "Merve", "Ceren", "Buse", "Ece", "Zeynep", "Pınar", "Lale", "Derya", "Ceyda", "Gamze", "Hale", "Melis", "Nazlı", "Özge", "Rana", "Tuğçe"]
NICKS = ["Sexy", "Sweet", "Angel", "Cherry", "Luna", "Bella", "Ruby", "Ivy", "Jade", "Sky", "Honey", "Velvet", "Star", "Pearl", "Coco", "Mia", "Nina", "Rosa", "Violet", "Amber"]
used = set()
r = subprocess.run(WP + ["post", "list", "--post_type=companion_profile", "--fields=ID,post_title", "--format=csv"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines()[1:]:
    if not line:
        continue
    pid, title = line.split(",", 1)
    title = title.strip('"')
    clean = re.sub(r"\d+", "", title).strip()
    clean = re.sub(r"[^a-zA-ZçğıöşüÇĞİÖŞÜ\s]", "", clean).strip()
    if not clean or len(clean) < 2:
        clean = random.choice(BASE)
    if random.random() < 0.55:
        nick = random.choice(NICKS)
        new_title = f"{nick} {clean.split()[0]}"
    else:
        new_title = clean.split()[0] if clean.split() else random.choice(BASE)
    n = 2
    base_new = new_title
    while new_title in used:
        new_title = f"{base_new}"
        n += 1
        if n > 5:
            new_title = f"{random.choice(NICKS)} {random.choice(BASE)}"
            break
    used.add(new_title)
    subprocess.run(WP + ["post", "update", pid, f"--post_title={new_title}"], capture_output=True)
    print(f"  {title} -> {new_title}")
PY

echo "=== 5) Profillere alt kategori ata ==="
TERM_IDS=$($WP term list companion_category --fields=term_id,parent --allow-root --url="$URL" --format=csv 2>/dev/null | awk -F, 'NR>1 && $2!="0" && $2!="\"0\"" {gsub(/"/,"",$1); print $1}')
PIDS=$($WP post list --post_type=companion_profile --field=ID --allow-root --url="$URL")
TARR=($TERM_IDS)
for pid in $PIDS; do
  [ ${#TARR[@]} -gt 0 ] || break
  t1=${TARR[$RANDOM % ${#TARR[@]}]}
  t2=${TARR[$RANDOM % ${#TARR[@]}]}
  $WP post term set "$pid" companion_category "$t1" "$t2" --allow-root --url="$URL" 2>/dev/null || true
done

echo "=== 6) Index güncelle ==="
$WP eval '
$urls = array(home_url("/"), home_url("/kategoriler/"), get_post_type_archive_link("companion_profile"));
$page = get_page_by_path("kategoriler");
if ($page) $urls[] = get_permalink($page);
foreach (get_terms(array("taxonomy"=>"companion_category","hide_empty"=>false)) as $t) {
  if (!preg_match("/^\d+$/", $t->name)) {
    $l = get_term_link($t);
    if (!is_wp_error($l)) $urls[] = $l;
  }
}
foreach (get_posts(array("post_type"=>"companion_profile","posts_per_page"=>-1,"post_status"=>"publish")) as $p) {
  $urls[] = get_permalink($p);
}
$urls[] = home_url("/sitemap_index.xml");
if (function_exists("hive_indexnow_ping_urls")) hive_indexnow_ping_urls($urls);
echo "pinged ".count($urls)." urls";
' --allow-root --url="$URL"

$WP rewrite flush --allow-root --url="$URL"
$WP cache flush --allow-root --url="$URL" 2>/dev/null || true
echo "=== TAMAMLANDI ==="
