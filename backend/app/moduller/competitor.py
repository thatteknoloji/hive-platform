from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

ANALIZ_BOYUTLARI = [
    "Site Otoritesi", "Backlink Profili", "İçerik Kalitesi",
    "Anahtar Kelime Stratejisi", "Sosyal Medya Varlığı", "Teknik SEO",
    "Kullanıcı Deneyimi", "Marka Bilinirliği",
]

def analiz_et(domain: str = ""):
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain belirtilmedi"}
        h = modul_hash(f"comp_{domain}")
        boyutlar = []
        for boyut in ANALIZ_BOYUTLARI:
            puan = modul_yuzde(f"puan_{domain}_{boyut}", 10, 95)
            boyutlar.append({
                "boyut": boyut,
                "puan": f"%{puan:.0f}",
                "durum": "güçlü" if puan > 70 else "orta" if puan > 40 else "zayıf",
            })
        rakip_domainler = []
        for i in range(5):
            rd = modul_sec(f"rakip_{h}_{i}", ["rakip1.com", "rakip2.net", "rakip3.org", "rakip4.com.tr", "rakip5.io", "benzer-site.com", "alternatif.com"])
            if rd != domain and rd not in rakip_domainler:
                rakip_domainler.append(rd)
        return {
            "domain": domain,
            "genel_puan": f"%{sum(int(b['puan'].strip('%')) for b in boyutlar) // len(boyutlar)}",
            "boyutlar": boyutlar,
            "guclu_yonler": [b["boyut"] for b in boyutlar if b["durum"] == "güçlü"][:3],
            "zayif_yonler": [b["boyut"] for b in boyutlar if b["durum"] == "zayıf"][:3],
            "benzer_rakipler": rakip_domainler[:3],
            "tavsiye": f"Zayıf yönleri hedef alın: {', '.join([b['boyut'] for b in boyutlar if b['durum'] == 'zayıf'][:2])}" if any(b["durum"] == "zayıf" for b in boyutlar) else "Rakip güçlü, farklılaşma stratejisi geliştirin.",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(domain: str, format: str = "csv"):
    try:
        sonuc = analiz_et(domain)
        if sonuc.get("status") == "hata":
            return sonuc
        boyutlar = sonuc.get("boyutlar", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(boyutlar)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(f"{b['boyut']}: {b['puan']} ({b['durum']})" for b in boyutlar)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(boyutlar)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
