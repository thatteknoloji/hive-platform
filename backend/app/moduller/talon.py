import csv
import io
import logging
import random
import uuid

from .talon_db import (
    search_kaydet, keyword_toplu_kaydet, search_listele, search_getir,
    search_sil, favori_ekle as db_favori_ekle,
    favori_kaldir as db_favori_kaldir,
    favori_listele as db_favori_listele,
    api_durum_listele,
)
from .talon_utils import LocationService, DataForSEOService, SerpAPIService, OllamaService

logger = logging.getLogger("hive.talon")

REKABET_KELIMELER = {
    "dusuk": ["vip", "lüks", "model", "hostes", "partner", "yabancı", "pahalı"],
    "orta": ["class", "kaliteli", "özel", "lisanslı", "genç", "seksi", "ateşli"],
}
HACIM_KELIMELER = {
    "1000+": ["anal", "oral", "ekonomik", "gece", "masaj", "otel", "plaj"],
    "500-1000": ["üniversiteli", "bayan arkadaş", "genç", "24 saat", "class"],
    "100-500": ["vip", "lüks", "model", "seksi", "olgun", "çift", "trans"],
    "0-100": ["hostes", "partner", "yabancı", "lisanslı", "ateşli", "pahalı"],
}


def _turkce_duzelt(kelime):
    duzeltmeler = {
        "kusadasi": "kuşadası", "kusadası": "kuşadası",
        "istanbul": "istanbul", "ankara": "ankara",
        "izmir": "izmir", "antalya": "antalya",
    }
    for yanlis, dogru in duzeltmeler.items():
        if yanlis in kelime.lower():
            kelime = kelime.lower().replace(yanlis, dogru)
            break
    return kelime


def _baslik_format(kelime: str) -> str:
    return kelime.strip().title()


def _rekabet_seviyesi(kelime):
    kl = kelime.lower()
    for seviye, anahtarlar in REKABET_KELIMELER.items():
        if any(a in kl for a in anahtarlar):
            return "düşük" if seviye == "dusuk" else seviye
    return "yüksek"


def _arama_hacmi(kelime):
    kl = kelime.lower()
    for hacim, anahtarlar in HACIM_KELIMELER.items():
        if any(a in kl for a in anahtarlar):
            return hacim
    return "100-500"


def _rakip_var_mi(kelime):
    import hashlib
    h = int(hashlib.md5(kelime.encode("utf-8")).hexdigest()[:8], 16)
    return h % 3 != 0


def _hacim_bucket(hacim: int) -> str:
    if hacim > 1000:
        return "1000+"
    if hacim > 500:
        return "500-1000"
    if hacim > 100:
        return "100-500"
    return "0-100"


def _rekabet_bucket(rekabet: float) -> str:
    if rekabet < 0.3:
        return "düşük"
    if rekabet < 0.6:
        return "orta"
    return "yüksek"


def _api_analiz_cache(kelime: str, cache: dict) -> dict | None:
    if kelime not in cache:
        cache[kelime] = DataForSEOService.keyword_analiz(kelime)
    return cache[kelime]


def anahtar_kelime_uret(
    ana_kelime: str = "kuşadası escort",
    adet: int = 10,
    sehir: str = "kuşadası",
    negatif_filtre: str = None,
    sektor: str = "escort",
):
    if adet > 100:
        adet = 100
    if adet < 1:
        adet = 1

    ana_kelime = _turkce_duzelt(ana_kelime)
    gercek_sehir, ilceler, caddeler, sokaklar = LocationService.lokasyon_ara(sehir)
    sehir = gercek_sehir or sehir

    from .talon_extensions import sektor_sablonu
    sablon = sektor_sablonu(sektor) or sektor_sablonu("escort") or {}
    hizmetler = sablon.get("hizmetler") or [
        "anal escort", "oral escort", "vip escort", "otel escort",
        "plaj escort", "gece escort", "24 saat escort", "masaj escort",
        "bayan arkadaş", "partner escort", "çift escort", "trans escort",
    ]
    sektor_kaliplar = sablon.get("kaliplar")

    if not ilceler:
        ilceler = ["Kadınlar Denizi", "Yılancı Burnu", "Güvercinada", "Davutlar", "Merkez"]
    if not caddeler:
        caddeler = ["Atatürk Caddesi", "Liman Caddesi", "İstiklal Caddesi", "Gazi Bulvarı"]
    if not sokaklar:
        sokaklar = ["2. Sokak", "5. Sokak", "Çınar Sokak", "Deniz Sokak", "Zeytin Sokak"]

    sonuclar = set()
    kaliplar = sektor_kaliplar or [
        "mahalle_hizmet", "cadde_sokak_hizmet", "mahalle_cadde_hizmet",
        "hizmet_mahalle_ana", "cadde_hizmet", "sokak_hizmet",
        "mahalle_cadde_sokak_hizmet", "ana_mahalle_hizmet",
    ]

    negatif_liste = []
    if negatif_filtre:
        negatif_liste = [k.strip().lower() for k in negatif_filtre.split(",") if k.strip()]

    api_kullanildi = SerpAPIService.is_configured() or DataForSEOService.is_configured()
    max_iter = adet * 100
    iter_count = 0

    while len(sonuclar) < adet and iter_count < max_iter:
        iter_count += 1
        hizmet = random.choice(hizmetler)
        mahalle = random.choice(ilceler)
        cadde = random.choice(caddeler) if caddeler else ""
        sokak = random.choice(sokaklar) if sokaklar else ""
        tip = random.choice(kaliplar)

        if tip == "mahalle_hizmet":
            kelime = f"{mahalle} {hizmet}"
        elif tip == "cadde_sokak_hizmet":
            kelime = f"{cadde} {sokak} {hizmet}"
        elif tip == "mahalle_cadde_hizmet":
            kelime = f"{mahalle} {cadde} {hizmet}"
        elif tip == "hizmet_mahalle_ana":
            kelime = f"{hizmet} {mahalle}"
        elif tip == "cadde_hizmet":
            kelime = f"{cadde} {hizmet}"
        elif tip == "sokak_hizmet":
            kelime = f"{sokak} {hizmet}"
        elif tip == "mahalle_cadde_sokak_hizmet":
            kelime = f"{mahalle} {cadde} {sokak} {hizmet}"
        else:
            kelime = f"{mahalle} {hizmet}"

        if random.choice([True, False]) and ana_kelime not in kelime:
            if random.choice([True, False]):
                kelime = f"{ana_kelime} {kelime}"
            else:
                kelime = f"{kelime} {ana_kelime}"

        kelime = _baslik_format(kelime)
        kl = kelime.lower()
        if any(nf in kl for nf in negatif_liste):
            continue
        sonuclar.add(kelime)

    if len(sonuclar) < adet:
        logger.warning("Talon: %d/%d kelime üretildi (filtre/şablon sınırı)", len(sonuclar), adet)

    sonuc_liste = list(sonuclar)[:adet]

    if negatif_filtre and len(negatif_liste) == 1:
        ai_temiz = OllamaService.anlam_filtrele(sonuc_liste, negatif_liste[0])
        if ai_temiz:
            sonuc_liste = [k for k in sonuc_liste if k in ai_temiz or k.lower() in [t.lower() for t in ai_temiz]]

    api_cache: dict = {}
    detayli = []
    for k in sonuc_liste:
        analiz = _api_analiz_cache(k, api_cache)
        if analiz:
            rekabet = _rekabet_bucket(float(analiz.get("rekabet", 0.5)))
            hacim = _hacim_bucket(int(analiz.get("hacim", 0)))
            cpc = str(round(float(analiz.get("cpc", 0)), 2))
        else:
            rekabet = _rekabet_seviyesi(k)
            hacim = _arama_hacmi(k)
            cpc = "0"

        rakip = SerpAPIService.rakip_kontrol(k)
        if rakip is None:
            rakip = _rakip_var_mi(k)
        else:
            rakip = rakip.get("rakip_sayisi", 0) > 0

        detayli.append({
            "kelime": k,
            "rekabet": rekabet,
            "arama_hacmi": hacim,
            "rakip_var": rakip,
            "cpc": cpc,
        })

    search_id = str(uuid.uuid4())[:8]
    try:
        search_kaydet(search_id, ana_kelime, sehir, adet, negatif_filtre, len(detayli), api_kullanildi)
        kw_list = [{"search_id": search_id, **item} for item in detayli]
        keyword_toplu_kaydet(kw_list)
    except Exception as e:
        logger.error("Talon DB kayıt hatası: %s", e)

    return detayli, search_id


def hiper_lokal_kelime_uret(
    ana_kelime: str = "kuşadası escort",
    adet: int = 50,
    sehir: str = "kuşadası",
    negatif_filtre: str = None,
    sektor: str = "escort",
):
    """Hiper-lokal uzun kuyruklu anahtar kelime üretimi."""
    return anahtar_kelime_uret(
        ana_kelime=ana_kelime, adet=adet, sehir=sehir,
        negatif_filtre=negatif_filtre, sektor=sektor,
    )


def kelime_grupla(kelimeler):
    ai_gruplar = OllamaService.kelime_grupla(kelimeler)
    if ai_gruplar:
        for g in ai_gruplar:
            ai_gruplar[g] = ai_gruplar[g][:50]
        return ai_gruplar

    gruplar = {
        "lokasyon_bazli": [], "hizmet_bazli": [],
        "fiyat_bazli": [], "zaman_bazli": [], "diger": [],
    }
    fiyat_k = ["vip", "lüks", "ekonomik", "ucuz", "pahalı", "class", "kaliteli"]
    zaman_k = ["gece", "24 saat", "akşam", "sabah"]
    hizmet_liste = [h.lower() for h in [
        "anal escort", "oral escort", "vip escort", "otel escort",
        "plaj escort", "gece escort", "24 saat escort", "masaj escort",
        "bayan arkadaş", "partner escort", "çift escort", "trans escort",
        "lisanslı escort", "yabancı escort",
    ]]

    _, ilceler, caddeler, sokaklar = LocationService.lokasyon_ara("")
    lokasyon_k = [m.lower() for m in ilceler] + [c.lower() for c in caddeler] + [s.lower() for s in sokaklar]

    for item in kelimeler:
        k = item["kelime"].lower()
        if any(fk in k for fk in fiyat_k):
            gruplar["fiyat_bazli"].append(item)
        elif any(zk in k for zk in zaman_k):
            gruplar["zaman_bazli"].append(item)
        elif any(lk in k for lk in lokasyon_k):
            gruplar["lokasyon_bazli"].append(item)
        elif any(ht in k for ht in hizmet_liste):
            gruplar["hizmet_bazli"].append(item)
        else:
            gruplar["diger"].append(item)

    for g in gruplar:
        gruplar[g] = gruplar[g][:50]
    return gruplar


def export_kelimeler(kelimeler, export_format="csv"):
    if export_format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Kelime", "Rekabet", "Arama Hacmi", "Rakip Var", "CPC"])
        for item in kelimeler:
            writer.writerow([
                item.get("kelime", ""),
                item.get("rekabet", ""),
                item.get("arama_hacmi", ""),
                "Evet" if item.get("rakip_var") else "Hayır",
                item.get("cpc", "0"),
            ])
        content = buf.getvalue()
    elif export_format == "json":
        import json
        content = json.dumps(kelimeler, indent=2, ensure_ascii=False)
    else:
        content = "\n".join(item["kelime"] for item in kelimeler)

    return {"format": export_format, "content": content}


def gecmis_listele():
    return search_listele()


def gecmis_getir(search_id):
    return search_getir(search_id)


def gecmis_sil(search_id):
    search_sil(search_id)


def favori_ekle(kelime, rekabet, arama_hacmi, rakip_var):
    return db_favori_ekle(kelime, rekabet, arama_hacmi, rakip_var)


def favori_kaldir(kelime):
    return db_favori_kaldir(kelime)


def favori_listele():
    return db_favori_listele()


def api_durum():
    return api_durum_listele()


def talon_settings_kaydet(settings: dict) -> dict:
    from .talon_db import api_key_kaydet
    allowed = (
        "tavily", "exa", "searxng_url", "openrouter", "ollama_host",
        "dataforseo_login", "dataforseo_password", "serpapi",
    )
    saved = []
    for key, value in settings.items():
        if key in allowed and value:
            api_key_kaydet(key, str(value).strip())
            saved.append(key)
    return {"kaydedilen": saved, "api": api_durum_listele()}
