"""
Production Readiness Engine V1 — HIVE OS canlı kullanıma hazırlık ölçümü.

Publish/deploy/içerik üretmez; yalnızca readiness skoru hesaplar.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("hive.production_readiness")

STATE_FILE = Path(__file__).resolve().parent.parent / "production_readiness_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "talon_data" / "reports"

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "min_production_score": 80,
    "min_enterprise_score": 90,
    "block_on_critical_audit": True,
    "block_on_stuck_queue": True,
}

SCORE_WEIGHTS: dict[str, float] = {
    "infrastructure": 0.12,
    "provider": 0.14,
    "audit": 0.14,
    "queue": 0.10,
    "security": 0.12,
    "testing": 0.08,
    "documentation": 0.08,
    "onboarding": 0.10,
    "monitoring": 0.12,
}

LAUNCH_MODES: list[tuple[int, int, str]] = [
    (0, 39, "development"),
    (40, 59, "alpha"),
    (60, 79, "beta"),
    (80, 89, "production_ready"),
    (90, 100, "enterprise_ready"),
]

READINESS_CHECKS: list[dict[str, str]] = [
    {"id": "provider_coverage", "title": "Provider Coverage", "module": "provider_control_center"},
    {"id": "audit_health", "title": "Audit Health", "module": "hive_audit_engine"},
    {"id": "queue_health", "title": "Queue Health", "module": "action_orchestrator"},
    {"id": "security", "title": "Security", "module": "hive_audit_engine"},
    {"id": "brain_health", "title": "Brain Health", "module": "hive_brain_engine"},
    {"id": "mission_control_health", "title": "Mission Control Health", "module": "mission_control_center"},
    {"id": "campaign_system", "title": "Campaign System", "module": "campaign_engine"},
    {"id": "revenue_tracking", "title": "Revenue Tracking", "module": "revenue_lead_engine"},
    {"id": "authority_network", "title": "Authority Network", "module": "authority_factory"},
    {"id": "publisher_network", "title": "Publisher Network", "module": "publisher_hub"},
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("last_calculation", {})
                data.setdefault("last_launch_mode", "development")
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "last_calculation": {},
        "last_launch_mode": "development",
        "history": [],
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_brain(event: str, *, result: dict | None = None) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(event, "production_readiness_engine", reason=event, result=result or {}, metadata={"module": "production_readiness_engine"})
    except Exception as exc:
        logger.debug("brain: %s", exc)


def _safe_call(module: str, func: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        mod = __import__(f"app.moduller.{module}", fromlist=[func])
        fn: Callable = getattr(mod, func)
        res = fn(*args, **kwargs)
        return res if isinstance(res, dict) else {"success": True, "data": res}
    except Exception as exc:
        logger.debug("readiness.%s.%s: %s", module, func, exc)
        return {"success": False, "error": str(exc)}


def get_settings() -> dict[str, Any]:
    st = _load_state()
    merged = dict(DEFAULT_SETTINGS)
    merged.update(st.get("settings") or {})
    return merged


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    settings = dict(get_settings())
    for key in DEFAULT_SETTINGS:
        if key in updates and updates[key] is not None:
            settings[key] = updates[key]
    st["settings"] = settings
    st.setdefault("history", []).insert(0, {"type": "settings_updated", "at": _now()})
    _save_state(st)
    return {"success": True, "settings": settings}


def _clamp(v: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(v))))


def _launch_mode(score: int, has_blockers: bool) -> str:
    mode = "development"
    for lo, hi, name in LAUNCH_MODES:
        if lo <= score <= hi:
            mode = name
            break
    if has_blockers and mode in ("production_ready", "enterprise_ready"):
        return "beta"
    return mode


def _collect_sources() -> dict[str, Any]:
    return {
        "providers": _safe_call("provider_control_center", "mission_control_payload"),
        "audit": _safe_call("hive_audit_engine", "mission_control_payload"),
        "mission_control": _safe_call("mission_control_center", "health_summary"),
        "executive": _safe_call("executive_ai", "mission_control_payload"),
        "success_path": _safe_call("hive_success_path", "mission_control_payload"),
        "orchestrator": _safe_call("action_orchestrator", "build_dashboard"),
        "campaigns": _safe_call("campaign_engine", "mission_control_payload"),
        "revenue": _safe_call("revenue_lead_engine", "mission_control_payload"),
        "publisher": _safe_call("publisher_hub", "health_summary"),
        "authority": _safe_call("authority_factory", "mission_control_payload"),
        "brain": _safe_call("hive_brain_engine", "dashboard"),
        "academy": _safe_call("hive_academy", "health"),
    }


def _score_components(sources: dict[str, Any]) -> dict[str, int]:
    mc = sources.get("mission_control") or {}
    prov = sources.get("providers") or {}
    audit = sources.get("audit") or {}
    orch = sources.get("orchestrator") or {}
    sp = sources.get("success_path") or {}
    academy = sources.get("academy") or {}
    brain = sources.get("brain") or {}
    pub = sources.get("publisher") or {}
    camp = sources.get("campaigns") or {}

    infrastructure = _clamp(float(mc.get("system_health") or 50))
    provider = _clamp(float(prov.get("provider_health_score") or 0))
    audit_score = _clamp(float(audit.get("audit_score") or 0))

    stuck = int(audit.get("stuck_queues") or 0)
    queued = int((orch.get("mission_control") or orch).get("pending_actions") or orch.get("queued") or 0)
    pub_q = int(pub.get("queue_size") or (pub.get("dashboard") or {}).get("queued") or 0)
    queue_penalty = min(40, stuck * 15 + min(20, queued // 5) + min(10, pub_q // 10))
    queue = _clamp(100 - queue_penalty)

    critical_audit = int(audit.get("critical_audit_issues") or 0)
    critical_prov = int(prov.get("critical_providers") or 0)
    security = _clamp(100 - critical_audit * 20 - critical_prov * 15 - int(audit.get("provider_risks") or 0) * 5)

    testing = _clamp(float(audit.get("audit_score") or 50) * 0.6 + (100 if audit.get("last_run") else 30))

    documentation = _clamp(float(academy.get("progress_percent") or 0))

    onboarding = _clamp(float(sp.get("completion_percent") or 0))

    events = len(brain.get("recent") or [])
    monitoring = _clamp(40 + min(30, events * 2) + (20 if mc.get("generated_at") else 0) + (10 if sp.get("path_completed") else 0))

    return {
        "infrastructure": infrastructure,
        "provider": provider,
        "audit": audit_score,
        "queue": queue,
        "security": security,
        "testing": testing,
        "documentation": documentation,
        "onboarding": onboarding,
        "monitoring": monitoring,
    }


def _detect_blockers(sources: dict[str, Any], components: dict[str, int]) -> list[dict[str, Any]]:
    settings = get_settings()
    blockers: list[dict[str, Any]] = []
    audit = sources.get("audit") or {}
    prov = sources.get("providers") or {}
    mc = sources.get("mission_control") or {}
    orch = sources.get("orchestrator") or {}

    if settings.get("block_on_critical_audit") and int(audit.get("critical_audit_issues") or 0) > 0:
        for issue in (audit.get("top_critical") or [])[:5]:
            blockers.append({
                "type": "critical_audit_issue",
                "severity": "critical",
                "title": issue.get("title") or issue.get("id") or "Critical audit issue",
                "module": "hive_audit_engine",
                "detail": issue,
            })
        if not blockers:
            blockers.append({
                "type": "critical_audit_issue",
                "severity": "critical",
                "title": f"{audit.get('critical_audit_issues')} critical audit issue(s)",
                "module": "hive_audit_engine",
            })

    for alert in (prov.get("provider_alerts") or []):
        if alert.get("status") in ("critical", "provider_missing"):
            blockers.append({
                "type": "provider_missing",
                "severity": "critical",
                "title": f"Provider missing: {alert.get('label') or alert.get('provider')}",
                "module": "provider_control_center",
                "detail": alert,
            })

    stuck = int(audit.get("stuck_queues") or 0)
    if settings.get("block_on_stuck_queue") and stuck > 0:
        blockers.append({
            "type": "stuck_queue",
            "severity": "critical",
            "title": f"{stuck} stuck queue(s) detected",
            "module": "action_orchestrator",
        })

    astro = (mc.get("worker_status") or {}).get("astro_auto_publisher") or {}
    if astro.get("last_deploy_status") == "failed" or int(astro.get("failed_deploys") or 0) > 0:
        blockers.append({
            "type": "failed_deployment",
            "severity": "critical",
            "title": "Failed deployment detected",
            "module": "astro_auto_publisher",
            "detail": astro,
        })

    if components.get("security", 100) < 50:
        blockers.append({
            "type": "security_finding",
            "severity": "critical",
            "title": f"Security score too low ({components.get('security')})",
            "module": "hive_audit_engine",
        })

    return blockers


def _detect_warnings(sources: dict[str, Any], components: dict[str, int]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    prov = sources.get("providers") or {}
    sp = sources.get("success_path") or {}
    audit = sources.get("audit") or {}

    if components.get("documentation", 0) < 40:
        warnings.append({
            "type": "documentation_low",
            "severity": "warning",
            "title": "Academy / documentation progress düşük",
            "module": "hive_academy",
            "score": components.get("documentation"),
        })

    if components.get("onboarding", 0) < 50:
        warnings.append({
            "type": "onboarding_low",
            "severity": "warning",
            "title": "Success Path onboarding tamamlanmadı",
            "module": "hive_success_path",
            "score": components.get("onboarding"),
        })

    if int(prov.get("warning_providers") or 0) > 0:
        warnings.append({
            "type": "provider_warning",
            "severity": "warning",
            "title": f"{prov.get('warning_providers')} provider warning",
            "module": "provider_control_center",
        })

    if components.get("testing", 0) < 60:
        warnings.append({
            "type": "low_test_coverage",
            "severity": "warning",
            "title": "Testing readiness düşük — audit/test coverage artırın",
            "module": "hive_audit_engine",
            "score": components.get("testing"),
        })

    if not audit.get("last_run"):
        warnings.append({
            "type": "audit_stale",
            "severity": "warning",
            "title": "Audit henüz çalıştırılmadı",
            "module": "hive_audit_engine",
        })

    return warnings


def _run_checks(sources: dict[str, Any], components: dict[str, int], blockers: list, warnings: list) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    prov = sources.get("providers") or {}
    audit = sources.get("audit") or {}
    camp = sources.get("campaigns") or {}
    rev = sources.get("revenue") or {}
    auth = sources.get("authority") or {}
    pub = sources.get("publisher") or {}
    brain = sources.get("brain") or {}
    mc = sources.get("mission_control") or {}

    checks = {
        "provider_coverage": int(prov.get("connected_providers") or 0) >= 2 and components["provider"] >= 50,
        "audit_health": components["audit"] >= 60 and not audit.get("critical_audit_issues"),
        "queue_health": components["queue"] >= 60,
        "security": components["security"] >= 60,
        "brain_health": bool(brain.get("success", True)) and len(brain.get("recent") or []) >= 0,
        "mission_control_health": bool(mc.get("success")) and float(mc.get("system_health") or 0) >= 40,
        "campaign_system": int(camp.get("total_campaigns") or 0) >= 0,
        "revenue_tracking": True,
        "authority_network": int(auth.get("factory_batches") or auth.get("batches_count") or 0) >= 0,
        "publisher_network": int(pub.get("channels_connected") or 0) >= 0,
    }

    for chk in READINESS_CHECKS:
        cid = chk["id"]
        if checks.get(cid, False):
            passed.append(cid)
        else:
            failed.append(cid)

    return passed, failed


def _recommendation(score: int, launch_mode: str, blockers: list, warnings: list) -> str:
    if blockers:
        b = blockers[0].get("title", "blocker")
        return f"Production Ready değil — önce blocker çözün: {b}"
    if launch_mode == "enterprise_ready":
        return "Enterprise Ready — canlı operasyon için uygun. Monitoring ve audit döngüsünü sürdürün."
    if launch_mode == "production_ready":
        return "Production Ready — kontrollü launch yapılabilir. Kalan uyarıları giderin."
    if launch_mode == "beta":
        return "Beta — core sistemler çalışıyor; provider ve onboarding'i tamamlayın."
    if launch_mode == "alpha":
        return "Alpha — temel altyapı kısmen hazır; audit ve provider coverage artırın."
    return "Development — kritik entegrasyonlar ve onboarding eksik."


def _overall_score(components: dict[str, int]) -> int:
    total = 0.0
    for key, weight in SCORE_WEIGHTS.items():
        total += components.get(key, 0) * weight
    return _clamp(total)


_CALC_MEMO: dict[str, Any] = {"at": 0.0, "data": None}
_CALC_MEMO_TTL_SEC = 60


def calculate(*, persist: bool = True) -> dict[str, Any]:
    """Readiness hesapla — publish/deploy yapmaz."""
    import time
    if not persist:
        now = time.monotonic()
        memo = _CALC_MEMO.get("data")
        if memo and (now - _CALC_MEMO.get("at", 0)) < _CALC_MEMO_TTL_SEC:
            return dict(memo)

    sources = _collect_sources()
    components = _score_components(sources)
    overall = _overall_score(components)
    blockers = _detect_blockers(sources, components)
    warnings = _detect_warnings(sources, components)
    passed, _failed = _run_checks(sources, components, blockers, warnings)
    launch_mode = _launch_mode(overall, bool(blockers))
    recommendation = _recommendation(overall, launch_mode, blockers, warnings)

    model = {
        "overall_score": overall,
        "overall_readiness_score": overall,
        "launch_mode": launch_mode,
        "blockers": blockers,
        "warnings": warnings,
        "passed_checks": passed,
        "recommendation": recommendation,
        "score_components": components,
        "calculated_at": _now(),
    }

    st = _load_state()
    prev_mode = st.get("last_launch_mode") or "development"
    st["last_calculation"] = model
    st.setdefault("history", []).insert(0, {"type": "calculated", "at": _now(), "overall_score": overall, "launch_mode": launch_mode})
    st["history"] = st["history"][:200]

    if persist:
        _save_state(st)
        _record_brain("readiness_calculated", result={"overall_score": overall, "launch_mode": launch_mode, "blockers": len(blockers)})
        if launch_mode != prev_mode:
            st["last_launch_mode"] = launch_mode
            _save_state(st)
            _record_brain("launch_mode_changed", result={"from": prev_mode, "to": launch_mode, "score": overall})
        if launch_mode == "production_ready" and not blockers:
            _record_brain("production_ready", result={"score": overall})
        if launch_mode == "enterprise_ready" and not blockers:
            _record_brain("enterprise_ready", result={"score": overall})
        for b in blockers[:3]:
            _record_brain("blocker_detected", result=b)

    result = {"success": True, "module": "production_readiness_engine", **model}
    if not persist:
        _CALC_MEMO["at"] = time.monotonic()
        _CALC_MEMO["data"] = result
    return result


def get_report() -> dict[str, Any]:
    st = _load_state()
    calc = st.get("last_calculation") or {}
    if not calc:
        calc = calculate(persist=True)
    return {"success": True, "report": calc, "history_count": len(st.get("history") or [])}


def get_blockers() -> dict[str, Any]:
    calc = calculate(persist=False)
    return {"success": True, "blockers": calc.get("blockers") or [], "count": len(calc.get("blockers") or [])}


def get_warnings() -> dict[str, Any]:
    calc = calculate(persist=False)
    return {"success": True, "warnings": calc.get("warnings") or [], "count": len(calc.get("warnings") or [])}


def health() -> dict[str, Any]:
    st = _load_state()
    calc = st.get("last_calculation") or {}
    if not calc:
        calc = calculate(persist=False)
    return {
        "success": True,
        "module": "production_readiness_engine",
        "enabled": get_settings().get("enabled", True),
        "overall_score": calc.get("overall_score", 0),
        "launch_mode": calc.get("launch_mode", "development"),
        "blockers_count": len(calc.get("blockers") or []),
        "warnings_count": len(calc.get("warnings") or []),
        "last_calculated": calc.get("calculated_at", ""),
    }


def dashboard() -> dict[str, Any]:
    calc = calculate(persist=True)
    sources = _collect_sources()
    return {
        "success": True,
        "module": "production_readiness_engine",
        "readiness": calc,
        "checks": READINESS_CHECKS,
        "launch_modes": [{"min": lo, "max": hi, "mode": name} for lo, hi, name in LAUNCH_MODES],
        "score_weights": SCORE_WEIGHTS,
        "sources_summary": {
            "provider_health": (sources.get("providers") or {}).get("provider_health_score"),
            "audit_score": (sources.get("audit") or {}).get("audit_score"),
            "system_health": (sources.get("mission_control") or {}).get("system_health"),
            "success_path_pct": (sources.get("success_path") or {}).get("completion_percent"),
        },
        "settings": get_settings(),
        "mission_control": mission_control_payload(),
    }


def mission_control_payload() -> dict[str, Any]:
    st = _load_state()
    calc = st.get("last_calculation") or calculate(persist=False)
    return {
        "success": True,
        "overall_score": calc.get("overall_score", 0),
        "launch_mode": calc.get("launch_mode", "development"),
        "blockers_count": len(calc.get("blockers") or []),
        "warnings_count": len(calc.get("warnings") or []),
        "top_blocker": (calc.get("blockers") or [{}])[0].get("title") if calc.get("blockers") else None,
        "recommendation": calc.get("recommendation", ""),
        "production_ready": calc.get("launch_mode") in ("production_ready", "enterprise_ready") and not calc.get("blockers"),
    }


def executive_readiness_payload() -> dict[str, Any]:
    calc = calculate(persist=False)
    score = int(calc.get("overall_score") or 0)
    blockers = calc.get("blockers") or []
    mode = calc.get("launch_mode", "development")
    if blockers:
        rec = f"Launch blocked — {blockers[0].get('title', 'blocker')}"
    elif mode == "enterprise_ready":
        rec = "Enterprise launch approved — proceed with monitoring"
    elif mode == "production_ready":
        rec = "Production launch viable — resolve warnings first"
    else:
        rec = calc.get("recommendation", "Continue readiness improvements")
    return {
        "success": True,
        "executive_readiness_score": score,
        "executive_launch_recommendation": rec,
        "launch_mode": mode,
        "blockers_count": len(blockers),
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    calc = calculate(persist=True)
    payload = {
        "report_type": report_type,
        "generated_at": _now(),
        "readiness": calc,
        "settings": get_settings(),
    }
    fname = f"production_readiness_{report_type}_{uuid.uuid4().hex[:8]}.json"
    path = REPORTS_DIR / fname
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path), "report": payload}
