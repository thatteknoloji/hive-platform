import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi, TURKCE_SEHIRLER
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

YONLER = ["Yükselen", "Düşen", "Sabit"]
KATEGORILER = {
    "teknoloji": ["yapay zeka", "blockchain", "bulut bilişim", "siber güvenlik", "nesnelerin interneti"],
    "pazarlama": ["seo", "sosyal medya", "e-posta pazarlama", "içerik pazarlama", "influencer"],
    "ekonomi": ["enflasyon", "faiz", "borsa", "kripto para", "döviz"],
    "sağlık": ["tele-tıp", "biyoteknoloji", "genetik", "ilaç", "sağlık turizmi"],
    "eğitim": ["online eğitim", "uzaktan öğretim", "sertifika", "kodlama", "dijital beceri"],
}

def analiz_et(konu):
    try:
        if not konu:
            return {"durum": "hata", "mesaj": "konu parametresi gerekli"}
        h = modul_hash(f"trend_analiz_{konu}_{simdi()[:10]}")
        trendler = _yukle("trend.json")
        mevcut = [t for t in trendler if t["konu"] == konu]
        onceki_puan = mevcut[-1]["populerlik"] if mevcut else 50
        momentum = (h % 21) - 10
        yeni_puan = max(0, min(100, onceki_puan + momentum))
        yon = "Yükselen" if momentum > 3 else ("Düşen" if momentum < -3 else "Sabit")
        kategori = None
        for kat, kelimeler in KATEGORILER.items():
            if any(k in konu.lower() for k in kelimeler):
                kategori = kat
                break
        kayit = {
            "id": f"TRND-{modul_hash(f'trend_{konu}_{simdi()}') % 100000:05d}",
            "konu": konu,
            "populerlik": yeni_puan,
            "yon": yon,
            "momentum": momentum,
            "kategori": kategori or "genel",
            "sehir": modul_sec(f"sehir_{konu}", TURKCE_SEHIRLER),
            "timestamp": simdi(),
        }
        trendler.append(kayit)
        _kaydet("trend.json", trendler)
        log_module_run("TREND", "Trend Analizi", {"konu": konu}, {"durum": "başarılı", "yon": yon})
        return {"durum": "başarılı", "kayit": kayit}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def listele():
    try:
        trendler = _yukle("trend.json")
        if not trendler:
            return {"durum": "başarılı", "toplam": 0, "trendler": []}
        trendler.reverse()
        return {"durum": "başarılı", "toplam": len(trendler), "trendler": trendler[:50]}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def populer():
    try:
        trendler = _yukle("trend.json")
        if not trendler:
            return {"durum": "başarılı", "populer": []}
        son = {}
        for t in trendler:
            son[t["konu"]] = t
        sirali = sorted(son.values(), key=lambda x: x["populerlik"], reverse=True)
        return {"durum": "başarılı", "populer": sirali[:20]}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def grafik(konu):
    try:
        if not konu:
            return {"durum": "hata", "mesaj": "konu parametresi gerekli"}
        trendler = _yukle("trend.json")
        filtrelenmis = [t for t in trendler if t["konu"] == konu]
        if not filtrelenmis:
            return {"durum": "hata", "mesaj": f"'{konu}' için veri bulunamadı"}
        noktalar = [{"tarih": t["timestamp"][:10], "deger": t["populerlik"], "yon": t["yon"]} for t in filtrelenmis[-30:]]
        ortalama = sum(n["deger"] for n in noktalar) / len(noktalar) if noktalar else 0
        return {
            "durum": "başarılı",
            "konu": konu,
            "veri_noktasi": len(noktalar),
            "noktalar": noktalar,
            "ortalama": round(ortalama, 1),
            "min": min(n["deger"] for n in noktalar) if noktalar else 0,
            "max": max(n["deger"] for n in noktalar) if noktalar else 0,
        }
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}
