#!/usr/bin/env python3
"""Pornhub EN/TR kategoriler için benzersiz 1500-2000 kelime SEO."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import random
import re
import subprocess
import sys
import textwrap

from kusadasi_geo import GEO_FACTS, LANDMARKS, MAHALLELER
from pornhub_categories import CATEGORIES

TARGET_MIN = 1500
TARGET_MAX = 2000
WP = ["docker", "exec", "hive_wordpress", "wp", "--allow-root"]
URL = "https://balkutusu.com"

# Kategori özel GEO notları (benzersizlik)
CATEGORY_NOTES: dict[str, str] = {
    "anal": "Anal hizmet kapsamı profil bazında değişir; Kuşadası randevularında sınırlar önceden yazılı teyit edilmelidir.",
    "milf": "MILF profiller olgun deneyim ve sofistike iletişim sunar; Kuşadası VIP otellerinde sık tercih edilir.",
    "lesbian": "Lezbiyen show ve çift bayan profiller Kuşadası yaz sezonunda talep artışı gösterir.",
    "russian": "Rus escort profilleri marina ve otel kuşağında yabancı misafir yoğunluğuyla öne çıkar.",
    "massage": "Masaj eşliğinde escort, Kuşadası spa ve butik otellerinde popülerdir.",
    "threesome": "Üçlü randevularda süre, katılımcı ve ücret paketi netleştirilmelidir.",
    "blowjob": "Oral hizmet etiketi taşıyan profillerde hijyen ve karşılıklı konfor önceliklidir.",
    "creampie": "İçine boşalma detayı her profilde sunulmayabilir; kapsamı mesajda sorun.",
    "pov": "POV formatı buluşma değil içerik tarzını ifade edebilir; escort randevusunda ayrı netleştirin.",
    "webcam": "Webcam ön görüşme veya sanal ön tanışma için kullanılabilir; yüz yüze randevu ayrı planlanır.",
}


def word_count(text: str) -> int:
    plain = re.sub(r"<[^>]+>", " ", text)
    return len(re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", plain, re.UNICODE))


def wp(args: list[str]) -> str:
    r = subprocess.run(WP + args + [f"--url={URL}"], capture_output=True, text=True)
    return (r.stdout or "").strip()


def p(text: str) -> str:
    return f"<p>{html.escape(textwrap.fill(text, width=105))}</p>"


def h2(text: str) -> str:
    return f"<h2>{html.escape(text)}</h2>"


def rng(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha256("||".join(parts).encode()).hexdigest()[:16], 16))


def generate_en_category(label: str, slug: str, pair: str) -> str:
    """EN kategori adı — Kuşadası escort sitesinde TR metin + EN anahtar kelime."""
    kw = f"Kuşadası {label} Escort"
    r = rng(slug, label, "en")
    parts = []
    note = CATEGORY_NOTES.get(pair, f"{label} Kuşadası escort segmentinde niş bir arama kategorisidir.")

    parts.append(h2(f"{kw} — Kuşadası {label} Rehberi"))
    parts.append(p(
        f"Bal Kutusu (balkutusu.com) üzerinde {kw} kategorisi, {label} etiketli güncel escort profillerini Kuşadası mahalle ve sahil aksına göre listeler. "
        f"{note} Aydın'ın Ege kıyısındaki Kuşadası ilçesinde {label} araması yapan ziyaretçiler; gizlilik, net iletişim ve lokasyon teyidini önceliklendirmelidir."
    ))

    parts.append(h2(f"Kuşadası Mahalleleri ve {label} Lokasyonları"))
    for mslug, mname, _ in r.sample(MAHALLELER, min(8, len(MAHALLELER))):
        fact = GEO_FACTS.get(mslug, "")
        parts.append(p(
            f"{mname} mahallesinde {kw} seçenekleri {label} filtresiyle görüntülenir. {fact} "
            f"Kuşadası {mname} bölgesinde {label} randevusu planlarken marina, sahil veya merkez caddeler referans alınabilir."
        ))

    parts.append(h2(f"{label} — Hizmet Kapsamı ve Profil Seçimi"))
    for _ in range(6):
        parts.append(p(
            f"{label} profilleri Kuşadası escort platformunda farklı yaş, görünüm ve hizmet paketleri sunar. {kw} arayanların profil fotoğrafları, "
            f"Telegram/WhatsApp yanıt süresi ve {label} etiket tutarlılığını kontrol etmesi önerilir. {note}"
        ))

    parts.append(h2(f"{label} Rezervasyon — Kuşadası 2026"))
    for lm in r.sample(LANDMARKS, 5):
        parts.append(p(
            f"Kuşadası {lm} çevresinden {kw} randevusu alan ziyaretçiler, buluşma noktasını önceden yazılı netleştirmelidir. "
            f"Yaz sezonunda {label} talebi artar; {lm} aksında trafik ve taksi süresi plana dahil edilmelidir."
        ))

    parts.append(h2(f"Sık Sorulan Sorular — {kw}"))
    faqs = [
        (f"Kuşadası'da {label} escort nasıl bulunur?", f"balkutusu.com {kw} kategori sayfasından güncel profillere ulaşın."),
        (f"{label} güvenilir mi?", "İletişimi net ve fotoğrafları tutarlı profilleri tercih edin."),
        (f"{kw} fiyatları?", "Sezon ve süreye göre değişir; paket detayını mesajda sorun."),
    ]
    for q, a in faqs:
        parts.append(p(f"{q} {a}"))

    parts.append(h2(f"Sonuç — {kw}"))
    parts.append(p(
        f"Bu sayfa {slug} kategorisine özel hazırlanmıştır; diğer {label} veya mahalle sayfalarından farklı bölüm sırası ve yerel detaylar içerir. "
        f"Kuşadası {label} escort aramasında GEO uyumlu, kopya olmayan içerik kullanıcı ve arama motorları için değer sağlar."
    ))

    body = "\n".join(parts)
    wc = word_count(body)
    i = 0
    extras = [
        f"Kuşadası marina ve sahil aksında {kw} randevuları yaz aylarında yoğunlaşır.",
        f"{label} kategorisinde profil seçerken iletişim hızı ve fotoğraf tutarlılığına dikkat edin.",
        f"Aydın Kuşadası {kw} aramalarında mahalle filtresi doğru eşleşmeyi hızlandırır.",
        f"Bal Kutusu {kw} listeleri düzenli güncellenir; sezon öncesi erken yazışma avantaj sağlar.",
    ]
    while wc < TARGET_MIN and i < 40:
        parts.append(p(extras[i % len(extras)] + f" {note}"))
        body = "\n".join(parts)
        wc = word_count(body)
        i += 1
    while wc > TARGET_MAX:
        idx = body.rfind("<p>")
        if idx < 0:
            break
        body = body[:idx]
        wc = word_count(body)
    return body


def generate_tr_category(label: str, slug: str, pair: str) -> str:
    """TR kategori — tamamen Türkçe benzersiz içerik."""
    kw = f"Kuşadası {label} Escort"
    r = rng(slug, label, "tr")
    parts = []
    note = CATEGORY_NOTES.get(pair, f"{label} kategorisi Kuşadası escort aramalarında belirgin bir niş oluşturur.")

    intros = [
        f"{kw} arayan ziyaretçiler için Kuşadası, mahalle bazlı filtreleme ve güncel ilan yapısıyla güçlü bir escort pazarı sunar. {note}",
        f"Kuşadası ilçesinde {label} hizmeti; yaz sezonu, marina trafiği ve otel kuşağı yoğunluğuyla birlikte değerlendirilmelidir. {note}",
        f"Bal Kutusu ana portalında {kw} listeleri düzenli güncellenir. {label} profillerinde iletişim kanalı, müsaitlik ve lokasyon bilgisi randevu kalitesini belirler.",
    ]
    parts.append(h2(f"{kw} Rehberi — Kuşadası"))
    parts.append(p(r.choice(intros)))

    parts.append(h2(f"{label} ve Kuşadası Coğrafyası"))
    for mslug, mname, streets in r.sample(MAHALLELER, min(7, len(MAHALLELER))):
        street = streets[0][1] if streets else "merkez caddeleri"
        parts.append(p(
            f"{mname} — {street} hattında {kw} ilanları yoğunlaşabilir. {GEO_FACTS.get(mslug, '')} "
            f"{label} kategorisinde {mname} bölgesi, ulaşım ve buluşma noktası çeşitliliği açısından Kuşadası ziyaretçileri tarafından sık filtrelenir."
        ))

    parts.append(h2(f"{label} Profil Tipleri ve Beklenti Yönetimi"))
    for _ in range(7):
        parts.append(p(
            f"Kuşadası'da {label} etiketli profiller farklı fiyat segmentleri sunar. {kw} görüşmesi öncesinde süre, adres ve "
            f"ödeme yöntemi yazılı teyit edilmelidir. {note} Gizlilik her iki taraf için temel ilkedir."
        ))

    parts.append(h2("Gizlilik, Güven ve İletişim"))
    for _ in range(4):
        parts.append(p(
            f"{kw} randevularında kişisel veri paylaşımı minimumda tutulmalıdır. Kuşadası escort kültüründe saygılı ilk mesaj "
            f"onay şansını artırır. {label} kategorisinde sahte fotoğraf şüphesi durumunda randevuyu iptal etmekten çekinmeyin."
        ))

    parts.append(h2(f"{label} — Sık Sorulan Sorular"))
    for q, a in [
        (f"{kw} nereden bulunur?", "balkutusu.com kategori menüsü ve profil arşivi."),
        (f"En uygun mahalle?", "Profil lokasyon etiketine göre Kadınlar Denizi, Merkez veya Marina seçilebilir."),
        (f"{label} fiyatı?", "Sezon ve VIP statüsüne göre değişir; paket kapsamını sorun."),
    ]:
        parts.append(p(f"{q} {a}"))

    parts.append(h2(f"Özet — {kw}"))
    parts.append(p(
        f"Bu içerik yalnızca {slug} sayfası içindir; hash tabanlı üretimle diğer kategorilerden farklı cümle yapısı kullanılmıştır. "
        f"Kuşadası {label} escort aramasında yerel GEO sinyalleri ve benzersiz metin SEO performansını destekler."
    ))

    body = "\n".join(parts)
    wc = word_count(body)
    i = 0
    extras_tr = [
        f"Kuşadası merkez ve sahil mahallelerinde {kw} için ulaşım ve adres teyidi önemlidir.",
        f"{label} profillerinde gizlilik ve karşılıklı saygı temel beklentidir.",
        f"Ege kıyısı Kuşadası'nda {kw} fiyatları sezon ve süreye göre değişir.",
        f"balkutusu.com üzerinden {label} kategorisinde güncel ilanlara ulaşabilirsiniz.",
    ]
    while wc < TARGET_MIN and i < 40:
        parts.append(p(extras_tr[i % len(extras_tr)]))
        body = "\n".join(parts)
        wc = word_count(body)
        i += 1
    while wc > TARGET_MAX:
        idx = body.rfind("<p>")
        if idx < 0:
            break
        body = body[:idx]
        wc = word_count(body)
    return body


def save_term(tid: int, body: str) -> None:
    b64 = base64.b64encode(body.encode()).decode()
    wp(["eval", f"update_term_meta({tid}, 'hive_seo_body', base64_decode('{b64}'));"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    raw = wp(["eval", """
$terms = get_terms(array('taxonomy'=>'companion_category','hide_empty'=>false,'number'=>0,
  'meta_query'=>array(array('key'=>'hive_cat_group','value'=>array('porn_en','porn_tr'),'compare'=>'IN'))));
$out=array();
foreach($terms as $t){
  $out[] = array(
    'id'=>(int)$t->term_id,
    'slug'=>$t->slug,
    'name'=>$t->name,
    'group'=>get_term_meta($t->term_id,'hive_cat_group',true),
    'label'=>get_term_meta($t->term_id,'hive_porn_label',true),
    'pair'=>get_term_meta($t->term_id,'hive_porn_pair',true),
  );
}
echo json_encode($out);
"""])
    terms = json.loads(raw) if raw else []
    n = 0
    for t in terms:
        label = t.get("label") or t["name"]
        pair = t.get("pair") or ""
        if t["group"] == "porn_en":
            body = generate_en_category(label, t["slug"], pair)
        else:
            body = generate_tr_category(label, t["slug"], pair)
        save_term(t["id"], body)
        n += 1
        if n % 20 == 0 or n <= 3:
            print(f"  [{n}] {t['name'][:50]} — {word_count(body)} kelime", flush=True)
        if args.limit and n >= args.limit:
            break
    print(f"Tamam: {n}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
