"""
HIVE Audit Engine V1 — merkezi denetim ve risk raporlama katmanı.

SEO motoru değildir; publish/deploy yapmaz.
Modülleri, API/frontend route'ları, provider'ları, state ve queue'ları okur, raporlar.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.hive_audit_engine")

APP_DIR = Path(__file__).resolve().parent.parent
MODULLER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent.parent
TESTS_DIR = PROJECT_ROOT / "backend" / "tests"
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
MAIN_PY = APP_DIR / "main.py"
NAV_JS = FRONTEND_SRC / "config" / "hiveOsNav.js"
ROUTES_JS = FRONTEND_SRC / "config" / "hiveOsRoutes.js"
APP_JS = FRONTEND_SRC / "App.js"

STATE_FILE = APP_DIR / "hive_audit_engine_state.json"
REPORTS_DIR = PROJECT_ROOT / "backend" / "reports"

ISSUE_LIMIT = 2000
HISTORY_LIMIT = 200
REPORT_LIMIT = 50

ISSUE_CATEGORIES = ("module", "api", "frontend", "provider", "state", "queue", "test", "security")
SEVERITIES = ("info", "warning", "critical")

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "auto_run_on_startup": False,
    "stale_state_days": 30,
    "stale_provider_check_hours": 48,
    "stuck_queue_hours": 6,
    "large_state_mb": 5,
    "alert_on_critical": True,
}

PUBLIC_API_PATHS = frozenset({
    "/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico",
    "/api/talon/health", "/api/revenue-leads/track", "/api/revenue-leads/track-redirect",
})

HIVE_OS_MODULE_IDS = frozenset({
    "mission_control_center", "hive_brain_engine", "executive_ai", "autonomous_seo_agent",
    "action_orchestrator", "talon", "rank_index_watcher", "serp_defense_engine",
    "opportunity_engine", "citation_engine", "crawl_gap_engine", "question_intelligence_engine",
    "content_refresh_engine", "astro_factory", "astro_auto_publisher", "publisher_hub",
    "authority_mesh_engine", "authority_factory", "revenue_lead_engine", "support_network_engine",
    "network_replicator", "site_replicator", "hive_academy", "hive_mentor", "first_run_wizard",
    "provider_control_center", "hive_audit_engine", "seo_quality_gate", "listing_hub",
    "hive_success_path", "campaign_engine", "production_readiness_engine",
    "entity_geo_graph", "place_seo_pipeline", "entity_detail_generator",
})

QUEUE_MODULES: dict[str, dict[str, Any]] = {
    "action_orchestrator": {
        "state": "action_orchestrator_state.json",
        "keys": [("actions", "status"), ("pipelines", "status")],
        "stuck_statuses": ("processing", "running", "queued"),
    },
    "publisher_hub": {
        "state": "publisher_hub_state.json",
        "keys": [("queue", "status"), ("drafts", "status")],
        "stuck_statuses": ("queued", "processing", "review_required"),
    },
    "authority_factory": {
        "state": "authority_factory_state.json",
        "nested": "batches.items",
        "stuck_statuses": ("processing", "queued", "login_required"),
    },
    "google_sites_worker": {
        "state": "google_sites_worker_state.json",
        "keys": [("tasks", "status")],
        "stuck_statuses": ("processing", "queued", "login_required"),
    },
    "github_pages_worker": {
        "state": "github_pages_worker_state.json",
        "keys": [("sites", "status")],
        "stuck_statuses": ("processing", "queued", "deploying"),
    },
    "astro_auto_publisher": {
        "state": "astro_auto_publisher_state.json",
        "keys": [("queue", "status"), ("processing", "status")],
        "stuck_statuses": ("processing", "queued", "building"),
    },
    "content_refresh_engine": {
        "state": "content_refresh_engine_state.json",
        "keys": [("queue", "status"), ("refresh_queue", "status")],
        "stuck_statuses": ("processing", "queued", "scheduled"),
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value.replace("+00:00", "").strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("issues", [])
                data.setdefault("reports", [])
                data.setdefault("scores", {})
                data.setdefault("last_run", "")
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "issues": [],
        "reports": [],
        "scores": {},
        "last_run": "",
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
        if k in DEFAULT_SETTINGS:
            cur[k] = v
    _save_state(st)
    return dict(cur)


def _record_brain(event_type: str, *, keyword: str = "", result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event_type,
            "hive_audit_engine",
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "hive_audit_engine", "audit_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _make_issue(
    category: str,
    severity: str,
    title: str,
    description: str = "",
    *,
    affected_file: str = "",
    affected_module: str = "",
    recommended_fix: str = "",
) -> dict[str, Any]:
    return {
        "issue_id": f"audit-{uuid.uuid4().hex[:10]}",
        "category": category,
        "severity": severity if severity in SEVERITIES else "info",
        "title": title,
        "description": description,
        "affected_file": affected_file,
        "affected_module": affected_module,
        "recommended_fix": recommended_fix,
        "status": "open",
        "created_at": _now(),
        "updated_at": _now(),
    }


def _score_from_issues(issues: list[dict[str, Any]], category: str | None = None) -> int:
    subset = [i for i in issues if i.get("status") != "resolved" and (category is None or i.get("category") == category)]
    score = 100
    for issue in subset:
        sev = issue.get("severity", "info")
        if sev == "critical":
            score -= 8
        elif sev == "warning":
            score -= 3
        else:
            score -= 1
    return max(0, min(100, score))


def _compute_scores(issues: list[dict[str, Any]]) -> dict[str, Any]:
    open_issues = [i for i in issues if i.get("status") != "resolved"]
    scores = {
        "module_score": _score_from_issues(open_issues, "module"),
        "api_score": _score_from_issues(open_issues, "api"),
        "frontend_score": _score_from_issues(open_issues, "frontend"),
        "provider_score": _score_from_issues(open_issues, "provider"),
        "state_score": _score_from_issues(open_issues, "state"),
        "queue_score": _score_from_issues(open_issues, "queue"),
        "test_score": _score_from_issues(open_issues, "test"),
        "security_score": _score_from_issues(open_issues, "security"),
    }
    vals = list(scores.values())
    scores["overall_audit_score"] = int(sum(vals) / max(len(vals), 1))
    scores["open_issues"] = len(open_issues)
    scores["critical_issues"] = sum(1 for i in open_issues if i.get("severity") == "critical")
    scores["warning_issues"] = sum(1 for i in open_issues if i.get("severity") == "warning")
    return scores


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _parse_main_routes() -> list[dict[str, str]]:
    text = _read_text(MAIN_PY)
    routes: list[dict[str, str]] = []
    for m in re.finditer(r'@app\.(get|post|put|delete|patch)\("([^"]+)"', text):
        routes.append({"method": m.group(1).upper(), "path": m.group(2)})
    return routes


def _registered_modules() -> list[dict[str, Any]]:
    try:
        from app.moduller.liste import MODULLER, MODUL_ENDPOINTS
        return [{"id": m["id"], "endpoint": MODUL_ENDPOINTS.get(m["id"], f"/api/{m['id']}/health"), **m} for m in MODULLER]
    except Exception:
        return []


def _nav_ids() -> set[str]:
    text = _read_text(NAV_JS)
    return set(re.findall(r'\bid:\s*"([^"]+)"', text))


def _route_map() -> dict[str, str]:
    text = _read_text(ROUTES_JS)
    pairs = re.findall(r'(\w+):\s*"([^"]+)"', text)
    return {k: v for k, v in pairs if not k.startswith("export")}


def _app_gosterge_ids() -> set[str]:
    text = _read_text(APP_JS)
    return set(re.findall(r'gosterge\s*===\s*"([^"]+)"', text))


def _test_files() -> dict[str, int]:
    out: dict[str, int] = {}
    if not TESTS_DIR.exists():
        return out
    for path in TESTS_DIR.glob("test_*.py"):
        name = path.stem.replace("test_", "")
        try:
            content = path.read_text(encoding="utf-8")
            count = len(re.findall(r"^\s*def test_", content, re.MULTILINE))
        except OSError:
            count = 0
        out[name] = count
    return out


def _state_files() -> list[Path]:
    return sorted(APP_DIR.glob("*_state.json"))


def _module_py_exists(module_id: str) -> bool:
    candidates = [
        MODULLER_DIR / f"{module_id}.py",
        MODULLER_DIR / f"{module_id.replace('-', '_')}.py",
    ]
    return any(p.exists() for p in candidates)


def audit_modules() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    modules = _registered_modules()
    nav_ids = _nav_ids()
    routes = _parse_main_routes()
    route_paths = {r["path"] for r in routes}
    tests = _test_files()
    state_names = {p.stem.replace("_state", "") for p in _state_files()}

    for mod in modules:
        mid = mod["id"]
        endpoint = mod.get("endpoint", "")
        py_exists = _module_py_exists(mid)

        if not py_exists and mid in HIVE_OS_MODULE_IDS:
            issues.append(_make_issue(
                "module", "warning", f"Modül dosyası eksik: {mid}",
                f"{mid}.py bulunamadı",
                affected_module=mid,
                recommended_fix=f"backend/app/moduller/{mid}.py oluşturun veya liste.py'den kaldırın",
            ))

        if endpoint and endpoint not in route_paths:
            has_health_variant = any("/health" in r["path"] and mid.replace("_", "-") in r["path"] for r in routes)
            if not has_health_variant:
                issues.append(_make_issue(
                    "module", "warning", f"Health endpoint kayıtlı ama route yok: {mid}",
                    f"Beklenen: {endpoint}",
                    affected_module=mid,
                    affected_file="backend/app/main.py",
                    recommended_fix=f"main.py'ye {endpoint} route ekleyin",
                ))

        if mid in HIVE_OS_MODULE_IDS and mid not in nav_ids:
            issues.append(_make_issue(
                "module", "info", f"HIVE OS sidebar'da yok: {mid}",
                "Modül kayıtlı ama hiveOsNav.js'de görünmüyor",
                affected_module=mid,
                affected_file="frontend/src/config/hiveOsNav.js",
                recommended_fix="hiveOsNav.js'e sidebar item ekleyin",
            ))

        test_key = mid.replace("-", "_")
        test_count = tests.get(test_key, 0)
        for alt in (mid, mid.replace("_engine", ""), mid.replace("_", "")):
            if alt in tests:
                test_count = max(test_count, tests[alt])
        if mid in HIVE_OS_MODULE_IDS and test_count == 0:
            issues.append(_make_issue(
                "test", "warning", f"Test dosyası yok: {mid}",
                f"backend/tests/test_{test_key}.py bulunamadı",
                affected_module=mid,
                recommended_fix=f"test_{test_key}.py oluşturun",
            ))

        state_key = mid.replace("-", "_")
        if state_key in HIVE_OS_MODULE_IDS and state_key not in state_names:
            issues.append(_make_issue(
                "state", "info", f"State dosyası yok: {mid}",
                f"{state_key}_state.json bulunamadı (opsiyonel olabilir)",
                affected_module=mid,
                affected_file=f"backend/app/{state_key}_state.json",
            ))

    return issues


def audit_api() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    routes = _parse_main_routes()
    seen: dict[str, list[str]] = {}
    for r in routes:
        key = f"{r['method']}:{r['path']}"
        seen.setdefault(key, []).append(r["path"])

    for key, paths in seen.items():
        if len(paths) > 1:
            issues.append(_make_issue(
                "api", "critical", f"Duplicate route: {key}",
                "Aynı method+path birden fazla kez tanımlı",
                affected_file="backend/app/main.py",
                recommended_fix="Duplicate route tanımını kaldırın",
            ))

    for path in PUBLIC_API_PATHS:
        if path.startswith("/api/") and "track" in path:
            issues.append(_make_issue(
                "security", "warning", f"Public API endpoint: {path}",
                "API key middleware'den muaf — rate limit kontrol edin",
                affected_file="backend/app/main.py",
                recommended_fix="Rate limiting ve abuse koruması ekleyin",
            ))

    hive_modules = _registered_modules()
    health_paths = {r["path"] for r in routes if "/health" in r["path"]}
    for mod in hive_modules:
        if mod["id"] not in HIVE_OS_MODULE_IDS:
            continue
        ep = mod.get("endpoint", "")
        if ep and "/health" in ep and ep not in health_paths:
            issues.append(_make_issue(
                "api", "warning", f"Missing health route: {mod['id']}",
                f"liste.py endpoint {ep} main.py'de yok",
                affected_module=mod["id"],
                affected_file="backend/app/main.py",
            ))

    api_prefixes = sorted({r["path"].split("/")[2] if len(r["path"].split("/")) > 2 else "" for r in routes if r["path"].startswith("/api/")})
    modules_with_routes = set()
    for mod in hive_modules:
        prefix = mod["id"].replace("_", "-")
        if any(prefix in r["path"] for r in routes):
            modules_with_routes.add(mod["id"])
    for mid in HIVE_OS_MODULE_IDS:
        prefix = mid.replace("_", "-")
        if mid not in modules_with_routes and _module_py_exists(mid):
            if not any(prefix in r["path"] or mid in r["path"] for r in routes):
                issues.append(_make_issue(
                    "api", "info", f"Modül API route eksik: {mid}",
                    f"/api/{prefix}/* route bulunamadı",
                    affected_module=mid,
                    recommended_fix="main.py'ye modül API route'ları ekleyin",
                ))

    if len(routes) == 0:
        issues.append(_make_issue(
            "api", "critical", "main.py route parse edilemedi",
            "Hiç route bulunamadı",
            affected_file="backend/app/main.py",
        ))

    return issues


def audit_frontend() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    nav_ids = _nav_ids()
    route_map = _route_map()
    app_ids = _app_gosterge_ids()

    for nav_id in nav_ids:
        if nav_id in route_map and nav_id not in app_ids:
            issues.append(_make_issue(
                "frontend", "warning", f"Route var ama App.js component yok: {nav_id}",
                f"hiveOsRoutes: {route_map[nav_id]}",
                affected_module=nav_id,
                affected_file="frontend/src/App.js",
                recommended_fix=f'App.js\'e gosterge === "{nav_id}" handler ekleyin',
            ))

    for route_id, path in route_map.items():
        if route_id not in nav_ids:
            issues.append(_make_issue(
                "frontend", "info", f"Route tanımlı ama sidebar'da yok: {route_id}",
                f"Path: {path}",
                affected_module=route_id,
                affected_file="frontend/src/config/hiveOsNav.js",
            ))
        if route_id not in app_ids:
            issues.append(_make_issue(
                "frontend", "critical", f"Broken route — component eksik: {route_id}",
                f"{path} için App.js handler yok",
                affected_module=route_id,
                affected_file="frontend/src/App.js",
                recommended_fix="Component import ve render ekleyin",
            ))

    for nav_id in nav_ids:
        if nav_id in HIVE_OS_MODULE_IDS and nav_id in route_map and nav_id not in app_ids:
            issues.append(_make_issue(
                "frontend", "critical", f"HIVE OS dead page: {nav_id}",
                "Sidebar + route var ama sayfa render edilmiyor",
                affected_module=nav_id,
            ))

    pcc_page = FRONTEND_SRC / "pages" / "ProviderControlCenter.js"
    if "provider_control_center" in nav_ids and not pcc_page.exists():
        issues.append(_make_issue(
            "frontend", "critical", "ProviderControlCenter.js eksik",
            "Sidebar kayıtlı ama page component yok",
            affected_file=str(pcc_page),
        ))

    return issues


def audit_providers() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    settings = get_settings()
    stale_hours = int(settings.get("stale_provider_check_hours") or 48)
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_hours)

    try:
        from app.moduller.provider_control_center import list_providers
        data = list_providers(refresh=False)
        providers = data.get("providers") or []
    except Exception as exc:
        issues.append(_make_issue(
            "provider", "critical", "Provider Control Center okunamadı",
            str(exc),
            affected_module="provider_control_center",
            recommended_fix="provider_control_center modülünü kontrol edin",
        ))
        return issues

    for p in providers:
        pid = p.get("provider", "")
        status = p.get("status", "")
        label = p.get("label", pid)
        tokens = (p.get("metadata") or {}).get("tokens") or {}
        token_present = tokens.get("token_present", False)

        if status == "provider_missing":
            issues.append(_make_issue(
                "provider", "critical", f"Provider missing: {label}",
                p.get("last_error") or "Modül/probe erişilemiyor",
                affected_module=pid,
                recommended_fix="Provider worker veya API credential yapılandırın",
            ))
        elif status == "not_configured":
            issues.append(_make_issue(
                "provider", "warning", f"Provider not configured: {label}",
                "Token veya credential eksik",
                affected_module=pid,
                recommended_fix="API Settings'ten credential girin",
            ))
        elif status == "critical":
            issues.append(_make_issue(
                "provider", "critical", f"Provider critical: {label}",
                p.get("last_error") or "Bağlantı/hata durumu",
                affected_module=pid,
            ))
        elif status == "warning":
            issues.append(_make_issue(
                "provider", "warning", f"Provider warning: {label}",
                p.get("last_error") or "Kısmi sorun",
                affected_module=pid,
            ))

        if not token_present and status not in ("healthy",) and pid not in ("wordpress",):
            masked = tokens.get("tokens_masked") or []
            if not masked:
                issues.append(_make_issue(
                    "provider", "info", f"Token yok: {label}",
                    "Credential tanımlı değil",
                    affected_module=pid,
                ))

        if p.get("last_error"):
            issues.append(_make_issue(
                "provider", "warning", f"Son provider hatası: {label}",
                p.get("last_error", ""),
                affected_module=pid,
            ))

        last_check = _parse_dt(p.get("last_check") or "")
        if last_check and last_check < stale_cutoff:
            issues.append(_make_issue(
                "provider", "info", f"Uzun süredir kontrol edilmemiş: {label}",
                f"Son kontrol: {p.get('last_check')}",
                affected_module=pid,
                recommended_fix="Provider Control Center'dan check çalıştırın",
            ))

    return issues


def audit_states() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    settings = get_settings()
    large_mb = float(settings.get("large_state_mb") or 5)
    stale_days = int(settings.get("stale_state_days") or 30)
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)

    seen_names: dict[str, list[str]] = {}
    for path in _state_files():
        name = path.name
        base = name.replace("_state.json", "")
        seen_names.setdefault(base, []).append(str(path))

        size_mb = path.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            issues.append(_make_issue(
                "state", "critical", f"Bozuk JSON state: {name}",
                str(exc),
                affected_file=str(path),
                recommended_fix="State dosyasını yedekleyip düzeltin veya sıfırlayın",
            ))
            continue
        except OSError as exc:
            issues.append(_make_issue(
                "state", "warning", f"State okunamadı: {name}",
                str(exc),
                affected_file=str(path),
            ))
            continue

        if size_mb > large_mb:
            issues.append(_make_issue(
                "state", "warning", f"Çok büyük state: {name}",
                f"{size_mb:.1f} MB (limit {large_mb} MB)",
                affected_file=str(path),
                recommended_fix="Eski kayıtları temizleyin veya arşivleyin",
            ))

        if isinstance(data, dict) and len(data) <= 1:
            issues.append(_make_issue(
                "state", "info", f"Empty/minimal state: {name}",
                "State neredeyse boş",
                affected_file=str(path),
            ))

        if mtime < stale_cutoff:
            issues.append(_make_issue(
                "state", "info", f"Stale state: {name}",
                f"Son değişiklik: {mtime.strftime('%Y-%m-%d')}",
                affected_file=str(path),
            ))

        if isinstance(data, dict):
            for key in ("history", "events", "reports", "issues"):
                arr = data.get(key)
                if isinstance(arr, list) and len(arr) > 5000:
                    issues.append(_make_issue(
                        "state", "warning", f"State array çok büyük: {name}.{key}",
                        f"{len(arr)} kayıt",
                        affected_file=str(path),
                    ))

    for base, paths in seen_names.items():
        if len(paths) > 1:
            issues.append(_make_issue(
                "state", "warning", f"Duplicate state pattern: {base}",
                f"{len(paths)} dosya",
                affected_file=", ".join(paths),
            ))

    moduler_states = {p.stem.replace("_state", "") for p in _state_files()}
    for mid in HIVE_OS_MODULE_IDS:
        sk = mid.replace("-", "_")
        py = MODULLER_DIR / f"{sk}.py"
        if py.exists() and sk not in moduler_states and (APP_DIR / f"{sk}_state.json").exists() is False:
            pass  # optional — only flag if module references STATE_FILE

    return issues


def _queue_items_from_state(module_id: str, spec: dict[str, Any], data: dict) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if spec.get("nested") == "batches.items":
        for batch in data.get("batches") or []:
            for it in batch.get("items") or []:
                items.append({**it, "_batch_id": batch.get("batch_id")})
        return items
    for key, status_field in spec.get("keys") or []:
        for it in data.get(key) or []:
            if isinstance(it, dict):
                items.append(it)
    return items


def audit_queues() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    settings = get_settings()
    stuck_hours = int(settings.get("stuck_queue_hours") or 6)
    stuck_cutoff = datetime.now(timezone.utc) - timedelta(hours=stuck_hours)

    for module_id, spec in QUEUE_MODULES.items():
        path = APP_DIR / spec["state"]
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            issues.append(_make_issue(
                "queue", "critical", f"Queue state okunamadı: {module_id}",
                spec["state"],
                affected_module=module_id,
                affected_file=str(path),
            ))
            continue

        items = _queue_items_from_state(module_id, spec, data)
        stuck_statuses = set(spec.get("stuck_statuses") or ())

        for it in items:
            status = (it.get("status") or "").lower()
            if status == "failed":
                issues.append(_make_issue(
                    "queue", "warning", f"Failed queue item: {module_id}",
                    it.get("title") or it.get("id") or it.get("source_id") or status,
                    affected_module=module_id,
                    affected_file=spec["state"],
                ))
            if status == "login_required":
                issues.append(_make_issue(
                    "queue", "warning", f"Login required item: {module_id}",
                    it.get("title") or it.get("error") or "login_required",
                    affected_module=module_id,
                ))
            if "provider_missing" in (it.get("error") or "").lower() or status == "provider_missing":
                issues.append(_make_issue(
                    "queue", "critical", f"Provider missing queue item: {module_id}",
                    it.get("error") or "provider_missing",
                    affected_module=module_id,
                ))
            if status in stuck_statuses:
                ts = _parse_dt(it.get("updated_at") or it.get("started_at") or it.get("created_at") or "")
                if ts and ts < stuck_cutoff:
                    issues.append(_make_issue(
                        "queue", "critical", f"Stuck queue item: {module_id}",
                        f"Status={status}, since {ts.strftime('%Y-%m-%d %H:%M')}",
                        affected_module=module_id,
                        recommended_fix="Queue item'ı retry veya cancel edin",
                    ))

    return issues


def audit_tests() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    tests = _test_files()
    st = _load_state()
    last_results = (st.get("scores") or {}).get("last_test_run")

    for mid in HIVE_OS_MODULE_IDS:
        keys = [mid, mid.replace("_engine", ""), mid.replace("_", "")]
        count = 0
        matched = ""
        for k in keys:
            if k in tests:
                count = max(count, tests[k])
                matched = k
        if count == 0 and _module_py_exists(mid):
            issues.append(_make_issue(
                "test", "warning", f"HIVE OS modül testi yok: {mid}",
                "backend/tests altında test dosyası bulunamadı",
                affected_module=mid,
                recommended_fix=f"tests/test_{mid}.py oluşturun",
            ))
        elif count > 0 and count < 3 and mid in {
            "mission_control_center", "executive_ai", "provider_control_center",
            "citation_engine", "action_orchestrator", "publisher_hub",
        }:
            issues.append(_make_issue(
                "test", "info", f"Düşük test coverage: {mid}",
                f"{count} test (test_{matched}.py)",
                affected_module=mid,
            ))

    if not last_results:
        issues.append(_make_issue(
            "test", "info", "Son test sonucu state'te yok",
            "pytest sonuçları audit state'e yazılmamış",
            recommended_fix="Audit run sonrası test özeti kaydedilir",
        ))

    return issues


def audit_security() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    main_text = _read_text(MAIN_PY)

    for path in PUBLIC_API_PATHS:
        if path.startswith("/api/"):
            issues.append(_make_issue(
                "security", "warning", f"Public endpoint (no API key): {path}",
                "Middleware exempt listesinde",
                affected_file="backend/app/main.py",
                recommended_fix="Abuse koruması ve rate limit doğrulayın",
            ))

    if "/api/revenue-leads/track-redirect" in PUBLIC_API_PATHS:
        if "redirect" not in main_text.lower() or "allow" not in main_text.lower():
            issues.append(_make_issue(
                "security", "info", "Redirect endpoint güvenlik incelemesi",
                "track-redirect public — open redirect riski kontrol edilmeli",
                affected_file="backend/app/main.py",
            ))

    try:
        from app.moduller.provider_control_center import mask_token
        sample = mask_token("sk-secret-key-abcd")
        if "sk-secret" in sample or sample != "********abcd":
            issues.append(_make_issue(
                "security", "critical", "Provider token masking hatalı",
                f"Mask örneği: {sample}",
                affected_module="provider_control_center",
            ))
        if "********" not in sample:
            issues.append(_make_issue(
                "security", "critical", "Token UI'ye açık gidebilir",
                "mask_token beklenen formatı üretmiyor",
                affected_module="provider_control_center",
            ))
    except Exception as exc:
        issues.append(_make_issue(
            "security", "warning", "Provider token mask kontrol edilemedi",
            str(exc),
            affected_module="provider_control_center",
        ))

    secret_patterns = [
        (r'logger\.(?:info|debug|warning|error)\([^)]*api_key', "API key loglanıyor olabilir"),
        (r'print\([^)]*password', "Password print ediliyor olabilir"),
        (r'print\([^)]*token', "Token print ediliyor olabilir"),
    ]
    for pattern, msg in secret_patterns:
        if re.search(pattern, main_text, re.IGNORECASE):
            issues.append(_make_issue(
                "security", "warning", msg,
                "main.py içinde potansiyel secret log",
                affected_file="backend/app/main.py",
                recommended_fix="Secret değerleri loglamayın; mask kullanın",
            ))

    if "rate_limit" not in main_text.lower() and "RateLimit" not in main_text:
        if any("track" in p for p in PUBLIC_API_PATHS):
            issues.append(_make_issue(
                "security", "warning", "Tracking endpoint rate limit yok",
                "Public track endpoint'ler için rate limit bulunamadı",
                affected_file="backend/app/main.py",
                recommended_fix="slowapi veya custom rate limit ekleyin",
            ))

    return issues


def _merge_issues(existing: list[dict[str, Any]], new_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Önceki ack/resolved durumlarını koru."""
    index = {
        (i.get("category"), i.get("title"), i.get("affected_module"), i.get("affected_file")): i
        for i in existing
    }
    merged: list[dict[str, Any]] = []
    for issue in new_issues:
        key = (issue.get("category"), issue.get("title"), issue.get("affected_module"), issue.get("affected_file"))
        prev = index.get(key)
        if prev and prev.get("status") in ("acknowledged", "resolved"):
            merged.append({**issue, "issue_id": prev["issue_id"], "status": prev["status"], "updated_at": _now()})
        else:
            merged.append(issue)
    return merged[:ISSUE_LIMIT]


def run_audit(*, persist: bool = True) -> dict[str, Any]:
    _record_brain("audit_started", result={"at": _now()})
    st = _load_state() if persist else {"issues": [], "settings": get_settings()}

    all_issues: list[dict[str, Any]] = []
    sections = {
        "module": audit_modules(),
        "api": audit_api(),
        "frontend": audit_frontend(),
        "provider": audit_providers(),
        "state": audit_states(),
        "queue": audit_queues(),
        "test": audit_tests(),
        "security": audit_security(),
    }
    for cat_issues in sections.values():
        all_issues.extend(cat_issues)

    merged = _merge_issues(st.get("issues") or [], all_issues)
    scores = _compute_scores(merged)
    run_at = _now()
    report = {
        "report_id": f"audit-{uuid.uuid4().hex[:10]}",
        "run_at": run_at,
        "scores": scores,
        "issue_counts": {cat: len(sections[cat]) for cat in sections},
        "total_issues": len(all_issues),
        "open_issues": scores["open_issues"],
        "critical_issues": scores["critical_issues"],
    }

    critical_new = [i for i in all_issues if i.get("severity") == "critical"]
    for issue in all_issues:
        _record_brain("audit_issue_found", keyword=issue.get("category", ""), result={"title": issue.get("title"), "severity": issue.get("severity")})
    for issue in critical_new:
        _record_brain("audit_critical_found", keyword=issue.get("affected_module", ""), result={"title": issue.get("title")})

    if persist:
        st["issues"] = merged
        st["scores"] = scores
        st["last_run"] = run_at
        reports = st.setdefault("reports", [])
        reports.insert(0, report)
        st["reports"] = reports[:REPORT_LIMIT]
        hist = st.setdefault("history", [])
        hist.insert(0, {"action": "run_audit", "at": run_at, "scores": scores, "total": len(all_issues)})
        st["history"] = hist[:HISTORY_LIMIT]
        _save_state(st)

    _record_brain("audit_completed", result={"overall_audit_score": scores["overall_audit_score"], "critical": scores["critical_issues"]})

    return {
        "success": True,
        "run_at": run_at,
        "scores": scores,
        "sections": {k: {"count": len(v), "issues": v[:20]} for k, v in sections.items()},
        "issues": merged if persist else all_issues,
        "report": report,
    }


def list_issues(
    *,
    category: str = "",
    severity: str = "",
    status: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    st = _load_state()
    items = st.get("issues") or []
    if category:
        items = [i for i in items if i.get("category") == category]
    if severity:
        items = [i for i in items if i.get("severity") == severity]
    if status:
        items = [i for i in items if i.get("status") == status]
    return {"success": True, "issues": items[:limit], "count": len(items[:limit]), "total": len(items)}


def get_issue(issue_id: str) -> dict[str, Any]:
    st = _load_state()
    for issue in st.get("issues") or []:
        if issue.get("issue_id") == issue_id:
            return {"success": True, "issue": issue}
    return {"success": False, "error": f"Issue not found: {issue_id}"}


def ack_issue(issue_id: str) -> dict[str, Any]:
    st = _load_state()
    for issue in st.get("issues") or []:
        if issue.get("issue_id") == issue_id:
            issue["status"] = "acknowledged"
            issue["updated_at"] = _now()
            st["scores"] = _compute_scores(st.get("issues") or [])
            _save_state(st)
            return {"success": True, "issue": issue}
    return {"success": False, "error": f"Issue not found: {issue_id}"}


def resolve_issue(issue_id: str) -> dict[str, Any]:
    st = _load_state()
    for issue in st.get("issues") or []:
        if issue.get("issue_id") == issue_id:
            issue["status"] = "resolved"
            issue["updated_at"] = _now()
            st["scores"] = _compute_scores(st.get("issues") or [])
            _save_state(st)
            _record_brain("audit_issue_resolved", keyword=issue.get("category", ""), result={"issue_id": issue_id, "title": issue.get("title")})
            return {"success": True, "issue": issue}
    return {"success": False, "error": f"Issue not found: {issue_id}"}


def mission_control_payload() -> dict[str, Any]:
    st = _load_state()
    scores = st.get("scores") or {}
    if not scores or not st.get("last_run"):
        try:
            res = run_audit(persist=True)
            scores = res.get("scores") or {}
        except Exception:
            scores = _compute_scores(st.get("issues") or [])

    open_issues = [i for i in (st.get("issues") or []) if i.get("status") == "open"]
    critical = [i for i in open_issues if i.get("severity") == "critical"]
    queue_issues = [i for i in open_issues if i.get("category") == "queue"]
    route_issues = [i for i in open_issues if i.get("category") in ("frontend", "api")]
    provider_issues = [i for i in open_issues if i.get("category") == "provider"]

    return {
        "success": True,
        "audit_score": scores.get("overall_audit_score", 0),
        "critical_audit_issues": len(critical),
        "stuck_queues": len([i for i in queue_issues if "stuck" in (i.get("title") or "").lower()]),
        "broken_routes": len(route_issues),
        "provider_risks": len(provider_issues),
        "top_critical": critical[:8],
        "last_run": st.get("last_run", ""),
        "scores": scores,
    }


def executive_risk_payload() -> dict[str, Any]:
    st = _load_state()
    scores = st.get("scores") or _compute_scores(st.get("issues") or [])
    open_issues = [i for i in (st.get("issues") or []) if i.get("status") != "resolved"]
    critical = sum(1 for i in open_issues if i.get("severity") == "critical")
    warning = sum(1 for i in open_issues if i.get("severity") == "warning")
    audit_risk = min(100, critical * 10 + warning * 3 + max(0, 100 - scores.get("overall_audit_score", 100)))
    return {
        "success": True,
        "audit_risk_score": audit_risk,
        "overall_audit_score": scores.get("overall_audit_score", 0),
        "critical_audit_issues": critical,
        "open_audit_issues": len(open_issues),
    }


def dashboard() -> dict[str, Any]:
    st = _load_state()
    scores = st.get("scores") or {}
    issues = st.get("issues") or []
    open_issues = [i for i in issues if i.get("status") == "open"]
    return {
        "success": True,
        "module": "hive_audit_engine",
        "enabled": get_settings().get("enabled", True),
        "last_run": st.get("last_run", ""),
        "scores": scores,
        "summary": {
            "overall_audit_score": scores.get("overall_audit_score", 0),
            "open_issues": len(open_issues),
            "critical_issues": sum(1 for i in open_issues if i.get("severity") == "critical"),
            "warning_issues": sum(1 for i in open_issues if i.get("severity") == "warning"),
            "by_category": {cat: sum(1 for i in open_issues if i.get("category") == cat) for cat in ISSUE_CATEGORIES},
        },
        "recent_reports": (st.get("reports") or [])[:5],
        "top_critical": [i for i in open_issues if i.get("severity") == "critical"][:10],
        "settings": get_settings(),
    }


def health() -> dict[str, Any]:
    dash = dashboard()
    return {
        "success": True,
        "module": "hive_audit_engine",
        "enabled": get_settings().get("enabled", True),
        "overall_audit_score": dash.get("scores", {}).get("overall_audit_score", 0),
        "last_run": dash.get("last_run", ""),
        "open_issues": dash.get("summary", {}).get("open_issues", 0),
        "produces_content": False,
        "publishes": False,
    }


def list_reports(limit: int = 20) -> dict[str, Any]:
    st = _load_state()
    reports = (st.get("reports") or [])[:limit]
    return {"success": True, "reports": reports, "count": len(reports)}


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if report_type == "issues":
        payload = list_issues(limit=500)
    elif report_type == "full":
        payload = run_audit(persist=False)
    else:
        payload = dashboard()
    path = REPORTS_DIR / f"hive-audit-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}
