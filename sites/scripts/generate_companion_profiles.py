#!/usr/bin/env python3
"""
Generate companion_profile data (JSON + CSV) and optionally import to WordPress via SSH/WP-CLI.

Usage:
  python3 generate_companion_profiles.py --count 85 --output-dir ../data
  python3 generate_companion_profiles.py --count 85 --import --host 13.140.138.135
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import subprocess
import sys
import textwrap
from pathlib import Path

NAMES = [
    "Aylin", "Ceyda", "Derya", "Elif", "Funda", "Gamze", "Hale", "Irmak", "Jale",
    "Kader", "Lale", "Melis", "Nazlı", "Özge", "Pınar", "Rana", "Selin", "Tuğçe",
    "Umay", "Vildan", "Yasemin", "Zeynep",
]

LOCATIONS = [
    "Kadınlar Denizi", "Yılancı Burnu", "Güvercinada", "Davutlar", "Merkez",
    "Türkmen", "Cumhuriyet", "Hacıfeyzullah", "Camiatik", "Karaova",
    "Güzelçamlı", "Yavansu",
]

PAYMENT_OPTIONS = ["Nakit", "Kredi Kartı", "Kripto"]

FEATURES_POOL = [
    "otel gelir", "eve gelir", "türkçe bilir", "yabancı uyruklu",
    "24 saat", "masaj", "partner",
]

# Picsum portrait-friendly IDs (placeholder until real stock photos)
IMAGE_URLS = [
    f"https://picsum.photos/id/{pid}/400/600"
    for pid in [64, 65, 66, 101, 177, 338, 399, 433, 447, 453, 475, 536, 548, 550, 582, 593, 597, 638, 659, 675]
]

INTRO_LINES = [
    "Kuşadası'nın enerjisini seven, sıcakkanlı ve güler yüzlü biriyim.",
    "Yeni insanlarla tanışmayı, samimi sohbetleri ve keyifli anları paylaşmayı seviyorum.",
    "Profesyonel, özenli ve güven veren bir yaklaşımla hizmet veriyorum.",
    "Şehrin en güzel köşelerinde birlikte vakit geçirmek için sabırsızlanıyorum.",
    "İletişim gücüm yüksek; karşımdakini dinlemeyi ve iyi hissettirmeyi önemsiyorum.",
    "Zarif, bakımlı ve pozitif enerjisiyle öne çıkan bir profil sunuyorum.",
    "Kuşadası'nda uzun süredir bulunuyorum; bölgeyi ve yaşam ritmini çok iyi biliyorum.",
    "Her buluşmada özel hissettirmek ve kaliteli zaman geçirmek benim için öncelik.",
]

DETAIL_LINES = [
    "Sohbet, gezinti, akşam yemeği veya sakin bir kahve molası gibi planları birlikte şekillendirebiliriz.",
    "Randevularımı düzenli ve planlı yürütürüm; zamanına saygı benim için çok önemlidir.",
    "İngilizce ve Türkçe iletişim kurabiliyorum; misafirlerimle rahat bir ortam oluşturuyorum.",
    "Otel veya merkezi buluşma noktalarında görüşmeyi tercih edebilirim; detayları önceden netleştiririz.",
    "Güleryüzlü tavrım ve nezaketim sayesinde kısa sürede güven veren bir atmosfer kurarım.",
    "Kuşadası'nın sahil şeridi, marina ve merkez noktalarında keyifli rotalar önerebilirim.",
    "Özel isteklere açığım; beklentilerinizi dinleyip uygun bir program öneririm.",
    "Sakin, enerjik veya romantik bir akşam — ne arıyorsanız birlikte planlayabiliriz.",
]

CLOSING_LINES = [
    "Benimle iletişime geçerek uygun saat ve buluşma detaylarını kolayca ayarlayabilirsiniz.",
    "Profilimi incelediyseniz bir mesaj bırakmanız yeterli; kısa sürede dönüş yaparım.",
    "Kaliteli ve saygılı bir deneyim arıyorsanız doğru yerdesiniz.",
    "Kuşadası'nda unutulmaz bir arkadaşlık deneyimi için sabırsızlanıyorum.",
    "Güven, gizlilik ve samimiyet benim için her zaman ön plandadır.",
]


def random_phone() -> str:
    operator = random.choice([
        "532", "533", "534", "535", "536", "537", "538", "539",
        "541", "542", "543", "544", "545", "546", "551", "552", "553", "554", "555", "556",
    ])
    a = random.randint(100, 999)
    b = random.randint(10, 99)
    c = random.randint(10, 99)
    return f"0{operator} {a} {b:02d} {c:02d}"


def build_description(name: str, location: str, features: list[str]) -> str:
    parts = [
        random.choice(INTRO_LINES),
        f"Ben {name}, Kuşadası {location} bölgesinde aktif olarak hizmet veriyorum.",
        random.choice(DETAIL_LINES),
    ]
    if features:
        feat_text = ", ".join(features[:4])
        parts.append(f"Sunabildiğim özellikler arasında {feat_text} yer alıyor.")
    parts.append(random.choice(DETAIL_LINES))
    parts.append(random.choice(CLOSING_LINES))
    text = " ".join(parts)
    words = text.split()
    # Pad to ~100-150 words
    while len(words) < 100:
        words.extend(random.choice(DETAIL_LINES).split())
    if len(words) > 150:
        words = words[:150]
    return " ".join(words)


def generate_profiles(count: int, seed: int | None = 42) -> list[dict]:
    if seed is not None:
        random.seed(seed)

    profiles = []
    used_titles: set[str] = set()

    for i in range(count):
        base_name = random.choice(NAMES)
        location = random.choice(LOCATIONS)
        title = base_name
        n = 2
        while title in used_titles:
            title = f"{base_name} {n}"
            n += 1
        used_titles.add(title)

        age = random.randint(20, 35)
        price = random.randint(1000, 5000)
        # Round to nearest 50
        price = round(price / 50) * 50

        payments = random.sample(PAYMENT_OPTIONS, k=random.randint(1, 3))
        feat_count = random.randint(2, 5)
        features = random.sample(FEATURES_POOL, k=feat_count)

        profile = {
            "title": title,
            "yas": str(age),
            "lokasyon": f"Kuşadası, {location}",
            "fiyat": str(price),
            "telefon": random_phone(),
            "odeme_sekli": ", ".join(payments),
            "ozellikler": ", ".join(features),
            "vip": "1" if random.random() < 0.25 else "0",
            "image_url": IMAGE_URLS[i % len(IMAGE_URLS)],
            "content": build_description(base_name, location, features),
            "category": random.choice(["VIP", "Yeni", "Popüler", "Merkez"]),
        }
        profiles.append(profile)

    return profiles


def save_json(profiles: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def save_csv(profiles: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "title", "yas", "lokasyon", "fiyat", "telefon",
        "odeme_sekli", "ozellikler", "vip", "image_url", "content", "category",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(profiles)


def shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def import_via_ssh(profiles: list[dict], host: str, user: str, password: str) -> None:
    try:
        import pexpect
    except ImportError:
        print("pexpect required for SSH import: pip install pexpect", file=sys.stderr)
        sys.exit(1)

    remote_json = "/tmp/companion_profiles_import.json"
    local_json = Path(__file__).resolve().parent.parent / "data" / "companion_profiles.json"
    save_json(profiles, local_json)

    # Upload JSON via scp
    child = pexpect.spawn(
        f"scp -o StrictHostKeyChecking=no {local_json} {user}@{host}:{remote_json}",
        timeout=120,
        encoding="utf-8",
    )
    idx = child.expect(["password:", pexpect.EOF], timeout=60)
    if idx == 0:
        child.sendline(password)
        child.expect(pexpect.EOF, timeout=120)

    import_script = r'''#!/bin/bash
set -e
JSON=/tmp/companion_profiles_import.json
COUNT=$(python3 -c "import json; print(len(json.load(open('$JSON'))))")
echo "Importing $COUNT profiles..."

# Ensure categories
for cat in VIP Yeni Popüler Merkez; do
  docker exec hive_wordpress wp term create companion_category "$cat" --allow-root 2>/dev/null || true
done

# Placeholder image
mkdir -p /opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/assets/images
if [ ! -f /opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/assets/images/placeholder-woman.jpg ]; then
  curl -fsSL -o /opt/thiqos/apps/hive/sites/wp-content/themes/hive-ultra-premium/assets/images/placeholder-woman.jpg \
    "https://picsum.photos/id/64/400/600" || true
fi

python3 << 'PY'
import json, subprocess, shlex, time

def wp(*args):
    cmd = ["docker", "exec", "hive_wordpress", "wp"] + list(args) + ["--allow-root"]
    return subprocess.run(cmd, capture_output=True, text=True)

def wp_out(*args):
    r = wp(*args)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)
    return (r.stdout or "").strip()

data = json.load(open("/tmp/companion_profiles_import.json"))
ok = 0
fail = 0

for i, p in enumerate(data):
    title = p["title"]
    content = p["content"]
    try:
        pid = wp_out("post", "create",
            f"--post_type=companion_profile",
            f"--post_title={title}",
            f"--post_status=publish",
            f"--post_content={content}",
            "--porcelain")
        meta = {
            "yas": p["yas"], "lokasyon": p["lokasyon"], "fiyat": p["fiyat"],
            "telefon": p["telefon"], "odeme_sekli": p["odeme_sekli"],
            "ozellikler": p["ozellikler"], "vip": p.get("vip", "0"),
            "image_url": p.get("image_url", ""),
        }
        for k, v in meta.items():
            wp("post", "meta", "update", pid, k, str(v))

        # Category
        cat = p.get("category", "Yeni")
        wp("post", "term", "set", pid, "companion_category", cat)

        # Featured image from URL
        img = p.get("image_url", "")
        if img:
            r = wp("media", "import", img, f"--post_id={pid}", "--featured_image")
            if r.returncode != 0:
                wp("post", "meta", "update", pid, "image_url", img)

        ok += 1
        if (i + 1) % 10 == 0:
            print(f"  ... {i+1}/{len(data)} imported")
        time.sleep(0.3)
    except Exception as e:
        fail += 1
        print(f"FAIL {title}: {e}")

print(f"DONE: {ok} ok, {fail} failed")
wp_out("cache", "flush")
wp_out("rewrite", "flush")
total = wp_out("post", "list", "--post_type=companion_profile", "--format=count")
print(f"Total profiles in DB: {total}")
PY
'''

    child2 = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no {user}@{host} bash",
        timeout=600,
        encoding="utf-8",
    )
    child2.expect(["password:", pexpect.EOF], timeout=30)
    if child2.after and "password" in str(child2.after):
        child2.sendline(password)
    child2.sendline(import_script)
    child2.expect(pexpect.EOF, timeout=900)
    print(child2.before or "")


def main():
    parser = argparse.ArgumentParser(description="Generate and import companion profiles")
    parser.add_argument("--count", type=int, default=85)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--import", dest="do_import", action="store_true")
    parser.add_argument("--host", default="13.140.138.135")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="Fadafx35")
    args = parser.parse_args()

    profiles = generate_profiles(args.count, args.seed)
    out_dir = args.output_dir
    json_path = out_dir / "companion_profiles.json"
    csv_path = out_dir / "companion_profiles.csv"

    save_json(profiles, json_path)
    save_csv(profiles, csv_path)
    print(f"Generated {len(profiles)} profiles")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")

    if args.do_import:
        print(f"Importing to {args.host} ...")
        import_via_ssh(profiles, args.host, args.user, args.password)


if __name__ == "__main__":
    main()
