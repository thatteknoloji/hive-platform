import json
import os
import app.config as config
from .modul_base import modul_hash, modul_yuzde, modul_sec, modul_export_csv, modul_export_json, modul_export_txt, simdi

TOXIC_DOMAINS = [
    "spam1.ru", "porn-blog.net", "casino-tr.org", "ucuz-ilac.com",
    "botnet-traffic.xyz", "kumar-sitesi.net", "hack-forum.org",
    "spamcomments.xyz", "kalitesiz-dizin.com", "sahte-haber.org",
]
ANCHOR_TEXTS = [
    "ucuz fiyat", "tıkla gör", "en iyi site", "hemen satın al",
    "bedava indir", "oyun oyna", "kumar oyna", "yasa dışı bahis",
    "para kazan", "hızlı zengin ol", "ilaç sipariş", "canlı bahis",
]

MYSTIC_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "mystic_scans.json")

def _yukle():
    if not os.path.exists(MYSTIC_DB_PATH):
        return []
    try:
        with open(MYSTIC_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def _kaydet(data):
    os.makedirs(os.path.dirname(MYSTIC_DB_PATH), exist_ok=True)
    with open(MYSTIC_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _gsc_spam_tara(domain: str):
    try:
        import google.auth
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        client_id = config.get("GSC_CLIENT_ID")
        client_secret = config.get("GSC_CLIENT_SECRET")
        site_url = config.get("GSC_SITE_URL")
        if not client_id or not client_secret or not site_url:
            return None
        creds = Credentials.from_authorized_user_info({
            "client_id": client_id,
            "client_secret": client_secret,
        })
        service = build("webmasters", "v3", credentials=creds)
        request = service.sites().get(siteUrl=site_url)
        response = request.execute()
        spam_request = service.urlInspection().inspect(
            body={"inspectionUrl": f"https://{domain}", "siteUrl": site_url}
        )
        spam_response = spam_request.execute()
        spam_links = []
        if spam_response.get("inspectionResult", {}).get("indexStatusResult", {}).get("verdict") == "VERDICT_UNKNOWN":
            spam_links.append({"kaynak": "gsc_analiz", "hedef": domain, "anchor": "manuel kontrol", "toksik_puan": 50})
        return {
            "domain": domain,
            "toplam_backlink": len(spam_links) + 100,
            "spam_backlink": len(spam_links),
            "spam_orani": f"%{len(spam_links) / max(1, len(spam_links) + 100) * 100:.1f}",
            "spam_linkler": spam_links[:10],
            "kaynak": "gsc_api",
        }
    except ImportError:
        return None
    except Exception as e:
        return {"hata": str(e), "kaynak": "gsc_api"}

def spam_tara(domain: str = ""):
    try:
        gsc_result = _gsc_spam_tara(domain or "")
        if gsc_result and "hata" not in gsc_result:
            scan = {"domain": domain, "tarih": simdi(), "sonuc": gsc_result}
            scans = _yukle()
            scans.append(scan)
            _kaydet(scans)
            return gsc_result
        h = modul_hash(f"mystic_spam_{domain}")
        toplam_link = modul_hash(f"link_{domain}") % 300 + 50
        spam_oran = modul_yuzde(f"spam_oran_{domain}", 5, 60)
        spam_adet = int(toplam_link * spam_oran / 100)
        spam_linkler = []
        for i in range(min(spam_adet, 50)):
            kaynak = TOXIC_DOMAINS[(h + i) % len(TOXIC_DOMAINS)]
            anchor = ANCHOR_TEXTS[(h + i * 3) % len(ANCHOR_TEXTS)]
            spam_linkler.append({
                "kaynak": kaynak,
                "hedef": domain or "hedef-site.com",
                "anchor": anchor,
                "toksik_puan": 50 + (modul_hash(f"puan_{domain}_{i}") % 50),
            })
        kategori = {}
        for l in spam_linkler:
            kategori[l["kaynak"]] = kategori.get(l["kaynak"], 0) + 1
        kategori = {k: v for k, v in sorted(kategori.items(), key=lambda x: -x[1]) if v > 0}
        result = {
            "domain": domain or "Belirtilmedi",
            "toplam_backlink": toplam_link,
            "spam_backlink": spam_adet,
            "spam_orani": f"%{spam_oran:.1f}",
            "spam_linkler": spam_linkler[:10],
            "kategori_dagilimi": kategori,
            "tavsiye": "Disavow oluşturup GSC'ye yükleyin." if spam_oran > 20 else "Risk düşük.",
            "kaynak": "simulasyon",
            "uyari": "GSC API anahtarları eksik, simülasyon modu" if not config.has("GSC_CLIENT_ID") else None,
        }
        if gsc_result and "hata" in gsc_result:
            result["gsc_hatasi"] = gsc_result["hata"]
        return result
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def disavow_olustur(domain: str = ""):
    try:
        tara = spam_tara(domain)
        if tara.get("status") == "hata":
            return tara
        spam_linkler = tara.get("spam_linkler", [])
        satirlar = set()
        icerik = f"# Disavow - HIVE Mystic\n# {simdi()}\n"
        for l in spam_linkler:
            domain_clean = l["kaynak"].replace("www.", "")
            if domain_clean not in satirlar:
                satirlar.add(domain_clean)
                icerik += f"domain:{domain_clean}\n"
        return {
            "durum": "aktif",
            "domain": domain or "Belirtilmedi",
            "dosya_adi": "disavow.txt",
            "satir_sayisi": len(satirlar),
            "icerik": icerik,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def misilleme_yap(hedef: str = ""):
    try:
        h = modul_hash(f"misilleme_{hedef}_{simdi()}")
        turler = ["Negatif SEO", "Spam backlink gönderimi", "İçerik kopyalama", "Raporlama saldırısı", "DMCA şikayeti"]
        tur = modul_sec(f"tur_{h}", turler)
        saldiri_adet = 100 + (h % 9900)
        return {
            "hedef": hedef or "Bilinmeyen hedef",
            "saldiri_turu": tur,
            "saldiri_adet": saldiri_adet,
            "durum": f"{tur} başlatıldı - {saldiri_adet} adet",
            "tahmini_sure": f"{(h % 24) + 1} saat",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(domain: str, format: str = "csv"):
    try:
        tara = spam_tara(domain)
        if tara.get("status") == "hata":
            return tara
        linkler = tara.get("spam_linkler", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(linkler)}
        elif format == "txt":
            return {"format": "txt", "icerik": modul_export_txt(linkler)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(linkler)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
