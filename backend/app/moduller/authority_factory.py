"""
Authority Factory V1 — otorite kaynak üretim orkestrasyon katmanı.

Authority Mesh planlarını üretim batch'lerine çevirir; GitHub Pages, Google Sites,
Publisher Hub ve Astro/Network katmanlarını delegasyon ile kullanır.
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
from urllib.parse import urlparse

logger = logging.getLogger("hive.authority_factory")

STATE_FILE = Path(__file__).resolve().parent.parent / "authority_factory_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 500
BATCH_LIMIT = 200

ROLES = (
    "faq_hub", "geo_hub", "entity_hub", "blog_hub", "support_hub", "citation_hub",
)

BATCH_SOURCES = (
    "authority_mesh", "opportunity", "serp_defense", "action_orchestrator", "manual",
    "campaign", "data_miner", "domain_intelligence",
)

V2_DEFAULT_PROVIDER_MIX: dict[str, int] = {
    "github_pages": 2,
    "google_sites": 2,
    "blogger": 3,
    "tumblr": 5,
    "devto": 1,
    "wordpress": 1,
    "astro": 1,
}

DOMAIN_SCORE_MIN = 65
DOMAIN_SPAM_MAX = 40
MIN_QUALITY_SCORE = 75

CAMPAIGN_FACTORY_ITEM_TYPES = (
    "authority_source", "publisher_content", "support_site", "citation_expansion",
)

CAMPAIGN_ITEM_PROVIDER_MAP: dict[str, list[str]] = {
    "authority_source": ["github_pages", "google_sites", "blogger", "tumblr"],
    "publisher_content": ["blogger", "tumblr", "devto", "wordpress"],
    "support_site": ["github_pages", "astro", "google_sites"],
    "citation_expansion": ["devto", "tumblr", "wordpress"],
}

CAMPAIGN_ITEM_ROLE_MAP: dict[str, str] = {
    "authority_source": "entity_hub",
    "publisher_content": "blog_hub",
    "support_site": "support_hub",
    "citation_expansion": "citation_hub",
}

PROVIDERS: dict[str, dict[str, Any]] = {
    "github_pages": {"label": "GitHub Pages", "provider_type": "api", "publisher_channel": None, "safety_key": "allow_github_pages"},
    "google_sites": {"label": "Google Sites", "provider_type": "browser", "publisher_channel": None, "safety_key": "allow_google_sites"},
    "blogger": {"label": "Blogger", "provider_type": "api", "publisher_channel": "blogger", "safety_key": "allow_publisher"},
    "tumblr": {"label": "Tumblr", "provider_type": "api", "publisher_channel": "tumblr", "safety_key": "allow_publisher"},
    "devto": {"label": "Dev.to", "provider_type": "api", "publisher_channel": "devto", "safety_key": "allow_publisher"},
    "wordpress": {"label": "WordPress", "provider_type": "api", "publisher_channel": "wordpress", "safety_key": "allow_publisher"},
    "medium": {"label": "Medium", "provider_type": "browser", "publisher_channel": "medium", "safety_key": "allow_publisher"},
    "quora": {"label": "Quora", "provider_type": "browser", "publisher_channel": "quora", "safety_key": "allow_publisher"},
    "linkedin": {"label": "LinkedIn", "provider_type": "browser", "publisher_channel": "linkedin", "safety_key": "allow_publisher"},
    "astro": {"label": "Astro Support", "provider_type": "static", "publisher_channel": None, "safety_key": "allow_astro"},
}

DEFAULT_FACTORY_COUNTS: dict[str, int] = {
    "github_pages": 2,
    "google_sites": 3,
    "blogger": 4,
    "tumblr": 6,
    "devto": 2,
    "wordpress": 1,
    "astro": 1,
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "auto_process": False,
    "allow_google_sites": False,
    "allow_github_pages": False,
    "allow_publisher": True,
    "allow_astro": False,
    "max_items_per_batch": 25,
    "max_exact_anchor_ratio": 0.15,
    "duplicate_block": True,
    "default_money_site": "https://www.balkutusu.com",
    "default_network_id": "",
    "auto_track_rank_watcher": True,
    "auto_register_support_network": True,
    "min_quality_score": MIN_QUALITY_SCORE,
    "provider_mix": dict(V2_DEFAULT_PROVIDER_MIX),
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
                data.setdefault("batches", [])
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"settings": dict(DEFAULT_SETTINGS), "batches": [], "history": []}


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


def _append_history(state: dict[str, Any], entry: dict[str, Any]) -> None:
    lst = state.setdefault("history", [])
    lst.insert(0, entry)
    state["history"] = lst[:HISTORY_LIMIT]


def _record_brain(event_type: str, *, domain: str = "", keyword: str = "", result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event_type,
            "authority_factory",
            domain=domain,
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "authority_factory", "factory_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _item_fingerprint(keyword: str, provider: str, title: str) -> str:
    raw = f"{provider}:{keyword}:{title}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _find_batch(state: dict[str, Any], batch_id: str) -> dict[str, Any] | None:
    return next((b for b in state.get("batches") or [] if b.get("batch_id") == batch_id), None)


def _find_item(batch: dict[str, Any], item_id: str) -> dict[str, Any] | None:
    return next((it for it in batch.get("items") or [] if it.get("item_id") == item_id), None)


def _duplicate_exists(keyword: str, provider: str, title: str, *, exclude_batch_id: str = "") -> bool:
    settings = get_settings()
    if not settings.get("duplicate_block", True):
        return False
    fp = _item_fingerprint(keyword, provider, title)
    st = _load_state()
    for batch in st.get("batches") or []:
        if batch.get("batch_id") == exclude_batch_id:
            continue
        for it in batch.get("items") or []:
            if it.get("fingerprint") == fp and it.get("status") in ("published", "processing", "queued"):
                return True
            if (
                it.get("target_keyword", "").lower() == keyword.lower()
                and it.get("provider") == provider
                and it.get("title", "").lower() == title.lower()
                and it.get("status") in ("published", "processing", "queued")
            ):
                return True
    return False


def _validate_link_policy(link_policies: list[dict[str, Any]], keyword: str, settings: dict[str, Any]) -> dict[str, Any]:
    """Authority Mesh link policy — exact match oranı kontrolü."""
    if not link_policies:
        return {"ok": True, "exact_ratio": 0.0, "warnings": []}
    kw = keyword.lower().strip()
    exact = 0
    with_anchor = 0
    for p in link_policies:
        anchor = (p.get("anchor") or "").lower().strip()
        if not anchor:
            continue
        with_anchor += 1
        if anchor == kw or p.get("link_type") == "partial" and kw and kw in anchor:
            exact += 1
    ratio = exact / with_anchor if with_anchor else 0.0
    max_ratio = float(settings.get("max_exact_anchor_ratio", 0.15))
    warnings: list[str] = []
    if ratio > max_ratio:
        warnings.append(f"exact_anchor_ratio_high:{ratio:.2f}>{max_ratio}")
    return {"ok": ratio <= max_ratio, "exact_ratio": round(ratio, 4), "warnings": warnings}


def _default_role(provider: str) -> str:
    if provider in ("blogger", "tumblr", "medium", "devto"):
        return "blog_hub"
    if provider == "google_sites":
        return "geo_hub"
    if provider == "github_pages":
        return "support_hub"
    if provider == "astro":
        return "support_hub"
    return "support_hub"


def _build_factory_items(
    keyword: str,
    money_site: str,
    *,
    factory_counts: dict[str, int] | None = None,
    mesh_plan: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Mesh plan veya factory_counts'tan item listesi üret."""
    from app.moduller.authority_mesh_engine import generate_link_policy

    link_policies = generate_link_policy(keyword, money_site)
    items: list[dict[str, Any]] = []
    warnings: list[str] = []

    if mesh_plan and mesh_plan.get("items"):
        source_items = mesh_plan["items"]
    else:
        counts = dict(DEFAULT_FACTORY_COUNTS)
        if factory_counts:
            counts.update(factory_counts)
        source_items = []
        for provider, count in counts.items():
            if count <= 0 or provider not in PROVIDERS:
                continue
            meta = PROVIDERS[provider]
            for i in range(count):
                title = f"{keyword} — {meta['label']}" + (f" #{i + 1}" if count > 1 else "")
                source_items.append({
                    "provider": provider,
                    "provider_type": meta["provider_type"],
                    "title": title,
                    "role": _default_role(provider),
                    "link_policy": link_policies[len(source_items) % len(link_policies)] if link_policies else {},
                })

    settings = get_settings()
    max_items = int(settings.get("max_items_per_batch", 25))
    if len(source_items) > max_items:
        warnings.append(f"items_truncated:{len(source_items)}>{max_items}")
        source_items = source_items[:max_items]

    for idx, src in enumerate(source_items):
        provider = src.get("provider", "")
        title = src.get("title", keyword)
        if _duplicate_exists(keyword, provider, title):
            warnings.append(f"duplicate_found:{provider}:{title[:40]}")
            if settings.get("duplicate_block", True):
                continue
        link = src.get("link_policy") or (link_policies[idx % len(link_policies)] if link_policies else {})
        meta = PROVIDERS.get(provider, {"provider_type": "manual", "label": provider})
        items.append({
            "item_id": f"afi-{uuid.uuid4().hex[:10]}",
            "provider": provider,
            "provider_type": meta.get("provider_type", src.get("provider_type", "manual")),
            "role": src.get("role") if src.get("role") in ROLES else _default_role(provider),
            "title": title,
            "target_keyword": keyword,
            "target_url": money_site,
            "status": "queued",
            "result_url": "",
            "error": "",
            "assigned_worker": meta.get("label", provider),
            "link_policy": link,
            "fingerprint": _item_fingerprint(keyword, provider, title),
        })

    return items, link_policies, warnings


def create_batch(
    keyword: str,
    *,
    money_site: str = "",
    name: str = "",
    source: str = "manual",
    role: str = "",
    factory_counts: dict[str, int] | None = None,
    mesh_plan_id: str = "",
    project_id: str = "",
    network_id: str = "",
    auto_process: bool | None = None,
) -> dict[str, Any]:
    kw = (keyword or "").strip()
    if not kw:
        return {"success": False, "error": "keyword gerekli"}

    settings = get_settings()
    if not settings.get("enabled", False):
        return {"success": False, "error": "authority_factory disabled — settings.enabled=true gerekli"}

    money = (money_site or settings.get("default_money_site") or "").strip()
    net_id = network_id or settings.get("default_network_id", "")
    src = source if source in BATCH_SOURCES else "manual"

    mesh_plan: dict[str, Any] | None = None
    mesh_plan_id_used = mesh_plan_id
    if mesh_plan_id:
        try:
            from app.moduller.authority_mesh_engine import _load_state as ame_load
            ame_st = ame_load()
            mesh_plan = next((p for p in ame_st.get("mesh_plans") or [] if p.get("plan_id") == mesh_plan_id), None)
            if not mesh_plan:
                return {"success": False, "error": "mesh_plan_not_found"}
        except Exception as exc:
            return {"success": False, "error": f"mesh_plan_load_failed:{exc}"}
    else:
        try:
            from app.moduller.authority_mesh_engine import create_site_plan
            plan_res = create_site_plan(
                kw,
                money_site=money,
                project_id=project_id,
                network_id=net_id,
                mesh_counts=factory_counts,
            )
            if plan_res.get("success"):
                mesh_plan = plan_res.get("plan")
                mesh_plan_id_used = mesh_plan.get("plan_id", "")
        except Exception as exc:
            logger.debug("mesh plan fallback: %s", exc)

    items, link_policies, dup_warnings = _build_factory_items(kw, money, factory_counts=factory_counts, mesh_plan=mesh_plan)
    if not items:
        return {"success": False, "error": "no_items_after_duplicate_control", "warnings": dup_warnings}

    lp_check = _validate_link_policy(link_policies, kw, settings)
    all_warnings = list(dup_warnings) + list(lp_check.get("warnings") or [])

    batch_name = name.strip() or f"{kw.title()} Authority Batch"
    batch_id = f"af-{uuid.uuid4().hex[:10]}"
    batch = {
        "batch_id": batch_id,
        "name": batch_name,
        "target_keyword": kw,
        "target_money_site": money,
        "source": src,
        "status": "planned",
        "items": items,
        "mesh_plan_id": mesh_plan_id_used,
        "project_id": project_id,
        "network_id": net_id,
        "link_policies": link_policies,
        "created_at": _now(),
        "started_at": "",
        "completed_at": "",
        "summary": {
            "total_items": len(items),
            "queued": len(items),
            "exact_anchor_ratio": lp_check.get("exact_ratio", 0),
            "link_policy_ok": lp_check.get("ok", True),
            "warnings": all_warnings,
        },
    }
    if role and role in ROLES:
        for it in batch["items"]:
            it["role"] = role

    st = _load_state()
    st.setdefault("batches", []).insert(0, batch)
    st["batches"] = st["batches"][:BATCH_LIMIT]
    batch["status"] = "queued"
    _append_history(st, {"type": "batch_created", "batch_id": batch_id, "keyword": kw, "items": len(items), "at": _now()})
    _save_state(st)

    _record_brain(
        "authority_factory_batch_created",
        keyword=kw,
        domain=money,
        result={"batch_id": batch_id, "items": len(items), "source": src, "warnings": all_warnings},
        reason=batch_name,
    )

    should_process = auto_process if auto_process is not None else settings.get("auto_process", False)
    process_res = None
    if should_process:
        process_res = process_batch(batch_id)

    return {
        "success": True,
        "batch": batch,
        "link_policy_check": lp_check,
        "warnings": all_warnings,
        "auto_processed": bool(should_process),
        "process_result": process_res,
    }


def create_batch_from_orchestrator(action: dict[str, Any]) -> dict[str, Any]:
    """Action Orchestrator authority_source / github_page / google_site aksiyonları."""
    at = action.get("action_type", "")
    payload = action.get("payload") or {}
    keyword = (action.get("keyword") or payload.get("keyword") or payload.get("target_keyword") or "").strip()
    money = (payload.get("money_site") or payload.get("target_money_site") or "").strip()
    counts: dict[str, int] | None = None

    if at == "github_page":
        counts = {"github_pages": int(payload.get("count") or 1)}
    elif at == "google_site":
        counts = {"google_sites": int(payload.get("count") or 1)}
    elif at == "authority_source":
        counts = payload.get("factory_counts") or payload.get("mesh_counts")

    return create_batch(
        keyword,
        money_site=money,
        source="action_orchestrator",
        factory_counts=counts,
        project_id=action.get("project_id") or payload.get("project_id") or "",
        network_id=payload.get("network_id") or "",
        name=payload.get("name") or f"AO: {keyword or at}",
    )


def _provider_allowed(provider: str, settings: dict[str, Any]) -> tuple[bool, str]:
    meta = PROVIDERS.get(provider, {})
    key = meta.get("safety_key")
    if key and not settings.get(key, False):
        return False, f"{key} disabled"
    if provider == "astro" and not settings.get("allow_astro", False):
        return False, "allow_astro disabled"
    return True, ""


def _publisher_ready(channel: str) -> tuple[bool, str | None]:
    try:
        from app.moduller.publisher_hub import _channel_status
        st = _channel_status(channel)
        if st.get("connected"):
            return True, None
        err = st.get("error") or ""
        if st.get("configured") and not st.get("connected"):
            if channel == "blogger":
                try:
                    from app.moduller.blogger_api import get_status
                    bs = get_status()
                    err = str(bs.get("error") or err or "blogger_not_connected")
                except Exception as exc:
                    err = str(exc)
            elif not err:
                err = f"{channel}_not_connected"
            err_l = err.lower()
            if "invalid_grant" in err_l or "token" in err_l or "auth" in err_l:
                return False, err
            return False, err or f"{channel} yapılandırıldı ama bağlı değil"
        return False, err or f"{channel} yapılandırılmadı"
    except Exception as exc:
        return False, str(exc)


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_entities(entities: list[dict[str, Any]] | list[Any] | None) -> list[str]:
    out: list[str] = []
    for ent in entities or []:
        if isinstance(ent, dict):
            label = _safe_text(ent.get("label") or ent.get("name") or ent.get("title"))
        else:
            label = _safe_text(ent)
        if label:
            out.append(label)
    return out[:20]


def _normalize_faqs(faqs: list[dict[str, Any]] | list[Any] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for faq in faqs or []:
        if isinstance(faq, dict):
            q = _safe_text(faq.get("question"))
            a = _safe_text(faq.get("answer"))
        else:
            q = _safe_text(faq)
            a = ""
        if q:
            out.append({"question": q, "answer": a or "Bu soru için güncel cevap içeriği hazırlanıyor."})
    return out[:12]


def _fallback_faqs(keyword: str, count: int = 3) -> list[dict[str, str]]:
    kw = _safe_text(keyword) or "bu konu"
    return [
        {"question": f"{kw} nedir?", "answer": f"{kw} için temel kavramlar, kapsam ve güncel kullanım örnekleri bu rehberde özetlenir."},
        {"question": f"{kw} için en doğru kaynaklar hangileri?", "answer": f"{kw} hakkında resmi kaynaklar, yerel doğrulama sinyalleri ve güvenilir referans alanları birlikte değerlendirilir."},
        {"question": f"{kw} için nasıl aksiyon planı çıkarılır?", "answer": "Varlıklar, SSS, lokasyon sinyalleri, bağlantı stratejisi ve düzenli içerik güncellemesi adım adım planlanır."},
    ][: max(1, count)]


def _build_content_html(
    title: str,
    keyword: str,
    link: dict[str, Any],
    *,
    item: dict[str, Any] | None = None,
    batch: dict[str, Any] | None = None,
) -> str:
    it = item or {}
    bt = batch or {}
    role = _safe_text(it.get("role") or "support_hub")
    provider = _safe_text(it.get("provider") or "publisher")
    target_url = _safe_text(link.get("target_url") or it.get("target_url") or bt.get("target_money_site"))
    anchor = _safe_text(link.get("anchor") or target_url)
    dataset_id = _safe_text(it.get("dataset_id") or bt.get("dataset_id"))
    categories = [_safe_text(c) for c in (it.get("categories") or []) if _safe_text(c)][:6]
    locations = [_safe_text(x) for x in (it.get("addresses") or it.get("locations") or []) if _safe_text(x)][:6]
    entities = _normalize_entities(it.get("entities"))
    faqs = _normalize_faqs(it.get("faqs"))
    faq_source = "dataset"
    if not faqs:
        faqs = _fallback_faqs(keyword, count=3)
        faq_source = "generated_from_keyword"

    intro = (
        f"{keyword} odağında hazırlanan bu içerik, otorite sinyallerini güçlendirmek için varlıklar, "
        "sık sorulan sorular, yerel bağlam ve kaynak doğrulama katmanlarını birlikte işler. "
        "Metin, tek bir sayfada hem kullanıcı niyetine yanıt vermeyi hem de yayın ağında tutarlı bir içerik omurgası oluşturmayı hedefler. "
        "Özellikle entity, kategori ve lokasyon ilişkileri aynı başlık altında birleştirilerek arama motorlarının konu bütünlüğü okuması kolaylaştırılır. "
        "Ek olarak içerik içinde referans kaynakları, ilişkili rehber bağlantıları ve güven sinyali üretmeye yardımcı alanlar planlı şekilde yer alır. "
        "Bu yapı Publisher Hub kalite kapısından geçecek düzeyde içerik zenginliği sağlar ve bağlantı politikasını doğal akışta uygular."
    )

    entity_lines = []
    for e in entities[:8]:
        cat = categories[0] if categories else "Genel"
        loc = locations[0] if locations else "Yerel bağlam"
        entity_lines.append(f"<li><strong>{e}</strong> — kategori: {cat}, lokasyon: {loc}, ilişki: {keyword} içerik kümesi</li>")
    if not entity_lines:
        entity_lines.append("<li>Entity verisi bulunamadı.</li>")

    faq_lines = [
        f"<details><summary>{f['question']}</summary><p>{f['answer']}</p></details>"
        for f in faqs[:8]
    ]

    geo_text = ", ".join(locations[:4]) if locations else "şehir / ilçe / mahalle sinyalleri planlanıyor"
    related_guide_links = [
        f'<li><a href="{target_url}">{anchor or target_url}</a> — ana rehber bağlantısı</li>' if target_url else "",
        "<li><a href=\"/rehber/icerik-stratejisi\">İçerik stratejisi rehberi</a></li>",
        "<li><a href=\"/rehber/entity-modelleme\">Entity modelleme rehberi</a></li>",
    ]
    related_guide_links = [x for x in related_guide_links if x]

    citation_items = [
        f"<li>Dataset source: {dataset_id or 'manual'}</li>",
        f"<li>Provider: {provider}</li>",
        f"<li>Role: {role}</li>",
        f"<li>FAQ source: {faq_source}</li>",
    ]

    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["question"],
                "acceptedAnswer": {"@type": "Answer", "text": f["answer"]},
            }
            for f in faqs[:8]
        ],
    }
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "/"},
            {"@type": "ListItem", "position": 2, "name": "Authority Hub", "item": "/authority"},
            {"@type": "ListItem", "position": 3, "name": title or keyword, "item": target_url or "/authority/content"},
        ],
    }

    return "\n".join(
        [
            f"<article data-role=\"{role}\" data-provider=\"{provider}\">",
            f"<h1>{title}</h1>",
            f"<p>{intro}</p>",
            "<h2>Entity Section</h2>",
            "<ul>",
            *entity_lines,
            "</ul>",
            "<h2>FAQ Section</h2>",
            *faq_lines,
            "<h2>Local / GEO Section</h2>",
            f"<p>Bu içerik {geo_text} bağlamında optimize edildi. Yakın entity mention yapısı ile yerel eşleşme kuvvetlendirilir.</p>",
            "<h2>Related Guide Links</h2>",
            "<ul>",
            *related_guide_links,
            "</ul>",
            "<h2>Citation / Source Block</h2>",
            "<ul>",
            *citation_items,
            "</ul>",
            "<h2>Money Site Link Policy</h2>",
            f"<p>Link type: {_safe_text(link.get('link_type') or 'none')}; hedef: {target_url or 'yok'}; anchor: {anchor or 'yok'}.</p>",
            "<h2>Author & Publisher</h2>",
            f"<p>Author: Hive Authority Writer | Publisher: {provider} | Last updated: {_now()}</p>",
            f"<script type=\"application/ld+json\">{json.dumps(breadcrumb_schema, ensure_ascii=False)}</script>",
            f"<script type=\"application/ld+json\">{json.dumps(faq_schema, ensure_ascii=False)}</script>",
            "</article>",
        ]
    )


def _content_stats(html: str, entities: list[str], faqs: list[dict[str, str]], quality: dict[str, Any]) -> dict[str, Any]:
    words = len(re.findall(r"\b[\wçğıöşüÇĞİÖŞÜ-]+\b", re.sub(r"<[^>]+>", " ", html)))
    h_count = len(re.findall(r"<h[1-6][^>]*>", html, flags=re.IGNORECASE))
    link_count = len(re.findall(r"<a\s+[^>]*href=", html, flags=re.IGNORECASE))
    script_count = len(re.findall(r"<script[^>]*application/ld\+json", html, flags=re.IGNORECASE))
    reasons = []
    if words < 150:
        reasons.append(f"word_count_low:{words}<150")
    if h_count < 4:
        reasons.append(f"heading_count_low:{h_count}<4")
    if not faqs:
        reasons.append("faq_missing")
    if not entities:
        reasons.append("entity_missing")
    if link_count < 2:
        reasons.append(f"link_count_low:{link_count}<2")
    if script_count < 1:
        reasons.append("schema_missing")
    if not re.search(r"Author:|Publisher:", html, flags=re.IGNORECASE):
        reasons.append("author_publisher_missing")
    if quality.get("analysis") and not quality.get("passed"):
        reasons.append(f"quality_gate_failed:{quality.get('score', 0)}")
    return {
        "word_count": words,
        "heading_count": h_count,
        "link_count": link_count,
        "faq_count": len(faqs),
        "entity_count": len(entities),
        "schema_count": script_count,
        "quality_reasons": reasons,
    }


def _register_support_network(url: str, role: str, network_id: str, keyword: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("auto_register_support_network", True):
        return {"success": False, "skipped": True}
    try:
        from app.moduller.authority_mesh_engine import register_external_publish
        return register_external_publish(
            "authority_factory",
            url=url,
            keyword=keyword,
            money_site="",
            role=role,
            network_id=network_id,
        )
    except Exception as exc:
        host = urlparse(url if "://" in url else f"https://{url}").netloc or url
        try:
            from app.moduller.network_replicator import add_domain
            if network_id:
                return add_domain(network_id, host, role=role)
        except Exception:
            pass
        return {"success": False, "error": str(exc), "domain": host}


def _track_rank_watcher(url: str, keyword: str, provider: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("auto_track_rank_watcher", True) or not url or not keyword:
        return {"success": False, "skipped": True}
    try:
        from app.moduller.rank_index_watcher import register_project, track_keyword
        domain = urlparse(url).netloc
        if not domain:
            return {"success": False, "error": "domain_missing"}
        pid = f"af-{provider}-{uuid.uuid4().hex[:8]}"
        register_project(pid, domain, source=f"authority_factory:{provider}")
        return track_keyword(keyword, domain, project_id=pid)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _process_github_pages_item(item: dict[str, Any], batch: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    allowed, reason = _provider_allowed("github_pages", settings)
    if not allowed:
        item["status"] = "failed"
        item["error"] = reason
        return {"success": False, "error": reason}

    try:
        from app.moduller.github_pages_worker import health, create_site_from_mesh_item
        h = health()
        if not h.get("provider_ready"):
            item["status"] = "provider_missing"
            item["error"] = h.get("error") or "provider_missing"
            return {"success": False, "error": item["error"]}

        res = create_site_from_mesh_item(
            title=item.get("title", ""),
            keyword=item.get("target_keyword", ""),
            money_site=batch.get("target_money_site", ""),
            role=item.get("role", "support_hub"),
            link_policy=item.get("link_policy"),
            network_id=batch.get("network_id", ""),
        )
        site = res.get("site") or {}
        url = site.get("pages_url") or res.get("pages_url") or ""
        status = site.get("status") or res.get("status", "")
        if url and status in ("published", "pages_enabled", "repo_created"):
            item["status"] = "published"
            item["result_url"] = url
            _register_support_network(url, item.get("role", "support_hub"), batch.get("network_id", ""), item.get("target_keyword", ""))
            _track_rank_watcher(url, item.get("target_keyword", ""), "github_pages")
            return {"success": True, "url": url, **res}
        if res.get("success"):
            item["status"] = "review_required"
            item["result_url"] = url
            return {"success": True, "status": "review_required", **res}
        item["status"] = "failed"
        item["error"] = res.get("error") or res.get("message") or "github_pages_failed"
        return {"success": False, **res}
    except Exception as exc:
        item["status"] = "failed"
        item["error"] = str(exc)
        return {"success": False, "error": str(exc)}


def _process_google_sites_item(item: dict[str, Any], batch: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    allowed, reason = _provider_allowed("google_sites", settings)
    if not allowed:
        item["status"] = "failed"
        item["error"] = reason
        return {"success": False, "error": reason}

    try:
        from app.moduller.google_sites_worker import health, create_task_from_mesh_item, process_task
        h = health()
        if not h.get("ready") and not h.get("provider_ready"):
            item_status = "browser_missing" if h.get("error") == "browser_missing" or not h.get("chromium_installed") else "provider_missing"
            item["status"] = item_status
            item["error"] = h.get("reason") or h.get("error") or item_status
            return {"success": False, "error": item["error"], "status": item_status}

        create_res = create_task_from_mesh_item(
            title=item.get("title", ""),
            keyword=item.get("target_keyword", ""),
            money_site=batch.get("target_money_site", ""),
            link_policy=item.get("link_policy"),
        )
        if not create_res.get("success"):
            item["status"] = "failed"
            item["error"] = create_res.get("error") or "task_create_failed"
            return {"success": False, **create_res}

        task = create_res.get("task") or {}
        task_id = task.get("task_id", "")
        item["assigned_worker"] = f"google_sites_worker:{task_id}"
        item.setdefault("metadata", {})["google_sites_task_id"] = task_id
        proc = process_task(task_id, network_id=batch.get("network_id", ""))
        task = proc.get("task") or task
        status = task.get("status", "failed")

        if status == "login_required":
            item["status"] = "login_required"
            item["error"] = task.get("error") or proc.get("message") or "google_login_required"
            return {"success": False, "status": "login_required", "task_id": task_id, **proc}
        if status in ("browser_missing", "provider_missing"):
            item["status"] = status
            item["error"] = task.get("error") or proc.get("message") or status
            return {"success": False, "status": status, "task_id": task_id, **proc}
        if status == "published" and task.get("published_url"):
            url = task["published_url"]
            item["status"] = "published"
            item["result_url"] = url
            _register_support_network(url, item.get("role", "support_hub"), batch.get("network_id", ""), item.get("target_keyword", ""))
            _track_rank_watcher(url, item.get("target_keyword", ""), "google_sites")
            return {"success": True, "url": url, "task_id": task_id, **proc}
        if status == "review_required":
            item["status"] = "review_required"
            return {"success": True, "task_id": task_id, **proc}
        item["status"] = "failed"
        item["error"] = task.get("error") or proc.get("error") or "google_sites_failed"
        return {"success": False, "task_id": task_id, **proc}
    except Exception as exc:
        item["status"] = "failed"
        item["error"] = str(exc)
        return {"success": False, "error": str(exc)}


def _process_publisher_item(item: dict[str, Any], batch: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    provider = item.get("provider", "")
    channel = PROVIDERS.get(provider, {}).get("publisher_channel")
    if not channel:
        item["status"] = "review_required"
        item["error"] = "publisher_channel_missing"
        return {"success": False, "error": "publisher_channel_missing"}

    allowed, reason = _provider_allowed(provider, settings)
    if not allowed:
        item["status"] = "failed"
        item["error"] = reason
        return {"success": False, "error": reason}

    ready, err = _publisher_ready(channel)
    if not ready:
        err_text = str(err or "provider_missing")
        err_l = err_text.lower()
        if "invalid_grant" in err_l or "token" in err_l or "auth" in err_l:
            item["status"] = "provider_auth_failed"
        else:
            item["status"] = "provider_missing"
        item["error"] = err_text
        return {"success": False, "error": item["error"], "status": item["status"]}

    title = item.get("title", "")
    keyword = item.get("target_keyword", "")
    link = item.get("link_policy") or {}
    entities = _normalize_entities(item.get("entities"))
    if not entities:
        item["status"] = "review_required"
        item["error"] = "review_required:entity_missing"
        return {"success": True, "status": "review_required", "error": item["error"]}
    html = _build_content_html(title, keyword, link, item=item, batch=batch)
    item["content_html"] = html

    try:
        from app.moduller.publisher_hub import enqueue, _quality_check
        qc = _quality_check({"title": title, "content_html": html, "keyword": keyword})
        stats = _content_stats(html, entities, _normalize_faqs(item.get("faqs")), qc)
        item["quality_score"] = int(qc.get("score", 0))
        item.setdefault("metadata", {}).update(
            {
                "word_count": stats["word_count"],
                "faq_count": stats["faq_count"],
                "entity_count": stats["entity_count"],
                "quality_reasons": stats["quality_reasons"],
            }
        )
        if not qc.get("passed", True):
            item["status"] = "review_required"
            item["error"] = f"quality_gate_failed:{qc.get('score', 0)}"
            return {"success": True, "status": "review_required", "error": item["error"], "quality": qc, "stats": stats}

        enq = enqueue({
            "title": title,
            "content_html": html,
            "keyword": keyword,
            "source": "authority_factory",
            "channels": [channel],
        })
        if not enq.get("success"):
            item["status"] = "failed"
            item["error"] = enq.get("error") or "enqueue_failed"
            return {"success": False, **enq}
        queue_id = enq.get("publish_id", "")
        item["status"] = "queued"
        item.setdefault("metadata", {})["queue_id"] = queue_id
        return {"success": True, "status": "queued", "queue_id": queue_id, "quality": qc, "stats": stats}
    except Exception as exc:
        item["status"] = "failed"
        item["error"] = str(exc)
        return {"success": False, "error": str(exc)}


def _process_astro_item(item: dict[str, Any], batch: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    allowed, reason = _provider_allowed("astro", settings)
    if not allowed:
        item["status"] = "failed"
        item["error"] = reason
        return {"success": False, "error": reason}

    keyword = item.get("target_keyword", "")
    money = batch.get("target_money_site", "")
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower())[:30].strip("-") or "support"
    domain = f"{slug}-support.example.com"

    try:
        from app.moduller.site_replicator import create_domain_variant
        res = create_domain_variant(
            base_project_id=batch.get("project_id") or "",
            domain_role="geo_support",
            target_domain=domain,
            main_site_url=money,
        )
        if res.get("success"):
            summary = res.get("summary") or {}
            url = f"https://{summary.get('target_domain', domain)}"
            item["status"] = "published" if summary.get("target_project_id") else "review_required"
            item["result_url"] = url
            if item["status"] == "published":
                _register_support_network(url, item.get("role", "support_hub"), batch.get("network_id", ""), keyword)
                _track_rank_watcher(url, keyword, "astro")
            return {"success": True, **res}
        item["status"] = "failed"
        item["error"] = res.get("error") or "astro_failed"
        return {"success": False, **res}
    except Exception as exc:
        item["status"] = "review_required"
        item["error"] = str(exc)
        return {"success": False, "error": str(exc), "note": "astro_requires_base_project"}


def _process_browser_manual_item(item: dict[str, Any]) -> dict[str, Any]:
    item["status"] = "review_required"
    item["error"] = ""
    return {"success": True, "status": "review_required", "note": f"{item.get('provider')} browser/manual queue"}


def process_batch(batch_id: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled", False):
        return {"success": False, "error": "authority_factory disabled"}

    st = _load_state()
    batch = _find_batch(st, batch_id)
    if not batch:
        return {"success": False, "error": "batch_not_found"}
    if batch.get("status") == "paused":
        return {"success": False, "error": "batch_paused"}
    if batch.get("status") == "completed":
        return {"success": True, "batch": batch, "message": "already_completed"}

    batch["status"] = "processing"
    batch["started_at"] = batch.get("started_at") or _now()
    _save_state(st)
    _record_brain("authority_factory_batch_started", keyword=batch.get("target_keyword", ""), result={"batch_id": batch_id})

    results: list[dict] = []
    for item in batch.get("items") or []:
        if item.get("status") not in ("queued", "planned"):
            continue

        item["status"] = "processing"
        provider = item.get("provider", "")
        ptype = item.get("provider_type") or PROVIDERS.get(provider, {}).get("provider_type", "manual")

        if provider == "github_pages":
            res = _process_github_pages_item(item, batch, settings)
        elif provider == "google_sites":
            res = _process_google_sites_item(item, batch, settings)
        elif provider in ("blogger", "tumblr", "devto", "wordpress"):
            res = _process_publisher_item(item, batch, settings)
        elif provider == "astro":
            res = _process_astro_item(item, batch, settings)
        elif ptype in ("browser", "manual"):
            res = _process_browser_manual_item(item)
        else:
            item["status"] = "review_required"
            res = {"success": True, "status": "review_required"}

        results.append({"item_id": item.get("item_id"), "provider": provider, **res})

        if item.get("status") == "published":
            _record_brain(
                "authority_factory_item_published",
                keyword=item.get("target_keyword", ""),
                domain=item.get("result_url", ""),
                result={"item_id": item.get("item_id"), "provider": provider, "url": item.get("result_url")},
            )
        elif item.get("status") in ("failed", "provider_missing", "login_required"):
            _record_brain(
                "authority_factory_item_failed",
                keyword=item.get("target_keyword", ""),
                result={"item_id": item.get("item_id"), "status": item.get("status"), "error": item.get("error")},
                reason=provider,
            )

    published = sum(1 for it in batch.get("items") or [] if it.get("status") == "published")
    failed = sum(1 for it in batch.get("items") or [] if it.get("status") in ("failed", "provider_missing"))
    login_req = sum(1 for it in batch.get("items") or [] if it.get("status") == "login_required")
    queued = sum(1 for it in batch.get("items") or [] if it.get("status") in ("queued", "planned"))
    processing = sum(1 for it in batch.get("items") or [] if it.get("status") == "processing")

    batch["summary"] = {
        **(batch.get("summary") or {}),
        "published": published,
        "failed": failed,
        "login_required": login_req,
        "queued": queued,
        "processing": processing,
        "review_required": sum(1 for it in batch.get("items") or [] if it.get("status") == "review_required"),
    }

    if queued == 0 and processing == 0:
        batch["status"] = "completed" if published > 0 else "failed"
        batch["completed_at"] = _now()
        evt = "authority_factory_batch_completed" if published > 0 else "authority_factory_batch_failed"
        _record_brain(evt, keyword=batch.get("target_keyword", ""), result={"batch_id": batch_id, **batch["summary"]})
    else:
        batch["status"] = "processing"

    _append_history(st, {"type": "batch_processed", "batch_id": batch_id, "published": published, "at": _now()})
    _save_state(st)

    return {
        "success": published > 0 or any(r.get("success") for r in results),
        "batch_id": batch_id,
        "batch": batch,
        "results": results,
        "summary": batch["summary"],
    }


def pause_batch(batch_id: str) -> dict[str, Any]:
    st = _load_state()
    batch = _find_batch(st, batch_id)
    if not batch:
        return {"success": False, "error": "batch_not_found"}
    batch["status"] = "paused"
    _save_state(st)
    return {"success": True, "batch": batch}


def resume_batch(batch_id: str) -> dict[str, Any]:
    st = _load_state()
    batch = _find_batch(st, batch_id)
    if not batch:
        return {"success": False, "error": "batch_not_found"}
    if batch.get("status") != "paused":
        return {"success": False, "error": "batch_not_paused"}
    batch["status"] = "queued"
    _save_state(st)
    return process_batch(batch_id)


def list_batches(limit: int = 50, status: str = "") -> dict[str, Any]:
    st = _load_state()
    batches = st.get("batches") or []
    if status:
        batches = [b for b in batches if b.get("status") == status]
    return {"success": True, "batches": batches[:limit], "count": len(batches[:limit])}


def get_batch(batch_id: str) -> dict[str, Any]:
    st = _load_state()
    batch = _find_batch(st, batch_id)
    if not batch:
        return {"success": False, "error": "batch_not_found"}
    return {"success": True, "batch": batch}


def list_items(
    *,
    batch_id: str = "",
    status: str = "",
    provider: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    st = _load_state()
    items: list[dict] = []
    for batch in st.get("batches") or []:
        if batch_id and batch.get("batch_id") != batch_id:
            continue
        for it in batch.get("items") or []:
            if status and it.get("status") != status:
                continue
            if provider and it.get("provider") != provider:
                continue
            items.append({**it, "batch_id": batch.get("batch_id"), "batch_name": batch.get("name")})
    return {"success": True, "items": items[:limit], "count": len(items[:limit])}


def preview_content(item_id: str, format: str = "html") -> dict[str, Any]:
    st = _load_state()
    batch, item = _find_item_global(st, item_id)
    if not item:
        return {"success": False, "error": "item_not_found"}
    fmt = (format or "html").lower().strip()
    if fmt != "html":
        return {"success": False, "error": "unsupported_format"}

    title = item.get("title", "")
    keyword = item.get("target_keyword", "")
    link = item.get("link_policy") or {}
    entities = _normalize_entities(item.get("entities"))
    faqs = _normalize_faqs(item.get("faqs"))
    html = _build_content_html(title, keyword, link, item=item, batch=batch or {})

    from app.moduller.publisher_hub import _quality_check

    qc = _quality_check({"title": title, "content_html": html, "keyword": keyword})
    stats = _content_stats(html, entities, faqs, qc)
    return {
        "success": True,
        "item_id": item_id,
        "html": html,
        "word_count": stats["word_count"],
        "faq_count": stats["faq_count"],
        "entity_count": stats["entity_count"],
        "quality_score": int(qc.get("score", 0)),
        "quality_reasons": stats["quality_reasons"],
    }


def _provider_status() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pid, meta in PROVIDERS.items():
        ptype = meta.get("provider_type")
        channel = meta.get("publisher_channel")
        entry: dict[str, Any] = {"provider_type": ptype, "label": meta.get("label")}
        if pid == "github_pages":
            try:
                from app.moduller.github_pages_worker import health
                h = health()
                entry["ready"] = h.get("provider_ready", False)
                entry["error"] = h.get("error")
            except Exception as exc:
                entry["ready"] = False
                entry["error"] = str(exc)
        elif pid == "google_sites":
            try:
                from app.moduller.google_sites_worker import health
                h = health()
                entry["ready"] = h.get("provider_ready", False)
                entry["error"] = h.get("error")
            except Exception as exc:
                entry["ready"] = False
                entry["error"] = str(exc)
        elif channel:
            ready, err = _publisher_ready(channel)
            entry["ready"] = ready
            entry["error"] = err
        elif pid == "astro":
            entry["ready"] = get_settings().get("allow_astro", False)
            entry["error"] = None if entry["ready"] else "allow_astro disabled"
        else:
            entry["ready"] = False
            entry["error"] = "browser/manual"
        out[pid] = entry
    return out


def _record_brain_v2(event_type: str, *, domain: str = "", keyword: str = "", result: dict | None = None, reason: str = "") -> None:
    _record_brain(event_type, domain=domain, keyword=keyword, result=result, reason=reason)


def _v2_batch_id() -> str:
    return f"af2-{uuid.uuid4().hex[:10]}"


def _v2_item_id() -> str:
    return f"afi2-{uuid.uuid4().hex[:10]}"


def get_provider_mix() -> dict[str, Any]:
    settings = get_settings()
    mix = dict(V2_DEFAULT_PROVIDER_MIX)
    mix.update(settings.get("provider_mix") or {})
    return {"success": True, "provider_mix": mix, "defaults": V2_DEFAULT_PROVIDER_MIX}


def generate_provider_mix(overrides: dict[str, int] | None = None) -> dict[str, Any]:
    mix = dict(V2_DEFAULT_PROVIDER_MIX)
    mix.update(get_settings().get("provider_mix") or {})
    if overrides:
        for k, v in overrides.items():
            if k in PROVIDERS and int(v) >= 0:
                mix[k] = int(v)
    total = sum(mix.values())
    return {"success": True, "provider_mix": mix, "total_items": total}


def _effective_provider_mix(overrides: dict[str, int] | None = None) -> dict[str, int]:
    res = generate_provider_mix(overrides)
    return res["provider_mix"]


def _compute_item_quality_score(item: dict[str, Any], settings: dict[str, Any]) -> int:
    score = 70
    entities = item.get("entities") or []
    faqs = item.get("faqs") or []
    if entities:
        score += min(15, len(entities) * 3)
    if faqs:
        score += min(10, len(faqs) * 2)
    if item.get("title"):
        score += 5
    link = item.get("link_policy") or {}
    if link.get("link_type") == "brand":
        score += 5
    elif link.get("link_type") == "partial":
        score += 3
    lp = _validate_link_policy([link] if link else [], item.get("target_keyword", ""), settings)
    if not lp.get("ok", True):
        score -= 20
    return max(0, min(100, score))


def _apply_quality_gate(item: dict[str, Any], settings: dict[str, Any]) -> None:
    min_q = int(settings.get("min_quality_score", MIN_QUALITY_SCORE))
    qs = _compute_item_quality_score(item, settings)
    item["quality_score"] = qs
    if qs < min_q and item.get("status") not in ("failed", "provider_missing", "login_required", "published"):
        item["status"] = "review_required"
        item["error"] = item.get("error") or f"quality_below_threshold:{qs}<{min_q}"


def _find_item_global(state: dict[str, Any], item_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    for batch in state.get("batches") or []:
        it = _find_item(batch, item_id)
        if it:
            return batch, it
    return None, None


def _build_v2_items(
    keyword: str,
    money_site: str,
    *,
    provider_mix: dict[str, int] | None = None,
    entities: list | None = None,
    faqs: list | None = None,
    role_override: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    from app.moduller.authority_mesh_engine import generate_link_policy

    mix = _effective_provider_mix(provider_mix)
    link_policies = generate_link_policy(keyword, money_site)
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    settings = get_settings()
    max_items = int(settings.get("max_items_per_batch", 25))
    idx = 0

    for provider, count in mix.items():
        if count <= 0 or provider not in PROVIDERS:
            continue
        meta = PROVIDERS[provider]
        for i in range(int(count)):
            title = f"{keyword} — {meta['label']}" + (f" #{i + 1}" if count > 1 else "")
            if _duplicate_exists(keyword, provider, title):
                warnings.append(f"duplicate_found:{provider}:{title[:40]}")
                if settings.get("duplicate_block", True):
                    continue
            link = link_policies[idx % len(link_policies)] if link_policies else {}
            role = role_override if role_override in ROLES else _default_role(provider)
            item = {
                "item_id": _v2_item_id(),
                "provider": provider,
                "provider_type": meta.get("provider_type", "manual"),
                "role": role,
                "title": title,
                "target_keyword": keyword,
                "target_url": money_site,
                "entities": list(entities or [])[:20],
                "faqs": list(faqs or [])[:20],
                "status": "queued",
                "result_url": "",
                "error": "",
                "quality_score": 0,
                "assigned_worker": meta.get("label", provider),
                "link_policy": link,
                "fingerprint": _item_fingerprint(keyword, provider, title),
            }
            item["quality_score"] = _compute_item_quality_score(item, settings)
            items.append(item)
            idx += 1

    if len(items) > max_items:
        warnings.append(f"items_truncated:{len(items)}>{max_items}")
        items = items[:max_items]

    return items, link_policies, warnings


def _save_v2_batch(
    *,
    keyword: str,
    money_site: str,
    source: str,
    items: list[dict[str, Any]],
    link_policies: list[dict[str, Any]],
    warnings: list[str],
    dataset_id: str = "",
    campaign_id: str = "",
    domain_candidates: list | None = None,
    provider_mix: dict[str, int] | None = None,
    name: str = "",
    project_id: str = "",
    network_id: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    lp_check = _validate_link_policy(link_policies, keyword, settings)
    all_warnings = list(warnings) + list(lp_check.get("warnings") or [])
    mix = _effective_provider_mix(provider_mix)
    entity_count = max((len(it.get("entities") or []) for it in items), default=0)
    faq_count = max((len(it.get("faqs") or []) for it in items), default=0)
    batch_id = _v2_batch_id()
    batch_name = name.strip() or f"{keyword.title()} Authority V2"
    batch = {
        "batch_id": batch_id,
        "name": batch_name,
        "target_keyword": keyword,
        "target_domain": money_site,
        "target_money_site": money_site,
        "source": source if source in BATCH_SOURCES else "manual",
        "dataset_id": dataset_id,
        "campaign_id": campaign_id,
        "domain_candidates": domain_candidates or [],
        "entity_count": entity_count,
        "faq_count": faq_count,
        "provider_mix": mix,
        "status": "queued",
        "items": items,
        "score": 0,
        "mesh_plan_id": "",
        "project_id": project_id,
        "network_id": network_id,
        "link_policies": link_policies,
        "created_at": _now(),
        "started_at": "",
        "completed_at": "",
        "summary": {
            "total_items": len(items),
            "queued": len(items),
            "exact_anchor_ratio": lp_check.get("exact_ratio", 0),
            "link_policy_ok": lp_check.get("ok", True),
            "warnings": all_warnings,
            "version": "v2",
        },
    }
    batch["score"] = int(sum(it.get("quality_score", 0) for it in items) / max(len(items), 1))

    st = _load_state()
    st.setdefault("batches", []).insert(0, batch)
    st["batches"] = st["batches"][:BATCH_LIMIT]
    _append_history(st, {"type": "v2_batch_created", "batch_id": batch_id, "source": source, "keyword": keyword, "at": _now()})
    _save_state(st)

    _record_brain_v2(
        "authority_factory_v2_batch_created",
        keyword=keyword,
        domain=money_site,
        result={"batch_id": batch_id, "source": source, "items": len(items), "dataset_id": dataset_id, "campaign_id": campaign_id},
        reason=batch_name,
    )
    for it in items[:5]:
        _record_brain_v2(
            "authority_factory_v2_item_created",
            keyword=keyword,
            result={"item_id": it.get("item_id"), "provider": it.get("provider"), "batch_id": batch_id},
        )

    return {
        "success": True,
        "batch": batch,
        "link_policy_check": lp_check,
        "warnings": all_warnings,
    }


def create_from_dataset(
    dataset_id: str,
    *,
    keyword: str = "",
    money_site: str = "",
    provider_mix: dict[str, int] | None = None,
    auto_process: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled", False):
        return {"success": False, "error": "authority_factory disabled — settings.enabled=true gerekli"}
    if not dataset_id:
        return {"success": False, "error": "dataset_id gerekli"}

    try:
        from app.moduller.data_miner_engine import get_results, list_datasets
        job_res = get_results(dataset_id)
        if not job_res.get("success"):
            ds_list = list_datasets().get("datasets") or []
            match = next((d for d in ds_list if d.get("id") == dataset_id), None)
            if not match:
                return {"success": False, "error": "dataset_not_found"}
            job_res = get_results(match.get("id", dataset_id))
        result = job_res.get("result") or job_res
        entities = result.get("entities") or []
        faqs = result.get("faqs") or []
        kw = (keyword or result.get("keyword") or result.get("source") or "dataset").strip()
        money = (money_site or settings.get("default_money_site") or "").strip()
    except Exception as exc:
        return {"success": False, "error": f"dataset_load_failed:{exc}"}

    items, link_policies, warnings = _build_v2_items(kw, money, provider_mix=provider_mix, entities=entities, faqs=faqs)
    if not items:
        return {"success": False, "error": "no_items_after_build", "warnings": warnings}

    res = _save_v2_batch(
        keyword=kw,
        money_site=money,
        source="data_miner",
        items=items,
        link_policies=link_policies,
        warnings=warnings,
        dataset_id=dataset_id,
        provider_mix=provider_mix,
        name=f"Dataset: {kw}",
    )
    should_process = auto_process if auto_process is not None else settings.get("auto_process", False)
    if should_process and res.get("success"):
        res["process_result"] = process_batch(res["batch"]["batch_id"])
    return res


def _filter_domain_candidates(scores: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    out = []
    for s in scores:
        overall = float(s.get("overall_domain_score") or 0)
        spam = float(s.get("spam_risk_score") or 100)
        if overall >= DOMAIN_SCORE_MIN and spam <= DOMAIN_SPAM_MAX:
            out.append({
                "domain": s.get("domain", ""),
                "overall_domain_score": overall,
                "topical_match_score": s.get("topical_match_score"),
                "brandability_score": s.get("brandability_score"),
                "spam_risk_score": spam,
            })
    out.sort(key=lambda x: -x.get("overall_domain_score", 0))
    return out[:limit]


def list_domain_candidates(limit: int = 50) -> dict[str, Any]:
    try:
        from app.moduller.expireddomain import list_scores
        raw = list_scores().get("scores") or []
    except Exception as exc:
        return {"success": False, "error": str(exc), "candidates": []}
    candidates = _filter_domain_candidates(raw, limit=limit)
    return {"success": True, "candidates": candidates, "count": len(candidates), "thresholds": {"min_overall": DOMAIN_SCORE_MIN, "max_spam": DOMAIN_SPAM_MAX}}


def create_from_domain_candidates(
    *,
    keyword: str = "",
    money_site: str = "",
    domains: list[str] | None = None,
    provider_mix: dict[str, int] | None = None,
    auto_process: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled", False):
        return {"success": False, "error": "authority_factory disabled — settings.enabled=true gerekli"}

    cand_res = list_domain_candidates(limit=100)
    candidates = cand_res.get("candidates") or []
    if domains:
        dom_set = {d.lower().strip() for d in domains}
        candidates = [c for c in candidates if c.get("domain", "").lower() in dom_set]
    if not candidates:
        return {"success": False, "error": "no_qualified_domain_candidates"}

    kw = (keyword or candidates[0].get("domain", "domain")).strip()
    money = (money_site or settings.get("default_money_site") or "").strip()
    items, link_policies, warnings = _build_v2_items(kw, money, provider_mix=provider_mix)
    if not items:
        return {"success": False, "error": "no_items_after_build", "warnings": warnings}

    res = _save_v2_batch(
        keyword=kw,
        money_site=money,
        source="domain_intelligence",
        items=items,
        link_policies=link_policies,
        warnings=warnings,
        domain_candidates=candidates,
        provider_mix=provider_mix,
        name=f"Domain: {kw}",
    )
    should_process = auto_process if auto_process is not None else settings.get("auto_process", False)
    if should_process and res.get("success"):
        res["process_result"] = process_batch(res["batch"]["batch_id"])
    return res


def list_datasets_for_factory(limit: int = 50) -> dict[str, Any]:
    try:
        from app.moduller.data_miner_engine import list_datasets, get_results
        datasets = list_datasets().get("datasets") or []
        enriched = []
        for ds in datasets[:limit]:
            job = get_results(ds.get("id", ""))
            result = (job.get("result") or job) if job.get("success") else {}
            enriched.append({
                **ds,
                "entity_count": ds.get("entity_count") or len(result.get("entities") or []),
                "faq_count": ds.get("faq_count") or len(result.get("faqs") or []),
                "keyword_hint": result.get("keyword") or ds.get("source", ""),
            })
        return {"success": True, "datasets": enriched, "count": len(enriched)}
    except Exception as exc:
        return {"success": False, "error": str(exc), "datasets": []}


def _merge_dataset_entities(payload: dict[str, Any], ds_entities: list) -> list:
    merged: list = list(ds_entities[:20]) if ds_entities else []
    for ent in payload.get("entities") or []:
        if ent and ent not in merged:
            merged.append(ent)
    if payload.get("entity"):
        ent = payload["entity"]
        if ent and ent not in merged:
            merged.insert(0, ent)
    return merged[:20]


def _merge_dataset_faqs(payload: dict[str, Any], ds_faqs: list) -> list:
    merged: list = list(ds_faqs[:20]) if ds_faqs else []
    for faq in payload.get("faqs") or []:
        if faq and faq not in merged:
            merged.append(faq)
    if payload.get("faq"):
        faq = payload["faq"]
        if faq and faq not in merged:
            merged.insert(0, faq)
    return merged[:20]


def _ensure_campaign_dataset_fields(campaign: dict[str, Any]) -> None:
    if not campaign.get("dataset_id"):
        return
    if campaign.get("dataset_entities") and campaign.get("dataset_faqs"):
        return
    try:
        from app.moduller.campaign_engine import _apply_dataset_to_campaign, _load_dataset

        job = _load_dataset(campaign["dataset_id"])
        if job.get("success"):
            _apply_dataset_to_campaign(campaign, job)
    except Exception as exc:
        logger.debug("ensure campaign dataset fields: %s", exc)


def _campaign_tasks_to_items(campaign: dict[str, Any], provider_mix: dict[str, int] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    from app.moduller.authority_mesh_engine import generate_link_policy

    kw = campaign.get("target_keyword", "")
    money = campaign.get("target_money_site") or campaign.get("target_domain") or get_settings().get("default_money_site", "")
    link_policies = generate_link_policy(kw, money)
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    settings = get_settings()
    ds_entities = campaign.get("dataset_entities") or []
    ds_faqs = campaign.get("dataset_faqs") or []
    ds_categories = campaign.get("dataset_categories") or []
    tasks = [
        t for t in (campaign.get("tasks") or [])
        if t.get("item_type") in CAMPAIGN_FACTORY_ITEM_TYPES
        or t.get("factory_eligible")
        or t.get("module") == "authority_factory"
    ]
    if not tasks:
        if campaign.get("dataset_id"):
            return [], link_policies, ["dataset_campaign_requires_plan_first"]
        mix = _effective_provider_mix(provider_mix)
        return _build_v2_items(kw, money, provider_mix=mix)

    idx = 0
    for task in tasks:
        item_type = task.get("item_type") or "authority_source"
        if item_type not in CAMPAIGN_FACTORY_ITEM_TYPES and not task.get("factory_eligible"):
            continue
        providers = CAMPAIGN_ITEM_PROVIDER_MAP.get(item_type, ["blogger"])
        role = CAMPAIGN_ITEM_ROLE_MAP.get(item_type, "entity_hub")
        provider = providers[idx % len(providers)]
        meta = PROVIDERS.get(provider, {"label": provider, "provider_type": "manual"})
        title = task.get("title") or f"{kw} — {item_type}"
        link = link_policies[idx % len(link_policies)] if link_policies else {}
        payload = task.get("payload") or {}
        item_entities = _merge_dataset_entities(payload, ds_entities)
        item_faqs = _merge_dataset_faqs(payload, ds_faqs)
        item = {
            "item_id": _v2_item_id(),
            "provider": provider,
            "provider_type": meta.get("provider_type", "manual"),
            "role": role,
            "title": title,
            "target_keyword": kw,
            "target_url": money,
            "entities": item_entities,
            "faqs": item_faqs,
            "categories": payload.get("categories") or ds_categories[:5],
            "status": "queued",
            "result_url": "",
            "error": "",
            "quality_score": 0,
            "campaign_task_id": task.get("task_id", ""),
            "item_type": item_type,
            "assigned_worker": meta.get("label", provider),
            "link_policy": link,
            "fingerprint": _item_fingerprint(kw, provider, title),
            "dataset_id": campaign.get("dataset_id", ""),
        }
        item["quality_score"] = _compute_item_quality_score(item, settings)
        items.append(item)
        idx += 1
        try:
            from app.moduller.campaign_engine import update_task_factory_status
            update_task_factory_status(task.get("task_id", ""), "sent_to_factory")
        except Exception:
            pass

    max_items = int(settings.get("max_items_per_batch", 25))
    if len(items) > max_items:
        warnings.append(f"items_truncated:{len(items)}>{max_items}")
        items = items[:max_items]
    return items, link_policies, warnings


def create_from_campaign(
    campaign_id: str,
    *,
    provider_mix: dict[str, int] | None = None,
    auto_process: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled", False):
        return {"success": False, "error": "authority_factory disabled — settings.enabled=true gerekli"}
    if not campaign_id:
        return {"success": False, "error": "campaign_id gerekli"}

    try:
        from app.moduller.campaign_engine import get_campaign
        camp_res = get_campaign(campaign_id)
    except Exception as exc:
        return {"success": False, "error": f"campaign_load_failed:{exc}"}
    if not camp_res.get("success"):
        return camp_res

    campaign = camp_res.get("campaign") or {}
    _ensure_campaign_dataset_fields(campaign)
    kw = campaign.get("target_keyword", "")
    money = campaign.get("target_money_site") or campaign.get("target_domain") or settings.get("default_money_site", "")
    items, link_policies, warnings = _campaign_tasks_to_items(campaign, provider_mix)
    if not items:
        return {"success": False, "error": "no_campaign_factory_items", "warnings": warnings}

    res = _save_v2_batch(
        keyword=kw,
        money_site=money,
        source="campaign",
        items=items,
        link_policies=link_policies,
        warnings=warnings,
        campaign_id=campaign_id,
        dataset_id=campaign.get("dataset_id", ""),
        provider_mix=provider_mix,
        name=f"Campaign: {kw}",
        project_id=campaign.get("project_id", ""),
    )
    should_process = auto_process if auto_process is not None else settings.get("auto_process", False)
    if should_process and res.get("success"):
        res["process_result"] = process_batch(res["batch"]["batch_id"])
    return res


def validate_batch(batch_id: str) -> dict[str, Any]:
    st = _load_state()
    batch = _find_batch(st, batch_id)
    if not batch:
        return {"success": False, "error": "batch_not_found"}
    settings = get_settings()
    issues: list[str] = []
    items = batch.get("items") or []
    if not items:
        issues.append("empty_batch")
    if len(items) > int(settings.get("max_items_per_batch", 25)):
        issues.append("max_items_exceeded")
    lp = _validate_link_policy(batch.get("link_policies") or [], batch.get("target_keyword", ""), settings)
    if not lp.get("ok", True):
        issues.append("link_policy_violation")
    low_quality = [it for it in items if _compute_item_quality_score(it, settings) < int(settings.get("min_quality_score", MIN_QUALITY_SCORE))]
    if low_quality:
        issues.append(f"low_quality_items:{len(low_quality)}")
    for it in items:
        allowed, reason = _provider_allowed(it.get("provider", ""), settings)
        if not allowed:
            issues.append(f"provider_blocked:{it.get('provider')}:{reason}")
    return {
        "success": len(issues) == 0,
        "batch_id": batch_id,
        "valid": len(issues) == 0,
        "issues": issues,
        "link_policy": lp,
        "item_count": len(items),
        "batch_score": batch.get("score", 0),
    }


def process_item(item_id: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled", False):
        return {"success": False, "error": "authority_factory disabled"}

    st = _load_state()
    batch, item = _find_item_global(st, item_id)
    if not batch or not item:
        return {"success": False, "error": "item_not_found"}

    if item.get("status") not in ("queued", "planned", "review_required"):
        return {"success": True, "item": item, "message": f"already_{item.get('status')}"}

    item["status"] = "processing"
    _save_state(st)

    task_id = item.get("campaign_task_id", "")
    if task_id:
        try:
            from app.moduller.campaign_engine import update_task_factory_status
            update_task_factory_status(task_id, "factory_processing")
        except Exception:
            pass

    provider = item.get("provider", "")
    ptype = item.get("provider_type") or PROVIDERS.get(provider, {}).get("provider_type", "manual")

    if provider == "github_pages":
        res = _process_github_pages_item(item, batch, settings)
    elif provider == "google_sites":
        res = _process_google_sites_item(item, batch, settings)
    elif provider in ("blogger", "tumblr", "devto", "wordpress"):
        res = _process_publisher_item(item, batch, settings)
    elif provider == "astro":
        res = _process_astro_item(item, batch, settings)
    elif ptype in ("browser", "manual"):
        res = _process_browser_manual_item(item)
    else:
        item["status"] = "review_required"
        res = {"success": True, "status": "review_required"}

    _apply_quality_gate(item, settings)

    if item.get("status") == "published":
        _record_brain_v2(
            "authority_factory_v2_item_published",
            keyword=item.get("target_keyword", ""),
            domain=item.get("result_url", ""),
            result={"item_id": item_id, "provider": provider, "url": item.get("result_url")},
        )
        if task_id:
            try:
                from app.moduller.campaign_engine import update_task_factory_status
                update_task_factory_status(task_id, "factory_completed")
            except Exception:
                pass
    elif item.get("status") == "login_required":
        _record_brain_v2("authority_factory_v2_login_required", keyword=item.get("target_keyword", ""), result={"item_id": item_id, "provider": provider})
    elif item.get("status") == "provider_missing":
        _record_brain_v2("authority_factory_v2_provider_missing", keyword=item.get("target_keyword", ""), result={"item_id": item_id, "provider": provider})
    elif item.get("status") == "failed":
        _record_brain_v2("authority_factory_v2_item_failed", keyword=item.get("target_keyword", ""), result={"item_id": item_id, "error": item.get("error")})

    published = sum(1 for it in batch.get("items") or [] if it.get("status") == "published")
    total = len(batch.get("items") or [])
    if published == total and total > 0:
        batch["status"] = "completed"
        batch["completed_at"] = _now()
        _record_brain_v2("authority_factory_v2_batch_completed", keyword=batch.get("target_keyword", ""), result={"batch_id": batch.get("batch_id"), "published": published})

    _save_state(st)
    return {"success": res.get("success", False), "item": item, "batch_id": batch.get("batch_id"), "result": res}


def executive_payload() -> dict[str, Any]:
    dash = dashboard()
    v2_batches = [b for b in (_load_state().get("batches") or []) if str(b.get("batch_id", "")).startswith("af2-")]
    failed = int(dash.get("failed_items") or 0)
    login_req = int(dash.get("login_required_items") or 0)
    published = int(dash.get("published_items") or 0)
    queued = int(dash.get("queued_items") or 0)
    total = max(int(dash.get("total_items") or 1), 1)
    execution = _clamp_pct(published / total * 100)
    risk = _clamp_pct(failed * 8 + login_req * 12 + (0 if dash.get("enabled") else 25))
    growth = _clamp_pct(len(v2_batches) * 10 + published * 5 + queued * 2)
    return {
        "success": True,
        "authority_execution_score": execution,
        "authority_factory_risk": risk,
        "authority_growth_potential": growth,
        "v2_batches": len(v2_batches),
        "published_items": published,
        "queued_items": queued,
    }


def _clamp_pct(val: float) -> int:
    return max(0, min(100, int(round(val))))


def mission_control_payload() -> dict[str, Any]:
    """Mission Control entegrasyonu — factory batch özeti."""
    dash = dashboard()
    v2_count = sum(1 for b in (_load_state().get("batches") or []) if str(b.get("batch_id", "")).startswith("af2-"))
    return {
        "success": True,
        "factory_batches": dash.get("batches_count", 0),
        "authority_factory_v2_batches": v2_count,
        "processing_items": dash.get("processing_items", 0),
        "processing_authority_items": dash.get("processing_items", 0),
        "published_authority_items": dash.get("published_items", 0),
        "login_required_items": dash.get("login_required_items", 0),
        "provider_missing_items": dash.get("provider_missing_items", 0),
        "failed_items": dash.get("failed_items", 0),
        "published_today": dash.get("published_today", 0),
        "queued_batches": dash.get("queued_batches", 0),
        "recent_batches": dash.get("recent_batches", []),
        "executive": executive_payload(),
    }


def dashboard() -> dict[str, Any]:
    st = _load_state()
    batches = st.get("batches") or []
    all_items: list[dict] = []
    for b in batches:
        all_items.extend(b.get("items") or [])

    today = _today()
    published_today = 0
    for b in batches:
        if b.get("completed_at", "").startswith(today):
            published_today += int((b.get("summary") or {}).get("published") or 0)
    for it in all_items:
        if it.get("status") == "published" and it.get("result_url"):
            published_today += 0  # item-level timestamp yok — batch summary kullanılıyor

    by_provider: dict[str, int] = {}
    for it in all_items:
        p = it.get("provider", "?")
        by_provider[p] = by_provider.get(p, 0) + 1

    return {
        "success": True,
        "module": "authority_factory",
        "enabled": get_settings().get("enabled", False),
        "batches_count": len(batches),
        "queued_batches": sum(1 for b in batches if b.get("status") in ("queued", "planned")),
        "processing_batches": sum(1 for b in batches if b.get("status") == "processing"),
        "completed_batches": sum(1 for b in batches if b.get("status") == "completed"),
        "failed_batches": sum(1 for b in batches if b.get("status") == "failed"),
        "total_items": len(all_items),
        "queued_items": sum(1 for it in all_items if it.get("status") in ("queued", "planned")),
        "processing_items": sum(1 for it in all_items if it.get("status") == "processing"),
        "published_items": sum(1 for it in all_items if it.get("status") == "published"),
        "failed_items": sum(1 for it in all_items if it.get("status") in ("failed", "provider_missing")),
        "provider_missing_items": sum(1 for it in all_items if it.get("status") == "provider_missing"),
        "login_required_items": sum(1 for it in all_items if it.get("status") == "login_required"),
        "review_required_items": sum(1 for it in all_items if it.get("status") == "review_required"),
        "published_today": published_today,
        "by_provider": by_provider,
        "recent_batches": batches[:15],
        "v2_batches": sum(1 for b in batches if str(b.get("batch_id", "")).startswith("af2-")),
        "dataset_driven_batches": sum(1 for b in batches if b.get("source") == "data_miner"),
        "domain_driven_batches": sum(1 for b in batches if b.get("source") == "domain_intelligence"),
        "campaign_driven_batches": sum(1 for b in batches if b.get("source") == "campaign"),
        "provider_mix": get_provider_mix().get("provider_mix", V2_DEFAULT_PROVIDER_MIX),
        "provider_status": _provider_status(),
        "settings": get_settings(),
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "overview": dashboard,
        "batches": lambda: list_batches(100),
        "items": lambda: list_items(limit=200),
        "providers": lambda: {"success": True, "providers": _provider_status()},
    }
    fn = generators.get(report_type, dashboard)
    payload = fn()
    path = REPORTS_DIR / f"authority-factory-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def health() -> dict[str, Any]:
    settings = get_settings()
    dash = dashboard()
    return {
        "success": True,
        "module": "authority_factory",
        "enabled": settings.get("enabled", False),
        "auto_process": settings.get("auto_process", False),
        "providers": {k: v["provider_type"] for k, v in PROVIDERS.items()},
        "provider_status": dash.get("provider_status", {}),
        "batches_count": dash.get("batches_count", 0),
        "queued_items": dash.get("queued_items", 0),
        "safety": {
            "allow_github_pages": settings.get("allow_github_pages", False),
            "allow_google_sites": settings.get("allow_google_sites", False),
            "allow_publisher": settings.get("allow_publisher", True),
            "allow_astro": settings.get("allow_astro", False),
        },
    }
