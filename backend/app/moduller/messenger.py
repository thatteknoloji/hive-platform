from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

PLATFORMLAR = ["WhatsApp", "Telegram", "Signal"]
GRUPLAR = {
    "WhatsApp": ["SEO Grubu 1", "Dijital Pazarlama TR", "Backlink Ağı", "Webmaster Sohbet"],
    "Telegram": ["SEO Türkiye", "Dijital Reklam", "Freelancer Ağı", "Startup TR"],
    "Signal": ["Gizlilik Grubu", "Teknoloji Sohbet", "Yazılımcılar"],
}

def mesaj_gonder(mesaj: str = "", platform: str = "", adet: int = 3):
    try:
        if not mesaj:
            return {"status": "hata", "hata": "Mesaj belirtilmedi"}
        if platform and platform not in PLATFORMLAR:
            return {"status": "hata", "hata": f"Geçersiz platform: {platform}"}
        h = modul_hash(f"mesaj_{mesaj}_{simdi()}")
        platform = platform or modul_sec(f"platform_{h}", PLATFORMLAR)
        adet = max(1, min(20, adet))
        gruplar = GRUPLAR.get(platform, ["Genel Grup"])
        secilen = []
        for i in range(min(adet, len(gruplar))):
            grp = gruplar[(h + i) % len(gruplar)]
            secilen.append({
                "platform": platform,
                "grup": grp,
                "durum": "gönderildi",
                "tarih": simdi()[:10],
            })
        return {
            "platform": platform,
            "mesaj_uzunlugu": len(mesaj),
            "gonderilen_grup": adet,
            "gruplar": secilen,
            "mesaj_icerik": mesaj[:200],
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def platform_listele():
    return {"platformlar": PLATFORMLAR, "gruplar": GRUPLAR}
