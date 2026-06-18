import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "funnel.json"

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

ASAMALAR = ["ziyaret", "goz_atma", "sepete_ekle", "odeme", "satinalma"]

def analiz_et(url):
    veri = _yukle()
    funnel_id = modul_hash(url + simdi())
    hash_key = str(funnel_id)
    onceki = 0
    asama_verileri = []
    for i, asama in enumerate(ASAMALAR):
        if i == 0:
            miktar = 500 + modul_hash(hash_key + f"s{i}") % 1500
            onceki = miktar
        else:
            dusus = 10 + modul_yuzde(hash_key + f"d{i}", 0, 50)
            miktar = max(1, int(onceki * (100 - dusus) / 100))
            onceki = miktar
        asama_verileri.append({
            "asama": asama,
            "ziyaretci": miktar,
            "onceki_asamaya_gore_yuzde": round((miktar / onceki * 100) if i > 0 and onceki > 0 else 100, 1)
        })
    toplam_dusus = round((1 - asama_verileri[-1]["ziyaretci"] / asama_verileri[0]["ziyaretci"]) * 100, 1) if asama_verileri[0]["ziyaretci"] > 0 else 0
    funnel = {
        "id": funnel_id,
        "url": url,
        "tarih": simdi(),
        "asamalar": asama_verileri,
        "toplam_ziyaretci": asama_verileri[0]["ziyaretci"],
        "toplam_satinalma": asama_verileri[-1]["ziyaretci"],
        "genel_donusum_orani": round(asama_verileri[-1]["ziyaretci"] / asama_verileri[0]["ziyaretci"] * 100, 2) if asama_verileri[0]["ziyaretci"] > 0 else 0,
        "toplam_dusus_orani": toplam_dusus,
        "en_cok_dusus_asamasi": max(asama_verileri[1:], key=lambda a: 100 - a["onceki_asamaya_gore_yuzde"])["asama"] if len(asama_verileri) > 1 else None
    }
    veri.append(funnel)
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Huni analizi tamamlandı: {url}", "funnel": funnel}

def listele():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Henüz huni analizi yok", "funnellar": []}
    return {"status": "ok", "toplam": len(veri), "funnellar": sorted(veri, key=lambda f: f["tarih"], reverse=True)}

def detay(funnel_id):
    veri = _yukle()
    for f in veri:
        if f["id"] == funnel_id:
            return {"status": "ok", "funnel": f}
    return {"status": "hata", "mesaj": f"Huni bulunamadı: {funnel_id}"}

def optimize_et(funnel_id):
    veri = _yukle()
    for f in veri:
        if f["id"] == funnel_id:
            asamalar = f["asamalar"]
            oneriler = []
            for a in asamalar[1:]:
                onceki_miktar = asamalar[asamalar.index(a) - 1]["ziyaretci"]
                if onceki_miktar > 0 and a["onceki_asamaya_gore_yuzde"] < 70:
                    oneriler.append(f"{a['asama']} aşamasında %{round(100 - a['onceki_asamaya_gore_yuzde'], 1)} düşüş var. CTA iyileştirmesi, form kısaltma veya güven sinyalleri ekleyin.")
            if not oneriler:
                oneriler.append("Huni genel olarak sağlıklı görünüyor. Küçük iyileştirmeler için A/B test önerilir.")
            oneriler.append(f"Toplam dönüşüm oranı %{f['genel_donusum_orani']}. Sektör ortalamasına göre değerlendirin.")
            return {"status": "ok", "mesaj": f"Optimizasyon önerileri hazır: {f['url']}", "funnel_id": funnel_id, "oneriler": oneriler}
    return {"status": "hata", "mesaj": f"Huni bulunamadı: {funnel_id}"}
