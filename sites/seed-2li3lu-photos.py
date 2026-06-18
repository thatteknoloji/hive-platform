#!/usr/bin/env python3
"""
2li3lu klasöründeki 100 fotoğrafı WordPress'e yükle:
- 50 → 2'li arkadaş profilleri (cift kategorileri)
- 50 → 3'lü arkadaş profilleri (grup/üçlü kategorileri)
- Tüm balkutusu görsellerini thumbnailsiz profillere ata (Tinder swipe havuzu)

VPS'te çalıştır: python3 seed-2li3lu-photos.py
"""
from __future__ import annotations

import base64
import json
import random
import subprocess
import sys
from pathlib import Path

WP = ["docker", "exec", "hive_wordpress", "wp", "--allow-root", "--url=https://balkutusu.com"]
HOST_IMG_DIR = Path("/opt/thiqos/apps/hive/sites/wp-content/uploads/2li3lu-import")
# wp media import docker içinden çalışır — container yolu gerekli
CONTAINER_IMG_DIR = "/var/www/html/wp-content/uploads/2li3lu-import"

NAMES = [
    "Aylin", "Selin", "Elif", "Ceren", "Derya", "Melis", "Buse", "Ece", "Gamze", "Hale",
    "Lale", "Nazlı", "Özge", "Pınar", "Rana", "Tuğçe", "Vildan", "Zeynep", "Ceyda", "Funda",
]
NICKS = ["Ruby", "Luna", "Honey", "Bella", "Cherry", "Velvet", "Pearl", "Star", "Amber", "Jade"]
MAHALLE = [
    "kadinlar-denizi", "yilanciburnu", "guvercinada", "davutlar", "kusadasi-merkez",
    "turkmen", "cumhuriyet", "hacifeyzullah", "camiatik", "karaova", "guzelcamli", "yavansu",
]
LOCATIONS = {
    "kadinlar-denizi": "Kuşadası, Kadınlar Denizi",
    "yilanciburnu": "Kuşadası, Yılancı Burnu",
    "guvercinada": "Kuşadası, Güvercinada",
    "davutlar": "Kuşadası, Davutlar",
    "kusadasi-merkez": "Kuşadası Merkez",
    "turkmen": "Kuşadası, Türkmen",
    "cumhuriyet": "Kuşadası, Cumhuriyet",
    "hacifeyzullah": "Kuşadası, Hacıfeyzullah",
    "camiatik": "Kuşadası, Camiatik",
    "karaova": "Kuşadası, Karaova",
    "guzelcamli": "Kuşadası, Güzelçamlı",
    "yavansu": "Kuşadası, Yavansu",
}


def wp(args: list[str]) -> str:
    r = subprocess.run(WP + args, capture_output=True, text=True)
    if r.returncode != 0 and r.stderr:
        print(r.stderr.strip(), file=sys.stderr)
    return (r.stdout or "").strip()


def wp_eval(php: str) -> str:
    r = subprocess.run(WP + ["eval", php], capture_output=True, text=True)
    return (r.stdout or "").strip()


def import_media(filename: str) -> int | None:
    path = f"{CONTAINER_IMG_DIR}/{filename}"
    mid = wp(["media", "import", path, "--porcelain"])
    if mid.isdigit():
        return int(mid)
    return None


def duo_title() -> str:
    a, b = random.sample(NAMES, 2)
    if random.random() < 0.6:
        return f"{random.choice(NICKS)} {a} & {b}"
    return f"{a} & {b}"


def trio_title() -> str:
    a, b, c = random.sample(NAMES, 3)
    if random.random() < 0.6:
        return f"{random.choice(NICKS)} {a}, {b} & {c}"
    return f"{a}, {b} & {c}"


def create_profile(
    title: str,
    media_id: int,
    mahalle: str,
    group: str,
    ozellikler: str,
) -> int | None:
    """group: 'duo' | 'trio'"""
    lokasyon = LOCATIONS.get(mahalle, "Kuşadası")
    yas = str(random.randint(20, 32))
    fiyat = str(random.randint(1800, 4500))
    telefon = f"05{random.randint(30, 59)} {random.randint(100, 999)} {random.randint(10, 99):02d} {random.randint(10, 99):02d}"

    if group == "duo":
        cat_slugs = [f"{mahalle}-cift-kadinlar", "cift-escort"]
        hizmetler = ["cift", "partner"]
    else:
        cat_slugs = [f"{mahalle}-grup-yapanlar", "grup-escort"]
        hizmetler = ["grup", "partner"]

    desc = (
        f"{title} — Kuşadası'nda birlikte hizmet veren özel arkadaşlık profili. "
        f"{lokasyon} bölgesinde buluşma imkânı. Gizlilik ve hijyen önceliğimizdir. "
        f"Detaylar için iletişime geçin."
    )

    pid = wp([
        "post", "create",
        "--post_type=companion_profile",
        "--post_status=publish",
        f"--post_title={title}",
        f"--post_content={desc}",
        "--porcelain",
    ])
    if not pid.isdigit():
        return None

    pid_i = int(pid)
    wp(["post", "meta", "update", str(pid_i), "yas", yas])
    wp(["post", "meta", "update", str(pid_i), "lokasyon", lokasyon])
    wp(["post", "meta", "update", str(pid_i), "fiyat", fiyat])
    wp(["post", "meta", "update", str(pid_i), "telefon", telefon])
    wp(["post", "meta", "update", str(pid_i), "ozellikler", ozellikler])
    wp(["post", "meta", "update", str(pid_i), "_thumbnail_id", str(media_id)])
    wp(["post", "meta", "update", str(pid_i), "vip", "0"])

    # hizmetler (serialized array)
    php = f"""
update_post_meta({pid_i}, 'hizmetler', array({",".join(f"'{h}'" for h in hizmetler)}));
$slugs = {json.dumps(cat_slugs, ensure_ascii=False)};
$tids = array();
foreach ($slugs as $slug) {{
  $t = get_term_by('slug', $slug, 'companion_category');
  if ($t && !is_wp_error($t)) $tids[] = (int)$t->term_id;
}}
if ($tids) wp_set_object_terms({pid_i}, $tids, 'companion_category', true);
echo 'ok';
"""
    wp_eval(php)
    return pid_i


def sync_orphan_images_to_profiles() -> None:
    """Tüm balkutusu görsellerini thumbnailsiz profillere ata (swipe havuzu)."""
    php = r"""
$attachments = get_posts(array(
  'post_type'      => 'attachment',
  'post_mime_type' => 'image',
  'posts_per_page' => -1,
  'post_status'    => 'inherit',
  'fields'         => 'ids',
));
$used = array();
foreach ($attachments as $aid) {
  $q = new WP_Query(array(
    'post_type'  => 'companion_profile',
    'meta_key'   => '_thumbnail_id',
    'meta_value' => (string)$aid,
    'fields'     => 'ids',
    'posts_per_page' => 1,
  ));
  if ($q->have_posts()) $used[(int)$aid] = true;
}
$free_media = array();
foreach ($attachments as $aid) {
  if (!isset($used[(int)$aid])) $free_media[] = (int)$aid;
}
$no_thumb = get_posts(array(
  'post_type'      => 'companion_profile',
  'posts_per_page' => -1,
  'fields'         => 'ids',
  'post_status'    => 'publish',
  'meta_query'     => array(
    'relation' => 'OR',
    array('key' => '_thumbnail_id', 'compare' => 'NOT EXISTS'),
    array('key' => '_thumbnail_id', 'value' => '', 'compare' => '='),
    array('key' => '_thumbnail_id', 'value' => '0', 'compare' => '='),
  ),
));
$assigned = 0;
$mi = 0;
$mc = count($free_media);
foreach ($no_thumb as $pid) {
  if ($mc === 0) break;
  $mid = $free_media[$mi % $mc];
  update_post_meta((int)$pid, '_thumbnail_id', $mid);
  $assigned++;
  $mi++;
}
$created_swipe = 0;
$names = array('Selin','Elif','Aylin','Ceren','Derya','Melis','Lale','Nazlı','Pınar','Zeynep');
while ($mi < $mc) {
  $mid = $free_media[$mi];
  $n1 = $names[array_rand($names)];
  $title = 'Ruby ' . $n1;
  $pid = wp_insert_post(array(
    'post_type' => 'companion_profile',
    'post_status' => 'publish',
    'post_title' => $title,
    'post_content' => 'Kuşadası escort profili.',
  ));
  if ($pid && !is_wp_error($pid)) {
    update_post_meta($pid, '_thumbnail_id', $mid);
    update_post_meta($pid, 'lokasyon', 'Kuşadası');
    update_post_meta($pid, 'yas', (string)rand(21,29));
    update_post_meta($pid, 'fiyat', (string)rand(1500,3500));
    $created_swipe++;
  }
  $mi++;
}
echo "orphan_media:$mc no_thumb:".count($no_thumb)." assigned:$assigned created_swipe:$created_swipe";
"""
    print("sync:", wp_eval(php), flush=True)


def main() -> int:
    if not HOST_IMG_DIR.is_dir():
        print(f"Klasör yok: {HOST_IMG_DIR}", file=sys.stderr)
        return 1

    files = sorted(HOST_IMG_DIR.glob("*.webp"))
    if not files:
        print("Görsel bulunamadı", file=sys.stderr)
        return 1

    print(f"Toplam görsel: {len(files)}", flush=True)
    duo_count = len(files) // 2
    trio_count = len(files) - duo_count

    created = 0
    for i, fpath in enumerate(files):
        mid = import_media(fpath.name)
        if not mid:
            print(f"  import fail: {fpath.name}", flush=True)
            continue

        mahalle = random.choice(MAHALLE)
        if i < duo_count:
            title = duo_title()
            oz = "çift, partner, otel gelir"
            pid = create_profile(title, mid, mahalle, "duo", oz)
        else:
            title = trio_title()
            oz = "grup, partner, 24 saat"
            pid = create_profile(title, mid, mahalle, "trio", oz)

        if pid:
            created += 1
            if created % 10 == 0:
                print(f"  {created} profil oluşturuldu…", flush=True)

    print(f"duo:{duo_count} trio:{trio_count} created:{created}", flush=True)
    sync_orphan_images_to_profiles()
    wp(["cache", "flush"])
    total = wp(["post", "list", "--post_type=companion_profile", "--format=count"])
    print(f"toplam profil: {total}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
