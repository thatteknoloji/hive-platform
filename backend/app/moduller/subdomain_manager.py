from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

_site_basliklari = [
    "VIP Escort Model", "Elit Masaj Salonu", "Canlı Sohbet Odaları",
    "Yetişkin Filmler", "Partner Arama Platformu", "Özel Dans Stüdyosu",
    "Görüntülü Sohbet", "Premium Refakat", "Lüks Eskort Hizmeti",
    "Gece Hayatı Rehberi", "Özel Fotoğraf Çekimi", "Model Ajansı",
]

_subdomain_db = {}
_subdomain_counter = [0]

def _sub_id():
    _subdomain_counter[0] += 1
    return _subdomain_counter[0]

def subdomain_ekle(domain_id: int = 0, subdomain: str = "", site_title: str = "",
                   admin_email: str = "", parent_domain: str = "",
                   icerik_doldur: bool = False):
    try:
        sid = _sub_id()
        h = modul_hash(f"sub_{subdomain}_{domain_id}_{simdi()}")
        site_baslik = site_title or modul_sec(f"st_{sid}", _site_basliklari)
        email = admin_email or f"admin@{subdomain}.com"
        tam_domain = f"{subdomain}.{parent_domain}" if parent_domain else f"{subdomain}.multisite.com"
        sayfa_sayisi = 3 + (h % 8) if icerik_doldur else 0
        kayit = {
            "id": sid,
            "domain_id": domain_id,
            "subdomain": subdomain,
            "tam_domain": tam_domain,
            "site_title": site_baslik,
            "admin_email": email,
            "multisite_site_id": domain_id * 1000 + sid,
            "wp_admin_url": f"https://{tam_domain}/wp-admin",
            "icerik_dolu": icerik_doldur,
            "sayfa_sayisi": sayfa_sayisi,
            "durum": "aktif",
            "created_at": simdi(),
        }
        _subdomain_db[sid] = kayit
        return kayit
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def subdomain_listele(domain_id: int = 0):
    try:
        liste = [s for s in _subdomain_db.values() if s["domain_id"] == domain_id]
        return {"domain_id": domain_id, "toplam": len(liste), "subdomainler": liste}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def subdomain_sil(sub_id: int):
    try:
        if sub_id in _subdomain_db:
            silinen = _subdomain_db.pop(sub_id)
            return {"silinen_id": sub_id, "subdomain": silinen.get("tam_domain"), "durum": "silindi"}
        return {"status": "hata", "hata": f"Subdomain #{sub_id} bulunamadı"}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def subdomain_duzenle(sub_id: int, site_title: str = "", admin_email: str = ""):
    try:
        if sub_id not in _subdomain_db:
            return {"status": "hata", "hata": f"Subdomain #{sub_id} bulunamadı"}
        kayit = _subdomain_db[sub_id]
        if site_title:
            kayit["site_title"] = site_title
        if admin_email:
            kayit["admin_email"] = admin_email
        kayit["updated_at"] = simdi()
        return {"guncellendi": True, "subdomain": kayit}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def subdomain_talondan_olustur(domain_id: int = 0, kelimeler: list = None,
                                parent_domain: str = "", icerik_doldur: bool = True):
    try:
        h = modul_hash(f"talon_sub_{domain_id}_{simdi()}")
        if not kelimeler:
            kelimeler = [
                "vip-model", "anal-escort", "oral-masaj", "otel-escort",
                "kadinlar-denizi", "gece-escort", "sisman-escort", "minyon-escort",
                "ucuz-escort", "luks-escort", "groups-escort", "snob-escort",
                "genc-escort", "olgun-escort", "turk-escort", "yabancı-escort",
                "escort-kadin", "escort-bayan", "escort-kiz", "escort-arkadasi",
            ][:30]
        olusan = []
        for i, kw in enumerate(kelimeler):
            sub_slug = kw.lower().replace(" ", "-").replace("ı","i").replace("ü","u").replace("ö","o").replace("ç","c").replace("ş","s").replace("ğ","g")
            sub_slug = "".join(c for c in sub_slug if c.isalnum() or c == "-")
            if not sub_slug or len(sub_slug) < 2:
                continue
            site_baslik = f"{kw.replace('-',' ').title()} Escort"
            sub = subdomain_ekle(
                domain_id=domain_id,
                subdomain=sub_slug[:50],
                site_title=site_baslik,
                admin_email=f"admin@{sub_slug}.com",
                parent_domain=parent_domain,
                icerik_doldur=icerik_doldur,
            )
            olusan.append(sub)
        return {
            "domain_id": domain_id,
            "kaynak": "Talon",
            "kelime_sayisi": len(kelimeler),
            "olusturulan_subdomain": len(olusan),
            "icerik_dolduruldu": icerik_doldur,
            "subdomainler": [s.get("subdomain") for s in olusan],
            "durum": "tamamlandi",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def subdomain_batch_sil(sub_ids: list):
    try:
        silinen = []
        for sid in sub_ids:
            if sid in _subdomain_db:
                silinen.append(_subdomain_db.pop(sid).get("tam_domain"))
        return {"silinen_sayi": len(silinen), "silinenler": silinen}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def subdomain_batch_sifirla(sub_ids: list):
    try:
        sonuclar = []
        for sid in sub_ids:
            if sid in _subdomain_db:
                h2 = modul_hash(f"sub_reset_{sid}_{simdi()}")
                sifre = f"Admin@{h2 % 100000}!pass"
                sonuclar.append({
                    "sub_id": sid,
                    "subdomain": _subdomain_db[sid].get("tam_domain"),
                    "yeni_sifre": sifre,
                })
        return {"islem_sayisi": len(sonuclar), "sonuclar": sonuclar}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def subdomain_batch_plugin(sub_ids: list, plugin_adi: str = ""):
    try:
        p_adi = plugin_adi or modul_sec(f"sub_p_{simdi()}", ["Rank Math SEO", "Elementor Pro", "WP Rocket", "Wordfence"])
        sonuclar = []
        for sid in sub_ids:
            if sid in _subdomain_db:
                sonuclar.append({
                    "sub_id": sid,
                    "subdomain": _subdomain_db[sid].get("tam_domain"),
                    "plugin": p_adi,
                    "durum": "yuklendi",
                })
        return {"islem_sayisi": len(sonuclar), "plugin": p_adi, "sonuclar": sonuclar}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
