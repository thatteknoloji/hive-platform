import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi, modul_export_json, modul_export_csv

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "citation.json"

def _yukle():
    path = os.path.join(DATA_DIR, DOSYA)
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []

def _kaydet(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, DOSYA), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

PLATFORMLAR = ["Yelp", "Foursquare", "Google Business Profile", "Yandex", "Bing Places", "Apple Maps",
               "Facebook", "Instagram", "Twitter", "LinkedIn", "Turkcell", "Vodafone", "Turk Telekom",
               "Sahibinden", "Kariyer.net"]

ILCELER = ["Merkez", "Kadıköy", "Beşiktaş", "Çankaya", "Konak", "Muratpaşa", "Osmangazi", "Tepebaşı",
           "Seyhan", "Nilüfer", "Karşıyaka", "Buca", "Keçiören", "Mamak", "Sincan", "Esenler", "Küçükçekmece",
           "Bağcılar", "Ümraniye", "Maltepe"]

ULKELER = ["Türkiye", "ABD", "Almanya", "İngiltere", "Fransa", "Hollanda", "Birleşik Arap Emirlikleri", "Suudi Arabistan"]

def olustur(isletme):
    veri = _yukle()
    cit_id = modul_hash(isletme + simdi())
    hash_key = str(cit_id)
    platform_sayisi = 3 + modul_hash(hash_key + "pc") % 8
    secilen_platformlar = []
    mevcut = list(PLATFORMLAR)
    for i in range(min(platform_sayisi, len(mevcut))):
        secim = modul_sec(hash_key + f"p{i}", mevcut)
        if secim not in secilen_platformlar:
            secilen_platformlar.append(secim)
    citation = {
        "id": cit_id,
        "isletme": isletme,
        "tarih": simdi(),
        "platform_sayisi": len(secilen_platformlar),
        "platformlar": [{
            "platform": p,
            "url": f"https://{p.lower().replace(' ', '')}.com/{isletme.lower().replace(' ', '-')}",
            "dogrulandi": modul_sec(hash_key + f"v{p}", [True, False]),
            "puan": round(3 + modul_yuzde(hash_key + f"s{p}", 0, 2), 1)
        } for p in secilen_platformlar],
        "adres_tutarliligi": round(70 + modul_yuzde(hash_key + "addr", 0, 30), 1),
        "telefon_tutarliligi": round(70 + modul_yuzde(hash_key + "tel", 0, 30), 1),
        "isim_tutarliligi": round(80 + modul_yuzde(hash_key + "name", 0, 20), 1),
        "nap_kapali": modul_sec(hash_key + "nap", [True, True, False])
    }
    veri.append(citation)
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Citation oluşturuldu: {isletme}", "citation": citation}

def listele():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Henüz citation kaydı yok", "citationlar": []}
    return {"status": "ok", "toplam": len(veri), "citationlar": sorted(veri, key=lambda c: c["tarih"], reverse=True)}

def dogrula(isletme):
    veri = _yukle()
    for c in veri:
        if c["isletme"] == isletme:
            platform_durum = []
            for p in c["platformlar"]:
                sim_hash = modul_hash(isletme + p["platform"] + "verify")
                durum = modul_sec(str(sim_hash), ["dogrulandi", "beklemede", "hata", "uyumsuz"])
                platform_durum.append({"platform": p["platform"], "durum": durum})
            genel_puan = round(sum(1 for pd in platform_durum if pd["durum"] == "dogrulandi") / len(platform_durum) * 100, 1) if platform_durum else 0
            return {
                "status": "ok",
                "isletme": isletme,
                "platform_durumlari": platform_durum,
                "genel_dogruluk_puani": genel_puan,
                "tavsiye": "Tüm platformlarda NAP tutarlılığını kontrol edin." if genel_puan < 80 else "Citation profili iyi durumda."
            }
    return {"status": "hata", "mesaj": f"Citation bulunamadı: {isletme}"}

def export(format):
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Dışa aktarılacak veri yok", "veri": ""}
    alanlar = ["id", "isletme", "tarih", "platform_sayisi", "nap_kapali"]
    if format == "csv":
        cikti = modul_export_csv(veri, alanlar)
    elif format == "json":
        cikti = modul_export_json(veri, alanlar)
    else:
        cikti = modul_export_json(veri, alanlar)
    return {"status": "ok", "format": format, "veri": cikti, "satir_sayisi": len(veri)}
