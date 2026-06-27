"""HIVE Academy V2 — kullanıcı ilerleme, rozet, favori, not depolama."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_FILE = Path(__file__).resolve().parent / "academy_user_state.json"

BADGE_DEFS: list[dict[str, Any]] = [
    {"id": "first_project", "title": "İlk Firma", "icon": "🏢", "rule": "slug:ilk-firma-nasil-eklenir", "xp": 50},
    {"id": "first_publish", "title": "İlk Publish", "icon": "🚀", "rule": "slug:ilk-publish", "xp": 50},
    {"id": "first_authority", "title": "İlk Authority", "icon": "🌐", "rule": "slug:authority-factory-nedir", "xp": 75},
    {"id": "first_deploy", "title": "İlk Deploy", "icon": "⚙️", "rule": "section:deploy", "xp": 75},
    {"id": "seo_expert", "title": "SEO Uzmanı", "icon": "📈", "rule": "count:3:seo", "xp": 100},
    {"id": "publisher_expert", "title": "Publisher Uzmanı", "icon": "📢", "rule": "slug:publisher-hub-nedir", "xp": 100},
    {"id": "automation_expert", "title": "Automation Uzmanı", "icon": "🤖", "rule": "percent:50", "xp": 150},
    {"id": "authority_expert", "title": "Authority Uzmanı", "icon": "🔗", "rule": "slug:authority-factory-nedir", "xp": 100},
    {"id": "deploy_expert", "title": "Deploy Uzmanı", "icon": "🛠", "rule": "section:deploy", "xp": 100},
    {"id": "academy_graduate", "title": "Academy Mezunu", "icon": "🎓", "rule": "percent:80", "xp": 500},
]

XP_PER_COMPLETE = 50
XP_PER_MISSION = 25
XP_LEVEL_STEP = 200

LEARNING_PATH = [
    {"id": "baslangic", "label": "Başlangıç"},
    {"id": "seo", "label": "SEO"},
    {"id": "geo", "label": "GEO"},
    {"id": "authority", "label": "Authority"},
    {"id": "publish", "label": "Publish"},
    {"id": "deploy", "label": "Deploy"},
    {"id": "advanced", "label": "Advanced"},
    {"id": "developer", "label": "Developer"},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("users", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"users": {}}


def _save(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _user_bucket(state: dict[str, Any], user_id: str) -> dict[str, Any]:
    users = state.setdefault("users", {})
    bucket = users.setdefault(user_id, {})
    bucket.setdefault("progress", {})
    bucket.setdefault("favorites", [])
    bucket.setdefault("notes", {})
    bucket.setdefault("badges", [])
    bucket.setdefault("quiz_scores", {})
    bucket.setdefault("missions_done", {})
    bucket.setdefault("checklists", {})
    bucket.setdefault("xp", 0)
    bucket.setdefault("daily_goal", 1)
    bucket.setdefault("daily_completed_today", 0)
    bucket.setdefault("daily_date", "")
    bucket.setdefault("total_read_seconds", 0)
    bucket.setdefault("last_slug", "")
    bucket.setdefault("last_active_at", "")
    return bucket


def _slug_meta_map(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for section in index.get("sections") or []:
        sec_slug = section.get("slug") or ""
        for item in section.get("items") or []:
            slug = item.get("slug") or ""
            if slug:
                out[slug] = {**item, "section_slug": sec_slug, "section_title": section.get("title")}
    return out


def _compute_percent(progress: dict[str, Any], total_docs: int) -> float:
    if total_docs <= 0:
        return 0.0
    completed = sum(1 for p in progress.values() if p.get("completed"))
    return round(100.0 * completed / total_docs, 1)


def _award_badges(bucket: dict[str, Any], index: dict[str, Any]) -> list[str]:
    earned = set(bucket.get("badges") or [])
    progress = bucket.get("progress") or {}
    meta_map = _slug_meta_map(index)
    total = sum(len(s.get("items") or []) for s in index.get("sections") or [])
    pct = _compute_percent(progress, total)
    new_badges: list[str] = []

    for badge in BADGE_DEFS:
        bid = badge["id"]
        if bid in earned:
            continue
        rule = badge.get("rule") or ""
        ok = False
        if rule.startswith("slug:"):
            ok = rule.split(":", 1)[1] in progress and progress[rule.split(":", 1)[1]].get("completed")
        elif rule.startswith("section:"):
            sec = rule.split(":", 1)[1]
            ok = any(
                meta_map.get(sl, {}).get("section_slug") == sec and p.get("completed")
                for sl, p in progress.items()
            )
        elif rule.startswith("count:"):
            parts = rule.split(":")
            need = int(parts[1]) if len(parts) > 1 else 1
            tag = parts[2] if len(parts) > 2 else ""
            cnt = sum(
                1 for sl, p in progress.items()
                if p.get("completed") and tag in sl
            )
            ok = cnt >= need
        elif rule.startswith("percent:"):
            need = float(rule.split(":", 1)[1])
            ok = pct >= need

        if ok:
            earned.add(bid)
            new_badges.append(bid)

    bucket["badges"] = sorted(earned)
    return new_badges


def _level_from_xp(xp: int) -> int:
    return max(1, xp // XP_LEVEL_STEP + 1)


def _add_xp(bucket: dict[str, Any], amount: int) -> int:
    bucket["xp"] = int(bucket.get("xp") or 0) + max(0, amount)
    return bucket["xp"]


def doc_status(progress_entry: dict[str, Any] | None) -> str:
    if not progress_entry:
        return "not_started"
    if progress_entry.get("completed"):
        return "completed"
    if progress_entry.get("read_count") or progress_entry.get("checklist"):
        return "in_progress"
    return "not_started"


def _daily_tick(bucket: dict[str, Any]) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if bucket.get("daily_date") != today:
        bucket["daily_date"] = today
        bucket["daily_completed_today"] = 0


def get_progress(user_id: str, index: dict[str, Any]) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    total = sum(len(s.get("items") or []) for s in index.get("sections") or [])
    progress = bucket.get("progress") or {}
    percent = _compute_percent(progress, total)
    completed_slugs = [s for s, p in progress.items() if p.get("completed")]
    statuses = {slug: doc_status(p) for slug, p in progress.items()}
    xp = int(bucket.get("xp") or 0)
    _daily_tick(bucket)
    return {
        "success": True,
        "percent": percent,
        "total_docs": total,
        "completed_count": len(completed_slugs),
        "completed_slugs": completed_slugs,
        "statuses": statuses,
        "last_slug": bucket.get("last_slug") or "",
        "total_read_seconds": int(bucket.get("total_read_seconds") or 0),
        "badges": bucket.get("badges") or [],
        "favorites": bucket.get("favorites") or [],
        "learning_path": LEARNING_PATH,
        "progress": progress,
        "xp": xp,
        "level": _level_from_xp(xp),
        "daily_goal": int(bucket.get("daily_goal") or 1),
        "daily_completed_today": int(bucket.get("daily_completed_today") or 0),
        "missions_done": bucket.get("missions_done") or {},
        "checklists": bucket.get("checklists") or {},
    }


def update_progress(
    user_id: str,
    *,
    slug: str,
    read_seconds: int = 0,
    completed: bool = False,
    index: dict[str, Any],
) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    progress = bucket.setdefault("progress", {})
    entry = progress.setdefault(slug, {"first_read_at": _now(), "read_count": 0})
    entry["read_count"] = int(entry.get("read_count") or 0) + 1
    entry["last_read_at"] = _now()
    if read_seconds > 0:
        entry["read_seconds"] = int(entry.get("read_seconds") or 0) + read_seconds
        bucket["total_read_seconds"] = int(bucket.get("total_read_seconds") or 0) + read_seconds
    if completed:
        entry["completed"] = True
        if not entry.get("xp_awarded"):
            _add_xp(bucket, XP_PER_COMPLETE)
            entry["xp_awarded"] = True
            _daily_tick(bucket)
            bucket["daily_completed_today"] = int(bucket.get("daily_completed_today") or 0) + 1
    entry["status"] = doc_status(entry)
    bucket["last_slug"] = slug
    bucket["last_active_at"] = _now()
    new_badges = _award_badges(bucket, index)
    _save(state)
    return {
        "success": True,
        "slug": slug,
        "new_badges": new_badges,
        **get_progress(user_id, index),
    }


def get_badges(user_id: str) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    earned = set(bucket.get("badges") or [])
    return {
        "success": True,
        "badges": [{**b, "earned": b["id"] in earned} for b in BADGE_DEFS],
    }


def toggle_favorite(user_id: str, slug: str) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    favs: list[str] = list(bucket.get("favorites") or [])
    if slug in favs:
        favs.remove(slug)
        added = False
    else:
        favs.append(slug)
        added = True
    bucket["favorites"] = favs
    _save(state)
    return {"success": True, "slug": slug, "favorited": added, "favorites": favs}


def get_favorites(user_id: str) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    return {"success": True, "favorites": bucket.get("favorites") or []}


def save_note(user_id: str, slug: str, content: str) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    notes = bucket.setdefault("notes", {})
    notes[slug] = {"content": content, "updated_at": _now()}
    _save(state)
    return {"success": True, "slug": slug, "updated_at": notes[slug]["updated_at"]}


def get_notes(user_id: str, slug: str = "") -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    notes = bucket.get("notes") or {}
    if slug:
        return {"success": True, "slug": slug, "note": notes.get(slug)}
    return {"success": True, "notes": notes}


def save_quiz_score(user_id: str, slug: str, score: int, total: int) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    scores = bucket.setdefault("quiz_scores", {})
    scores[slug] = {"score": score, "total": total, "percent": round(100 * score / total, 1) if total else 0, "at": _now()}
    if total and score == total:
        _add_xp(bucket, 30)
    _save(state)
    return {"success": True, **scores[slug]}


def save_checklist(user_id: str, slug: str, checklist: dict[str, bool]) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    checklists = bucket.setdefault("checklists", {})
    checklists[slug] = {**checklist, "updated_at": _now()}
    progress = bucket.setdefault("progress", {})
    entry = progress.setdefault(slug, {"first_read_at": _now(), "read_count": 0})
    entry["checklist"] = checklist
    entry["status"] = doc_status(entry)
    if all(checklist.values()) and checklist:
        entry["completed"] = True
        if not entry.get("xp_awarded"):
            _add_xp(bucket, XP_PER_COMPLETE)
            entry["xp_awarded"] = True
    _save(state)
    return {"success": True, "slug": slug, "checklist": checklist, "status": entry.get("status")}


def complete_mission(user_id: str, slug: str, mission_id: str, index: dict[str, Any]) -> dict[str, Any]:
    state = _load()
    bucket = _user_bucket(state, user_id)
    missions = bucket.setdefault("missions_done", {})
    key = f"{slug}:{mission_id}"
    if key not in missions:
        missions[key] = _now()
        _add_xp(bucket, XP_PER_MISSION)
    _award_badges(bucket, index)
    _save(state)
    xp = int(bucket.get("xp") or 0)
    return {"success": True, "mission_id": mission_id, "xp": xp, "level": _level_from_xp(xp)}
