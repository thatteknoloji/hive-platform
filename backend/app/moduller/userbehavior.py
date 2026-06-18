import random
def analiz_et(url: str = ""):
    return {"url": url or "belirtilmedi", "ortalama_seyir": f"{random.randint(1, 15)} dk", "sayfa_basina_kalma": f"{random.randint(10, 60)} sn", "cikis_sayfasi": random.choice(["/", "/iletisim", "/hakkimizda"]), "durum": "Kullanıcı davranış analizi tamamlandı (simülasyon)"}
