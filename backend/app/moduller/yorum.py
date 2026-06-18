from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi, TURKCE_ISIMLER

YORUM_METINLERI = [
    "Çok faydalı bir yazı, emeğinize sağlık.",
    "Teşekkürler, tam aradığım bilgilerdi.",
    "Bu konuda daha detaylı bir makale bekliyoruz.",
    "Harika içerik, devamını bekliyoruz.",
    "Bilgiler için teşekkürler, çok açıklayıcı olmuş.",
    "Yıllardır bu konuyu araştırıyorum, çok iyi özetlemişsiniz.",
    "Ellerinize sağlık, gerçekten kaliteli bir içerik.",
    "Bazı noktalara katılmıyorum ama genel olarak başarılı.",
]

def yorum_yap(url: str = "", adet: int = 5):
    try:
        if not url:
            return {"status": "hata", "hata": "URL belirtilmedi"}
        adet = max(1, min(50, adet))
        h = modul_hash(f"yorum_{url}_{simdi()}")
        yorumlar = []
        for i in range(adet):
            isim = TURKCE_ISIMLER[(h + i) % len(TURKCE_ISIMLER)]
            metin = YORUM_METINLERI[(h + i * 3) % len(YORUM_METINLERI)]
            puan = 3 + (modul_hash(f"yorum_puan_{i}") % 3)
            yorumlar.append({"isim": isim, "puan": min(5, puan), "yorum": metin, "tarih": simdi()[:10]})
        return {
            "url": url,
            "gonderilen_yorum": adet,
            "ortalama_puan": sum(y["puan"] for y in yorumlar) / adet,
            "yorumlar": yorumlar[:10],
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
