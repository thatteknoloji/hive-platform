"""Network Replicator & Blueprint Engine — multi-domain Astro network clone/deploy."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.moduller.storyforge_categories import _slugify

logger = logging.getLogger("hive.network_replicator")

STATE_FILE = Path(__file__).resolve().parent.parent / "network_replicator_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "reports"

MIN_DEPLOY_SCORE = 85

DOMAIN_ROLES = {
    "brand_hub": {"label": "Ana marka", "niche": "Marka Hub", "focus": "brand"},
    "faq_hub": {"label": "SSS merkezi", "niche": "SSS Hub", "focus": "faq"},
    "geo_hub": {"label": "GEO landing", "niche": "GEO Hub", "focus": "geo"},
    "entity_hub": {"label": "Entity rehber", "niche": "Entity Hub", "focus": "entity"},
    "blog_hub": {"label": "Blog ağı", "niche": "Blog Hub", "focus": "blog"},
    "support_hub": {"label": "Destek içerik", "niche": "Support Hub", "focus": "support"},
    "city_hub": {"label": "Şehir ağı", "niche": "City Hub", "focus": "geo"},
    "topic_hub": {"label": "Kategori ağı", "niche": "Topic Hub", "focus": "blog"},
}

REWRITE_MODES = {
    "light": {"instruction": "Metni yaklaşık %20 oranında yeniden yaz, anlamı koru.", "min_change": 0.15},
    "balanced": {"instruction": "Metni yaklaşık %50 oranında yeniden yaz, farklı cümle yapıları kullan.", "min_change": 0.35},
    "heavy": {"instruction": "Metni yaklaşık %80 oranında yeniden yaz, tamamen farklı anlatım.", "min_change": 0.55},
    "full_rebuild": {"instruction": "Metni sıfırdan özgün üret, sadece konu aynı kalsın.", "min_change": 0.75},
}

RETHEME_STYLES = {
    "modern": {"accent": "6366f1", "font": "system-ui", "layout": "grid"},
    "magazine": {"accent": "dc2626", "font": "Georgia, serif", "layout": "magazine"},
    "directory": {"accent": "059669", "font": "Inter, sans-serif", "layout": "cards"},
    "corporate": {"accent": "1e40af", "font": "Helvetica, Arial", "layout": "corporate"},
    "travel": {"accent": "0891b2", "font": "Nunito, sans-serif", "layout": "hero-grid"},
    "nightlife": {"accent": "a855f7", "font": "Montserrat, sans-serif", "layout": "dark-cards"},
    "tourism": {"accent": "f59e0b", "font": "Poppins, sans-serif", "layout": "wide"},
    "minimal": {"accent": "374151", "font": "Helvetica, sans-serif", "layout": "minimal"},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("networks", {})
                data.setdefault("blueprints", {})
                data.setdefault("jobs", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"networks": {}, "blueprints": {}, "jobs": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _network_id() -> str:
    return f"net-{uuid.uuid4().hex[:10]}"


def _job_id() -> str:
    return f"nr-{uuid.uuid4().hex[:10]}"


def _domain_host(domain: str) -> str:
    d = (domain or "").strip()
    if d.startswith("http"):
        return urlparse(d).netloc or d
    return d.split("/")[0]


def _assign_role_for_domain(domain: str, index: int) -> str:
    host = _domain_host(domain).lower()
    if host.endswith(".info"):
        return "faq_hub"
    if host.endswith(".org"):
        return "entity_hub"
    if host.endswith(".net"):
        return "blog_hub"
    if host.endswith(".blog"):
        return "blog_hub"
    if host.endswith(".online"):
        return "support_hub"
    roles = list(DOMAIN_ROLES.keys())
    return roles[index % len(roles)]


def health() -> dict[str, Any]:
    st = _load_state()
    cf_ok = False
    try:
        from app.moduller.cloudflare_pages_deploy import cf_status
        cf_ok = bool(cf_status().get("configured"))
    except Exception:
        pass
    return {
        "success": True,
        "module": "network_replicator",
        "network_count": len(st.get("networks") or {}),
        "cloudflare_configured": cf_ok,
        "min_deploy_score": MIN_DEPLOY_SCORE,
        "domain_roles": list(DOMAIN_ROLES.keys()),
        "rewrite_modes": list(REWRITE_MODES.keys()),
        "retheme_styles": list(RETHEME_STYLES.keys()),
    }


def create_network(main_domain: str, name: str = "") -> dict[str, Any]:
    host = _domain_host(main_domain)
    if not host:
        return {"success": False, "error": "main_domain gerekli"}
    nid = _network_id()
    network = {
        "network_id": nid,
        "name": name or f"{host} Network",
        "main_domain": host,
        "domains": [{"domain": host, "role": "brand_hub", "project_id": "", "status": "primary"}],
        "projects": [],
        "roles": ["brand_hub"],
        "created_at": _now(),
        "updated_at": _now(),
    }
    st = _load_state()
    st["networks"][nid] = network
    _save_state(st)
    return {"success": True, "network": network}


def add_domain(network_id: str, domain: str, role: str = "", project_id: str = "") -> dict[str, Any]:
    st = _load_state()
    network = st["networks"].get(network_id)
    if not network:
        return {"success": False, "error": "Network bulunamadı"}
    host = _domain_host(domain)
    r = role if role in DOMAIN_ROLES else _assign_role_for_domain(host, len(network["domains"]))
    entry = {
        "domain": host,
        "role": r,
        "project_id": project_id,
        "status": "pending",
        "build_status": "pending",
        "deploy_status": "pending",
        "quality_score": 0,
        "last_publish": "",
        "index_status": "unknown",
        "rank_status": "unknown",
    }
    network["domains"].append(entry)
    if r not in network["roles"]:
        network["roles"].append(r)
    network["updated_at"] = _now()
    st["networks"][network_id] = network
    _save_state(st)
    return {"success": True, "network": network, "domain_entry": entry}


def _domain_research_scores(domain_entry: dict[str, Any]) -> dict[str, int]:
    """SEOctopus / Agentic SEO inspired domain health signals."""
    pid = domain_entry.get("project_id") or ""
    scores = {
        "authority_score": int(domain_entry.get("quality_score") or 0),
        "content_freshness": 45,
        "entity_density": 0,
        "ai_visibility": 0,
    }
    if domain_entry.get("last_publish"):
        scores["content_freshness"] = 78
    if domain_entry.get("build_status") == "built":
        scores["content_freshness"] = min(100, scores["content_freshness"] + 12)
    if not pid:
        return scores
    try:
        from app.moduller.entity_geo_graph import get_project_scores
        gs = get_project_scores(pid)
        if gs.get("success"):
            scores["entity_density"] = int(gs.get("entity_strength_score") or 0)
            scores["authority_score"] = max(
                scores["authority_score"],
                int(gs.get("topic_authority_score") or 0),
            )
    except Exception:
        pass
    try:
        gate_path = Path(__file__).resolve().parent.parent / "seo_quality_gate_state.json"
        if gate_path.exists():
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            for report in (gate.get("reports") or {}).values():
                if report.get("project_id") != pid:
                    continue
                scores["ai_visibility"] = int(
                    report.get("llm_visibility_score")
                    or report.get("overview_probability_score")
                    or report.get("aeo_score")
                    or 0,
                )
                scores["authority_score"] = max(
                    scores["authority_score"],
                    int(report.get("overall_score") or 0),
                )
                break
    except Exception:
        pass
    return scores


def _enrich_network_domains(network: dict[str, Any]) -> dict[str, Any]:
    for d in network.get("domains") or []:
        d.update(_domain_research_scores(d))
    return network


def list_networks() -> dict[str, Any]:
    networks = [_enrich_network_domains(dict(n)) for n in (_load_state().get("networks") or {}).values()]
    networks.sort(key=lambda n: n.get("created_at", ""), reverse=True)
    return {"success": True, "networks": networks, "count": len(networks)}


def get_network(network_id: str) -> dict[str, Any]:
    network = (_load_state().get("networks") or {}).get(network_id)
    if not network:
        return {"success": False, "error": "Network bulunamadı"}
    return {"success": True, "network": _enrich_network_domains(dict(network))}


def clone_site(
    source_project_id: str,
    target_domain: str,
    target_site_name: str = "",
    *,
    network_id: str = "",
    role: str = "",
    main_site_url: str = "https://www.balkutusu.com",
) -> dict[str, Any]:
    from app.moduller.site_replicator import clone_owned_site
    host = _domain_host(target_domain)
    name = target_site_name or host.replace(".", " ").title()
    result = clone_owned_site(
        source_project_id, host, name,
        content_strategy="keep",
        theme_variation=False,
        auto_build=False,
        auto_deploy=False,
        main_site_url=main_site_url,
    )
    if not result.get("success"):
        return result

    pid = result.get("summary", {}).get("target_project_id", "")
    _update_domain_meta(pid, host, name, main_site_url)

    if network_id:
        add_domain(network_id, host, role=role or _assign_role_for_domain(host, 0), project_id=pid)
        st = _load_state()
        net = st["networks"].get(network_id, {})
        if pid and pid not in net.get("projects", []):
            net.setdefault("projects", []).append(pid)
            st["networks"][network_id] = net
            _save_state(st)

    return {**result, "target_project_id": pid, "target_domain": host}


def _update_domain_meta(project_id: str, domain: str, site_name: str, main_site_url: str) -> None:
    from app.moduller.site_replicator import _update_domain_meta as sr_update
    from app.moduller.astro_factory import _get_project, _project_path
    project = _get_project(project_id)
    sr_update(_project_path(project["slug"]), f"https://{domain}" if not domain.startswith("http") else domain, site_name, main_site_url)


def rewrite_content(project_id: str, mode: str = "balanced") -> dict[str, Any]:
    if mode not in REWRITE_MODES:
        return {"success": False, "error": f"Geçersiz mode: {mode}"}
    from app.moduller.astro_factory import _get_project, _project_path
    from app.moduller.site_replicator import _rewrite_data_files, _rewrite_text

    cfg = REWRITE_MODES[mode]
    project = _get_project(project_id)
    path = _project_path(project["slug"])

    if mode == "full_rebuild":
        count = _rewrite_data_files(path, project.get("site_name", ""), seed=f"rebuild-{project_id}")
    else:
        import app.moduller.site_replicator as sr

        def patched_rewrite(text: str, context: str, seed: str = "") -> str:
            prompt = f"{cfg['instruction']}\nBağlam: {context}\nSeed: {seed}\nMetin:\n{text[:3500]}"
            try:
                from app.moduller import llm_router
                out, _ = llm_router.generate(prompt, max_tokens=2500, min_length=80)
                return out.strip() if out else text
            except Exception:
                return text

        original = sr._rewrite_text
        sr._rewrite_text = patched_rewrite
        try:
            count = _rewrite_data_files(path, project.get("site_name", ""), seed=f"{mode}-{project_id}")
        finally:
            sr._rewrite_text = original

    gate = _quality_gate_project(project_id)
    return {"success": True, "project_id": project_id, "mode": mode, "rewritten_fields": count, "quality_gate": gate}


def retheme_site(project_id: str, style: str = "modern") -> dict[str, Any]:
    if style not in RETHEME_STYLES:
        return {"success": False, "error": f"Geçersiz style: {style}"}
    from app.moduller.astro_factory import _get_project, _project_path
    cfg = RETHEME_STYLES[style]
    project = _get_project(project_id)
    path = _project_path(project["slug"])

    css_vars = (
        f":root {{ --accent: #{cfg['accent']}; --nr-theme: {style}; "
        f"--nr-font: {cfg['font']}; --nr-layout: {cfg['layout']}; }}\n"
    )
    for css in list(path.glob("src/**/*.css"))[:8]:
        try:
            content = css.read_text(encoding="utf-8")
            if "--nr-theme:" not in content:
                content = css_vars + content
            else:
                import re
                content = re.sub(r"--accent:\s*#[0-9a-fA-F]+", f"--accent: #{cfg['accent']}", content)
                content = re.sub(r"--nr-theme:\s*\w+", f"--nr-theme: {style}", content)
            css.write_text(content, encoding="utf-8")
        except OSError:
            pass

    layout_note = path / "src" / "data" / "theme.json"
    layout_note.parent.mkdir(parents=True, exist_ok=True)
    layout_note.write_text(json.dumps({"style": style, **cfg}, ensure_ascii=False, indent=2), encoding="utf-8")

    from app.moduller.astro_factory import _update_project
    _update_project(project_id, theme=style, updated_at=_now())
    return {"success": True, "project_id": project_id, "style": style, "theme": cfg}


def clone_to_many(
    source_project_id: str,
    domains: list[str],
    *,
    network_id: str = "",
    rewrite_mode: str = "balanced",
    retheme_style: str = "modern",
    auto_build: bool = True,
    auto_deploy: bool = False,
    main_site_url: str = "https://www.balkutusu.com",
) -> dict[str, Any]:
    jid = _job_id()
    results: list[dict[str, Any]] = []

    for i, domain in enumerate(domains):
        host = _domain_host(domain)
        role = _assign_role_for_domain(host, i)
        clone = clone_site(source_project_id, host, host.replace(".", " ").title(), network_id=network_id, role=role, main_site_url=main_site_url)
        if not clone.get("success"):
            results.append({"domain": host, "success": False, "error": clone.get("error")})
            continue
        pid = clone.get("target_project_id", "")
        rw = rewrite_content(pid, rewrite_mode)
        rt = retheme_site(pid, retheme_style)
        built = deployed = False
        gate = rw.get("quality_gate") or {}

        if auto_build and gate.get("deploy_allowed", False):
            from app.moduller.astro_factory import build_astro_project, generate_pages
            generate_pages(pid)
            build_res = build_astro_project(pid)
            built = bool(build_res.get("success"))

        if auto_deploy and built:
            from app.moduller.cloudflare_pages_deploy import deploy_to_cloudflare
            dep = deploy_to_cloudflare(pid)
            deployed = bool(dep.get("success"))
            if deployed:
                _rank_notify(pid, host)

        results.append({
            "domain": host, "role": role, "project_id": pid,
            "success": True, "rewrite": rw.get("rewritten_fields", 0),
            "retheme": rt.get("style"), "built": built, "deployed": deployed,
            "quality_score": gate.get("passed_count", 0),
        })

    job = {"job_id": jid, "type": "clone_to_many", "results": results, "finished_at": _now()}
    st = _load_state()
    st["jobs"][jid] = job
    _save_state(st)
    return {"success": True, "job_id": jid, "cloned": sum(1 for r in results if r.get("success")), "results": results}


def analyze_blueprint(url: str) -> dict[str, Any]:
    from app.moduller.site_replicator import analyze_competitor_blueprint
    blocked_check = __import__("app.moduller.site_replicator", fromlist=["_is_blocked_url"])._is_blocked_url(url)
    if blocked_check:
        return {"success": False, "error": blocked_check}

    base = analyze_competitor_blueprint(url)
    if not base.get("success"):
        return base

    bp = base.get("blueprint") or {}
    enriched = {
        "blueprint": bp,
        "category_tree": bp.get("category_structure") or [],
        "content_clusters": bp.get("content_gaps") or [],
        "internal_link_patterns": bp.get("internal_link_patterns") or [],
        "schema_patterns": bp.get("schema_patterns") or [],
        "entity_patterns": [h.get("text") for h in (bp.get("heading_structure") or []) if "entity" in (h.get("text") or "").lower()],
        "geo_patterns": [p for p in (bp.get("url_patterns") or []) if any(x in p.lower() for x in ("geo", "sehir", "city", "kusadasi", "location"))],
        "content_gaps": bp.get("content_gaps") or [],
        "compliance": base.get("compliance"),
    }

    bp_id = base.get("blueprint_id", f"bp-{uuid.uuid4().hex[:8]}")
    st = _load_state()
    st["blueprints"][bp_id] = {"url": url, **enriched, "created_at": _now()}
    _save_state(st)
    return {"success": True, "blueprint_id": bp_id, **enriched}


def generate_variant(
    blueprint_id: str,
    target_domain: str,
    site_name: str,
    *,
    role: str = "brand_hub",
    network_id: str = "",
    main_site_url: str = "https://www.balkutusu.com",
    auto_build: bool = False,
) -> dict[str, Any]:
    st = _load_state()
    bp_entry = st.get("blueprints", {}).get(blueprint_id)
    if bp_entry:
        from app.moduller.astro_factory import create_project, generate_pages, build_astro_project, _get_project, _project_path, _write_project_data
        from app.moduller.site_replicator import _rewrite_text, _apply_theme_variation, _safe_project_path, _run_quality_gate_on_project

        host = _domain_host(target_domain)
        slug = _slugify(site_name or host)
        domain = f"https://{host}" if not host.startswith("http") else host
        proj = create_project({
            "site_name": site_name or host,
            "slug": slug,
            "domain": domain,
            "seed_keyword": site_name,
            "main_site_url": main_site_url,
            "niche": DOMAIN_ROLES.get(role, {}).get("niche", "Network Variant"),
        })
        if not proj.get("success"):
            return proj
        pid = proj["project"]["id"]
        project = _get_project(pid)
        path = _project_path(project["slug"])
        clusters = bp_entry.get("content_clusters") or bp_entry.get("category_tree") or []
        geo_pages = []
        for i, cat in enumerate(clusters[:6]):
            title = f"{cat} — {site_name}"
            html = _rewrite_text(f"<h1>{title}</h1><p>Özgün varyant — blueprint referans, içerik kopyası yok.</p>", title, seed=f"nv-{i}")
            geo_pages.append({"slug": _slugify(f"{cat}-{slug}")[:50], "title": title, "content_html": html, "keyword": str(cat)})
        home_html = _rewrite_text(f"<h1>{site_name}</h1><p>Network Replicator özgün sürüm.</p>", site_name, seed="home")
        _write_project_data(path, project, home_page={"title": site_name, "description": site_name, "content_html": home_html}, geo_pages=geo_pages, faq_pages=[], blog_pages=[])
        _apply_theme_variation(path)
        gate = _run_quality_gate_on_project(path, min_score=MIN_DEPLOY_SCORE)
        generate_pages(pid)
        built = False
        if auto_build and gate.get("deploy_allowed"):
            built = bool(build_astro_project(pid).get("success"))
        if network_id:
            add_domain(network_id, host, role=role, project_id=pid)
        return {"success": True, "project_id": pid, "quality_gate": gate, "built": built, "compliance": {"copied_content": False, "copied_assets": False}}
    from app.moduller.site_replicator import generate_original_template
    result = generate_original_template(blueprint_id, target_domain, site_name, main_site_url, auto_build=auto_build)
    if not result.get("success"):
        return result
    pid = result.get("summary", {}).get("project_id", "")
    if pid:
        retheme_site(pid, "modern" if role == "brand_hub" else "directory")
        if network_id:
            add_domain(network_id, target_domain, role=role, project_id=pid)
    return result


def _quality_gate_project(project_id: str) -> dict[str, Any]:
    from app.moduller.site_replicator import _run_quality_gate_on_project, _get_source_project
    _, path = _get_source_project(project_id)
    gate = _run_quality_gate_on_project(path, min_score=MIN_DEPLOY_SCORE)
    return gate


def build_network(network_id: str) -> dict[str, Any]:
    network = get_network(network_id)
    if not network.get("success"):
        return network
    from app.moduller.astro_factory import build_astro_project, generate_pages
    results: list[dict[str, Any]] = []
    for d in network["network"].get("domains") or []:
        pid = d.get("project_id")
        if not pid:
            continue
        gate = _quality_gate_project(pid)
        if not gate.get("deploy_allowed"):
            results.append({"domain": d["domain"], "success": False, "error": "Quality Gate fail", "gate": gate})
            d["build_status"] = "blocked"
            continue
        generate_pages(pid)
        res = build_astro_project(pid)
        ok = bool(res.get("success"))
        d["build_status"] = "built" if ok else "failed"
        d["quality_score"] = gate.get("passed_count", 0)
        results.append({"domain": d["domain"], "project_id": pid, "success": ok})
    st = _load_state()
    st["networks"][network_id] = network["network"]
    _save_state(st)
    return {"success": True, "network_id": network_id, "results": results}


def deploy_network(network_id: str) -> dict[str, Any]:
    network = get_network(network_id)
    if not network.get("success"):
        return network
    from app.moduller.cloudflare_pages_deploy import deploy_to_cloudflare
    results: list[dict[str, Any]] = []
    for d in network["network"].get("domains") or []:
        pid = d.get("project_id")
        if not pid or d.get("build_status") != "built":
            continue
        gate = _quality_gate_project(pid)
        if not gate.get("deploy_allowed"):
            results.append({"domain": d["domain"], "success": False, "error": "Quality Gate < 85"})
            continue
        dep = deploy_to_cloudflare(pid)
        ok = bool(dep.get("success"))
        d["deploy_status"] = "deployed" if ok else "failed"
        d["last_publish"] = _now() if ok else d.get("last_publish", "")
        if ok:
            _rank_notify(pid, d["domain"])
        results.append({"domain": d["domain"], "success": ok, "url": dep.get("url") or dep.get("deployment_url")})
    st = _load_state()
    st["networks"][network_id] = network["network"]
    _save_state(st)
    return {"success": True, "network_id": network_id, "deployed": sum(1 for r in results if r.get("success")), "results": results}


def _rank_notify(project_id: str, domain: str) -> None:
    try:
        from app.moduller.rank_index_watcher import register_project, track_keyword
        from app.moduller.astro_factory import _get_project
        project = _get_project(project_id)
        host = _domain_host(domain)
        register_project(project_id, host, source="network_replicator")
        kw = (project.get("seed_keyword") or project.get("site_name") or host).lower()
        track_keyword(kw, host, save=True, project_id=project_id)
    except Exception as exc:
        logger.warning("Rank watcher: %s", exc)


def export_report(network_id: str = "", job_id: str = "") -> dict[str, Any]:
    st = _load_state()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if network_id:
        net = st["networks"].get(network_id)
        if not net:
            return {"success": False, "error": "Network bulunamadı"}
        path = REPORTS_DIR / f"network-replicator-{network_id}.json"
        path.write_text(json.dumps(net, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "report_path": str(path), "report": net}
    if job_id:
        job = st["jobs"].get(job_id)
        if not job:
            return {"success": False, "error": "Job bulunamadı"}
        path = REPORTS_DIR / f"network-replicator-job-{job_id}.json"
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "report_path": str(path), "report": job}
    return {"success": False, "error": "network_id veya job_id gerekli"}


network_replicator = type("NetworkReplicator", (), {
    "health": staticmethod(health),
    "create_network": staticmethod(create_network),
    "add_domain": staticmethod(add_domain),
    "list_networks": staticmethod(list_networks),
    "get_network": staticmethod(get_network),
    "clone_site": staticmethod(clone_site),
    "clone_to_many": staticmethod(clone_to_many),
    "rewrite_content": staticmethod(rewrite_content),
    "retheme_site": staticmethod(retheme_site),
    "analyze_blueprint": staticmethod(analyze_blueprint),
    "generate_variant": staticmethod(generate_variant),
    "build_network": staticmethod(build_network),
    "deploy_network": staticmethod(deploy_network),
    "export_report": staticmethod(export_report),
})()
