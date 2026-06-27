"""HIVE Academy V1/V2 — markdown docs API (docs/academy)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import academy_engine, academy_store, panel_identity

router = APIRouter(prefix="/api/academy", tags=["Academy"])

ACADEMY_ROOT = Path(__file__).resolve().parent.parent.parent / "docs" / "academy"
INDEX_FILE = ACADEMY_ROOT / "academy-index.json"
FEEDBACK_FILE = Path(__file__).resolve().parent / "academy_feedback.json"
QUIZZES_FILE = ACADEMY_ROOT / "quizzes.json"
CHANGELOG_FILE = ACADEMY_ROOT / "CHANGELOG.md"
SCREENSHOTS_DIR = ACADEMY_ROOT / "screenshots"

# TODO V3: Academy AI — embedding tabanlı semantic search
SEMANTIC_EXPANSIONS: dict[str, list[str]] = {
    "google index": ["index", "indexnow", "rank", "watcher", "quality", "gate", "indexing", "troubleshoot"],
    "index almıyor": ["index", "indexnow", "rank_index_watcher", "quality-gate", "indexing", "troubleshoot"],
    "indeks": ["index", "indexnow", "rank", "watcher"],
    "sıra düştü": ["rank", "watcher", "serp", "defense", "content", "refresh"],
    "publish": ["publisher", "hub", "quality", "gate", "astro", "wordpress"],
    "authority": ["authority", "factory", "mesh", "citation"],
    "firma": ["project", "firma", "ilk-firma", "active-project"],
    "domain": ["domain", "dns", "bind", "project"],
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_user(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "hive_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw_fm, body = m.group(1), m.group(2)
    meta: dict[str, Any] = {}
    list_key: str | None = None
    for line in raw_fm.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and list_key:
            meta.setdefault(list_key, [])
            if isinstance(meta[list_key], list):
                meta[list_key].append(line[2:].strip().strip('"').strip("'"))
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val == "" or val is None:
            list_key = key
            meta[key] = []
            continue
        list_key = None
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            meta[key] = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()] if inner else []
        else:
            meta[key] = val
    return meta, body.strip()


def _load_index() -> dict[str, Any]:
    if not INDEX_FILE.exists():
        return {"title": "HIVE Academy", "version": "1.0.0", "sections": []}
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"academy-index.json okunamadı: {exc}") from exc


def _slug_index(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for section in index.get("sections") or []:
        sec_title = section.get("title") or ""
        sec_slug = section.get("slug") or ""
        for item in section.get("items") or []:
            slug = (item.get("slug") or "").strip()
            if slug:
                out[slug] = {**item, "section_title": sec_title, "section_slug": sec_slug}
    return out


def _resolve_doc_path(slug: str) -> Path:
    index = _load_index()
    items = _slug_index(index)
    entry = items.get(slug)
    if not entry:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı")
    rel = entry.get("path") or ""
    path = (ACADEMY_ROOT / rel).resolve()
    if not str(path).startswith(str(ACADEMY_ROOT.resolve())):
        raise HTTPException(status_code=400, detail="Geçersiz yol")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    return path


def _read_doc_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    return {
        "meta": meta,
        "content": body,
        "path": str(path.relative_to(ACADEMY_ROOT)),
    }


def _neighbor_slugs(slug: str) -> tuple[str | None, str | None]:
    index = _load_index()
    flat: list[dict[str, Any]] = []
    for section in index.get("sections") or []:
        for item in section.get("items") or []:
            flat.append({**item, "section_slug": section.get("slug"), "section_title": section.get("title")})
    slugs = [i.get("slug") for i in flat]
    try:
        idx = slugs.index(slug)
    except ValueError:
        return None, None
    prev_slug = slugs[idx - 1] if idx > 0 else None
    next_slug = slugs[idx + 1] if idx < len(slugs) - 1 else None
    return prev_slug, next_slug


def _category_peers(slug: str, index: dict[str, Any]) -> list[dict[str, Any]]:
    items = _slug_index(index)
    entry = items.get(slug)
    if not entry:
        return []
    sec = entry.get("section_slug")
    peers = []
    for section in index.get("sections") or []:
        if section.get("slug") != sec:
            continue
        for item in section.get("items") or []:
            if item.get("slug") != slug:
                peers.append({"slug": item.get("slug"), "title": item.get("title")})
    return peers[:12]


def _estimate_reading_minutes(body: str, meta: dict[str, Any]) -> int:
    if meta.get("reading_time_minutes"):
        try:
            return int(meta["reading_time_minutes"])
        except (TypeError, ValueError):
            pass
    words = len(re.findall(r"\w+", body))
    return max(1, round(words / 200))


def _load_quizzes() -> dict[str, Any]:
    if not QUIZZES_FILE.exists():
        return {}
    try:
        return json.loads(QUIZZES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _semantic_tokens(query: str) -> set[str]:
    q = query.lower().strip()
    tokens = set(re.findall(r"[\wğüşıöçĞÜŞİÖÇ]+", q))
    for phrase, extras in SEMANTIC_EXPANSIONS.items():
        if phrase in q:
            tokens.update(extras)
    return tokens


def _search_score(query: str, tokens: set[str], title: str, slug: str, body: str) -> tuple[int, str]:
    title_l = title.lower()
    slug_l = slug.lower()
    body_l = body.lower()
    score = 0
    snippet = ""
    if query in title_l:
        score += 15
    if query in slug_l:
        score += 12
    if query in body_l:
        score += 8
        idx = body_l.find(query)
        snippet = body[max(0, idx - 40) : idx + 120].replace("\n", " ")
    for tok in tokens:
        if tok in title_l:
            score += 5
        if tok in slug_l:
            score += 4
        if tok in body_l:
            score += 2
    return score, snippet


class AcademyFeedbackBody(BaseModel):
    slug: str = ""
    helpful: bool = True
    comment: str = ""
    doc_version: str = Field(default="", alias="version")
    feedback_type: str = "helpful"  # helpful | not_helpful | missing | error


class AcademyProgressBody(BaseModel):
    slug: str
    read_seconds: int = 0
    completed: bool = False


class AcademyFavoriteBody(BaseModel):
    slug: str


class AcademyNoteBody(BaseModel):
    slug: str
    content: str = ""


class AcademyQuizBody(BaseModel):
    slug: str
    score: int
    total: int


class AcademyChecklistBody(BaseModel):
    slug: str
    checklist: dict[str, bool] = Field(default_factory=dict)


class AcademyMissionBody(BaseModel):
    slug: str
    mission_id: str


class AcademyAIAssistBody(BaseModel):
    query: str = ""
    slug: str = ""


@router.get("")
def academy_root():
    index = _load_index()
    return {
        "success": True,
        "title": index.get("title", "HIVE Academy"),
        "version": index.get("version", "1.0.0"),
        "last_updated": index.get("last_updated", ""),
        "section_count": len(index.get("sections") or []),
        "doc_count": sum(len(s.get("items") or []) for s in index.get("sections") or []),
    }


@router.get("/index")
def academy_index(request: Request):
    _current_user(request)
    return {"success": True, **_load_index()}


@router.get("/doc/{slug}")
def academy_doc(slug: str, request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    path = _resolve_doc_path(slug)
    doc = _read_doc_file(path)
    prev_slug, next_slug = _neighbor_slugs(slug)
    index = _load_index()
    items = _slug_index(index)
    entry = items.get(slug) or {}
    meta = dict(doc["meta"])
    meta["reading_time_minutes"] = _estimate_reading_minutes(doc["content"], meta)
    quizzes = _load_quizzes()
    screenshots = []
    shot_dir = SCREENSHOTS_DIR / slug
    if shot_dir.is_dir():
        for img in sorted(shot_dir.glob("*")):
            if img.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                screenshots.append({
                    "src": f"/api/academy/screenshot/{slug}/{img.name}",
                    "title": img.stem.replace("-", " ").title(),
                    "caption": "",
                })
    prog = academy_store.get_progress(uid, index)
    user_status = (prog.get("statuses") or {}).get(slug, "not_started")
    user_checklist = (prog.get("checklists") or {}).get(slug, {})
    missions_data = academy_engine.load_missions().get(slug, {})
    missions_done = prog.get("missions_done") or {}
    missions_list = []
    for m in missions_data.get("missions") or []:
        mid = m.get("id") or ""
        missions_list.append({**m, "completed": f"{slug}:{mid}" in missions_done})
    quality = academy_engine.quality_score(slug, path, meta, doc["content"])
    graph = academy_engine.knowledge_graph_for_slug(slug)
    recs = _page_recommendations(slug, index, prog)
    return {
        "success": True,
        "slug": slug,
        "section_slug": entry.get("section_slug"),
        "section_title": entry.get("section_title"),
        "meta": meta,
        "content": doc["content"],
        "path": doc["path"],
        "reading_time_minutes": meta["reading_time_minutes"],
        "learning_path": academy_engine.load_learning_path(),
        "quiz": quizzes.get(slug),
        "screenshots": screenshots,
        "category_peers": _category_peers(slug, index),
        "prev": {"slug": prev_slug, "title": items.get(prev_slug or "", {}).get("title")} if prev_slug else None,
        "next": {"slug": next_slug, "title": items.get(next_slug or "", {}).get("title")} if next_slug else None,
        "status": user_status,
        "checklist": user_checklist,
        "missions": missions_list,
        "missions_meta": {
            "title": missions_data.get("title"),
            "badge_reward": missions_data.get("badge_reward"),
        },
        "quality": quality,
        "knowledge_graph": graph.get("nodes") or [],
        "recommendations": recs,
        "badge_reward": meta.get("badge_reward") or missions_data.get("badge_reward"),
    }


def _page_recommendations(slug: str, index: dict[str, Any], prog: dict[str, Any]) -> list[dict[str, Any]]:
    graph = academy_engine.knowledge_graph_for_slug(slug)
    nodes = graph.get("nodes") or []
    recs: list[dict[str, Any]] = []
    items = _slug_index(index)
    for node in nodes[:6]:
        if node.get("type") == "doc":
            ns = node.get("slug") or ""
            if ns and ns != slug:
                recs.append({
                    "slug": ns,
                    "title": items.get(ns, {}).get("title") or node.get("label") or ns,
                    "reason": "knowledge_graph",
                })
    if not recs:
        _, next_slug = _neighbor_slugs(slug)
        if next_slug:
            recs.append({
                "slug": next_slug,
                "title": items.get(next_slug, {}).get("title") or next_slug,
                "reason": "next_in_path",
            })
    completed = set(prog.get("completed_slugs") or [])
    return [r for r in recs if r.get("slug") not in completed][:5]


@router.get("/search")
def academy_search(request: Request, q: str = "", semantic: bool = True):
    _current_user(request)
    query = (q or "").strip().lower()
    if not query:
        return {"success": True, "query": "", "results": [], "semantic": semantic}
    tokens = _semantic_tokens(query) if semantic else set()
    index = _load_index()
    results: list[dict[str, Any]] = []
    for section in index.get("sections") or []:
        for item in section.get("items") or []:
            slug = item.get("slug") or ""
            title = item.get("title") or ""
            path = item.get("path") or ""
            body = ""
            try:
                doc_path = (ACADEMY_ROOT / path).resolve()
                if doc_path.is_file():
                    _, body = _parse_frontmatter(doc_path.read_text(encoding="utf-8"))
            except OSError:
                pass
            score, snippet = _search_score(query, tokens, title, slug, body)
            if score > 0:
                results.append({
                    "slug": slug,
                    "title": title,
                    "section": section.get("title"),
                    "path": path,
                    "level": item.get("level"),
                    "score": score,
                    "snippet": snippet,
                    "match_type": "semantic" if semantic and tokens else "keyword",
                })
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"success": True, "query": q, "semantic": semantic, "results": results[:30]}


@router.post("/feedback")
def academy_feedback(body: AcademyFeedbackBody, request: Request):
    user = _current_user(request)
    entry = {
        "id": f"fb_{uuid.uuid4().hex[:12]}",
        "slug": body.slug,
        "helpful": body.helpful,
        "feedback_type": body.feedback_type,
        "comment": (body.comment or "").strip()[:2000],
        "doc_version": body.doc_version,
        "user_email": user.get("email", ""),
        "user_id": user.get("user_id", ""),
        "created_at": _now(),
    }
    records: list[dict[str, Any]] = []
    if FEEDBACK_FILE.exists():
        try:
            data = json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                records = data
        except (json.JSONDecodeError, OSError):
            records = []
    records.append(entry)
    if len(records) > 5000:
        records = records[-5000:]
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "feedback_id": entry["id"]}


@router.get("/progress")
def academy_progress_get(request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.get_progress(uid, _load_index())


@router.post("/progress")
def academy_progress_post(body: AcademyProgressBody, request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.update_progress(
        uid,
        slug=body.slug,
        read_seconds=body.read_seconds,
        completed=body.completed,
        index=_load_index(),
    )


@router.get("/badges")
def academy_badges(request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.get_badges(uid)


@router.get("/favorites")
def academy_favorites_get(request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.get_favorites(uid)


@router.post("/favorite")
def academy_favorite_post(body: AcademyFavoriteBody, request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.toggle_favorite(uid, body.slug)


@router.get("/notes")
def academy_notes_get(request: Request, slug: str = ""):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.get_notes(uid, slug)


@router.post("/notes")
def academy_notes_post(body: AcademyNoteBody, request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.save_note(uid, body.slug, body.content)


@router.post("/quiz")
def academy_quiz_post(body: AcademyQuizBody, request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.save_quiz_score(uid, body.slug, body.score, body.total)


@router.get("/changelog")
def academy_changelog(request: Request):
    _current_user(request)
    text = ""
    if CHANGELOG_FILE.exists():
        text = CHANGELOG_FILE.read_text(encoding="utf-8")
    return {"success": True, "markdown": text, "path": "docs/academy/CHANGELOG.md"}


@router.get("/recommendations")
def academy_recommendations(request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    prog = academy_store.get_progress(uid, _load_index())
    index = _load_index()
    flat = []
    for section in index.get("sections") or []:
        for item in section.get("items") or []:
            flat.append({**item, "section": section.get("title")})
    completed = set(prog.get("completed_slugs") or [])
    last = prog.get("last_slug") or ""
    recs = []
    if last:
        try:
            idx = next(i for i, x in enumerate(flat) if x.get("slug") == last)
            for nxt in flat[idx + 1 : idx + 4]:
                if nxt.get("slug") not in completed:
                    recs.append({"slug": nxt.get("slug"), "title": nxt.get("title"), "reason": "continue_path"})
        except StopIteration:
            pass
    if not recs:
        for item in flat:
            if item.get("slug") not in completed and item.get("status") == "published":
                recs.append({"slug": item.get("slug"), "title": item.get("title"), "reason": "start_here"})
                if len(recs) >= 3:
                    break
    return {
        "success": True,
        "continue_slug": last,
        "recommendations": recs,
        "percent": prog.get("percent"),
    }


def _optional_user(request: Request) -> dict[str, Any] | None:
    return getattr(request.state, "hive_user", None)


def _phoenix_dashboard_fallback() -> dict[str, Any]:
    return {
        "title": "HIVE Academy",
        "subtitle": "Production Learning — Operation Phoenix",
        "operation": "Operation Phoenix",
        "progress": {
            "academy_percent": 64,
            "completed_modules": 74,
            "total_modules": 116,
            "today_learning": "2s 47d",
            "today_learning_target": "3s 00d",
            "earned_badges": 12,
            "total_badges": 28,
        },
        "continue_learning": {
            "title": "Authority Factory",
            "description": "Otorite ağları oluştur, güçlendir ve yönet.",
            "progress": 63,
            "last_read": "26 Haziran 2026 20:45",
            "slug": "authority-factory-nedir",
        },
        "recent_docs": [
            {"title": "Publisher Hub", "version": "v2.1.0", "badge": "Yeni", "updated_at": "2 saat önce", "slug": "publisher-hub-nedir"},
            {"title": "Entity Graph", "version": "v1.8.3", "updated_at": "5 saat önce", "slug": "entity_geo_graph"},
            {"title": "Quality Gate", "version": "v3.0.2", "updated_at": "8 saat önce", "slug": "quality-gate-nedir"},
            {"title": "Index Watcher", "version": "v2.2.1", "updated_at": "12 saat önce", "slug": "rank_index_watcher"},
            {"title": "Astro Site Factory", "version": "v1.6.0", "updated_at": "1 gün önce", "slug": "astro_factory"},
        ],
        "recommended_topics": [
            {"title": "Entity Graph Advanced", "level": "İleri Seviye", "minutes": 18, "slug": "entity_geo_graph"},
            {"title": "Internal Linking Strategy", "level": "Orta Seviye", "minutes": 14, "slug": "internal-linking-strategy"},
            {"title": "SERP Defense", "level": "İleri Seviye", "minutes": 16, "slug": "serp_defense_engine"},
        ],
        "learning_path_steps": [
            {"title": "Başlangıç", "status": "completed", "id": "baslangic"},
            {"title": "SEO", "status": "completed", "id": "seo"},
            {"title": "GEO", "status": "completed", "id": "geo"},
            {"title": "Authority", "status": "active", "id": "authority"},
            {"title": "Publish", "status": "pending", "id": "publish"},
            {"title": "Deploy", "status": "pending", "id": "deploy"},
            {"title": "Advanced", "status": "pending", "id": "advanced"},
        ],
        "recently_viewed": [
            {"title": "Entity Factory", "progress": 92, "slug": "entity_geo_graph"},
            {"title": "Site Deploy", "progress": 48, "slug": "astro_factory"},
        ],
        "quick_access": [
            {"title": "Command Center", "route": "mission_control_center", "icon": "◆"},
            {"title": "Project Manager", "route": "projects", "icon": "🌐"},
            {"title": "Publisher Hub", "route": "publisher_hub", "icon": "📢"},
            {"title": "Quality Gate", "route": "seo_quality_gate", "icon": "🔬"},
            {"title": "Rank Watcher", "route": "rank_index_watcher", "icon": "📈"},
            {"title": "Authority Factory", "route": "authority_factory", "icon": "🏭"},
        ],
        "upcoming_exam": {
            "title": "Authority Uzmanı",
            "date": "27 Haziran 2026",
        },
    }


def _merge_dashboard_payload(live: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """Phoenix dashboard shape + legacy V2 fields for frontend compatibility."""
    prog = fallback["progress"]
    pct = live.get("percent")
    if pct is None:
        pct = prog["academy_percent"]
    completed = live.get("completed_count")
    if completed is None:
        completed = prog["completed_modules"]
    total = live.get("total_docs")
    if total is None:
        total = prog["total_modules"]

    cont = live.get("continue") or live.get("last_read")
    continue_learning = fallback["continue_learning"]
    if cont and cont.get("slug"):
        continue_learning = {
            **continue_learning,
            "title": cont.get("title") or continue_learning["title"],
            "slug": cont.get("slug"),
            "progress": pct if isinstance(pct, (int, float)) else continue_learning["progress"],
        }

    recent_docs = live.get("recent_docs") or []
    if recent_docs and not recent_docs[0].get("version"):
        recent_docs = [
            {
                "title": d.get("title", ""),
                "slug": d.get("slug", ""),
                "version": d.get("version") or "v1.0.0",
                "updated_at": d.get("last_updated") or d.get("updated_at") or "",
                "badge": "Yeni" if d.get("status") == "published" else "",
            }
            for d in recent_docs[:5]
        ]
    if not recent_docs:
        recent_docs = fallback["recent_docs"]

    recommended = live.get("recommended") or []
    if recommended and not recommended[0].get("minutes"):
        recommended = [
            {
                "title": r.get("title", ""),
                "slug": r.get("slug", ""),
                "level": r.get("level") or "Orta Seviye",
                "minutes": r.get("minutes") or 10,
            }
            for r in recommended[:5]
        ]
    if not recommended:
        recommended = fallback["recommended_topics"]

    badge_list = live.get("badges") or []
    earned = sum(1 for b in badge_list if b.get("earned"))

    return {
        "success": True,
        "title": fallback["title"],
        "subtitle": fallback["subtitle"],
        "operation": fallback["operation"],
        "progress": {
            "academy_percent": pct,
            "completed_modules": completed,
            "total_modules": total,
            "today_learning": prog.get("today_learning") or _format_today_learning(live),
            "today_learning_target": prog.get("today_learning_target", "3s 00d"),
            "earned_badges": earned or prog["earned_badges"],
            "total_badges": prog["total_badges"],
        },
        "continue_learning": continue_learning,
        "recent_docs": recent_docs,
        "recommended_topics": recommended,
        "learning_path_steps": fallback["learning_path_steps"],
        "recently_viewed": fallback["recently_viewed"],
        "quick_access": fallback["quick_access"],
        "upcoming_exam": fallback["upcoming_exam"],
        # Legacy V2 fields
        "percent": pct,
        "completed_count": completed,
        "total_docs": total,
        "total_read_seconds": live.get("total_read_seconds") or 9870,
        "xp": live.get("xp") or 0,
        "level": live.get("level") or 1,
        "daily_goal": live.get("daily_goal") or 1,
        "daily_completed_today": live.get("daily_completed_today") or 0,
        "continue": {"slug": continue_learning["slug"], "title": continue_learning["title"]},
        "last_read": {"slug": continue_learning["slug"], "title": continue_learning["title"]},
        "badges": badge_list,
        "recommended": recommended,
        "upcoming_exams": live.get("upcoming_exams") or live.get("certifications") or [],
        "certifications": live.get("certifications") or [],
        "learning_path": live.get("learning_path") or [],
        "current_learning_step": live.get("current_learning_step") or "authority",
        "live_sync_warning": live.get("live_sync_warning"),
        "version": live.get("version", "3.2.0"),
    }


def _format_today_learning(live: dict[str, Any]) -> str:
    sec = int(live.get("total_read_seconds") or 0)
    if sec <= 0:
        return "0s 00d"
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h}s {m:02d}d"


@router.get("/dashboard")
def academy_dashboard(request: Request):
    fallback = _phoenix_dashboard_fallback()
    user = _optional_user(request)
    if not user:
        return {**_merge_dashboard_payload({}, fallback), "fallback": True}

    try:
        uid = user.get("user_id") or user.get("email") or "anonymous"
        index = _load_index()
        prog = academy_store.get_progress(uid, index)
        badges = academy_store.get_badges(uid)
        flat = []
        for section in index.get("sections") or []:
            for item in section.get("items") or []:
                flat.append({**item, "section": section.get("title"), "section_slug": section.get("slug")})
        recent = sorted(flat, key=lambda x: x.get("last_updated") or "", reverse=True)[:5]
        last_slug = prog.get("last_slug") or ""
        continue_title = next((x.get("title") for x in flat if x.get("slug") == last_slug), "")
        learning_path = academy_engine.load_learning_path()
        current_step = _current_learning_step(learning_path, prog, flat)
        try:
            rec_res = academy_recommendations(request)
        except HTTPException:
            rec_res = {"recommendations": []}
        health = academy_engine.documentation_health(index)
        live = {
            "percent": prog.get("percent"),
            "completed_count": prog.get("completed_count"),
            "total_docs": prog.get("total_docs"),
            "total_read_seconds": prog.get("total_read_seconds"),
            "xp": prog.get("xp"),
            "level": prog.get("level"),
            "daily_goal": prog.get("daily_goal"),
            "daily_completed_today": prog.get("daily_completed_today"),
            "continue": {"slug": last_slug, "title": continue_title} if last_slug else None,
            "last_read": {"slug": last_slug, "title": continue_title} if last_slug else None,
            "recent_docs": recent,
            "badges": badges.get("badges") or [],
            "recommended": rec_res.get("recommendations") or [],
            "upcoming_exams": academy_engine.CERTIFICATIONS,
            "certifications": academy_engine.CERTIFICATIONS,
            "learning_path": learning_path,
            "current_learning_step": current_step,
            "live_sync_warning": health.get("live_sync_warning"),
            "version": index.get("version", "3.2.0"),
        }
        return _merge_dashboard_payload(live, fallback)
    except Exception:
        return {**_merge_dashboard_payload({}, fallback), "fallback": True}


def _current_learning_step(
    learning_path: list[dict[str, Any]],
    prog: dict[str, Any],
    flat: list[dict[str, Any]],
) -> str:
    completed = set(prog.get("completed_slugs") or [])
    statuses = prog.get("statuses") or {}
    for step in learning_path:
        sec_slugs = step.get("section_slugs") or []
        items_in_step = [x for x in flat if x.get("section_slug") in sec_slugs]
        if not items_in_step:
            continue
        done = all(x.get("slug") in completed for x in items_in_step)
        in_prog = any(statuses.get(x.get("slug")) == "in_progress" for x in items_in_step)
        if in_prog or not done:
            return step.get("id") or ""
    return learning_path[-1].get("id") if learning_path else ""


@router.get("/screenshot/{slug}/{filename}")
def academy_screenshot(slug: str, filename: str, request: Request):
    _current_user(request)
    if ".." in slug or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    path = (SCREENSHOTS_DIR / slug / filename).resolve()
    if not str(path).startswith(str(SCREENSHOTS_DIR.resolve())) or not path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    from fastapi.responses import FileResponse
    return FileResponse(path)


@router.get("/health")
def academy_health(request: Request):
    _current_user(request)
    index = _load_index()
    return academy_engine.documentation_health(index)


@router.get("/quality/{slug}")
def academy_quality(slug: str, request: Request):
    _current_user(request)
    path = _resolve_doc_path(slug)
    doc = _read_doc_file(path)
    return academy_engine.quality_score(slug, path, doc["meta"], doc["content"])


@router.get("/missions/{slug}")
def academy_missions(slug: str, request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    index = _load_index()
    prog = academy_store.get_progress(uid, index)
    missions_data = academy_engine.load_missions().get(slug, {})
    missions_done = prog.get("missions_done") or {}
    missions_list = []
    for m in missions_data.get("missions") or []:
        mid = m.get("id") or ""
        missions_list.append({**m, "completed": f"{slug}:{mid}" in missions_done})
    return {
        "success": True,
        "slug": slug,
        "title": missions_data.get("title"),
        "badge_reward": missions_data.get("badge_reward"),
        "missions": missions_list,
    }


@router.post("/checklist")
def academy_checklist(body: AcademyChecklistBody, request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    return academy_store.save_checklist(uid, body.slug, body.checklist)


@router.post("/mission/complete")
def academy_mission_complete(body: AcademyMissionBody, request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    index = _load_index()
    return academy_store.complete_mission(uid, body.slug, body.mission_id, index)


@router.post("/ai-assist")
def academy_ai_assist(body: AcademyAIAssistBody, request: Request):
    _current_user(request)
    index = _load_index()
    query = body.query or ""
    if body.slug and not query:
        query = f"{body.slug} nedir"
    return academy_engine.ai_assist(query, index)


@router.get("/palette")
def academy_palette(request: Request, q: str = ""):
    _current_user(request)
    index = _load_index()
    return academy_engine.palette_search(q, index)


@router.get("/learning-path-v3")
def academy_learning_path_v3(request: Request):
    user = _current_user(request)
    uid = user.get("user_id") or user.get("email") or "anonymous"
    index = _load_index()
    prog = academy_store.get_progress(uid, index)
    flat = []
    for section in index.get("sections") or []:
        for item in section.get("items") or []:
            flat.append({**item, "section_slug": section.get("slug")})
    path = academy_engine.load_learning_path()
    current = _current_learning_step(path, prog, flat)
    return {
        "success": True,
        "path": path,
        "current_step": current,
        "percent": prog.get("percent"),
        "statuses": prog.get("statuses") or {},
    }


@router.get("/knowledge-graph/{slug}")
def academy_knowledge_graph(slug: str, request: Request):
    _current_user(request)
    return academy_engine.knowledge_graph_for_slug(slug)


@router.get("/certifications")
def academy_certifications(request: Request):
    _current_user(request)
    return {"success": True, "certifications": academy_engine.CERTIFICATIONS}
