from datetime import datetime
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi
from app.database import log_module_run

DEMO_BACKLINK_KAYNAKLARI = [
    "spamsitesi1.xyz", "porn-blog.net", "casino-tr.org", "hack-sitesi.com",
    "ucuz-ilac.net", "bot-traffic.xyz", "kalitesiz-dizin.org", "forum-spam.com",
    "sanal-rehber.net", "bahis-sitesi.org", "yorum-sitesi.xyz", "replica-shop.com",
]
DEMO_ANCHORLAR = ["escort", "ucuz", "bedava", "bahis", "casino", "porno", "hack", "ilaç", "takipçi", "bot"]

def log_activity(modul_adi: str, aksiyon: str, durum: str, detay: str):
    log_module_run(
        "KEFEN",
        f"KEFEN - {modul_adi}",
        {"aksiyon": aksiyon, "detay": detay},
        {"durum": durum}
    )

def rakip_backlink_analizi(domain: str):
    try:
        if not domain:
            return {"durum": "hata", "mesaj": "domain gerekli"}
        h = modul_hash(f"kefen_analiz_{domain}")
        adet = 5 + (h % 15)
        backlinkler = []
        for i in range(adet):
            backlinkler.append({
                "source": DEMO_BACKLINK_KAYNAKLARI[(h + i) % len(DEMO_BACKLINK_KAYNAKLARI)],
                "anchor": modul_sec(f"anchor_{i}_{h}", DEMO_ANCHORLAR),
                "dofollow": (h + i) % 3 != 0,
                "date": f"2025-{(h % 12) + 1:02d}-{(h % 28) + 1:02d}",
            })
        log_activity("Backlink Analizi", "rakip_backlink_analizi", "başarılı", domain)
        return {
            "domain": domain,
            "toplam": adet,
            "backlinkler": backlinkler,
        }
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def btk_sikayet_gonder(domain: str):
    try:
        if not domain:
            return {"durum": "hata", "mesaj": "domain gerekli"}
        h = modul_hash(f"kefen_btk_{domain}")
        basarili = h % 5 != 0
        if basarili:
            log_activity("BTK Şikayeti", "btk_sikayet_gonder", "başarılı", domain)
            return {
                "durum": "şikayet iletildi",
                "domain": domain,
                "aciklama": "Fuhşa aracılık ve müstehcen içerik",
                "referans": f"BTK-{modul_hash(f'ref_{domain}') % 1000000:06d}",
            }
        else:
            log_activity("BTK Şikayeti", "btk_sikayet_gonder", "hata", domain)
            return {"durum": "hata", "mesaj": "BTK sunucusuna bağlanılamadı", "domain": domain}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def spam_backlink_gonder(hedef_domain: str, adet: int = 100):
    try:
        if not hedef_domain:
            return {"durum": "hata", "mesaj": "hedef_domain gerekli"}
        adet = max(1, min(10000, adet))
        h = modul_hash(f"kefen_spam_{hedef_domain}_{adet}")
        kaynaklar = ["forumlar", "blog yorumları", "dizinler", "PBN ağı"]
        secilen = kaynaklar[:2 + (h % 3)]
        log_activity("Spam Backlink", "spam_backlink_gonder", "başarılı", f"{hedef_domain} ({adet} adet)")
        return {
            "durum": "spam backlink gönderildi",
            "hedef": hedef_domain,
            "adet": adet,
            "kaynaklar": secilen,
        }
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

def rapor_uret(domain: str):
    try:
        if not domain:
            return {"durum": "hata", "mesaj": "domain gerekli"}
        backlink_sonuc = rakip_backlink_analizi(domain)
        btk_sonuc = btk_sikayet_gonder(domain)
        spam_sonuc = spam_backlink_gonder(domain, 100)
        log_activity("Kapsamlı Rapor", "rapor_uret", "başarılı", domain)
        return {
            "modul": "KEFEN",
            "rakip": domain,
            "backlink_analizi": backlink_sonuc,
            "btk_sikayet": btk_sonuc,
            "spam_sonuc": spam_sonuc,
            "oneriler": [
                "BTK'ya şikayet et",
                "Spam backlink gönder",
                "Rakibin PBN ağını tespit et",
                "Google'a manuel ceza bildir",
            ],
        }
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

analiz_et = rakip_backlink_analizi
