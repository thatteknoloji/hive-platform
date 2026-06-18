"""
Revenue / Lead Engine V1 — gelir ve lead ölçüm katmanı.

SEO/GEO çalışmalarının ticari sonucunu izler; üretim motoru değildir.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

logger = logging.getLogger("hive.revenue_lead")

STATE_FILE = Path(__file__).resolve().parent.parent / "revenue_lead_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 500
LEAD_LIMIT = 5000
VISIT_LIMIT = 2000

EVENT_TYPES = (
    "whatsapp_click",
    "phone_click",
    "email_click",
    "form_submit",
    "external_link_click",
    "listing_contact_click",
    "publisher_referral",
    "authority_referral",
)

LEAD_TYPE_MAP = {
    "whatsapp_click": "whatsapp",
    "phone_click": "phone",
    "email_click": "email",
    "form_submit": "form",
    "external_link_click": "external_click",
    "listing_contact_click": "external_click",
    "publisher_referral": "external_click",
    "authority_referral": "external_click",
}

STATUSES = ("new", "qualified", "invalid", "converted", "lost")

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "tracking_secret_required": False,
    "tracking_secret": "",
    "allowed_redirect_domains": [],
    "default_lead_value": 100,
    "spam_window_seconds": 30,
    "store_ip_hash": True,
    "rate_limit_per_minute": 60,
    "gdpr_note": "IP adresleri hash olarak saklanır; ham IP ve hassas kişisel veri tutulmaz.",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("leads", [])
                data.setdefault("visits", [])
                data.setdefault("rate_buckets", {})
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "leads": [],
        "visits": [],
        "rate_buckets": {},
        "history": [],
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, Any]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = st.setdefault("settings", dict(DEFAULT_SETTINGS))
    for k, v in (patch or {}).items():
        if k in DEFAULT_SETTINGS or k == "tracking_secret":
            cur[k] = v
    _save_state(st)
    return dict(cur)


def _append_history(state: dict[str, Any], entry: dict[str, Any]) -> None:
    lst = state.setdefault("history", [])
    lst.insert(0, entry)
    state["history"] = lst[:HISTORY_LIMIT]


def _record_brain(event_type: str, *, keyword: str = "", domain: str = "", result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event_type,
            "revenue_lead_engine",
            domain=domain,
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "revenue_lead_engine", "revenue_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _hash_ip(ip: str, salt: str = "hive-revenue-v1") -> str:
    if not ip:
        return ""
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


def _normalize_domain(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or url).lower().strip()


def _sanitize_target(target: str, max_len: int = 120) -> str:
    t = (target or "").strip()[:max_len]
    return t


def _spam_key(event_type: str, source_url: str, target: str, ip_hash: str) -> str:
    raw = f"{event_type}:{_normalize_domain(source_url)}:{_sanitize_target(target)}:{ip_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _rate_limit_ok(ip_hash: str) -> tuple[bool, str]:
    settings = get_settings()
    limit = int(settings.get("rate_limit_per_minute") or 60)
    st = _load_state()
    buckets = st.setdefault("rate_buckets", {})
    now = datetime.now(timezone.utc).timestamp()
    key = ip_hash or "anon"
    entries = [t for t in buckets.get(key, []) if now - t < 60]
    if len(entries) >= limit:
        return False, "rate_limit_exceeded"
    entries.append(now)
    buckets[key] = entries[-limit * 2:]
    _save_state(st)
    return True, ""


def _is_spam_duplicate(spam_key: str) -> bool:
    settings = get_settings()
    window = int(settings.get("spam_window_seconds") or 30)
    st = _load_state()
    now = datetime.now(timezone.utc).timestamp()
    recent = st.setdefault("_spam_recent", {})
    last = recent.get(spam_key)
    if last and now - last < window:
        return True
    recent[spam_key] = now
    st["_spam_recent"] = {k: v for k, v in list(recent.items())[-500:] if now - v < window * 3}
    _save_state(st)
    return False


def _infer_source_module(source_url: str, metadata: dict[str, Any]) -> str:
    if metadata.get("source_module"):
        return str(metadata["source_module"])
    dom = _normalize_domain(source_url)
    if not dom:
        return metadata.get("source_module") or "unknown"
    try:
        from app.moduller.publisher_hub import _load_state as pub_load
        pub_st = pub_load()
        for pub in pub_st.get("published") or []:
            for ch_res in (pub.get("channel_results") or {}).values():
                url = ch_res.get("url") if isinstance(ch_res, dict) else ""
                if url and _normalize_domain(url) == dom:
                    return f"publisher_hub:{pub.get('channels', ['unknown'])[0] if pub.get('channels') else 'publisher'}"
    except Exception:
        pass
    try:
        from app.moduller.authority_factory import _load_state as af_load
        for batch in af_load().get("batches") or []:
            for it in batch.get("items") or []:
                if _normalize_domain(it.get("result_url", "")) == dom:
                    return f"authority_factory:{it.get('provider', 'authority')}"
    except Exception:
        pass
    if "github.io" in dom:
        return "github_pages_worker"
    if "sites.google.com" in dom or "googleusercontent.com" in dom:
        return "google_sites_worker"
    if "blogspot" in dom:
        return "publisher_hub:blogger"
    if "tumblr.com" in dom:
        return "publisher_hub:tumblr"
    if "dev.to" in dom:
        return "publisher_hub:devto"
    if metadata.get("listing_id"):
        return "listing_hub"
    if metadata.get("astro_project_id"):
        return "astro_factory"
    return "organic"


def _compute_scores(lead: dict[str, Any]) -> dict[str, float]:
    event = lead.get("lead_type") or ""
    lt = lead.get("lead_type") or ""
    commercial = 40.0
    if lt in ("whatsapp", "phone"):
        commercial = 85.0
    elif lt == "form":
        commercial = 75.0
    elif lt == "email":
        commercial = 65.0
    elif event == "external_click":
        commercial = 45.0

    quality = 50.0
    if lead.get("keyword"):
        quality += 15
    if lead.get("utm"):
        quality += 10
    if lead.get("source_domain"):
        quality += 10
    if lead.get("status") == "qualified":
        quality += 20
    elif lead.get("status") == "converted":
        quality += 30

    source_val = 40.0
    sm = lead.get("source_module") or ""
    if "authority" in sm or "github" in sm or "google_sites" in sm:
        source_val += 25
    if "publisher" in sm or "blogger" in sm or "wordpress" in sm:
        source_val += 20
    if "listing" in sm:
        source_val += 15
    if "astro" in sm:
        source_val += 10

    return {
        "lead_quality_score": round(min(100, quality), 1),
        "commercial_intent_score": round(min(100, commercial), 1),
        "source_value_score": round(min(100, source_val), 1),
    }


def _make_lead(
    event_type: str,
    *,
    source_url: str = "",
    keyword: str = "",
    campaign: str = "",
    target: str = "",
    page_title: str = "",
    referrer: str = "",
    utm: dict | None = None,
    metadata: dict | None = None,
    ip_hash: str = "",
) -> dict[str, Any]:
    meta = dict(metadata or {})
    dom = _normalize_domain(source_url)
    sm = _infer_source_module(source_url, meta)
    lead_type = LEAD_TYPE_MAP.get(event_type, "external_click")
    settings = get_settings()
    est = float(meta.get("estimated_value") or settings.get("default_lead_value") or 100)

    lead = {
        "lead_id": f"lead-{uuid.uuid4().hex[:12]}",
        "timestamp": _now(),
        "source_url": source_url[:500] if source_url else "",
        "source_domain": dom,
        "source_module": sm,
        "keyword": (keyword or meta.get("keyword") or "").strip()[:200],
        "campaign": (campaign or meta.get("campaign") or "").strip()[:120],
        "lead_type": lead_type,
        "event_type": event_type,
        "target": _sanitize_target(target),
        "page_title": (page_title or meta.get("page_title") or "")[:200],
        "referrer": (referrer or "")[:500],
        "utm": utm or meta.get("utm") or {},
        "metadata": {k: v for k, v in meta.items() if k not in ("keyword", "campaign", "page_title", "estimated_value")},
        "status": "new",
        "estimated_value": est,
        "ip_hash": ip_hash if settings.get("store_ip_hash", True) else "",
    }
    scores = _compute_scores(lead)
    lead.update(scores)
    return lead


def track_lead(
    event_type: str,
    *,
    source_url: str = "",
    keyword: str = "",
    campaign: str = "",
    target: str = "",
    page_title: str = "",
    referrer: str = "",
    utm: dict | None = None,
    metadata: dict | None = None,
    client_ip: str = "",
    tracking_secret: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled", True):
        return {"success": False, "error": "revenue_lead_engine disabled"}

    et = (event_type or "").strip().lower()
    if et not in EVENT_TYPES:
        return {"success": False, "error": f"invalid_event_type:{et}"}

    if settings.get("tracking_secret_required") and tracking_secret != settings.get("tracking_secret", ""):
        return {"success": False, "error": "invalid_tracking_secret"}

    ip_hash = _hash_ip(client_ip) if settings.get("store_ip_hash", True) else ""
    ok, err = _rate_limit_ok(ip_hash or "anon")
    if not ok:
        return {"success": False, "error": err}

    sk = _spam_key(et, source_url, target, ip_hash)
    if _is_spam_duplicate(sk):
        return {"success": False, "error": "spam_duplicate", "message": "Duplicate event within spam window"}

    lead = _make_lead(
        et,
        source_url=source_url,
        keyword=keyword,
        campaign=campaign,
        target=target,
        page_title=page_title,
        referrer=referrer,
        utm=utm,
        metadata=metadata,
        ip_hash=ip_hash,
    )

    st = _load_state()
    st.setdefault("leads", []).insert(0, lead)
    st["leads"] = st["leads"][:LEAD_LIMIT]
    _append_history(st, {"type": "lead_created", "lead_id": lead["lead_id"], "event_type": et, "at": _now()})
    _save_state(st)

    _record_brain("lead_created", keyword=lead.get("keyword", ""), domain=lead.get("source_domain", ""), result={"lead_id": lead["lead_id"], "event_type": et})
    if lead.get("commercial_intent_score", 0) >= 70:
        _record_brain("revenue_signal_detected", keyword=lead.get("keyword", ""), domain=lead.get("source_domain", ""), result={"lead_id": lead["lead_id"], "scores": {k: lead[k] for k in ("commercial_intent_score", "source_value_score") if k in lead}})

    _post_track_hooks(lead)
    return {"success": True, "lead": lead}


def _post_track_hooks(lead: dict[str, Any]) -> None:
    """Authority / publisher attribution side-effects."""
    sm = lead.get("source_module") or ""
    url = lead.get("source_url") or ""
    if "authority_factory" in sm or "github_pages" in sm or "google_sites" in sm:
        try:
            boost_authority_from_lead(url, lead.get("keyword", ""), lead)
        except Exception as exc:
            logger.debug("authority boost: %s", exc)


def boost_authority_from_lead(source_url: str, keyword: str, lead: dict[str, Any] | None = None) -> dict[str, Any]:
    """Authority Factory item / mesh site lead taşıyorsa skor artır."""
    dom = _normalize_domain(source_url)
    if not dom:
        return {"success": False, "error": "domain_missing"}
    boosted = False
    try:
        from app.moduller.authority_factory import _load_state as af_load, _save_state as af_save
        st = af_load()
        for batch in st.get("batches") or []:
            for it in batch.get("items") or []:
                if _normalize_domain(it.get("result_url", "")) == dom:
                    it["lead_count"] = int(it.get("lead_count") or 0) + 1
                    it["revenue_signal"] = True
                    it["authority_score_boost"] = min(25, int(it.get("authority_score_boost") or 0) + 5)
                    boosted = True
        if boosted:
            af_save(st)
    except Exception:
        pass
    try:
        from app.moduller.authority_mesh_engine import _load_state as ame_load, _save_state as ame_save, compute_authority_score
        st = ame_load()
        for site in st.get("authority_sites") or []:
            urls = site.get("published_urls") or []
            if any(_normalize_domain(u) == dom for u in urls) or _normalize_domain(site.get("domain_or_url", "")) == dom:
                site["lead_count"] = int(site.get("lead_count") or 0) + 1
                site["rank_watcher_signal"] = min(100, int(site.get("rank_watcher_signal") or 0) + 10)
                site["authority_score"] = compute_authority_score({**site, "provider_trust": 80})
                boosted = True
        if boosted:
            ame_save(st)
    except Exception:
        pass
    return {"success": boosted, "domain": dom}


def track_listing_contact(
    listing_id: str,
    contact_type: str = "phone",
    *,
    source_url: str = "",
    keyword: str = "",
    target: str = "",
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Listing Hub ilan kontakt aksiyonu."""
    event_map = {"phone": "phone_click", "whatsapp": "whatsapp_click", "email": "email_click", "form": "form_submit"}
    et = event_map.get(contact_type, "listing_contact_click")
    meta = dict(metadata or {})
    meta["listing_id"] = listing_id
    meta["source_module"] = "listing_hub"
    return track_lead(et, source_url=source_url, keyword=keyword, target=target, metadata=meta)


def update_lead_status(lead_id: str, status: str, *, estimated_value: float | None = None) -> dict[str, Any]:
    if status not in STATUSES:
        return {"success": False, "error": f"invalid_status:{status}"}
    st = _load_state()
    lead = next((l for l in st.get("leads") or [] if l.get("lead_id") == lead_id), None)
    if not lead:
        return {"success": False, "error": "lead_not_found"}
    lead["status"] = status
    if estimated_value is not None:
        lead["estimated_value"] = float(estimated_value)
    scores = _compute_scores(lead)
    lead.update(scores)
    _save_state(st)

    brain_map = {"qualified": "lead_qualified", "converted": "lead_converted", "lost": "lead_lost", "invalid": "lead_lost"}
    if status in brain_map:
        _record_brain(brain_map[status], keyword=lead.get("keyword", ""), domain=lead.get("source_domain", ""), result={"lead_id": lead_id, "status": status})
    return {"success": True, "lead": lead}


def _validate_redirect_target(event_type: str, target: str) -> tuple[bool, str, str]:
    """Returns ok, error, resolved_url."""
    t = (target or "").strip()
    if not t:
        return False, "target_required", ""

    et = (event_type or "").strip().lower()
    allowed_domains = get_settings().get("allowed_redirect_domains") or []

    if et == "whatsapp_click":
        digits = re.sub(r"\D", "", t)
        if digits and len(digits) >= 10:
            return True, "", f"https://wa.me/{digits}"
        if t.startswith("https://wa.me/") or t.startswith("https://api.whatsapp.com/"):
            return True, "", t
        return False, "invalid_whatsapp_target", ""

    if et == "phone_click":
        digits = re.sub(r"\D", "", t)
        if digits:
            return True, "", f"tel:+{digits.lstrip('+')}"
        if t.startswith("tel:"):
            return True, "", t
        return False, "invalid_phone_target", ""

    if et == "email_click":
        if t.startswith("mailto:"):
            return True, "", t
        if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", t):
            return True, "", f"mailto:{t}"
        return False, "invalid_email_target", ""

    if et in ("external_link_click", "listing_contact_click", "publisher_referral", "authority_referral", "form_submit"):
        if not t.startswith("http://") and not t.startswith("https://"):
            return False, "invalid_external_url", ""
        parsed = urlparse(t)
        if not parsed.netloc:
            return False, "invalid_external_url", ""
        if allowed_domains:
            host = parsed.netloc.lower()
            if not any(host == d.lower() or host.endswith("." + d.lower()) for d in allowed_domains):
                return False, "open_redirect_blocked", ""
        else:
            blocked = ("javascript:", "data:", "file:", "//")
            low = t.lower()
            if any(b in low for b in blocked):
                return False, "open_redirect_blocked", ""
        return True, "", t

    return False, "unsupported_redirect_event", ""


def track_and_redirect(
    event_type: str,
    target: str,
    *,
    source_url: str = "",
    keyword: str = "",
    campaign: str = "",
    client_ip: str = "",
    tracking_secret: str = "",
) -> dict[str, Any]:
    ok, err, resolved = _validate_redirect_target(event_type, target)
    if not ok:
        return {"success": False, "error": err}

    track_res = track_lead(
        event_type,
        source_url=source_url,
        keyword=keyword,
        campaign=campaign,
        target=target,
        metadata={"redirect": True},
        client_ip=client_ip,
        tracking_secret=tracking_secret,
    )
    if not track_res.get("success") and track_res.get("error") not in ("spam_duplicate",):
        return track_res

    return {"success": True, "redirect_url": resolved, "track": track_res}


def build_redirect_url(
    event_type: str,
    target: str,
    *,
    source_url: str = "",
    keyword: str = "",
    campaign: str = "",
    base_api: str = "http://localhost:4001",
) -> str:
    params = {
        "event_type": event_type,
        "target": target,
        "source_url": source_url,
        "keyword": keyword,
        "campaign": campaign,
    }
    q = "&".join(f"{k}={quote(str(v))}" for k, v in params.items() if v)
    return f"{base_api.rstrip('/')}/api/revenue-leads/track-redirect?{q}"


def generate_tracking_script(base_api: str = "http://localhost:4001") -> str:
    """Astro siteler için minimal JS tracking snippet."""
    api = base_api.rstrip("/")
    return f"""(function(){{
  var API="{api}/api/revenue-leads/track";
  function track(ev,target,extra){{
    var p={{event_type:ev,target:target||"",source_url:location.href,keyword:document.title,metadata:extra||{{}}}};
    try{{navigator.sendBeacon&&navigator.sendBeacon(API,JSON.stringify(p))||
      fetch(API,{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(p),keepalive:true}});}}catch(e){{}}
  }}
  document.addEventListener("click",function(e){{
    var a=e.target.closest("a");if(!a)return;
    var h=a.getAttribute("href")||"";
    if(h.indexOf("wa.me")>-1||h.indexOf("whatsapp")>-1)track("whatsapp_click",h);
    else if(h.indexOf("tel:")===0)track("phone_click",h);
    else if(h.indexOf("mailto:")===0)track("email_click",h);
  }});
  document.querySelectorAll("form").forEach(function(f){{
    f.addEventListener("submit",function(){{track("form_submit",location.href);}});
  }});
}})();"""


def list_leads(
    *,
    status: str = "",
    keyword: str = "",
    source_domain: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    st = _load_state()
    leads = st.get("leads") or []
    if status:
        leads = [l for l in leads if l.get("status") == status]
    if keyword:
        kw = keyword.lower()
        leads = [l for l in leads if kw in (l.get("keyword") or "").lower()]
    if source_domain:
        sd = source_domain.lower()
        leads = [l for l in leads if sd in (l.get("source_domain") or "").lower()]
    total = len(leads)
    return {"success": True, "leads": leads[offset:offset + limit], "count": len(leads[offset:offset + limit]), "total": total}


def get_lead(lead_id: str) -> dict[str, Any]:
    st = _load_state()
    lead = next((l for l in st.get("leads") or [] if l.get("lead_id") == lead_id), None)
    if not lead:
        return {"success": False, "error": "lead_not_found"}
    return {"success": True, "lead": lead}


def _aggregate_sources(leads: list[dict]) -> list[dict]:
    agg: dict[str, dict] = {}
    for l in leads:
        key = l.get("source_module") or "unknown"
        if key not in agg:
            agg[key] = {"source_module": key, "leads": 0, "converted": 0, "estimated_revenue": 0.0, "avg_commercial_score": 0.0, "_scores": []}
        agg[key]["leads"] += 1
        if l.get("status") == "converted":
            agg[key]["converted"] += 1
        agg[key]["estimated_revenue"] += float(l.get("estimated_value") or 0)
        agg[key]["_scores"].append(float(l.get("commercial_intent_score") or 0))
    out = []
    for v in agg.values():
        scores = v.pop("_scores", [])
        v["avg_commercial_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        v["conversion_rate"] = round(v["converted"] / v["leads"] * 100, 2) if v["leads"] else 0
        out.append(v)
    return sorted(out, key=lambda x: -x["leads"])


def _aggregate_keywords(leads: list[dict]) -> list[dict]:
    agg: dict[str, dict] = {}
    for l in leads:
        kw = (l.get("keyword") or "").strip().lower()
        if not kw:
            continue
        if kw not in agg:
            agg[kw] = {"keyword": kw, "leads": 0, "converted": 0, "estimated_revenue": 0.0, "avg_quality_score": 0.0, "_scores": []}
        agg[kw]["leads"] += 1
        if l.get("status") == "converted":
            agg[kw]["converted"] += 1
        agg[kw]["estimated_revenue"] += float(l.get("estimated_value") or 0)
        agg[kw]["_scores"].append(float(l.get("lead_quality_score") or 0))
    out = []
    for v in agg.values():
        scores = v.pop("_scores", [])
        v["avg_quality_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        out.append(v)
    return sorted(out, key=lambda x: -x["leads"])


def build_funnel(*, days: int = 30) -> dict[str, Any]:
    st = _load_state()
    leads = st.get("leads") or []
    visits = len(st.get("visits") or [])
    clicks = sum(1 for l in leads if l.get("event_type") in EVENT_TYPES)
    qualified = sum(1 for l in leads if l.get("status") in ("qualified", "converted"))
    converted = sum(1 for l in leads if l.get("status") == "converted")
    est_rev = sum(float(l.get("estimated_value") or 0) for l in leads if l.get("status") in ("qualified", "converted", "new"))
    conv_rate = round(converted / clicks * 100, 2) if clicks else 0.0
    return {
        "success": True,
        "visits": visits,
        "clicks": clicks,
        "leads": len(leads),
        "qualified": qualified,
        "converted": converted,
        "estimated_revenue": round(est_rev, 2),
        "conversion_rate": conv_rate,
    }


def list_sources(limit: int = 50) -> dict[str, Any]:
    st = _load_state()
    sources = _aggregate_sources(st.get("leads") or [])[:limit]
    return {"success": True, "sources": sources, "count": len(sources)}


def list_keywords(limit: int = 50) -> dict[str, Any]:
    st = _load_state()
    keywords = _aggregate_keywords(st.get("leads") or [])[:limit]
    return {"success": True, "keywords": keywords, "count": len(keywords)}


def publisher_impact() -> dict[str, Any]:
    st = _load_state()
    channels = ("wordpress", "blogger", "tumblr", "devto", "github_pages", "google_sites")
    leads = st.get("leads") or []
    out = {ch: {"channel": ch, "leads": 0, "converted": 0, "estimated_revenue": 0.0} for ch in channels}
    for l in leads:
        sm = (l.get("source_module") or "").lower()
        for ch in channels:
            if ch in sm or (ch == "github_pages" and "github" in sm) or (ch == "google_sites" and "google_sites" in sm):
                out[ch]["leads"] += 1
                if l.get("status") == "converted":
                    out[ch]["converted"] += 1
                out[ch]["estimated_revenue"] += float(l.get("estimated_value") or 0)
    return {"success": True, "channels": list(out.values())}


def authority_impact() -> dict[str, Any]:
    st = _load_state()
    leads = [l for l in st.get("leads") or [] if "authority" in (l.get("source_module") or "") or "github" in (l.get("source_module") or "") or "google_sites" in (l.get("source_module") or "")]
    domains: dict[str, dict] = {}
    for l in leads:
        d = l.get("source_domain") or "unknown"
        if d not in domains:
            domains[d] = {"domain": d, "leads": 0, "module": l.get("source_module"), "estimated_revenue": 0.0}
        domains[d]["leads"] += 1
        domains[d]["estimated_revenue"] += float(l.get("estimated_value") or 0)
    return {"success": True, "domains": sorted(domains.values(), key=lambda x: -x["leads"])}


def opportunity_scoring_payload() -> dict[str, Any]:
    """Opportunity Engine — commercial_opportunity_score sinyalleri."""
    st = _load_state()
    leads = st.get("leads") or []
    kw_stats = _aggregate_keywords(leads)
    signals = []
    for row in kw_stats:
        kw = row["keyword"]
        lead_count = row["leads"]
        commercial = min(100, 40 + lead_count * 12 + row.get("avg_quality_score", 0) * 0.3)
        signals.append({
            "keyword": kw,
            "lead_count": lead_count,
            "commercial_opportunity_score": round(commercial, 1),
            "estimated_revenue": row.get("estimated_revenue", 0),
            "boost": lead_count >= 2,
            "penalize": False,
        })
    high_traffic_no_lead = _high_traffic_no_lead_keywords()
    for item in high_traffic_no_lead:
        signals.append({
            "keyword": item["keyword"],
            "lead_count": 0,
            "commercial_opportunity_score": max(0, item.get("traffic_score", 50) - 25),
            "boost": False,
            "penalize": True,
            "reason": "traffic_without_leads",
        })
    return {"success": True, "signals": signals, "high_value_keywords": [s for s in signals if s.get("boost")][:20]}


def _high_traffic_no_lead_keywords() -> list[dict]:
    """Rank trafik var lead yok keyword adayları."""
    lead_kws = {((l.get("keyword") or "").lower()) for l in _load_state().get("leads") or [] if l.get("keyword")}
    out: list[dict] = []
    try:
        from app.moduller.rank_index_watcher import _load_state as rw_load
        for pid, proj in (rw_load().get("projects") or {}).items():
            for kw in proj.get("keywords") or []:
                k = (kw.get("keyword") or "").lower()
                pos = kw.get("last_position")
                if k and k not in lead_kws and pos and pos <= 15:
                    out.append({"keyword": k, "traffic_score": max(30, 100 - pos * 4), "project_id": pid})
    except Exception:
        pass
    return out[:30]


def agent_signals(project_id: str = "") -> dict[str, Any]:
    """Autonomous Agent — lead/trafik insight."""
    st = _load_state()
    leads = st.get("leads") or []
    kw_stats = {r["keyword"]: r for r in _aggregate_keywords(leads)}
    insights: list[dict] = []

    for item in _high_traffic_no_lead_keywords():
        kw = item["keyword"]
        insights.append({
            "type": "traffic_no_leads",
            "keyword": kw,
            "message": f"'{kw}' trafik getiriyor ama lead getirmiyor",
            "recommended_action": "optimize_conversion",
            "priority": "HIGH",
        })

    for kw, row in kw_stats.items():
        if row["leads"] >= 2 and row["leads"] <= 20:
            insights.append({
                "type": "high_lead_keyword",
                "keyword": kw,
                "message": f"'{kw}' az/orta trafikle {row['leads']} lead getirdi",
                "recommended_action": "scale_content",
                "priority": "MEDIUM",
                "metadata": row,
            })

    auth = authority_impact()
    for dom in (auth.get("domains") or [])[:5]:
        if dom.get("leads", 0) >= 1:
            insights.append({
                "type": "authority_lead_carrier",
                "keyword": "",
                "message": f"Authority source {dom['domain']} lead taşıyor ({dom['leads']})",
                "recommended_action": "replicate_authority_pattern",
                "priority": "MEDIUM",
                "metadata": dom,
            })

    return {"success": True, "insights": insights[:25], "project_id": project_id}


def mission_control_payload() -> dict[str, Any]:
    st = _load_state()
    today = _today()
    today_leads = [l for l in st.get("leads") or [] if (l.get("timestamp") or "").startswith(today)]
    high_value = [l for l in today_leads if float(l.get("estimated_value") or 0) >= float(get_settings().get("default_lead_value") or 100) * 1.5 or float(l.get("commercial_intent_score") or 0) >= 75]
    sources = _aggregate_sources(st.get("leads") or [])
    best_source = sources[0] if sources else None
    no_lead_pages = _high_traffic_no_lead_keywords()

    rev_opp = sum(float(l.get("estimated_value") or 0) for l in today_leads)
    return {
        "success": True,
        "today_leads": len(today_leads),
        "high_value_leads": len(high_value),
        "best_lead_source": best_source,
        "revenue_opportunity": round(rev_opp, 2),
        "no_lead_high_traffic_pages": no_lead_pages[:8],
        "recent_leads": today_leads[:10],
        "funnel": build_funnel(),
    }


def dashboard() -> dict[str, Any]:
    st = _load_state()
    leads = st.get("leads") or []
    today = _today()
    today_leads = [l for l in leads if (l.get("timestamp") or "").startswith(today)]
    funnel = build_funnel()
    return {
        "success": True,
        "module": "revenue_lead_engine",
        "enabled": get_settings().get("enabled", True),
        "total_leads": len(leads),
        "today_leads": len(today_leads),
        "converted": sum(1 for l in leads if l.get("status") == "converted"),
        "qualified": sum(1 for l in leads if l.get("status") == "qualified"),
        "estimated_revenue": funnel.get("estimated_revenue", 0),
        "conversion_rate": funnel.get("conversion_rate", 0),
        "top_sources": _aggregate_sources(leads)[:10],
        "top_keywords": _aggregate_keywords(leads)[:10],
        "funnel": funnel,
        "recent_leads": leads[:15],
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "overview": dashboard,
        "leads": lambda: list_leads(limit=500),
        "sources": list_sources,
        "keywords": list_keywords,
        "funnel": build_funnel,
        "publisher": publisher_impact,
        "authority": authority_impact,
    }
    fn = generators.get(report_type, dashboard)
    payload = fn()
    path = REPORTS_DIR / f"revenue-leads-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def health() -> dict[str, Any]:
    settings = get_settings()
    dash = dashboard()
    return {
        "success": True,
        "module": "revenue_lead_engine",
        "enabled": settings.get("enabled", True),
        "event_types": list(EVENT_TYPES),
        "total_leads": dash.get("total_leads", 0),
        "today_leads": dash.get("today_leads", 0),
        "tracking_secret_required": settings.get("tracking_secret_required", False),
        "gdpr_note": settings.get("gdpr_note", ""),
    }


def apply_commercial_scores_to_opportunities(opportunities: list[dict]) -> list[dict]:
    """Opportunity Engine entegrasyonu — commercial_opportunity_score ekle."""
    payload = opportunity_scoring_payload()
    by_kw = {s["keyword"].lower(): s for s in payload.get("signals") or [] if s.get("keyword")}
    out = []
    for opp in opportunities:
        o = dict(opp)
        kw = (o.get("keyword") or "").lower()
        sig = by_kw.get(kw)
        base = float(o.get("opportunity_score") or 50)
        if sig:
            commercial = float(sig.get("commercial_opportunity_score") or base)
            o["commercial_opportunity_score"] = commercial
            if sig.get("boost"):
                o["opportunity_score"] = round(min(100, base * 0.7 + commercial * 0.3 + 8), 1)
            elif sig.get("penalize"):
                o["opportunity_score"] = round(max(0, base * 0.85 - 5), 1)
                o["revenue_penalty"] = True
            else:
                o["opportunity_score"] = round(min(100, base * 0.85 + commercial * 0.15), 1)
        else:
            o["commercial_opportunity_score"] = round(base * 0.5, 1)
        out.append(o)
    return out
