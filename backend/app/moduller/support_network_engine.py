"""
Support Network Engine V1 — domain orkestrasyon katmanı.

İçerik üretmez. Mevcut modülleri okur ve network/domain kararlarını üretir.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app import config

logger = logging.getLogger("hive.support_network_engine")

STATE_FILE = Path(__file__).resolve().parent.parent / "support_network_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

# network_replicator rolleri + ek roller
BASE_ROLES = (
    "money_site",
    "brand_hub",
    "geo_hub",
    "entity_hub",
    "faq_hub",
    "blog_hub",
    "support_hub",
    "city_hub",
    "topic_hub",
    "authority_hub",
    "publisher_hub",
)

NETWORK_GROUPS = {
    "money_sites": ["money_site", "brand_hub"],
    "brand_sites": ["brand_hub"],
    "geo_sites": ["geo_hub", "city_hub"],
    "entity_sites": ["entity_hub"],
    "faq_sites": ["faq_hub"],
    "blog_sites": ["blog_hub", "topic_hub"],
    "support_sites": ["support_hub", "authority_hub"],
    "authority_sites": ["authority_hub", "money_site"],
    "publisher_channels": ["publisher_hub"],
}

ROLE_LABELS = {
    "money_site": "Money Site",
    "brand_hub": "Brand Hub",
    "geo_hub": "GEO Hub",
    "entity_hub": "Entity Hub",
    "faq_hub": "FAQ Hub",
    "blog_hub": "Blog Hub",
    "support_hub": "Support Hub",
    "city_hub": "City Hub",
    "topic_hub": "Topic Hub",
    "authority_hub": "Authority Hub",
    "publisher_hub": "Publisher Hub",
}

PUBLISHER_CHANNEL_IDS = (
    "wordpress", "blogger", "tumblr", "devto", "medium",
    "google_sites", "linkedin", "quora", "ghost", "hashnode",
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "default_network_id": "",
    "keyword_cannibalization_threshold": 0.85,
    "authority_overload_threshold": 8,
    "outbound_link_warning": 15,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("domain_overrides", {})
                data.setdefault("link_plans", [])
                data.setdefault("keyword_registry", {})
                data.setdefault("jobs", {})
                data.setdefault("network_cache", {})
                data.setdefault("last_sync_at", "")
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "domain_overrides": {},
        "link_plans": [],
        "keyword_registry": {},
        "jobs": {},
        "network_cache": {},
        "last_sync_at": "",
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, Any]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = st.setdefault("settings", dict(DEFAULT_SETTINGS))
    cur.update(patch)
    _save_state(st)
    return dict(cur)


def _host(domain: str) -> str:
    d = (domain or "").strip()
    if d.startswith("http"):
        return urlparse(d).netloc or d
    return d.split("/")[0].lower()


def _group_for_role(role: str) -> str:
    for group, roles in NETWORK_GROUPS.items():
        if role in roles:
            return group
    return "support_sites"


def _latest_gate_report(project_id: str) -> dict[str, Any]:
    gate_path = Path(__file__).resolve().parent.parent / "seo_quality_gate_state.json"
    if not gate_path.exists():
        return {}
    try:
        data = json.loads(gate_path.read_text(encoding="utf-8"))
        best: dict[str, Any] = {}
        for report in (data.get("reports") or {}).values():
            if report.get("project_id") != project_id:
                continue
            if not best or (report.get("created_at", "") > best.get("created_at", "")):
                best = report
        return best
    except (json.JSONDecodeError, OSError):
        return {}


def _rank_project(project_id: str) -> dict[str, Any]:
    try:
        from app.moduller.rank_index_watcher import get_project
        res = get_project(project_id)
        return res.get("project") or {} if res.get("success") else {}
    except Exception as exc:
        logger.debug("rank project: %s", exc)
        return {}


def _astro_project(project_id: str) -> dict[str, Any]:
    if not project_id:
        return {}
    try:
        from app.moduller.astro_factory import _get_project
        return _get_project(project_id)
    except Exception:
        return {}


def _entity_scores(project_id: str) -> dict[str, Any]:
    if not project_id:
        return {}
    try:
        from app.moduller.entity_geo_graph import get_project_scores
        return get_project_scores(project_id) or {}
    except Exception as exc:
        logger.debug("entity scores: %s", exc)
        return {}


def _content_stats(project_id: str) -> dict[str, Any]:
    if not project_id:
        return {"content_count": 0, "last_content_date": ""}
    try:
        from app.moduller.astro_factory import _get_project, _project_path
        project = _get_project(project_id)
        data_dir = _project_path(project["slug"]) / "src" / "data"
        count = 0
        latest = project.get("updated_at", "")
        for fname in ("pages.json", "faqs.json", "blog.json", "entity_pages.json"):
            p = data_dir / fname
            if not p.exists():
                continue
            raw = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                count += len(raw)
            elif isinstance(raw, dict):
                count += len(raw.get("geo") or []) + (1 if raw.get("home") else 0)
                for faq in raw.get("faqs") or []:
                    if isinstance(faq, dict):
                        count += 1
        return {"content_count": count, "last_content_date": latest}
    except Exception:
        return {"content_count": 0, "last_content_date": ""}


def _publisher_queue_size(project_id: str) -> int:
    try:
        from app.moduller.publisher_hub import get_queue
        q = get_queue().get("queue") or []
        return sum(1 for i in q if i.get("project_id") == project_id)
    except Exception:
        return 0


def _astro_queue_size(project_id: str) -> int:
    try:
        from app.moduller.astro_auto_publisher import get_queue
        q = get_queue().get("queue") or []
        return sum(1 for i in q if i.get("project_id") == project_id)
    except Exception:
        return 0


def _refresh_candidates(project_id: str) -> int:
    cre_path = Path(__file__).resolve().parent.parent / "content_refresh_engine_state.json"
    if not cre_path.exists():
        return 0
    try:
        data = json.loads(cre_path.read_text(encoding="utf-8"))
        cands = data.get("candidates", {}).get(project_id) or []
        return sum(1 for c in cands if c.get("refresh_needed"))
    except Exception:
        return 0


def _refresh_meta(project_id: str) -> dict[str, Any]:
    cre_path = Path(__file__).resolve().parent.parent / "content_refresh_engine_state.json"
    if not cre_path.exists():
        return {"refresh_candidates": 0, "last_refresh_date": ""}
    try:
        data = json.loads(cre_path.read_text(encoding="utf-8"))
        cands = data.get("candidates", {}).get(project_id) or []
        needed = [c for c in cands if c.get("refresh_needed")]
        last = ""
        for job in (data.get("jobs") or {}).values():
            if job.get("project_id") == project_id and job.get("finished_at", "") > last:
                last = job.get("finished_at", "")
        return {
            "refresh_candidates": len(needed),
            "last_refresh_date": last or data.get("last_refresh_at", ""),
        }
    except Exception:
        return {"refresh_candidates": 0, "last_refresh_date": ""}


def _publisher_channel_map() -> dict[str, list[str]]:
    """project_id/domain → yayın yapılan kanallar (Publisher Hub published)."""
    mapping: dict[str, set[str]] = {}
    try:
        from app.moduller.publisher_hub import get_published
        for item in get_published(limit=500).get("published") or []:
            pid = item.get("project_id") or ""
            dom = _host(item.get("domain") or item.get("canonical_url") or "")
            for ch in item.get("channels") or []:
                if ch:
                    if pid:
                        mapping.setdefault(pid, set()).add(ch)
                    if dom:
                        mapping.setdefault(dom, set()).add(ch)
    except Exception as exc:
        logger.debug("publisher channel map: %s", exc)
    return {k: sorted(v) for k, v in mapping.items()}


def _deploy_pending(project_id: str) -> bool:
    try:
        from app.moduller.astro_auto_publisher import get_queue
        for q in get_queue().get("queue") or []:
            if q.get("project_id") == project_id and q.get("status") in ("queued", "pending", "processing"):
                return True
    except Exception:
        pass
    return False


def _cloudflare_meta(project: dict[str, Any]) -> dict[str, Any]:
    try:
        from app.moduller.cloudflare_pages_deploy import cf_status
        cf = cf_status()
        if not cf.get("configured"):
            return {"configured": False, "error": "Cloudflare API token veya account_id eksik"}
    except Exception as exc:
        return {"configured": False, "error": str(exc)}
    pinfo = (project.get("cloudflare") or {}) if project else {}
    return {
        "configured": True,
        "project_name": pinfo.get("project_name") or pinfo.get("pages_project") or "",
        "deploy_url": pinfo.get("deploy_url") or pinfo.get("last_deploy_url") or "",
    }


def _integration_status() -> dict[str, Any]:
    """Gerçek modül sağlığı — mock başarı yok."""
    checks: dict[str, Any] = {}

    def _chk(name: str, fn):
        try:
            res = fn()
            ok = bool(res.get("success", True)) if isinstance(res, dict) else bool(res)
            checks[name] = {"ok": ok, "detail": res}
        except Exception as exc:
            checks[name] = {"ok": False, "error": str(exc)}

    _chk("network_replicator", lambda: __import__(
        "app.moduller.network_replicator", fromlist=["health"]
    ).health())
    _chk("astro_factory", lambda: __import__(
        "app.moduller.astro_factory", fromlist=["health"]
    ).health())
    _chk("publisher_hub", lambda: __import__(
        "app.moduller.publisher_hub", fromlist=["health"]
    ).health())
    _chk("rank_index_watcher", lambda: __import__(
        "app.moduller.rank_index_watcher", fromlist=["health"]
    ).health())
    _chk("entity_geo_graph", lambda: __import__(
        "app.moduller.entity_geo_graph", fromlist=["health"]
    ).health())
    _chk("content_refresh_engine", lambda: __import__(
        "app.moduller.content_refresh_engine", fromlist=["health"]
    ).health())
    _chk("astro_auto_publisher", lambda: __import__(
        "app.moduller.astro_auto_publisher", fromlist=["health"]
    ).health())
    try:
        from app.moduller.cloudflare_pages_deploy import cf_status
        cf = cf_status()
        checks["cloudflare_deploy"] = {
            "ok": cf.get("configured", False),
            "detail": cf,
            "error": None if cf.get("configured") else "CLOUDFLARE_API_TOKEN veya CLOUDFLARE_ACCOUNT_ID eksik",
        }
    except Exception as exc:
        checks["cloudflare_deploy"] = {"ok": False, "error": str(exc)}

    return checks


def build_domain_profile(
    domain_entry: dict[str, Any],
    network_id: str = "",
    network_name: str = "",
    main_domain: str = "",
    channel_map: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Tek domain için birleşik profil — gerçek modül verilerinden."""
    domain = _host(domain_entry.get("domain", ""))
    role = domain_entry.get("role") or "support_hub"
    if domain_entry.get("status") == "primary" and role == "brand_hub":
        role = "money_site"
    pid = domain_entry.get("project_id") or ""
    project = _astro_project(pid)
    gate = _latest_gate_report(pid)
    rank = _rank_project(pid)
    entity = _entity_scores(pid)
    content = _content_stats(pid)
    refresh = _refresh_meta(pid)
    cf_meta = _cloudflare_meta(project)
    ch_map = channel_map if channel_map is not None else _publisher_channel_map()

    keywords = []
    for kw in rank.get("keywords") or []:
        if isinstance(kw, dict) and kw.get("keyword"):
            keywords.append({
                "keyword": kw["keyword"],
                "last_position": kw.get("last_position"),
                "decay_score": kw.get("ranking_decay_score", 0),
                "trend": kw.get("trend_direction", "flat"),
            })

    overall = int(gate.get("overall_score") or domain_entry.get("quality_score") or 0)
    gate_status = "pass"
    if overall < 85:
        gate_status = "fail"
    elif overall < 90 or int(gate.get("risk_score") or 0) > 25:
        gate_status = "warning"

    overrides = (_load_state().get("domain_overrides") or {}).get(domain, {})
    publish_channels = overrides.get("publish_channels") or ch_map.get(pid) or ch_map.get(domain) or []
    supports = overrides.get("supports_domain") or (
        main_domain if role in ("support_hub", "blog_hub", "faq_hub", "authority_hub") and main_domain else ""
    )
    cluster = overrides.get("cluster") or project.get("seed_keyword") or entity.get("primary_cluster") or ""

    profile = {
        "domain": domain,
        "role": role,
        "role_label": ROLE_LABELS.get(role, role),
        "network_group": _group_for_role(role),
        "network_id": network_id,
        "network_name": network_name,
        "supports_domain": supports,
        "cluster": cluster,
        "project_id": pid,
        "cloudflare_project": cf_meta.get("project_name") or "",
        "cloudflare_configured": cf_meta.get("configured", False),
        "publish_channels": publish_channels,
        "authority_score": int(
            domain_entry.get("authority_score")
            or gate.get("authority_score")
            or entity.get("topic_authority_score")
            or overall
        ),
        "trust_score": max(0, 100 - int(gate.get("risk_score") or 0)),
        "entity_score": int(entity.get("entity_strength_score") or gate.get("entity_score") or 0),
        "geo_score": int(entity.get("geo_coverage_score") or gate.get("geo_score") or 0),
        "content_count": content["content_count"],
        "indexed_pages": len(rank.get("index_status") or []),
        "ranking_keywords": keywords,
        "last_content_date": content["last_content_date"] or project.get("updated_at", ""),
        "last_publish_date": domain_entry.get("last_publish") or "",
        "last_refresh_date": refresh.get("last_refresh_date", ""),
        "network_links": overrides.get("network_links") or [],
        "quality_score": overall,
        "status": domain_entry.get("status") or "unknown",
        "build_status": domain_entry.get("build_status", ""),
        "deploy_status": domain_entry.get("deploy_status", ""),
        "deploy_pending": _deploy_pending(pid),
        "quality_gate_status": gate_status,
        "deploy_blocked": bool(gate.get("deploy_allowed") is False or gate.get("support_network_ready") is False),
        "support_network_ready": bool(gate.get("support_network_ready")),
        "publisher_queue": _publisher_queue_size(pid),
        "astro_queue": _astro_queue_size(pid),
        "refresh_candidates": refresh.get("refresh_candidates", 0),
        "should_produce_content": content["content_count"] < 3 or refresh.get("refresh_candidates", 0) > 0,
        "should_link_out": role in ("support_hub", "blog_hub", "faq_hub", "geo_hub", "city_hub"),
        "risk_flags": [],
        "seed_keyword": project.get("seed_keyword", ""),
        "location": project.get("location", ""),
        "site_name": project.get("site_name", ""),
    }
    if profile["quality_gate_status"] == "fail":
        profile["risk_flags"].append("quality_gate_fail")
    if profile["refresh_candidates"] > 0:
        profile["risk_flags"].append("refresh_needed")
    if profile["content_count"] == 0:
        profile["risk_flags"].append("no_content")
    return profile


def _iter_all_domains(network_id: str = "") -> list[dict[str, Any]]:
    from app.moduller.network_replicator import list_networks
    res = list_networks()
    if not res.get("success"):
        return []
    ch_map = _publisher_channel_map()
    domains: list[dict[str, Any]] = []
    for net in res.get("networks") or []:
        nid = net.get("network_id", "")
        if network_id and nid != network_id:
            continue
        main = _host(net.get("main_domain", ""))
        for d in net.get("domains") or []:
            domains.append(build_domain_profile(
                d, network_id=nid, network_name=net.get("name", ""),
                main_domain=main, channel_map=ch_map,
            ))
    if not domains:
        # fallback: astro factory projeleri
        try:
            from app.moduller.astro_factory import list_projects
            for p in list_projects().get("projects") or []:
                domains.append(build_domain_profile({
                    "domain": p.get("domain", ""),
                    "role": "brand_hub",
                    "project_id": p.get("id", ""),
                    "status": p.get("status", "active"),
                    "quality_score": 0,
                    "last_publish": "",
                }))
        except Exception as exc:
            logger.warning("astro fallback: %s", exc)
    return domains


def list_domains(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    grouped: dict[str, list] = {g: [] for g in NETWORK_GROUPS}
    for d in domains:
        grouped.setdefault(d["network_group"], []).append(d)
    return {"success": True, "count": len(domains), "domains": domains, "grouped": grouped}


def authority_map(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    if not domains:
        return {"success": False, "error": "Domain bulunamadı — önce Network Replicator'da ağ oluşturun"}

    settings = get_settings()
    overload_thr = int(settings.get("authority_overload_threshold") or 8)
    outbound_thr = int(settings.get("outbound_link_warning") or 15)

    carrying: list[dict] = []
    losing: list[dict] = []
    no_contribution: list[dict] = []
    no_content: list[dict] = []
    high_outbound: list[dict] = []
    no_inbound: list[dict] = []
    idle_wasting: list[dict] = []
    supporting_money: list[dict] = []

    money_domains = {_host(d["domain"]) for d in domains if d["role"] in ("money_site", "brand_hub")}

    for d in domains:
        auth = d["authority_score"]
        kws = d.get("ranking_keywords") or []
        decaying = sum(1 for k in kws if (k.get("decay_score") or 0) >= 30)
        outbound = len(d.get("network_links") or [])

        if auth >= 75:
            carrying.append({"domain": d["domain"], "role": d["role"], "authority_score": auth})
        if decaying >= 2 or any(k.get("trend") == "decaying" for k in kws):
            losing.append({"domain": d["domain"], "decaying_keywords": decaying, "authority_score": auth})
        if auth < 40 and d["content_count"] < 3:
            no_contribution.append({"domain": d["domain"], "authority_score": auth})
        if d["content_count"] == 0:
            no_content.append({"domain": d["domain"], "role": d["role"]})
        if outbound >= outbound_thr:
            high_outbound.append({"domain": d["domain"], "outbound_links": outbound})
        if auth < 50 and not d.get("network_links"):
            no_inbound.append({"domain": d["domain"]})
        if d["content_count"] == 0 and not d.get("publish_channels") and d["publisher_queue"] == 0:
            idle_wasting.append({"domain": d["domain"], "role": d["role"]})
        sup = d.get("supports_domain") or ""
        if sup and _host(sup) in money_domains:
            supporting_money.append({
                "domain": d["domain"],
                "role": d["role"],
                "supports": sup,
            })

    return {
        "success": True,
        "carrying_authority": carrying,
        "losing_authority": losing,
        "no_contribution": no_contribution,
        "no_content": no_content,
        "high_outbound": high_outbound,
        "no_inbound_links": no_inbound,
        "idle_wasting": idle_wasting,
        "supporting_money_site": supporting_money,
        "overloaded": [
            {"domain": d["domain"], "keyword_count": len(d.get("ranking_keywords") or [])}
            for d in domains if len(d.get("ranking_keywords") or []) >= overload_thr
        ],
        "summary": {
            "total_domains": len(domains),
            "avg_authority": round(sum(d["authority_score"] for d in domains) / len(domains), 1),
        },
    }


def link_strategy(network_id: str = "", max_per_domain: int = 5) -> dict[str, Any]:
    """Link planı üret — gerçek link eklemez."""
    domains = _iter_all_domains(network_id)
    if not domains:
        return {"success": False, "error": "Domain yok"}

    plans: list[dict[str, Any]] = []
    by_role: dict[str, list] = {}
    for d in domains:
        by_role.setdefault(d["role"], []).append(d)

    money = by_role.get("brand_hub", []) + by_role.get("money_site", [])
    support = by_role.get("support_hub", []) + by_role.get("blog_hub", [])
    geo = by_role.get("geo_hub", []) + by_role.get("city_hub", [])
    entity = by_role.get("entity_hub", [])
    faq = by_role.get("faq_hub", [])

    def add_plan(src: dict, tgt: dict, anchor: str, reason: str):
        plans.append({
            "from_domain": src["domain"],
            "from_role": src["role"],
            "to_domain": tgt["domain"],
            "to_role": tgt["role"],
            "suggested_page": tgt.get("seed_keyword") or tgt["domain"],
            "anchor_text": anchor,
            "reason": reason,
            "action": "plan_only",
        })

    # support → money
    for s in support[:max_per_domain]:
        for m in money[:2]:
            if s["domain"] != m["domain"]:
                add_plan(s, m, m.get("seed_keyword") or m["site_name"] or m["domain"], "support_to_money")

    # geo → entity
    for g in geo[:max_per_domain]:
        for e in entity[:2]:
            add_plan(g, e, e.get("location") or e["domain"], "geo_to_entity")

    # faq → geo
    for f in faq[:max_per_domain]:
        for g in geo[:1]:
            add_plan(f, g, g.get("location") or "yerel rehber", "faq_to_geo")

    # entity graph internal plans
    for d in domains:
        pid = d.get("project_id")
        if not pid:
            continue
        try:
            from app.moduller.entity_geo_graph import internal_link_plan
            ilp = internal_link_plan(pid, max_links_per_page=max_per_domain)
            if not ilp.get("success"):
                continue
            for link in (ilp.get("links") or [])[:max_per_domain]:
                plans.append({
                    "from_domain": d["domain"],
                    "from_role": d["role"],
                    "to_domain": d["domain"],
                    "to_role": d["role"],
                    "suggested_page": link.get("target_label") or link.get("target", ""),
                    "anchor_text": link.get("anchor") or link.get("suggested_anchor", ""),
                    "reason": link.get("reason", "entity_graph"),
                    "action": "plan_only",
                })
        except Exception as exc:
            logger.debug("internal_link_plan %s: %s", pid, exc)

    st = _load_state()
    st["link_plans"] = plans[-2000:]
    st["last_sync_at"] = _now()
    _save_state(st)
    return {"success": True, "count": len(plans), "plans": plans}


def _kw_similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def keyword_distribution(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    settings = get_settings()
    threshold = float(settings.get("keyword_cannibalization_threshold") or 0.85)

    registry: dict[str, list] = {}
    for d in domains:
        pid = d.get("project_id") or d["domain"]
        kws = set()
        if d.get("seed_keyword"):
            kws.add(d["seed_keyword"].lower())
        for kw in d.get("ranking_keywords") or []:
            if kw.get("keyword"):
                kws.add(kw["keyword"].lower())
        for kw in kws:
            registry.setdefault(kw, []).append({
                "domain": d["domain"],
                "role": d["role"],
                "project_id": pid,
            })

    by_domain = {d["domain"]: d for d in domains}
    network_ids = {d.get("network_id") for d in domains if d.get("network_id")}

    cannibalization: list[dict] = []
    seen_pairs: set[tuple] = set()
    keys = list(registry.keys())

    def _risk_score(sim: float, domain_count: int, scope: str) -> int:
        base = int(sim * 50) + domain_count * 15
        if scope == "city_hub":
            base += 20
        if scope == "cluster":
            base += 10
        return min(100, base)

    for i, k1 in enumerate(keys):
        for k2 in keys[i + 1:]:
            sim = _kw_similar(k1, k2)
            if sim < threshold and k1 != k2:
                continue
            pair = tuple(sorted([k1, k2]))
            if pair in seen_pairs:
                continue
            entries = registry.get(k1, []) + ([e for e in registry.get(k2, []) if k1 != k2] if k1 != k2 else [])
            hosts = {e["domain"] for e in entries}
            if len(hosts) <= 1:
                continue
            seen_pairs.add(pair)

            # aynı keyword exact duplicate
            if k1 == k2 or sim >= 0.99:
                kw_label = k1
            else:
                kw_label = f"{k1} ~ {k2}"

            scopes: list[str] = ["network"]
            doms = [by_domain.get(h, {}) for h in hosts]
            if len({d.get("network_id") for d in doms if d.get("network_id")}) <= 1 and network_ids:
                scopes.append("network")
            clusters = {d.get("cluster") for d in doms if d.get("cluster")}
            if len(clusters) == 1 and list(clusters)[0]:
                scopes.append("cluster")
            cities = {d.get("location", "").lower() for d in doms if d.get("location")}
            city_roles = sum(1 for d in doms if d.get("role") in ("city_hub", "geo_hub"))
            if city_roles >= 2 and cities:
                scopes.append("city_hub")

            risk = _risk_score(max(sim, 0.85 if k1 == k2 else sim), len(hosts), scopes[-1])
            cannibalization.append({
                "keyword": kw_label,
                "keyword_a": k1,
                "keyword_b": k2 if k1 != k2 else k1,
                "similarity": round(sim if k1 != k2 else 1.0, 3),
                "domains": sorted(hosts),
                "scope": scopes,
                "risk": "critical" if risk >= 75 else "high" if risk >= 50 else "medium",
                "risk_score": risk,
            })

    duplicates = [
        {"keyword": kw, "domains": entries, "count": len(entries)}
        for kw, entries in registry.items()
        if len(entries) > 1
    ]

    st = _load_state()
    st["keyword_registry"] = {k: v for k, v in list(registry.items())[:500]}
    _save_state(st)

    return {
        "success": True,
        "unique_keywords": len(registry),
        "duplicate_keywords": duplicates,
        "cannibalization_risks": cannibalization,
        "risk_count": len(cannibalization),
        "avg_risk_score": round(
            sum(c.get("risk_score", 0) for c in cannibalization) / max(len(cannibalization), 1), 1
        ),
    }


def network_health(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    if not domains:
        return {"success": False, "error": "Analiz için domain yok"}

    n = len(domains)
    auth_avg = sum(d["authority_score"] for d in domains) / n
    geo_avg = sum(d["geo_score"] for d in domains) / n
    entity_avg = sum(d["entity_score"] for d in domains) / n
    fresh = sum(1 for d in domains if d.get("last_content_date")) / n * 100
    indexed = sum(d.get("indexed_pages", 0) for d in domains) / max(n, 1)
    publish_active = sum(1 for d in domains if d.get("last_publish_date")) / n * 100
    gate_pass = sum(1 for d in domains if d.get("quality_gate_status") == "pass") / n * 100

    roles_present = {d["role"] for d in domains}
    coverage = len(roles_present) / len(BASE_ROLES) * 100

    scores = {
        "authority": round(auth_avg, 1),
        "coverage": round(coverage, 1),
        "content_freshness": round(fresh, 1),
        "geo_coverage": round(geo_avg, 1),
        "entity_coverage": round(entity_avg, 1),
        "link_balance": round(100 - min(100, sum(len(d.get("network_links") or []) for d in domains) / n * 5), 1),
        "publish_activity": round(publish_active, 1),
        "index_coverage": round(min(100, indexed * 10), 1),
        "quality_gate_pass_rate": round(gate_pass, 1),
    }
    overall = round(sum(scores.values()) / len(scores), 1)

    return {
        "success": True,
        "overall_network_score": overall,
        "network_score": overall,
        "scores": scores,
        "domain_count": n,
        "roles_present": sorted(roles_present),
    }


def network_gaps(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    roles = {d["role"] for d in domains}
    locations = {d.get("location", "").lower() for d in domains if d.get("location")}
    keywords = {d.get("seed_keyword", "").lower() for d in domains if d.get("seed_keyword")}

    expected_roles = set(BASE_ROLES) - {"money_site"}
    missing_roles = sorted(expected_roles - roles)

    gaps: list[dict] = []
    for r in missing_roles:
        gaps.append({"type": "missing_role", "item": r, "label": ROLE_LABELS.get(r, r)})

    if "geo_hub" not in roles and "city_hub" not in roles:
        gaps.append({"type": "missing_geo_hub", "item": "geo_hub"})
    if "faq_hub" not in roles:
        gaps.append({"type": "missing_faq_hub", "item": "faq_hub"})
    if "entity_hub" not in roles:
        gaps.append({"type": "missing_entity_hub", "item": "entity_hub"})
    if "support_hub" not in roles:
        gaps.append({"type": "missing_support_site", "item": "support_hub"})
    if "authority_hub" not in roles:
        gaps.append({"type": "missing_authority_support", "item": "authority_hub"})
    if "topic_hub" not in roles:
        gaps.append({"type": "missing_topic_cluster", "item": "topic_hub"})

    # eksik şehir — network'te beklenen lokasyon kapsamı
    all_locs = [d.get("location", "").strip() for d in domains if d.get("location")]
    geo_domains = [d for d in domains if d.get("role") in ("geo_hub", "city_hub")]
    if all_locs and not geo_domains:
        gaps.append({"type": "missing_city_hub", "item": all_locs[0], "label": "GEO/City hub eksik"})

    clusters = {d.get("cluster") for d in domains if d.get("cluster")}
    entity_domains = [d for d in domains if d.get("role") == "entity_hub"]
    if clusters and not entity_domains:
        gaps.append({"type": "missing_entity_cluster", "item": list(clusters)[0]})

    for d in domains:
        if d["content_count"] < 2:
            gaps.append({"type": "thin_content", "domain": d["domain"], "count": d["content_count"]})
        if d["refresh_candidates"] > 0:
            gaps.append({"type": "refresh_needed", "domain": d["domain"], "count": d["refresh_candidates"]})
        if d["quality_gate_status"] == "fail":
            gaps.append({"type": "quality_gate_fail", "domain": d["domain"]})

    return {
        "success": True,
        "gaps": gaps,
        "gap_count": len(gaps),
        "locations_covered": sorted(locations),
        "keywords_tracked": len(keywords),
    }


def rank_overview(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    by_domain: list[dict] = []
    all_kws: list[dict] = []
    clusters: dict[str, int] = {}

    for d in domains:
        kws = d.get("ranking_keywords") or []
        traffic_score = sum(max(0, 100 - (k.get("last_position") or 100)) for k in kws)
        by_domain.append({
            "domain": d["domain"],
            "role": d["role"],
            "project_id": d.get("project_id"),
            "keyword_count": len(kws),
            "traffic_score": traffic_score,
            "avg_decay": round(
                sum(k.get("decay_score", 0) for k in kws) / max(len(kws), 1), 1
            ) if kws else 0,
            "indexed_pages": d.get("indexed_pages", 0),
            "keywords": kws[:10],
        })
        cl = d.get("cluster") or d.get("seed_keyword") or "general"
        clusters[cl] = clusters.get(cl, 0) + traffic_score
        for kw in kws:
            all_kws.append({
                "keyword": kw.get("keyword"),
                "domain": d["domain"],
                "position": kw.get("last_position"),
                "score": max(0, 100 - (kw.get("last_position") or 100)),
            })

    by_domain.sort(key=lambda x: x.get("traffic_score", 0), reverse=True)
    top_keywords = sorted(all_kws, key=lambda x: x.get("score", 0), reverse=True)[:20]
    top_clusters = sorted(
        [{"cluster": k, "traffic_score": v} for k, v in clusters.items()],
        key=lambda x: x["traffic_score"], reverse=True,
    )[:15]

    return {
        "success": True,
        "domains": by_domain,
        "top_domains": by_domain[:10],
        "top_keywords": top_keywords,
        "top_clusters": top_clusters,
        "top_pages": [
            {"domain": d["domain"], "indexed_pages": d.get("indexed_pages", 0), "keywords": len(d.get("ranking_keywords") or [])}
            for d in by_domain[:10]
        ],
    }


def refresh_overview(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    stale = []
    authority_declining = []
    for d in domains:
        kws = d.get("ranking_keywords") or []
        decaying = any((k.get("decay_score") or 0) >= 30 for k in kws)
        if d["refresh_candidates"] > 0 or d["content_count"] == 0:
            stale.append({
                "domain": d["domain"],
                "project_id": d.get("project_id"),
                "refresh_candidates": d["refresh_candidates"],
                "last_content_date": d.get("last_content_date"),
                "last_refresh_date": d.get("last_refresh_date"),
                "no_content": d["content_count"] == 0,
            })
        if decaying or d.get("quality_gate_status") == "warning":
            authority_declining.append({
                "domain": d["domain"],
                "authority_score": d.get("authority_score"),
                "decaying_keywords": sum(1 for k in kws if (k.get("decay_score") or 0) >= 30),
            })
    return {
        "success": True,
        "stale_domains": stale,
        "authority_declining": authority_declining,
        "count": len(stale),
    }


def publisher_overview(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    backlog = [
        {
            "domain": d["domain"],
            "publisher_queue": d["publisher_queue"],
            "astro_queue": d["astro_queue"],
            "deploy_pending": d.get("deploy_pending", False),
            "total_queue": d["publisher_queue"] + d["astro_queue"],
        }
        for d in domains
        if d["publisher_queue"] + d["astro_queue"] > 0 or d.get("deploy_pending")
    ]
    try:
        from app.moduller.publisher_hub import _load_state as ph_state
        dispatch = (ph_state().get("network_dispatch") or [])[-50:]
    except Exception:
        dispatch = []
    return {"success": True, "backlog": backlog, "network_dispatch": dispatch}


def publisher_channels_view(network_id: str = "") -> dict[str, Any]:
    """Domain × kanal matrisi — Publisher Hub published verisi."""
    domains = _iter_all_domains(network_id)
    channel_stats: dict[str, dict[str, Any]] = {ch: {"domains": [], "count": 0} for ch in PUBLISHER_CHANNEL_IDS}
    by_domain: list[dict] = []

    for d in domains:
        chs = d.get("publish_channels") or []
        by_domain.append({
            "domain": d["domain"],
            "role": d["role"],
            "channels": chs,
            "publisher_queue": d.get("publisher_queue", 0),
        })
        for ch in chs:
            if ch in channel_stats:
                channel_stats[ch]["domains"].append(d["domain"])
                channel_stats[ch]["count"] += 1

    return {
        "success": True,
        "by_domain": by_domain,
        "by_channel": [
            {"channel": ch, "domain_count": meta["count"], "domains": meta["domains"][:20]}
            for ch, meta in channel_stats.items() if meta["count"] > 0
        ],
        "channels_tracked": list(PUBLISHER_CHANNEL_IDS),
    }


def quality_overview(network_id: str = "") -> dict[str, Any]:
    domains = _iter_all_domains(network_id)
    fail = [d for d in domains if d.get("quality_gate_status") == "fail"]
    warn = [d for d in domains if d.get("quality_gate_status") == "warning"]
    deploy_blocked = [d for d in domains if d.get("deploy_blocked")]
    return {
        "success": True,
        "fail_domains": [{"domain": d["domain"], "role": d["role"], "quality_score": d.get("quality_score")} for d in fail],
        "warning_domains": [{"domain": d["domain"], "role": d["role"], "quality_score": d.get("quality_score")} for d in warn],
        "deploy_blocked": [{"domain": d["domain"], "project_id": d.get("project_id")} for d in deploy_blocked],
        "pass_count": sum(1 for d in domains if d.get("quality_gate_status") == "pass"),
    }


def discover_network(network_id: str = "") -> dict[str, Any]:
    """Tüm modüllerden network state oluştur ve cache'e yaz."""
    integrations = _integration_status()
    failed = [k for k, v in integrations.items() if not v.get("ok")]
    domains = _iter_all_domains(network_id)
    networks: list[dict] = []
    try:
        from app.moduller.network_replicator import list_networks
        for net in (list_networks().get("networks") or []):
            nid = net.get("network_id", "")
            if network_id and nid != network_id:
                continue
            net_domains = [d for d in domains if d.get("network_id") == nid]
            networks.append({
                "network_id": nid,
                "name": net.get("name", ""),
                "main_domain": net.get("main_domain", ""),
                "domain_count": len(net_domains),
                "domains": [d["domain"] for d in net_domains],
            })
    except Exception as exc:
        return {"success": False, "error": f"Network Replicator okunamadı: {exc}"}

    if not networks and domains:
        networks.append({
            "network_id": "astro-fallback",
            "name": "Astro Factory Projects",
            "main_domain": domains[0]["domain"] if domains else "",
            "domain_count": len(domains),
            "domains": [d["domain"] for d in domains],
        })

    cache = {
        "discovered_at": _now(),
        "network_id": network_id,
        "networks": networks,
        "domain_count": len(domains),
        "integrations": integrations,
        "integration_errors": failed,
    }
    st = _load_state()
    st["network_cache"] = cache
    st["last_sync_at"] = _now()
    _save_state(st)
    return {"success": True, **cache}


def list_networks_api() -> dict[str, Any]:
    discover_network()
    cache = _load_state().get("network_cache") or {}
    return {
        "success": True,
        "networks": cache.get("networks") or [],
        "count": len(cache.get("networks") or []),
        "last_discovered_at": cache.get("discovered_at", ""),
        "integration_errors": cache.get("integration_errors") or [],
    }


def get_network(network_id: str) -> dict[str, Any]:
    if not network_id:
        return {"success": False, "error": "network_id gerekli"}
    if network_id == "astro-fallback":
        domains = [d for d in _iter_all_domains() if not d.get("network_id")]
    else:
        domains = _iter_all_domains(network_id)
    if not domains:
        return {"success": False, "error": f"Network bulunamadı: {network_id}"}
    grouped: dict[str, list] = {g: [] for g in NETWORK_GROUPS}
    for d in domains:
        grouped.setdefault(d["network_group"], []).append(d)
    nh = network_health(network_id)
    return {
        "success": True,
        "network_id": network_id,
        "network_name": domains[0].get("network_name", ""),
        "main_domain": next((d["domain"] for d in domains if d["role"] == "money_site"), ""),
        "domain_count": len(domains),
        "domains": domains,
        "grouped": grouped,
        "health": nh if nh.get("success") else None,
    }


def get_domain(domain: str) -> dict[str, Any]:
    host = _host(domain)
    if not host:
        return {"success": False, "error": "domain gerekli"}
    for d in _iter_all_domains():
        if d["domain"] == host:
            return {
                "success": True,
                "profile": d,
                "link_plans": [
                    p for p in (_load_state().get("link_plans") or [])
                    if p.get("from_domain") == host or p.get("to_domain") == host
                ][:50],
            }
    return {"success": False, "error": f"Domain bulunamadı: {host}"}


def dashboard(network_id: str = "") -> dict[str, Any]:
    discover_network(network_id)
    domains = _iter_all_domains(network_id)
    nh = network_health(network_id) if domains else {"success": False}
    auth = authority_map(network_id) if domains else {"success": False}
    kw = keyword_distribution(network_id) if domains else {"success": False}
    gaps = network_gaps(network_id) if domains else {"success": False}
    pub = publisher_channels_view(network_id) if domains else {"success": False}
    rank = rank_overview(network_id) if domains else {"success": False}
    integrations = _integration_status()
    return {
        "success": True,
        "domain_count": len(domains),
        "overall_network_score": nh.get("overall_network_score") if nh.get("success") else None,
        "health_scores": nh.get("scores") if nh.get("success") else {},
        "authority_summary": auth.get("summary") if auth.get("success") else {},
        "cannibalization_risks": kw.get("risk_count", 0) if kw.get("success") else 0,
        "gap_count": gaps.get("gap_count", 0) if gaps.get("success") else 0,
        "top_domains": rank.get("top_domains", [])[:5] if rank.get("success") else [],
        "publisher_channels": pub.get("by_channel", []) if pub.get("success") else [],
        "integrations": integrations,
        "integration_errors": [k for k, v in integrations.items() if not v.get("ok")],
        "last_sync_at": _load_state().get("last_sync_at", ""),
    }


def growth_opportunities(network_id: str = "") -> dict[str, Any]:
    gaps = network_gaps(network_id)
    auth = authority_map(network_id)
    if not gaps.get("success"):
        return gaps
    opportunities: list[dict] = []
    for g in gaps.get("gaps") or []:
        if g["type"].startswith("missing_"):
            opportunities.append({
                "type": "fill_gap",
                "priority": "high",
                "item": g.get("item") or g.get("label"),
                "reason": g["type"],
            })
    for d in (auth.get("no_content") or []):
        opportunities.append({
            "type": "create_content",
            "priority": "high",
            "domain": d["domain"],
            "reason": "no_content",
        })
    for d in (auth.get("supporting_money_site") or []):
        opportunities.append({
            "type": "strengthen_support",
            "priority": "medium",
            "domain": d["domain"],
            "supports": d.get("supports"),
            "reason": "money_site_support",
        })
    return {"success": True, "opportunities": opportunities, "count": len(opportunities)}


def suggest_role(domain: str, index: int = 0) -> dict[str, Any]:
    from app.moduller.network_replicator import _assign_role_for_domain
    role = _assign_role_for_domain(domain, index)
    return {
        "success": True,
        "domain": _host(domain),
        "suggested_role": role,
        "role_label": ROLE_LABELS.get(role, role),
        "network_group": _group_for_role(role),
    }


def sync_network(network_id: str = "") -> dict[str, Any]:
    """Tüm analizleri çalıştır ve state güncelle."""
    job_id = f"sne-{uuid.uuid4().hex[:10]}"
    results = {
        "discovery": discover_network(network_id),
        "domains": list_domains(network_id),
        "authority": authority_map(network_id),
        "keywords": keyword_distribution(network_id),
        "health": network_health(network_id),
        "gaps": network_gaps(network_id),
        "links": link_strategy(network_id),
        "rank": rank_overview(network_id),
        "refresh": refresh_overview(network_id),
        "publisher": publisher_overview(network_id),
        "publisher_channels": publisher_channels_view(network_id),
        "quality": quality_overview(network_id),
        "opportunities": growth_opportunities(network_id),
    }
    st = _load_state()
    st["jobs"][job_id] = {
        "job_id": job_id,
        "type": "sync",
        "network_id": network_id,
        "status": "completed",
        "finished_at": _now(),
        "summary": {
            "domains": results["domains"].get("count", 0),
            "network_score": results["health"].get("network_score"),
            "gaps": results["gaps"].get("gap_count", 0),
            "link_plans": results["links"].get("count", 0),
            "cannibalization": results["keywords"].get("risk_count", 0),
        },
    }
    st["last_sync_at"] = _now()
    _save_state(st)
    return {"success": True, "job_id": job_id, "results": results}


def export_report(report_type: str = "overview", network_id: str = "") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "overview": lambda: dashboard(network_id),
        "authority": lambda: authority_map(network_id),
        "links": lambda: link_strategy(network_id),
        "keywords": lambda: keyword_distribution(network_id),
        "publisher": lambda: publisher_channels_view(network_id),
        "geo": lambda: network_gaps(network_id),
        "entity": lambda: network_health(network_id),
        "risk": lambda: keyword_distribution(network_id),
        "growth": lambda: growth_opportunities(network_id),
        "health": lambda: network_health(network_id),
    }
    fn = generators.get(report_type, generators["overview"])
    payload = fn()
    path = REPORTS_DIR / f"support-network-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def health() -> dict[str, Any]:
    st = _load_state()
    domains = _iter_all_domains()
    nh = network_health() if domains else {"success": False}
    integrations = _integration_status()
    errors = [
        {"module": k, "error": v.get("error") or "provider not ready"}
        for k, v in integrations.items() if not v.get("ok")
    ]
    return {
        "success": True,
        "module": "support_network_engine",
        "enabled": get_settings().get("enabled", True),
        "domain_count": len(domains),
        "network_groups": list(NETWORK_GROUPS.keys()),
        "roles": list(BASE_ROLES),
        "last_sync_at": st.get("last_sync_at", ""),
        "integrations": integrations,
        "integration_errors": errors,
        "dashboard": {
            "domains": len(domains),
            "network_score": nh.get("overall_network_score") if nh.get("success") else None,
            "link_plans": len(st.get("link_plans") or []),
            "keyword_registry_size": len(st.get("keyword_registry") or {}),
            "jobs": len(st.get("jobs") or {}),
        },
    }
