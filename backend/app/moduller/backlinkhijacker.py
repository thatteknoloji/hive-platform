"""
Backlink Hijacker — OpenSEO / DataSEO MCP ile kırık backlink tespiti.

Simülasyon yok: backlink_hunter.get_backlinks + gerçek HTTP doğrulama.
steal_backlink: kırık link outreach fırsatı kaydı (site değiştirmez).
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from .backlink_hunter import get_backlinks
from .modul_base import modul_export_csv, modul_export_json, simdi

logger = logging.getLogger("hive.backlinkhijacker")

HIJACK_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "hijack_results.json"
)
HTTP_TIMEOUT = 12
USER_AGENT = "Mozilla/5.0 (compatible; HIVE-BacklinkHijacker/1.0)"


def _yukle() -> list[dict]:
    if not os.path.exists(HIJACK_DB_PATH):
        return []
    try:
        with open(HIJACK_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _kaydet(data: list[dict]) -> None:
    os.makedirs(os.path.dirname(HIJACK_DB_PATH), exist_ok=True)
    with open(HIJACK_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data[-500:], f, indent=2, ensure_ascii=False)


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    for p in ("https://", "http://", "www."):
        d = d.replace(p, "")
    return d.split("/")[0].split(":")[0]


def _http_check(url: str) -> dict[str, Any]:
    if not (url or "").strip():
        return {"url": url, "reachable": False, "status": 0, "broken": True, "error": "empty_url"}
    try:
        resp = requests.head(
            url.strip(),
            timeout=HTTP_TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code in (405, 501):
            resp = requests.get(
                url.strip(),
                timeout=HTTP_TIMEOUT,
                allow_redirects=True,
                headers={"User-Agent": USER_AGENT},
                stream=True,
            )
            resp.close()
        broken = resp.status_code >= 400 or resp.status_code == 0
        return {
            "url": url,
            "reachable": not broken,
            "status": resp.status_code,
            "broken": broken,
        }
    except requests.RequestException as exc:
        return {"url": url, "reachable": False, "status": 0, "broken": True, "error": str(exc)}


def _extract_hrefs(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r"""href\s*=\s*["']([^"']+)["']""", html or "", re.I)
    out: list[str] = []
    for href in hrefs:
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        out.append(urljoin(base_url, href))
    return out


def find_broken_backlinks(target_domain: str, limit: int = 50) -> dict[str, Any]:
    """OpenSEO/DataSEO backlink listesinden kırık hedef URL'leri tespit et."""
    dom = _normalize_domain(target_domain)
    if not dom:
        return {"status": "hata", "hata": "domain gerekli"}

    bl = get_backlinks(dom, limit=limit)
    if not bl.get("success"):
        return {
            "status": "hata",
            "hata": bl.get("message") or bl.get("error") or "Backlink sağlayıcısı erişilemedi",
            "domain": dom,
            "provider_hint": bl.get("hint"),
        }

    links = bl.get("links") or bl.get("backlinks") or []
    checked_targets: dict[str, dict] = {}
    broken: list[dict] = []

    for ln in links:
        source = (ln.get("source_url") or "").strip()
        target = (ln.get("target_url") or "").strip()
        if not target:
            continue
        if target not in checked_targets:
            checked_targets[target] = _http_check(target)
        tcheck = checked_targets[target]
        if not tcheck.get("broken"):
            continue
        broken.append({
            "source_url": source,
            "target_url": target,
            "broken_target_status": tcheck.get("status"),
            "anchor": ln.get("anchor") or "",
            "domain_from": ln.get("domain_from") or "",
            "rank": ln.get("rank") or 0,
            "dofollow": ln.get("dofollow", True),
            "provider": bl.get("provider") or ln.get("provider"),
        })

    sonuc = {
        "status": "aktif",
        "domain": dom,
        "provider": bl.get("provider"),
        "toplam_backlink": len(links),
        "tespit_edilen_kirik": len(broken),
        "kirilan_linkler": broken[:30],
        "kaynak": "openseo_dataseo_http",
        "olusturma": simdi(),
    }
    db = _yukle()
    db.append(sonuc)
    _kaydet(db)
    return sonuc


def steal_backlink(source_url: str, target_url: str, broken_url: str = "") -> dict[str, Any]:
    """
    Kaynak sayfadaki kırık outbound link için outreach kaydı oluştur.
    Gerçek site içeriğini değiştirmez — broken link building hazırlığı.
    """
    src = (source_url or "").strip()
    tgt = (target_url or "").strip()
    if not src or not tgt:
        return {"status": "hata", "hata": "source_url ve target_url gerekli"}

    try:
        resp = requests.get(src, timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})
    except requests.RequestException as exc:
        return {"status": "hata", "hata": f"Kaynak sayfa alınamadı: {exc}"}

    if resp.status_code >= 400:
        return {"status": "hata", "hata": f"Kaynak sayfa HTTP {resp.status_code}"}

    hrefs = _extract_hrefs(resp.text, src)
    broken_candidates: list[dict] = []
    broken_hint = (broken_url or "").strip()

    for href in hrefs:
        if broken_hint and broken_hint not in href:
            continue
        check = _http_check(href)
        if check.get("broken"):
            broken_candidates.append({"url": href, **check})

    if broken_hint and not broken_candidates:
        hint_check = _http_check(broken_hint)
        if hint_check.get("broken"):
            broken_candidates.append({"url": broken_hint, **hint_check})

    if not broken_candidates:
        return {
            "status": "hata",
            "hata": "Kaynak sayfada doğrulanmış kırık outbound link bulunamadı",
            "source_url": src,
            "hedef_onerisi": tgt,
        }

    primary = broken_candidates[0]
    pitch = (
        f"Merhaba,\n\n"
        f"{src} sayfanızdaki '{primary['url']}' bağlantısı artık çalışmıyor "
        f"(HTTP {primary.get('status')}).\n"
        f"Güncel kaynak olarak şunu önerebilirsiniz: {tgt}\n\n"
        f"Teşekkürler."
    )

    kayit = {
        "id": f"HIJ-{simdi().replace(' ', '').replace(':', '')[:14]}",
        "source_url": src,
        "broken_url": primary["url"],
        "broken_status": primary.get("status"),
        "onerilen_hedef": tgt,
        "outreach_pitch": pitch,
        "durum": "outreach_hazir",
        "olusturma": simdi(),
        "kaynak": "http_dogrulama",
    }
    db = _yukle()
    db.append(kayit)
    _kaydet(db)

    return {
        "status": "aktif",
        "durum": "outreach_hazir",
        "source_url": src,
        "broken_url": primary["url"],
        "onerilen_hedef": tgt,
        "outreach_pitch": pitch,
        "kayit": kayit,
        "kaynak": "gercek_http",
        "not": "Site içeriği değiştirilmedi — outreach metni üretildi",
    }


def cal(domain: str = "") -> dict[str, Any]:
    """Legacy tarama — find_broken_backlinks sarmalayıcısı."""
    if not (domain or "").strip():
        return {"status": "hata", "hata": "domain gerekli", "uyari": "Domain belirtilmemiş"}
    res = find_broken_backlinks(domain)
    if res.get("status") == "hata":
        return res
    kirilan = res.get("kirilan_linkler") or []
    return {
        "domain": res.get("domain"),
        "tespit_edilen_kirik": res.get("tespit_edilen_kirik", 0),
        "calinan_backlink": len(kirilan),
        "ortalama_dr": (
            sum(int(l.get("rank") or 0) for l in kirilan) // len(kirilan) if kirilan else 0
        ),
        "calinan_linkler": [
            {
                "kaynak": l.get("source_url"),
                "tip": "kirilan_backlink",
                "dr": l.get("rank") or 0,
                "anchor": l.get("anchor") or "",
                "durum": "firsat",
                "hedef": l.get("target_url"),
                "broken_status": l.get("broken_target_status"),
            }
            for l in kirilan[:10]
        ],
        "provider": res.get("provider"),
        "kaynak": res.get("kaynak"),
        "olusturma": res.get("olusturma"),
    }


def calinan_listele() -> dict[str, Any]:
    liste = _yukle()
    liste.sort(key=lambda h: h.get("olusturma", ""), reverse=True)
    return {"toplam": len(liste), "sonuclar": liste[-30:]}


def analiz_et() -> dict[str, Any]:
    results = _yukle()
    kirik_toplam = sum(h.get("tespit_edilen_kirik", 0) for h in results if "tespit_edilen_kirik" in h)
    outreach = sum(1 for h in results if h.get("durum") == "outreach_hazir")
    return {
        "toplam_tarama": sum(1 for h in results if "tespit_edilen_kirik" in h),
        "toplam_kirik": kirik_toplam,
        "outreach_hazir": outreach,
        "toplam_kayit": len(results),
    }


def hedef_tara(domain: str) -> dict[str, Any]:
    return cal(domain)


def export(domain: str, format: str = "csv") -> dict[str, Any]:
    sonuc = cal(domain)
    if sonuc.get("status") == "hata":
        return sonuc
    linkler = sonuc.get("calinan_linkler", [])
    if format == "json":
        return {"format": "json", "icerik": modul_export_json(linkler)}
    if format == "txt":
        lines = [
            f"{l.get('kaynak')} DR:{l.get('dr')} - {l.get('anchor')} -> {l.get('hedef')}"
            for l in linkler
        ]
        return {"format": "txt", "icerik": "\n".join(lines)}
    return {"format": "csv", "icerik": modul_export_csv(linkler)}


def health() -> dict[str, Any]:
    from .backlink_hunter import health as hunter_health
    h = hunter_health()
    return {
        "status": "aktif",
        "module": "backlinkhijacker",
        "simulation": False,
        "providers": h.get("providers", ["openseo", "dataseo_mcp"]),
        "openseo_live": h.get("openseo_live"),
        "kayit_sayisi": len(_yukle()),
    }
