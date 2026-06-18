from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

KAYNAKLAR = ["RSS Feed", "API", "Web Scraper", "AI Generator", "Guest Post"]
FREKANSLAR = ["saatlik", "günlük", "haftalık", "aylık"]

def baslat(konfig: str = ""):
    try:
        h = modul_hash(f"autoblog_{simdi()}")
        kaynak = modul_sec(f"kaynak_{h}", KAYNAKLAR)
        frekans = modul_sec(f"frekans_{h}", FREKANSLAR)
        gunluk_adet = 1 + (h % 10)
        return {
            "durum": "otomatik blog çalışıyor",
            "kaynak": kaynak,
            "frekans": frekans,
            "gunluk_makale": gunluk_adet,
            "bugun_uretilen": h % gunluk_adet,
            "toplam_makale": h % 500 + 50,
            "hedef_kategori": modul_sec(f"kat_{h}", ["teknoloji", "sağlık", "finans", "eğitim", "spor", "moda", "yemek"]),
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(konfig: str, format: str = "csv"):
    try:
        sonuc = baslat(konfig)
        if sonuc.get("status") == "hata":
            return sonuc
        data = [{"metrik": k, "deger": v} for k, v in sonuc.items() if k != "durum"]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(data)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(data)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

yayinla = baslat
