#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kuşadası Gece Hayatı Rehberi — 180 mekan × 500+ kelime plain text üretici.

Kullanım:
  python3 generate-gece-hayati-rehberi.py
  python3 generate-gece-hayati-rehberi.py --out sites/content/gece-hayati

Çıktı:
  - HARITA.txt          → içerik haritası
  - mekanlar/*.txt    → her mekan ayrı dosya
  - TUM-REHBERLER.txt → tek dosyada tüm rehberler
"""

from __future__ import annotations

import argparse
import hashlib
import random
import re
import textwrap
from pathlib import Path

from kusadasi_geo import GEO_FACTS, LANDMARKS, MAHALLELER

# ── Saat dilimleri ──────────────────────────────────────────────────────────
SLOTS = [
    ("15-18", "15:00–18:00", "Öğleden Sonra & Happy Hour", "15:00-18:00"),
    ("18-21", "18:00–21:00", "Akşam Başlangıcı & Aperitif", "18:00-21:00"),
    ("21-23", "21:00–23:00", "Prime Time Gece", "21:00-23:00"),
    ("23-02", "23:00–02:00", "Gece Zirvesi", "23:00-02:00"),
    ("02-05", "02:00–05:00", "After Hours", "02:00-05:00"),
    ("24-saat", "24 Saat", "7/24 Açık Mekanlar", "24 Saat"),
]

# ── Mekan türleri ───────────────────────────────────────────────────────────
TYPES = [
    ("bar", "Bar", ["Breeze", "Rocks", "Tavern", "Spirits", "Harbor", "Sunset", "Wave", "Oak", "Cask"]),
    ("lounge", "Lounge", ["Velvet", "Noir", "Pearl", "Amber", "Silk", "Crown", "Horizon", "Mist", "Aura"]),
    ("club", "Club", ["Pulse", "Eclipse", "Neon", "Voltage", "Tempo", "Apex", "Fusion", "Riot", "Storm"]),
    ("after", "After", ["Dawn", "Phantom", "Nightfall", "03AM", "Loft", "Underground", "Vault", "Nocturne"]),
    ("otel", "Otel Bar & Lounge", ["Grand Terrace", "Marina Rooftop", "Sea View", "Palm Court", "Horizon Bar", "Azure Deck"]),
    ("plaj", "Plaj & Beach Club", ["Beach Club", "Shore", "Sands", "Bay", "Cove", "Tides", "Dune", "Lagoon"]),
]

VENUES_PER_TYPE = 5  # 6 slot × 6 tür × 5 = 180 mekan

# Mahalle koordinat tabanı (yaklaşık)
COORDS = {
    "kadinlar-denizi": (37.8621, 27.2684),
    "yilanciburnu": (37.8645, 27.2712),
    "guvercinada": (37.8598, 27.2561),
    "davutlar": (37.8482, 27.2415),
    "kusadasi-merkez": (37.8575, 27.2613),
    "turkmen": (37.8558, 27.2589),
    "cumhuriyet": (37.8569, 27.2598),
    "marina": (37.8582, 27.2547),
    "yavansu": (37.8512, 27.2488),
    "guzelcamli": (37.8312, 27.2188),
    "camiatik": (37.8545, 27.2571),
    "zeus": (37.8605, 27.2655),
}

COCKTAILS = [
    ("Ege Esintisi", "cin, lavanta şurubu, tonic ve taze limon dilimi"),
    ("Kuşadası Sunset", "rom, ananas suyu, grenadin ve portakal kabuğu"),
    ("Midnight Pearl", "votka, beyaz vermut, greyfurt ve zencefil"),
    ("Golden Marina", "viski, bal, portakal bitter ve buz küpü"),
    ("Turquoise Bay", "tekila, mavi curaçao, lime ve tuzlu kenar"),
    ("Aegean Breeze", "gin, salatalık, nane ve soda"),
    ("Ruby Night", "prosecco, nar suyu, frambuaz ve gül yaprakları"),
    ("Onyx Velvet", "konyak, espresso, kakao bitter ve krema"),
]

FEATURES_POOL = [
    "Canlı DJ", "Kapalı bahçe", "Özel kabin", "Sahil manzarası", "Açık otopark",
    "Rooftop teras", "VIP masa rezervasyonu", "Sigara içilebilir alan", "Deniz kenarı deck",
    "Klima kontrollü salon", "Kokteyl barı", "Şarap mahzeni", "Happy hour menüsü",
    "Canlı piyano", "Latin gecesi", "Tema partileri", "Özel etkinlik alanı",
]

HOURS_BY_SLOT = {
    "15-18": "15:00 – 20:00",
    "18-21": "18:00 – 01:00",
    "21-23": "19:00 – 03:00",
    "23-02": "22:00 – 04:00",
    "02-05": "02:00 – 05:30",
    "24-saat": "7/24 Açık",
}

ENTRY_BY_SLOT = {
    "15-18": "Yok (happy hour döneminde)",
    "18-21": "Yok",
    "21-23": "Cuma–Cumartesi 200–400 TL (sezona göre değişir)",
    "23-02": "350–600 TL (VIP masada minimum harcama uygulanabilir)",
    "02-05": "Yok veya 150 TL (after party girişi)",
    "24-saat": "Yok",
}

AGE_BY_TYPE = {
    "bar": "18+",
    "lounge": "18+",
    "club": "21+",
    "after": "21+",
    "otel": "18+",
    "plaj": "18+",
}


def slugify(text: str) -> str:
    repl = {
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u",
        " ": "-",
    }
    s = "".join(repl.get(c, c) for c in text).lower()
    return re.sub(r"[^a-z0-9-]+", "", s)


def seeded_rng(*parts: str) -> random.Random:
    h = hashlib.sha256("||".join(parts).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def word_count(text: str) -> int:
    return len(re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", text, re.UNICODE))


def pick_mahalle(idx: int) -> tuple[str, str, list]:
    m = MAHALLELER[idx % len(MAHALLELER)]
    return m[0], m[1], m[2]


def build_venue_name(mahalle_name: str, type_suffix: str, suffix: str) -> str:
    return f"{mahalle_name} {suffix}" if type_suffix != "otel" else f"{mahalle_name} {suffix}"


def generate_guide(
    venue: str,
    slot_label: str,
    slot_slug: str,
    slot_seo: str,
    type_label: str,
    type_slug: str,
    mahalle_slug: str,
    mahalle_name: str,
    street_name: str,
    street_type: str,
    venue_idx: int,
) -> str:
    rng = seeded_rng(venue, slot_slug, type_slug, str(venue_idx))
    base_lat, base_lon = COORDS.get(mahalle_slug, (37.8575, 27.2613))
    lat = base_lat + rng.uniform(-0.004, 0.004)
    lon = base_lon + rng.uniform(-0.004, 0.004)
    no = rng.randint(8, 186)
    phone = f"0{rng.choice([256, 532])} {rng.randint(200, 899)} {rng.randint(10, 99):02d} {rng.randint(10, 99):02d}"
    insta = f"@kusadasi_{slugify(venue)[:24]}"

    nearby_hotels = rng.sample(
        [f"{mahalle_name} Resort", f"{mahalle_name} Boutique Hotel", "Palm Wings Beach", "Charisma De Luxe", "Tusan Beach Resort"],
        3,
    )
    nearby_landmarks = rng.sample(LANDMARKS, 3)
    features = rng.sample(FEATURES_POOL, 6)
    cocktails = rng.sample(COCKTAILS, 3)

    decor = rng.choice([
        "modern Ege minimalizmi ve sıcak ahşap detaylar",
        "lüks art deco dokunuşları ve altın vurgular",
        "retro 80'ler plaj kulübü estetiği",
        "açık hava bohem dekorasyonu ve fener ışıkları",
        "koyu tonlarda gizemli lounge atmosferi",
        "beyaz mermer ve deniz mavisi aksanlar",
    ])
    profile = rng.choice([
        "25–40 yaş arası iş insanları ve hafta sonu kaçamakçıları",
        "Avrupa ve İngiltere'den gelen turistler ile yerli eğlence severler",
        "çiftler, arkadaş grupları ve özel kutlama organizasyonları",
        "marina yat sahipleri ve premium konaklama misafirleri",
        "Kuşadası merkez otellerinden yürüyerek gelen gezginler",
    ])
    spirit = rng.choice([
        "enerjik ve iddialı",
        "sakin ama sofistike",
        "romantik ve samimi",
        "gizlilik odaklı ve seçkin",
        "plaj havasında rahat ve neşeli",
    ])

    transport = []
    if mahalle_slug in ("kadinlar-denizi", "yilanciburnu", "kusadasi-merkez", "marina"):
        transport.append("Kuşadası merkez otellerinden yürüyerek 5–15 dakikada ulaşılabilir.")
    transport.append("Taksi veya özel araçla Atatürk Caddesi / sahil yolu üzerinden doğrudan ön kapıya varış mümkündür.")
    if type_slug == "plaj":
        transport.append("Yaz sezonunda sahil servisleri ve dolmuş hatları mekana yakın duraklardan geçer.")
    if type_slug == "otel":
        transport.append("Otel konukları için asansör veya lobiden doğrudan erişim sağlanır; dışarıdan rezervasyonla giriş yapılabilir.")

    reviews = [
        f'"{mahalle_name}\'nda iş seyahatindeydim. Otelden çıkıp yürüyerek geldim. {venue} ortamı çok iyiydi, yalnız hissettirmiyor. Kokteylleri harika." — Mehmet K., İstanbul',
        f'"Arkadaşlarla geldik, özel kabin ayarladılar. Gizlilikleri çok iyi, garsonlar ilgili. {slot_label} saatlerinde bile kalabalık ama düzenli." — Ayşe & Deniz, İzmir',
        f'"Turist sezonunda keşfettik. Müzik seviyesi konuşmayı engellemiyor, manzara muhteşem. Tekrar geleceğiz." — James R., UK',
        f'"Kuşadası gece hayatı rehberlerinde gördük, beklentiyi aştı. İmza kokteyl {cocktails[0][0]} mutlaka denenmeli." — Selin A., Ankara',
    ]
    rng.shuffle(reviews)
    reviews = reviews[:3]

    events = {
        "15-18": [
            "Pazartesi–Perşembe: Happy hour %20 indirimli kokteyller.",
            "Cuma: DJ warm-up seti ve gün batımı partisi.",
            "Cumartesi: Canlı akustik performans.",
            "Pazar: Chill-out ve lounge müzik.",
        ],
        "18-21": [
            "Her gün: Aperitif menüsü ve şarap eşleştirmeleri.",
            "Cuma–Cumartesi: Canlı DJ ve dans pisti açılışı.",
            "Pazar: Latin müzik gecesi.",
            "Ayın ilk Perşembesi: Tema gecesi (retro / white party).",
        ],
        "21-23": [
            "Cuma–Cumartesi: Headliner DJ performansları.",
            "Perşembe: Ladies night özel kokteyller.",
            "Pazar: R&B ve house karışımı gece.",
            "Bayram ve özel günlerde uzatılmış saat.",
        ],
        "23-02": [
            "Cuma–Cumartesi: Peak hour DJ ve lazer gösteri.",
            "Gece yarısı: Shot menüsü ve VIP masa servisi.",
            "Özel davetlerde after-party uzatması.",
            "Sezon sonu kapanış partileri.",
        ],
        "02-05": [
            "Cuma–Cumartesi: After party 02:00 sonrası.",
            "Sınırlı kapasite; erken gelenlere öncelik.",
            "Sakin müzik ve gece atıştırmalıkları.",
            "Personel rotasyonu ile güvenli çıkış desteği.",
        ],
        "24-saat": [
            "7/24 bar servisi ve gece kahvaltısı menüsü.",
            "Otel misafirleri için gece turu sonrası buluşma noktası.",
            "Havaalanı transferi bekleyenlere açık lounge.",
            "Ramazan ve bayramda özel saat düzenlemesi duyurulur.",
        ],
    }

    geo_fact = GEO_FACTS.get(mahalle_slug, "Kuşadası Ege kıyısının önemli turizm merkezidir.")

    intro = textwrap.fill(
        f"{venue}, Kuşadası'nın {mahalle_name} bölgesinde {slot_label} saat diliminde öne çıkan "
        f"{type_label.lower()} konseptli mekanlardan biridir. {geo_fact} "
        f"Bu rehber sayfası, mekana gitmeden önce konum, ulaşım, atmosfer, menü ve müşteri deneyimi "
        f"hakkında kapsamlı bilgi sunmak için hazırlanmıştır. Özellikle {slot_seo} aralığında "
        f"Kuşadası gece hayatı planı yapan ziyaretçiler için {venue} detaylı bir durak noktasıdır.",
        width=100,
    )

    seo_block = textwrap.fill(
        f"Kuşadası gece hayatı aramalarında '{mahalle_name} {type_label.lower()}', "
        f"'Kuşadası {slot_seo} mekanları' ve '{venue}' anahtar kelimeleriyle bulunabilirsiniz. "
        f"{mahalle_name} bölgesindeki oteller, plajlar ve diğer eğlence noktalarıyla çapraz bağlantılı "
        f"bu içerik, lokasyon SEO'su için optimize edilmiştir. Güncel çalışma saatleri ve etkinlikler "
        f"için mekanı aramadan önce Instagram hesabını kontrol etmenizi öneririz.",
        width=100,
    )

    tips_block = textwrap.fill(
        f"Ziyaret ipucu: {slot_label} saatlerinde {venue} genellikle {rng.choice(['19:30', '20:00', '21:00', '22:30'])} "
        f"civarında yoğunlaşır; kalabalık yaşamamak için bir saat erken gelmek mantıklıdır. "
        f"Özel gün kutlamaları için en az 48 saat önceden telefon veya Instagram DM ile masa ayırtın. "
        f"Kuşadası merkez–{mahalle_name} aksında taksi ücretleri sezona göre değişir; yürüyüş mesafesinde "
        f"iseniz sahil yolunu tercih ederek manzaralı bir rota izleyebilirsiniz.",
        width=100,
    )

    lines = [
        f"### {venue} – Kuşadası {slot_seo} Rehberi",
        "",
        intro,
        "",
        "**📍 Konum ve Ulaşım**",
        f"- Tam Adres: Kuşadası, {mahalle_name}, {street_name} No:{no}",
        f"- Koordinatlar: {lat:.4f}°K, {lon:.4f}°D (Google Maps)",
        "- Ulaşım:",
    ]
    for t in transport:
        lines.append(f"  • {t}")
    lines += [
        "- Çevredeki Önemli Yerler:",
        f"  • Yakın oteller: {', '.join(nearby_hotels)}",
        f"  • Yürüme mesafesi: {', '.join(nearby_landmarks)}",
        f"  • Bölge notu: {geo_fact}",
        "",
        "**📞 İletişim ve Detaylar**",
        f"- Telefon: {phone}",
        f"- Instagram: {insta}",
        f"- Çalışma Saatleri: {HOURS_BY_SLOT[slot_slug]} ({slot_label} yoğunluğu)",
        f"- Yaş Sınırı: {AGE_BY_TYPE[type_slug]}",
        f"- Giriş Ücreti: {ENTRY_BY_SLOT[slot_slug]}",
        f"- Özellikler: {', '.join(features)}",
        "",
        "**🍸 Atmosfer ve Konsept**",
        f"- Dekorasyon: {decor.capitalize()}.",
        f"- Müşteri Profili: {profile.capitalize()}.",
        f"- Mekanın Ruhu: {spirit.capitalize()}. {type_label} konsepti {slot_label} saatlerinde "
        f"Kuşadası'nın {mahalle_name} aksında farklı bir deneyim sunar.",
        "",
        textwrap.fill(
            f"{venue} iç mekânında oturma düzeni, bar tezgâhı ve müzik sistemi {type_label.lower()} "
            f"kategorisinin beklentilerine göre kurgulanmıştır. Yaz aylarında açık alan kapasitesi artar; "
            f"kış sezonunda kapalı salon ve ısıtıcılı teras kullanılır. Personel çoğunlukla İngilizce "
            f"ve Türkçe hizmet verir; turist yoğunluğu yüksek dönemlerde rezervasyon önerilir.",
            width=100,
        ),
        "",
        "**🍹 Öne Çıkanlar**",
        "- İmza Kokteyller:",
    ]
    for name, desc in cocktails:
        lines.append(f"  • {name}: {desc}")
    lines += [
        "- Popüler İçkiler: Premium viski (Jack Daniel's, Chivas), votka (Absolut, Grey Goose), "
        "yerel ve ithal bira (Efes, Bomonti, Corona), beyaz ve kırmızı şarap seçkisi.",
        "- Atıştırmalıklar: Nachos, deniz ürünleri tabağı, peynir şarküteri, mevsim meyveleri ve vegan seçenekler.",
        "",
        "**💬 Müşteri Yorumları**",
    ]
    for r in reviews:
        lines.append(f"- *{r}*")
    lines += [
        "",
        "**🗓️ Haftalık ve Günlük Etkinlikler**",
    ]
    for ev in events[slot_slug]:
        lines.append(f"- {ev}")
    lines += [
        "",
        "**🔗 Bağlantılı İçerikler**",
        f"- Bu bölgedeki oteller: [Link: Kuşadası {mahalle_name} Otel Rehberi]",
        f"- Bu bölgedeki diğer barlar: [Link: {mahalle_name}'nin En İyi 5 Barı]",
        f"- Yakın plajlar: [Link: {mahalle_name} Plaj Rehberi]",
        f"- Saat dilimi rehberi: [Link: Kuşadası Gece Hayatı {slot_seo}]",
        f"- Mekan türü: [Link: Kuşadası {type_label} Rehberi]",
        "",
        tips_block,
        "",
        seo_block,
        "",
        "─" * 72,
        "",
    ]
    return "\n".join(lines)


def build_content_map() -> list[dict]:
    venues: list[dict] = []
    global_idx = 0
    for si, (slot_slug, slot_label, slot_title, slot_seo) in enumerate(SLOTS):
        for ti, (type_slug, type_label, suffixes) in enumerate(TYPES):
            for vi in range(VENUES_PER_TYPE):
                mslug, mname, streets = pick_mahalle(global_idx + si + ti + vi)
                street_slug, street_name, street_type = streets[vi % len(streets)]
                suffix = suffixes[vi % len(suffixes)]
                name = build_venue_name(mname, type_slug, suffix)
                venues.append({
                    "id": global_idx + 1,
                    "name": name,
                    "slug": slugify(f"{name}-{slot_slug}-{type_slug}"),
                    "slot_slug": slot_slug,
                    "slot_label": slot_label,
                    "slot_title": slot_title,
                    "slot_seo": slot_seo,
                    "type_slug": type_slug,
                    "type_label": type_label,
                    "mahalle_slug": mslug,
                    "mahalle_name": mname,
                    "street_name": street_name,
                    "street_type": street_type,
                    "venue_idx": vi,
                })
                global_idx += 1
    return venues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="sites/content/gece-hayati")
    args = parser.parse_args()
    out = Path(args.out)
    mekan_dir = out / "mekanlar"
    mekan_dir.mkdir(parents=True, exist_ok=True)

    venues = build_content_map()
    all_text: list[str] = []
    map_lines = [
        "KUŞADASI GECE HAYATI İÇERİK HARİTASI",
        f"Toplam mekan: {len(venues)}",
        f"Saat dilimi: {len(SLOTS)} | Mekan türü: {len(TYPES)} | Tür başına: {VENUES_PER_TYPE}",
        "=" * 72,
        "",
    ]

    wc_stats: list[int] = []
    for v in venues:
        body = generate_guide(
            v["name"], v["slot_label"], v["slot_slug"], v["slot_seo"],
            v["type_label"], v["type_slug"], v["mahalle_slug"], v["mahalle_name"],
            v["street_name"], v["street_type"], v["venue_idx"],
        )
        wc = word_count(body)
        wc_stats.append(wc)
        fname = f"{v['id']:03d}-{v['slug']}.txt"
        (mekan_dir / fname).write_text(body, encoding="utf-8")
        all_text.append(body)
        map_lines.append(
            f"{v['id']:3d}. [{v['slot_seo']}] [{v['type_label']}] {v['name']} "
            f"→ {v['mahalle_name']} / {fname} ({wc} kelime)"
        )

    (out / "HARITA.txt").write_text("\n".join(map_lines), encoding="utf-8")
    (out / "TUM-REHBERLER.txt").write_text("\n".join(all_text), encoding="utf-8")

    print(f"Üretildi: {len(venues)} mekan rehberi")
    print(f"Kelime: min={min(wc_stats)}, max={max(wc_stats)}, ort={sum(wc_stats)//len(wc_stats)}")
    print(f"Çıktı: {out.resolve()}")


if __name__ == "__main__":
    main()
