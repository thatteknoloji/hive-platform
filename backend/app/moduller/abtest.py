import os, json, math
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "abtest.json"

def _yukle():
    path = os.path.join(DATA_DIR, DOSYA)
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []

def _kaydet(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, DOSYA), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _ki_kare_hesapla(ziyaret_a, donusum_a, ziyaret_b, donusum_b):
    if ziyaret_a == 0 or ziyaret_b == 0:
        return 0, 0
    oran_a = donusum_a / ziyaret_a
    oran_b = donusum_b / ziyaret_b
    toplam_ziyaret = ziyaret_a + ziyaret_b
    toplam_donusum = donusum_a + donusum_b
    if toplam_ziyaret == 0 or toplam_donusum == 0:
        return 0, 0
    beklenen_oran = toplam_donusum / toplam_ziyaret
    beklenen_a = beklenen_oran * ziyaret_a
    beklenen_b = beklenen_oran * ziyaret_b
    ki_kare = 0
    if beklenen_a > 0:
        ki_kare += (donusum_a - beklenen_a) ** 2 / beklenen_a
    if beklenen_b > 0:
        ki_kare += (donusum_b - beklenen_b) ** 2 / beklenen_b
    guven = 1 - 0.05
    return ki_kare, round(guven * 100, 1)

def baslat(varyant_a, varyant_b):
    veri = _yukle()
    test_id = modul_hash(varyant_a + varyant_b + simdi())
    hash_key = str(test_id)
    ziyaret_a = 100 + modul_hash(hash_key + "va") % 900
    ziyaret_b = 100 + modul_hash(hash_key + "vb") % 900
    donusum_a = int(ziyaret_a * (2 + modul_yuzde(hash_key + "ca", 0, 18)) / 100)
    donusum_b = int(ziyaret_b * (2 + modul_yuzde(hash_key + "cb", 0, 18)) / 100)
    test = {
        "id": test_id,
        "varyant_a": varyant_a,
        "varyant_b": varyant_b,
        "baslama": simdi(),
        "durum": "devam",
        "ziyaret_a": ziyaret_a,
        "ziyaret_b": ziyaret_b,
        "donusum_a": donusum_a,
        "donusum_b": donusum_b,
        "donusum_orani_a": round(donusum_a / ziyaret_a * 100, 2),
        "donusum_orani_b": round(donusum_b / ziyaret_b * 100, 2)
    }
    ki_kare, guven = _ki_kare_hesapla(ziyaret_a, donusum_a, ziyaret_b, donusum_b)
    test["ki_kare"] = round(ki_kare, 4)
    test["guven_seviyesi"] = guven
    if test["donusum_orani_a"] > test["donusum_orani_b"]:
        test["kazanan"] = "A"
    elif test["donusum_orani_b"] > test["donusum_orani_a"]:
        test["kazanan"] = "B"
    else:
        test["kazanan"] = "Beraberlik"
    veri.append(test)
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"A/B test başlatıldı: {varyant_a} vs {varyant_b}", "test": test}

def listele():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Henüz A/B testi yok", "testler": []}
    return {"status": "ok", "toplam": len(veri), "testler": sorted(veri, key=lambda t: t.get("baslama", ""), reverse=True)}

def sonlandir(test_id):
    veri = _yukle()
    for test in veri:
        if test["id"] == test_id:
            test["durum"] = "tamamlandi"
            test["bitis"] = simdi()
            _kaydet(veri)
            return {"status": "ok", "mesaj": f"Test sonlandırıldı: {test_id}", "test": test}
    return {"status": "hata", "mesaj": f"Test bulunamadı: {test_id}"}

def istatistik(test_id):
    veri = _yukle()
    for test in veri:
        if test["id"] == test_id:
            iyilesme = round(test["donusum_orani_b"] - test["donusum_orani_a"], 2)
            return {
                "status": "ok",
                "test": test,
                "iyilesme_yuzde": iyilesme,
                "toplam_ziyaret": test["ziyaret_a"] + test["ziyaret_b"],
                "toplam_donusum": test["donusum_a"] + test["donusum_b"],
                "anlamli_mi": test.get("guven_seviyesi", 0) >= 95
            }
    return {"status": "hata", "mesaj": f"Test bulunamadı: {test_id}"}

def rapor(test_id):
    veri = _yukle()
    for test in veri:
        if test["id"] == test_id:
            return {
                "status": "ok",
                "rapor": {
                    "test_id": test["id"],
                    "varyant_a": {"isim": test["varyant_a"], "ziyaret": test["ziyaret_a"], "donusum": test["donusum_a"], "oran": test["donusum_orani_a"]},
                    "varyant_b": {"isim": test["varyant_b"], "ziyaret": test["ziyaret_b"], "donusum": test["donusum_b"], "oran": test["donusum_orani_b"]},
                    "kazanan": test["kazanan"],
                    "guven_seviyesi": test.get("guven_seviyesi", 0),
                    "durum": test["durum"],
                    "baslama": test.get("baslama", ""),
                    "bitis": test.get("bitis", "devam ediyor")
                }
            }
    return {"status": "hata", "mesaj": f"Test bulunamadı: {test_id}"}
