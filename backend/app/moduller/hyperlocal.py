from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi, TURKCE_SEHIRLER

LOKASYONLAR = [
    "Kuşadası", "Kadınlar Denizi", "Davutlar", "Güzelçamlı",
    "Karaova", "Soğucak", "Yaylaköy", "Çamlık", "Kirazlı",
]
KATEGORILER = [
    "restoran", "otel", "kafe", "plaj", "gezi", "alışveriş",
    "eğlence", "kültür", "spor", "sağlık",
]

def hikaye_uret(lokasyon: str = "", kategori: str = "", dil: str = "tr"):
    try:
        h = modul_hash(f"hikaye_{lokasyon}_{kategori}_{simdi()}")
        lokasyon = lokasyon or modul_sec(f"lok_{h}", LOKASYONLAR)
        kategori = kategori or modul_sec(f"kat_{h}", KATEGORILER)
        template = f"""{lokasyon} bölgesinde {kategori} deneyimi yaşamak isteyenler için harika bir rehber hazırladık. 
Bu yazıda {lokasyon}'un en gözde {kategori} mekanlarını, fiyat aralıklarını ve 
ziyaretçi yorumlarını bulabilirsiniz. {lokasyon} ziyaretinizde mutlaka görmeniz 
gereken yerler listemizde. {'Doğal güzellikleri' if h % 2 == 0 else 'Tarihi dokusu'} 
ile {lokasyon}, her mevsim keşfedilmeyi bekliyor."""
        return {
            "lokasyon": lokasyon,
            "kategori": kategori,
            "hikaye_uzunlugu": len(template),
            "hikaye": template,
            "dil": dil,
            "tahmini_okuma_suresi": f"{len(template) // 300} dk",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(lokasyon: str, format: str = "csv"):
    try:
        sonuc = hikaye_uret(lokasyon)
        if sonuc.get("status") == "hata":
            return sonuc
        if format == "json":
            return {"format": "json", "icerik": modul_export_json([sonuc])}
        else:
            return {"format": "txt", "icerik": sonuc.get("hikaye", "")}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
