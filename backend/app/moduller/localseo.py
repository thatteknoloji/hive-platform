import random
def optimize_et(isletme: str = "", adres: str = ""):
    return {"isletme": isletme or "belirtilmedi", "adres": adres or "belirtilmedi", "nap_tutarlilik": f"%{random.randint(60, 100)}", "durum": "Yerel SEO optimizasyonu tamamlandı (simülasyon)"}
