from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

PLATFORMLAR = ["WordPress", "Joomla", "Drupal", "Magento", "Laravel", "Shopify"]
SEVIYELER = ["kritik", "yüksek", "orta", "düşük"]

def zafiyet_tara(hedef: str = ""):
    try:
        if not hedef:
            return {"status": "hata", "hata": "Hedef URL belirtilmedi"}
        h = modul_hash(f"zday_{hedef}")
        platform = modul_sec(f"platform_{h}", PLATFORMLAR)
        zafiyet_sayisi = h % 12
        zafiyetler = []
        for i in range(zafiyet_sayisi):
            zafiyetler.append({
                "tip": modul_sec(f"tip_{i}", ["XSS", "SQL Injection", "CSRF", "RCE", "File Upload", "LFI", "SSRF", "XXE"]),
                "seviye": modul_sec(f"seviye_{i}", SEVIYELER),
                "cvss": round(3 + (modul_hash(f"cvss_{i}") % 70) / 10, 1),
                "plugin": f"{modul_sec(f'plugin_{i}', ['contact-form-7', 'elementor', 'woocommerce', 'yoast-seo', 'jetpack'])} v{modul_hash(f'ver_{i}') % 5}.{modul_hash(f'ver2_{i}') % 10}",
            })
        return {
            "hedef": hedef,
            "platform": platform,
            "toplam_zafiyet": zafiyet_sayisi,
            "kritik_zafiyet": sum(1 for z in zafiyetler if z["seviye"] == "kritik"),
            "zafiyetler": zafiyetler[:15],
            "guvenlik_puani": f"%{max(0, 100 - zafiyet_sayisi * 15)}",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(hedef: str, format: str = "csv"):
    try:
        sonuc = zafiyet_tara(hedef)
        if sonuc.get("status") == "hata":
            return sonuc
        zafs = sonuc.get("zafiyetler", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(zafs)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(f"[{z['seviye'].upper()}] {z['tip']} - CVSS {z['cvss']} ({z['plugin']})" for z in zafs)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(zafs)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

ara = zafiyet_tara
