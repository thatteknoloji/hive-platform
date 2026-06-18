import os, json
from datetime import datetime
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi
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

KOSULLAR = {
    "buyuk_esit": lambda d, e: d >= e,
    "kucuk_esit": lambda d, e: d <= e,
    "buyuk": lambda d, e: d > e,
    "kucuk": lambda d, e: d < e,
    "esit": lambda d, e: d == e,
}

def olustur(hedef, kosul, esik):
    try:
        if not hedef or not kosul or esik is None:
            return {"durum": "hata", "mesaj": "hedef, kosul ve esik parametreleri gerekli"}
        if kosul not in KOSULLAR:
            return {"durum": "hata", "mesaj": f"desteklenmeyen kosul: {kosul}, seçenekler: {list(KOSULLAR.keys())}"}
        alert = {
            "id": f"ALRT-{modul_hash(f'alert_{hedef}_{kosul}_{simdi()}') % 100000:05d}",
            "hedef": hedef,
            "kosul": kosul,
            "esik": esik,
            "aktif": True,
            "tetiklenme_sayisi": 0,
            "son_tetiklenme": None,
            "olusturulma": simdi(),
        }
        alerts = _yukle("alert.json")
        alerts.append(alert)
        _kaydet("alert.json", alerts)
        log_module_run("ALERT", "Alert Oluşturma", {"hedef": hedef, "kosul": kosul, "esik": esik}, {"durum": "başarılı"})
        return {"durum": "başarılı", "alert": alert}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def listele():
    try:
        alerts = _yukle("alert.json")
        if not alerts:
            return {"durum": "başarılı", "toplam": 0, "alertler": []}
        alerts.reverse()
        return {"durum": "başarılı", "toplam": len(alerts), "alertler": alerts[:50]}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def sil(alert_id):
    try:
        if not alert_id:
            return {"durum": "hata", "mesaj": "alert_id gerekli"}
        alerts = _yukle("alert.json")
        yenialerts = [a for a in alerts if a["id"] != alert_id]
        if len(yenialerts) == len(alerts):
            return {"durum": "hata", "mesaj": f"alert bulunamadı: {alert_id}"}
        _kaydet("alert.json", yenialerts)
        return {"durum": "başarılı", "silinen_id": alert_id, "kalan": len(yenialerts)}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def kontrol_et():
    try:
        alerts = _yukle("alert.json")
        tetiklenenler = []
        simdiki_zaman = simdi()
        for alert in alerts:
            if not alert.get("aktif", True):
                continue
            h = modul_hash(f"kontrol_{alert['id']}_{simdiki_zaman[:10]}")
            simulation_value = alert["esik"] + (h % 21 - 10)
            kosul_fonk = KOSULLAR[alert["kosul"]]
            if kosul_fonk(simulation_value, alert["esik"]):
                alert["tetiklenme_sayisi"] = alert.get("tetiklenme_sayisi", 0) + 1
                alert["son_tetiklenme"] = simdiki_zaman
                tetiklenenler.append({
                    "id": alert["id"],
                    "hedef": alert["hedef"],
                    "kosul": alert["kosul"],
                    "esik": alert["esik"],
                    "anlik_deger": simulation_value,
                    "tetiklenme_sayisi": alert["tetiklenme_sayisi"],
                })
        _kaydet("alert.json", alerts)
        return {
            "durum": "başarılı",
            "kontrol_sayisi": len(alerts),
            "tetiklenen_sayisi": len(tetiklenenler),
            "tetiklenenler": tetiklenenler,
        }
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def gecmis():
    try:
        alerts = _yukle("alert.json")
        tetiklenmis = [a for a in alerts if a.get("tetiklenme_sayisi", 0) > 0]
        if not tetiklenmis:
            return {"durum": "başarılı", "toplam": 0, "tetiklenenler": []}
        tetiklenmis.sort(key=lambda a: a.get("son_tetiklenme", ""), reverse=True)
        return {"durum": "başarılı", "toplam": len(tetiklenmis), "tetiklenenler": tetiklenmis[:50]}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}
