import hashlib
import json
import csv
import io
import random
from datetime import datetime

def modul_hash(seed: str) -> int:
    return int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)

def modul_yuzde(seed: str, min_v: float = 0, max_v: float = 100) -> float:
    return min_v + (modul_hash(seed) % 10000) / 10000 * (max_v - min_v)

def modul_sec(seed: str, secenekler: list):
    return secenekler[modul_hash(seed) % len(secenekler)]

def modul_sec_n(seed: str, secenekler: list, n: int):
    h = modul_hash(seed)
    karisik = list(secenekler)
    random.Random(h).shuffle(karisik)
    return karisik[:min(n, len(karisik))]

def modul_export_json(data: list, fields: list = None) -> str:
    if fields:
        data = [{k: item.get(k) for k in fields} for item in data]
    return json.dumps(data, indent=2, ensure_ascii=False)

def modul_export_csv(data: list, fields: list = None) -> str:
    if not data:
        return ""
    if not fields:
        fields = list(data[0].keys())
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(fields)
    for item in data:
        writer.writerow([item.get(f, "") for f in fields])
    return output.getvalue()

def modul_export_txt(data: list, fields: list = None) -> str:
    if not data:
        return ""
    if not fields:
        fields = list(data[0].keys())
    satirlar = []
    for item in data:
        satirlar.append(" | ".join(f"{f}: {item.get(f, '')}" for f in fields))
    return "\n".join(satirlar)

def modul_hata(e: Exception) -> dict:
    return {"status": "hata", "hata": str(e), "tip": type(e).__name__}

def simdi() -> str:
    return datetime.now().isoformat()

TURKCE_SEHIRLER = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin",
    "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur",
    "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan",
    "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkâri", "Hatay", "Iğdır", "Isparta",
    "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis",
    "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin",
    "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun",
    "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak",
    "Van", "Yalova", "Yozgat", "Zonguldak"
]

TURKCE_ISIMLER = [
    "Ahmet", "Mehmet", "Ali", "Veli", "Osman", "Hasan", "Hüseyin", "İbrahim", "Mustafa", "Murat",
    "Ayşe", "Fatma", "Zeynep", "Elif", "Merve", "Büşra", "Esra", "Sema", "Hatice", "Emine"
]
