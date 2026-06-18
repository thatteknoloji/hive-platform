import random
import hashlib
from datetime import datetime, timedelta

HIZMET_KATEGORILERI = {
    "seo": ["seo hizmetleri", "seo danışmanlığı", "seo ajansı", "seo uzmanı", "seo paketleri",
            "kurumsal seo", "e-ticaret seo", "yerel seo", "teknik seo", "seo denetimi"],
    "yazilim": ["yazılım geliştirme", "web tasarım", "mobil uygulama", "e-ticaret yazılımı",
                "özel yazılım", "sap danışmanlığı", "bulut çözümleri", "veritabanı yönetimi"],
    "dijital": ["dijital pazarlama", "sosyal medya yönetimi", "google reklam", "smm panel",
                "e-posta pazarlama", "performans pazarlama", "inovasyon danışmanlığı"],
    "ticaret": ["e-ticaret sitesi", "dropshipping", "dijital ürün", "online satış",
                "pazaryeri yönetimi", "sanal pos", "ödeme sistemleri"],
    "saglik": ["sağlık turizmi", "estetik cerrahi", "diş kliniği", "saç ekimi",
               "göz hastalıkları", "tüp bebek", "fizik tedavi"],
    "hukuk": ["avukat", "hukuk bürosu", "boşanma avukatı", "ceza avukatı",
              "icra avukatı", "gayrimenkul avukatı", "aile hukuku"],
    "emlak": ["emlak danışmanı", "konut kredisi", "inşaat firması", "gayrimenkul",
              "kira", "satılık ev", "kiralık daire", "arsa"],
    "egitim": ["özel ders", "online eğitim", "kurs", "sertifika programı", "akademi",
               "dil okulu", "mesleki eğitim", "koçluk"],
}

LOKASYONLAR = [
    "İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep",
    "Mersin", "Kayseri", "Eskişehir", "Diyarbakır", "Samsun", "Trabzon", "Erzurum",
    "Denizli", "Batman", "Malatya", "Manisa", "Elazığ", "Van", "Şanlıurfa", "Balıkesir",
    "Kocaeli", "Sakarya", "Muğla", "Aydın", "Tekirdağ", "Isparta", "Edirne",
]

ILCELER = {
    "İstanbul": ["Kadıköy", "Beşiktaş", "Şişli", "Üsküdar", "Maltepe", "Kartal", "Pendik",
                 "Beylikdüzü", "Başakşehir", "Bakırköy", "Sarıyer", "Ümraniye", "Ataşehir"],
    "Ankara": ["Çankaya", "Keçiören", "Yenimahalle", "Mamak", "Etimesgut", "Sincan",
               "Altındağ", "Gölbaşı", "Polatlı"],
    "İzmir": ["Karşıyaka", "Bornova", "Konak", "Buca", "Çiğli", "Balçova", "Gaziemir",
              "Narlıdere", "Urla", "Menemen"],
    "Bursa": ["Nilüfer", "Osmangazi", "Yıldırım", "Mudanya", "Gemlik", "Gürsu"],
    "Antalya": ["Muratpaşa", "Kepez", "Konyaaltı", "Alanya", "Manavgat", "Serik"],
}

REKABET_ANAHTARLARI = {
    "düşük": ["nedir", "nasıl yapılır", "fiyatları", "ücreti", "yorumları", "ne işe yarar"],
    "orta": ["eğitimi", "kursu", "sertifikası", "danışmanlık", "hizmeti", "firması", "ajansı"],
    "yüksek": ["satın al", "kiralık", "fiyat", "indirim", "kapmanyası", "ucuz", "en iyi"],
}

HACIM_ANAHTARLARI = {
    "1000+": ["sigorta", "kredi", "kira", "satılık", "fiyatları", "indirim", "kampanya"],
    "500-1000": ["hizmeti", "eğitimi", "kursu", "danışmanlık", "tedavisi", "firması"],
    "100-500": ["uzmanı", "merkezi", "kliniği", "bürosu", "ajansı", "atölyesi"],
    "0-100": ["nedir", "ne işe yarar", "sertifikası", "belgesi", "raporu"],
}

def _normalize(kelime):
    return kelime.strip().lower()

def _hash_seed(kelime):
    h = int(hashlib.md5(kelime.encode("utf-8")).hexdigest()[:8], 16)
    return h

def _tahmin_rekabet(kelime):
    kl = _normalize(kelime)
    for seviye, anahtarlar in REKABET_ANAHTARLARI.items():
        if any(a in kl for a in anahtarlar):
            return seviye
    return "orta"

def _tahmin_hacim(kelime):
    kl = _normalize(kelime)
    for hacim, anahtarlar in HACIM_ANAHTARLARI.items():
        if any(a in kl for a in anahtarlar):
            return hacim
    return "100-500"

def _tahmin_zorluk(kelime):
    h = _hash_seed(kelime)
    return h % 100

def _tahmin_cpc(kelime):
    h = _hash_seed(kelime)
    return round((h % 500 + 50) / 100, 2)

def _tahmin_niyet(kelime):
    kl = _normalize(kelime)
    if any(w in kl for w in ["satın al", "fiyat", "kiralık", "ucuz", "indirim"]):
        return "transactional"
    elif any(w in kl for w in ["en iyi", "nerede", "karşılaştırma", "vs", "alternatifi"]):
        return "commercial"
    elif any(w in kl for w in ["nedir", "nasıl", "ne işe", "tarihi", "örnek"]):
        return "informational"
    return "commercial"

def _ilgili_kelimeler_uret(ana_kelime, limit=30):
    kl = _normalize(ana_kelime)
    sonuclar = set()
    sonuclar.add(ana_kelime)

    kategori = None
    for kat, kelimeler in HIZMET_KATEGORILERI.items():
        if any(k in kl for k in kelimeler):
            kategori = kat
            break
    if not kategori:
        for kat, kelimeler in HIZMET_KATEGORILERI.items():
            if any(k in kl.split() for k in kelimeler):
                kategori = kat
                break
    if not kategori:
        kategori = random.choice(list(HIZMET_KATEGORILERI.keys()))

    kategori_kelime = random.choice(HIZMET_KATEGORILERI[kategori])
    for sehir in random.sample(LOKASYONLAR, min(5, len(LOKASYONLAR))):
        sonuclar.add(f"{sehir} {kategori_kelime}")
        if sehir in ILCELER:
            for ilce in random.sample(ILCELER[sehir], min(3, len(ILCELER[sehir]))):
                sonuclar.add(f"{ilce} {kategori_kelime}")

    es_anlamli = {
        "fiyat": ["ücret", "bedel", "maliyet", "fiyatlandırma"],
        "hizmet": ["servis", "çözüm", "destek", "yardım"],
        "danışmanlık": ["danışman", "uzman", "profesyonel"],
        "ajans": ["firma", "şirket", "kurum"],
    }
    for anahtar, esler in es_anlamli.items():
        if anahtar in kl:
            for es in esler:
                sonuclar.add(kl.replace(anahtar, es))

    while len(sonuclar) < limit:
        kalip = random.choice([
            f"{kategori_kelime} {random.choice(LOKASYONLAR)}",
            f"{random.choice(LOKASYONLAR)} {kategori_kelime}",
            f"{kategori_kelime} {random.choice(list(HIZMET_KATEGORILERI[kategori]))}",
            f"en iyi {kategori_kelime}",
            f"{kategori_kelime} fiyatları",
        ])
        sonuclar.add(kalip)

    return list(sonuclar)[:limit]

def _oneri_kelimeleri_uret(ana_kelime, limit=20):
    kl = _normalize(ana_kelime)
    oneriler = set()
    ekler = ["online", "profesyonel", "kurumsal", "premium", "ekonomik", "hızlı", "güvenilir"]
    for ek in ekler:
        oneriler.add(f"{ek} {ana_kelime}")
        oneriler.add(f"{ana_kelime} {ek}")
    while len(oneriler) < limit:
        e1 = random.choice(ekler)
        e2 = random.choice(ekler)
        oneriler.add(f"{e1} {ana_kelime} {e2}")
    return list(oneriler)[:limit]

def openseo_keyword_research(ana_kelime: str, mod: str = "auto", limit: int = 50, lokasyon: str = "TR"):
    if mod == "auto":
        kaynak = "related"
        ilgili = _ilgili_kelimeler_uret(ana_kelime, limit)
        if len(ilgili) < 5:
            ilgili = _oneri_kelimeleri_uret(ana_kelime, limit)
            kaynak = "suggestions"
            if len(ilgili) < limit:
                ekstra = _ilgili_kelimeler_uret(ana_kelime, limit - len(ilgili))
                ilgili.extend(ekstra)
                kaynak = "ideas"
    elif mod == "related":
        kaynak = "related"
        ilgili = _ilgili_kelimeler_uret(ana_kelime, limit)
    elif mod == "suggestions":
        kaynak = "suggestions"
        ilgili = _oneri_kelimeleri_uret(ana_kelime, limit)
    else:
        kaynak = "ideas"
        ilgili = _ilgili_kelimeler_uret(ana_kelime, limit)
        ekstra = _oneri_kelimeleri_uret(ana_kelime, limit // 2)
        ilgili.extend([k for k in ekstra if k not in ilgili])
        ilgili = ilgili[:limit]

    rows = []
    for k in ilgili:
        rows.append({
            "kelime": k,
            "hacim": _tahmin_hacim(k),
            "rekabet": _tahmin_rekabet(k),
            "cpc": _tahmin_cpc(k),
            "zorluk": _tahmin_zorluk(k),
            "niyet": _tahmin_niyet(k),
        })

    gecerli = [r for r in rows if r["kelime"].lower() != ana_kelime.lower()]
    seed = next((r for r in rows if r["kelime"].lower() == ana_kelime.lower()), rows[0] if rows else None)

    return {
        "status": "aktif",
        "kaynak": kaynak,
        "seed": seed,
        "toplam": len(rows),
        "kelimeler": rows,
        "diagnostics": {
            "aranan": ana_kelime,
            "mod": mod,
            "lokasyon": lokasyon,
            "esik": 5,
            "kaynak_denemeleri": [{"kaynak": kaynak, "satir": len(rows), "seed_dis": len(gecerli)}]
        }
    }
