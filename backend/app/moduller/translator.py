from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

DILLER = ["İngilizce", "Almanca", "Fransızca", "İspanyolca", "Rusça", "Arapça", "Çince", "Japonca"]

def cevir(metin: str = "", hedef_dil: str = ""):
    try:
        if not metin:
            return {"status": "hata", "hata": "Metin belirtilmedi"}
        hedef_dil = hedef_dil or modul_sec(f"dil_{simdi()}", DILLER)
        h = modul_hash(f"trans_{metin[:30]}_{hedef_dil}")
        return {
            "orijinal": metin[:200],
            "hedef_dil": hedef_dil,
            "ceviri": f"[{hedef_dil}] {metin[:100]} [sembolik çeviri]",
            "kelime_sayisi": len(metin.split()),
            "guven_puani": f"%{70 + (h % 25):.0f}",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(metin: str, format: str = "csv"):
    try:
        sonuc = cevir(metin)
        if sonuc.get("status") == "hata":
            return sonuc
        data = [{"tip": "orijinal", "icerik": sonuc["orijinal"]}, {"tip": "ceviri", "dil": sonuc["hedef_dil"], "icerik": sonuc["ceviri"]}]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(data)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(data)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
