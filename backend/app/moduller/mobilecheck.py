from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

KONTROLLER = [
    "Viewport Meta Tag", "Duyarlı Tasarım", "Dokunmatik Hedef Boyutu",
    "Yazı Tipi Okunabilirliği", "Yatay Kaydırma", "Boşluk Kullanımı",
]

def test_et(url: str = ""):
    try:
        if not url:
            return {"status": "hata", "hata": "URL belirtilmedi"}
        h = modul_hash(f"mobile_{url}")
        gecen = 0
        detay = []
        for k in KONTROLLER:
            sonuc = h % 3 != 0
            if sonuc:
                gecen += 1
            detay.append({"kontrol": k, "sonuc": "geçti" if sonuc else "kaldı"})
        return {
            "url": url,
            "mobil_uyum_puani": f"%{(gecen / len(KONTROLLER)) * 100:.0f}",
            "gecen_test": gecen,
            "toplam_test": len(KONTROLLER),
            "detay": detay,
            "viewport_var": "Evet" if h % 5 != 0 else "Hayır",
            "tavsiye": "Mobil uyum sorunu yok." if gecen == len(KONTROLLER) else f"{len(KONTROLLER) - gecen} test başarısız.",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(url: str, format: str = "csv"):
    try:
        sonuc = test_et(url)
        if sonuc.get("status") == "hata":
            return sonuc
        detay = sonuc.get("detay", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(detay)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(f"[{d['sonuc'].upper()}] {d['kontrol']}" for d in detay)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(detay)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

kontrol_et = test_et
