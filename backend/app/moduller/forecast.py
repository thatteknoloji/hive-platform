import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi, modul_export_json, modul_export_csv, modul_export_txt
from app.database import log_module_run

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")

def _yukle(dosya):
    path = os.path.join(DATA_DIR, dosya)
    if not os.path.exists(path): return []
    try:
        with open(path) as f: return json.load(f)
    except: return []

def _kaydet(dosya, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, dosya), "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)

VERI_TIPLERI = {
    "organik_trafik": {"birim": "ziyaretçi", "min": 1000, "max": 50000, "trend": 0.05},
    "siralama": {"birim": "sıra", "min": 1, "max": 100, "trend": -0.03},
    "donusum": {"birim": "%", "min": 0.5, "max": 15, "trend": 0.02},
    "backlink": {"birim": "adet", "min": 10, "max": 2000, "trend": 0.08},
    "sayfa_goruntuleme": {"birim": "gösterim", "min": 5000, "max": 200000, "trend": 0.04},
}

def _tahmin_uret(veri_tipi, ay_sayisi=12):
    config = VERI_TIPLERI.get(veri_tipi)
    if not config:
        return []
    h = modul_hash(f"forecast_{veri_tipi}_{simdi()[:7]}")
    noktalar = []
    deger = config["min"] + (h % (config["max"] - config["min"]))
    for i in range(ay_sayisi):
        mevsim = 1 + 0.2 * __import__("math").sin(i * 3.14159 / 6)
        dalgalanma = (modul_hash(f"{veri_tipi}_{i}_{simdi()[:4]}") % 21 - 10) / 100
        buyume = config["trend"] * i
        deger = deger * (1 + buyume + dalgalanma) * mevsim
        deger = max(config["min"], min(config["max"], int(deger)))
        ay_tarih = (datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m")
        noktalar.append({"tarih": ay_tarih, "tahmin": deger, "birim": config["birim"]})
    return noktalar

def tahmin_et(veri_tipi):
    try:
        if not veri_tipi:
            return {"durum": "hata", "mesaj": "veri_tipi gerekli"}
        if veri_tipi not in VERI_TIPLERI:
            return {"durum": "hata", "mesaj": f"desteklenmeyen veri tipi: {veri_tipi}, seçenekler: {list(VERI_TIPLERI.keys())}"}
        noktalar = _tahmin_uret(veri_tipi)
        kayit = {
            "id": f"FRCST-{modul_hash(f'forecast_{veri_tipi}_{simdi()}') % 100000:05d}",
            "veri_tipi": veri_tipi,
            "birim": VERI_TIPLERI[veri_tipi]["birim"],
            "noktalar": noktalar,
            "ilk_deger": noktalar[0]["tahmin"],
            "son_deger": noktalar[-1]["tahmin"],
            "degisim_yuzde": round((noktalar[-1]["tahmin"] - noktalar[0]["tahmin"]) / noktalar[0]["tahmin"] * 100, 1),
            "timestamp": simdi(),
        }
        tahminler = _yukle("forecast.json")
        tahminler.append(kayit)
        _kaydet("forecast.json", tahminler)
        log_module_run("FORECAST", "Tahmin", {"veri_tipi": veri_tipi}, {"durum": "başarılı"})
        return {"durum": "başarılı", "kayit": kayit}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def listele():
    try:
        tahminler = _yukle("forecast.json")
        if not tahminler:
            return {"durum": "başarılı", "toplam": 0, "tahminler": []}
        tahminler.reverse()
        return {"durum": "başarılı", "toplam": len(tahminler), "tahminler": tahminler[:50]}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def karsilastir(tahmin_id):
    try:
        if not tahmin_id:
            return {"durum": "hata", "mesaj": "tahmin_id gerekli"}
        tahminler = _yukle("forecast.json")
        hedef = None
        for t in tahminler:
            if t["id"] == tahmin_id:
                hedef = t
                break
        if not hedef:
            return {"durum": "hata", "mesaj": f"tahmin bulunamadı: {tahmin_id}"}
        ayni_tip = [t for t in tahminler if t["veri_tipi"] == hedef["veri_tipi"] and t["id"] != tahmin_id]
        karsilastirmalar = []
        for t in ayni_tip[-5:]:
            karsilastirmalar.append({
                "id": t["id"],
                "tarih": t["timestamp"][:10],
                "ilk_deger": t["ilk_deger"],
                "son_deger": t["son_deger"],
                "degisim": t["degisim_yuzde"],
            })
        return {
            "durum": "başarılı",
            "hedef": {"id": hedef["id"], "veri_tipi": hedef["veri_tipi"], "degisim": hedef["degisim_yuzde"]},
            "karsilastirmalar": karsilastirmalar,
        }
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def export(format):
    try:
        if format not in ("json", "csv", "txt"):
            return {"durum": "hata", "mesaj": "desteklenen formatlar: json, csv, txt"}
        tahminler = _yukle("forecast.json")
        if not tahminler:
            return {"durum": "hata", "mesaj": "dışa aktarılacak veri yok"}
        alanlar = ["id", "veri_tipi", "ilk_deger", "son_deger", "degisim_yuzde", "timestamp"]
        if format == "json":
            icerik = modul_export_json(tahminler, alanlar)
        elif format == "csv":
            icerik = modul_export_csv(tahminler, alanlar)
        else:
            icerik = modul_export_txt(tahminler, alanlar)
        return {"durum": "başarılı", "format": format, "icerik": icerik}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}
