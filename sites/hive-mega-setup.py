#!/usr/bin/env python3
"""
balkutusu.com – HIVE Multisite mega kurulum (subdomain, kategori, içerik, SEO)
VPS üzerinde çalıştır: python3 /tmp/hive-mega-setup.py
"""

import random
import re
import subprocess
import sys
import time

WP = ["docker", "exec", "hive_wordpress", "wp"]
THEME = "hive-ultra-premium"
PAGES_PER_SITE = 5   # subdomain başına (50 için artır)
MAIN_PAGES = 20
MAX_SITES_CONTENT = 60  # ilk N siteye içerik (tümü için artır)

# --- Subdomain slug listesi (200+) ---
BASE_SUBS = [
    # Hizmet
    "anal", "oral", "vip", "otel", "plaj", "gece", "24saat", "masaj", "cift", "grup",
    "anal-escort", "oral-escort", "otel-escort", "plaj-escort", "gece-escort",
    "24saat-escort", "masaj-escort", "cift-escort", "grup-escort", "vip-escort",
    # Lokasyon
    "kadinlar-denizi", "yilanciburnu", "guvercinada", "davutlar", "merkez",
    "turkmen", "cumhuriyet", "hacifeyzullah", "camiatik", "karaova",
    "guzelcamli", "yavansu", "sogucak", "camlik", "kusadasi-merkez",
    # Fiziksel
    "sarisin", "esmer", "kizil", "uzun-boylu", "zayif", "dolgun", "fit", "minyon",
    "sarisin-escort", "esmer-escort", "kizil-escort", "uzun-boylu-escort",
    "zayif-escort", "dolgun-escort", "fit-escort", "minyon-escort", "kumral-escort",
    # Yaş
    "genc-escort-20-25", "yetiskin-escort-25-35", "olgun-escort-35-45",
    "orta-yas-escort-45-55", "genc-escort", "yetiskin-escort", "olgun-escort",
    # Dil
    "ingilizce-escort", "rusca-escort", "almanca-escort", "yabanci-escort",
    "ukraynali-escort", "moldovali-escort", "ingilizce-bilen", "rusca-bilen",
    # VIP / Lüks
    "vip-model", "premium-escort", "luxury-escort", "elite-escort",
    "premium", "luxury", "elite", "prestij", "luks-escort", "seckin-escort",
]

# Ek kombinasyonlar 200+ için
EXTRA_SUFFIX = ["escort", "bayan", "model", "vip", "premium", "rehber", "portal"]
EXTRA_PREFIX = ["kusadasi", "aydin", "ege", "sahil", "otel", "plaj", "gece", "vip"]

for p in EXTRA_PREFIX:
    for s in EXTRA_SUFFIX:
        BASE_SUBS.append(f"{p}-{s}")
for i in range(1, 31):
    BASE_SUBS.append(f"escort{i}")
    BASE_SUBS.append(f"model{i}")

# Tekilleştir
SUB_SLUGS = list(dict.fromkeys(BASE_SUBS))[:220]

TELEGRAM_POOL = [
    "kusadasi_vip", "hive_destek", "aydin_escort", "kusadasi_bayan", "vip_kusadasi",
    "escort_kusadasi", "gece_kusadasi", "otel_escort_kus", "plaj_escort", "vip_model_tr",
]

KEYWORD_TEMPLATES = [
    "{kw} escort kuşadası",
    "kuşadası {kw} escort bayan",
    "{kw} escort hizmeti kuşadası",
    "en iyi {kw} escort kuşadası 2026",
    "{kw} escort fiyatları kuşadası",
    "kuşadası {kw} vip escort",
    "{kw} escort iletişim kuşadası",
    "güvenilir {kw} escort kuşadası",
    "{kw} escort rezervasyon kuşadası",
    "kuşadası gece {kw} escort",
]


def wp(*args, url=None, check=True):
    cmd = WP + list(args) + ["--allow-root"]
    if url:
        cmd.extend(["--url", url])
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if check and r.returncode != 0 and "already exists" not in err.lower():
        print(f"WP WARN: {' '.join(args)} -> {err[:200]}", file=sys.stderr)
    return out


def wp_run(args_list):
    return wp(*args_list, check=False)


def existing_domains():
    out = wp_run(["site", "list", "--field=domain"])
    return set(line.strip() for line in out.splitlines() if line.strip())


def create_subdomains():
    existing = existing_domains()
    created = 0
    for slug in SUB_SLUGS:
        domain = f"{slug}.balkutusu.com"
        if domain in existing:
            continue
        title = slug.replace("-", " ").title() + " Kuşadası"
        wp_run(["site", "create", f"--slug={slug}", f"--title={title}", "--email=admin@balkutusu.com"])
        created += 1
    print(f"Subdomain: +{created} (hedef {len(SUB_SLUGS)})")


def activate_theme_all():
    blogs = wp_run(["site", "list", "--field=blog_id"]).splitlines()
    for bid in blogs:
        if not bid.strip():
            continue
        url = wp_run(["site", "list", "--field=url", f"--blog_id={bid}"]).splitlines()
        if url:
            wp_run(["theme", "activate", THEME, f"--url={url[0]}"])
    wp_run(["theme", "enable", THEME, "--network"])
    print("Tema tüm sitelere aktif")


def install_seo_plugins():
    for plugin in ["seo-by-rank-math", "microsoft-indexnow", "super-simple-map-embeds"]:
        wp_run(["plugin", "install", plugin, "--activate"])
    wp_run(["plugin", "activate", "seo-by-rank-math", "--network"])
    wp_run(["plugin", "activate", "microsoft-indexnow", "--network"])
    print("SEO eklentileri kuruldu")


def assign_profile_categories():
    """Her profile 2-3 kategori (lokasyon + hizmet)."""
    pids = wp_run(["post", "list", "--post_type=companion_profile", "--field=ID"]).splitlines()
    all_terms = wp_run(["term", "list", "companion_category", "--field=term_id,parent,slug"]).splitlines()

    parents = []
    children = []
    for line in all_terms:
        parts = line.split("\t")
        if len(parts) >= 3:
            tid, parent, slug = parts[0], parts[1], parts[2]
            if parent == "0":
                parents.append(tid)
            else:
                children.append(tid)

    if not parents:
        parents = [t.split("\t")[0] for t in all_terms if t]

    hizmet_slugs = ("anal", "oral", "vip", "otel", "masaj", "24-saat", "otele", "eve")
    hizmet_terms = []
    for line in all_terms:
        if any(h in line for h in hizmet_slugs):
            hizmet_terms.append(line.split("\t")[0])

    for pid in pids:
        if not pid.strip():
            continue
        picks = []
        if parents:
            picks.append(random.choice(parents))
        if hizmet_terms:
            picks.append(random.choice(hizmet_terms))
        if children and random.random() > 0.4:
            picks.append(random.choice(children))
        picks = list(dict.fromkeys(picks))[:3]
        if picks:
            wp_run(["post", "term", "set", pid, "companion_category"] + picks)

    print(f"Kategori atandı: {len(pids)} profil")


def fill_telegram():
    pids = wp_run(["post", "list", "--post_type=companion_profile", "--field=ID"]).splitlines()
    n = 0
    for pid in pids:
        if not pid.strip():
            continue
        tg = wp_run(["post", "meta", "get", pid, "telegram"])
        if not tg or tg == "null":
            user = random.choice(TELEGRAM_POOL) + str(random.randint(1, 99))
            wp_run(["post", "meta", "update", pid, "telegram", user])
            n += 1
    print(f"Telegram eklendi: {n} profil")


def slugify_kw(text):
    s = text.lower().replace("ş", "s").replace("ı", "i").replace("ğ", "g")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80] or "sayfa"


def generate_pages_for_site(url, site_kw, count):
    existing = wp_run(["post", "list", "--post_type=page", "--format=count", f"--url={url}"])
    try:
        if int(existing or 0) >= count:
            return 0
    except ValueError:
        pass

    made = 0
    for i in range(count):
        tpl = random.choice(KEYWORD_TEMPLATES)
        kw = site_kw.replace("-", " ")
        title = tpl.format(kw=kw).title()
        slug = slugify_kw(title) + f"-{i+1}"
        content = (
            f"<h1>{title}</h1>"
            f"<p>Kusadasi {kw} escort arayanlar icin ozel rehber.</p>"
            f"<h2>Kusadasi {kw.title()} Hizmetleri</h2>"
            f"<p>Guvenilir escort hizmetleri Kadınlar Denizi, Yilanci Burnu ve merkez bolgelerde.</p>"
            f"<h3>Iletisim</h3><p>Telefon ve Telegram ile ulasin.</p>"
        )
        meta_desc = f"{title} - Kusadasi escort rehberi."

        import os
        host_dir = "/opt/thiqos/apps/hive/sites/wp-content/uploads/page-import"
        os.makedirs(host_dir, exist_ok=True)
        fname = f"hive-page-{slug}.html"
        host_path = os.path.join(host_dir, fname)
        with open(host_path, "w", encoding="utf-8") as f:
            f.write(content)
        container_path = f"/var/www/html/wp-content/uploads/page-import/{fname}"

        pid = wp_run([
            "post", "create",
            "--post_type=page",
            f"--post_title={title}",
            f"--post_name={slug}",
            f"--post_content=<{container_path}",
            "--post_status=publish",
            "--porcelain",
            f"--url={url}",
        ])
        try:
            os.remove(host_path)
        except OSError:
            pass
        if pid.isdigit():
            wp_run(["post", "meta", "update", pid, "rank_math_description", meta_desc, f"--url={url}"])
            made += 1
    return made


def generate_all_content():
    lines = wp_run(["site", "list", "--fields=blog_id,url,domain", "--format=csv"]).splitlines()
    total = 0
    for i, line in enumerate(lines[1:MAX_SITES_CONTENT + 1]):
        parts = line.split(",")
        if len(parts) < 3:
            continue
        url, domain = parts[1].strip(), parts[2].strip()
        slug = domain.replace(".balkutusu.com", "")
        count = MAIN_PAGES if slug == "balkutusu.com" else PAGES_PER_SITE
        n = generate_pages_for_site(url, slug, count)
        total += n
        if (i + 1) % 10 == 0:
            print(f"  İçerik: {i+1} site, +{total} sayfa")
        time.sleep(0.05)
    print(f"Toplam yeni sayfa: {total}")


def ping_sitemaps():
    sites = wp_run(["site", "list", "--field=url"]).splitlines()[:30]
    for url in sites:
        if not url.strip():
            continue
        sm = url.rstrip("/") + "/sitemap_index.xml"
        subprocess.run(["curl", "-s", "-o", "/dev/null", f"https://www.bing.com/ping?sitemap={sm}"], timeout=10)
        subprocess.run(["curl", "-s", "-o", "/dev/null", f"https://www.google.com/ping?sitemap={sm}"], timeout=10)
    print("Sitemap ping gönderildi (ilk 30 site)")


def main():
    steps = sys.argv[1:] or ["all"]
    if "all" in steps:
        steps = ["subs", "theme", "seo", "categories", "telegram", "content", "ping", "flush"]

    if "subs" in steps:
        create_subdomains()
    if "theme" in steps:
        activate_theme_all()
    if "seo" in steps:
        install_seo_plugins()
    if "categories" in steps:
        assign_profile_categories()
    if "telegram" in steps:
        fill_telegram()
    if "content" in steps:
        generate_all_content()
    if "ping" in steps:
        ping_sitemaps()
    if "flush" in steps:
        wp_run(["rewrite", "flush"])
        wp_run(["cache", "flush"])

    print("--- ÖZET ---")
    print("Siteler:", wp_run(["site", "list", "--format=count"]))
    print("Kategoriler:", wp_run(["term", "list", "companion_category", "--format=count"]))
    print("Profiller:", wp_run(["post", "list", "--post_type=companion_profile", "--format=count"]))
    print("Sayfalar:", wp_run(["post", "list", "--post_type=page", "--format=count"]))


if __name__ == "__main__":
    main()
