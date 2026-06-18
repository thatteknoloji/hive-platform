from .modul_base import modul_hash, modul_sec, simdi

SITE_TEMPLERI = [
    "Escort Parlor", "VIP Model", "Masaj Salonu", "Yetişkin İçerik",
    "Canlı Sohbet", "Partner Bulma", "Görüntülü Sohbet", "Özel Dans",
]
JWT_SECRETS = ["wp_jwt_secret_key", "supersecret_jwt_token", "multisite_auth_key"]
MULTISITE_ENDPOINTS = [
    "https://admin.example.com/wp-json/multisite/v1/sites",
    "https://yonetim.ornek.com/wp-json/multisite/v1/sites",
]
WPVERSIONS = ["6.4.2", "6.5.1", "6.6.0", "6.7.1"]
ICERIK_SABLONLARI = {
    "ana_sayfa": [
        "Hoş Geldiniz – En Özel Hizmetler",
        "VIP Escort & Masaj Hizmetleri",
        "7/24 Profesyonel Hizmet",
    ],
    "alt_sayfalar": [
        "Hakkımızda", "Hizmetlerimiz", "Galeri", "Fiyatlar",
        "Müşteri Yorumları", "Sıkça Sorulan Sorular", "İletişim",
        "Rezervasyon", "Gizlilik Politikası", "Şartlar ve Koşullar",
    ],
    "seo_kelimeleri": [
        "vip escort", "masaj salonu", "özel hizmet", "profesyonel model",
        "sınırsız eğlence", "gece hayatı", "premium refakat",
    ],
}

_site_db = {}
_site_counter = [0]

def _site_id():
    _site_counter[0] += 1
    return _site_counter[0]

def site_olustur(subdomain: str = "", baslik: str = "", email: str = "", domain: str = ""):
    try:
        sid = _site_id()
        h = modul_hash(f"wp_{subdomain}_{baslik}_{simdi()}")
        domain_adi = domain or f"{subdomain}.multisite.com"
        wp_versiyon = modul_sec(f"wpv_{sid}", WPVERSIONS)
        jwt = modul_sec(f"jwt_{sid}", JWT_SECRETS)
        endpoint = modul_sec(f"ep_{sid}", MULTISITE_ENDPOINTS)
        site_data = {
            "id": sid,
            "subdomain": subdomain,
            "domain": domain_adi,
            "baslik": baslik or f"Site #{sid}",
            "admin_email": email or f"admin@{subdomain}.com",
            "wp_version": wp_versiyon,
            "multisite_id": sid * 100 + (h % 100),
            "jwt_token": f"{jwt}.{sid}.{h % 10000}",
            "rest_endpoint": f"{endpoint}/{sid}",
            "icerik_dolu": False,
            "sayfa_sayisi": 0,
            "durum": "aktif",
            "created_at": simdi(),
        }
        _site_db[sid] = site_data
        return site_data
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def site_listele():
    try:
        liste = list(_site_db.values())
        return {"toplam": len(liste), "siteler": liste}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def site_sil(site_id: int):
    try:
        if site_id in _site_db:
            silinen = _site_db.pop(site_id)
            return {"silinen_id": site_id, "domain": silinen.get("domain"), "durum": "silindi"}
        return {"status": "hata", "hata": f"Site #{site_id} bulunamadı"}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def site_sifirla(site_id: int, yeni_sifre: str = ""):
    try:
        if site_id not in _site_db:
            return {"status": "hata", "hata": f"Site #{site_id} bulunamadı"}
        site = _site_db[site_id]
        h = modul_hash(f"reset_{site_id}_{simdi()}")
        sifre = yeni_sifre or f"Admin@{h % 100000}!pass"
        return {
            "site_id": site_id,
            "domain": site.get("domain"),
            "yeni_sifre": sifre,
            "wp_admin_url": f"https://{site.get('domain')}/wp-admin",
            "durum": "sifre_sifirlandi",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def site_icerik_doldur(domain_id: int = 0):
    try:
        h = modul_hash(f"icerik_{domain_id}_{simdi()}")
        ana_baslik = modul_sec(f"as_{h}", ICERIK_SABLONLARI["ana_sayfa"])
        alt_sayfa_sayisi = 4 + (h % 7)
        secilen_alt = [ICERIK_SABLONLARI["alt_sayfalar"][(h + i) % len(ICERIK_SABLONLARI["alt_sayfalar"])]
                       for i in range(alt_sayfa_sayisi)]
        seo_kelimeler = [ICERIK_SABLONLARI["seo_kelimeleri"][(h // 3 + i) % len(ICERIK_SABLONLARI["seo_kelimeleri"])]
                         for i in range(3)]
        sayfalar = []
        sayfalar.append({
            "baslik": ana_baslik,
            "slug": "/",
            "tip": "Ana Sayfa",
            "icerik_uzunlugu": f"{2000 + (h % 3000)} karakter",
            "h1": ana_baslik,
            "meta_description": f"Profesyonel {seo_kelimeler[0].lower()} hizmetleri. {alt_sayfa_sayisi} farklı kategoride premium deneyim.",
        })
        for i, s in enumerate(secilen_alt):
            kelime = seo_kelimeler[i % len(seo_kelimeler)]
            sayfalar.append({
                "baslik": f"{s} | {kelime}",
                "slug": f"/{s.lower().replace(' ','-').replace('ı','i').replace('ü','u').replace('ö','o').replace('ç','c').replace('ş','s').replace('ğ','g')}",
                "tip": s,
                "icerik_uzunlugu": f"{800 + ((h + i) % 2200)} karakter",
                "h1": s,
                "seo_kelime": kelime,
                "sss_eklendi": (h + i) % 2 == 0,
            })
        for sid in _site_db:
            if domain_id == 0 or _site_db[sid].get("multisite_id", 0) // 100 == domain_id or domain_id == 0:
                _site_db[sid]["icerik_dolu"] = True
                _site_db[sid]["sayfa_sayisi"] = len(sayfalar)
        from .subdomain_manager import _subdomain_db
        for sid in _subdomain_db:
            if domain_id == 0 or _subdomain_db[sid].get("domain_id") == domain_id:
                pass
        return {
            "domain_id": domain_id or "tum_siteler",
            "ana_sayfa_basligi": ana_baslik,
            "olusturulan_sayfa": len(sayfalar),
            "toplam_sayfa": len(sayfalar),
            "sayfalar": sayfalar[:8],
            "seo_kelimeler": seo_kelimeler,
            "wp_cache_temizlendi": True,
            "permalink_yapisi": "/%postname%/",
            "durum": "icerik_dolduruldu",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def site_batch_plugin(domain_ids: list, plugin_adi: str):
    try:
        sonuclar = []
        for did in domain_ids:
            sonuclar.append({
                "domain_id": did,
                "plugin": plugin_adi,
                "durum": "yuklendi",
                "wp_cli_cikti": f"Plugin {plugin_adi} başarıyla yüklendi ve aktifleştirildi",
            })
        return {"islem_sayisi": len(sonuclar), "plugin": plugin_adi, "sonuclar": sonuclar}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
