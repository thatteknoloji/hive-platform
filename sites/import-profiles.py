#!/usr/bin/env python3
"""
Hive Ultra Premium Plus – companion_profile toplu üretici ve import aracı.

Kullanım:
  python3 import-profiles.py --generate          # JSON + CSV oluştur (85 profil)
  python3 import-profiles.py --generate --count 90
  python3 import-profiles.py --deploy          # VPS'e yükle ve WP-CLI ile import et
  python3 import-profiles.py --deploy --count 85
"""

import argparse
import csv
import json
import random
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
JSON_PATH = DATA_DIR / "profiles.json"
CSV_PATH = DATA_DIR / "profiles.csv"

NAMES = [
    "Aylin", "Ceyda", "Derya", "Elif", "Funda", "Gamze", "Hale", "Irmak",
    "Jale", "Kader", "Lale", "Melis", "Nazlı", "Özge", "Pınar", "Rana",
    "Selin", "Tuğçe", "Umay", "Vildan", "Yasemin", "Zeynep",
]

LOCATIONS = [
    "Kadınlar Denizi", "Yılancı Burnu", "Güvercinada", "Davutlar", "Merkez",
    "Türkmen", "Cumhuriyet", "Hacıfeyzullah", "Camiatik", "Karaova",
    "Güzelçamlı", "Yavansu",
]

PAYMENTS = ["Nakit", "Kredi Kartı", "Kripto"]

FEATURES_POOL = [
    "otel gelir", "eve gelir", "türkçe bilir", "yabancı uyruklu",
    "24 saat", "masaj", "partner",
]

# Picsum portrait-oriented image IDs
IMAGE_IDS = [
    64, 65, 177, 338, 399, 447, 548, 550, 582, 633, 659, 672, 836,
    1027, 1011, 1005, 996, 978, 962, 950, 921, 897, 883, 862, 839,
]

INTRO_TEMPLATES = [
    "Merhaba, ben {name}. Kuşadası'nın {location} bölgesinde sizlere özel, samimi ve güvenilir bir arkadaşlık deneyimi sunuyorum.",
    "Ben {name}, {location} çevresinde yaşayan, enerjisi yüksek ve pozitif biriyim. Birlikte geçireceğimiz zamanın unutulmaz olması için özen gösteriyorum.",
    "Selam! Adım {name}. {location} mahallesinde buluşmalar düzenliyorum; sıcakkanlı, anlayışlı ve profesyonel bir yaklaşım benim için öncelik.",
    "Kuşadası'nın en güzel köşelerinden {location}'da hizmet veren {name} olarak sizleri ağırlamaktan mutluluk duyarım.",
]

BODY_TEMPLATES = [
    "Şehrin ritmine uyum sağlayan, esnek programım sayesinde günün her saatinde randevu alabilirsiniz. İlk görüşmede rahat hissetmeniz benim için çok önemli; bu yüzden iletişime her zaman açık ve netim.",
    "Uzun süredir bu alanda deneyimliyim ve müşteri memnuniyetini her şeyin üzerinde tutuyorum. Gizliliğe saygı, hijyen ve nezaket benim için vazgeçilmez üç temel ilkedir.",
    "Seyahat eden misafirlerin yanı sıra yerel ziyaretçilere de hizmet veriyorum. İngilizce ve Türkçe iletişim kurabiliyorum; yabancı misafirler için de uygun bir profilim.",
    "Randevu öncesi kısa bir telefon görüşmesiyle beklentilerinizi dinlemeyi tercih ediyorum. Böylece buluşmamız daha verimli ve keyifli geçiyor.",
    "Kuşadası'nın gece hayatı, sahil yürüyüşleri ve sakin mekanlarında birlikte vakit geçirmekten hoşlanırım. Sizin tercihlerinize göre programı birlikte şekillendirebiliriz.",
]

CLOSING_TEMPLATES = [
    "Detaylı bilgi ve randevu için benimle iletişime geçebilirsiniz. Sizi tanımak ve güzel bir deneyim paylaşmak için sabırsızlanıyorum.",
    "Uygun ödeme seçenekleri ve esnek buluşma koşulları sunuyorum. Sorularınız için mesaj atmanız yeterli.",
    "Profilimi incelediğiniz için teşekkürler. Güvenilir, samimi ve profesyonel bir buluşma için doğru adrestesiniz.",
    "Her buluşmada özenli, saygılı ve pozitif bir atmosfer yaratmaya çalışıyorum. Görüşmek üzere!",
]

HOST = "13.140.138.135"
SSH_USER = "root"
SSH_PASS = "Fadafx35"


def random_phone() -> str:
    prefix = random.choice(["532", "533", "534", "535", "536", "537", "538", "539", "542", "543", "544", "545"])
    mid = random.randint(100, 999)
    end1 = random.randint(10, 99)
    end2 = random.randint(10, 99)
    return f"05{prefix[1:]} {mid} {end1:02d} {end2:02d}"


def random_payments() -> str:
    n = random.randint(1, 3)
    return ", ".join(random.sample(PAYMENTS, n))


def random_features() -> str:
    n = random.randint(2, 5)
    return ", ".join(random.sample(FEATURES_POOL, n))


def generate_description(name: str, location: str, age: int, features: str) -> str:
    parts = [
        random.choice(INTRO_TEMPLATES).format(name=name, location=location),
        f"{age} yaşındayım ve Kuşadası'nda aktif olarak hizmet veriyorum.",
        random.choice(BODY_TEMPLATES),
        random.choice(BODY_TEMPLATES),
        f"Sunabildiğim özellikler: {features}.",
        random.choice(CLOSING_TEMPLATES),
    ]
    text = " ".join(parts)
    words = text.split()
    # Pad to ~110-140 words if short
    while len(words) < 110:
        words.extend(random.choice(BODY_TEMPLATES).split())
    if len(words) > 150:
        words = words[:145]
        text = " ".join(words) + "..."
    else:
        text = " ".join(words)
    return text


def unique_title(name: str, used: set) -> str:
    base = name
    if base not in used:
        used.add(base)
        return base
    for suffix in ["", " VIP", " Plus", " Premium", " Elite"]:
        candidate = f"{name}{suffix}".strip()
        if candidate not in used:
            used.add(candidate)
            return candidate
    i = 2
    while f"{name} {i}" in used:
        i += 1
    title = f"{name} {i}"
    used.add(title)
    return title


def generate_profiles(count: int) -> list:
    random.seed(42)
    used_titles = set()
    profiles = []

    for i in range(count):
        name = random.choice(NAMES)
        title = unique_title(name, used_titles)
        age = random.randint(20, 35)
        location = random.choice(LOCATIONS)
        price = random.randint(10, 50) * 100  # 1000-5000
        phone = random_phone()
        payments = random_payments()
        features = random_features()
        image_id = IMAGE_IDS[i % len(IMAGE_IDS)]
        image_url = f"https://picsum.photos/id/{image_id}/400/600"
        vip = "1" if random.random() < 0.22 else "0"

        profiles.append({
            "title": title,
            "yas": str(age),
            "lokasyon": f"Kuşadası, {location}",
            "fiyat": str(price),
            "telefon": phone,
            "odeme_sekli": payments,
            "ozellikler": features,
            "vip": vip,
            "image_url": image_url,
            "image_id": image_id,
            "content": generate_description(title.split()[0], location, age, features),
        })

    return profiles


def save_outputs(profiles: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    fieldnames = [
        "title", "yas", "lokasyon", "fiyat", "telefon",
        "odeme_sekli", "ozellikler", "vip", "image_url", "content",
    ]
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(profiles)

    print(f"✓ {len(profiles)} profil → {JSON_PATH}")
    print(f"✓ CSV → {CSV_PATH}")


def ssh_run(cmd: str, timeout: int = 600) -> str:
    try:
        import pexpect
    except ImportError:
        print("pexpect gerekli: pip install pexpect", file=sys.stderr)
        sys.exit(1)

    child = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no {SSH_USER}@{HOST} {repr(cmd)}",
        timeout=timeout,
        encoding="utf-8",
    )
    idx = child.expect(["password:", pexpect.EOF, pexpect.TIMEOUT], timeout=45)
    if idx == 0:
        child.sendline(SSH_PASS)
        child.expect(pexpect.EOF, timeout=timeout)
    return child.before or ""


def scp_upload(local: Path, remote: str) -> None:
    import pexpect
    child = pexpect.spawn(
        f"scp -o StrictHostKeyChecking=no {local} {SSH_USER}@{HOST}:{remote}",
        timeout=120,
        encoding="utf-8",
    )
    child.expect("password:")
    child.sendline(SSH_PASS)
    child.expect(pexpect.EOF)


def deploy(profiles: list) -> None:
    save_outputs(profiles)
    scp_upload(JSON_PATH, "/tmp/profiles.json")

    # Download unique images on VPS
    unique_ids = sorted({p["image_id"] for p in profiles})
    ids_str = " ".join(str(i) for i in unique_ids)

    setup = f"""
set -e
mkdir -p /tmp/profile-images /tmp/profile-import
cd /tmp/profile-images
for id in {ids_str}; do
  [ -f "p$id.jpg" ] || curl -sL -o "p$id.jpg" "https://picsum.photos/id/$id/400/600" || wget -q -O "p$id.jpg" "https://picsum.photos/id/$id/400/600"
done
ls /tmp/profile-images | wc -l
echo "Images ready"
"""
    print(ssh_run(setup, timeout=300))

    # Build import shell script on VPS
    import_script = r'''#!/bin/bash
set -e
JSON=/tmp/profiles.json
IMGDIR=/tmp/profile-images
declare -A MEDIA_MAP

echo "=== Medya import ==="
for f in "$IMGDIR"/p*.jpg; do
  [ -f "$f" ] || continue
  id=$(basename "$f" .jpg | sed 's/p//')
  MID=$(docker exec hive_wordpress wp media import "$f" --porcelain --allow-root 2>/dev/null || true)
  if [ -n "$MID" ] && [ "$MID" -gt 0 ] 2>/dev/null; then
    MEDIA_MAP[$id]=$MID
    echo "Media $id -> $MID"
  fi
done

echo "=== Profil import ==="
COUNT=0
python3 << 'PYIMPORT'
import json, subprocess, shlex, os

with open("/tmp/profiles.json", encoding="utf-8") as f:
    profiles = json.load(f)

media_map = {}
# Parse MEDIA_MAP from env file written by bash
map_file = "/tmp/media_map.txt"
if os.path.exists(map_file):
    for line in open(map_file):
        parts = line.strip().split("=")
        if len(parts) == 2:
            media_map[parts[0]] = parts[1]

created = 0
for p in profiles:
    title = p["title"].replace("'", "'\\''")
    content = p["content"].replace("'", "'\\''")
    cmd = f"""docker exec hive_wordpress wp post create \
      --post_type=companion_profile \
      --post_title='{title}' \
      --post_status=publish \
      --post_content='{content}' \
      --porcelain --allow-root"""
    pid = subprocess.check_output(cmd, shell=True, text=True).strip()
    if not pid.isdigit():
        print(f"SKIP {title}: {pid}")
        continue
    for key in ["yas","lokasyon","fiyat","telefon","odeme_sekli","ozellikler","vip"]:
        val = p.get(key, "").replace("'", "'\\''")
        subprocess.run(f"docker exec hive_wordpress wp post meta update {pid} {key} '{val}' --allow-root", shell=True)
    img_id = str(p.get("image_id", ""))
    mid = media_map.get(img_id)
    if mid:
        subprocess.run(f"docker exec hive_wordpress wp post meta update {pid} _thumbnail_id {mid} --allow-root", shell=True)
    created += 1
    if created % 10 == 0:
        print(f"  {created} profil oluşturuldu...")
print(f"DONE: {created} profil")
PYIMPORT
'''

    # Simpler approach: pure bash loop reading JSON with python one-liner per profile
    # Rewrite deploy to use a self-contained remote script file

    remote_py = '''
import json, subprocess, random

with open("/tmp/profiles.json", encoding="utf-8") as f:
    profiles = json.load(f)

# Import images first
media = {}
import os, glob
for path in sorted(glob.glob("/tmp/profile-images/p*.jpg")):
    img_key = os.path.basename(path).replace("p","").replace(".jpg","")
    r = subprocess.run(
        ["docker", "exec", "hive_wordpress", "wp", "media", "import", path, "--porcelain", "--allow-root"],
        capture_output=True, text=True
    )
    mid = r.stdout.strip()
    if mid.isdigit():
        media[img_key] = mid
        print(f"media {img_key} -> {mid}")

created = 0
for p in profiles:
    r = subprocess.run(
        ["docker", "exec", "hive_wordpress", "wp", "post", "create",
         "--post_type=companion_profile",
         "--post_title=" + p["title"],
         "--post_status=publish",
         "--post_content=" + p["content"],
         "--porcelain", "--allow-root"],
        capture_output=True, text=True
    )
    pid = r.stdout.strip()
    if not pid.isdigit():
        print("ERR", p["title"], r.stderr)
        continue
    for key in ["yas","lokasyon","fiyat","telefon","odeme_sekli","ozellikler","vip"]:
        subprocess.run(
            ["docker", "exec", "hive_wordpress", "wp", "post", "meta", "update", pid, key, p.get(key,""), "--allow-root"],
            capture_output=True
        )
    mid = media.get(str(p.get("image_id","")))
    if mid:
        subprocess.run(
            ["docker", "exec", "hive_wordpress", "wp", "post", "meta", "update", pid, "_thumbnail_id", mid, "--allow-root"],
            capture_output=True
        )
    created += 1
    if created % 10 == 0:
        print(f"{created}...")
print(f"TOTAL: {created}")
'''

    remote_py_path = DATA_DIR / "remote_import.py"
    remote_py_path.write_text(remote_py, encoding="utf-8")
    scp_upload(remote_py_path, "/tmp/remote_import.py")

    result = ssh_run(
        f"python3 /tmp/remote_import.py 2>&1",
        timeout=600,
    )
    print(result)

    count_check = ssh_run(
        "docker exec hive_wordpress wp post list --post_type=companion_profile --format=count --allow-root"
    )
    print(f"\nToplam profil sayısı: {count_check.strip()}")

    # Placeholder in theme
    ssh_run(
        "mkdir -p /opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/assets/images && "
        "curl -sL -o /opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/assets/images/placeholder-woman.jpg "
        "'https://picsum.photos/id/64/400/600' 2>/dev/null || true"
    )
    print("✓ Deploy tamamlandı")


def main():
    parser = argparse.ArgumentParser(description="Companion profile generator & importer")
    parser.add_argument("--generate", action="store_true", help="JSON/CSV oluştur")
    parser.add_argument("--deploy", action="store_true", help="VPS'e import et")
    parser.add_argument("--count", type=int, default=85, help="Profil sayısı (80-90)")
    args = parser.parse_args()

    if not args.generate and not args.deploy:
        args.generate = True

    count = max(80, min(90, args.count))
    profiles = generate_profiles(count)

    if args.generate:
        save_outputs(profiles)

    if args.deploy:
        deploy(profiles)


if __name__ == "__main__":
    main()
