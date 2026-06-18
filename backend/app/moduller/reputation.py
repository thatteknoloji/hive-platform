from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

KAYNAKLAR = ["Ekşi Sözlük", "Twitter/X", "Reddit", "Google Reviews", "Trustpilot", "Sikayetvar", "Facebook", "Instagram"]

def tara(marka: str = ""):
    try:
        if not marka:
            return {"status": "hata", "hata": "Marka adı belirtilmedi"}
        h = modul_hash(f"reputation_{marka}")
        pozitif = modul_yuzde(f"poz_{marka}", 10, 80)
        negatif = max(0, 100 - pozitif - 20)
        notr = 100 - pozitif - negatif
        bahisler = []
        for i in range(h % 15 + 3):
            kaynak = modul_sec(f"kaynak_{i}", KAYNAKLAR)
            bahisler.append({
                "kaynak": kaynak,
                "icerik": f"{marka} hakkında {modul_sec(f'icerik_{i}', ['olumlu yorum', 'olumsuz yorum', 'nötr bahis', 'kullanıcı deneyimi', 'şikayet'])}",
                "duygu": "olumlu" if modul_hash(f"duygu_{i}") % 3 == 0 else "olumsuz" if modul_hash(f"duygu_{i}") % 3 == 1 else "nötr",
                "tarih": simdi(),
            })
        return {
            "marka": marka,
            "itibar_puani": f"%{pozitif:.0f}",
            "pozitif_oran": f"%{pozitif:.0f}",
            "negatif_oran": f"%{negatif:.0f}",
            "notr_oran": f"%{notr:.0f}",
            "toplam_bahis": len(bahisler),
            "bahisler": bahisler[:10],
            "tehdit_seviyesi": "düşük" if pozitif > 60 else "orta" if pozitif > 40 else "yüksek",
            "tavsiye": "Kriz iletişimi başlatın." if negatif > 40 else "Mevcut durum yönetilebilir.",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(marka: str, format: str = "csv"):
    try:
        sonuc = tara(marka)
        if sonuc.get("status") == "hata":
            return sonuc
        bahisler = sonuc.get("bahisler", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(bahisler)}
        elif format == "txt":
            return {"format": "txt", "icerik": "\n".join(f"[{b['duygu'].upper()}] {b['kaynak']}: {b['icerik']}" for b in bahisler)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(bahisler)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
