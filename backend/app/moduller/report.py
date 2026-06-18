import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi, modul_export_json, modul_export_csv, modul_export_txt
from app.database import log_module_run
from . import trend, sentiment, forecast, alert

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

MODUL_ADLARI = ["trend", "sentiment", "forecast", "alert", "notification"]

def _veri_topla(modul_id):
    if modul_id == "trend":
        return trend.listele()
    elif modul_id == "sentiment":
        return sentiment.istatistik()
    elif modul_id == "forecast":
        return forecast.listele()
    elif modul_id == "alert":
        return alert.listele()
    return None

def olustur(modul_id, format):
    try:
        if modul_id not in MODUL_ADLARI:
            return {"durum": "hata", "mesaj": f"desteklenmeyen modul: {modul_id}, seçenekler: {MODUL_ADLARI}"}
        if format not in ("json", "csv", "txt"):
            return {"durum": "hata", "mesaj": "desteklenen formatlar: json, csv, txt"}
        veri = _veri_topla(modul_id)
        if not veri or veri.get("durum") == "hata":
            return {"durum": "hata", "mesaj": f"'{modul_id}' modülünden veri alınamadı"}
        icerik = ""
        if format == "json":
            icerik = json.dumps(veri, indent=2, ensure_ascii=False)
        elif format == "csv":
            alanlar = list(veri.keys()) if isinstance(veri, dict) else []
            icerik = modul_export_csv([veri], alanlar) if alanlar else ""
        else:
            alanlar = list(veri.keys())
            icerik = modul_export_txt([veri], alanlar)
        rapor = {
            "id": f"RPRT-{modul_hash(f'report_{modul_id}_{format}_{simdi()}') % 100000:05d}",
            "modul_id": modul_id,
            "format": format,
            "icerik": icerik[:500],
            "icerik_uzunlugu": len(icerik),
            "olusturulma": simdi(),
        }
        raporlar = _yukle("report.json")
        raporlar.append(rapor)
        _kaydet("report.json", raporlar)
        log_module_run("REPORT", "Rapor Oluşturma", {"modul_id": modul_id, "format": format}, {"durum": "başarılı"})
        return {"durum": "başarılı", "rapor": rapor}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def listele():
    try:
        raporlar = _yukle("report.json")
        if not raporlar:
            return {"durum": "başarılı", "toplam": 0, "raporlar": []}
        raporlar.reverse()
        ozet = [{"id": r["id"], "modul_id": r["modul_id"], "format": r["format"], "olusturulma": r["olusturulma"]} for r in raporlar[:50]]
        return {"durum": "başarılı", "toplam": len(raporlar), "raporlar": ozet}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def sil(rapor_id):
    try:
        if not rapor_id:
            return {"durum": "hata", "mesaj": "rapor_id gerekli"}
        raporlar = _yukle("report.json")
        yeniler = [r for r in raporlar if r["id"] != rapor_id]
        if len(yeniler) == len(raporlar):
            return {"durum": "hata", "mesaj": f"rapor bulunamadı: {rapor_id}"}
        _kaydet("report.json", yeniler)
        return {"durum": "başarılı", "silinen_id": rapor_id, "kalan": len(yeniler)}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def indir(rapor_id):
    try:
        if not rapor_id:
            return {"durum": "hata", "mesaj": "rapor_id gerekli"}
        raporlar = _yukle("report.json")
        for r in raporlar:
            if r["id"] == rapor_id:
                return {
                    "durum": "başarılı",
                    "rapor": r,
                    "dosya_adi": f"{r['modul_id']}_{r['id']}.{r['format']}",
                    "icerik": r.get("icerik", ""),
                }
        return {"durum": "hata", "mesaj": f"rapor bulunamadı: {rapor_id}"}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def zamanla(rapor_id, periyot):
    try:
        if not rapor_id or not periyot:
            return {"durum": "hata", "mesaj": "rapor_id ve periyot gerekli"}
        gecerli_periyotlar = {"gunluk": 1, "haftalik": 7, "aylik": 30}
        if periyot not in gecerli_periyotlar:
            return {"durum": "hata", "mesaj": f"desteklenmeyen periyot: {periyot}, seçenekler: {list(gecerli_periyotlar.keys())}"}
        raporlar = _yukle("report.json")
        hedef = None
        for r in raporlar:
            if r["id"] == rapor_id:
                hedef = r
                break
        if not hedef:
            return {"durum": "hata", "mesaj": f"rapor bulunamadı: {rapor_id}"}
        schedule = {
            "rapor_id": rapor_id,
            "modul_id": hedef["modul_id"],
            "periyot": periyot,
            "gun_aralik": gecerli_periyotlar[periyot],
            "baslangic": simdi(),
            "sonraki_olusum": (datetime.now() + timedelta(days=gecerli_periyotlar[periyot])).isoformat(),
            "aktif": True,
        }
        path = os.path.join(DATA_DIR, "report_schedule.json")
        planlar = []
        if os.path.exists(path):
            try:
                with open(path) as f: planlar = json.load(f)
            except:
                planlar = []
        planlar.append(schedule)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(path, "w") as f: json.dump(planlar, f, indent=2, ensure_ascii=False)
        return {"durum": "başarılı", "zamanlama": schedule}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}
