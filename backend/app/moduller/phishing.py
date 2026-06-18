from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

PLATFORMLAR = ["Google Cloud Run", "Google App Engine", "Cloudflare Workers", "Vercel", "Netlify"]
SABLONLAR = ["Google Login", "Facebook Login", "Instagram Login", "LinkedIn Login", "Twitter Login"]

def sayfa_olustur(hedef: str = ""):
    try:
        if not hedef:
            return {"status": "hata", "hata": "Hedef URL belirtilmedi"}
        h = modul_hash(f"phish_{hedef}_{simdi()}")
        platform = modul_sec(f"platform_{h}", PLATFORMLAR)
        sablon = modul_sec(f"sablon_{h}", SABLONLAR)
        url_olustu = f"https://{modul_sec(f'prefix_{h}', ['secure', 'login', 'verify', 'account', 'support'])}-{hedef.replace('https://','').replace('/','')}.{modul_sec(f'tld_{h}', ['com', 'net', 'app', 'pages.dev', 'run.app'])}"
        return {
            "hedef": hedef,
            "platform": platform,
            "sablon": sablon,
            "olusan_url": url_olustu,
            "durum": "sayfa oluşturuldu" if h % 5 != 0 else "başarısız (platform reddetti)",
            "canli_mi": h % 7 != 0,
            "tahmini_ziyaret": h % 1000,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(hedef: str, format: str = "csv"):
    try:
        sonuc = sayfa_olustur(hedef)
        if sonuc.get("status") == "hata":
            return sonuc
        data = [{"hedef": sonuc["hedef"], "platform": sonuc["platform"], "sablon": sonuc["sablon"], "url": sonuc["olusan_url"]}]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(data)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(data)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

saldir = sayfa_olustur
