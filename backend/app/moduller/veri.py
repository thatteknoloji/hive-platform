from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi, TURKCE_ISIMLER

VERI_TIPLERI = [
    "TC Kimlik No", "Telefon Numarası", "E-posta Adresi", "Adres",
    "IP Adresi", "Doğum Tarihi", "Kredi Kartı (maskeli)", "Hesap Numarası",
]

def gizlilik_tara(veri: str = ""):
    try:
        if not veri:
            return {"status": "hata", "hata": "Veri belirtilmedi"}
        h = modul_hash(f"veri_{veri}_{simdi()}")
        bulunanlar = []
        tc_pattern = any(k.isdigit() and len(k) == 11 for k in veri.split())
        email_pattern = "@" in veri
        phone_pattern = any(k.startswith("05") and len(k) >= 10 for k in veri.split())
        if tc_pattern:
            bulunanlar.append({"tip": "TC Kimlik No", "risk": "yüksek", "cozum": "Maskelenmeli veya silinmeli"})
        if email_pattern:
            bulunanlar.append({"tip": "E-posta Adresi", "risk": "yüksek", "cozum": "KVKK kapsamında imha edilmeli"})
        if phone_pattern:
            bulunanlar.append({"tip": "Telefon Numarası", "risk": "orta", "cozum": "Anonimleştirilmeli"})
        try:
            import re
            ip_find = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', veri)
            if ip_find:
                for ip in ip_find[:5]:
                    bulunanlar.append({"tip": f"IP Adresi: {ip}", "risk": "düşük", "cozum": "Loglardan temizlenmeli"})
        except:
            pass
        if not bulunanlar:
            bulunanlar.append({"tip": "Kişisel veri tespit edilmedi", "risk": "yok", "cozum": "Herhangi bir işlem gerekmiyor"})
        toplam_bulgu = sum(1 for b in bulunanlar if b["risk"] != "yok")
        return {
            "girilen_veri": veri[:100],
            "bulunan_bulgu": toplam_bulgu,
            "detaylar": bulunanlar,
            "kvkk_uyum": "riskli" if toplam_bulgu > 0 else "uyumlu",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
