#!/usr/bin/env python3
"""
Erotik hikaye üretici – kategori × lokasyon kombinasyonları, WP-CLI import.

Kullanım (VPS üzerinde):
  python3 generate-erotic-stories.py --url https://balkutusu.com --limit 48
  python3 generate-erotic-stories.py --url https://balkutusu.com --limit 500 --batch 50
  python3 generate-erotic-stories.py --url https://balkutusu.com --use-ollama --limit 10

Uzaktan (SSH):
  python3 generate-erotic-stories.py --host 13.140.138.135 --url https://balkutusu.com --limit 48
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import textwrap
import time
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

CATEGORIES = [
    ("anal-hikaye", "Anal Escort Hikayeleri", "anal escort"),
    ("oral-hikaye", "Oral Escort Hikayeleri", "oral escort"),
    ("vip-hikaye", "VIP Escort Hikayeleri", "vip escort"),
    ("otel-hikaye", "Otel Escort Hikayeleri", "otel escort"),
    ("plaj-hikaye", "Plaj Escort Hikayeleri", "plaj escort"),
    ("gece-hikaye", "Gece Escort Hikayeleri", "gece escort"),
    ("cift-hikaye", "Çift Escort Hikayeleri", "çift escort"),
    ("grup-hikaye", "Grup Escort Hikayeleri", "grup escort"),
]

LOCATIONS = [
    "Kuşadası Kadınlar Denizi",
    "Kuşadası Yılancı Burnu",
    "Kuşadası Atatürk Caddesi",
    "Kuşadası Liman Caddesi",
    "Kuşadası 2. Sokak",
    "Kuşadası Merkez",
    "Kuşadası Güvercinada",
    "Kuşadası Marina",
]

NAMES = ["Elif", "Selin", "Deniz", "Ayşe", "Merve", "Ceren", "Buse", "Ece", "Zeynep", "Pınar"]

OPENERS = [
    "Yaz akşamının sıcaklığı {loc} boyunca hissediliyordu.",
    "{loc} civarında yürürken telefonum titredi — beklediğim mesaj gelmişti.",
    "Kuşadası'nın {loc} bölgesinde geçen bu anı, uzun süre unutamayacağım.",
    "Tatil planım sadece deniz ve güneş değildi; {loc} benim için farklı bir başlangıç oldu.",
]

BODY = [
    "Profesyonel ve zarif tavrıyla hemen güven verdi. Sohbetimiz kısa sürede samimi bir tona büründü.",
    "Randevuyu önceden netleştirmiştik; buluşma noktası tam istediğim gibiydi, merkeze yakın ve sakin.",
    "Gülüşü, bakışları ve özenli duruşu ortamın enerjisini anında yükseltti.",
    "Kuşadası gecelerinin ritmini bilen biri olduğu her hareketinden belli oluyordu.",
    "İletişim gücü yüksekti; ne istediğimi sormadan anlayan nadir insanlardan biriydi.",
    "Otel lobisinden odasına geçerken bile çevreden dikkat çekmeyecek şekilde hareket etti.",
    "Sahil kenarındaki yürüyüşümüz, gün batımıyla birleşince romantik bir atmosfer oluşturdu.",
    "Masaj ve sohbet arasında geçen o saatler, stresimi tamamen aldı.",
]

CLOSERS = [
    "Gece sona ererken {keyword} deneyiminin Kuşadası'nda ne kadar özel olabileceğini bir kez daha anladım.",
    "{loc} artık benim için sadece bir adres değil; güzel anıların kayıtlı olduğu bir yer.",
    "Tekrar geldiğimde aynı bölgede, aynı sıcaklıkta bir buluşma planlamak istiyorum.",
    "Gizlilik ve saygı çerçevesinde geçen bu buluşma, beklentilerimin üzerindeydi.",
    "{keyword} arayanlar için {loc} gerçekten doğru bir tercih olabilir.",
]

META_TPL = "{loc} bölgesinde {keyword} deneyimi — Kuşadası escort hikayesi. Samimi anılar, lokasyon ve kategori bazlı arşiv."


def build_story(loc: str, keyword: str, name: str) -> tuple[str, str, str]:
    """Başlık, içerik (HTML), meta açıklama üret."""
    short_loc = loc.replace("Kuşadası ", "")
    title = f"{short_loc} {keyword.title()} Hikayesi – {name} ile Unutulmaz Bir Gece"
    opener = random.choice(OPENERS).format(loc=loc)
    paragraphs = [opener]
    for _ in range(random.randint(4, 6)):
        paragraphs.append(random.choice(BODY))
    paragraphs.append(random.choice(CLOSERS).format(loc=loc, keyword=keyword))
    paragraphs.append(
        f"Bu hikaye {keyword} kategorisinde, {loc} lokasyonu için arşivlenmiştir. "
        f"Kuşadası escort platformunda benzer deneyimler için kategori sayfalarını ziyaret edebilirsiniz."
    )
    content = "".join(f"<p>{textwrap.fill(p, width=90)}</p>" for p in paragraphs)
    excerpt = META_TPL.format(loc=loc, keyword=keyword)
    return title, content, excerpt


def ollama_story(loc: str, keyword: str, model: str = "llama3", host: str = "http://127.0.0.1:11434") -> Optional[str]:
    if not requests:
        return None
    prompt = (
        f"Kuşadası {loc} bölgesinde {keyword} ile yaşanmış gerçekçi, samimi, yetişkinlere yönelik "
        f"bir anı yaz. 300 kelime. SEO uyumlu olsun. Anahtar kelime: {keyword} {loc}. Türkçe yaz."
    )
    try:
        r = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"  [ollama] skip: {e}", file=sys.stderr)
        return None


def wp_cli(cmd: list[str], url: str, host: Optional[str], ssh_user: str, ssh_pass: str) -> subprocess.CompletedProcess:
    inner = ["docker", "exec", "hive_wordpress", "wp", "--allow-root", f"--url={url}"] + cmd
    if host:
        full = ["sshpass", "-p", ssh_pass, "ssh", "-o", "StrictHostKeyChecking=no", f"{ssh_user}@{host}"] + inner
    else:
        full = inner
    return subprocess.run(full, capture_output=True, text=True)


def ensure_term(slug: str, name: str, url: str, host: Optional[str], ssh_user: str, ssh_pass: str) -> None:
    r = wp_cli(["term", "list", "story_category", "--slug=" + slug, "--field=term_id", "--format=ids"], url, host, ssh_user, ssh_pass)
    if r.stdout.strip():
        return
    wp_cli(["term", "create", "story_category", name, f"--slug={slug}"], url, host, ssh_user, ssh_pass)


def create_story(
    title: str,
    content: str,
    excerpt: str,
    term_slug: str,
    lokasyon: str,
    url: str,
    host: Optional[str],
    ssh_user: str,
    ssh_pass: str,
) -> bool:
    r = wp_cli(
        [
            "post", "create",
            "--post_type=erotic_story",
            "--post_status=publish",
            f"--post_title={title}",
            f"--post_content={content}",
            f"--post_excerpt={excerpt}",
            "--porcelain",
        ],
        url,
        host,
        ssh_user,
        ssh_pass,
    )
    if r.returncode != 0:
        print(f"  FAIL create: {r.stderr.strip()}", file=sys.stderr)
        return False
    post_id = r.stdout.strip()
    if not post_id.isdigit():
        print(f"  FAIL id: {post_id}", file=sys.stderr)
        return False
    wp_cli(["post", "meta", "update", post_id, "story_lokasyon", lokasyon], url, host, ssh_user, ssh_pass)
    wp_cli(["post", "meta", "update", post_id, "story_likes", str(random.randint(3, 120))], url, host, ssh_user, ssh_pass)
    wp_cli(["post", "term", "set", post_id, "story_category", term_slug], url, host, ssh_user, ssh_pass)
    print(f"  OK #{post_id} {title[:50]}...")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Erotik hikaye üret ve WordPress'e kaydet")
    ap.add_argument("--url", default="https://balkutusu.com", help="WordPress site URL")
    ap.add_argument("--host", default=None, help="SSH host (uzaktan çalıştırma)")
    ap.add_argument("--ssh-user", default="root")
    ap.add_argument("--ssh-pass", default="Fadafx35")
    ap.add_argument("--limit", type=int, default=48, help="Üretilecek hikaye sayısı")
    ap.add_argument("--batch", type=int, default=0, help="Batch arası bekleme (saniye), 0=kapalı")
    ap.add_argument("--use-ollama", action="store_true")
    ap.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    combos = [(c, loc) for c in CATEGORIES for loc in LOCATIONS]
    random.shuffle(combos)

    created = 0
    for slug, cat_name, keyword in CATEGORIES:
        ensure_term(slug, cat_name, args.url, args.host, args.ssh_user, args.ssh_pass)

    for i in range(args.limit):
        cat_tuple, loc = combos[i % len(combos)]
        slug, cat_name, keyword = cat_tuple
        name = random.choice(NAMES)

        if args.use_ollama:
            raw = ollama_story(loc, keyword, host=args.ollama_host)
            if raw:
                title = f"{loc.replace('Kuşadası ', '')} {keyword.title()} – {name}"
                content = "".join(f"<p>{textwrap.fill(p.strip(), 90)}</p>" for p in raw.split("\n\n") if p.strip())
                excerpt = META_TPL.format(loc=loc, keyword=keyword)
            else:
                title, content, excerpt = build_story(loc, keyword, name)
        else:
            title, content, excerpt = build_story(loc, keyword, name)

        if args.dry_run:
            print(f"[dry-run] {title}")
            created += 1
            continue

        if create_story(title, content, excerpt, slug, loc, args.url, args.host, args.ssh_user, args.ssh_pass):
            created += 1
        if args.batch and (created % 10 == 0):
            time.sleep(args.batch)

    print(f"\nTamamlandı: {created} hikaye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
