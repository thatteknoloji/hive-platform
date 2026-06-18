"""SSS sayfası üretim motoru — SEO/GEO uyumlu FAQ içerik."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

import requests

from app import config
from app.moduller.modul_base import modul_hash, simdi

SYSTEM_PROMPT = """Sen BalKutusu.com için SEO ve GEO uyumlu içerik üreten bir SSS sayfası üretim motorusun.

Görevin: Verilen şehir, ilçe, kategori ve alt kategori bilgisine göre otomatik SSS sayfası üretmek.

Her SSS sayfası:
- Tamamen özgün olmalı.
- Aynı kalıp cevapları tekrar etmemeli.
- Yerel arama niyetine uygun olmalı.
- Google'da indekslenebilir kaliteye sahip olmalı.
- AI arama motorlarının alıntılayabileceği net cevaplar içermeli.
- Kullanıcıya gerçekten bilgi vermeli.
- Gereksiz uzun, boş ve genel ifadelerden kaçınmalı.

Çıktı formatı:
1. SEO Başlığı (60 karakter max)
2. Meta Açıklama (155 karakter max)
3. URL Slug (Türkçe karakter yok, küçük harf, tireli)
4. H1 Başlık
5. Kısa Giriş (100-150 kelime)
6. SSS Listesi (20+ soru-cevap, her cevap 50-120 kelime)
7. İç Link Önerileri
8. Schema.org FAQ JSON-LD

Kurallar:
- Uydurma işletme adı verme.
- Kesin olmayan fiyat, adres, telefon, ruhsat bilgisi verme.
- "En iyi", "garanti", "kesin" gibi abartılı ifadeler kullanma.
- Yerel arama niyetleri kullanılmalı: nerede, nasıl gidilir, ne zaman açık, ücretli mi, güvenli mi, kimler gider, sezon ne zaman, nelere dikkat edilmeli.

SSS formatı:
S: Soru metni
C: Cevap metni

İç link önerileri satır başına bir link metni ve açıklama.
Schema JSON-LD geçerli JSON olmalı."""

TR_MAP = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})

MIN_INTRO_WORDS = 100
MAX_INTRO_WORDS = 150
MIN_FAQ_COUNT = 20
MIN_ANSWER_WORDS = 50
MAX_ANSWER_WORDS = 120
MIN_HTML_CHARS = 3000
DEFAULT_SITE = "https://www.balkutusu.com"


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.translate(TR_MAP).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80] or "sss-sayfasi"


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text or "", re.UNICODE))


def _expand_text(text: str, min_words: int, max_words: int, padding: list[str]) -> str:
    combined = (text or "").strip()
    if not padding:
        return combined
    idx = 0
    while _word_count(combined) < min_words and idx < len(padding) * 4:
        combined = f"{combined} {padding[idx % len(padding)]}".strip()
        idx += 1
    words = combined.split()
    if len(words) > max_words:
        combined = " ".join(words[:max_words])
    return combined


def _context_padding(city: str, district: str, category: str, subcategory: str, keyword: str) -> list[str]:
    return [
        f"{district}, {city} bölgesinde {subcategory} planlaması yaparken ulaşım, konaklama ve sezon yoğunluğunu hesaba katmak önemlidir.",
        f"{category} kategorisinde {keyword} arayan kullanıcılar güncel, yerel ve güvenilir kaynaklardan bilgi almayı tercih eder.",
        f"{district} çevresinde ziyaret öncesi çalışma saatleri, ödeme yöntemleri ve yerel düzenlemeler hakkında araştırma yapmak faydalıdır.",
        f"{city} ve {district} odaklı içerikler, bölgeye yeni gelen ziyaretçiler için pratik planlama ipuçları sunar.",
        f"Yoğun sezonlarda erken planlama, {subcategory} deneyimini daha rahat hale getirebilir.",
    ]


def _build_default_internal_links(
    city: str,
    district: str,
    category: str,
    subcategory: str,
    keyword: str,
    site: str = DEFAULT_SITE,
) -> list[dict[str, str]]:
    site = (site or DEFAULT_SITE).rstrip("/")
    dslug = _slugify(district)
    kslug = _slugify(keyword)
    return [
        {"text": f"{district} ilan ve profil listesi", "url": f"{site}/profil/"},
        {"text": f"{district} {subcategory} rehberi", "url": f"{site}/{dslug}/" if dslug else site},
        {"text": f"{city} {category} ana sayfa", "url": site},
        {"text": f"{keyword} yerel SSS", "url": f"{site}/{kslug}/" if kslug else site},
    ]


def _enforce_page_limits(
    page: dict[str, Any],
    city: str,
    district: str,
    category: str,
    subcategory: str,
    keyword: str,
) -> dict[str, Any]:
    padding = _context_padding(city, district, category, subcategory, keyword)
    intro = page.get("intro") or ""
    if _word_count(intro) < MIN_INTRO_WORDS:
        intro = _expand_text(intro, MIN_INTRO_WORDS, MAX_INTRO_WORDS, padding)
    elif _word_count(intro) > MAX_INTRO_WORDS:
        intro = " ".join(intro.split()[:MAX_INTRO_WORDS])
    page["intro"] = intro

    enforced: list[dict[str, str]] = []
    for faq in page.get("faqs") or []:
        answer = faq.get("answer", "")
        wc = _word_count(answer)
        if wc < MIN_ANSWER_WORDS:
            answer = _expand_text(answer, MIN_ANSWER_WORDS, MAX_ANSWER_WORDS, padding)
        elif wc > MAX_ANSWER_WORDS:
            answer = " ".join(answer.split()[:MAX_ANSWER_WORDS])
        enforced.append({"question": faq.get("question", "").strip(), "answer": answer})
    page["faqs"] = enforced

    links = page.get("internal_links") or []
    fixed_links: list[dict[str, str]] = []
    for link in links:
        url = (link.get("url") or "").strip()
        text = (link.get("text") or "").strip()
        if text:
            fixed_links.append({"text": text, "url": url if url and url != "#" else ""})
    if not fixed_links:
        fixed_links = _build_default_internal_links(city, district, category, subcategory, keyword)
    page["internal_links"] = fixed_links
    return page


def _page_word_stats(page: dict[str, Any]) -> dict[str, int]:
    faqs = page.get("faqs") or []
    answer_words = [_word_count(f.get("answer", "")) for f in faqs]
    return {
        "intro_words": _word_count(page.get("intro", "")),
        "faq_count": len(faqs),
        "min_answer_words": min(answer_words) if answer_words else 0,
        "max_answer_words": max(answer_words) if answer_words else 0,
        "html_chars": len(page.get("html") or ""),
    }


def _ollama_generate(prompt: str, system: str = SYSTEM_PROMPT) -> tuple[str, bool]:
    from app.moduller import llm_router
    text, engine = llm_router.generate(prompt, system=system, max_tokens=8000, min_length=200)
    return text, bool(text and engine)


def _parse_faqs(text: str) -> list[dict[str, str]]:
    faqs: list[dict[str, str]] = []
    blocks = re.split(r"(?=^S:\s*)", text, flags=re.M)
    for block in blocks:
        block = block.strip()
        if not block.startswith("S:"):
            continue
        m = re.match(r"S:\s*(.+?)\n+C:\s*(.+)", block, re.S)
        if m:
            faqs.append({"question": m.group(1).strip(), "answer": m.group(2).strip()})
    if not faqs:
        for q, a in re.findall(r"(?:Soru|Q)[:\s]+(.+?)\n+(?:Cevap|A)[:\s]+(.+?)(?=\n(?:Soru|Q)[:\s]|\Z)", text, re.S | re.I):
            faqs.append({"question": q.strip(), "answer": a.strip()})
    return faqs


def _parse_section(text: str, labels: list[str]) -> str:
    for label in labels:
        m = re.search(
            rf"(?:^|\n)\s*(?:\d+\.\s*)?{re.escape(label)}\s*[:\-]?\s*(.+?)(?=\n\s*(?:\d+\.\s*)?(?:SEO|Meta|URL|H1|Kısa|SSS|İç|Schema)|\Z)",
            text,
            re.S | re.I,
        )
        if m:
            return m.group(1).strip()
    return ""


def _parse_response(raw: str, city: str, district: str, keyword: str) -> dict[str, Any]:
    seo_title = _parse_section(raw, ["SEO Başlığı", "SEO Basligi"])[:60]
    meta_desc = _parse_section(raw, ["Meta Açıklama", "Meta Aciklama"])[:155]
    slug = _parse_section(raw, ["URL Slug", "Slug"])
    h1 = _parse_section(raw, ["H1 Başlık", "H1 Baslik", "H1"])
    intro = _parse_section(raw, ["Kısa Giriş", "Kisa Giris", "Giriş", "Giris"])
    faq_text = _parse_section(raw, ["SSS Listesi", "SSS", "Sık Sorulan Sorular"])
    links_text = _parse_section(raw, ["İç Link Önerileri", "Ic Link Onerileri", "İç Linkler"])
    schema_text = _parse_section(raw, ["Schema.org FAQ JSON-LD", "Schema", "JSON-LD"])

    faqs = _parse_faqs(faq_text or raw)
    if not slug:
        slug = _slugify(f"{district}-{keyword}-sss")
    if not seo_title:
        seo_title = f"{district} {keyword} — SSS Rehberi"[:60]
    if not h1:
        h1 = f"{district} {keyword} Hakkında Sık Sorulan Sorular"
    if not meta_desc:
        meta_desc = f"{district}, {city} bölgesinde {keyword} hakkında merak edilen sorular ve yerel rehber bilgileri."[:155]

    internal_links: list[dict[str, str]] = []
    for line in (links_text or "").splitlines():
        line = line.strip().lstrip("-•*")
        if line:
            internal_links.append({"text": line, "url": "#"})

    schema: dict | None = None
    if schema_text:
        try:
            schema = json.loads(re.search(r"\{.*\}", schema_text, re.S).group(0))
        except (json.JSONDecodeError, AttributeError):
            schema = None

    return {
        "seo_title": seo_title,
        "meta_description": meta_desc,
        "slug": _slugify(slug),
        "h1": h1,
        "intro": intro,
        "faqs": faqs,
        "internal_links": internal_links,
        "schema": schema,
        "raw": raw,
    }


def _fallback_faqs(city: str, district: str, category: str, subcategory: str, keyword: str) -> list[dict[str, str]]:
    offset = modul_hash(f"{city}{district}{category}{subcategory}{keyword}") % 22
    templates = [
        (f"{district} bölgesinde {subcategory} nasıl bulunur?", f"{district}, {city} sınırları içinde {subcategory} arayanlar için merkez ve çevre mahallelerde yoğunlaşan seçenekler bulunur. Sezon ve günün saatine göre yoğunluk değişebilir; ziyaret öncesi güncel çalışma saatlerini kontrol etmek faydalıdır."),
        (f"{keyword} için en uygun ziyaret saatleri hangileri?", f"{district} çevresinde {category} deneyimi genellikle akşam saatlerinde yoğunlaşır. Hafta içi daha sakin, hafta sonu daha kalabalık olabilir. Yerel etkinlik takvimini göz önünde bulundurun."),
        (f"{district} {subcategory} ücretli mi?", f"Çoğu {subcategory} işletmesi giriş veya hizmet bazlı ücretlendirme uygular; fiyatlar mekâna ve sezona göre değişir. Kesin tutarlar için işletmeyle doğrudan iletişim kurmak gerekir."),
        (f"{city} {district} bölgesine nasıl gidilir?", f"{district}, {city} içinde toplu taşıma, taksi veya özel araçla ulaşılabilir. Merkez noktalara yakın konaklayan ziyaretçiler yürüyerek de erişebilir."),
        (f"{subcategory} ziyareti güvenli mi?", f"Kalabalık ve aydınlatılmış bölgelerde hareket etmek, kişisel eşyalarınıza dikkat etmek ve resmi işletmeleri tercih etmek genel güvenlik önerileridir."),
        (f"{district} {category} sezonu ne zaman başlar?", f"{city} kıyı bölgelerinde sezon genellikle ilkbahar sonundan sonbahara kadar uzanır. {district} için yoğun dönem yaz aylarıdır."),
        (f"{keyword} arayanlar kimlerdir?", f"Yerel sakinler, tatilciler ve {city} bölgesini keşfeden ziyaretçiler {subcategory} hakkında bilgi arar. Aileler, çiftler ve arkadaş grupları farklı mekân tercihleri yapabilir."),
        (f"{district} bölgesinde nelere dikkat edilmeli?", f"Rezervasyon gereksinimi, kıyafet kuralları, yaş sınırı ve ödeme yöntemleri mekândan mekâna değişir. Yerel düzenlemelere ve işletme kurallarına uymak önemlidir."),
        (f"{subcategory} için rezervasyon gerekli mi?", f"Popüler dönemlerde ve hafta sonları rezervasyon yapmak yer bulmayı kolaylaştırır. Daha sakin günlerde kapıda yer bulmak mümkün olabilir."),
        (f"{district} çevresinde alternatif {category} seçenekleri var mı?", f"{city} ve komşu ilçelerde farklı tarzda {category} mekânları bulunur. {district} merkez dışındaki mahalleler de keşfedilmeye değer olabilir."),
        (f"{keyword} ile ilgili yerel kurallar nelerdir?", f"Alkol tüketimi, sigara kullanımı ve gürültü düzenlemeleri {city} yönetmeliklerine tabidir. İşletmelerin kendi kurallarını da inceleyin."),
        (f"{district} {subcategory} için park yeri var mı?", f"Merkez bölgelerde sokak parkı veya ücretli otoparklar bulunabilir. Yoğun saatlerde erken gitmek park sorununu azaltır."),
        (f"{subcategory} mekânları hangi günler açık?", f"Hafta içi ve hafta sonu çalışma saatleri işletmeye göre değişir. Resmi tatil günlerinde bazı mekânlar kapalı olabilir."),
        (f"{district} bölgesinde {category} bütçesi nasıl planlanır?", f"Giriş ücreti, içecek ve ek hizmetler ayrı kalemlerdir. Bütçenizi belirlerken sezon ve mekân tipini hesaba katın."),
        (f"{keyword} hakkında yerel ipuçları nelerdir?", f"Yerel halkın yoğun olmadığı saatleri tercih etmek, önceden rota planlamak ve {district} mahallelerini keşfetmek deneyimi zenginleştirir."),
        (f"{city} {district} turistler için uygun mu?", f"Evet, {district} turistik bir bölge olduğundan {subcategory} arayan yabancı ziyaretçiler için de bilgi kaynakları mevcuttur."),
        (f"{subcategory} için yaş sınırı var mı?", f"Birçok {category} mekânında yaş sınırı uygulanır; genellikle 18 yaş altına giriş kısıtlıdır. Kimlik kontrolü yapılabilir."),
        (f"{district} bölgesinde ödeme yöntemleri nelerdir?", f"Nakit ve banka kartı yaygındır; bazı işletmeler yalnızca kart kabul edebilir. Ödeme öncesi bilgi almak iyi bir pratiktir."),
        (f"{keyword} deneyimi için ne giymeli?", f"Mekânın tarzına uygun kıyafet tercih edin. Bazı mekânlar smart casual, bazıları daha rahat kıyafet bekleyebilir."),
        (f"{district} {subcategory} hava durumundan etkilenir mi?", f"Açık hava etkinlikleri hava koşullarından etkilenebilir. Kapalı mekânlar yıl boyu hizmet verebilir."),
        (f"{city} bölgesinde {category} rehberi nereden bulunur?", f"Yerel turizm ofisleri, güncel web kaynakları ve {district} odaklı içerikler planlama için yardımcı olur."),
    ]
    rotated = templates[offset:] + templates[:offset]
    return [{"question": q, "answer": a} for q, a in rotated[:22]]


def _build_schema(faqs: list[dict[str, str]], h1: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "name": h1,
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["question"],
                "acceptedAnswer": {"@type": "Answer", "text": f["answer"]},
            }
            for f in faqs[:25]
        ],
    }


def build_html(page: dict[str, Any]) -> str:
    parts: list[str] = []
    if page.get("h1"):
        parts.append(f"<h1>{page['h1']}</h1>")
    if page.get("intro"):
        parts.append(f"<p>{page['intro']}</p>")
    parts.append("<h2>Sık Sorulan Sorular</h2>")
    for faq in page.get("faqs", []):
        parts.append(f"<h3>{faq['question']}</h3>")
        parts.append(f"<p>{faq['answer']}</p>")
    links = page.get("internal_links") or []
    if links:
        parts.append("<h2>İlgili Sayfalar ve İlanlar</h2><ul>")
        for link in links:
            text = link.get("text", "")
            url = (link.get("url") or "").strip()
            if url:
                parts.append(f'<li><a href="{url}">{text}</a></li>')
            else:
                parts.append(f"<li>{text}</li>")
        parts.append("</ul>")
    schema = page.get("schema") or _build_schema(page.get("faqs", []), page.get("h1", ""))
    parts.append(
        f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'
    )
    return "\n".join(p for p in parts if p)


def generate_sss_page(
    city: str,
    district: str,
    category: str,
    subcategory: str,
    main_keyword: str,
    secondary_keywords: str = "",
) -> dict[str, Any]:
    prompt = f"""Şehir: {city}
İlçe: {district}
Kategori: {category}
Alt kategori: {subcategory}
Hedef anahtar kelime: {main_keyword}
Yan anahtar kelimeler: {secondary_keywords}

Yukarıdaki bilgilere göre bir SSS sayfası üret. Formatı birebir takip et.
En az 20 soru-cevap üret. Her cevap 50-120 kelime olsun."""

    raw, ai_used = _ollama_generate(prompt)
    if ai_used and raw:
        page = _parse_response(raw, city, district, main_keyword)
    else:
        page = {
            "seo_title": f"{district} {main_keyword} — SSS"[:60],
            "meta_description": f"{district}, {city} {subcategory} hakkında sık sorulan sorular ve yerel rehber."[:155],
            "slug": _slugify(f"{district}-{main_keyword}-sss"),
            "h1": f"{district} {main_keyword} Hakkında Sık Sorulan Sorular",
            "intro": (
                f"{district}, {city} bölgesinde {subcategory} arayanlar için hazırlanan bu SSS sayfası, "
                f"{category} kategorisinde yerel arama niyetlerine yanıt verir. Ulaşım, sezon, güvenlik ve "
                f"pratik planlama sorularını {main_keyword} odağında ele alır."
            ),
            "faqs": _fallback_faqs(city, district, category, subcategory, main_keyword),
            "internal_links": [
                {"text": f"{city} {category} ana kategori sayfası", "url": "#"},
                {"text": f"{district} ilan ve rehber sayfaları", "url": "#"},
                {"text": f"{city} blog ve güncel içerikler", "url": "#"},
            ],
            "schema": None,
            "raw": "",
        }

    if len(page.get("faqs", [])) < MIN_FAQ_COUNT:
        extra = _fallback_faqs(city, district, category, subcategory, main_keyword)
        existing_q = {f["question"] for f in page["faqs"]}
        for e in extra:
            if e["question"] not in existing_q:
                page["faqs"].append(e)
            if len(page["faqs"]) >= MIN_FAQ_COUNT + 2:
                break

    page = _enforce_page_limits(page, city, district, category, subcategory, main_keyword)

    if not page.get("schema"):
        page["schema"] = _build_schema(page["faqs"], page["h1"])

    page["html"] = build_html(page)
    page["word_stats"] = _page_word_stats(page)
    page["ai_ollama"] = ai_used
    page["tarih"] = simdi()
    return page


class SSSGenerator:
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT

    def generate(
        self,
        city: str,
        district: str,
        category: str,
        subcategory: str,
        main_keyword: str,
        secondary_keywords: str = "",
    ) -> dict[str, Any]:
        return generate_sss_page(
            city, district, category, subcategory,
            main_keyword, secondary_keywords,
        )


sss_generator = SSSGenerator()
