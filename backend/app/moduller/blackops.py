from .modul_base import modul_hash, modul_sec, simdi

BLACK_MODULLER = [
    "KEFEN", "Zeus", "Phishing", "0-Day Exploit", "Spam Backlink",
    "Backlink Hijacker", "Yorum Botu", "Maps Saldırı",
]
UYARI_METNI = """⚠️⚠️⚠️ BLACK OPS UYARISI ⚠️⚠️⚠️

Bu modüller yasa dışı faaliyetler içerebilir.
- Tüm sorumluluk kullanıcıya aittir.
- HIVE Panel bu modüllerin kullanımından doğacak hukuki sonuçlardan sorumlu değildir.
- Sadece eğitim ve pentest amaçlı kullanın.
- Yetkisiz kullanım yasa dışıdır."""

def aktiflestir():
    try:
        h = modul_hash(f"blackops_{simdi()}")
        return {
            "durum": "TÜM BLACK OPS MODÜLLERİ AKTİF",
            "aktif_moduller": BLACK_MODULLER,
            "toplam_modul": len(BLACK_MODULLER),
            "sorumluluk": "Kullanıcıya ait",
            "uyari": UYARI_METNI,
            "aktivasyon_kodu": f"BLK-{h % 1000000:06d}",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def deaktiflestir():
    return {"durum": "Black Ops modülleri devre dışı", "aktif_moduller": []}
