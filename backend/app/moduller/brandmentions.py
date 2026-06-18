import random
def tara(marka: str = ""):
    adet = random.randint(10, 40)
    return {"marka": marka or "belirtilmedi", "mention_sayisi": adet, "durum": f"{adet} platformda marka tespit edildi (simülasyon)"}
