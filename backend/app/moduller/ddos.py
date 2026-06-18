from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

SALDIRI_TIPLERI = [
    "SYN Flood", "HTTP Flood", "DNS Amplification", "UDP Flood", "Slowloris",
]
KORUMA_SAGLAYICILARI = ["Cloudflare", "Akamai", "AWS Shield", "Fastly", "Imperva"]

def koruma_aktif(url: str = ""):
    try:
        h = modul_hash(f"ddos_{url or simdi()}")
        risk = modul_yuzde(f"risk_{url}", 0, 100)
        aktif_saldiri = risk > 60
        saldiri_turu = modul_sec(f"tur_{h}", SALDIRI_TIPLERI) if aktif_saldiri else None
        saglayici = modul_sec(f"saglayici_{h}", KORUMA_SAGLAYICILARI)
        return {
            "url": url or "Genel Durum",
            "risk_seviyesi": f"%{risk:.1f}",
            "aktif_saldiri": aktif_saldiri,
            "saldiri_turu": saldiri_turu,
            "oneren_koruma": f"{saglayici} önerilir" if risk > 30 else "Mevcut durum yeterli",
            "saniyedeki_istek": modul_hash(f"req_{url}") % 100000 if aktif_saldiri else 0,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def koruma_test(url: str = ""):
    try:
        h = modul_hash(f"ddos_test_{url or simdi()}")
        ping = 5 + (h % 195)
        sertifikalar = h % 3 != 0
        waf = h % 5 != 0
        return {
            "url": url or "test.hedef.com",
            "ping_ms": ping,
            "ssl_sertifikasi": "geçerli" if sertifikalar else "süresi dolmuş",
            "waf_aktif": waf,
            "guvenlik_puani": f"%{70 + (h % 30)}" if waf and sertifikalar else f"%{h % 40}",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
