from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

AJAN_TIPLERI = [
    "içerik denetleme", "rakip analizi", "backlink tarama",
    "keyword keşfi", "itibar takibi", "trend analizi",
]
HEDEFLER = ["Moltbook", "Perplexity", "ChatGPT", "Claude", "Gemini"]

def gonder(hedef: str = "", ajan_tipi: str = ""):
    try:
        h = modul_hash(f"ajan_{hedef}_{ajan_tipi}_{simdi()}")
        hedef = hedef or modul_sec(f"hedef_{h}", HEDEFLER)
        ajan_tipi = ajan_tipi or modul_sec(f"tip_{h}", AJAN_TIPLERI)
        sure = 10 + (h % 60)
        toplam_islem = 100 + (h % 900)
        return {
            "hedef": hedef,
            "ajan_tipi": ajan_tipi,
            "ajan_id": f"AJ-{h % 1000000:06d}",
            "durum": "aktif",
            "tahmini_sure": f"{sure} dakika",
            "toplam_islem": toplam_islem,
            "basari_orani": f"%{50 + (h % 45)}",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def durum_sorgula(ajan_id: str = ""):
    try:
        h = modul_hash(f"ajan_durum_{ajan_id or simdi()}")
        durumlar = ["çalışıyor", "tamamlandı", "beklemede", "hata"]
        durum = durumlar[h % len(durumlar)]
        return {
            "ajan_id": ajan_id or "Belirtilmedi",
            "durum": durum,
            "ilerleme": f"%{h % 100}",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
