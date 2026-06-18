from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi, TURKCE_SEHIRLER

KATEGORILER = ["teknoloji", "sağlık", "eğitim", "finans", "seyahat", "moda", "yemek", "spor"]

def arastir(kelime: str = ""):
    try:
        if not kelime:
            return {"status": "hata", "hata": "Kelime belirtilmedi"}
        h = modul_hash(f"kw_{kelime}")
        hacim = 100 + (h % 50000)
        rekabet = modul_yuzde(f"rekabet_{kelime}", 0.01, 1.0)
        zorluk = modul_yuzde(f"zorluk_{kelime}", 0, 100)
        cpc = round(0.1 + (modul_hash(f"cpc_{kelime}") % 500) / 100, 2)
        trend_yon = "yükselen" if h % 3 != 0 else "düşen"
        ilgili = []
        for i in range(10):
            ilgili.append(f"{kelime} {modul_sec(f'ilgili_{i}', ['nedir', 'nasıl yapılır', 'fiyat', 'yorum', 'ankara', 'istanbul', 'online', 'eğitim', 'sertifika', 'iş ilanları'])}")
        return {
            "kelime": kelime,
            "hacim": hacim,
            "rekabet": f"{rekabet:.2f}",
            "zorluk": f"%{zorluk:.0f}",
            "cpc": f"${cpc}",
            "trend": trend_yon,
            "ilgili_kelimeler": ilgili,
            "tavsiye": "Düşük rekabetli, yüksek hacimli varyasyonları hedefleyin." if rekabet > 0.7 else "Hedeflemek için uygun.",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(kelime: str, format: str = "csv"):
    try:
        sonuc = arastir(kelime)
        if sonuc.get("status") == "hata":
            return sonuc
        ilgili = [{"kelime": k} for k in sonuc.get("ilgili_kelimeler", [])]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(ilgili)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(sonuc.get("ilgili_kelimeler", []))}
        else:
            return {"format": "csv", "icerik": modul_export_csv(ilgili)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
