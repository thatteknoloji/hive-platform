import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "heatmap.json"

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

OGE_SECENEKLER = ["header", "nav-logo", "hero-title", "hero-cta", "feature-card-1", "feature-card-2", "feature-card-3",
                  "testimonial-1", "testimonial-2", "pricing-table", "pricing-cta", "footer-link", "footer-social",
                  "sidebar-widget", "search-box", "menu-item-1", "menu-item-2", "menu-item-3", "blog-card",
                  "faq-item", "contact-form", "submit-btn", "video-player", "image-gallery", "scroll-top"]

def olustur(url):
    veri = _yukle()
    heatmap_id = modul_hash(url + simdi())
    hash_key = str(heatmap_id)
    toplam_tiklama = 100 + modul_hash(hash_key + "tc") % 4900
    kalan = toplam_tiklama
    element_tiklari = []
    secilen_ogeler = modul_sec(hash_key + "elem", OGE_SECENEKLER, 1)
    for i, oge in enumerate(OGE_SECENEKLER[:10]):
        if kalan <= 0:
            break
        pay = int(kalan * (5 + modul_yuzde(hash_key + f"e{i}", 0, 25)) / 100) if i < 9 else kalan
        if pay <= 0:
            pay = 1
        kalan -= pay
        element_tiklari.append({"element": oge, "tiklamalar": pay, "yuzde": round(pay / toplam_tiklama * 100, 1)})
    element_tiklari.sort(key=lambda e: e["tiklamalar"], reverse=True)
    heatmap = {
        "id": heatmap_id,
        "url": url,
        "tarih": simdi(),
        "toplam_tiklama": toplam_tiklama,
        "ekran_cozunurlugu": modul_sec(hash_key + "res", ["1920x1080", "1366x768", "1440x900", "1536x864", "2560x1440"]),
        "ortalama_kayma_derinligi_yuzde": round(30 + modul_yuzde(hash_key + "scroll", 0, 60), 1),
        "element_tiklamalari": element_tiklari,
        "en_sicak_bolge": element_tiklari[0]["element"] if element_tiklari else "bilinmiyor",
        "soguk_bolgeler": [e["element"] for e in element_tiklari[-3:]] if len(element_tiklari) >= 3 else []
    }
    veri.append(heatmap)
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Isı haritası oluşturuldu: {url}", "heatmap": heatmap}

def listele():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Henüz ısı haritası yok", "heatmapler": []}
    return {"status": "ok", "toplam": len(veri), "heatmapler": sorted(veri, key=lambda h: h["tarih"], reverse=True)}

def detay(heatmap_id):
    veri = _yukle()
    for h in veri:
        if h["id"] == heatmap_id:
            return {"status": "ok", "heatmap": h}
    return {"status": "hata", "mesaj": f"Isı haritası bulunamadı: {heatmap_id}"}

def sil(heatmap_id):
    veri = _yukle()
    once = len(veri)
    veri = [h for h in veri if h["id"] != heatmap_id]
    if len(veri) == once:
        return {"status": "hata", "mesaj": f"Isı haritası bulunamadı: {heatmap_id}"}
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Isı haritası silindi: {heatmap_id}"}
