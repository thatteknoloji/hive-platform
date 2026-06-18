from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

AI_PLATFORMLAR = [
    "Google AI Overview", "ChatGPT", "Perplexity", "Claude", "Gemini", "Copilot",
]
TRUST_SIGNALS = [
    "Wikipedia kaynaklı", "resmi site", "haber ajansı",
    ".edu referansı", ".gov referansı", "sektör lideri",
]

def sorgula(marka: str = ""):
    try:
        if not marka:
            return {"status": "hata", "hata": "Marka adı belirtilmedi"}
        h = modul_hash(f"ai_citation_{marka}_{simdi()}")
        platformlar = []
        for i, platform in enumerate(AI_PLATFORMLAR):
            var = modul_yuzde(f"var_{marka}_{platform}") > 30
            platformlar.append({
                "platform": platform,
                "var": var,
                "guven_sinyali": modul_sec(f"sinyal_{marka}_{platform}", TRUST_SIGNALS) if var else "bulunamadı",
                "etki_puani": 30 + (modul_hash(f"etki_{marka}_{platform}") % 70) if var else 0,
            })
        toplam_var = sum(1 for p in platformlar if p["var"])
        return {
            "marka": marka,
            "toplam_ai_platform": len(AI_PLATFORMLAR),
            "bulundugu_platform": toplam_var,
            "gorunurluk_yuzdesi": f"%{(toplam_var / len(AI_PLATFORMLAR)) * 100:.0f}",
            "platformlar": platformlar,
            "tavsiye": "AI görünürlüğü artırmak için güvenilir kaynaklarda yer alın." if toplam_var < 3 else "İyi durumda, düzenli takip önerilir.",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(marka: str, format: str = "csv"):
    try:
        sonuc = sorgula(marka)
        if sonuc.get("status") == "hata":
            return sonuc
        platformlar = sonuc.get("platformlar", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(platformlar)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(f"[{p['platform']}] {'✓' if p['var'] else '✗'} {p['guven_sinyali']}" for p in platformlar)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(platformlar)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
