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

KANALLAR = ["email", "webhook", "sms", "slack", "telegram"]
VARSAYILAN_AYARLAR = {
    "email_aktif": True,
    "webhook_aktif": False,
    "sms_aktif": False,
    "slack_aktif": False,
    "telegram_aktif": False,
    "sessiz_saat_baslangic": None,
    "sessiz_saat_bitis": None,
    "maksimum_bildirim_gunluk": 100,
}

def _ayarlar_yukle():
    path = os.path.join(DATA_DIR, "notification_settings.json")
    if not os.path.exists(path):
        return dict(VARSAYILAN_AYARLAR)
    try:
        with open(path) as f: return json.load(f)
    except:
        return dict(VARSAYILAN_AYARLAR)

def _ayarlar_kaydet(ayarlar):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "notification_settings.json"), "w") as f:
        json.dump(ayarlar, f, indent=2, ensure_ascii=False)

def gonder(kanal, baslik, mesaj):
    try:
        if kanal not in KANALLAR:
            return {"durum": "hata", "mesaj": f"desteklenmeyen kanal: {kanal}, seçenekler: {KANALLAR}"}
        if not baslik or not mesaj:
            return {"durum": "hata", "mesaj": "baslik ve mesaj parametreleri gerekli"}
        h = modul_hash(f"notif_{kanal}_{baslik}_{simdi()}")
        basarili = h % 10 > 1
        bildirim = {
            "id": f"NTF-{modul_hash(f'notif_{simdi()}') % 100000:05d}",
            "kanal": kanal,
            "baslik": baslik,
            "mesaj": mesaj[:200],
            "durum": "gönderildi" if basarili else "başarısız",
            "okundu": False,
            "timestamp": simdi(),
        }
        bildirimler = _yukle("notification.json")
        bildirimler.append(bildirim)
        _kaydet("notification.json", bildirimler)
        log_module_run("NOTIFICATION", "Bildirim Gönderme", {"kanal": kanal, "baslik": baslik}, {"durum": bildirim["durum"]})
        return {"durum": "başarılı" if basarili else "hata", "bildirim": bildirim}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def listele():
    try:
        bildirimler = _yukle("notification.json")
        if not bildirimler:
            return {"durum": "başarılı", "toplam": 0, "bildirimler": []}
        bildirimler.reverse()
        return {"durum": "başarılı", "toplam": len(bildirimler), "bildirimler": bildirimler[:50]}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def oku(bildirim_id):
    try:
        if not bildirim_id:
            return {"durum": "hata", "mesaj": "bildirim_id gerekli"}
        bildirimler = _yukle("notification.json")
        for b in bildirimler:
            if b["id"] == bildirim_id:
                b["okundu"] = True
                b["okunma_tarihi"] = simdi()
                _kaydet("notification.json", bildirimler)
                return {"durum": "başarılı", "bildirim": b}
        return {"durum": "hata", "mesaj": f"bildirim bulunamadı: {bildirim_id}"}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def temizle():
    try:
        bildirimler = _yukle("notification.json")
        okunanlar = [b for b in bildirimler if not b.get("okundu", False)]
        silinen = len(bildirimler) - len(okunanlar)
        _kaydet("notification.json", okunanlar)
        return {"durum": "başarılı", "silinen": silinen, "kalan": len(okunanlar)}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def ayarlar(ayar_dict=None):
    try:
        mevcut = _ayarlar_yukle()
        if ayar_dict:
            for anahtar, deger in ayar_dict.items():
                if anahtar in mevcut:
                    mevcut[anahtar] = deger
            _ayarlar_kaydet(mevcut)
            return {"durum": "başarılı", "ayarlar": mevcut, "guncellendi": list(ayar_dict.keys())}
        return {"durum": "başarılı", "ayarlar": mevcut}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}
