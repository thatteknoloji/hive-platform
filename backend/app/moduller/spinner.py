from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

ES_ANLAMLILAR = {
    "iyi": ["harika", "mükemmel", "başarılı", "kaliteli", "etkili"],
    "kötü": ["berbat", "başarısız", "düşük kaliteli", "etkisiz", "yetersiz"],
    "büyük": ["dev", "geniş", "kapsamlı", "muazzam", "önemli"],
    "küçük": ["ufak", "mini", "dar", "sınırlı", "özel"],
    "hızlı": ["süratli", "çabuk", "seri", "pratik", "ani"],
}

def cevir(metin: str = ""):
    try:
        if not metin:
            return {"status": "hata", "hata": "Metin belirtilmedi"}
        h = modul_hash(f"spin_{metin[:50]}")
        yeni_metin = metin
        for eski, yeniler in ES_ANLAMLILAR.items():
            if eski in yeni_metin.lower():
                yeni_metin = yeni_metin[:]
                yeni_metin = yeni_metin.replace(eski, modul_sec(f"es_{eski}_{h}", yeniler))
        return {
            "orijinal": metin[:200],
            "spinned": yeni_metin[:200],
            "degisim_orani": f"%{modul_yuzde(f'degisim_{h}', 5, 40):.0f}",
            "kelime_sayisi": len(metin.split()),
            "durum": "döndürme tamamlandı",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(metin: str, format: str = "csv"):
    try:
        sonuc = cevir(metin)
        if sonuc.get("status") == "hata":
            return sonuc
        data = [{"tip": "orijinal", "icerik": sonuc["orijinal"]}, {"tip": "spinned", "icerik": sonuc["spinned"]}]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(data)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(data)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

dondur = cevir
