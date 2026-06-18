import random
def paylas(platform: str = "Twitter", mesaj: str = ""):
    return {"platform": platform, "mesaj_uzunlugu": len(mesaj), "durum": f"{platform}'da paylaşım yapıldı (simülasyon)", "begeni": random.randint(10, 200)}
