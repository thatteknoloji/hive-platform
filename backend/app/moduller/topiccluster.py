from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

SORU_KALIPLARI = [
    "{konu} nedir?", "{konu} nasıl yapılır?", "{konu} neden önemlidir?",
    "{konu} için en iyi araçlar", "{konu} örnekleri", "{konu} fiyatları",
    "{konu} hakkında bilinmesi gerekenler", "{konu} ile ilgili sık sorulan sorular",
]

def olustur(konu: str = "", cluster_sayisi: int = 5):
    try:
        if not konu:
            return {"status": "hata", "hata": "Konu belirtilmedi"}
        cluster_sayisi = max(3, min(20, cluster_sayisi))
        h = modul_hash(f"cluster_{konu}")
        pillar = f"{konu} Kapsamlı Rehberi {simdi()[:4]}"
        clusters = []
        for i in range(cluster_sayisi):
            alt_konu = modul_sec(f"alt_{konu}_{i}", [
                "temel kavramlar", "ileri teknikler", "başlangıç rehberi",
                "uzman ipuçları", "vaka çalışmaları", "araç ve kaynaklar",
                "sık yapılan hatalar", "strateji geliştirme",
            ])
            soru = SORU_KALIPLARI[(h + i) % len(SORU_KALIPLARI)].format(konu=f"{konu} {alt_konu}")
            clusters.append({
                "cluster_basligi": f"{konu} {alt_konu}",
                "aciklama": soru,
                "hedef_kelime": f"{konu} {alt_konu}",
                "tahmini_trafik": 100 + (modul_hash(f"trafik_{konu}_{i}") % 5000),
            })
        return {
            "konu": konu,
            "pillar_sayfa": pillar,
            "cluster_sayisi": len(clusters),
            "clusters": clusters,
            "tahmini_toplam_trafik": sum(c["tahmini_trafik"] for c in clusters),
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(konu: str, format: str = "csv"):
    try:
        sonuc = olustur(konu)
        if sonuc.get("status") == "hata":
            return sonuc
        clusters = sonuc.get("clusters", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(clusters)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n\n".join(f"[{c['cluster_basligi']}]\n{c['aciklama']}\nTrafik: {c['tahmini_trafik']}" for c in clusters)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(clusters)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
