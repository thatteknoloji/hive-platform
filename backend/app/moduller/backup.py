import os, json, shutil
from datetime import datetime
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "backup.json"

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

def _module_dosyasi(modul_id):
    return os.path.join(DATA_DIR, f"{modul_id}.json")

def olustur(module_id):
    kaynak = _module_dosyasi(module_id)
    if not os.path.exists(kaynak):
        return {"status": "hata", "mesaj": f"{module_id} icin kaynak dosya bulunamadi"}
    try:
        with open(kaynak) as f:
            veri = json.load(f)
    except:
        return {"status": "hata", "mesaj": "Kaynak dosya okunamadi"}
    yedekler = _yukle()
    kayit = {
        "id": f"yedek_{modul_hash(str(datetime.now().timestamp()))}",
        "module_id": module_id,
        "tarih": simdi(),
        "boyut": len(json.dumps(veri)),
        "kayit_sayisi": len(veri) if isinstance(veri, list) else 1,
        "dosya_adi": f"{module_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        "veri": veri
    }
    yedekler.append(kayit)
    _kaydet(yedekler)
    return {"status": "ok", "yedek": kayit["id"], "kayit_sayisi": kayit["kayit_sayisi"]}

def listele():
    yedekler = _yukle()
    ozet = [{"id": y["id"], "module_id": y["module_id"], "tarih": y["tarih"], "boyut": y["boyut"]} for y in yedekler]
    return {"status": "ok", "toplam": len(ozet), "yedekler": ozet}

def sil(yedek_id):
    yedekler = _yukle()
    yeni = [y for y in yedekler if y["id"] != yedek_id]
    if len(yeni) == len(yedekler):
        return {"status": "hata", "mesaj": "Yedek bulunamadi"}
    _kaydet(yeni)
    return {"status": "ok", "mesaj": "Yedek silindi"}

def indir(yedek_id):
    yedekler = _yukle()
    for y in yedekler:
        if y["id"] == yedek_id:
            return {"status": "ok", "veri": y.get("veri"), "module_id": y["module_id"], "tarih": y["tarih"]}
    return {"status": "hata", "mesaj": "Yedek bulunamadi"}

def otomatik_zamanla(periyot):
    if periyot not in ["saatlik", "gunluk", "haftalik", "aylik"]:
        return {"status": "hata", "mesaj": "Gecersiz periyot. Secenekler: saatlik, gunluk, haftalik, aylik"}
    kayit = {
        "id": f"otoyedek_{modul_hash(str(datetime.now().timestamp()))}",
        "periyot": periyot,
        "baslangic": simdi(),
        "durum": "aktif"
    }
    yedekler = _yukle()
    yedekler.insert(0, {"tip": "otomatik_zamanlama", "kayit": kayit})
    _kaydet(yedekler)
    return {"status": "ok", "mesaj": f"Otomatik yedekleme {periyot} olarak ayarlandi", "kayit": kayit}
