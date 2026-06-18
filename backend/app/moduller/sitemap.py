from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

FREKANSLAR = ["hourly", "daily", "weekly", "monthly", "yearly"]

def olustur(domain: str = ""):
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain belirtilmedi"}
        h = modul_hash(f"sitemap_{domain}")
        sayfa_sayisi = 10 + (h % 500)
        urller = []
        for i in range(min(sayfa_sayisi, 20)):
            urller.append({
                "loc": f"https://{domain}/{modul_sec(f'path_{i}', ['', 'hakkimizda', 'iletisim', 'blog', f'makale-{i}', f'kategori-{i}'])}",
                "lastmod": simdi(),
                "changefreq": modul_sec(f"freq_{i}", FREKANSLAR),
                "priority": round(0.3 + (modul_hash(f"prio_{i}") % 70) / 100, 1),
            })
        return {
            "domain": domain,
            "toplam_sayfa": sayfa_sayisi,
            "format": "XML Sitemap",
            "ornek_urls": urller[:10],
            "dosya_boyutu": f"{sayfa_sayisi * 0.5:.1f} KB",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(domain: str, format: str = "csv"):
    try:
        sonuc = olustur(domain)
        if sonuc.get("status") == "hata":
            return sonuc
        urller = sonuc.get("ornek_urls", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(urller)}
        elif format == "txt":
            lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
            for u in urller:
                lines.append(f"  <url><loc>{u['loc']}</loc><lastmod>{u['lastmod']}</lastmod><changefreq>{u['changefreq']}</changefreq><priority>{u['priority']}</priority></url>")
            lines.append('</urlset>')
            return {"format": "txt", "icerik": "\n".join(lines)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(urller)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
