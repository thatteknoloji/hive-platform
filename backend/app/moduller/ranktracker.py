"""Rank Tracker — DataForSEO SERP + Google Search Console (SerpAPI kaldırıldı)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from .modul_base import modul_export_csv, modul_export_json, modul_export_txt, simdi

RT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "rank_tracker.json")


def _yukle() -> dict[str, Any]:
    if not os.path.exists(RT_DB_PATH):
        return {"keywords": [], "history": []}
    try:
        with open(RT_DB_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("keywords", [])
            data.setdefault("history", [])
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"keywords": [], "history": []}


def _kaydet(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(RT_DB_PATH), exist_ok=True)
    with open(RT_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _gsc_configured() -> bool:
    from app.moduller.rank_index_watcher import _gsc_oauth_configured

    return _gsc_oauth_configured()


def _dataforseo_configured() -> bool:
    from app.moduller.dataforseo_client import is_configured

    return is_configured()


def health() -> dict[str, Any]:
    gsc = _gsc_configured()
    dfs = _dataforseo_configured()
    veri = _yukle()
    return {
        "success": True,
        "search_console": gsc,
        "dataforseo": dfs,
        "ready": gsc or dfs,
        "providers": [
            {"id": "search_console", "label": "Google Search Console", "active": gsc},
            {"id": "dataforseo", "label": "DataForSEO SERP", "active": dfs},
        ],
        "keyword_count": len(veri.get("keywords") or []),
        "history_count": len(veri.get("history") or []),
        "note": None if (gsc or dfs) else "DATAFORSEO_LOGIN/PASSWORD veya GSC OAuth yapılandırın",
    }


def _gsc_keyword_metrics(keyword: str, days: int = 28) -> dict[str, Any] | None:
    from app.moduller.rank_index_watcher import _gsc_service, _gsc_site_url

    if not _gsc_configured():
        return None
    service, err = _gsc_service()
    if not service:
        return {"error": err or "search_console_error"}

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=max(1, days))
    site_url = _gsc_site_url()
    if not site_url:
        return {"error": "GSC_SITE_URL veya GOOGLE_SEARCH_CONSOLE_SITE_URL eksik"}

    body: dict[str, Any] = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["query", "date"],
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension": "query",
                "operator": "equals",
                "expression": keyword,
            }],
        }],
        "rowLimit": 250,
    }
    try:
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    except Exception as exc:
        return {"error": str(exc)}

    rows = resp.get("rows") or []
    if not rows:
        return {
            "position": None,
            "clicks": 0,
            "impressions": 0,
            "ctr": 0.0,
            "daily": [],
            "source": "search_console",
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    clicks = sum(r.get("clicks", 0) for r in rows)
    impressions = sum(r.get("impressions", 0) for r in rows)
    positions = [r.get("position", 0) for r in rows if r.get("position")]
    avg_position = round(sum(positions) / len(positions), 2) if positions else None
    daily: list[dict[str, Any]] = []
    for r in rows:
        keys = r.get("keys") or []
        day = keys[1] if len(keys) > 1 else ""
        daily.append({
            "tarih": day,
            "pozisyon": round(r.get("position", 0), 2) if r.get("position") else None,
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
        })
    daily.sort(key=lambda x: x.get("tarih") or "")

    return {
        "position": avg_position,
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(clicks / impressions, 4) if impressions else 0.0,
        "daily": daily[-14:],
        "source": "search_console",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
    }


def _dataforseo_rank(keyword: str, domain: str) -> dict[str, Any] | None:
    if not _dataforseo_configured():
        return None
    if not (domain or "").strip():
        return {"error": "domain_gerekli", "message": "DataForSEO sıra kontrolü için domain gerekli"}

    from app.moduller.rank_index_watcher import track_keyword

    res = track_keyword(keyword, domain, save=False)
    if not res.get("success"):
        return {"error": res.get("error", "provider_error"), "message": res.get("message", "")}
    return {
        "position": res.get("position"),
        "first_url": res.get("first_url", ""),
        "serp_snapshot": res.get("serp_snapshot") or [],
        "source": "dataforseo",
        "checked_at": res.get("checked_at"),
    }


def _history_for_keyword(kelime: str, limit: int = 14) -> list[dict[str, Any]]:
    veri = _yukle()
    items = [
        h for h in veri.get("history") or []
        if (h.get("kelime") or "").lower() == kelime.lower()
    ]
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    gecmis = []
    for h in items[:limit]:
        gecmis.append({
            "gun": h.get("timestamp", ""),
            "pozisyon": h.get("pozisyon"),
            "kaynak": h.get("kaynak", ""),
            "tarih": (h.get("timestamp") or "")[:10],
        })
    gecmis.reverse()
    return gecmis


def _compute_trend(gecmis: list[dict[str, Any]]) -> str:
    positions = [g.get("pozisyon") for g in gecmis if g.get("pozisyon") is not None]
    if len(positions) < 2:
        return "sabit"
    cur, prev = positions[-1], positions[-2]
    if cur < prev:
        return "yükseliyor"
    if cur > prev:
        return "düşüyor"
    return "sabit"


def _append_history(kelime: str, pozisyon: int | None, kaynak: str, extra: dict | None = None) -> None:
    veri = _yukle()
    entry = {
        "kelime": kelime,
        "pozisyon": pozisyon,
        "kaynak": kaynak,
        "timestamp": simdi(),
        **(extra or {}),
    }
    veri.setdefault("history", []).append(entry)
    veri["history"] = veri["history"][-5000:]
    for kw in veri.get("keywords") or []:
        if (kw.get("kelime") or "").lower() == kelime.lower():
            kw["pozisyon"] = pozisyon
            kw["son_kontrol"] = entry["timestamp"]
            kw["kaynak"] = kaynak
    _kaydet(veri)


def takip_et(kelime: str, domain: str = "", sehir: str = "") -> dict[str, Any]:
    try:
        kw = (kelime or "").strip()
        if not kw:
            return {"status": "hata", "hata": "Kelime belirtilmedi"}

        gsc_ok = _gsc_configured()
        dfs_ok = _dataforseo_configured()
        if not gsc_ok and not dfs_ok:
            return {
                "status": "hata",
                "hata": "provider_missing",
                "mesaj": "DataForSEO (DATAFORSEO_LOGIN/PASSWORD) veya Google Search Console (OAuth + site URL) yapılandırın",
                "providers": health()["providers"],
            }

        dfs_res = _dataforseo_rank(kw, domain) if dfs_ok else None
        gsc_res = _gsc_keyword_metrics(kw) if gsc_ok else None

        errors: list[str] = []
        if dfs_res and dfs_res.get("error"):
            errors.append(f"DataForSEO: {dfs_res.get('message') or dfs_res['error']}")
        if gsc_res and gsc_res.get("error"):
            errors.append(f"GSC: {gsc_res['error']}")

        live_pos = dfs_res.get("position") if dfs_res and "error" not in dfs_res else None
        gsc_pos = gsc_res.get("position") if gsc_res and "error" not in gsc_res else None
        guncel = live_pos if live_pos is not None else gsc_pos

        sources: list[str] = []
        if live_pos is not None:
            sources.append("dataforseo")
        if gsc_pos is not None:
            sources.append("search_console")
        kaynak = "+".join(sources) if sources else "yok"

        if guncel is None and errors and not sources:
            return {
                "status": "hata",
                "hata": "sorgu_basarisiz",
                "mesaj": "; ".join(errors),
                "kelime": kw,
                "domain": domain or "",
            }

        gecmis_db = _history_for_keyword(kw)
        onceki = gecmis_db[-2].get("pozisyon") if len(gecmis_db) >= 2 else None

        if guncel is not None:
            _append_history(
                kw,
                guncel,
                kaynak,
                {
                    "domain": domain or "",
                    "gsc_position": gsc_pos,
                    "dataforseo_position": live_pos,
                },
            )
            gecmis_db = _history_for_keyword(kw)

        gsc_daily = (gsc_res or {}).get("daily") or []
        if gsc_daily and not gecmis_db:
            gecmis = [
                {"gun": d.get("tarih", ""), "pozisyon": d.get("pozisyon"), "tarih": d.get("tarih", ""), "kaynak": "search_console"}
                for d in gsc_daily
            ]
        else:
            gecmis = gecmis_db

        trend = _compute_trend(gecmis)
        degisim = (onceki - guncel) if onceki is not None and guncel is not None else None

        return {
            "kelime": kw,
            "domain": domain or "",
            "sehir": sehir or "Türkiye",
            "guncel_pozisyon": guncel,
            "onceki_pozisyon": onceki,
            "degisim": degisim,
            "trend": trend,
            "gecmis": gecmis[-14:],
            "kaynak": kaynak,
            "dataforseo": {
                "position": live_pos,
                "first_url": (dfs_res or {}).get("first_url"),
                "serp_snapshot": (dfs_res or {}).get("serp_snapshot") or [],
            } if dfs_ok else None,
            "search_console": {
                "position": gsc_pos,
                "clicks": (gsc_res or {}).get("clicks"),
                "impressions": (gsc_res or {}).get("impressions"),
                "ctr": (gsc_res or {}).get("ctr"),
                "daily": gsc_daily,
            } if gsc_ok and gsc_res and "error" not in gsc_res else (
                {"error": (gsc_res or {}).get("error")} if gsc_ok and gsc_res and gsc_res.get("error") else None
            ),
            "provider_errors": errors or None,
            "uyari": "; ".join(errors) if errors and guncel is not None else None,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def keyword_kaydet(kelime: str, domain: str = ""):
    try:
        if not kelime:
            return {"status": "hata", "hata": "Kelime belirtilmedi"}
        veri = _yukle()
        if any(k["kelime"] == kelime for k in veri["keywords"]):
            return {"durum": "zaten_var", "kelime": kelime}
        veri["keywords"].append({
            "kelime": kelime,
            "domain": domain or "",
            "timestamp": simdi(),
        })
        _kaydet(veri)
        return {"durum": "kaydedildi", "kelime": kelime}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def keyword_sil(kelime: str):
    try:
        veri = _yukle()
        once = len(veri["keywords"])
        veri["keywords"] = [k for k in veri["keywords"] if k["kelime"] != kelime]
        if len(veri["keywords"]) == once:
            return {"durum": "bulunamadi", "kelime": kelime}
        _kaydet(veri)
        return {"durum": "silindi", "kelime": kelime}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def keyword_listele():
    try:
        veri = _yukle()
        keywords = list(veri.get("keywords") or [])
        keywords.sort(key=lambda k: k.get("timestamp", ""), reverse=True)
        return {"toplam": len(keywords), "keywords": keywords[:100]}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def toplu_kontrol(kelimeler: list, domain: str = "", sehir: str = ""):
    try:
        if not kelimeler:
            return {"status": "hata", "hata": "Kelime listesi boş"}
        sonuclar = []
        hatalar = []
        for item in kelimeler:
            if isinstance(item, dict):
                kw = item.get("kelime", "")
                dom = item.get("domain", domain)
                shr = item.get("sehir", sehir)
            else:
                kw = str(item)
                dom = domain
                shr = sehir
            if not kw:
                continue
            sonuc = takip_et(kw, dom, shr)
            if sonuc.get("status") == "hata":
                hatalar.append({"kelime": kw, "hata": sonuc.get("hata"), "mesaj": sonuc.get("mesaj")})
            else:
                sonuclar.append(sonuc)
        return {
            "toplam": len(sonuclar),
            "sonuclar": sonuclar,
            "hatalar": hatalar,
            "providers": health()["providers"],
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def export(kelime: str, format: str = "csv"):
    try:
        sonuc = takip_et(kelime)
        if sonuc.get("status") == "hata":
            return sonuc
        gecmis = sonuc.get("gecmis", [])
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(gecmis)}
        if format == "txt":
            return {"format": "txt", "icerik": modul_export_txt(gecmis)}
        return {"format": "csv", "icerik": modul_export_csv(gecmis)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
