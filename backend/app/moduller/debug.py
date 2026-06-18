import os, json, time, importlib
from datetime import datetime
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "debug.json"

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

def _modul_import(modul_id):
    try:
        return importlib.import_module(f".{modul_id}", "app.moduller")
    except:
        return None

def modul_test(modul_id):
    basla = time.time()
    modul = _modul_import(modul_id)
    if not modul:
        return {"status": "hata", "mesaj": f"{modul_id} modulu bulunamadi"}
    testable = [f for f in dir(modul) if callable(getattr(modul, f)) and not f.startswith("_")]
    debug = _yukle()
    kayit = {
        "id": f"test_{modul_hash(str(datetime.now().timestamp()))}",
        "modul_id": modul_id,
        "tip": "modul_test",
        "tarih": simdi(),
        "fonksiyonlar": testable,
        "sure_ms": round((time.time() - basla) * 1000, 2),
        "durum": "basarili"
    }
    debug.append(kayit)
    _kaydet(debug)
    return {"status": "ok", "modul_id": modul_id, "testable_fonksiyonlar": testable, "sure_ms": kayit["sure_ms"]}

def hata_ayikla(modul_id, parametreler=None):
    modul = _modul_import(modul_id)
    if not modul:
        return {"status": "hata", "mesaj": f"{modul_id} modulu bulunamadi"}
    sonuc = {}
    hatalar = []
    for fn, args in (parametreler or {}).items():
        func = getattr(modul, fn, None)
        if not func:
            hatalar.append({"fonksiyon": fn, "hata": "Fonksiyon bulunamadi"})
            continue
        try:
            if isinstance(args, dict):
                res = func(**args)
            elif isinstance(args, list):
                res = func(*args)
            else:
                res = func(args) if args else func()
            sonuc[fn] = res
        except Exception as e:
            hatalar.append({"fonksiyon": fn, "hata": str(e)})
    debug = _yukle()
    kayit = {
        "id": f"hata_{modul_hash(str(datetime.now().timestamp()))}",
        "modul_id": modul_id,
        "tip": "hata_ayiklama",
        "tarih": simdi(),
        "parametreler": parametreler,
        "sonuc_sayisi": len(sonuc),
        "hata_sayisi": len(hatalar)
    }
    debug.append(kayit)
    _kaydet(debug)
    return {"status": "ok" if not hatalar else "kismi", "sonuc": sonuc, "hatalar": hatalar}

def performans(modul_id):
    modul = _modul_import(modul_id)
    if not modul:
        return {"status": "hata", "mesaj": f"{modul_id} modulu bulunamadi"}
    fonksiyonlar = [f for f in dir(modul) if callable(getattr(modul, f)) and not f.startswith("_")]
    olcumler = []
    for fn in fonksiyonlar[:10]:
        func = getattr(modul, fn)
        basla = time.time()
        try:
            if fn in ("listele",):
                func()
            elif fn in ("istatistik", "ayarlar"):
                func()
            else:
                func("test")
            sure = round((time.time() - basla) * 1000, 2)
            olcumler.append({"fonksiyon": fn, "sure_ms": sure})
        except:
            olcumler.append({"fonksiyon": fn, "sure_ms": None, "hata": "calistirilamadi"})
    debug = _yukle()
    kayit = {
        "id": f"perf_{modul_hash(str(datetime.now().timestamp()))}",
        "modul_id": modul_id,
        "tip": "performans",
        "tarih": simdi(),
        "fonksiyon_sayisi": len(fonksiyonlar),
        "olcumler": olcumler
    }
    debug.append(kayit)
    _kaydet(debug)
    return {"status": "ok", "modul_id": modul_id, "olcumler": olcumler, "ortalama_ms": round(sum(o["sure_ms"] for o in olcumler if o.get("sure_ms")) / max(len([o for o in olcumler if o.get("sure_ms")]), 1), 2)}

def log_incele(modul_id, satir=50):
    dosya = os.path.join(DATA_DIR, f"{modul_id}.json")
    if not os.path.exists(dosya):
        return {"status": "hata", "mesaj": f"{modul_id} icin veri dosyasi bulunamadi"}
    try:
        with open(dosya) as f:
            veri = json.load(f)
    except:
        return {"status": "hata", "mesaj": "Dosya okunamadi"}
    if isinstance(veri, list):
        goruntulenen = veri[-satir:]
    elif isinstance(veri, dict):
        anahtarlar = list(veri.keys())[-satir:]
        goruntulenen = {k: veri[k] for k in anahtarlar}
    else:
        goruntulenen = str(veri)[:500]
    debug = _yukle()
    kayit = {
        "id": f"incele_{modul_hash(str(datetime.now().timestamp()))}",
        "modul_id": modul_id,
        "tip": "log_incele",
        "tarih": simdi(),
        "satir": satir,
        "toplam_kayit": len(veri) if isinstance(veri, (list, dict)) else 1
    }
    debug.append(kayit)
    _kaydet(debug)
    return {"status": "ok", "modul_id": modul_id, "toplam_kayit": len(veri) if isinstance(veri, (list, dict)) else 1, "goruntulenen": goruntulenen}

def sema_dogrula(modul_id):
    modul = _modul_import(modul_id)
    if not modul:
        return {"status": "hata", "mesaj": f"{modul_id} modulu bulunamadi"}
    dosya = os.path.join(DATA_DIR, f"{modul_id}.json")
    if not os.path.exists(dosya):
        return {"status": "hata", "mesaj": "Veri dosyasi bulunamadi"}
    try:
        with open(dosya) as f:
            veri = json.load(f)
    except:
        return {"status": "hata", "mesaj": "Dosya okunamadi (JSON gecersiz)"}
    uyarilar = []
    if isinstance(veri, list):
        if len(veri) == 0:
            uyarilar.append("Veri dosyasi bos liste")
        for i, item in enumerate(veri[:100]):
            if not isinstance(item, dict):
                uyarilar.append(f"Index {i}: dict degil ({type(item).__name__})")
    elif isinstance(veri, dict):
        if not veri:
            uyarilar.append("Veri dosyasi bos sozluk")
    else:
        uyarilar.append(f"Beklenmeyen veri tipi: {type(veri).__name__}")
    debug = _yukle()
    kayit = {
        "id": f"sema_{modul_hash(str(datetime.now().timestamp()))}",
        "modul_id": modul_id,
        "tip": "sema_dogrulama",
        "tarih": simdi(),
        "veri_tipi": type(veri).__name__,
        "kayit_sayisi": len(veri) if isinstance(veri, (list, dict)) else 1,
        "uyari_sayisi": len(uyarilar)
    }
    debug.append(kayit)
    _kaydet(debug)
    return {"status": "ok" if not uyarilar else "uyari", "veri_tipi": type(veri).__name__, "kayit_sayisi": len(veri) if isinstance(veri, (list, dict)) else 1, "uyarilar": uyarilar}
