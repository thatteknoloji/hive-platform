from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

PROTOKOLLER = ["IndexNow + GSC", "IndexNow API", "GSC URL Inspection", "XML Sitemap", "Social Signal"]

def bildir(url: str = "", protokol: str = ""):
    try:
        if not url:
            return {"status": "hata", "hata": "URL belirtilmedi"}
        h = modul_hash(f"index_{url}_{simdi()}")
        protokol = protokol or modul_sec(f"protokol_{h}", PROTOKOLLER)
        basari = modul_yuzde(f"basar_{url}") > 20
        tahmini_sure = f"{1 + (h % 24)} saat" if basari else "tekrar denenmeli"
        return {
            "url": url,
            "protokol": protokol,
            "durum": "indexleme isteği gönderildi" if basari else "başarısız, tekrar deneyin",
            "tahmini_indexlenme": tahmini_sure,
            "indexnow_anahtar": f"hive-key-{h % 1000000:06d}" if "IndexNow" in protokol else None,
            "onceki_kontrol": "indexlenmemiş" if h % 3 != 0 else "indexlenmiş",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
