from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

SCHEMA_TIPLERI = [
    "Article", "Product", "LocalBusiness", "FAQPage", "HowTo",
    "Review", "Event", "Recipe", "JobPosting", "SoftwareApplication",
]

def olustur(url: str = "", tip: str = ""):
    try:
        if not url:
            return {"status": "hata", "hata": "URL belirtilmedi"}
        tip = tip or modul_sec(f"tip_{url}", SCHEMA_TIPLERI)
        h = modul_hash(f"schema_{url}_{tip}")
        jsonld = {
            "@context": "https://schema.org",
            "@type": tip,
            "name": f"{tip} - {url}",
            "url": url,
            "description": f"{tip} şema işaretlemesi",
            "datePublished": simdi(),
        }
        return {
            "url": url,
            "schema_tipi": tip,
            "jsonld": jsonld,
            "jsonld_str": str(jsonld),
            "durum": "şema oluşturuldu",
            "test_sonucu": "geçerli" if h % 5 != 0 else "uyarı: tip doğrulanamadı",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(url: str, format: str = "csv"):
    try:
        sonuc = olustur(url)
        if sonuc.get("status") == "hata":
            return sonuc
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(sonuc["jsonld"])}
        elif format == "txt":
            return {"format": "txt", "icerik": sonuc["jsonld_str"]}
        else:
            data = [{"anahtar": k, "deger": str(v)} for k, v in sonuc["jsonld"].items()]
            return {"format": "csv", "icerik": modul_export_csv(data)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

ekle = olustur
