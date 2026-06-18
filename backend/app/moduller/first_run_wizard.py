"""
First Run Wizard V1 — yeni kullanıcı onboarding adımları.

Mevcut modül motorlarını değiştirmez; health/state okuyarak ilerleme tespit eder.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("hive.first_run_wizard")

STATE_FILE = Path(__file__).resolve().parent.parent / "first_run_wizard_state.json"

from app.moduller.hive_learn_content import WIZARD_STEP_DETAILS

WIZARD_STEPS: list[dict[str, Any]] = [
    {
        "step_id": "wordpress",
        "order": 1,
        "title": "WordPress bağlantısı",
        "description": "Ana WordPress ağına REST API oturumu açın.",
        "module_id": "wordpress",
        "deep_link": "wordpress",
        "academy_guide": "guide_wordpress",
    },
    {
        "step_id": "github",
        "order": 2,
        "title": "GitHub bağlantısı",
        "description": "GitHub Pages worker için token ve provider yapılandırması.",
        "module_id": "authority_mesh_engine",
        "deep_link": "authority_mesh_engine",
        "mesh_tab": "github_pages",
        "academy_guide": "guide_authority_mesh",
    },
    {
        "step_id": "blogger",
        "order": 3,
        "title": "Blogger bağlantısı",
        "description": "Google OAuth ile Blogger kanalını bağlayın.",
        "module_id": "blogger",
        "deep_link": "blogger",
        "academy_guide": "guide_wordpress",
    },
    {
        "step_id": "astro_project",
        "order": 4,
        "title": "İlk Astro projesi",
        "description": "Astro Factory veya Auto Publisher'da ilk proje kaydı.",
        "module_id": "astro_factory",
        "deep_link": "astro_factory",
    },
    {
        "step_id": "authority_mesh",
        "order": 5,
        "title": "İlk Authority Mesh",
        "description": "En az bir support site planı veya yayın.",
        "module_id": "authority_mesh_engine",
        "deep_link": "authority_mesh_engine",
        "academy_guide": "guide_authority_mesh",
    },
    {
        "step_id": "first_publish",
        "order": 6,
        "title": "İlk yayın",
        "description": "Publisher Hub üzerinden ilk içerik yayını.",
        "module_id": "publisher_hub",
        "deep_link": "publisher_hub",
        "academy_guide": "guide_publisher",
    },
    {
        "step_id": "rank_watcher",
        "order": 7,
        "title": "İlk Rank Watcher projesi",
        "description": "Keyword takibi için proje oluşturun.",
        "module_id": "rank_index_watcher",
        "deep_link": "rank_index_watcher",
        "academy_guide": "guide_rank_watcher",
    },
    {
        "step_id": "mission_control",
        "order": 8,
        "title": "Mission Control aktivasyonu",
        "description": "Command Center'ı açıp operasyon özetini görüntüleyin.",
        "module_id": "mission_control_center",
        "deep_link": "mission_control_center",
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("manual_completed", [])
                data.setdefault("wizard_completed_at", "")
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"manual_completed": [], "wizard_completed_at": "", "history": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_brain(event: str, *, step_id: str = "", result: dict | None = None) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            "module_action",
            "first_run_wizard",
            reason=event,
            result=result or {},
            metadata={"learn_event": event, "step_id": step_id},
        )
    except Exception as exc:
        logger.debug("brain: %s", exc)


def _safe_call(module: str, func: str) -> dict[str, Any]:
    try:
        mod = __import__(f"app.moduller.{module}", fromlist=[func])
        fn: Callable = getattr(mod, func)
        res = fn()
        return res if isinstance(res, dict) else {"success": True, "data": res}
    except Exception as exc:
        logger.debug("wizard.%s.%s: %s", module, func, exc)
        return {"success": False, "error": str(exc)}


def _check_wordpress() -> bool:
    try:
        from app.moduller.wordpress_api import ensure_wp_connected
        r = ensure_wp_connected(verify=False)
        return bool(r.get("connected") or r.get("success"))
    except Exception:
        try:
            from app.moduller.wordpress_api import get_session
            return get_session() is not None
        except Exception:
            return False


def _check_github() -> bool:
    h = _safe_call("github_pages_worker", "health")
    return bool(h.get("provider_ready")) or int(h.get("sites_count") or h.get("published_count") or 0) > 0


def _check_blogger() -> bool:
    r = _safe_call("blogger_api", "get_status")
    return bool(r.get("connected"))


def _check_astro() -> bool:
    d = _safe_call("astro_auto_publisher", "get_dashboard")
    if int(d.get("project_count") or d.get("projects_count") or 0) > 0:
        return True
    d2 = _safe_call("astro_factory", "health")
    return bool(d2.get("has_projects") or d2.get("project_count"))


def _check_authority_mesh() -> bool:
    d = _safe_call("authority_mesh_engine", "dashboard")
    return int(d.get("published_count") or 0) > 0 or int(d.get("queued_tasks") or 0) > 0


def _check_publish() -> bool:
    h = _safe_call("publisher_hub", "health")
    return int(h.get("published_count") or 0) > 0


def _check_rank_watcher() -> bool:
    h = _safe_call("rank_index_watcher", "health")
    return int(h.get("project_count") or 0) > 0


def _check_mission_control() -> bool:
    try:
        from app.moduller.mission_control_center import _load_state as mcc_load
        st = mcc_load()
        return bool(st.get("last_opened_at"))
    except Exception:
        return False


STEP_CHECKS: dict[str, Callable[[], bool]] = {
    "wordpress": _check_wordpress,
    "github": _check_github,
    "blogger": _check_blogger,
    "astro_project": _check_astro,
    "authority_mesh": _check_authority_mesh,
    "first_publish": _check_publish,
    "rank_watcher": _check_rank_watcher,
    "mission_control": _check_mission_control,
}


def _step_completed(step_id: str, state: dict[str, Any]) -> bool:
    if step_id in (state.get("manual_completed") or []):
        return True
    checker = STEP_CHECKS.get(step_id)
    if checker:
        try:
            return checker()
        except Exception:
            pass
    return False


def _progress_bucket(completed: int, total: int) -> int:
    if total == 0:
        return 0
    pct = int((completed / total) * 100)
    if pct >= 100:
        return 100
    if pct >= 75:
        return 75
    if pct >= 50:
        return 50
    if pct >= 25:
        return 25
    return 0


def health() -> dict[str, Any]:
    status = get_status()
    return {
        "success": True,
        "module": "first_run_wizard",
        "progress_percent": status.get("progress_percent", 0),
        "progress_bucket": status.get("progress_bucket", 0),
        "completed_count": status.get("completed_count", 0),
        "total_steps": status.get("total_steps", 8),
        "wizard_completed": status.get("wizard_completed", False),
    }


def _enrich_step(
    step: dict[str, Any],
    *,
    done: bool,
    auto_ok: bool = False,
    check_error: str = "",
) -> dict[str, Any]:
    sid = step["step_id"]
    detail = WIZARD_STEP_DETAILS.get(sid, {})
    manual = _load_state().get("manual_completed") or []
    connect_required = not done and not auto_ok and sid not in manual
    return {
        **step,
        **detail,
        "completed": done,
        "status": "done" if done else ("connect_required" if connect_required else "pending"),
        "auto_detected": auto_ok,
        "check_error": check_error,
    }


def _run_step_checks() -> tuple[dict[str, bool], dict[str, str]]:
    """Her adım için checker'ı yalnızca bir kez çalıştır."""
    results: dict[str, bool] = {}
    errors: dict[str, str] = {}
    state = _load_state()
    manual = set(state.get("manual_completed") or [])
    for sid, checker in STEP_CHECKS.items():
        if sid in manual:
            results[sid] = True
            continue
        try:
            results[sid] = bool(checker())
        except Exception as exc:
            results[sid] = False
            errors[sid] = str(exc)
    return results, errors


def get_status() -> dict[str, Any]:
    state = _load_state()
    check_results, check_errors = _run_step_checks()
    manual = set(state.get("manual_completed") or [])
    steps_out: list[dict[str, Any]] = []
    completed_count = 0
    for step in WIZARD_STEPS:
        sid = step["step_id"]
        done = sid in manual or check_results.get(sid, False)
        if done:
            completed_count += 1
        steps_out.append(_enrich_step(
            step,
            done=done,
            auto_ok=check_results.get(sid, False),
            check_error=check_errors.get(sid, ""),
        ))

    total = len(WIZARD_STEPS)
    raw_pct = int((completed_count / total) * 100) if total else 0
    bucket = _progress_bucket(completed_count, total)
    wizard_done = completed_count >= total
    if wizard_done and not state.get("wizard_completed_at"):
        state["wizard_completed_at"] = _now()
        state.setdefault("history", []).insert(0, {"type": "wizard_completed", "at": _now()})
        _save_state(state)
        _record_brain("wizard_completed", result={"completed_count": completed_count})
        try:
            from app.moduller.hive_success_path import _ensure_path_started
            _ensure_path_started()
        except Exception:
            pass

    return {
        "success": True,
        "steps": steps_out,
        "completed_count": completed_count,
        "total_steps": total,
        "progress_percent": raw_pct,
        "progress_bucket": bucket,
        "wizard_completed": wizard_done,
        "wizard_completed_at": state.get("wizard_completed_at") or "",
    }


def complete_step(step_id: str, *, manual: bool = True) -> dict[str, Any]:
    if not step_id:
        return {"success": False, "error": "step_id gerekli"}
    valid = {s["step_id"] for s in WIZARD_STEPS}
    if step_id not in valid:
        return {"success": False, "error": f"Geçersiz step_id: {step_id}"}

    state = _load_state()
    manual_list = state.setdefault("manual_completed", [])
    if manual and step_id not in manual_list:
        manual_list.append(step_id)
        state.setdefault("history", []).insert(0, {"type": "step_completed", "step_id": step_id, "at": _now(), "manual": manual})
        _save_state(state)
        _record_brain("wizard_step_completed", step_id=step_id, result={"manual": manual})

    status = get_status()
    return {"success": True, "step_id": step_id, **status}


def reset_wizard() -> dict[str, Any]:
    state = {"manual_completed": [], "wizard_completed_at": "", "history": [{"type": "reset", "at": _now()}]}
    _save_state(state)
    return {"success": True, "message": "Wizard sıfırlandı", **get_status()}
