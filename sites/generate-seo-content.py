#!/usr/bin/env python3
"""
Kategori başına 1500–2000 kelime, GEO + SEO uyumlu, birbirinden farklı içerik.
VPS: python3 generate-seo-content.py --host 13.140.138.135 --categories-only
"""

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

from kusadasi_geo import GEO_FACTS, LANDMARKS, MAHALLELER, VARIANTS

TARGET_MIN = 1500
TARGET_MAX = 2000

WP_BASE = ["docker", "exec", "hive_wordpress", "wp", "--allow-root"]


def word_count(text: str) -> int:
    plain = re.sub(r"<[^>]+>", " ", text)
    return len(re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", plain, re.UNICODE))


def wp(args: list[str], url: str | None = None, host: str | None = None, ssh_pass: str = "Fadafx35") -> str:
    cmd = WP_BASE + args
    if url:
        cmd.append(f"--url={url}")
    if host:
        full = ["sshpass", "-p", ssh_pass, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{host}"] + cmd
    else:
        full = cmd
    r = subprocess.run(full, capture_output=True, text=True)
    return (r.stdout or "").strip()


def p(text: str) -> str:
    return f"<p>{html.escape(textwrap.fill(text, width=105))}</p>"


def h2(text: str) -> str:
    return f"<h2>{html.escape(text)}</h2>"


def h3(text: str) -> str:
    return f"<h3>{html.escape(text)}</h3>"


def seeded_rng(*parts: str) -> random.Random:
    h = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def term_context(term: dict) -> dict:
    """WP term + meta → bağlam."""
    slug = term.get("slug", "")
    name = term.get("name", "")
    meta = term.get("meta") or {}
    mahalle = meta.get("hive_geo_mahalle", "")
    street = meta.get("hive_geo_street", "")
    variant = meta.get("hive_variant", "")
    group = meta.get("hive_cat_group", "")
    loc_type = meta.get("hive_loc_type", "")

    mslug = ""
    for ms, mn, _ in MAHALLELER:
        if mn == mahalle or slug.startswith(ms + "-"):
            mslug = ms
            break

    kw = name
    if variant and street and mahalle:
        kw = f"Kuşadası {mahalle} {street} {variant}"
    elif variant and mahalle:
        kw = f"Kuşadası {mahalle} {variant}"
    elif street and mahalle:
        kw = f"Kuşadası {mahalle} {street}"
    elif mahalle:
        kw = f"Kuşadası {mahalle}"

    return {
        "slug": slug,
        "name": name,
        "kw": kw,
        "mahalle": mahalle,
        "street": street,
        "variant": variant,
        "group": group,
        "loc_type": loc_type,
        "mslug": mslug,
        "geo_fact": GEO_FACTS.get(mslug, "Kuşadası, Aydın ilinin Ege kıyısındaki önemli turizm ve yaşam merkezidir."),
    }


def pick_unique(rng: random.Random, pool: list[str], n: int) -> list[str]:
    if n >= len(pool):
        return list(pool)
    return rng.sample(pool, n)


def generate_body(ctx: dict) -> str:
    """Bağlama özel, tekrar etmeyen SEO metni."""
    kw = ctx["kw"]
    rng = seeded_rng(ctx["slug"], kw, ctx.get("variant", ""), ctx.get("street", ""))
    parts: list[str] = []

    openings = [
        f"{kw} arayan ziyaretçiler için Kuşadası'nda doğru lokasyon ve doğru profil eşleşmesi, randevu kalitesini doğrudan belirler. Bu sayfa; {ctx['geo_fact']} Bu bağlamda {kw} hizmetleri, mahalle sınırları, ulaşım alışkanlıkları ve sezon yoğunluğu ile birlikte değerlendirilmelidir.",
        f"Kuşadası escort ekosisteminde {kw} kategorisi, arama niyeti yüksek ve lokasyon odaklı bir segmenttir. Aydın'ın Ege kıyısındaki Kuşadası ilçesinde {kw} profillerine ulaşırken; gizlilik, iletişim netliği ve buluşma noktasının önceden teyidi standart beklentiler arasındadır.",
        f"Bal Kutusu (balkutusu.com) üzerinde listelenen {kw} ilanları, Kuşadası'nın farklı mahalle ve sokak dokusuna göre filtrelenmiş güncel profiller sunar. {ctx['geo_fact']} {kw} planlarken bu coğrafi bağlamı göz önünde bulundurmak, zaman kaybını azaltır.",
    ]
    parts.append(h2(f"{kw} — Kuşadası Rehberi"))
    parts.append(p(rng.choice(openings)))

    if ctx["mahalle"]:
        parts.append(h2(f"{ctx['mahalle']} Mahallesi ve Çevre Coğrafyası"))
        parts.append(h3(f"{ctx['mahalle']} — Ulaşım ve Buluşma Noktaları"))
        landmarks = pick_unique(rng, LANDMARKS, 5)
        for lm in landmarks:
            parts.append(p(
                f"{ctx['mahalle']} bölgesinden {lm} yönüne ulaşım, Kuşadası'da {kw} randevularında sık kullanılan referans noktalarındandır. "
                f"Özellikle yaz sezonunda {lm} çevresi yoğunlaşır; {kw} buluşması planlanırken trafik, taksi ve yürüme mesafesi önceden hesaplanmalıdır. "
                f"{ctx['geo_fact']} Bu mahallede {kw} arayanların profil açıklamasındaki mahalle bilgisini {lm} referansıyla çapraz kontrol etmesi önerilir."
            ))

    if ctx["street"]:
        ltype = ctx["loc_type"] or "cadde"
        parts.append(h2(f"{ctx['street']} — {ctx['mahalle']} {ltype.title()} Detayı"))
        street_paras = [
            f"{ctx['street']}, {ctx['mahalle']} mahallesi sınırları içinde Kuşadası'nın yerel adres dokusunu yansıtan bir {ltype}dir. {kw} hizmeti bu {ltype} hattında veya yakın çevresinde planlandığında, bina girişi, otopark ve gece saatlerinde ulaşılabilirlik ayrıca netleştirilmelidir.",
            f"Kuşadası'da {ctx['street']} üzerinde veya komşu sokaklarda {kw} talebi, merkezi konuma yakınlık ve konaklama yoğunluğu nedeniyle artış gösterir. {ctx['street']} için profil seçerken fotoğraf, yaş aralığı ve hizmet etiketlerinin {kw} beklentinizle uyumlu olduğundan emin olun.",
            f"{ctx['mahalle']} — {ctx['street']} aksında {kw} görüşmeleri genelde kısa süreli randevu veya otel buluşması formatında ilerler. Kuşadası'nın Ege ikliminde {ctx['street']} çevresi akşam saatlerinde hareketlenir; {kw} randevu saatini buna göre ayarlamak pratik bir adımdır.",
        ]
        for _ in range(4):
            parts.append(p(rng.choice(street_paras)))

    if ctx["variant"]:
        parts.append(h2(f"{ctx['variant']} Hizmet Kapsamı — Kuşadası"))
        variant_notes = {
            "Türk Escort": "Yerel dil avantajı, kültürel uyum ve hızlı iletişim Türk escort profillerinin öne çıkan yanlarıdır.",
            "Rus Escort": "Rus escort profilleri Kuşadası'da yabancı misafir yoğunluğunun arttığı sezonlarda talep görür.",
            "Anal Escort": "Anal hizmet kapsamı profil bazında değişir; sınırlar ve ek ücretler randevu öncesi yazılı teyit edilmelidir.",
            "Oral Escort": "Oral hizmet etiketi taşıyan profillerde hijyen ve karşılıklı konfor önceliklidir.",
            "CIM Escort": "CIM hizmeti her profilde sunulmayabilir; Kuşadası'da {kw} randevusunda kapsamı açıkça sorun.",
            "CIF Escort": "CIF detayı profil açıklamasında veya ilk mesajda netleştirilmelidir.",
            "VIP Escort": "VIP profiller öncelikli randevu, üst segment konaklama ve genişletilmiş hizmet paketi sunabilir.",
            "Masaj Escort": "Masaj eşliğinde escort, Kuşadası otellerinde ve özel dairelerde sık talep edilir.",
            "Otel Escort": "Otel escort buluşmalarında resepsiyon prosedürü ve oda numarası paylaşımı gizlilik kurallarına uygun yapılmalıdır.",
            "Eve Gelen Escort": "Eve gelen hizmette adres doğrulama ve güvenlik karşılıklı sorumluluktur.",
        }
        note = variant_notes.get(ctx["variant"], f"{ctx['variant']} Kuşadası escort pazarında niş bir arama segmentidir; profil etiketlerini dikkatle okuyun.")
        note = note.replace("{kw}", kw)
        for i in range(5):
            parts.append(p(
                f"{kw} kapsamında {ctx['variant']}: {note} "
                f"Kuşadası {ctx['mahalle'] or 'merkez'} bölgesinde {ctx['variant']} etiketli ilanlar, "
                f"Bal Kutusu filtreleriyle {ctx['street'] or 'mahalle geneli'} adreslerine göre listelenir. "
                f"Profil ile ilk temasta hizmet sınırları, süre ve ücret {ctx['variant']} için ayrıca teyit edilmelidir."
            ))

    parts.append(h2("Kuşadası Ulaşım, Sezon ve Randevu Pratiği"))
    parts.append(h3(f"{kw} Randevusu İçin Pratik İpuçları"))
    transport = [
        f"Kuşadası'na Efes Havalimanı veya İzmir üzerinden gelen ziyaretçiler için {kw} randevusu, varış saatine göre planlanmalıdır. İlçe içi ulaşımda dolmuş, taksi ve yürüme mesafesi mahalleler arası farklılık gösterir.",
        f"Yaz sezonunda (Haziran–Eylül) Kuşadası'da {kw} talebi zirve yapar; hafta içi gündüz saatleri daha esnek müsaitlik sunabilir. Kış aylarında {kw} profilleri sınırlı ama düzenli hizmet verebilir.",
        f"Marina, liman ve otogar çevresi {kw} için yaygın buluşma referanslarıdır. Adres paylaşımında sokak ve bina adı net olmalı; Kuşadası'da bazı sokaklar benzer isim taşıyabileceğinden {ctx['street'] or ctx['mahalle'] or 'merkez'} vurgusu önemlidir.",
    ]
    for t in transport * 2:
        parts.append(p(t.replace("Kuşadası'da", f"Kuşadası'da {kw} için")))

    parts.append(h2(f"{kw} — Gizlilik, Güven ve İletişim"))
    for _ in range(4):
        parts.append(p(
            f"Kuşadası {kw} görüşmelerinde karşılıklı saygı ve gizlilik temel ilkedir. Telegram veya WhatsApp üzerinden yazışırken gereksiz kişisel veri paylaşmayın. "
            f"Profil fotoğrafları ile gerçek kişi uyumu {kw} deneyimini etkiler; şüpheli durumlarda randevuyu iptal etmekten çekinmeyin. "
            f"balkutusu.com ana portalı {kw} kategorilerini düzenli günceller; sahte veya yanıltıcı ilanları bildirmek topluluk kalitesini korur."
        ))

    parts.append(h2(f"Sık Sorulan Sorular — {kw}"))
    faq_pool = [
        (f"{kw} için en uygun mahalle hangisi?", f"{ctx['mahalle'] or 'Kadınlar Denizi ve Merkez'} Kuşadası'da {kw} için sık tercih edilir; profilin lokasyon etiketine bakın."),
        (f"Kuşadası'da {kw} fiyatları nasıl belirlenir?", f"Sezon, süre, VIP statüsü ve hizmet kapsamı fiyatı etkiler; {kw} için paket detayını mesajda sorun."),
        (f"{kw} güvenilir mi?", f"İletişimi net, fotoğrafları tutarlı profilleri tercih edin; {kw} için acele baskı yapan ilanlardan kaçının."),
        (f"{ctx['street'] or 'Bu bölgede'} {kw} buluşması nasıl planlanır?", f"Saat, adres ve süre yazılı netleştirilmeli; Kuşadası'da {kw} için otel veya özel adres seçenekleri profille uyumlu olmalı."),
        (f"{ctx['variant'] or 'Escort'} ile {kw} farkı nedir?", f"Profil etiketleri hizmet kapsamını gösterir; {kw} aramasında doğru varyant filtresi zaman kazandırır."),
        (f"{kw} için hangi iletişim kanalı kullanılır?", f"Telegram ve WhatsApp yaygındır; {kw} profillerinde yanıt süresini kontrol edin."),
        (f"Kuşadası {kw} sezonu ne zaman yoğun?", "Haziran–Eylül en yoğun dönemdir; hafta içi gündüz daha esnek müsaitlik sunabilir."),
    ]
    parts.append('<section class="hive-faq">')
    for q, a in pick_unique(rng, faq_pool, 6):
        parts.append(h3(q))
        parts.append(p(a.format(kw=kw)))
    parts.append("</section>")

    parts.append(h2(f"Sonuç — Kuşadası {kw}"))
    closings = [
        f"Kuşadası {kw} rehberi, {ctx['mahalle'] or 'ilçe geneli'} ve {ctx['street'] or 'sokak/cadde'} bağlamında arama yapan ziyaretçiler için yapılandırılmıştır. Doğru profil, net iletişim ve lokasyon teyidi {kw} deneyiminin üç temel unsurudur. Güncel ilanlar için balkutusu.com ana portalını ve {kw} kategori sayfasını takip edebilirsiniz.",
        f"{kw} Kuşadası escort aramasında GEO uyumlu içerik, gerçek mahalle ve adres bilgisiyle anlam kazanır. Bu sayfa {ctx['slug']} kategorisine özel hazırlanmıştır; diğer mahalle ve varyant sayfalarından farklı bölüm sırası ve yerel detaylar içerir.",
    ]
    parts.append(p(rng.choice(closings)))

    body = "\n".join(parts)
    wc = word_count(body)

    # Benzersizlik: slug hash ile ek paragraf varyasyonları
    extras = [
        f"Kuşadası Aydın il sınırlarında; {kw} aramalarında 'Kuşadası escort', 'Kuşadası VIP' ve mahalle bazlı long-tail kelimeler doğal şekilde hedeflenir.",
        f"{ctx['geo_fact']} SEO ve kullanıcı deneyimi açısından {kw} sayfası, kopya içerikten kaçınarak yerel bağlam sunar.",
        f"Ege Denizi kıyısındaki Kuşadası'nda {kw} planlayanlar; rüzgarlı günlerde sahil mahallelerinde ulaşım alternatiflerini da göz önünde bulundurmalıdır.",
    ]
    idx = 0
    while wc < TARGET_MIN and idx < 30:
        parts.append(p(extras[rng.randint(0, len(extras) - 1)] + f" ({ctx['slug']}-{idx})"))
        body = "\n".join(parts)
        wc = word_count(body)
        idx += 1

    while wc > TARGET_MAX:
        last_p = body.rfind("<p>")
        if last_p == -1:
            break
        body = body[:last_p]
        wc = word_count(body)

    return body


def get_terms_with_meta(url: str, host: str | None) -> list[dict]:
    raw = wp(
        ["eval", """
$terms = get_terms(array('taxonomy'=>'companion_category','hide_empty'=>false,'number'=>0));
$out = array();
foreach ($terms as $t) {
  if (preg_match('/^\\d+$/', $t->name)) continue;
  $out[] = array(
    'term_id' => (int)$t->term_id,
    'name' => $t->name,
    'slug' => $t->slug,
    'meta' => array(
      'hive_cat_group' => get_term_meta($t->term_id,'hive_cat_group',true),
      'hive_geo_mahalle' => get_term_meta($t->term_id,'hive_geo_mahalle',true),
      'hive_geo_street' => get_term_meta($t->term_id,'hive_geo_street',true),
      'hive_variant' => get_term_meta($t->term_id,'hive_variant',true),
      'hive_loc_type' => get_term_meta($t->term_id,'hive_loc_type',true),
    ),
  );
}
echo json_encode($out);
"""],
        url,
        host,
    )
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def save_term_meta(term_id: str, content: str, url: str, host: str | None) -> None:
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    wp(["eval", f"update_term_meta({int(term_id)}, 'hive_seo_body', base64_decode('{b64}'));"], url, host)


def save_option(content: str, url: str, host: str | None) -> None:
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    wp(["eval", f"update_option('hive_site_seo_body', base64_decode('{b64}'));"], url, host)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    ap.add_argument("--url", default="https://balkutusu.com")
    ap.add_argument("--categories-only", action="store_true")
    ap.add_argument("--sites-only", action="store_true")
    ap.add_argument("--limit-cats", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--only-group", default="", help="variant, mahalle, location, escort_tip")
    args = ap.parse_args()

    if not args.sites_only:
        print("=== Kategori SEO (GEO uyumlu) ===", flush=True)
        terms = get_terms_with_meta(args.url, args.host)
        if args.only_group:
            terms = [t for t in terms if (t.get("meta") or {}).get("hive_cat_group") == args.only_group]
        terms = terms[args.offset :]
        n = 0
        for t in terms:
            ctx = term_context(t)
            body = generate_body(ctx)
            wc = word_count(body)
            save_term_meta(str(t["term_id"]), body, args.url, args.host)
            n += 1
            if n % 25 == 0 or n <= 3:
                print(f"  [{n}] {t['name'][:60]} — {wc} kelime", flush=True)
            if args.limit_cats and n >= args.limit_cats:
                break
        print(f"Kategori SEO tamam: {n}", flush=True)

    if not args.categories_only:
        print("=== Subdomain SEO ===", flush=True)
        raw_sites = wp(["site", "list", "--format=json", "--fields=blog_id,url,domain"], args.url, args.host)
        sites = json.loads(raw_sites) if raw_sites else []
        for row in sites:
            domain = row.get("domain", "")
            site_url = row.get("url", "")
            if not domain or not site_url:
                continue
            slug = domain.replace(".balkutusu.com", "")
            if domain == "balkutusu.com":
                ctx = term_context({"slug": "kusadasi-escort", "name": "Kuşadası Escort", "meta": {}})
            else:
                ctx = term_context({"slug": slug, "name": slug.replace("-", " ").title() + " Kuşadası Escort", "meta": {}})
            body = generate_body(ctx)
            save_option(body, site_url, args.host)
            print(f"  {domain} — {word_count(body)} kelime", flush=True)

    print("Tamamlandı.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
