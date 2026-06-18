import random
def gonder(konu: str = "", adet: int = 100):
    return {"konu": konu, "gonderilen": adet, "acilma_orani": f"%{random.randint(10, 45)}", "durum": f"{adet} e-posta gönderildi (simülasyon)"}
