"""
Expired Domain Avcısı / Domain Intelligence Engine V2

Katman 1: Keyword → availability, bulk check, save, export
Katman 2: Expiry Watcher (WHOIS / RDAP — sahte veri yok)
Katman 3: Authority Discovery (Wayback CDX)
Katman 4: Domain Score (0–100, gerçek sinyallerden)
Katman 5: HIVE read-only entegrasyon + brain events
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

import requests

from .modul_base import modul_export_csv, modul_export_json, modul_hash, modul_sec, simdi

logger = logging.getLogger("hive.expireddomain")

MCP_DOMAIN_TIMEOUT = int(os.environ.get("MCP_DOMAIN_TIMEOUT", "25"))
RDAP_TIMEOUT = int(os.environ.get("RDAP_TIMEOUT", "15"))
WAYBACK_TIMEOUT = int(os.environ.get("WAYBACK_TIMEOUT", "20"))
TLDS = [".com", ".net", ".org", ".com.tr", ".info", ".io", ".co", ".biz"]
DOMAIN_ON_EKLERI = ["get", "best", "top", "my", "go", "the", "we", "all", "pro", "turbo"]
DOMAIN_SON_EKLERI = ["app", "hub", "pro", "zone", "online", "site", "world", "lab", "box", "center"]

EXP_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "expired_domains.json"
)

EXPIRY_STATUSES = frozenset({
    "active", "expiring_90", "expiring_60", "expiring_30", "expired", "provider_missing",
})

BRAIN_EVENTS = (
    "domain_discovered",
    "domain_expiring",
    "domain_scored",
    "authority_candidate_found",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    for p in ("https://", "http://", "www."):
        d = d.replace(p, "")
    return d.split("/")[0].split(":")[0]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    raw = value.strip().replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
    ):
        try:
            dt = datetime.strptime(raw[:26] if "T" in fmt else raw[:10], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _days_until(expires_at: datetime | None) -> int | None:
    if not expires_at:
        return None
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return (expires_at.date() - now.date()).days


def _expiry_status_from_days(days: int | None) -> str:
    if days is None:
        return "provider_missing"
    if days <= 0:
        return "expired"
    if days <= 30:
        return "expiring_30"
    if days <= 60:
        return "expiring_60"
    if days <= 90:
        return "expiring_90"
    return "active"


def _yukle() -> list[dict]:
    if not os.path.exists(EXP_DB_PATH):
        return []
    try:
        with open(EXP_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _kaydet(data: list[dict]) -> None:
    os.makedirs(os.path.dirname(EXP_DB_PATH), exist_ok=True)
    with open(EXP_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _find_entry(domains: list[dict], domain: str) -> dict | None:
    dom = _normalize_domain(domain)
    for d in domains:
        if _normalize_domain(d.get("domain", "")) == dom:
            return d
    return None


def _emit_brain_event(event_type: str, domain: str, *, metadata: dict | None = None, result: dict | None = None) -> None:
    if event_type not in BRAIN_EVENTS:
        return
    try:
        from app.moduller.hive_brain_engine import hive_brain
        hive_brain.record_event(
            event_type,
            "expireddomain",
            domain=domain,
            status="ok",
            metadata=metadata or {},
            result=result or {},
        )
    except Exception as exc:
        logger.debug("brain event skip %s: %s", event_type, exc)


# ── Katman 1: Availability ────────────────────────────────────────────────────

def _mcp_check_domain_raw(domain: str) -> dict[str, Any] | None:
    if not shutil.which("npx"):
        return {"success": False, "error": "npx_not_found", "domain": domain}
    dom = _normalize_domain(domain)
    if not dom or "." not in dom:
        return {"success": False, "error": "invalid_domain", "domain": domain}
    cmd = ["npx", "-y", "agent-domain-service-mcp", "check_domain", dom]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=MCP_DOMAIN_TIMEOUT)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()[:300]
            return {"success": False, "error": err or "mcp_failed", "domain": dom, "provider": "agent-domain-service-mcp"}
        out = (proc.stdout or "").strip()
        if not out:
            return {"success": False, "error": "empty_response", "domain": dom, "provider": "agent-domain-service-mcp"}
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {"domain": dom, "raw": out}
        data.setdefault("provider", "agent-domain-service-mcp")
        data["success"] = True
        data["domain"] = dom
        avail = data.get("available")
        if avail is None:
            avail = data.get("is_available")
        if avail is None and "status" in data:
            avail = str(data["status"]).lower() in ("available", "free", "unregistered")
        if avail is not None:
            data["available"] = bool(avail)
        return data
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "mcp_timeout", "domain": dom, "provider": "agent-domain-service-mcp"}
    except (FileNotFoundError, OSError) as exc:
        return {"success": False, "error": str(exc), "domain": dom, "provider": "agent-domain-service-mcp"}


def check_domain(domain: str) -> dict[str, Any]:
    result = _mcp_check_domain_raw(domain)
    if not result:
        return {"success": False, "error": "mcp_unavailable", "domain": _normalize_domain(domain)}
    if result.get("success"):
        return {
            "success": True,
            "domain": result.get("domain", _normalize_domain(domain)),
            "available": bool(result.get("available", False)),
            "provider": "agent-domain-service-mcp",
            "details": result,
        }
    return result


def check_bulk_domains(domains: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for dom in (domains or [])[:50]:
        out.append(check_domain(dom))
    return out


def _aday_domainler_uret(kelime: str, adet: int) -> list[str]:
    kelime = (kelime or "").strip().lower().replace(" ", "")
    if not kelime:
        return []
    adet = max(1, min(50, adet))
    h = modul_hash(f"expired_{kelime}_{simdi()}")
    adaylar: list[str] = []
    seen: set[str] = set()
    for i in range(adet * 3):
        if len(adaylar) >= adet:
            break
        prefix = modul_sec(f"on_ek_{kelime}_{i}", DOMAIN_ON_EKLERI)
        suffix = modul_sec(f"son_ek_{kelime}_{i}", DOMAIN_SON_EKLERI)
        tld = TLDS[(h + i) % len(TLDS)]
        pattern = i % 4
        if pattern == 0:
            dom = f"{prefix}{kelime}{tld}"
        elif pattern == 1:
            dom = f"{kelime}{suffix}{tld}"
        elif pattern == 2:
            dom = f"{prefix}-{kelime}-{suffix}{tld}"
        else:
            dom = f"{kelime}{tld}"
        if dom not in seen:
            seen.add(dom)
            adaylar.append(dom)
    return adaylar[:50]


def domain_bul(kelime: str = "", adet: int = 10) -> dict[str, Any]:
    try:
        if not kelime:
            return {"status": "hata", "hata": "Kelime belirtilmedi"}
        if not shutil.which("npx"):
            return {"status": "hata", "hata": "npx bulunamadı — agent-domain-service-mcp için Node/npx gerekli"}

        adet = max(1, min(50, adet))
        adaylar = _aday_domainler_uret(kelime, adet)
        checks = check_bulk_domains(adaylar)

        domainler = []
        for chk in checks:
            if not chk.get("success"):
                continue
            dom = chk.get("domain", "")
            avail = chk.get("available", False)
            entry = {
                "domain": dom,
                "musait": avail,
                "kaynak": "agent-domain-service-mcp",
                "durum": "müsait" if avail else "kayıtlı",
            }
            domainler.append(entry)
            if avail:
                _emit_brain_event("domain_discovered", dom, metadata={"keyword": kelime, "source": "keyword_search"})

        musait = [d for d in domainler if d.get("musait")]

        return {
            "kelime": kelime,
            "bulunan": len(musait),
            "kontrol_edilen": len(checks),
            "domainler": musait[:20] if musait else domainler[:20],
            "kaynak": "agent-domain-service-mcp",
            "provider": "agent-domain-service-mcp",
            "tavsiye": (
                f"En iyi müsait aday: {musait[0]['domain']}" if musait
                else f"{len([d for d in domainler if not d.get('musait')])} domain kayıtlı — farklı keyword deneyin"
            ),
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def domain_kaydet(domain: str, dr: int = 0, keyword: str = "") -> dict[str, Any]:
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain belirtilmedi"}
        dom = _normalize_domain(domain)
        domains = _yukle()
        entry = _find_entry(domains, dom)
        if not entry:
            chk = check_domain(dom)
            expiry = check_expiry(dom)
            entry = {
                "domain": dom,
                "dr": dr,
                "kayit_tarihi": simdi(),
                "durum": "izleniyor",
                "musait": chk.get("available"),
                "provider": chk.get("provider", "agent-domain-service-mcp"),
                "keyword": keyword or "",
                "expiry": expiry,
            }
            domains.append(entry)
            _kaydet(domains)
            _emit_brain_event("domain_discovered", dom, metadata={"watchlist": True})
            if expiry.get("status") in ("expiring_90", "expiring_60", "expiring_30", "expired"):
                _emit_brain_event("domain_expiring", dom, result=expiry)
        return {"durum": "kaydedildi", "domain": dom, "expiry": entry.get("expiry")}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def domain_listele() -> dict[str, Any]:
    try:
        liste = _yukle()
        liste.sort(key=lambda d: d.get("kayit_tarihi", ""), reverse=True)
        return {"toplam": len(liste), "domainler": liste}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def domain_sil(domain: str) -> dict[str, Any]:
    try:
        dom = _normalize_domain(domain)
        domains = _yukle()
        filtered = [d for d in domains if _normalize_domain(d.get("domain", "")) != dom]
        if len(filtered) == len(domains):
            return {"status": "hata", "hata": "Domain bulunamadı"}
        _kaydet(filtered)
        return {"durum": "silindi", "domain": dom}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def export(kelime: str, format: str = "csv") -> dict[str, Any]:
    try:
        sonuc = domain_bul(kelime, 20)
        if sonuc.get("status") == "hata":
            return sonuc
        domainler = sonuc.get("domainler", [])
        fields = ["domain", "musait", "durum", "kaynak"]
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(domainler, fields)}
        elif format == "txt":
            return {
                "format": "txt",
                "icerik": "\n".join(
                    f"{d['domain']} - {d.get('durum', '')} ({d.get('kaynak', '')})"
                    for d in domainler
                ),
            }
        return {"format": "csv", "icerik": modul_export_csv(domainler, fields)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


# ── Katman 2: Expiry Watcher ──────────────────────────────────────────────────

_WHOIS_EXPIRY_PATTERNS = [
    re.compile(r"registrar registration expiration date:\s*(.+)", re.I),
    re.compile(r"registry expiry date:\s*(.+)", re.I),
    re.compile(r"expir(?:y|ation)\s*date:\s*(.+)", re.I),
    re.compile(r"paid-till:\s*(.+)", re.I),
    re.compile(r"renewal date:\s*(.+)", re.I),
]


def _whois_expiry(domain: str) -> dict[str, Any]:
    dom = _normalize_domain(domain)
    if not shutil.which("whois"):
        return {"success": False, "provider": "whois", "error": "whois_not_installed"}
    try:
        proc = subprocess.run(["whois", dom], capture_output=True, text=True, timeout=15)
        text = (proc.stdout or "") + (proc.stderr or "")
        for pat in _WHOIS_EXPIRY_PATTERNS:
            m = pat.search(text)
            if m:
                expires_at = _parse_date(m.group(1).strip())
                if expires_at:
                    days = _days_until(expires_at)
                    return {
                        "success": True,
                        "provider": "whois",
                        "expires_at": expires_at.strftime("%Y-%m-%d"),
                        "days_remaining": days,
                        "status": _expiry_status_from_days(days),
                    }
        return {"success": False, "provider": "whois", "error": "expiry_not_found"}
    except subprocess.TimeoutExpired:
        return {"success": False, "provider": "whois", "error": "whois_timeout"}
    except Exception as exc:
        return {"success": False, "provider": "whois", "error": str(exc)}


def _rdap_expiry(domain: str) -> dict[str, Any]:
    dom = _normalize_domain(domain)
    try:
        r = requests.get(
            f"https://rdap.org/domain/{dom}",
            timeout=RDAP_TIMEOUT,
            headers={"Accept": "application/rdap+json"},
        )
        if r.status_code == 404:
            return {"success": False, "provider": "rdap", "error": "domain_not_found"}
        if r.status_code != 200:
            return {"success": False, "provider": "rdap", "error": f"http_{r.status_code}"}
        data = r.json()
        for ev in data.get("events") or []:
            if (ev.get("eventAction") or "").lower() == "expiration":
                expires_at = _parse_date(ev.get("eventDate", ""))
                if expires_at:
                    days = _days_until(expires_at)
                    return {
                        "success": True,
                        "provider": "rdap",
                        "expires_at": expires_at.strftime("%Y-%m-%d"),
                        "days_remaining": days,
                        "status": _expiry_status_from_days(days),
                    }
        return {"success": False, "provider": "rdap", "error": "expiry_not_found"}
    except requests.RequestException as exc:
        return {"success": False, "provider": "rdap", "error": str(exc)}


def check_expiry(domain: str) -> dict[str, Any]:
    """WHOIS → RDAP zinciri. Provider yoksa provider_missing — sahte tarih üretilmez."""
    dom = _normalize_domain(domain)
    last_checked = _now_iso()
    whois = _whois_expiry(dom)
    if whois.get("success"):
        return {
            "domain": dom,
            "last_checked": last_checked,
            "expires_at": whois.get("expires_at"),
            "days_remaining": whois.get("days_remaining"),
            "status": whois.get("status", "active"),
            "provider": whois.get("provider", "whois"),
        }
    rdap = _rdap_expiry(dom)
    if rdap.get("success"):
        return {
            "domain": dom,
            "last_checked": last_checked,
            "expires_at": rdap.get("expires_at"),
            "days_remaining": rdap.get("days_remaining"),
            "status": rdap.get("status", "active"),
            "provider": rdap.get("provider", "rdap"),
        }
    has_whois = bool(shutil.which("whois"))
    return {
        "domain": dom,
        "last_checked": last_checked,
        "expires_at": None,
        "days_remaining": None,
        "status": "provider_missing",
        "provider": "whois" if not has_whois else "rdap",
        "error": rdap.get("error") or whois.get("error"),
    }


def refresh_expiry_watch(domain: str | None = None) -> dict[str, Any]:
    """Watchlist expiry güncelle — tek veya tümü."""
    domains = _yukle()
    targets = domains
    if domain:
        dom = _normalize_domain(domain)
        targets = [d for d in domains if _normalize_domain(d.get("domain", "")) == dom]
        if not targets:
            return {"status": "hata", "hata": "Domain watchlist'te yok"}

    updated = []
    for entry in targets:
        dom = _normalize_domain(entry.get("domain", ""))
        expiry = check_expiry(dom)
        entry["expiry"] = expiry
        updated.append(expiry)
        if expiry.get("status") in ("expiring_90", "expiring_60", "expiring_30", "expired"):
            _emit_brain_event("domain_expiring", dom, result=expiry)

    _kaydet(domains)
    return {"success": True, "updated": len(updated), "expiry_records": updated}


def list_expiring(within_days: int = 90) -> dict[str, Any]:
    """Yakında süresi dolacak domainler."""
    within_days = max(1, min(365, within_days))
    domains = _yukle()
    expiring = []
    for entry in domains:
        exp = entry.get("expiry") or {}
        days = exp.get("days_remaining")
        status = exp.get("status", "")
        if status in ("expiring_90", "expiring_60", "expiring_30", "expired"):
            expiring.append({**entry, "expiry": exp})
        elif days is not None and days <= within_days:
            expiring.append({**entry, "expiry": exp})
    expiring.sort(key=lambda x: (x.get("expiry") or {}).get("days_remaining") if (x.get("expiry") or {}).get("days_remaining") is not None else 9999)
    return {"success": True, "within_days": within_days, "toplam": len(expiring), "domainler": expiring}


# ── Katman 3: Authority Discovery ─────────────────────────────────────────────

_CATEGORY_KEYWORDS = {
    "ecommerce": ("shop", "store", "buy", "cart", "market"),
    "blog": ("blog", "news", "post", "article", "mag"),
    "tech": ("tech", "dev", "app", "software", "cloud"),
    "local": ("local", "city", "tur", "istanbul", "ankara"),
    "brand": ("brand", "corp", "inc", "group"),
}


def _infer_category_from_urls(urls: list[str]) -> str:
    if not urls:
        return "unknown"
    text = " ".join(urls[:20]).lower()
    scores: dict[str, int] = {}
    for cat, kws in _CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for k in kws if k in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def _brand_signals(domain: str, snapshots: int, age_years: float | None) -> dict[str, Any]:
    dom = _normalize_domain(domain)
    label = dom.split(".")[0]
    signals: list[str] = []
    if len(label) <= 12 and label.isalpha():
        signals.append("short_alpha_label")
    if "-" not in label and not any(c.isdigit() for c in label):
        signals.append("clean_brand_pattern")
    if snapshots >= 50:
        signals.append("strong_archive_presence")
    if age_years and age_years >= 5:
        signals.append("established_age")
    if not signals:
        return {"status": "unknown", "signals": []}
    return {"status": "detected", "signals": signals}


def discover_authority(domain: str) -> dict[str, Any]:
    """Wayback CDX — archive snapshots. Bulunamazsa unknown."""
    dom = _normalize_domain(domain)
    try:
        r = requests.get(
            "https://web.archive.org/cdx/search/cdx",
            params={
                "url": dom,
                "output": "json",
                "fl": "timestamp,original,statuscode,mime",
                "limit": 500,
            },
            timeout=WAYBACK_TIMEOUT,
        )
        if r.status_code != 200:
            return _authority_unknown(dom, f"wayback_http_{r.status_code}")
        rows = r.json()
        if not rows or len(rows) < 2:
            return _authority_unknown(dom, "no_snapshots")

        header = rows[0]
        col = {name: i for i, name in enumerate(header)}
        ts_idx = col.get("timestamp", 1 if len(header) > 1 else 0)
        url_idx = col.get("original", 2 if len(header) > 2 else 1)

        data_rows = rows[1:]
        timestamps = [row[ts_idx] for row in data_rows if row and len(row) > ts_idx and row[ts_idx]]
        urls = [row[url_idx] for row in data_rows if len(row) > url_idx]
        if not timestamps:
            return _authority_unknown(dom, "empty_timestamps")

        first_ts = min(timestamps)
        last_ts = max(timestamps)
        first_seen = f"{first_ts[:4]}-{first_ts[4:6]}-{first_ts[6:8]}"
        last_seen = f"{last_ts[:4]}-{last_ts[4:6]}-{last_ts[6:8]}"
        try:
            age_years = (datetime.now() - datetime(int(first_ts[:4]), int(first_ts[4:6]), int(first_ts[6:8]))).days / 365.25
        except ValueError:
            age_years = None

        category = _infer_category_from_urls(urls)
        brand = _brand_signals(dom, len(data_rows), age_years)

        result = {
            "domain": dom,
            "archive_snapshots": len(data_rows),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "historical_category": category,
            "brand_signals": brand,
            "provider": "wayback_cdx",
            "status": "ok",
        }
        if brand.get("status") == "detected" or len(data_rows) >= 20:
            _emit_brain_event(
                "authority_candidate_found",
                dom,
                result={"snapshots": len(data_rows), "category": category},
            )
        return result
    except requests.RequestException as exc:
        return _authority_unknown(dom, str(exc))


def _authority_unknown(domain: str, reason: str = "") -> dict[str, Any]:
    return {
        "domain": domain,
        "archive_snapshots": 0,
        "first_seen": "unknown",
        "last_seen": "unknown",
        "historical_category": "unknown",
        "brand_signals": {"status": "unknown", "signals": []},
        "provider": "wayback_cdx",
        "status": "unknown",
        "reason": reason,
    }


# ── Katman 4: Domain Score ────────────────────────────────────────────────────

def _clamp_score(v: float) -> int:
    return max(0, min(100, int(round(v))))


def compute_domain_score(domain: str, keyword: str = "") -> dict[str, Any]:
    """0–100 skor — gerçek sinyaller; eksik veride düşük/unknown bileşenler."""
    dom = _normalize_domain(domain)
    authority = discover_authority(dom)
    expiry = check_expiry(dom)
    avail = check_domain(dom)

    label = dom.split(".")[0]
    brandability = 50
    if label.isalpha() and len(label) <= 10:
        brandability += 25
    if "-" in label:
        brandability -= 15
    if any(c.isdigit() for c in label):
        brandability -= 10
    brandability_score = _clamp_score(brandability)

    snapshots = authority.get("archive_snapshots") or 0
    if authority.get("status") == "unknown":
        authority_score = 0
    else:
        authority_score = _clamp_score(min(100, snapshots / 5))

    age_score = 0
    if authority.get("first_seen") and authority["first_seen"] != "unknown":
        try:
            first = datetime.strptime(authority["first_seen"], "%Y-%m-%d")
            years = (datetime.now() - first).days / 365.25
            age_score = _clamp_score(min(100, years * 12))
        except ValueError:
            age_score = 0

    spam_risk = 20
    if len(label) > 20:
        spam_risk += 20
    if label.count("-") >= 2:
        spam_risk += 25
    if sum(c.isdigit() for c in label) >= 3:
        spam_risk += 20
    spam_risk_score = _clamp_score(spam_risk)

    topical_match_score = 0
    if keyword:
        kw = keyword.lower().replace(" ", "")
        if kw in label or kw in dom:
            topical_match_score = 85
        elif any(kw[:i] in label for i in range(len(kw), 2, -1)):
            topical_match_score = 45
    else:
        topical_match_score = 0

    weights = (0.2, 0.25, 0.2, 0.15, 0.2)
    components = (brandability_score, authority_score, age_score, 100 - spam_risk_score, topical_match_score)
    overall = _clamp_score(sum(w * c for w, c in zip(weights, components)))

    result = {
        "domain": dom,
        "brandability_score": brandability_score,
        "authority_score": authority_score,
        "age_score": age_score,
        "spam_risk_score": spam_risk_score,
        "topical_match_score": topical_match_score,
        "overall_domain_score": overall,
        "available": avail.get("available") if avail.get("success") else None,
        "expiry_status": expiry.get("status"),
        "authority_status": authority.get("status"),
        "computed_at": _now_iso(),
    }
    _emit_brain_event("domain_scored", dom, result=result, metadata={"keyword": keyword})
    return result


def list_scores() -> dict[str, Any]:
    domains = _yukle()
    scores = []
    for entry in domains:
        dom = entry.get("domain", "")
        cached = entry.get("score")
        if cached:
            scores.append(cached)
        else:
            scores.append(compute_domain_score(dom, entry.get("keyword", "")))
    scores.sort(key=lambda x: -x.get("overall_domain_score", 0))
    return {"success": True, "toplam": len(scores), "scores": scores}


# ── Katman 5: HIVE Integration (read-only) ────────────────────────────────────

def _safe_health(fn) -> dict[str, Any]:
    try:
        res = fn()
        return {"ok": res.get("success", True) is not False, "detail": res}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


_INTEGRATION_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_INTEGRATION_TTL_SEC = 120


def hive_integrations() -> dict[str, Any]:
    """Opportunity, Authority Mesh, Campaign, Executive AI, Brain — read-only."""
    import time
    now = time.monotonic()
    cached = _INTEGRATION_CACHE.get("data")
    if cached is not None and (now - _INTEGRATION_CACHE["at"]) < _INTEGRATION_TTL_SEC:
        return dict(cached)

    integrations: dict[str, Any] = {}

    try:
        from app.moduller.opportunity_engine import health as opp_health
        integrations["opportunity_engine"] = _safe_health(opp_health)
    except Exception as exc:
        integrations["opportunity_engine"] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller.authority_mesh_engine import health as mesh_health
        integrations["authority_mesh"] = _safe_health(mesh_health)
    except Exception as exc:
        integrations["authority_mesh"] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller.campaign_engine import health as camp_health
        integrations["campaign_engine"] = _safe_health(camp_health)
    except Exception as exc:
        integrations["campaign_engine"] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller.executive_ai import health as exec_health
        integrations["executive_ai"] = _safe_health(exec_health)
    except Exception as exc:
        integrations["executive_ai"] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller.hive_brain_engine import hive_brain
        integrations["hive_brain"] = _safe_health(hive_brain.health)
        events = hive_brain.list_events(module="expireddomain", limit=10)
        integrations["hive_brain"]["recent_domain_events"] = events.get("events") or []
    except Exception as exc:
        integrations["hive_brain"] = {"ok": False, "error": str(exc)}

    ready = all(v.get("ok") for v in integrations.values() if isinstance(v, dict))
    result = {"success": True, "read_only": True, "ready": ready, "integrations": integrations}
    _INTEGRATION_CACHE["at"] = now
    _INTEGRATION_CACHE["data"] = result
    return result


def dashboard() -> dict[str, Any]:
    domains = _yukle()
    expiring = list_expiring(90)
    health_data = health()
    integrations = hive_integrations()

    status_counts: dict[str, int] = {}
    for d in domains:
        st = (d.get("expiry") or {}).get("status", "unchecked")
        status_counts[st] = status_counts.get(st, 0) + 1

    musait_count = sum(1 for d in domains if d.get("musait") is True)

    return {
        "success": True,
        "module": "expireddomain",
        "version": "v2",
        "watchlist_total": len(domains),
        "available_in_watchlist": musait_count,
        "expiring_soon": expiring.get("toplam", 0),
        "expiry_status_counts": status_counts,
        "health": health_data,
        "integrations_ready": integrations.get("ready"),
        "provider": health_data.get("provider"),
    }


def watchlist() -> dict[str, Any]:
    data = domain_listele()
    return {"success": True, **data}


def reports(report_type: str = "overview") -> dict[str, Any]:
    domains = _yukle()
    expiring = list_expiring(90)
    scores = list_scores()
    integrations = hive_integrations()

    base = {
        "success": True,
        "report_type": report_type,
        "generated_at": _now_iso(),
        "watchlist_total": len(domains),
    }

    if report_type == "expiring":
        return {**base, "data": expiring}
    if report_type == "scores":
        return {**base, "data": scores}
    if report_type == "integrations":
        return {**base, "data": integrations}
    if report_type == "authority":
        auth = []
        for entry in domains[:20]:
            dom = entry.get("domain", "")
            cached = entry.get("authority")
            auth.append(cached if cached else discover_authority(dom))
        return {**base, "data": {"domains": auth}}
    return {
        **base,
        "data": {
            "dashboard": dashboard(),
            "expiring": expiring,
            "top_scores": (scores.get("scores") or [])[:10],
            "integrations": integrations,
        },
    }


def health() -> dict[str, Any]:
    npx_ok = bool(shutil.which("npx"))
    whois_ok = bool(shutil.which("whois"))
    return {
        "status": "aktif" if (npx_ok or whois_ok) else "provider_gerekli",
        "module": "expireddomain",
        "version": "v2",
        "provider": "agent-domain-service-mcp",
        "npx_available": npx_ok,
        "whois_available": whois_ok,
        "rdap_available": True,
        "wayback_available": True,
        "api_key_required": False,
        "free_stack": True,
        "layers": ["availability", "expiry_watcher", "authority_discovery", "domain_score", "hive_integration"],
    }
