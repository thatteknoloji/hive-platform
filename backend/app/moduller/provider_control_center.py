"""
Provider Control Center V1 — dış servis gözlem ve raporlama katmanı.

Yeni entegrasyon yazmaz, publish/deploy yapmaz.
Yalnızca provider keşfi, sağlık, token, quota ve son işlem durumunu raporlar.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app import config

logger = logging.getLogger("hive.provider_control_center")

STATE_FILE = Path(__file__).resolve().parent.parent / "provider_control_center_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 500
ACTIVITY_LIMIT = 200
ALERT_LIMIT = 100

HEALTH_STATUSES = ("healthy", "warning", "critical", "provider_missing", "not_configured")

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "auto_check_interval_minutes": 30,
    "alert_on_critical": True,
    "alert_on_disconnect": True,
    "include_quota_probe": True,
}

PROVIDER_IDS = (
    "github_pages",
    "google_sites",
    "blogger",
    "tumblr",
    "devto",
    "wordpress",
    "cloudflare",
    "ghost",
    "hashnode",
    "openrouter",
    "dataforseo",
    "search_console",
    "google_analytics",
)

PROVIDER_LABELS: dict[str, str] = {
    "github_pages": "GitHub Pages",
    "google_sites": "Google Sites",
    "blogger": "Blogger",
    "tumblr": "Tumblr",
    "devto": "Dev.to",
    "wordpress": "WordPress",
    "cloudflare": "Cloudflare",
    "ghost": "Ghost",
    "hashnode": "Hashnode",
    "openrouter": "OpenRouter",
    "dataforseo": "DataForSEO",
    "search_console": "Search Console",
    "google_analytics": "Google Analytics",
}

TOKEN_ENV_KEYS: dict[str, list[str]] = {
    "github_pages": ["GITHUB_TOKEN", "GITHUB_API_KEY", "KF_GITHUB_TOKEN"],
    "google_sites": ["SELENIUM_DRIVER"],
    "blogger": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"],
    "tumblr": ["TUMBLR_CONSUMER_KEY", "TUMBLR_CONSUMER_SECRET"],
    "devto": ["DEVTO_API_KEY"],
    "wordpress": [],
    "cloudflare": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"],
    "ghost": ["GHOST_API_URL", "GHOST_ADMIN_API_KEY"],
    "hashnode": ["HASHNODE_API_TOKEN"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "dataforseo": ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"],
    "search_console": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "GSC_CLIENT_ID", "GSC_CLIENT_SECRET"],
    "google_analytics": ["GA4_MEASUREMENT_ID", "GA4_PROPERTY_ID", "GA4_SERVICE_ACCOUNT_FILE"],
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("providers", {})
                data.setdefault("alerts", [])
                data.setdefault("recent_activity", [])
                data.setdefault("history", [])
                data.setdefault("last_full_check", "")
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "providers": {},
        "alerts": [],
        "recent_activity": [],
        "history": [],
        "last_full_check": "",
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
        if k in DEFAULT_SETTINGS:
            cur[k] = v
    _save_state(st)
    return dict(cur)


def mask_token(value: str | None) -> str:
    """Token asla açık görünmez — ********ABCD formatı."""
    if not value or not str(value).strip():
        return ""
    raw = str(value).strip()
    suffix = raw[-4:] if len(raw) >= 4 else raw
    return f"********{suffix}"


def _token_info(provider_id: str) -> dict[str, Any]:
    keys = TOKEN_ENV_KEYS.get(provider_id, [])
    present: list[str] = []
    masked: list[str] = []
    for key in keys:
        val = (config.get(key) or "").strip()
        if val:
            present.append(key)
            masked.append(mask_token(val))
    return {
        "keys_expected": keys,
        "keys_present": present,
        "tokens_masked": masked,
        "token_present": bool(present),
    }


def _status_to_score(status: str) -> int:
    return {
        "healthy": 95,
        "warning": 55,
        "critical": 20,
        "not_configured": 35,
        "provider_missing": 10,
    }.get(status, 0)


def _append_history(state: dict[str, Any], entry: dict[str, Any]) -> None:
    lst = state.setdefault("history", [])
    lst.insert(0, entry)
    state["history"] = lst[:HISTORY_LIMIT]


def _append_activity(state: dict[str, Any], entry: dict[str, Any]) -> None:
    lst = state.setdefault("recent_activity", [])
    lst.insert(0, entry)
    state["recent_activity"] = lst[:ACTIVITY_LIMIT]


def _append_alert(state: dict[str, Any], entry: dict[str, Any]) -> None:
    lst = state.setdefault("alerts", [])
    lst.insert(0, entry)
    state["alerts"] = lst[:ALERT_LIMIT]


def _record_brain(
    event_type: str,
    *,
    keyword: str = "",
    result: dict | None = None,
    reason: str = "",
) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event_type,
            "provider_control_center",
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "provider_control_center", "provider_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _safe_call(fn: Callable[..., Any], *args: Any, default: Any = None, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("probe failed: %s", exc)
        return default


def _last_publish_for_channel(channel: str) -> dict[str, Any]:
    try:
        from app.moduller.publisher_hub import _load_state as ph_load
        st = ph_load()
        published = st.get("published") or []
        for item in reversed(published):
            ch = item.get("channel") or item.get("channels", [None])[0] if item.get("channels") else item.get("channel")
            if ch == channel or channel in (item.get("channels") or []):
                return {
                    "action": "publish",
                    "status": item.get("status"),
                    "at": item.get("published_at") or item.get("updated_at") or "",
                    "title": item.get("title", ""),
                    "error": item.get("error") if item.get("status") == "failed" else "",
                }
        stats = (st.get("channel_stats") or {}).get(channel) or {}
        return {"action": "publish", "stats": stats}
    except Exception:
        return {}


def _worker_last_action(worker: str, *, action: str = "deploy") -> dict[str, Any]:
    state_files = {
        "github_pages": Path(__file__).resolve().parent.parent / "github_pages_worker_state.json",
        "google_sites": Path(__file__).resolve().parent.parent / "google_sites_worker_state.json",
    }
    path = state_files.get(worker)
    if not path or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("sites") or data.get("tasks") or []
        for item in reversed(items):
            status = item.get("status", "")
            if status in ("published", "failed", "deployed", "error", "login_required"):
                return {
                    "action": action,
                    "status": status,
                    "at": item.get("updated_at") or item.get("completed_at") or item.get("created_at") or "",
                    "title": item.get("title") or item.get("site_title") or item.get("repo_name") or "",
                    "error": item.get("error") or (status if status in ("failed", "error") else ""),
                }
    except Exception:
        pass
    return {}


def _orchestrator_recent(provider_hint: str) -> dict[str, Any]:
    try:
        from app.moduller.action_orchestrator import build_dashboard
        dash = build_dashboard()
        for act in dash.get("recent_actions") or []:
            mod = (act.get("module") or act.get("target") or "").lower()
            if provider_hint in mod or mod in provider_hint:
                return {
                    "action": act.get("action_type") or act.get("type") or "sync",
                    "status": act.get("status"),
                    "at": act.get("completed_at") or act.get("started_at") or "",
                    "error": act.get("error") or "",
                }
    except Exception:
        pass
    return {}


def _probe_github_pages() -> dict[str, Any]:
    from app.moduller.github_pages_worker import health
    h = health()
    ready = bool(h.get("provider_ready"))
    err = h.get("error")
    tokens = _token_info("github_pages")
    configured = tokens["token_present"] or bool(h.get("owner_configured"))
    if not configured:
        status = "not_configured"
    elif not ready:
        status = "critical" if err else "warning"
    else:
        status = "healthy"
    last = _worker_last_action("github_pages", action="deploy")
    return {
        "connected": ready,
        "configured": configured,
        "status": status,
        "last_error": err or last.get("error") or "",
        "metadata": {
            "module": "github_pages_worker",
            "sites_count": h.get("sites_count", 0),
            "published_count": h.get("published_count", 0),
            "tokens": tokens,
            "last_action": last,
        },
        "quota": {"sites": h.get("sites_count", 0), "published": h.get("published_count", 0)},
    }


def _probe_google_sites() -> dict[str, Any]:
    from app.moduller.google_sites_worker import health
    h = health()
    ready = bool(h.get("provider_ready"))
    err = h.get("error")
    tokens = _token_info("google_sites")
    configured = ready or tokens["token_present"] or bool(h.get("playwright_available"))
    if not configured and not h.get("provider"):
        status = "provider_missing"
    elif not configured:
        status = "not_configured"
    elif not ready:
        status = "critical" if h.get("login_required_count", 0) else "warning"
    else:
        status = "healthy"
    last = _worker_last_action("google_sites", action="publish")
    return {
        "connected": ready,
        "configured": configured,
        "status": status,
        "last_error": err or last.get("error") or "",
        "metadata": {
            "module": "google_sites_worker",
            "provider": h.get("provider"),
            "tasks_count": h.get("tasks_count", 0),
            "login_required_count": h.get("login_required_count", 0),
            "tokens": tokens,
            "last_action": last,
        },
        "quota": {"tasks": h.get("tasks_count", 0), "published": h.get("published_count", 0)},
    }


def _probe_publisher_channel(channel_id: str, provider_id: str) -> dict[str, Any]:
    try:
        from app.moduller.publisher_hub import _channel_status
        st = _channel_status(channel_id)
    except Exception as exc:
        return {
            "connected": False,
            "configured": False,
            "status": "provider_missing",
            "last_error": str(exc),
            "metadata": {"module": "publisher_hub", "error": str(exc)},
            "quota": {},
        }
    tokens = _token_info(provider_id)
    configured = bool(st.get("configured")) or tokens["token_present"]
    connected = bool(st.get("connected"))
    err = st.get("error") or ""
    if not configured:
        status = "not_configured"
    elif not connected:
        status = "warning" if not err else "critical"
    else:
        status = "healthy"
    last = _last_publish_for_channel(channel_id)
    stats = last.get("stats") or {}
    return {
        "connected": connected,
        "configured": configured,
        "status": status,
        "last_error": err or last.get("error") or "",
        "metadata": {
            "module": "publisher_hub",
            "channel": channel_id,
            "label": st.get("label"),
            "mode": st.get("mode"),
            "tokens": tokens,
            "last_action": last if last.get("at") or last.get("status") else {},
        },
        "quota": {
            "published": stats.get("published", 0),
            "failed": stats.get("failed", 0),
        },
    }


def _probe_cloudflare() -> dict[str, Any]:
    from app.moduller.cloudflare_pages_deploy import cf_status
    h = cf_status()
    tokens = _token_info("cloudflare")
    configured = bool(h.get("configured")) or tokens["token_present"]
    connected = configured
    status = "healthy" if connected else "not_configured"
    last = _orchestrator_recent("cloudflare")
    return {
        "connected": connected,
        "configured": configured,
        "status": status,
        "last_error": last.get("error") or "",
        "metadata": {
            "module": "cloudflare_pages_deploy",
            "branch": h.get("branch"),
            "project_prefix": h.get("project_prefix"),
            "tokens": tokens,
            "last_action": last or {"action": "deploy"},
        },
        "quota": {"token_present": h.get("token_present", False)},
    }


def _probe_openrouter() -> dict[str, Any]:
    tokens = _token_info("openrouter")
    configured = tokens["token_present"]
    connected = configured
    status = "healthy" if connected else "not_configured"
    return {
        "connected": connected,
        "configured": configured,
        "status": status,
        "last_error": "",
        "metadata": {"module": "api_key_manager", "tokens": tokens},
        "quota": {"configured": configured},
    }


def _probe_dataforseo() -> dict[str, Any]:
    from app.moduller.dataforseo_client import is_configured
    tokens = _token_info("dataforseo")
    configured = is_configured() or tokens["token_present"]
    connected = configured
    status = "healthy" if connected else "not_configured"
    try:
        from app.moduller.provider_settings import get_settings
        mode = get_settings().get("rank", "auto")
    except Exception:
        mode = "auto"
    return {
        "connected": connected,
        "configured": configured,
        "status": status,
        "last_error": "" if connected else "DATAFORSEO credentials missing",
        "metadata": {"module": "dataforseo_client", "tokens": tokens, "provider_mode": mode},
        "quota": {"mode": mode, "available": connected},
    }


def _probe_search_console() -> dict[str, Any]:
    tokens = _token_info("search_console")
    configured = tokens["token_present"]
    connected = False
    err = ""
    try:
        from app.moduller.rank_index_watcher import health
        h = health()
        connected = bool(h.get("search_console"))
        configured = configured or connected
        if not connected and configured:
            err = "GSC OAuth not validated"
    except Exception as exc:
        err = str(exc)
    if not configured:
        status = "not_configured"
    elif not connected:
        status = "warning"
    else:
        status = "healthy"
    return {
        "connected": connected,
        "configured": configured,
        "status": status,
        "last_error": err,
        "metadata": {"module": "rank_index_watcher", "tokens": tokens},
        "quota": {"projects": _safe_call(lambda: __import__("app.moduller.rank_index_watcher", fromlist=["health"]).health().get("project_count", 0), default=0)},
    }


def _probe_google_analytics() -> dict[str, Any]:
    tokens = _token_info("google_analytics")
    has_mid = bool((config.get("GA4_MEASUREMENT_ID") or "").strip())
    has_prop = bool((config.get("GA4_PROPERTY_ID") or "").strip())
    has_sa = bool((config.get("GA4_SERVICE_ACCOUNT_FILE") or "").strip())
    configured = has_mid or has_prop or has_sa or tokens["token_present"]
    connected = configured
    status = "healthy" if connected else "not_configured"
    return {
        "connected": connected,
        "configured": configured,
        "status": status,
        "last_error": "" if connected else "GA4 credentials missing",
        "metadata": {
            "module": "api_key_manager",
            "tokens": tokens,
            "measurement_id": bool(has_mid),
            "property_id": bool(has_prop),
            "service_account": bool(has_sa),
        },
        "quota": {"configured": configured},
    }


PROBE_MAP: dict[str, Callable[[], dict[str, Any]]] = {
    "github_pages": _probe_github_pages,
    "google_sites": _probe_google_sites,
    "blogger": lambda: _probe_publisher_channel("blogger", "blogger"),
    "tumblr": lambda: _probe_publisher_channel("tumblr", "tumblr"),
    "devto": lambda: _probe_publisher_channel("devto", "devto"),
    "wordpress": lambda: _probe_publisher_channel("wordpress", "wordpress"),
    "ghost": lambda: _probe_publisher_channel("ghost", "ghost"),
    "hashnode": lambda: _probe_publisher_channel("hashnode", "hashnode"),
    "cloudflare": _probe_cloudflare,
    "openrouter": _probe_openrouter,
    "dataforseo": _probe_dataforseo,
    "search_console": _probe_search_console,
    "google_analytics": _probe_google_analytics,
}


def _build_provider_record(provider_id: str, probe: dict[str, Any], *, checked_at: str) -> dict[str, Any]:
    status = probe.get("status") or "provider_missing"
    if status not in HEALTH_STATUSES:
        status = "warning"
    connected = bool(probe.get("connected"))
    configured = bool(probe.get("configured"))
    last_action = (probe.get("metadata") or {}).get("last_action") or {}
    last_success = ""
    if connected and last_action.get("status") in ("published", "deployed", "success", "completed"):
        last_success = last_action.get("at") or checked_at
    elif connected and status == "healthy":
        last_success = checked_at
    return {
        "provider": provider_id,
        "label": PROVIDER_LABELS.get(provider_id, provider_id),
        "connected": connected,
        "configured": configured,
        "last_check": checked_at,
        "last_success": last_success,
        "last_error": probe.get("last_error") or "",
        "health_score": _status_to_score(status),
        "status": status,
        "quota": probe.get("quota") or {},
        "metadata": probe.get("metadata") or {},
    }


def _emit_state_transitions(
    state: dict[str, Any],
    provider_id: str,
    prev: dict[str, Any] | None,
    current: dict[str, Any],
) -> None:
    if not prev:
        if current.get("connected"):
            _record_brain("provider_connected", keyword=provider_id, result={"status": current.get("status")})
        return
    was_connected = bool(prev.get("connected"))
    now_connected = bool(current.get("connected"))
    prev_status = prev.get("status")
    now_status = current.get("status")
    if not was_connected and now_connected:
        _record_brain("provider_connected", keyword=provider_id, result={"status": now_status})
    elif was_connected and not now_connected:
        _record_brain("provider_disconnected", keyword=provider_id, reason=current.get("last_error") or "disconnected")
    if now_status in ("critical", "provider_missing") and prev_status not in ("critical", "provider_missing"):
        _record_brain("provider_error_detected", keyword=provider_id, result={"status": now_status, "error": current.get("last_error")})
        if get_settings().get("alert_on_critical"):
            _append_alert(state, {
                "alert_id": uuid.uuid4().hex[:12],
                "provider": provider_id,
                "type": "provider_error",
                "message": current.get("last_error") or f"{provider_id} critical",
                "status": now_status,
                "at": current.get("last_check"),
            })
    if prev_status in ("critical", "warning", "provider_missing") and now_status == "healthy":
        _record_brain("provider_health_restored", keyword=provider_id, result={"health_score": current.get("health_score")})


def check_provider(provider_id: str, *, persist: bool = True) -> dict[str, Any]:
    if provider_id not in PROVIDER_IDS:
        return {"success": False, "error": f"Unknown provider: {provider_id}"}
    checked_at = _now()
    probe_fn = PROBE_MAP.get(provider_id)
    probe = probe_fn() if probe_fn else {"status": "provider_missing", "connected": False, "configured": False}
    record = _build_provider_record(provider_id, probe, checked_at=checked_at)
    if persist:
        st = _load_state()
        prev = (st.get("providers") or {}).get(provider_id)
        st.setdefault("providers", {})[provider_id] = record
        _emit_state_transitions(st, provider_id, prev, record)
        _append_history(st, {"action": "check", "provider": provider_id, "status": record["status"], "at": checked_at})
        if record.get("last_error"):
            _append_activity(st, {
                "type": "error",
                "provider": provider_id,
                "message": record["last_error"],
                "at": checked_at,
            })
        last_action = (record.get("metadata") or {}).get("last_action") or {}
        if last_action:
            _append_activity(st, {
                "type": last_action.get("action") or "action",
                "provider": provider_id,
                "status": last_action.get("status"),
                "title": last_action.get("title"),
                "at": last_action.get("at") or checked_at,
            })
        _save_state(st)
    return {"success": True, "provider": record}


def check_all_providers(*, persist: bool = True) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for pid in PROVIDER_IDS:
        res = check_provider(pid, persist=False)
        results.append(res.get("provider") or {})
    if persist:
        st = _load_state()
        prev_map = dict(st.get("providers") or {})
        st["providers"] = {r["provider"]: r for r in results if r.get("provider")}
        st["last_full_check"] = _now()
        for rec in results:
            pid = rec.get("provider")
            if pid:
                _emit_state_transitions(st, pid, prev_map.get(pid), rec)
        _append_history(st, {"action": "full_check", "count": len(results), "at": st["last_full_check"]})
        _save_state(st)
    return {"success": True, "checked_at": _now(), "providers": results, "count": len(results)}


def list_providers(*, refresh: bool = False) -> dict[str, Any]:
    if refresh:
        check_all_providers(persist=True)
    st = _load_state()
    providers = st.get("providers") or {}
    if not providers:
        check_all_providers(persist=True)
        st = _load_state()
        providers = st.get("providers") or {}
    items = [providers[pid] for pid in PROVIDER_IDS if pid in providers]
    for pid in PROVIDER_IDS:
        if pid not in providers:
            items.append({
                "provider": pid,
                "label": PROVIDER_LABELS.get(pid, pid),
                "connected": False,
                "configured": False,
                "last_check": "",
                "last_success": "",
                "last_error": "",
                "health_score": 0,
                "status": "provider_missing",
                "quota": {},
                "metadata": {},
            })
    return {"success": True, "providers": items, "count": len(items)}


def get_provider(provider_id: str, *, refresh: bool = False) -> dict[str, Any]:
    if provider_id not in PROVIDER_IDS:
        return {"success": False, "error": f"Unknown provider: {provider_id}"}
    if refresh:
        return check_provider(provider_id, persist=True)
    st = _load_state()
    rec = (st.get("providers") or {}).get(provider_id)
    if not rec:
        return check_provider(provider_id, persist=True)
    return {"success": True, "provider": rec}


def _aggregate_health(providers: list[dict[str, Any]]) -> dict[str, Any]:
    if not providers:
        return {"health_score": 0, "connected": 0, "configured": 0, "failed": 0, "healthy": 0, "warning": 0, "critical": 0}
    scores = [int(p.get("health_score") or 0) for p in providers]
    connected = sum(1 for p in providers if p.get("connected"))
    configured = sum(1 for p in providers if p.get("configured"))
    failed = sum(1 for p in providers if p.get("status") in ("critical", "provider_missing"))
    healthy = sum(1 for p in providers if p.get("status") == "healthy")
    warning = sum(1 for p in providers if p.get("status") == "warning")
    critical = sum(1 for p in providers if p.get("status") in ("critical", "provider_missing"))
    return {
        "health_score": int(sum(scores) / max(len(scores), 1)),
        "connected": connected,
        "configured": configured,
        "failed": failed,
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
    }


def mission_control_payload() -> dict[str, Any]:
    lst = list_providers(refresh=False)
    providers = lst.get("providers") or []
    agg = _aggregate_health(providers)
    alerts = [p for p in providers if p.get("status") in ("critical", "provider_missing", "warning")][:8]
    return {
        "success": True,
        "provider_health_score": agg["health_score"],
        "connected_providers": agg["connected"],
        "configured_providers": agg["configured"],
        "failed_providers": agg["failed"],
        "healthy_providers": agg["healthy"],
        "warning_providers": agg["warning"],
        "critical_providers": agg["critical"],
        "provider_alerts": [
            {
                "provider": a.get("provider"),
                "label": a.get("label"),
                "status": a.get("status"),
                "message": a.get("last_error") or a.get("status"),
            }
            for a in alerts
        ],
        "last_full_check": _load_state().get("last_full_check", ""),
    }


def executive_risk_payload() -> dict[str, Any]:
    """Executive AI — provider risk katkısı."""
    lst = list_providers(refresh=False)
    providers = lst.get("providers") or []
    critical = [p for p in providers if p.get("status") in ("critical", "provider_missing")]
    warning = [p for p in providers if p.get("status") == "warning"]
    not_configured = [p for p in providers if p.get("status") == "not_configured"]
    risk_points = len(critical) * 12 + len(warning) * 5 + len(not_configured) * 2
    return {
        "success": True,
        "provider_risk_score": min(100, risk_points),
        "critical_providers": [p.get("provider") for p in critical],
        "warning_providers": [p.get("provider") for p in warning],
        "not_configured_providers": [p.get("provider") for p in not_configured],
        "provider_health_score": _aggregate_health(providers)["health_score"],
    }


def dashboard() -> dict[str, Any]:
    st = _load_state()
    lst = list_providers(refresh=False)
    providers = lst.get("providers") or []
    agg = _aggregate_health(providers)
    errors = [p for p in providers if p.get("last_error")]
    mc = mission_control_payload()
    return {
        "success": True,
        "module": "provider_control_center",
        "enabled": get_settings().get("enabled", True),
        "last_full_check": st.get("last_full_check", ""),
        "summary": agg,
        "providers_total": len(PROVIDER_IDS),
        "providers": providers,
        "errors": errors[:15],
        "alerts": (st.get("alerts") or [])[:15],
        "recent_activity": (st.get("recent_activity") or [])[:20],
        "mission_control": mc,
        "settings": get_settings(),
    }


def health() -> dict[str, Any]:
    dash = dashboard()
    return {
        "success": True,
        "module": "provider_control_center",
        "enabled": get_settings().get("enabled", True),
        "providers_total": len(PROVIDER_IDS),
        "provider_health_score": dash.get("summary", {}).get("health_score", 0),
        "connected_providers": dash.get("summary", {}).get("connected", 0),
        "failed_providers": dash.get("summary", {}).get("failed", 0),
        "last_full_check": dash.get("last_full_check", ""),
        "produces_content": False,
        "publishes": False,
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if report_type == "providers":
        payload = list_providers(refresh=True)
    elif report_type == "health":
        payload = {"health": health(), "providers": list_providers().get("providers", [])}
    else:
        payload = dashboard()
    path = REPORTS_DIR / f"provider-control-center-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}
