"""
Maps Saldırı Botu — YALNIZCA SİMÜLASYON.

Google Maps yorum gönderimi yasal risk taşır; gerçek API çağrısı yapılmaz.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .modul_base import modul_export_csv, modul_export_json, modul_hash, simdi

SIMULATION_NOTICE = (
    "Bu modül simülasyon amaçlıdır — gerçek Google Maps yorumu göndermez. "
    "Yasal risk nedeniyle canlı yorum API'si devre dışıdır."
)

MAPS_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "maps_data.json"
)


def _yukle() -> dict:
    if not os.path.exists(MAPS_DB_PATH):
        return {"yorumlar": [], "hedefler": [], "simulations": []}
    try:
        with open(MAPS_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("yorumlar", [])
            data.setdefault("hedefler", [])
            data.setdefault("simulations", [])
            return data
    except Exception:
        pass
    return {"yorumlar": [], "hedefler": [], "simulations": []}


def _kaydet(data: dict) -> None:
    os.makedirs(os.path.dirname(MAPS_DB_PATH), exist_ok=True)
    with open(MAPS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def simulate_review(place_name: str, rating: int = 5, comment: str = "") -> dict[str, Any]:
    """Simülasyon — gerçek yorum gönderilmez."""
    if not (place_name or "").strip():
        return {"success": False, "status": "hata", "hata": "place_name gerekli"}

    place = place_name.strip()
    rating = max(1, min(5, int(rating or 5)))
    text = (comment or "").strip() or f"[Simülasyon] {place} için örnek yorum metni"

    h = modul_hash(f"maps_sim_{place}_{simdi()}")
    record = {
        "simulation_id": f"SIM-{h % 1000000:06d}",
        "place_name": place,
        "rating": rating,
        "comment": text[:500],
        "simulation": True,
        "live_review_sent": False,
        "status": "simulation_complete",
        "message": "Simülasyon tamamlandı — gerçek yorum gönderilmedi",
        "created_at": simdi(),
    }

    data = _yukle()
    data.setdefault("simulations", []).append(record)
    data.setdefault("yorumlar", []).append({
        "isletme": place,
        "isim": "Simülasyon",
        "puan": rating,
        "yorum": text,
        "tarih": simdi()[:10],
        "created_at": simdi(),
        "simulation": True,
    })
    _kaydet(data)

    return {
        "success": True,
        "simulation": True,
        **record,
        "warning": SIMULATION_NOTICE,
    }


def yorum_gonder(isletme: str, adet: int = 1, puan: int = 0):
    """Geriye uyumluluk — her istek simulate_review ile simüle edilir."""
    if not isletme:
        return {"status": "hata", "hata": "İşletme adı belirtilmedi"}

    adet = max(1, min(50, int(adet or 1)))
    puan = puan or 4
    results = []
    for i in range(adet):
        res = simulate_review(isletme, rating=puan, comment=f"[Simülasyon #{i + 1}] Örnek yorum")
        results.append(res)

    return {
        "success": True,
        "simulation": True,
        "isletme": isletme,
        "simule_edilen": adet,
        "ortalama_puan": puan,
        "yorumlar": results,
        "warning": SIMULATION_NOTICE,
        "message": "Simülasyon tamamlandı — gerçek yorum gönderilmedi",
    }


def yorum_listele(isletme: str = ""):
    try:
        data = _yukle()
        liste = data.get("yorumlar", [])
        if isletme:
            liste = [y for y in liste if y.get("isletme") == isletme]
        liste.sort(key=lambda y: y.get("created_at", ""), reverse=True)
        return {
            "toplam": len(liste),
            "yorumlar": liste[-50:],
            "simulation_only": True,
            "warning": SIMULATION_NOTICE,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def yorum_istatistik(isletme: str = ""):
    try:
        data = _yukle()
        liste = data.get("yorumlar", [])
        if isletme:
            liste = [y for y in liste if y.get("isletme") == isletme]
        if not liste:
            return {"toplam": 0, "ortalama_puan": 0, "isletme": isletme or "tum", "simulation_only": True}
        puanlar = [y.get("puan", 3) for y in liste]
        return {
            "toplam": len(liste),
            "ortalama_puan": round(sum(puanlar) / len(puanlar), 1),
            "en_dusuk": min(puanlar),
            "en_yuksek": max(puanlar),
            "isletme": isletme or "tum",
            "simulation_only": True,
            "warning": SIMULATION_NOTICE,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def hedef_ekle(isletme: str, adres: str = ""):
    try:
        if not isletme:
            return {"status": "hata", "hata": "İşletme adı gerekli"}
        h = modul_hash(f"hedef_{isletme}_{simdi()}")
        data = _yukle()
        var = any(h.get("isletme") == isletme for h in data.get("hedefler", []))
        if not var:
            data.setdefault("hedefler", []).append({
                "isletme": isletme,
                "adres": adres or f"{isletme} Mah.",
                "puan": 4 + (h % 2),
                "created_at": simdi(),
                "simulation_only": True,
            })
            _kaydet(data)
        return {"durum": "hedef_eklendi", "isletme": isletme, "simulation_only": True, "warning": SIMULATION_NOTICE}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def export(isletme: str, format: str = "csv"):
    try:
        data = _yukle()
        yorumlar = [y for y in data.get("yorumlar", []) if y.get("isletme") == isletme] if isletme else data.get("yorumlar", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(yorumlar), "simulation_only": True}
        elif format == "txt":
            return {
                "format": "txt",
                "icerik": "\n\n".join(f"{y.get('isim', 'Sim')} ★{y.get('puan', 0)}\n{y.get('yorum', '')}" for y in yorumlar),
                "simulation_only": True,
            }
        return {"format": "csv", "icerik": modul_export_csv(yorumlar), "simulation_only": True}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def health() -> dict[str, Any]:
    data = _yukle()
    return {
        "success": True,
        "module": "maps",
        "simulation_only": True,
        "live_reviews": False,
        "simulations_total": len(data.get("simulations") or []),
        "warning": SIMULATION_NOTICE,
    }
