import random
def insa(kelime: str = "", adet: int = 10):
    return {"kelime": kelime, "hedeflenen_link": adet, "olusuturulan": random.randint(3, adet), "durum": f"{adet} backlink inşa edildi (simülasyon)"}
