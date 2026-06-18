"""
HIVE Mentor V1 — kural tabanlı modül ve workflow rehberliği.

LLM zorunlu değil; intent eşleştirme ile yönlendirme yapar.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.mentor")

STATE_FILE = Path(__file__).resolve().parent.parent / "hive_mentor_state.json"

from app.moduller.hive_learn_content import MENTOR_EXTRA_RULES

INTENT_RULES: list[dict[str, Any]] = [
    {
        "intent": "keyword_growth",
        "keywords": ["yüksel", "yuksel", "büyüt", "buyut", "trafik", "keyword", "quick win", "fırsat", "firsat", "rank", "sıralama", "siralama"],
        "geo_keywords": ["kuşadası", "kusadasi", "gece", "mekan", "otel", "tatil", "geo"],
        "steps": [
            {"order": 1, "module_id": "opportunity_engine", "title": "Opportunity Engine", "reason": "Quick win ve trafik potansiyeli tespiti"},
            {"order": 2, "module_id": "crawl_gap_engine", "title": "Crawl Gap", "reason": "FAQ ve entity içerik boşlukları"},
            {"order": 3, "module_id": "authority_mesh_engine", "title": "Authority Mesh", "reason": "Support site ağı ile authority güçlendirme"},
            {"order": 4, "module_id": "publisher_hub", "title": "Publisher Hub", "reason": "İçerik yayın pipeline'ı"},
        ],
        "workflow_id": "keyword_growth",
    },
    {
        "intent": "serp_defense",
        "keywords": ["savun", "tehdit", "düşüş", "dusus", "fortress", "serp", "rakip", "kaybet", "position"],
        "steps": [
            {"order": 1, "module_id": "rank_index_watcher", "title": "Rank Watcher", "reason": "Pozisyon düşüşü doğrulama"},
            {"order": 2, "module_id": "serp_defense_engine", "title": "SERP Defense", "reason": "Fortress analizi ve savunma planı"},
            {"order": 3, "module_id": "content_refresh_engine", "title": "Content Refresh", "reason": "Decay gösteren sayfaları yenile"},
            {"order": 4, "module_id": "autonomous_seo_agent", "title": "Autonomous Agent", "reason": "Günlük savunma görevleri"},
        ],
        "workflow_id": "serp_defense",
    },
    {
        "intent": "publish",
        "keywords": ["yayın", "yayin", "publish", "içerik", "icerik", "yazı", "yazi", "post", "blog"],
        "steps": [
            {"order": 1, "module_id": "publisher_hub", "title": "Publisher Hub", "reason": "Kuyruk ve kanal yönetimi"},
            {"order": 2, "module_id": "seo_quality_gate", "title": "SEO Quality Gate", "reason": "Yayın öncesi kalite kontrol"},
            {"order": 3, "module_id": "wordpress", "title": "WordPress", "reason": "Ana site kanalı"},
        ],
        "workflow_id": "content_publishing",
    },
    {
        "intent": "authority",
        "keywords": ["authority", "mesh", "support", "backlink", "ağ", "ag", "google sites", "github"],
        "steps": [
            {"order": 1, "module_id": "support_network_engine", "title": "Support Network", "reason": "Network gap analizi"},
            {"order": 2, "module_id": "authority_mesh_engine", "title": "Authority Mesh", "reason": "Mesh plan ve worker task'ları"},
            {"order": 3, "module_id": "publisher_hub", "title": "Publisher Hub", "reason": "Cross-link içerik yayını"},
        ],
        "workflow_id": "authority_building",
    },
    {
        "intent": "new_site",
        "keywords": ["yeni site", "aç", "ac", "launch", "astro", "deploy", "kurulum"],
        "steps": [
            {"order": 1, "module_id": "astro_factory", "title": "Astro Factory", "reason": "Proje oluşturma"},
            {"order": 2, "module_id": "astro_auto_publisher", "title": "Astro Auto Publisher", "reason": "Deploy pipeline"},
            {"order": 3, "module_id": "rank_index_watcher", "title": "Rank Watcher", "reason": "İlk takip projesi"},
            {"order": 4, "module_id": "mission_control_center", "title": "Mission Control", "reason": "Operasyon doğrulama"},
        ],
        "workflow_id": "new_site_launch",
    },
    {
        "intent": "faq_content",
        "keywords": ["faq", "sss", "soru", "cevap", "gap", "açık", "acik", "cluster"],
        "steps": [
            {"order": 1, "module_id": "crawl_gap_engine", "title": "Crawl Gap", "reason": "FAQ gap tespiti"},
            {"order": 2, "module_id": "question_intelligence_engine", "title": "QIE", "reason": "Soru cluster üretimi"},
            {"order": 3, "module_id": "publisher_hub", "title": "Publisher Hub", "reason": "FAQ yayını"},
        ],
        "workflow_id": "keyword_growth",
    },
    {
        "intent": "daily_ops",
        "keywords": ["bugün", "bugun", "ne yap", "görev", "gorev", "mission", "başla", "basla"],
        "steps": [
            {"order": 1, "module_id": "mission_control_center", "title": "Mission Control", "reason": "Günlük operasyon özeti"},
            {"order": 2, "module_id": "autonomous_seo_agent", "title": "Autonomous Agent", "reason": "Günlük görev planı"},
            {"order": 3, "module_id": "hive_brain_engine", "title": "HIVE Brain", "reason": "Son aktivite timeline"},
        ],
        "workflow_id": None,
    },
]
INTENT_RULES.extend(MENTOR_EXTRA_RULES)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("questions", [])
                data.setdefault("recommendation_history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"questions": [], "recommendation_history": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_brain(question: str, *, result: dict | None = None) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            "module_action",
            "hive_mentor",
            reason="mentor_question",
            result=result or {},
            metadata={"learn_event": "mentor_question", "question": question[:200]},
        )
    except Exception as exc:
        logger.debug("brain: %s", exc)


def _normalize(text: str) -> str:
    t = (text or "").lower().strip()
    t = t.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    return t


def _score_rule(rule: dict[str, Any], text: str) -> int:
    score = 0
    for kw in rule.get("keywords") or []:
        if _normalize(kw) in text:
            score += 2
    for gk in rule.get("geo_keywords") or []:
        if _normalize(gk) in text:
            score += 3
    return score


def _match_intent(question: str) -> dict[str, Any]:
    text = _normalize(question)
    best: dict[str, Any] | None = None
    best_score = 0
    for rule in INTENT_RULES:
        s = _score_rule(rule, text)
        if s > best_score:
            best_score = s
            best = rule
    if best and best_score > 0:
        return best
    return {
        "intent": "general",
        "keywords": [],
        "steps": [
            {"order": 1, "module_id": "mission_control_center", "title": "Mission Control", "reason": "Genel operasyon özeti"},
            {"order": 2, "module_id": "hive_academy", "title": "HIVE Academy", "reason": "Modül ansiklopedisi ve workflow'lar"},
            {"order": 3, "module_id": "first_run_wizard", "title": "First Run Wizard", "reason": "Henüz kurulum tamamlanmadıysa"},
        ],
        "workflow_id": None,
    }


def health() -> dict[str, Any]:
    st = _load_state()
    return {
        "success": True,
        "module": "hive_mentor",
        "questions_total": len(st.get("questions") or []),
        "rules_count": len(INTENT_RULES),
    }


def _academy_guide_for_intent(rule: dict) -> str:
    mapping = {
        "google_sites_setup": "guide_google_sites",
        "github_pages_setup": "guide_github_pages",
        "wordpress_setup": "guide_wordpress",
        "publish": "guide_publisher",
        "serp_defense": "guide_serp_defense",
        "keyword_growth": "guide_opportunity",
        "faq_content": "guide_crawl_gap",
        "authority": "guide_authority_mesh",
        "new_site": "guide_getting_started",
    }
    return mapping.get(rule.get("intent", ""), "")


def get_context() -> dict[str, Any]:
    st = _load_state()
    recent = (st.get("questions") or [])[:10]
    intent_catalog = [
        {
            "intent": r["intent"],
            "sample_keywords": (r.get("keywords") or [])[:4],
            "step_count": len(r.get("steps") or []),
        }
        for r in INTENT_RULES
    ]
    return {
        "success": True,
        "questions_asked": len(st.get("questions") or []),
        "recent_questions": recent,
        "available_intents": [r["intent"] for r in INTENT_RULES],
        "intent_catalog": intent_catalog,
    }


def ask(question: str) -> dict[str, Any]:
    if not (question or "").strip():
        return {"success": False, "error": "Soru boş olamaz"}

    text = _normalize(question)
    success_triggers = (
        "ne yapmaliyim", "ne yapmalıyım", "what should i do", "success path",
        "basari yolu", "başarı yolu", "aktivasyon", "activation",
    )
    if any(t in text for t in success_triggers):
        try:
            from app.moduller.hive_success_path import mentor_success_answer
            sp = mentor_success_answer()
            if sp.get("success"):
                answer_id = f"mentor-{uuid.uuid4().hex[:10]}"
                result = {
                    **sp,
                    "answer_id": answer_id,
                    "question": question.strip(),
                    "workflow_id": None,
                    "tips": ["Success Path panelinden checklist takip edin", "Eksik adımlar Academy derslerine yönlendirir"],
                    "created_at": _now(),
                }
                st = _load_state()
                st.setdefault("questions", []).insert(0, {
                    "answer_id": answer_id,
                    "question": question.strip(),
                    "intent": "success_path",
                    "at": _now(),
                })
                st["questions"] = st["questions"][:500]
                st.setdefault("recommendation_history", []).insert(0, result)
                st["recommendation_history"] = st["recommendation_history"][:200]
                _save_state(st)
                _record_brain(question, result={"intent": "success_path", "source": "hive_success_path"})
                return result
        except Exception as exc:
            logger.debug("success_path mentor: %s", exc)

    rule = _match_intent(question)
    answer_id = f"mentor-{uuid.uuid4().hex[:10]}"
    steps = rule.get("steps") or []
    summary = _build_summary(question, rule, steps)

    result = {
        "success": True,
        "answer_id": answer_id,
        "question": question.strip(),
        "intent": rule.get("intent", "general"),
        "summary": summary,
        "steps": steps,
        "workflow_id": rule.get("workflow_id"),
        "tips": rule.get("tips") or [],
        "academy_guide": _academy_guide_for_intent(rule),
        "created_at": _now(),
    }

    st = _load_state()
    st.setdefault("questions", []).insert(0, {
        "answer_id": answer_id,
        "question": question.strip(),
        "intent": rule.get("intent"),
        "at": _now(),
    })
    st["questions"] = st["questions"][:500]
    st.setdefault("recommendation_history", []).insert(0, result)
    st["recommendation_history"] = st["recommendation_history"][:200]
    _save_state(st)
    _record_brain(question, result={"intent": rule.get("intent"), "steps": [s["module_id"] for s in steps]})

    return result


def _build_summary(question: str, rule: dict, steps: list) -> str:
    intent = rule.get("intent", "general")
    if intent == "keyword_growth" and any(_normalize(g) in _normalize(question) for g in rule.get("geo_keywords") or []):
        names = " → ".join(s["title"] for s in steps[:4])
        return f"Geo/keyword büyüme hedefi için önerilen akış: {names}."
    if steps:
        names = " → ".join(s["title"] for s in steps[:4])
        return f"Önerilen modül sırası: {names}."
    return "Mission Control'den başlayın ve Academy workflow'larına bakın."


def get_recommendations(limit: int = 10) -> dict[str, Any]:
    st = _load_state()
    history = (st.get("recommendation_history") or [])[:limit]
    defaults = [
        {
            "title": "Günlük operasyon",
            "reason": "Her sabah Mission Control ile başlayın",
            "module_id": "mission_control_center",
        },
        {
            "title": "First Run Wizard",
            "reason": "Kurulum tamamlanmadıysa wizard'ı bitirin",
            "module_id": "first_run_wizard",
        },
    ]
    return {
        "success": True,
        "recommendations": history or defaults,
        "count": len(history) or len(defaults),
    }
