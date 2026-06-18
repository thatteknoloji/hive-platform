from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_csv, modul_export_json, simdi

METRIKLER = ["LCP", "FID", "CLS", "TTFB", "FCP"]
DURUMLAR = ["iyi", "iyileştirilmeli", "kötü"]

def optimize_et(url: str = ""):
    try:
        if not url:
            return {"status": "hata", "hata": "URL belirtilmedi"}
        h = modul_hash(f"speed_{url}")
        metrikler = {}
        for m in METRIKLER:
            deger = modul_yuzde(f"{m}_{url}", 0, 100)
            metrikler[m] = {
                "deger": f"{deger:.1f}{'ms' if m != 'CLS' else ''}",
                "durum": DURUMLAR[min(2, int(metrikler_sinir(m, deger)))]
            }
        return {
            "url": url,
            "performance_puani": f"%{modul_yuzde(f'perf_{url}', 30, 98):.0f}",
            "metrikler": metrikler,
            "oneri": f"{modul_sec(f'oneri_{h}', ['Görsel optimize', 'Cache ekle', 'JS küçült', 'CDN kullan', 'Font düzenle'])} yapılmalı",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def metrikler_sinir(m: str, d: float):
    sinirlar = {"LCP": (40, 70), "FID": (30, 60), "CLS": (40, 70), "TTFB": (30, 65), "FCP": (35, 65)}
    alt, ust = sinirlar.get(m, (40, 70))
    return 0 if d < alt else 1 if d < ust else 2

def export(url: str, format: str = "csv"):
    try:
        sonuc = optimize_et(url)
        if sonuc.get("status") == "hata":
            return sonuc
        data = [{"metrik": k, **v} for k, v in sonuc.get("metrikler", {}).items()]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(data)}
        elif format == "txt":
            return {"format": "txt", "icerik": f"Performance: {sonuc['performance_puani']}\nOneri: {sonuc['oneri']}\n" + "\n".join(f"{m['metrik']}: {m['deger']} ({m['durum']})" for m in data)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(data)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
