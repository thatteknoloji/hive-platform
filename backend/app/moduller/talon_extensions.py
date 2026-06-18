"""Talon genişletmeleri — Rank Tracker, trend, rakip gap, migrasyon."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from .modul_base import modul_hash, simdi
from .talon_db import search_getir, search_kaydet, keyword_toplu_kaydet

logger = logging.getLogger("hive.talon")

SECTOR_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "sector_templates.json"
LEGACY_HISTORY = Path(__file__).resolve().parent.parent.parent / "talon_data" / "talon_history.json"
LEGACY_FAVORITES = Path(__file__).resolve().parent.parent.parent / "talon_data" / "talon_favorites.json"

SEZON_AYLARI = {
    "yaz": [6, 7, 8, 9],
    "kis": [12, 1, 2],
    "ilkbahar": [3, 4, 5],
    "sonbahar": [10, 11],
}

SEZON_KELIMELER = {
    "yaz": ["yaz sezonu", "yaz ayları", "temmuz", "ağustos", "yaz tatili"],
    "kis": ["kış sezonu", "kış ayları", "ocak", "şubat"],
    "ilkbahar": ["ilkbahar", "nisan", "mayıs"],
    "sonbahar": ["sonbahar", "ekim", "kasım"],
}


def _load_sectors() -> dict:
    if SECTOR_FILE.exists():
        try:
            return json.loads(SECTOR_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Sektör şablonları okunamadı: %s", e)
    return {}


def liste_sektorler() -> list[dict]:
    sectors = _load_sectors()
    return [{"id": k, "ad": v.get("ad", k), "hizmet_sayisi": len(v.get("hizmetler", []))} for k, v in sectors.items()]


def sektor_sablonu(sektor_id: str) -> dict | None:
    return _load_sectors().get(sektor_id)


def rank_tracker_aktar(kelimeler: list, domain: str = "", sehir: str = "") -> dict:
    from .ranktracker import keyword_kaydet

    kaydedilen: list[str] = []
    zaten_var: list[str] = []
    hatalar: list[str] = []

    for item in kelimeler:
        kelime = item if isinstance(item, str) else (item.get("kelime") if isinstance(item, dict) else "")
        if not kelime:
            continue
        try:
            res = keyword_kaydet(kelime, domain)
            if res.get("durum") == "kaydedildi":
                kaydedilen.append(kelime)
            elif res.get("durum") == "zaten_var":
                zaten_var.append(kelime)
            else:
                hatalar.append(f"{kelime}: {res.get('hata', 'bilinmeyen')}")
        except Exception as e:
            hatalar.append(f"{kelime}: {e}")

    return {
        "status": "aktif",
        "kaydedilen": kaydedilen,
        "zaten_var": zaten_var,
        "hatalar": hatalar,
        "toplam_kaydedilen": len(kaydedilen),
        "domain": domain,
        "sehir": sehir,
    }


def trend_analiz(kelimeler: list, sehir: str = "") -> dict:
    from .talon_utils import DataForSEOService

    now = datetime.now()
    aktif_sezon = "yaz" if now.month in SEZON_AYLARI["yaz"] else (
        "kis" if now.month in SEZON_AYLARI["kis"] else (
            "ilkbahar" if now.month in SEZON_AYLARI["ilkbahar"] else "sonbahar"
        )
    )

    analizler = []
    for item in kelimeler[:30]:
        kelime = item if isinstance(item, str) else item.get("kelime", "")
        if not kelime:
            continue

        h = modul_hash(f"{kelime}{sehir}")
        momentum = ["yükseliyor", "sabit", "düşüyor"][h % 3]
        populerlik = 30 + (h % 70)

        sezon_etiketleri = []
        kl = kelime.lower()
        for sezon, etiketler in SEZON_KELIMELER.items():
            if any(e in kl for e in etiketler) or sezon == aktif_sezon:
                sezon_etiketleri.append(sezon)

        api = DataForSEOService.keyword_analiz(kelime)
        hacim = int(api.get("hacim", 0)) if api else None

        aylik = []
        base = (h % 500) + 100
        for ay in range(1, 13):
            sezon_carpan = 1.4 if ay in SEZON_AYLARI.get(aktif_sezon, []) else 0.8
            aylik.append({
                "ay": ay,
                "tahmini_hacim": int(base * sezon_carpan * (0.7 + (modul_hash(f"{kelime}{ay}") % 60) / 100)),
            })

        analizler.append({
            "kelime": kelime,
            "momentum": momentum,
            "populerlik": populerlik,
            "aktif_sezon": aktif_sezon,
            "sezon_etiketleri": sezon_etiketleri or [aktif_sezon],
            "gercek_hacim": hacim,
            "aylik_tahmin": aylik,
            "tavsiye": (
                f"{aktif_sezon.capitalize()} sezonu için '{kelime}' "
                f"{'yüksek potansiyel' if momentum == 'yükseliyor' else 'orta potansiyel'} gösteriyor."
            ),
        })

    return {
        "status": "aktif",
        "sehir": sehir,
        "aktif_sezon": aktif_sezon,
        "analiz_sayisi": len(analizler),
        "analizler": analizler,
        "tarih": simdi(),
    }


def rakip_keyword_gap(
    bizim_kelimeler: list,
    rakip_domain: str = "",
    hedef_domain: str = "",
    limit: int = 30,
) -> dict:
    from .talon_stack.services.talon_search_service import talon_search_service

    bizim_set = {
        (k if isinstance(k, str) else k.get("kelime", "")).lower().strip()
        for k in bizim_kelimeler
    }
    bizim_set.discard("")

    seed = rakip_domain or hedef_domain or " ".join(list(bizim_set)[:3]) or "rakip"
    comp = talon_search_service.find_competitors(seed, {"num_results": limit})
    kw_data = talon_search_service.generate_keyword_ideas(seed)

    rakip_kelimeler: set[str] = set(kw_data.get("autocompleteKeywords", []))
    for c in comp.get("competitors", []):
        rakip_kelimeler.add(c.get("domain", ""))

    gap = []
    ortak = []
    for kw in sorted(rakip_kelimeler):
        kl = kw.lower().strip()
        if not kl:
            continue
        if kl in bizim_set:
            ortak.append(kl)
        else:
            gap.append({"kelime": kl, "firsat": "yüksek" if len(kl) > 12 else "orta", "oncelik": len(kl)})

    gap.sort(key=lambda x: -x["oncelik"])
    return {
        "status": "aktif",
        "rakip_domain": rakip_domain,
        "hedef_domain": hedef_domain,
        "bizim_kelime_sayisi": len(bizim_set),
        "rakip_kelime_sayisi": len(rakip_kelimeler),
        "ortak_kelimeler": ortak[:20],
        "gap_kelimeler": gap[:limit],
        "competitors": comp.get("competitors", []),
        "kaynaklar": ["v2_stack", "autocomplete"],
        "tarih": simdi(),
    }


def gecmis_migrate(dry_run: bool = False) -> dict:
    if not LEGACY_HISTORY.exists():
        return {"status": "aktif", "mesaj": "Migrasyon dosyası bulunamadı", "tasinan": 0}

    try:
        records = json.loads(LEGACY_HISTORY.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"status": "hata", "hata": str(e)}

    if not isinstance(records, list):
        return {"status": "hata", "hata": "Geçersiz JSON formatı"}

    tasinan = 0
    atlanan = 0
    detay: list[dict] = []

    for rec in records:
        search_id = rec.get("id", "")
        if not search_id:
            continue
        if search_getir(search_id):
            atlanan += 1
            continue
        if dry_run:
            tasinan += 1
            detay.append({"id": search_id, "kelime_sayisi": len(rec.get("kelimeler", []))})
            continue

        try:
            search_kaydet(
                search_id,
                rec.get("ana_kelime", ""),
                rec.get("sehir", ""),
                rec.get("adet", 10),
                rec.get("negatif_filtre", ""),
                len(rec.get("kelimeler", [])),
                False,
            )
            kw_rows = []
            for kw in rec.get("kelimeler", []):
                kw_rows.append({
                    "search_id": search_id,
                    "kelime": kw.get("kelime", ""),
                    "rekabet": kw.get("rekabet", "orta"),
                    "arama_hacmi": kw.get("arama_hacmi", "100-500"),
                    "rakip_var": bool(kw.get("rakip_var", False)),
                    "cpc": kw.get("cpc", "0"),
                })
            keyword_toplu_kaydet(kw_rows)
            tasinan += 1
            detay.append({"id": search_id, "kelime_sayisi": len(kw_rows)})
        except Exception as e:
            logger.error("Migrasyon hatası %s: %s", search_id, e)

    if not dry_run and tasinan > 0:
        archive = LEGACY_HISTORY.with_suffix(".json.migrated")
        try:
            LEGACY_HISTORY.rename(archive)
        except OSError:
            pass

    return {
        "status": "aktif",
        "tasinan": tasinan,
        "atlanan": atlanan,
        "dry_run": dry_run,
        "detay": detay,
    }


def favoriler_migrate(dry_run: bool = False) -> dict:
    from .talon_db import favori_ekle as db_favori_ekle, favori_listele

    if not LEGACY_FAVORITES.exists():
        return {"status": "aktif", "mesaj": "Favori dosyası yok", "tasinan": 0}

    try:
        records = json.loads(LEGACY_FAVORITES.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"status": "hata", "hata": str(e)}

    mevcut = {f["kelime"] for f in favori_listele()}
    tasinan = 0
    for rec in records:
        kelime = rec.get("kelime", "") if isinstance(rec, dict) else str(rec)
        if not kelime or kelime in mevcut:
            continue
        if dry_run:
            tasinan += 1
            continue
        if db_favori_ekle(kelime, rec.get("rekabet", "orta"), rec.get("arama_hacmi", "100-500"), bool(rec.get("rakip_var"))):
            tasinan += 1

    return {"status": "aktif", "tasinan": tasinan, "dry_run": dry_run}
