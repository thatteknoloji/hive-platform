import json
import os
import app.config as config
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

SPAM_PLATFORMLAR = [
    "forum-spam", "blog-comment", "guestbook", "referrer-spam",
    "fake-directory", "link-farm", "wiki-spam", "social-bookmark",
]
ANCHOR_METINLERI = [
    "tıkla", "buraya göz at", "hemen indir", "ücretsiz", "en iyi fiyat",
    "kaçırma", "şimdi al", "detaylı bilgi", "incele", "gör",
]

SPAM_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "spam_backlink_data.json")

def _yukle():
    if not os.path.exists(SPAM_DB_PATH):
        return {"saldirilar": [], "hedefler": []}
    try:
        with open(SPAM_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"saldirilar": [], "hedefler": []}

def _kaydet(data):
    os.makedirs(os.path.dirname(SPAM_DB_PATH), exist_ok=True)
    with open(SPAM_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _spam_post_gonder(domain: str, adet: int):
    try:
        import requests
        proxy = config.get("PROXY_LIST")
        if not proxy:
            return None
        proxies = {"http": proxy, "https": proxy}
        session = requests.Session()
        session.proxies.update(proxies)
        fake_platforms = [
            {"url": f"http://forum-{modul_hash(domain) % 1000}.ru/spam", "method": "POST"},
            {"url": f"http://guestbook-{modul_hash(domain) % 1000}.xyz/add", "method": "POST"},
        ]
        gonderilen = 0
        for platform in fake_platforms:
            try:
                resp = session.post(platform["url"], data={"url": f"https://{domain}", "comment": "check this out"}, timeout=5)
                if resp.status_code < 500:
                    gonderilen += 1
            except:
                pass
        if gonderilen > 0:
            return {"durum": "spam_gonderildi", "adet": gonderilen}
    except ImportError:
        return None
    except:
        pass
    return None

def zehirle(domain: str, adet: int = 1000):
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain belirtilmedi"}
        adet = max(10, min(50000, adet))
        h = modul_hash(f"zehir_{domain}_{simdi()}")
        platform = SPAM_PLATFORMLAR[h % len(SPAM_PLATFORMLAR)]
        spam_result = _spam_post_gonder(domain, adet)
        if spam_result and "hata" not in spam_result:
            data = _yukle()
            data["saldirilar"].append({"hedef": domain, "adet": spam_result["adet"], "platform": platform, "created_at": simdi(), "kaynak": "http"})
            _kaydet(data)
            return {"hedef": domain, "gonderilen_adet": spam_result["adet"], "platform": platform, "kaynak": "http"}
        ornek_linkler = []
        for i in range(min(10, adet)):
            anchor = ANCHOR_METINLERI[(h + i) % len(ANCHOR_METINLERI)]
            ornek_linkler.append({
                "kaynak": f"http://{platform}-{h % 1000}.{['ru','cn','xyz','tk','ml'][(h+i)%5]}/page{i}",
                "anchor": anchor, "puan": 70 + (modul_hash(f"zehir_puan_{i}") % 30),
            })
        data = _yukle()
        data["saldirilar"].append({"hedef": domain, "adet": adet, "platform": platform, "etki": "yüksek" if adet > 5000 else "orta" if adet > 1000 else "düşük", "created_at": simdi()})
        _kaydet(data)
        return {
            "hedef": domain, "gonderilen_adet": adet, "platform": platform,
            "tahmini_sure": f"{(h % 48) + 1} saat",
            "etki_seviyesi": "yüksek" if adet > 5000 else "orta" if adet > 1000 else "düşük",
            "ornek_linkler": ornek_linkler,
            "uyari": "Google cezası riski yüksektir. Dikkatli kullanın.",
            "kaynak": "simulasyon",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def zehirleme_listele():
    try:
        data = _yukle()
        liste = data.get("saldirilar", [])
        liste.sort(key=lambda z: z.get("created_at", ""), reverse=True)
        return {"toplam": len(liste), "saldirilar": liste[-50:]}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def hedef_ekle(domain: str, aciklama: str = ""):
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain gerekli"}
        data = _yukle()
        data.setdefault("hedefler", []).append({"domain": domain, "aciklama": aciklama, "created_at": simdi()})
        _kaydet(data)
        return {"durum": "eklendi", "domain": domain}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def hedef_listele():
    try:
        data = _yukle()
        liste = data.get("hedefler", [])
        liste.sort(key=lambda h: h.get("created_at", ""), reverse=True)
        return {"toplam": len(liste), "hedefler": liste}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def rapor():
    try:
        data = _yukle()
        saldirilar = data.get("saldirilar", [])
        toplam = sum(z.get("adet", 0) for z in saldirilar)
        hedef_sayisi = len(set(z.get("hedef", "") for z in saldirilar))
        return {"toplam_saldiri": len(saldirilar), "toplam_link": toplam, "benzersiz_hedef": hedef_sayisi}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
