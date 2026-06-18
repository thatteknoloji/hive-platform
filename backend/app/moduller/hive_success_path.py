"""
HIVE Success Path V2 — onboarding + aktivasyon katmanı.

Kayıt → İlk kampanya → İlk lead → İlk keyword yükselişi yolculuğu.
Mevcut motorları değiştirmez; health/state okuyarak ilerleme tespit eder.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("hive.success_path")

STATE_FILE = Path(__file__).resolve().parent.parent / "hive_success_path_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "talon_data" / "reports"

from app.moduller.hive_learn_content import SUCCESS_PATH_STEP_DETAILS

PROVIDER_TARGETS = ("github_pages", "wordpress", "blogger", "cloudflare", "google_sites")

SUCCESS_STEPS: list[dict[str, Any]] = [
    {
        "step_id": "provider_setup",
        "order": 1,
        "title": "Provider Setup",
        "description": "GitHub, WordPress, Blogger, Cloudflare ve Google Sites bağlantıları.",
        "points": 10,
        "module_id": "provider_control_center",
        "deep_link": "provider_control_center",
        "academy_guide": "guide_provider_setup",
        "badge": None,
    },
    {
        "step_id": "first_project",
        "order": 2,
        "title": "İlk Proje",
        "description": "Campaign Engine veya Astro projesi oluşturun.",
        "points": 10,
        "module_id": "campaign_engine",
        "deep_link": "campaign_engine",
        "academy_guide": "guide_getting_started",
        "badge": None,
    },
    {
        "step_id": "first_keyword",
        "order": 3,
        "title": "İlk Keyword",
        "description": "Rank Watcher'da keyword kaydı.",
        "points": 10,
        "module_id": "rank_index_watcher",
        "deep_link": "rank_index_watcher",
        "academy_guide": "guide_rank_watcher",
        "badge": None,
    },
    {
        "step_id": "first_campaign",
        "order": 4,
        "title": "İlk Campaign",
        "description": "Campaign Engine içinde kampanya oluşturun.",
        "points": 15,
        "module_id": "campaign_engine",
        "deep_link": "campaign_engine",
        "academy_guide": "guide_getting_started",
        "badge": "first_campaign",
    },
    {
        "step_id": "first_authority",
        "order": 5,
        "title": "İlk Authority",
        "description": "Authority Factory batch oluşturun.",
        "points": 15,
        "module_id": "authority_factory",
        "deep_link": "authority_factory",
        "academy_guide": "guide_authority_mesh",
        "badge": "first_authority",
    },
    {
        "step_id": "first_publisher",
        "order": 6,
        "title": "İlk Publisher",
        "description": "Publisher Hub üzerinden dağıtım yapın.",
        "points": 10,
        "module_id": "publisher_hub",
        "deep_link": "publisher_hub",
        "academy_guide": "guide_publisher",
        "badge": "first_publish",
    },
    {
        "step_id": "first_citation",
        "order": 7,
        "title": "İlk Citation Analizi",
        "description": "Citation Engine ile sayfa analizi.",
        "points": 10,
        "module_id": "citation_engine",
        "deep_link": "citation_engine",
        "academy_guide": "guide_citation",
        "badge": "first_citation",
    },
    {
        "step_id": "first_lead",
        "order": 8,
        "title": "İlk Lead",
        "description": "Revenue Lead Engine'de ilk lead kaydı.",
        "points": 20,
        "module_id": "revenue_lead_engine",
        "deep_link": "revenue_lead_engine",
        "academy_guide": "guide_revenue",
        "badge": "first_lead",
    },
]

ROLE_FLOWS: dict[str, dict[str, Any]] = {
    "seo_agency": {
        "label": "SEO Agency",
        "description": "Tam funnel — kampanya, authority, citation ve lead odaklı.",
        "step_order": ["provider_setup", "first_project", "first_keyword", "first_campaign", "first_authority", "first_publisher", "first_citation", "first_lead"],
        "focus_modules": ["campaign_engine", "citation_engine", "revenue_lead_engine"],
    },
    "local_seo": {
        "label": "Local SEO",
        "description": "Citation, lead ve local keyword odaklı yol.",
        "step_order": ["provider_setup", "first_keyword", "first_citation", "first_campaign", "first_publisher", "first_lead", "first_project", "first_authority"],
        "focus_modules": ["citation_engine", "revenue_lead_engine", "rank_index_watcher"],
    },
    "directory_listing": {
        "label": "Directory / Listing",
        "description": "Publisher ve citation dağıtımı öncelikli.",
        "step_order": ["provider_setup", "first_publisher", "first_citation", "first_keyword", "first_project", "first_campaign", "first_authority", "first_lead"],
        "focus_modules": ["publisher_hub", "citation_engine", "listing_hub"],
    },
    "publisher_network": {
        "label": "Publisher Network",
        "description": "Yayın ağı ve authority mesh odaklı.",
        "step_order": ["provider_setup", "first_publisher", "first_authority", "first_project", "first_keyword", "first_campaign", "first_citation", "first_lead"],
        "focus_modules": ["publisher_hub", "authority_factory", "authority_mesh_engine"],
    },
    "authority_builder": {
        "label": "Authority Builder",
        "description": "Authority Factory ve mesh öncelikli büyüme.",
        "step_order": ["provider_setup", "first_authority", "first_publisher", "first_keyword", "first_campaign", "first_project", "first_citation", "first_lead"],
        "focus_modules": ["authority_factory", "authority_mesh_engine", "publisher_hub"],
    },
}

BADGE_DEFS: dict[str, dict[str, Any]] = {
    "first_campaign": {"title": "First Campaign", "icon": "🎯", "step_id": "first_campaign"},
    "first_authority": {"title": "First Authority", "icon": "🏭", "step_id": "first_authority"},
    "first_publish": {"title": "First Publish", "icon": "📢", "step_id": "first_publisher"},
    "first_citation": {"title": "First Citation", "icon": "📊", "step_id": "first_citation"},
    "first_lead": {"title": "First Lead", "icon": "💰", "step_id": "first_lead"},
    "campaign_master": {"title": "Campaign Master", "icon": "👑", "requires_steps": ["first_campaign", "first_project"]},
    "authority_builder": {"title": "Authority Builder", "icon": "🌐", "requires_steps": ["first_authority", "first_publisher"]},
    "citation_expert": {"title": "Citation Expert", "icon": "🎓", "requires_steps": ["first_citation"]},
    "revenue_hunter": {"title": "Revenue Hunter", "icon": "🏹", "requires_steps": ["first_lead"]},
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "user_id": "default",
    "role": "seo_agency",
    "auto_start_on_wizard": True,
    "enabled": True,
}

STEP_TIME_ESTIMATES: dict[str, str] = {
    "provider_setup": "15-30 dk",
    "first_project": "10-20 dk",
    "first_keyword": "5-10 dk",
    "first_campaign": "15-25 dk",
    "first_authority": "20-40 dk",
    "first_publisher": "10-20 dk",
    "first_citation": "10-15 dk",
    "first_lead": "5-15 dk",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("manual_completed", [])
                data.setdefault("badges_earned", [])
                data.setdefault("path_started_at", "")
                data.setdefault("path_completed_at", "")
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "manual_completed": [],
        "badges_earned": [],
        "path_started_at": "",
        "path_completed_at": "",
        "history": [],
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_brain(event: str, *, step_id: str = "", result: dict | None = None) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event,
            "hive_success_path",
            reason=event,
            result=result or {},
            metadata={"step_id": step_id, "module": "hive_success_path"},
        )
    except Exception as exc:
        logger.debug("brain: %s", exc)


def _safe_call(module: str, func: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        mod = __import__(f"app.moduller.{module}", fromlist=[func])
        fn: Callable = getattr(mod, func)
        res = fn(*args, **kwargs)
        return res if isinstance(res, dict) else {"success": True, "data": res}
    except Exception as exc:
        logger.debug("success_path.%s.%s: %s", module, func, exc)
        return {"success": False, "error": str(exc)}


def _check_provider_setup() -> bool:
    lst = _safe_call("provider_control_center", "list_providers")
    providers = lst.get("providers") or []
    connected = 0
    for p in providers:
        pid = p.get("provider", "")
        if pid not in PROVIDER_TARGETS:
            continue
        if p.get("status") in ("connected", "healthy", "ok", "ready"):
            connected += 1
    return connected >= 2


def _check_first_project() -> bool:
    camp = _safe_call("campaign_engine", "health")
    if int(camp.get("campaigns_total") or 0) > 0:
        return True
    astro = _safe_call("astro_auto_publisher", "get_dashboard")
    if int(astro.get("project_count") or astro.get("projects_count") or 0) > 0:
        return True
    af = _safe_call("astro_factory", "health")
    return bool(af.get("has_projects") or af.get("project_count"))


def _check_first_keyword() -> bool:
    try:
        from app.moduller.rank_index_watcher import _load_state as riw_load
        state = riw_load()
        for proj in (state.get("projects") or {}).values():
            if proj.get("keywords"):
                return True
    except Exception:
        pass
    return False


def _check_first_campaign() -> bool:
    h = _safe_call("campaign_engine", "health")
    return int(h.get("campaigns_total") or 0) > 0


def _check_first_authority() -> bool:
    d = _safe_call("authority_factory", "dashboard")
    return int(d.get("batches_count") or 0) > 0


def _check_first_publisher() -> bool:
    h = _safe_call("publisher_hub", "health")
    return int(h.get("published_count") or 0) > 0


def _check_first_citation() -> bool:
    mc = _safe_call("citation_engine", "mission_control_payload")
    if int(mc.get("pages_tracked") or 0) > 0:
        return True
    d = _safe_call("citation_engine", "dashboard")
    return int(d.get("pages_count") or 0) > 0


def _check_first_lead() -> bool:
    d = _safe_call("revenue_lead_engine", "dashboard")
    return int(d.get("total_leads") or 0) > 0


STEP_CHECKS: dict[str, Callable[[], bool]] = {
    "provider_setup": _check_provider_setup,
    "first_project": _check_first_project,
    "first_keyword": _check_first_keyword,
    "first_campaign": _check_first_campaign,
    "first_authority": _check_first_authority,
    "first_publisher": _check_first_publisher,
    "first_citation": _check_first_citation,
    "first_lead": _check_first_lead,
}


def get_settings() -> dict[str, Any]:
    st = _load_state()
    merged = dict(DEFAULT_SETTINGS)
    merged.update(st.get("settings") or {})
    return merged


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    settings = dict(get_settings())
    for key in ("user_id", "role", "auto_start_on_wizard", "enabled"):
        if key in updates and updates[key] is not None:
            settings[key] = updates[key]
    if settings.get("role") not in ROLE_FLOWS:
        settings["role"] = "seo_agency"
    st["settings"] = settings
    st.setdefault("history", []).insert(0, {"type": "settings_updated", "at": _now(), "settings": settings})
    _save_state(st)
    return {"success": True, "settings": settings}


def _wizard_completed() -> bool:
    w = _safe_call("first_run_wizard", "get_status")
    return bool(w.get("wizard_completed"))


def _ensure_path_started() -> None:
    st = _load_state()
    settings = get_settings()
    if st.get("path_started_at"):
        return
    if not settings.get("auto_start_on_wizard", True):
        return
    if not _wizard_completed():
        return
    st["path_started_at"] = _now()
    st.setdefault("history", []).insert(0, {"type": "path_started", "at": _now(), "trigger": "wizard_completed"})
    _save_state(st)
    _record_brain("success_path_started", result={"trigger": "wizard_completed"})


def _step_completed(step_id: str, state: dict[str, Any], check_results: dict[str, bool]) -> bool:
    if step_id in (state.get("manual_completed") or []):
        return True
    return bool(check_results.get(step_id))


def _run_step_checks() -> dict[str, bool]:
    state = _load_state()
    manual = set(state.get("manual_completed") or [])
    results: dict[str, bool] = {}
    for sid, checker in STEP_CHECKS.items():
        if sid in manual:
            results[sid] = True
            continue
        try:
            results[sid] = bool(checker())
        except Exception:
            results[sid] = False
    return results


def _ordered_steps(role: str) -> list[dict[str, Any]]:
    flow = ROLE_FLOWS.get(role) or ROLE_FLOWS["seo_agency"]
    order = flow.get("step_order") or [s["step_id"] for s in SUCCESS_STEPS]
    by_id = {s["step_id"]: s for s in SUCCESS_STEPS}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sid in order:
        if sid in by_id and sid not in seen:
            out.append(dict(by_id[sid]))
            seen.add(sid)
    for s in SUCCESS_STEPS:
        if s["step_id"] not in seen:
            out.append(dict(s))
    return out


def _enrich_step(step: dict[str, Any], *, done: bool, auto_ok: bool) -> dict[str, Any]:
    sid = step["step_id"]
    detail = SUCCESS_PATH_STEP_DETAILS.get(sid, {})
    return {
        **step,
        **detail,
        "completed": done,
        "status": "done" if done else "pending",
        "auto_detected": auto_ok and done,
        "academy_link": f"/hive-academy/guide/{step.get('academy_guide')}" if step.get("academy_guide") else "",
    }


def _compute_badges(completed_ids: set[str]) -> list[str]:
    earned: set[str] = set()
    for bid, meta in BADGE_DEFS.items():
        req = meta.get("requires_steps") or ([meta["step_id"]] if meta.get("step_id") else [])
        if req and all(r in completed_ids for r in req):
            earned.add(bid)
        elif meta.get("step_id") and meta["step_id"] in completed_ids:
            earned.add(bid)
    if "first_campaign" in completed_ids and "first_project" in completed_ids:
        earned.add("campaign_master")
    if "first_authority" in completed_ids and "first_publisher" in completed_ids:
        earned.add("authority_builder")
    if "first_citation" in completed_ids:
        earned.add("citation_expert")
    if "first_lead" in completed_ids:
        earned.add("revenue_hunter")
    return sorted(earned)


def _sync_badges(state: dict[str, Any], completed_ids: set[str]) -> list[str]:
    earned = _compute_badges(completed_ids)
    prev = set(state.get("badges_earned") or [])
    new_badges = [b for b in earned if b not in prev]
    if new_badges:
        state["badges_earned"] = earned
        for b in new_badges:
            state.setdefault("history", []).insert(0, {"type": "badge_earned", "badge": b, "at": _now()})
        _save_state(state)
    elif set(earned) != prev:
        state["badges_earned"] = earned
        _save_state(state)
    return earned


def _build_success_model(
    *,
    completion_score: int,
    steps_completed: list[str],
    steps_remaining: list[str],
    current_goal: str,
    next_action: str,
    estimated_time: str,
    role: str,
) -> dict[str, Any]:
    settings = get_settings()
    return {
        "user_id": settings.get("user_id", "default"),
        "completion_score": completion_score,
        "steps_completed": steps_completed,
        "steps_remaining": steps_remaining,
        "current_goal": current_goal,
        "next_action": next_action,
        "estimated_time_to_success": estimated_time,
        "role": role,
    }


def _estimate_remaining_time(remaining: list[str]) -> str:
    if not remaining:
        return "0 dk"
    mins_lo = 0
    mins_hi = 0
    for sid in remaining:
        est = STEP_TIME_ESTIMATES.get(sid, "10-15 dk")
        parts = est.replace(" dk", "").split("-")
        try:
            lo = int(parts[0])
            hi = int(parts[1]) if len(parts) > 1 else lo
        except ValueError:
            lo, hi = 10, 15
        mins_lo += lo
        mins_hi += hi
    if mins_hi <= 60:
        return f"{mins_lo}-{mins_hi} dk"
    return f"{mins_lo // 60}-{(mins_hi + 59) // 60} saat"


def _process_completion_events(state: dict[str, Any], newly_completed: list[str]) -> None:
    for sid in newly_completed:
        _record_brain("success_step_completed", step_id=sid, result={"step_id": sid})
        if sid == "first_campaign":
            _record_brain("first_campaign_created", step_id=sid)
        if sid == "first_lead":
            _record_brain("first_lead_received", step_id=sid)
    if newly_completed and not state.get("path_started_at"):
        state["path_started_at"] = _now()
        _record_brain("success_path_started", result={"trigger": "step_auto"})


def get_progress(*, recalculate: bool = True) -> dict[str, Any]:
    _ensure_path_started()
    state = _load_state()
    settings = get_settings()
    role = settings.get("role", "seo_agency")
    check_results = _run_step_checks() if recalculate else {}

    steps_out: list[dict[str, Any]] = []
    steps_completed: list[str] = []
    steps_remaining: list[str] = []
    score = 0
    prev_completed = set(state.get("_last_completed") or [])

    for step in _ordered_steps(role):
        sid = step["step_id"]
        done = _step_completed(sid, state, check_results)
        auto_ok = check_results.get(sid, False)
        if done:
            steps_completed.append(sid)
            score += int(step.get("points") or 0)
        else:
            steps_remaining.append(sid)
        steps_out.append(_enrich_step(step, done=done, auto_ok=auto_ok))

    newly = [s for s in steps_completed if s not in prev_completed]
    if newly:
        _process_completion_events(state, newly)
        state["_last_completed"] = steps_completed
        _save_state(state)

    badges = _sync_badges(state, set(steps_completed))
    next_step = next((s for s in steps_out if not s["completed"]), None)
    current_goal = next_step["title"] if next_step else "Success Path tamamlandı"
    next_action = (next_step.get("description") or next_step.get("title") or "") if next_step else "Tüm adımlar tamam — Mission Control'den büyümeye devam edin"
    estimated = _estimate_remaining_time(steps_remaining)

    path_done = score >= 100 or len(steps_remaining) == 0
    if path_done and not state.get("path_completed_at"):
        state["path_completed_at"] = _now()
        state.setdefault("history", []).insert(0, {"type": "path_completed", "at": _now(), "score": score})
        _save_state(state)
        _record_brain("success_path_completed", result={"completion_score": score})

    model = _build_success_model(
        completion_score=min(100, score),
        steps_completed=steps_completed,
        steps_remaining=steps_remaining,
        current_goal=current_goal,
        next_action=next_action,
        estimated_time=estimated,
        role=role,
    )

    return {
        "success": True,
        "module": "hive_success_path",
        **model,
        "steps": steps_out,
        "badges": [{"id": b, **BADGE_DEFS.get(b, {"title": b})} for b in badges],
        "path_started_at": state.get("path_started_at") or "",
        "path_completed_at": state.get("path_completed_at") or "",
        "wizard_completed": _wizard_completed(),
        "total_steps": len(SUCCESS_STEPS),
        "max_score": 100,
    }


def recalculate() -> dict[str, Any]:
    return get_progress(recalculate=True)


def get_steps() -> dict[str, Any]:
    settings = get_settings()
    role = settings.get("role", "seo_agency")
    progress = get_progress(recalculate=True)
    return {
        "success": True,
        "role": role,
        "role_flow": ROLE_FLOWS.get(role, ROLE_FLOWS["seo_agency"]),
        "steps": progress.get("steps") or [],
        "available_roles": [{"id": k, **{kk: vv for kk, vv in v.items() if kk != "step_order"}} for k, v in ROLE_FLOWS.items()],
    }


def get_recommendations(limit: int = 8) -> dict[str, Any]:
    progress = get_progress(recalculate=True)
    settings = get_settings()
    role = settings.get("role", "seo_agency")
    flow = ROLE_FLOWS.get(role, ROLE_FLOWS["seo_agency"])
    recs: list[dict[str, Any]] = []

    for step in progress.get("steps") or []:
        if step.get("completed"):
            continue
        recs.append({
            "priority": step.get("order", 99),
            "title": step.get("title"),
            "reason": step.get("description"),
            "module_id": step.get("module_id"),
            "deep_link": step.get("deep_link"),
            "step_id": step.get("step_id"),
            "academy_guide": step.get("academy_guide"),
            "academy_link": step.get("academy_link"),
            "estimated_time": STEP_TIME_ESTIMATES.get(step.get("step_id"), "10-15 dk"),
        })
        if len(recs) >= limit:
            break

    if not recs:
        recs.append({
            "priority": 0,
            "title": "Success Path tamamlandı",
            "reason": "Mission Control ve Campaign Engine ile ölçeklendirin",
            "module_id": "mission_control_center",
            "deep_link": "mission_control_center",
            "step_id": "complete",
        })

    return {
        "success": True,
        "recommendations": recs,
        "count": len(recs),
        "role": role,
        "focus_modules": flow.get("focus_modules") or [],
        "next_action": progress.get("next_action"),
        "current_goal": progress.get("current_goal"),
    }


def mentor_success_answer() -> dict[str, Any]:
    """Mentor — 'Ne yapmalıyım?' için Success Path cevabı."""
    progress = get_progress(recalculate=True)
    recs = get_recommendations(limit=3)
    steps = [
        {
            "order": i + 1,
            "module_id": r.get("module_id"),
            "title": r.get("title"),
            "reason": r.get("reason"),
            "step_id": r.get("step_id"),
        }
        for i, r in enumerate(recs.get("recommendations") or [])
    ]
    return {
        "success": True,
        "intent": "success_path",
        "summary": (
            f"Success Path %{progress.get('completion_score', 0)} — "
            f"Sıradaki hedef: {progress.get('current_goal')}. "
            f"{progress.get('next_action')}"
        ),
        "steps": steps,
        "completion_score": progress.get("completion_score", 0),
        "current_goal": progress.get("current_goal"),
        "next_action": progress.get("next_action"),
        "estimated_time_to_success": progress.get("estimated_time_to_success"),
        "academy_guide": (recs.get("recommendations") or [{}])[0].get("academy_guide", ""),
        "source": "hive_success_path",
    }


def health() -> dict[str, Any]:
    progress = get_progress(recalculate=False)
    settings = get_settings()
    return {
        "success": True,
        "module": "hive_success_path",
        "enabled": settings.get("enabled", True),
        "completion_score": progress.get("completion_score", 0),
        "steps_completed": len(progress.get("steps_completed") or []),
        "total_steps": progress.get("total_steps", len(SUCCESS_STEPS)),
        "path_completed": bool(progress.get("path_completed_at")),
        "role": settings.get("role", "seo_agency"),
        "wizard_completed": progress.get("wizard_completed", False),
    }


def dashboard() -> dict[str, Any]:
    progress = get_progress(recalculate=True)
    settings = get_settings()
    recs = get_recommendations(limit=5)
    return {
        "success": True,
        "module": "hive_success_path",
        "settings": settings,
        "progress": progress,
        "recommendations": recs.get("recommendations") or [],
        "mission_control": mission_control_payload(),
        "role_flow": ROLE_FLOWS.get(settings.get("role", "seo_agency"), ROLE_FLOWS["seo_agency"]),
        "badges": progress.get("badges") or [],
    }


def mission_control_payload() -> dict[str, Any]:
    progress = get_progress(recalculate=False)
    return {
        "success": True,
        "completion_percent": progress.get("completion_score", 0),
        "current_goal": progress.get("current_goal", ""),
        "next_action": progress.get("next_action", ""),
        "steps_completed": len(progress.get("steps_completed") or []),
        "total_steps": progress.get("total_steps", len(SUCCESS_STEPS)),
        "path_completed": bool(progress.get("path_completed_at")),
        "badges_count": len(progress.get("badges") or []),
        "estimated_time_to_success": progress.get("estimated_time_to_success", ""),
    }


def executive_activation_payload() -> dict[str, Any]:
    progress = get_progress(recalculate=False)
    score = int(progress.get("completion_score") or 0)
    return {
        "success": True,
        "activation_score": score,
        "activation_category": (
            "Activated" if score >= 75 else "On Track" if score >= 40 else "Needs Onboarding"
        ),
        "current_goal": progress.get("current_goal"),
        "next_action": progress.get("next_action"),
        "steps_remaining": len(progress.get("steps_remaining") or []),
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    progress = get_progress(recalculate=True)
    payload = {
        "report_type": report_type,
        "generated_at": _now(),
        "progress": progress,
        "settings": get_settings(),
        "recommendations": get_recommendations(limit=10),
    }
    fname = f"success_path_{report_type}_{uuid.uuid4().hex[:8]}.json"
    path = REPORTS_DIR / fname
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path), "report": payload}


def complete_step(step_id: str, *, manual: bool = True) -> dict[str, Any]:
    if step_id not in {s["step_id"] for s in SUCCESS_STEPS}:
        return {"success": False, "error": f"Geçersiz step_id: {step_id}"}
    state = _load_state()
    manual_list = state.setdefault("manual_completed", [])
    if manual and step_id not in manual_list:
        manual_list.append(step_id)
        state.setdefault("history", []).insert(0, {"type": "step_completed", "step_id": step_id, "at": _now(), "manual": manual})
        if not state.get("path_started_at"):
            state["path_started_at"] = _now()
            _record_brain("success_path_started", result={"trigger": "manual_step"})
        _save_state(state)
        _record_brain("success_step_completed", step_id=step_id, result={"manual": manual})
    return {"success": True, "step_id": step_id, **get_progress(recalculate=True)}
