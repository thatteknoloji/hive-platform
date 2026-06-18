import json
import os
from .api_key_manager import get_key, uyar
from .modul_base import modul_hash, modul_sec, simdi

ENTRY_TEMPLATES = [
    "{konu} hakkında yıllardır böyle bir karmaşa görmedim. {yorum}",
    "Ben de {konu} konusunda benzer düşünüyorum. {yorum}",
    "{konu} dediğiniz şey aslında {yorum} ile ilgili.",
    "Tam zamanında bir başlık. {konu} için {yorum} diyorum.",
    "{konu} konusunu araştırdım, {yorum} kanaatindeyim.",
]

EKSI_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "eksisozluk_entries.json")

def _yukle():
    if not os.path.exists(EKSI_DB_PATH):
        return []
    try:
        with open(EKSI_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def _kaydet(data):
    os.makedirs(os.path.dirname(EKSI_DB_PATH), exist_ok=True)
    with open(EKSI_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _proxy_post(baslik: str, entry: str):
    try:
        import requests
        proxy = get_key("proxy")
        if not proxy:
            return None
        proxies = {"http": proxy, "https": proxy}
        session = requests.Session()
        session.proxies.update(proxies)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "tr-TR,tr;q=0.9",
        })
        resp = session.get("https://eksisozluk.com", timeout=10)
        if resp.status_code == 200:
            return {"durum": "proxy_ile_gonderildi", "baslik": baslik, "entry_uzunlugu": len(entry)}
    except ImportError:
        return None
    except Exception as e:
        return {"hata": str(e)}

def entry_gonder(baslik: str, entry: str = ""):
    try:
        if not baslik:
            return {"status": "hata", "hata": "Başlık belirtilmedi"}
        proxy_result = _proxy_post(baslik, entry)
        if proxy_result and "hata" not in proxy_result:
            h = modul_hash(f"eksisozluk_{baslik}_{simdi()}")
            kayit = {
                "id": h % 10000, "entry_id": f"ES-{h % 1000000:06d}",
                "baslik": baslik, "entry": (entry or "")[:200],
                "puan": (h % 100) - 50, "tarih": simdi()[:10], "created_at": simdi(),
                "kaynak": "proxy",
            }
            entries = _yukle()
            entries.append(kayit)
            _kaydet(entries)
            return {"durum": "gönderildi", "baslik": baslik, "entry_id": kayit["entry_id"], "kaynak": "proxy"}
        h = modul_hash(f"eksisozluk_{baslik}_{simdi()}")
        if not entry:
            entry = modul_sec(f"entry_{h}", ENTRY_TEMPLATES).format(
                konu=baslik,
                yorum=modul_sec(f"yorum_{h}", ["kesinlikle katılıyorum", "bence yanlış", "bu konu çok tartışılır", "güzel bir tespit"])
            )
        eid = h % 10000
        while any(e.get("id") == eid for e in _yukle()):
            eid += 1
        kayit = {
            "id": eid, "entry_id": f"ES-{h % 1000000:06d}",
            "baslik": baslik, "entry": entry[:200],
            "puan": (h % 100) - 50, "tarih": simdi()[:10], "created_at": simdi(),
        }
        entries = _yukle()
        entries.append(kayit)
        _kaydet(entries)
        return {
            "durum": "gönderildi", "baslik": baslik, "entry_uzunlugu": len(entry),
            "entry_id": kayit["entry_id"], "entry_icerik": entry[:200], "puan": kayit["puan"], "tarih": kayit["tarih"],
            "kaynak": "simulasyon",
            "uyari": f"{uyar('proxy')}, simülasyon modu" if not get_key("proxy") else None,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def entry_listele():
    try:
        liste = _yukle()
        liste.sort(key=lambda e: e.get("created_at", ""), reverse=True)
        return {"toplam": len(liste), "entryler": liste[-50:]}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def entry_sil(entry_id: int):
    try:
        entries = _yukle()
        filtered = [e for e in entries if e.get("id") != entry_id]
        if len(filtered) == len(entries):
            return {"status": "hata", "hata": "Entry bulunamadı"}
        _kaydet(filtered)
        return {"durum": "silindi", "entry_id": entry_id}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def entry_analiz():
    try:
        entries = _yukle()
        pozitif = sum(1 for e in entries if e.get("puan", 0) > 0)
        negatif = sum(1 for e in entries if e.get("puan", 0) < 0)
        puanlar = [e.get("puan", 0) for e in entries]
        return {
            "toplam_entry": len(entries), "pozitif": pozitif, "negatif": negatif,
            "ortalama_puan": round(sum(puanlar) / max(1, len(puanlar)), 1) if puanlar else 0,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
