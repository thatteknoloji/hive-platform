from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

ONERI_TEMPLATES = [
    "benzer içerik", "ilgili makale", "detaylı rehber",
    "devamını oku", "bu konuda daha fazlası",
]

def optimize_et(url: str = ""):
    try:
        if not url:
            return {"status": "hata", "hata": "URL belirtilmedi"}
        h = modul_hash(f"internallink_{url}")
        sayfa_sayisi = 5 + (h % 50)
        mevcut_link = sayfa_sayisi // 3
        oneri_sayisi = max(3, sayfa_sayisi - mevcut_link)
        oneriler = []
        domain_clean = url.replace("https://", "").replace("http://", "").split("/")[0]
        for i in range(min(oneri_sayisi, 10)):
            sayfa = modul_sec(f"sayfa_{h}_{i}", ["seo-rehberi", "icerik-stratejisi", "keyword-arastirmasi", "backlink-kilavuzu", "sosyal-medya-ipuclari", "analiz-raporu", "performans-optimizasyonu", "donanim-ozellikleri"])
            oneriler.append({
                "kaynak": url,
                "hedef": f"https://{domain_clean}/{sayfa}",
                "anchor": modul_sec(f"anchor_{h}_{i}", ONERI_TEMPLATES),
                "oncelik": "yüksek" if i < 3 else "orta",
            })
        return {
            "url": url,
            "toplam_sayfa": sayfa_sayisi,
            "mevcut_ic_link": mevcut_link,
            "oneri_link": len(oneriler),
            "puan_artisi": f"+{5 + (h % 15)}",
            "oneriler": oneriler,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(url: str, format: str = "csv"):
    try:
        sonuc = optimize_et(url)
        if sonuc.get("status") == "hata":
            return sonuc
        oneriler = sonuc.get("oneriler", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(oneriler)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(f"{o['kaynak']} -> {o['hedef']} [{o['oncelik']}]" for o in oneriler)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(oneriler)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
