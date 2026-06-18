import random
def yonet(url: str = ""):
    return {"url": url or "belirtilmedi", "bulunan_yonlendirme": random.randint(0, 10), "durum": "Yönlendirme taraması tamamlandı (simülasyon)"}
