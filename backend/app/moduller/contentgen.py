from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

TONLAR = ["resmi", "samimi", "teknik", "pazarlama", "bilgilendirici"]
KONULAR = ["SEO Nedir?", "Dijital Pazarlama Stratejileri", "Web Sitesi Optimizasyonu", "İçerik Pazarlaması", "Backlink Oluşturma"]

def olustur(konu: str = "", uzunluk: str = "orta"):
    try:
        konu = konu or modul_sec(f"konu_{simdi()}", KONULAR)
        h = modul_hash(f"content_{konu}")
        ton = modul_sec(f"ton_{h}", TONLAR)
        uzunluk_map = {"kisa": 150, "orta": 500, "uzun": 1500}
        hedef_kelime = uzunluk_map.get(uzunluk, 500)
        kelime_sayisi = hedef_kelime + (h % 200)
        paragraf_sayisi = max(2, kelime_sayisi // 100)
        paragraflar = []
        for i in range(paragraf_sayisi):
            paragraflar.append(f"Paragraf {i+1}: {konu} ile ilgili {ton} tonda {'içerik' if h % 2 == 0 else 'bilgi'} üretildi.")
        return {
            "konu": konu,
            "ton": ton,
            "kelime_sayisi": kelime_sayisi,
            "paragraf_sayisi": paragraf_sayisi,
            "paragraflar": paragraflar,
            "durum": "içerik hazır",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(konu: str, format: str = "csv"):
    try:
        sonuc = olustur(konu)
        if sonuc.get("status") == "hata":
            return sonuc
        pars = [{"paragraf": i+1, "icerik": p} for i, p in enumerate(sonuc.get("paragraflar", []))]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(pars)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n\n".join(sonuc.get("paragraflar", []))}
        else:
            return {"format": "csv", "icerik": modul_export_csv(pars)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
