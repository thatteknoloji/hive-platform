"""HIVE Academy V3 — health, quality, missions, knowledge graph, AI assist."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ACADEMY_ROOT = Path(__file__).resolve().parent.parent.parent / "docs" / "academy"
INDEX_FILE = ACADEMY_ROOT / "academy-index.json"
MISSIONS_FILE = ACADEMY_ROOT / "missions.json"
GRAPH_FILE = ACADEMY_ROOT / "knowledge-graph.json"
CERT_FILE = ACADEMY_ROOT / "certifications.json"
QUIZZES_FILE = ACADEMY_ROOT / "quizzes.json"
SCREENSHOTS_DIR = ACADEMY_ROOT / "screenshots"
LEARNING_PATH_FILE = ACADEMY_ROOT / "learning-path-v3.json"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

# Kairos AI priority: Academy → Encyclopedia → Workflow → API → Changelog → code
AI_KNOWLEDGE_PRIORITY = ["academy", "encyclopedia", "workflow", "api", "changelog", "code"]

DEFAULT_LEARNING_PATH = [
    {"id": "baslangic", "label": "Başlangıç", "section_slugs": ["baslangic"]},
    {"id": "firma", "label": "Firma", "section_slugs": ["firma-proje", "ilk-gun"]},
    {"id": "domain", "label": "Domain", "section_slugs": ["firma-proje", "ilk-gun"]},
    {"id": "seo", "label": "SEO", "section_slugs": ["seo-geo-aeo", "ilk-gun"]},
    {"id": "geo", "label": "GEO", "section_slugs": ["seo-geo-aeo"]},
    {"id": "entity", "label": "Entity", "section_slugs": ["seo-geo-aeo", "modul-ansiklopedisi"]},
    {"id": "authority", "label": "Authority", "section_slugs": ["authority"]},
    {"id": "publisher", "label": "Publisher", "section_slugs": ["authority", "publish-pipeline"]},
    {"id": "deploy", "label": "Deploy", "section_slugs": ["deploy"]},
    {"id": "advanced", "label": "Advanced", "section_slugs": ["modul-ansiklopedisi"]},
    {"id": "developer", "label": "Developer", "section_slugs": ["api"]},
    {"id": "automation", "label": "Automation", "section_slugs": ["modul-ansiklopedisi"]},
    {"id": "blackops", "label": "BlackOps", "section_slugs": ["modul-ansiklopedisi"]},
    {"id": "enterprise", "label": "Enterprise", "section_slugs": ["certification"]},
]

CERTIFICATIONS = [
    {"id": "cert_operator", "title": "HIVE Certified Operator", "status": "placeholder"},
    {"id": "cert_seo", "title": "HIVE Certified SEO Expert", "status": "placeholder"},
    {"id": "cert_geo", "title": "HIVE Certified GEO Expert", "status": "placeholder"},
    {"id": "cert_authority", "title": "HIVE Certified Authority Engineer", "status": "placeholder"},
    {"id": "cert_partner", "title": "HIVE Certified Enterprise Partner", "status": "placeholder"},
]

# TODO V3+: Sandbox Mode — demo environment for hands-on tasks
# TODO V3+: Voice Search
# TODO V3+: Video Academy full player
# TODO V3+: Partner Academy tenant isolation
# TODO V3+: Marketplace Learning catalog


def _parse_fm(text: str) -> tuple[dict[str, Any], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta: dict[str, Any] = {}
    list_key = None
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- ") and list_key:
            meta.setdefault(list_key, []).append(line[2:].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip().strip('"')
        if not v:
            list_key = k
            meta[k] = []
        else:
            list_key = None
            meta[k] = v
    return meta, m.group(2).strip()


def load_learning_path() -> list[dict[str, Any]]:
    if LEARNING_PATH_FILE.exists():
        try:
            data = json.loads(LEARNING_PATH_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_LEARNING_PATH


def load_missions() -> dict[str, Any]:
    if MISSIONS_FILE.exists():
        try:
            return json.loads(MISSIONS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def load_graph() -> dict[str, Any]:
    if GRAPH_FILE.exists():
        try:
            return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def doc_status(progress_entry: dict[str, Any] | None) -> str:
    if not progress_entry:
        return "not_started"
    if progress_entry.get("completed"):
        return "completed"
    if progress_entry.get("read_count") or progress_entry.get("checklist"):
        return "in_progress"
    return "not_started"


def quality_score(slug: str, path: Path, meta: dict[str, Any], body: str) -> dict[str, Any]:
    has_quiz = slug in _load_json(QUIZZES_FILE, {})
    has_shots = (SCREENSHOTS_DIR / slug).is_dir() and any((SCREENSHOTS_DIR / slug).iterdir())
    has_mermaid = "```mermaid" in body
    has_api = bool(meta.get("related_api")) or "/api/" in body
    has_video = "video" in body.lower() or meta.get("related_videos")
    has_ai_slot = "AI_UPDATE_SLOT" in body
    is_published = meta.get("status") == "published"
    word_count = len(re.findall(r"\w+", body))

    scores = {
        "content": min(100, 40 + word_count // 20) if word_count > 100 else max(20, word_count // 3),
        "screenshot": 90 if has_shots else (30 if "Screenshot placeholder" in body else 10),
        "workflow": 85 if has_mermaid else 20,
        "api": 80 if has_api else 15,
        "quiz": 90 if has_quiz else 10,
        "video": 70 if has_video else 5,
        "ai_ready": 95 if has_ai_slot else 40,
        "published": 100 if is_published else 50,
    }
    weights = {"content": 25, "screenshot": 15, "workflow": 15, "api": 10, "quiz": 15, "video": 5, "ai_ready": 10, "published": 5}
    total = round(sum(scores[k] * weights[k] / 100 for k in weights), 1)
    return {"slug": slug, "scores": scores, "total": total}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def documentation_health(index: dict[str, Any]) -> dict[str, Any]:
    quizzes = _load_json(QUIZZES_FILE, {})
    missing_modules: list[str] = []
    try:
        from app.moduller.liste import MODULLER
        enc_dir = ACADEMY_ROOT / "06-modul-ansiklopedisi"
        for mod in MODULLER:
            mid = mod["id"]
            if not (enc_dir / f"{mid}.md").is_file():
                missing_modules.append(mid)
    except Exception:
        pass

    stats = {
        "total": 0,
        "published": 0,
        "auto_draft": 0,
        "draft": 0,
        "missing_screenshot": 0,
        "missing_video": 0,
        "missing_quiz": 0,
        "ai_update_pending": 0,
        "stale_version": 0,
        "low_quality": 0,
    }
    items_detail: list[dict[str, Any]] = []

    for section in index.get("sections") or []:
        for item in section.get("items") or []:
            slug = item.get("slug") or ""
            rel = item.get("path") or ""
            path = ACADEMY_ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            meta, body = _parse_fm(text)
            stats["total"] += 1
            st = meta.get("status") or item.get("status") or "draft"
            if st == "published":
                stats["published"] += 1
            elif st == "auto-draft":
                stats["auto_draft"] += 1
            else:
                stats["draft"] += 1
            if not (SCREENSHOTS_DIR / slug).is_dir():
                stats["missing_screenshot"] += 1
            if slug not in quizzes:
                stats["missing_quiz"] += 1
            if "video" not in body.lower() and not meta.get("related_videos"):
                stats["missing_video"] += 1
            if "TODO" in body or "EKSİK_BİLGİ" in body:
                stats["ai_update_pending"] += 1
            lu = meta.get("last_updated") or item.get("last_updated") or ""
            if lu and lu < "2026-06-01":
                stats["stale_version"] += 1
            qs = quality_score(slug, path, meta, body)
            if qs["total"] < 50:
                stats["low_quality"] += 1
            items_detail.append({"slug": slug, "title": item.get("title"), "quality": qs["total"], "status": st})

    return {
        "success": True,
        "stats": stats,
        "missing_module_docs": missing_modules[:30],
        "missing_module_count": len(missing_modules),
        "live_sync_warning": len(missing_modules) > 0,
        "items": sorted(items_detail, key=lambda x: x.get("quality", 0))[:50],
        "certifications": CERTIFICATIONS,
    }


def knowledge_graph_for_slug(slug: str) -> dict[str, Any]:
    graph = load_graph()
    if slug in graph:
        return {"success": True, "slug": slug, "nodes": graph[slug]}
    # fallback from missions + meta
    missions = load_missions().get(slug, {})
    related = missions.get("related_slugs") or []
    return {
        "success": True,
        "slug": slug,
        "nodes": [{"type": "doc", "slug": r, "label": r} for r in related],
    }


def ai_assist(query: str, index: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    """Academy-only RAG-lite — Kairos AI first knowledge source."""
    q = (query or "").strip().lower()
    if not q:
        return {"success": True, "answer": "", "sources": [], "priority": AI_KNOWLEDGE_PRIORITY}

    hits: list[dict[str, Any]] = []
    for section in index.get("sections") or []:
        for item in section.get("items") or []:
            slug = item.get("slug") or ""
            rel = item.get("path") or ""
            path = ACADEMY_ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            meta, body = _parse_fm(text)
            blob = f"{item.get('title')} {slug} {body}".lower()
            score = sum(3 for tok in re.findall(r"[\wğüşıöç]+", q) if tok in blob)
            if score <= 0:
                continue
            # extract best paragraph
            paras = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 40]
            best = ""
            for p in paras:
                if any(tok in p.lower() for tok in re.findall(r"[\wğüşıöç]+", q)):
                    best = p[:400]
                    break
            if not best and paras:
                best = paras[0][:400]
            hits.append({
                "slug": slug,
                "title": item.get("title"),
                "section": section.get("title"),
                "score": score,
                "excerpt": best,
                "source_type": "encyclopedia" if section.get("slug") == "modul-ansiklopedisi" else "academy",
            })

    hits.sort(key=lambda x: x["score"], reverse=True)
    top = hits[:limit]
    answer_parts = [h["excerpt"] for h in top if h.get("excerpt")]
    answer = "\n\n".join(answer_parts[:3]) if answer_parts else (
        "Academy'de bu konuyla ilgili doğrudan bir eşleşme bulamadım. "
        "İlgili modül ansiklopedisi veya Troubleshooting bölümüne bakın."
    )
    return {
        "success": True,
        "answer": answer,
        "sources": top,
        "priority": AI_KNOWLEDGE_PRIORITY,
        "disclaimer": "Yanıt yalnızca HIVE Academy kaynaklarından üretilmiştir (internet kullanılmaz).",
    }


def palette_search(query: str, index: dict[str, Any]) -> dict[str, Any]:
    q = (query or "").strip().lower()
    results: list[dict[str, Any]] = []
    if not q:
        return {"success": True, "results": []}

    for section in index.get("sections") or []:
        for item in section.get("items") or []:
            title = (item.get("title") or "").lower()
            slug = item.get("slug") or ""
            if q in title or q in slug:
                results.append({"type": "doc", "id": slug, "label": item.get("title"), "section": section.get("title")})

    try:
        from app.moduller.liste import MODULLER
        for mod in MODULLER:
            if q in mod["ad"].lower() or q in mod["id"]:
                results.append({"type": "module", "id": mod["id"], "label": mod["ad"], "section": mod.get("grup", "")})
                results.append({"type": "api", "id": mod["id"], "label": mod.get("endpoint", f"/api/{mod['id']}"), "section": "API"})
    except Exception:
        pass

    missions = load_missions()
    for slug, m in missions.items():
        if q in slug or q in json.dumps(m, ensure_ascii=False).lower():
            results.append({"type": "workflow", "id": slug, "label": m.get("title", slug), "section": "Mission"})

    if "sorun" in q or "hata" in q or "troubleshoot" in q:
        results.append({"type": "doc", "id": "troubleshooting-readme", "label": "Sorun Giderme", "section": "Troubleshooting"})

    return {"success": True, "query": query, "results": results[:40]}
