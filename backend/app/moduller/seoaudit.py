from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

AUDIT_KONTROLLERI = [
    {"kontrol": "Meta Title", "aciklama": "Sayfa başlığı kontrolü", "max_puan": 10},
    {"kontrol": "Meta Description", "aciklama": "Meta açıklama kontrolü", "max_puan": 10},
    {"kontrol": "H1 Etiketi", "aciklama": "Başlık etiketi varlığı", "max_puan": 8},
    {"kontrol": "Görsel Alt Text", "aciklama": "Görsel alternatif metin", "max_puan": 8},
    {"kontrol": "İç Link Yapısı", "aciklama": "Sayfa içi linkleme", "max_puan": 10},
    {"kontrol": "Sayfa Hızı", "aciklama": "Core Web Vitals", "max_puan": 15},
    {"kontrol": "Mobil Uyum", "aciklama": "Responsive tasarım", "max_puan": 10},
    {"kontrol": "SSL Sertifikası", "aciklama": "HTTPS kontrolü", "max_puan": 5},
    {"kontrol": "Schema Markup", "aciklama": "Yapısal veri varlığı", "max_puan": 8},
    {"kontrol": "İçerik Kalitesi", "aciklama": "Kelime sayısı ve özgünlük", "max_puan": 10},
    {"kontrol": "Kırık Link", "aciklama": "404 hata kontrolü", "max_puan": 6},
]

def denetle(url: str = ""):
    try:
        if not url:
            return {"status": "hata", "hata": "URL belirtilmedi"}
        h = modul_hash(f"audit_{url}")
        toplam_puan = 0
        toplam_max = sum(c["max_puan"] for c in AUDIT_KONTROLLERI)
        detaylar = []
        for kontrol in AUDIT_KONTROLLERI:
            puan = int(modul_yuzde(f"puan_{url}_{kontrol['kontrol']}", 0, kontrol["max_puan"]))
            toplam_puan += puan
            detaylar.append({
                "kontrol": kontrol["kontrol"],
                "puan": f"{puan}/{kontrol['max_puan']}",
                "durum": "başarılı" if puan > kontrol["max_puan"] * 0.6 else "uyarı" if puan > kontrol["max_puan"] * 0.3 else "hata",
            })
        yuzde = (toplam_puan / toplam_max) * 100
        return {
            "url": url,
            "genel_puan": f"%{yuzde:.1f}",
            "toplam_puan": f"{toplam_puan}/{toplam_max}",
            "seviye": "mükemmel" if yuzde > 80 else "iyi" if yuzde > 60 else "orta" if yuzde > 40 else "kötü",
            "detaylar": detaylar,
            "tavsiye": f"En kritik: {[d['kontrol'] for d in detaylar if d['durum'] == 'hata'][:3]}" if any(d["durum"] == "hata" for d in detaylar) else "Her şey yolunda.",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(url: str, format: str = "csv"):
    try:
        sonuc = denetle(url)
        if sonuc.get("status") == "hata":
            return sonuc
        detaylar = sonuc.get("detaylar", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(detaylar)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(f"[{d['durum'].upper()}] {d['kontrol']}: {d['puan']}" for d in detaylar)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(detaylar)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
