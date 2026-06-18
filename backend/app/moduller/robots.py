from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

USER_AGENTLER = ["Googlebot", "Bingbot", "YandexBot", "Baidoospider", "GPTBot", "Claude-Web", "*"]

def duzenle(domain: str = "", politika: str = "standart"):
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain belirtilmedi"}
        h = modul_hash(f"robots_{domain}")
        satirlar = [f"# Robots.txt - {domain}", f"# Oluşturma: {simdi()}", ""]
        for ua in USER_AGENTLER:
            satirlar.append(f"User-agent: {ua}")
            if politika == "agresif":
                satirlar.append("Disallow: /")
            elif politika == "seo":
                satirlar.append("Allow: /")
                satirlar.append("Disallow: /wp-admin/")
                satirlar.append("Disallow: /admin/")
                satirlar.append("Disallow: /private/")
            else:
                satirlar.append("Disallow: /admin/")
                satirlar.append("Disallow: /private/")
            satirlar.append(f"Crawl-delay: {5 + (h % 10)}")
            satirlar.append("")
        sitemap_path = "wp-sitemap.xml" if politika == "seo" else "sitemap.xml"
        satirlar.append(f"Sitemap: https://{domain}/{sitemap_path}")
        return {
            "domain": domain,
            "politika": politika,
            "satir_sayisi": len(satirlar),
            "icerik": "\n".join(satirlar),
            "durum": "robots.txt hazır",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(domain: str, format: str = "csv"):
    try:
        sonuc = duzenle(domain)
        if sonuc.get("status") == "hata":
            return sonuc
        if format == "txt":
            return {"format": "txt", "icerik": sonuc["icerik"]}
        data = [{"satir": i+1, "icerik": s} for i, s in enumerate(sonuc["icerik"].split("\n"))]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(data)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(data)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
