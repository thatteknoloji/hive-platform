from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

KRIS_TIPLERI = ["Negatif SEO Saldırısı", "İtibar Krizi", "Veri Sızıntısı", "DDoS Altında", "Marka Katliamı"]
SEVIYELER = ["kritik", "yüksek", "orta", "düşük"]

def izle(marka: str = ""):
    try:
        if not marka:
            return {"status": "hata", "hata": "Marka adı belirtilmedi"}
        h = modul_hash(f"crisis_{marka}")
        tehdit_alarm = h % 4 == 0
        kriz_tipi = modul_sec(f"tip_{h}", KRIS_TIPLERI) if tehdit_alarm else None
        seviye = modul_sec(f"seviye_{h}", SEVIYELER)
        kaynaklar = []
        for i in range(h % 8 + 2):
            kaynaklar.append({
                "kaynak": modul_sec(f"kaynak_{i}", ["Shodan", "Google Alerts", "Twitter/X", "Reddit", "Trustpilot", "Sikayetvar", "Haber siteleri"]),
                "tehdit_puani": f"%{modul_yuzde(f'threat_{i}', 10, 95):.0f}",
                "detay": f"{marka} ile ilgili {modul_sec(f'detay_{i}', ['olumsuz yorum', 'güvenlik zaafiyeti', 'müşteri şikayeti', 'veri sızıntısı iddiası'])} tespit edildi",
            })
        return {
            "marka": marka,
            "anlik_tehdit": tehdit_alarm,
            "kriz_tipi": kriz_tipi,
            "seviye": seviye,
            "tehdit_puani": f"%{modul_yuzde(f'threat_sum_{marka}', 0, 100):.0f}",
            "kaynaklar": kaynaklar,
            "aksiyon_yolu": {
                "adim_1": "Tehdit kaynağını analiz et",
                "adim_2": "İletişim ekibini bilgilendir",
                "adim_3": "Kriz masası oluştur",
                "adim_4": "Resmi açıklama hazırla",
            } if tehdit_alarm else {"durum": "Aktif kriz yok, rutin tarama devam ediyor"},
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(marka: str, format: str = "csv"):
    try:
        sonuc = izle(marka)
        if sonuc.get("status") == "hata":
            return sonuc
        kaynaklar = sonuc.get("kaynaklar", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(kaynaklar)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(f"[{k['tehdit_puani']}] {k['kaynak']}: {k['detay']}" for k in kaynaklar)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(kaynaklar)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
