from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

PLATFORMLAR = [
    "forumlar", "bloglar", "sosyal medya", "haber siteleri",
    "wiki", "yorum siteleri", "Q&A platformları", "basın bültenleri",
]
TEMPLATES = [
    "{marka} hakkında en iyi rehber - {marka} ile ilgili her şey",
    "{marka} kullanıcı yorumları ve deneyimleri",
    "{marka} nedir? Detaylı inceleme ve öneriler",
    "{marka} ile başarıya ulaşmanın yolları",
    "{marka} fiyatları ve kampanyaları",
]

def blast_yap(marka: str, adet: int = 5):
    try:
        if not marka:
            return {"status": "hata", "hata": "Marka adı belirtilmedi"}
        adet = max(1, min(50, adet))
        h = modul_hash(f"brand_{marka}_{simdi()}")
        mentions = []
        for i in range(adet):
            platform = PLATFORMLAR[(h + i) % len(PLATFORMLAR)]
            template = TEMPLATES[(h + i * 3) % len(TEMPLATES)]
            mention = {
                "platform": platform,
                "baslik": template.format(marka=marka),
                "etki_puani": 50 + (modul_hash(f"etki_{marka}_{i}") % 50),
                "tahmini_goruntulenme": 100 * (1 + (modul_hash(f"goruntu_{marka}_{i}") % 500)),
            }
            mentions.append(mention)
        mentions.sort(key=lambda m: -m["etki_puani"])
        return {
            "marka": marka,
            "olusturulan_mention": adet,
            "ortalama_etki": sum(m["etki_puani"] for m in mentions) // adet,
            "mentions": mentions[:10],
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(marka: str, format: str = "csv"):
    try:
        sonuc = blast_yap(marka, 10)
        if sonuc.get("status") == "hata":
            return sonuc
        mentions = sonuc.get("mentions", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(mentions)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n\n".join(f"[{m['platform']}] {m['baslik']} - Etki: {m['etki_puani']}" for m in mentions)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(mentions)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
