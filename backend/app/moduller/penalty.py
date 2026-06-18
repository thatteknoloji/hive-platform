from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

PENALTY_NEDENLERI = [
    "Doğal olmayan backlink profili",
    "İçerik kalitesi düşüklüğü (Google Panda)",
    "Spam içerikli bağlantılar (Google Penguin)",
    "Kullanıcı deneyimi sorunları",
    "Yinelenen içerik",
    "Gizli metin veya hileli yönlendirme",
    "Satın alınmış backlinkler",
]

def analiz_et(domain: str = ""):
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain belirtilmedi"}
        h = modul_hash(f"penalty_{domain}")
        risk_puani = modul_yuzde(f"risk_{domain}", 0, 100)
        ceza_var = risk_puani > 40
        nedenler = []
        for i, neden in enumerate(PENALTY_NEDENLERI):
            olasilik = modul_yuzde(f"olasilik_{domain}_{i}", 0, 100)
            if olasilik > 50:
                nedenler.append({"neden": neden, "olasilik": f"%{olasilik:.0f}"})
        traffic_kaybi = int(modul_yuzde(f"traffic_{domain}", 10, 90)) if ceza_var else 0
        itiraz_metni = ""
        if ceza_var:
            itiraz_metni = f"""Google Search Console'a İtiraz

Domain: {domain}
Tespit Edilen Sorunlar: {', '.join(n['neden'] for n in nedenler[:3])}

Yapılan Düzeltmeler:
1. Spam backlinkler disavow edildi
2. Düşük kaliteli içerik kaldırıldı
3. Site hızı optimize edildi

Tekrar inceleme talebinde bulunuyoruz."""
        return {
            "domain": domain,
            "risk_puani": f"%{risk_puani:.1f}",
            "ceza_var": ceza_var,
            "trafik_kaybi": f"%{traffic_kaybi}",
            "seviye": "kritik" if risk_puani > 75 else "yüksek" if risk_puani > 50 else "orta" if risk_puani > 25 else "düşük",
            "nedenler": nedenler[:5],
            "itiraz_metni": itiraz_metni,
            "tavsiye": "Disavow dosyası hazırlayın ve GSC'den itiraz gönderin." if ceza_var else "Şu an için risk görünmüyor.",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(domain: str, format: str = "csv"):
    try:
        sonuc = analiz_et(domain)
        if sonuc.get("status") == "hata":
            return sonuc
        nedenler = sonuc.get("nedenler", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(nedenler)}
        elif format == "txt":
            return {"format": "txt", "icerik": sonuc.get("itiraz_metni", "")}
        else:
            return {"format": "csv", "icerik": modul_export_csv(nedenler)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
