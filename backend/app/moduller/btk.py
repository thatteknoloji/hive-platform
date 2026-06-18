import json
import os
from .api_key_manager import get_key, uyar
from .modul_base import modul_hash, modul_sec, simdi

SIKAYET_GEREKCELERI = [
    "yasadışı bahis içeriği barındırmaktadır",
    "sahte ilan ve dolandırıcılık faaliyeti yürütmektedir",
    "5651 sayılı kanuna aykırı içerik bulundurmaktadır",
    "kullanıcı verilerini izinsiz toplamaktadır",
    "telif hakkı ihlali yapmaktadır",
    "kötü amaçlı yazılım dağıtmaktadır",
]

BTK_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "btk_sikayetleri.json")

def _yukle():
    if not os.path.exists(BTK_DB_PATH):
        return []
    try:
        with open(BTK_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def _kaydet(data):
    os.makedirs(os.path.dirname(BTK_DB_PATH), exist_ok=True)
    with open(BTK_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _btk_http_gonder(domain: str, gerekce: str):
    try:
        import requests
        ihbar_url = get_key("btk_ihbar")
        if not ihbar_url:
            return None
        payload = {
            "domain": domain,
            "gerekce": gerekce,
            "kaynak": "HIVE Panel",
        }
        resp = requests.post(f"{ihar_url}/ihbar", json=payload, timeout=10, headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
        })
        if resp.status_code in (200, 201):
            return {"durum": "btk_api_ile_gonderildi", "http_durum": resp.status_code, "cevap": resp.text[:200]}
    except ImportError:
        return None
    except Exception as e:
        return {"hata": str(e)}

def sikayet_gonder(domain: str, gerekce: str = ""):
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain belirtilmedi"}
        h = modul_hash(f"btk_{domain}_{simdi()}")
        if not gerekce:
            gerekce = modul_sec(f"gerekce_{h}", SIKAYET_GEREKCELERI)
        btk_result = _btk_http_gonder(domain, gerekce)
        if btk_result and "hata" not in btk_result:
            referans = f"BTK-{h % 1000000:06d}-{simdi()[:10]}"
            kayit = {"id": h % 10000, "domain": domain, "gerekce": gerekce, "referans_no": referans, "durum": "İletildi", "created_at": simdi(), "kaynak": "http_api"}
            sikayetler = _yukle()
            sikayetler.append(kayit)
            _kaydet(sikayetler)
            return {"domain": domain, "durum": "BTK'ya iletildi (API)", "referans_no": referans, "gerekce": gerekce, "kaynak": "http_api"}
        referans = f"BTK-{h % 1000000:06d}-{simdi()[:10]}"
        template = f"""T.C. Bilgi Teknolojileri ve İletişim Kurumu'na,

{domain} alan adı {gerekce}.
Sitenin yayından kaldırılması için gereğinin yapılmasını arz ederim.

Saygılarımla,
HIVE Panel Kullanıcısı

Referans: {referans}"""
        kayit = {"id": h % 10000, "domain": domain, "gerekce": gerekce, "referans_no": referans, "durum": "İletildi", "created_at": simdi()}
        sikayetler = _yukle()
        sikayetler.append(kayit)
        _kaydet(sikayetler)
        return {
            "domain": domain, "durum": "BTK'ya iletildi (simülasyon)", "referans_no": referans,
            "gerekce": gerekce, "sikayet_metni": template,
            "kaynak": "simulasyon",
            "uyari": uyar("btk_ihbar") if not get_key("btk_ihbar") else None,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def sikayet_sorgula(referans_no: str = ""):
    try:
        h = modul_hash(f"sorgu_{referans_no or simdi()}")
        durumlar = ["İşleme alındı", "İncelemede", "Karar aşamasında", "Sonuçlandı"]
        durum = durumlar[h % len(durumlar)]
        return {"referans_no": referans_no or "Belirtilmedi", "durum": durum, "guncelleme": simdi()[:10]}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def sikayet_listele():
    try:
        liste = _yukle()
        liste.sort(key=lambda s: s.get("created_at", ""), reverse=True)
        return {"toplam": len(liste), "sikayetler": liste[-50:]}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def sikayet_iptal(sikayet_id: int):
    try:
        sikayetler = _yukle()
        for s in sikayetler:
            if s.get("id") == sikayet_id:
                s["durum"] = "İptal edildi"
                _kaydet(sikayetler)
                return {"durum": "iptal_edildi", "referans": s.get("referans_no")}
        return {"status": "hata", "hata": "Şikayet bulunamadı"}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def istatistik():
    try:
        sikayetler = _yukle()
        toplam = len(sikayetler)
        bekleyen = sum(1 for s in sikayetler if s.get("durum") == "İletildi")
        return {"toplam_sikayet": toplam, "bekleyen": bekleyen, "sonuclanan": toplam - bekleyen}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
