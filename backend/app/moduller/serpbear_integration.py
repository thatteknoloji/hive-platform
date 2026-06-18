import json
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote

ANAHTAR_KELIME_VERI = {}

RENKLER = ["#e2b714", "#6b8e23", "#ff4444", "#4488ff", "#ff8844", "#aa66ff"]

def _domain_normalize(domain):
    domain = domain.strip().lower()
    if domain.startswith("http"):
        domain = urlparse(domain).hostname or domain
    domain = domain.replace("www.", "")
    return domain

def _hash_domain(d):
    return int(hashlib.md5(d.encode("utf-8")).hexdigest()[:8], 16)

def _simulasyon_serp(keyword, domain):
    h = _hash_domain(keyword + domain)
    pozisyon = (h % 30) + 1
    url = f"https://www.{domain}/"
    sonuclar = []
    for i in range(10):
        r = (h + i * 7) % 100
        if r == h % 100:
            sonuclar.append({"position": i + 1, "url": url, "title": f"{keyword} - {domain}"})
        else:
            sonuclar.append({
                "position": i + 1,
                "url": f"https://www.rakip{i}.com/{quote(keyword)}",
                "title": f"Rakip {i}: {keyword}"
            })
    return pozisyon, url, sonuclar

def serpbear_ekle(keyword: str, domain: str, device: str = "desktop", country: str = "TR"):
    domain = _domain_normalize(domain)
    anahtar = f"{keyword}:{domain}:{device}:{country}"
    if anahtar in ANAHTAR_KELIME_VERI:
        return {"status": "zaten_var", "mesaj": f"'{keyword}' zaten takip ediliyor ({domain})"}
    pozisyon, url, sonuclar = _simulasyon_serp(keyword, domain)
    now = datetime.now()
    ANAHTAR_KELIME_VERI[anahtar] = {
        "keyword": keyword,
        "domain": domain,
        "device": device,
        "country": country,
        "position": pozisyon,
        "url": url,
        "lastResult": sonuclar,
        "history": {now.strftime("%Y-%m-%d"): pozisyon},
        "added": now.isoformat(),
        "lastUpdated": now.isoformat(),
        "tags": [],
    }
    return {"status": "eklendi", "anahtar": keyword, "domain": domain, "position": pozisyon}

def serpbear_goruntule(keyword: str, domain: str = "", device: str = "desktop", country: str = "TR"):
    if domain:
        domain = _domain_normalize(domain)
        anahtar = f"{keyword}:{domain}:{device}:{country}"
        kayit = ANAHTAR_KELIME_VERI.get(anahtar)
        if kayit:
            pozisyon, url, sonuclar = _simulasyon_serp(keyword, domain)
            now = datetime.now()
            kayit["lastResult"] = sonuclar
            kayit["position"] = pozisyon
            kayit["url"] = url
            kayit["lastUpdated"] = now.isoformat()
            kayit["history"][now.strftime("%Y-%m-%d")] = pozisyon
            historia = [{"gun": g, "pozisyon": p} for g, p in sorted(kayit["history"].items())[-30:]]
            return {
                "status": "aktif",
                "keyword": kayit["keyword"],
                "domain": kayit["domain"],
                "position": pozisyon,
                "url": url,
                "lastResult": sonuclar,
                "history": historia,
                "lastUpdated": kayit["lastUpdated"],
            }
        return {"status": "bulunamadi", "mesaj": f"'{keyword}' için takip kaydı bulunamadı ({domain})"}
    else:
        sonuclar = []
        for anahtar, kayit in ANAHTAR_KELIME_VERI.items():
            if keyword.lower() in kayit["keyword"].lower():
                sonuclar.append({
                    "keyword": kayit["keyword"],
                    "domain": kayit["domain"],
                    "position": kayit["position"],
                    "lastUpdated": kayit["lastUpdated"],
                })
        return {"status": "aktif", "sonuclar": sonuclar, "toplam": len(sonuclar)}

def serpbear_sil(keyword: str, domain: str = ""):
    silinecek = []
    for anahtar in list(ANAHTAR_KELIME_VERI.keys()):
        k, d = anahtar.split(":", 1)[0], anahtar.split(":", 1)[1]
        if keyword.lower() in k.lower():
            if not domain or domain.lower() in d.lower():
                silinecek.append(anahtar)
    for anahtar in silinecek:
        del ANAHTAR_KELIME_VERI[anahtar]
    return {"status": "silindi", "adet": len(silinecek)}

def serpbear_liste():
    liste = []
    for anahtar, kayit in ANAHTAR_KELIME_VERI.items():
        liste.append({
            "keyword": kayit["keyword"],
            "domain": kayit["domain"],
            "position": kayit["position"],
            "device": kayit["device"],
            "lastUpdated": kayit["lastUpdated"],
            "tags": kayit.get("tags", []),
        })
    return {"status": "aktif", "toplam": len(liste), "kayitlar": sorted(liste, key=lambda x: x["position"])}

def serpbear_simulasyon_sonuclari(keyword: str):
    pozisyon, url, sonuclar = _simulasyon_serp(keyword, "ornek-site.com")
    return {
        "keyword": keyword,
        "snippet": [
            {"position": r["position"], "url": r["url"], "title": r["title"]}
            for r in sonuclar
        ],
        "tahmini_pozisyon": pozisyon,
    }
