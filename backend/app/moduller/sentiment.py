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

POZITIF_KELIMELER = ["harika", "mükemmel", "başarılı", "iyi", "güzel", "harika", "faydalı", "etkili", "kolay", "hızlı", "kaliteli", "gelişmiş", "yenilikçi", "profesyonel", "memnun"]
NEGATIF_KELIMELER = ["kötü", "berbat", "başarısız", "yavaş", "pahalı", "zor", "karmaşık", "kalitesiz", "sorunlu", "hatalı", "beceriksiz", "ilkel", "gereksiz", "yetersiz", "memnuniyetsiz"]

def _skorla(metin):
    metin_lower = metin.lower()
    pozitif_say = sum(1 for k in POZITIF_KELIMELER if k in metin_lower)
    negatif_say = sum(1 for k in NEGATIF_KELIMELER if k in metin_lower)
    toplam = pozitif_say + negatif_say
    if toplam == 0:
        h = modul_hash(metin)
        return "nötr", 50 + (h % 30)
    if pozitif_say > negatif_say:
        return "pozitif", int(50 + (pozitif_say / toplam) * 50)
    elif negatif_say > pozitif_say:
        return "pozitif" if negatif_say == 0 else "negatif", int(50 + (negatif_say / toplam) * 50)
    return "nötr", 65

def analiz_et(metin):
    try:
        if not metin:
            return {"durum": "hata", "mesaj": "metin parametresi gerekli"}
        duygu, guven = _skorla(metin)
        h = modul_hash(metin[:50])
        anahtar_kelimeler = []
        for k in POZITIF_KELIMELER + NEGATIF_KELIMELER:
            if k in metin.lower():
                anahtar_kelimeler.append(k)
        anahtar_kelimeler = list(set(anahtar_kelimeler))[:5]
        kayit = {
            "id": f"SENT-{modul_hash(f'sent_{simdi()}') % 100000:05d}",
            "metin_ozeti": metin[:100],
            "duygu": duygu,
            "guven_puani": guven,
            "anahtar_kelimeler": anahtar_kelimeler,
            "kelime_sayisi": len(metin.split()),
            "timestamp": simdi(),
        }
        gecmis = _yukle("sentiment.json")
        gecmis.append(kayit)
        _kaydet("sentiment.json", gecmis)
        log_module_run("SENTIMENT", "Duygu Analizi", {"metin": metin[:50]}, {"durum": "başarılı", "duygu": duygu})
        return {"durum": "başarılı", "kayit": kayit}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def toplu_analiz(metinler):
    try:
        if not metinler or not isinstance(metinler, list):
            return {"durum": "hata", "mesaj": "metin listesi gerekli"}
        sonuclar = []
        pozitif = negatif = notr = 0
        for metin in metinler:
            sonuc = analiz_et(metin)
            if sonuc.get("durum") == "başarılı":
                kayit = sonuc["kayit"]
                sonuclar.append(kayit)
                if kayit["duygu"] == "pozitif":
                    pozitif += 1
                elif kayit["duygu"] == "negatif":
                    negatif += 1
                else:
                    notr += 1
        return {
            "durum": "başarılı",
            "toplam": len(sonuclar),
            "pozitif": pozitif,
            "negatif": negatif,
            "notr": notr,
            "ortalama_guven": round(sum(s["guven_puani"] for s in sonuclar) / len(sonuclar), 1) if sonuclar else 0,
        }
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def gecmis():
    try:
        veri = _yukle("sentiment.json")
        if not veri:
            return {"durum": "başarılı", "toplam": 0, "kayitlar": []}
        veri.reverse()
        return {"durum": "başarılı", "toplam": len(veri), "kayitlar": veri[:50]}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def istatistik():
    try:
        veri = _yukle("sentiment.json")
        if not veri:
            return {"durum": "başarılı", "pozitif": 0, "negatif": 0, "notr": 0}
        pozitif = sum(1 for v in veri if v["duygu"] == "pozitif")
        negatif = sum(1 for v in veri if v["duygu"] == "negatif")
        notr = sum(1 for v in veri if v["duygu"] == "nötr")
        ort_guven = round(sum(v["guven_puani"] for v in veri) / len(veri), 1)
        en_sik = {}
        for v in veri:
            for k in v.get("anahtar_kelimeler", []):
                en_sik[k] = en_sik.get(k, 0) + 1
        en_sik_kelime = max(en_sik, key=en_sik.get) if en_sik else None
        return {
            "durum": "başarılı",
            "toplam": len(veri),
            "pozitif": pozitif,
            "negatif": negatif,
            "notr": notr,
            "pozitif_oran": round(pozitif / len(veri) * 100, 1),
            "negatif_oran": round(negatif / len(veri) * 100, 1),
            "ortalama_guven": ort_guven,
            "en_sik_anahtar_kelime": {"kelime": en_sik_kelime, "adet": en_sik.get(en_sik_kelime, 0)} if en_sik_kelime else None,
        }
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}
