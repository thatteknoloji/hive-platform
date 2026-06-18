"""Entity & GEO Graph — sayfa, lokasyon, kategori, keyword ve entity ilişki grafiği."""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import time
import uuid
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app import config
from app.moduller.astro_factory import GENERATED_DIR, _get_project, _project_path, _safe_slug
from app.moduller.seo_quality_gate import _collect_pages_from_data, _safe_read, _safe_read_json

logger = logging.getLogger("hive.entity_geo_graph")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = Path(__file__).resolve().parent.parent / "entity_geo_graph_state.json"
REPORTS_DIR = ROOT / "reports"
ASTRO_STATE = Path(__file__).resolve().parent.parent / "astro_factory_state.json"
SEO_GATE_STATE = Path(__file__).resolve().parent.parent / "seo_quality_gate_state.json"
RANK_STATE = Path(__file__).resolve().parent.parent / "rank_index_watcher_state.json"

USER_AGENT = "HIVE-EntityGeoGraph/1.0 (+https://balkutusu.com)"
URL_TIMEOUT = 15
NOMINATIM_DELAY_SEC = 1.1

NODE_TYPES = frozenset({
    "domain", "page", "keyword", "entity", "location", "category",
    "topic", "question", "schema", "source", "competitor",
})
EDGE_TYPES = frozenset({
    "targets", "mentions", "belongs_to", "located_in", "links_to",
    "supports", "answers", "competes_with", "has_schema", "needs_page", "should_link_to",
})

_BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})
_CATEGORY_WORDS = (
    "gece hayatı", "eğlence", "turizm", "otel", "restoran", "bar", "kulüp",
    "escort", "rehber", "hizmet", "plaj", "marina",
)
_SERVICE_WORDS = (
    "fiyat", "ücret", "rezervasyon", "ulaşım", "güvenlik", "sezon",
    "çalışma saatleri", "harita", "adres", "park",
)
_KNOWN_LOCATIONS = (
    "kuşadası", "güzelçamlı", "selçuk", "kadınlar denizi", "davutlar",
    "güvercinada", "long beach", "marina", "atatürk bulvarı", "yılancı burnu",
    "pamucak", "söke", "didim", "aydın", "izmir",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _max_nodes() -> int:
    try:
        return max(50, min(int(config.get("ENTITY_GRAPH_MAX_NODES") or 1000), 5000))
    except (TypeError, ValueError):
        return 1000


def _nominatim_url() -> str:
    return (config.get("NOMINATIM_URL") or "https://nominatim.openstreetmap.org").rstrip("/")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("graphs", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"graphs": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_project_id(project_id: str) -> str:
    pid = (project_id or "").strip()
    if not pid or ".." in pid or "/" in pid or "\\" in pid:
        raise ValueError("Geçersiz project_id")
    return pid


def _validate_project_path(slug: str) -> Path:
    safe = _safe_slug(slug)
    base = GENERATED_DIR.resolve()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    target = (GENERATED_DIR / safe).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal engellendi")
    return target


def _is_blocked_url(url: str) -> bool:
    try:
        parsed = urlparse((url or "").strip())
        host = (parsed.hostname or "").lower()
        if not host:
            return True
        if host in _BLOCKED_HOSTS or host.endswith(".localhost"):
            return True
        try:
            ip = ipaddress.ip_address(host)
            return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
        except ValueError:
            return False
    except Exception:
        return True


def _node_id(ntype: str, label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (label or "").lower().translate(str.maketrans("çğıöşü", "cgiosu"))).strip("-")
    return f"{ntype}:{slug or 'unknown'}"[:120]


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", (text or "").lower(), re.UNICODE)


def _strip_html(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def _parse_schema_entities(schema: Any) -> list[str]:
    entities: list[str] = []
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError:
            return entities
    if isinstance(schema, dict):
        for key in ("name", "@type", "headline", "description"):
            val = schema.get(key)
            if isinstance(val, str) and val.strip():
                entities.append(val.strip())
        for item in schema.get("mainEntity") or []:
            if isinstance(item, dict):
                q = item.get("name")
                if q:
                    entities.append(str(q).strip())
    return entities


def extract_entities_from_text(
    text: str,
    *,
    title: str = "",
    seed_keyword: str = "",
    location: str = "",
) -> dict[str, list[str]]:
    """Rule-based entity extraction — gerçek metinden."""
    combined = f"{title} {text}".strip()
    plain = _strip_html(combined)
    plain_low = plain.lower()
    tokens = _word_tokens(plain)

    locations: list[str] = []
    if location and location.lower() not in {x.lower() for x in locations}:
        locations.append(location.strip())
    for loc in _KNOWN_LOCATIONS:
        if loc in plain_low and loc.title() not in locations:
            locations.append(loc.title())

    categories = [c for c in _CATEGORY_WORDS if c in plain_low]
    services = [s for s in _SERVICE_WORDS if s in plain_low]

    proper: list[str] = []
    for m in re.finditer(r"\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+){0,3})\b", combined):
        term = m.group(1).strip()
        if len(term) > 2 and term not in proper:
            proper.append(term)

    phrases = Counter()
    words = tokens
    for n in (2, 3):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i : i + n])
            if len(phrase) > 5:
                phrases[phrase] += 1
    top_phrases = [p for p, c in phrases.most_common(15) if c >= 2]

    keywords: list[str] = []
    if seed_keyword:
        keywords.append(seed_keyword.strip())
    for var in _keyword_variations(seed_keyword, location):
        if var not in keywords:
            keywords.append(var)

    return {
        "entities": proper[:25],
        "locations": locations[:20],
        "categories": categories[:10],
        "services": services[:10],
        "phrases": top_phrases[:15],
        "keywords": keywords[:20],
    }


def _keyword_variations(seed: str, location: str) -> list[str]:
    seed = (seed or "").strip()
    loc = (location or "").strip()
    out: list[str] = []
    if seed:
        out.append(seed)
    if loc and seed:
        out.append(f"{loc} {seed}")
        out.append(f"{seed} {loc}")
    for suffix in ("rehberi", "fiyatları", "nerede", "nasıl gidilir"):
        if seed:
            out.append(f"{seed} {suffix}")
        if loc:
            out.append(f"{loc} {suffix}")
    return out[:12]


def _load_project_files(slug: str) -> dict[str, Any]:
    root = _validate_project_path(slug)
    data_dir = root / "src" / "data"
    pages_data = _safe_read_json(data_dir / "pages.json", {})
    faqs_data = _safe_read_json(data_dir / "faqs.json", [])
    blog_data = _safe_read_json(data_dir / "blog.json", [])
    sitemap = _safe_read(root / "public" / "sitemap.xml")
    dist_html_files: list[str] = []
    dist = root / "dist"
    if dist.is_dir():
        for html_path in dist.rglob("*.html"):
            if html_path.is_file():
                rel = str(html_path.relative_to(dist))
                dist_html_files.append(rel)
    return {
        "root": root,
        "pages_data": pages_data,
        "faqs_data": faqs_data if isinstance(faqs_data, list) else [],
        "blog_data": blog_data if isinstance(blog_data, list) else [],
        "sitemap": sitemap,
        "dist_html_files": dist_html_files[:200],
    }


def _seo_gate_scores(project_id: str) -> dict[str, Any]:
    if not SEO_GATE_STATE.is_file():
        return {}
    try:
        state = json.loads(SEO_GATE_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    best: dict[str, Any] = {}
    for rep in (state.get("reports") or {}).values():
        if rep.get("project_id") != project_id:
            continue
        if not best or (rep.get("overall_score") or 0) > (best.get("overall_score") or 0):
            best = rep
    if not best:
        return {}
    scores = best.get("scores") or {}
    return {
        "overall_score": best.get("overall_score", 0),
        "seo_score": scores.get("seo_score", best.get("seo_score", 0)),
        "geo_score": scores.get("geo_score", best.get("geo_score", 0)),
        "entity_score": scores.get("entity_score", best.get("entity_score", 0)),
        "authority_score": scores.get("authority_score", best.get("authority_score", 0)),
        "report_id": best.get("report_id"),
    }


def _rank_performance(project_id: str) -> dict[str, dict[str, Any]]:
    if not RANK_STATE.is_file():
        return {}
    try:
        state = json.loads(RANK_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    proj = (state.get("projects") or {}).get(project_id) or {}
    out: dict[str, dict[str, Any]] = {}
    for kw in proj.get("keywords") or []:
        if isinstance(kw, dict):
            key = (kw.get("keyword") or "").lower()
            if key:
                out[key] = kw
    for row in proj.get("performance_history") or []:
        if isinstance(row, dict):
            key = (row.get("keyword") or row.get("query") or "").lower()
            if key:
                out.setdefault(key, {}).update(row)
    return out


def _talon_keywords(seed: str, location: str, limit: int = 30) -> list[str]:
    keywords: list[str] = []
    try:
        from app.moduller.talon_orchestrator import get_sss_keyword_pool
        res = get_sss_keyword_pool(seed, location, count=limit)
        for item in res.get("keywords") or []:
            if isinstance(item, str) and item not in keywords:
                keywords.append(item)
            elif isinstance(item, dict):
                k = item.get("keyword") or item.get("kelime") or ""
                if k and k not in keywords:
                    keywords.append(k)
    except Exception as exc:
        logger.debug("Talon keyword pool: %s", exc)
    return keywords[:limit]


def _compute_node_score(
    *,
    mention_count: int,
    in_title: bool,
    in_h1: bool,
    has_schema: bool,
    internal_links: int,
    quality_score: int,
    rank_data: dict[str, Any] | None,
) -> int:
    score = min(40, mention_count * 4)
    if in_title:
        score += 15
    if in_h1:
        score += 10
    if has_schema:
        score += 10
    score += min(15, internal_links * 3)
    if quality_score:
        score += int(quality_score * 0.15)
    if rank_data:
        pos = rank_data.get("position") or rank_data.get("avg_position")
        if pos and float(pos) <= 20:
            score += 10
        clicks = rank_data.get("clicks") or 0
        if clicks and int(clicks) > 0:
            score += 5
    return max(0, min(100, score))


def build_project_graph(
    project_id: str,
    domain: str = "",
    seed_keyword: str = "",
    location: str = "",
    main_site_url: str = "https://www.balkutusu.com",
) -> dict[str, Any]:
    project_id = _safe_project_id(project_id)
    proj = _get_project(project_id)
    slug = proj.get("slug") or ""
    if not slug:
        return {"success": False, "error": "Proje slug yok"}

    seed_keyword = (seed_keyword or proj.get("seed_keyword") or "").strip()
    location = (location or proj.get("location") or "Kuşadası").strip()
    domain = (domain or proj.get("domain") or "").strip()
    main_site_url = (main_site_url or proj.get("main_site_url") or "https://www.balkutusu.com").strip()

    files = _load_project_files(slug)
    pages = _collect_pages_from_data(files["pages_data"], files["faqs_data"], files["blog_data"])
    seo_scores = _seo_gate_scores(project_id)
    rank_perf = _rank_performance(project_id)
    talon_kws = _talon_keywords(seed_keyword, location)

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    warnings: list[str] = []

    def add_node(ntype: str, label: str, score: int = 0, metadata: dict | None = None) -> str:
        if ntype not in NODE_TYPES:
            return ""
        nid = _node_id(ntype, label)
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "type": ntype,
                "label": label,
                "score": score,
                "metadata": metadata or {},
            }
        else:
            nodes[nid]["score"] = max(nodes[nid].get("score", 0), score)
            if metadata:
                nodes[nid]["metadata"].update(metadata)
        if len(nodes) >= _max_nodes():
            warnings.append(f"Maksimum node limiti ({_max_nodes()}) aşıldı — kırpıldı")
        return nid

    def add_edge(source: str, target: str, etype: str, weight: float = 1.0) -> None:
        if not source or not target or etype not in EDGE_TYPES:
            return
        edges.append({"source": source, "target": target, "type": etype, "weight": weight})

    dom_host = urlparse(domain if "://" in domain else f"https://{domain}").netloc or domain
    domain_nid = add_node("domain", dom_host or slug, 80, {"url": domain})
    seed_nid = add_node("keyword", seed_keyword, 90, {"role": "seed"})
    loc_nid = add_node("location", location, 85, {"role": "primary"})
    add_edge(seed_nid, loc_nid, "located_in", 1.0)

    entity_mentions: Counter[str] = Counter()
    page_nodes: list[str] = []

    for page in pages:
        title = (page.get("title") or "").strip() or page.get("slug") or "home"
        pslug = page.get("slug") or ""
        ptype = page.get("type", "page")
        html = page.get("content_html") or ""
        plain = _strip_html(html)
        extracted = extract_entities_from_text(
            plain, title=title, seed_keyword=seed_keyword, location=location,
        )
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.find("h1")
        h1_text = h1.get_text(strip=True) if h1 else ""
        schema = page.get("schema")
        schema_entities = _parse_schema_entities(schema)
        kw = (page.get("keyword") or seed_keyword).strip()
        rank_data = rank_perf.get(kw.lower()) if kw else None
        internal_links = len(soup.find_all("a", href=True))

        page_score = _compute_node_score(
            mention_count=len(extracted["entities"]) + len(extracted["phrases"]),
            in_title=bool(title),
            in_h1=bool(h1_text),
            has_schema=bool(schema_entities or schema),
            internal_links=internal_links,
            quality_score=seo_scores.get("overall_score", 0),
            rank_data=rank_data,
        )
        page_nid = add_node(
            "page", title, page_score,
            {"slug": pslug, "type": ptype, "keyword": kw, "url_path": f"/{pslug}" if pslug else "/"},
        )
        page_nodes.append(page_nid)
        add_edge(domain_nid, page_nid, "belongs_to", 1.0)
        if kw:
            kw_nid = add_node("keyword", kw, page_score)
            add_edge(page_nid, kw_nid, "targets", 0.9)
        add_edge(page_nid, loc_nid, "located_in", 0.8)
        if seed_nid:
            add_edge(page_nid, seed_nid, "supports", 0.7)

        for ent in extracted["entities"] + schema_entities:
            entity_mentions[ent] += 1
            e_nid = add_node("entity", ent, 50)
            add_edge(page_nid, e_nid, "mentions", 0.6)

        for cat in extracted["categories"]:
            c_nid = add_node("category", cat, 60)
            add_edge(page_nid, c_nid, "belongs_to", 0.5)

        for loc in extracted["locations"]:
            l_nid = add_node("location", loc, 55)
            add_edge(page_nid, l_nid, "located_in", 0.6)

        if ptype == "faq":
            for q in re.findall(r"<h3[^>]*>(.*?)</h3>", html, re.I | re.S):
                q_text = _strip_html(q)
                if q_text:
                    q_nid = add_node("question", q_text, 45)
                    add_edge(page_nid, q_nid, "answers", 0.7)

        if schema_entities or schema:
            sch_nid = add_node("schema", f"{title} FAQ" if ptype == "faq" else f"{title} schema", 40)
            add_edge(page_nid, sch_nid, "has_schema", 1.0)

    for kw in talon_kws:
        kw_nid = add_node("keyword", kw, 40, {"source": "talon"})
        add_edge(seed_nid, kw_nid, "supports", 0.5)
        if not any(e["target"] == kw_nid and e["type"] == "targets" for e in edges):
            add_edge(kw_nid, loc_nid, "located_in", 0.4)

    if files["sitemap"]:
        src_nid = add_node("source", "sitemap.xml", 30, {"urls": files["sitemap"].count("<loc>")})
        add_edge(domain_nid, src_nid, "belongs_to", 0.3)

    main_nid = add_node("source", urlparse(main_site_url).netloc or "main-site", 35, {"url": main_site_url})
    add_edge(domain_nid, main_nid, "links_to", 0.4)

    # orphan entities: mentioned but weakly connected
    orphan_entities: list[str] = []
    for nid, node in nodes.items():
        if node["type"] != "entity":
            continue
        connected = sum(1 for e in edges if e["source"] == nid or e["target"] == nid)
        if connected <= 1 and node.get("score", 0) < 55:
            orphan_entities.append(node["label"])

    # missing pages: keywords without page targets
    page_kw_targets = {
        nodes[e["target"]]["label"].lower()
        for e in edges if e["type"] == "targets" and e["target"] in nodes
    }
    missing_pages: list[str] = []
    for kw in talon_kws + _keyword_variations(seed_keyword, location):
        if kw.lower() not in page_kw_targets:
            missing_pages.append(kw)

    for nid, node in nodes.items():
        if node["type"] != "entity":
            continue
        mentions = sum(1 for e in edges if e.get("target") == nid and e.get("type") == "mentions")
        label = node.get("label", "")
        authority = min(100, node.get("score", 0) + mentions * 6)
        aeo_blend = seo_scores.get("aeo_score", seo_scores.get("overall_score", 50))
        visibility = min(100, int(authority * 0.55 + aeo_blend * 0.45))
        gap = 85 if any(label.lower() in m.lower() for m in missing_pages) else max(0, 70 - mentions * 12)
        strength = int((authority + visibility + max(0, 100 - gap)) / 3)
        node["entity_authority"] = authority
        node["entity_visibility"] = visibility
        node["entity_gap"] = gap
        node["entity_strength"] = strength

    # pillar / cluster
    pillar_pages: list[str] = []
    cluster_pages: list[str] = []
    if page_nodes:
        scored = sorted(
            [(nid, nodes[nid].get("score", 0), nodes[nid]["label"]) for nid in page_nodes],
            key=lambda x: x[1], reverse=True,
        )
        if scored:
            pillar_pages.append(scored[0][2])
            cluster_pages.extend([s[2] for s in scored[1:8]])

    entity_strength = int(
        sum(n.get("score", 0) for n in nodes.values() if n["type"] == "entity") /
        max(1, sum(1 for n in nodes.values() if n["type"] == "entity"))
    ) if any(n["type"] == "entity" for n in nodes.values()) else 40

    geo_coverage = int(
        sum(n.get("score", 0) for n in nodes.values() if n["type"] == "location") /
        max(1, sum(1 for n in nodes.values() if n["type"] == "location"))
    ) if any(n["type"] == "location" for n in nodes.values()) else 35

    topic_nodes = [n for n in nodes.values() if n["type"] in ("keyword", "topic", "category")]
    topic_authority = int(
        sum(n.get("score", 0) for n in topic_nodes) / max(1, len(topic_nodes))
    ) if topic_nodes else 45

    if seo_scores.get("entity_score"):
        entity_strength = int((entity_strength + seo_scores["entity_score"]) / 2)
    if seo_scores.get("geo_score"):
        geo_coverage = int((geo_coverage + seo_scores["geo_score"]) / 2)
    if seo_scores.get("authority_score"):
        topic_authority = int((topic_authority + seo_scores["authority_score"]) / 2)

    graph_id = str(uuid.uuid4())[:12]
    graph = {
        "graph_id": graph_id,
        "project_id": project_id,
        "domain": domain,
        "seed_keyword": seed_keyword,
        "location": location,
        "main_site_url": main_site_url,
        "nodes": list(nodes.values())[:_max_nodes()],
        "edges": edges[: _max_nodes() * 3],
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "orphan_entities": orphan_entities[:30],
            "missing_pages": missing_pages[:30],
            "pillar_pages": pillar_pages,
            "cluster_pages": cluster_pages,
            "entity_strength_score": entity_strength,
            "geo_coverage_score": geo_coverage,
            "topic_authority_score": topic_authority,
            "seo_gate_report_id": seo_scores.get("report_id"),
            "talon_keywords": len(talon_kws),
            "dist_html_count": len(files["dist_html_files"]),
        },
        "warnings": warnings,
        "created_at": _now(),
    }

    state = _load_state()
    state.setdefault("graphs", {})[graph_id] = graph
    _save_state(state)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"entity_geo_graph_{graph_id}.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    return {"success": True, **graph}


def geo_expand(location: str, radius_km: float = 30, seed_keyword: str = "") -> dict[str, Any]:
    location = (location or "").strip()
    seed_keyword = (seed_keyword or "").strip()
    if not location:
        return {"success": False, "error": "location gerekli"}

    warnings: list[str] = []
    geo_entities: list[dict[str, Any]] = []
    base_url = _nominatim_url()

    try:
        resp = requests.get(
            f"{base_url}/search",
            params={"q": f"{location}, Turkey", "format": "json", "limit": 5, "addressdetails": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=URL_TIMEOUT,
        )
        time.sleep(NOMINATIM_DELAY_SEC)
        resp.raise_for_status()
        results = resp.json()
        if not isinstance(results, list) or not results:
            warnings.append(f"Nominatim sonuç döndürmedi: {location}")
        else:
            for item in results:
                if not isinstance(item, dict):
                    continue
                name = item.get("display_name", "")
                geo_entities.append({
                    "name": name.split(",")[0].strip(),
                    "type": item.get("type", ""),
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "importance": item.get("importance"),
                    "source": "nominatim",
                })
            lat = float(results[0].get("lat", 0))
            lon = float(results[0].get("lon", 0))
            if lat and lon:
                nearby = requests.get(
                    f"{base_url}/search",
                    params={
                        "q": seed_keyword or "neighbourhood",
                        "format": "json",
                        "limit": 15,
                        "viewbox": f"{lon - 0.2},{lat + 0.2},{lon + 0.2},{lat - 0.2}",
                        "bounded": 1,
                    },
                    headers={"User-Agent": USER_AGENT},
                    timeout=URL_TIMEOUT,
                )
                time.sleep(NOMINATIM_DELAY_SEC)
                if nearby.ok:
                    for item in nearby.json() if isinstance(nearby.json(), list) else []:
                        if isinstance(item, dict):
                            nm = (item.get("display_name") or "").split(",")[0].strip()
                            if nm and nm not in {g["name"] for g in geo_entities}:
                                geo_entities.append({
                                    "name": nm,
                                    "type": item.get("type", ""),
                                    "lat": item.get("lat"),
                                    "lon": item.get("lon"),
                                    "source": "nominatim_nearby",
                                })
    except Exception as exc:
        warnings.append(f"Nominatim provider erişilemedi: {exc}")

    for loc in _KNOWN_LOCATIONS:
        if location.lower() in loc or loc in location.lower():
            continue
        geo_entities.append({"name": loc.title(), "type": "known_region", "source": "hive_known_locations"})

    seen: set[str] = set()
    suggested: list[dict[str, Any]] = []
    for ent in geo_entities:
        name = ent.get("name", "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        kw = f"{name} {seed_keyword}".strip() if seed_keyword else name
        suggested.append({
            "title": f"{name} {seed_keyword.title() or 'Rehberi'}".strip(),
            "slug": _safe_slug(kw),
            "target_keyword": kw.lower(),
            "page_type": "geo_landing",
            "location": name,
        })

    return {
        "success": True,
        "location": location,
        "radius_km": radius_km,
        "seed_keyword": seed_keyword,
        "geo_entities": geo_entities[:40],
        "suggested_geo_pages": suggested[:25],
        "warnings": warnings,
        "provider": "nominatim" if not warnings else "partial",
    }


def topic_clusters(project_id: str) -> dict[str, Any]:
    project_id = _safe_project_id(project_id)
    graph = _latest_graph_for_project(project_id)
    if not graph:
        proj = _get_project(project_id)
        built = build_project_graph(
            project_id,
            domain=proj.get("domain", ""),
            seed_keyword=proj.get("seed_keyword", ""),
            location=proj.get("location", ""),
        )
        if not built.get("success"):
            return built
        graph = built

    summary = graph.get("summary") or {}
    pillars = summary.get("pillar_pages") or []
    clusters = summary.get("cluster_pages") or []
    nodes = {n["id"]: n for n in graph.get("nodes") or []}

    cluster_groups: list[dict[str, Any]] = []
    pillar_label = pillars[0] if pillars else graph.get("seed_keyword", "Ana Konu")
    by_type: dict[str, list[str]] = defaultdict(list)
    for n in graph.get("nodes") or []:
        if n.get("type") == "page":
            by_type[n.get("metadata", {}).get("type", "page")].append(n.get("label", ""))

    cluster_groups.append({
        "pillar": pillar_label,
        "clusters": clusters or by_type.get("geo", []) + by_type.get("faq", []) + by_type.get("blog", []),
        "types": dict(by_type),
    })

    return {
        "success": True,
        "project_id": project_id,
        "graph_id": graph.get("graph_id"),
        "pillar": pillar_label,
        "clusters": cluster_groups[0]["clusters"][:30],
        "cluster_groups": cluster_groups,
        "topic_authority_score": summary.get("topic_authority_score", 0),
    }


def internal_link_plan(project_id: str, max_links_per_page: int = 5) -> dict[str, Any]:
    project_id = _safe_project_id(project_id)
    max_links_per_page = max(1, min(max_links_per_page, 20))
    graph = _latest_graph_for_project(project_id)
    if not graph:
        proj = _get_project(project_id)
        built = build_project_graph(project_id, seed_keyword=proj.get("seed_keyword", ""), location=proj.get("location", ""))
        if not built.get("success"):
            return built
        graph = built

    nodes = {n["id"]: n for n in graph.get("nodes") or []}
    page_ids = [nid for nid, n in nodes.items() if n.get("type") == "page"]
    links: list[dict[str, Any]] = []
    per_page: Counter[str] = Counter()

    def page_label(nid: str) -> str:
        return nodes[nid].get("label", nid)

    pillar = (graph.get("summary") or {}).get("pillar_pages") or []
    pillar_id = next((nid for nid in page_ids if nodes[nid]["label"] in pillar), page_ids[0] if page_ids else "")

    for edge in graph.get("edges") or []:
        src, tgt, etype = edge.get("source"), edge.get("target"), edge.get("type")
        if src not in nodes or tgt not in nodes:
            continue
        if nodes[src].get("type") != "page":
            continue
        reason = ""
        if etype == "located_in" and nodes[tgt].get("type") == "location":
            reason = "same_location"
        elif etype == "supports" and nodes[tgt].get("type") == "keyword":
            reason = "same_topic"
        elif etype == "targets":
            reason = "same_topic"
        elif pillar_id and tgt == pillar_id:
            reason = "pillar_support"
        else:
            continue
        if per_page[src] >= max_links_per_page:
            continue
        if nodes[tgt].get("type") == "page":
            to_page = page_label(tgt)
            from_page = page_label(src)
        elif nodes[tgt].get("type") == "keyword":
            to_page = nodes[tgt]["label"]
            from_page = page_label(src)
        else:
            continue
        anchor = to_page if reason != "pillar_support" else f"{to_page} rehberi"
        links.append({
            "from_page": from_page,
            "to_page": to_page,
            "anchor": anchor[:80],
            "reason": reason,
        })
        per_page[src] += 1

    # pillar → cluster önerileri
    if pillar_id:
        for nid in page_ids:
            if nid == pillar_id or per_page[pillar_id] >= max_links_per_page:
                continue
            links.append({
                "from_page": page_label(pillar_id),
                "to_page": page_label(nid),
                "anchor": page_label(nid),
                "reason": "pillar_support",
            })
            per_page[pillar_id] += 1

    return {
        "success": True,
        "project_id": project_id,
        "graph_id": graph.get("graph_id"),
        "links": links[: max_links_per_page * max(len(page_ids), 1)],
    }


def missing_entities(
    project_id: str = "",
    location: str = "",
    seed_keyword: str = "",
) -> dict[str, Any]:
    if project_id:
        project_id = _safe_project_id(project_id)
        proj = _get_project(project_id)
        location = location or proj.get("location", "")
        seed_keyword = seed_keyword or proj.get("seed_keyword", "")
        graph = _latest_graph_for_project(project_id)
    else:
        proj = None
        graph = None

    location = (location or "Kuşadası").strip()
    seed_keyword = (seed_keyword or "").strip()

    existing_entities: set[str] = set()
    existing_pages: set[str] = set()
    if graph:
        for n in graph.get("nodes") or []:
            lbl = (n.get("label") or "").lower()
            if n.get("type") == "entity":
                existing_entities.add(lbl)
            if n.get("type") == "page":
                existing_pages.add(lbl)

    geo = geo_expand(location, seed_keyword=seed_keyword)
    missing: list[dict[str, Any]] = []
    recommended: list[dict[str, Any]] = []

    for ent in geo.get("geo_entities") or []:
        name = (ent.get("name") or "").strip()
        if not name or name.lower() in existing_entities:
            continue
        missing.append({"entity": name, "type": ent.get("type", ""), "source": ent.get("source", "")})

    for kw in _talon_keywords(seed_keyword, location):
        if kw.lower() not in existing_pages and kw.lower() not in {m["entity"].lower() for m in missing}:
            missing.append({"entity": kw, "type": "keyword", "source": "talon"})

    for page in geo.get("suggested_geo_pages") or []:
        recommended.append(page)

    for m in missing[:20]:
        kw = m["entity"]
        if seed_keyword and seed_keyword.lower() not in kw.lower():
            kw = f"{kw} {seed_keyword}"
        recommended.append({
            "title": f"{m['entity'].title()} {seed_keyword.title() or 'Rehberi'}".strip(),
            "slug": _safe_slug(kw),
            "target_keyword": kw.lower(),
            "page_type": "geo_landing",
            "entity": m["entity"],
        })

    return {
        "success": True,
        "project_id": project_id or None,
        "location": location,
        "seed_keyword": seed_keyword,
        "missing_entities": missing[:40],
        "recommended_pages": recommended[:30],
        "warnings": geo.get("warnings", []),
    }


def analyze_url(url: str, seed_keyword: str = "", location: str = "") -> dict[str, Any]:
    url = (url or "").strip()
    if not url:
        return {"success": False, "error": "url gerekli"}
    if _is_blocked_url(url):
        return {"success": False, "error": "localhost / özel IP URL analizi engellendi"}
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        resp = requests.get(url, timeout=URL_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"success": False, "error": f"URL getirilemedi: {exc}"}

    soup = BeautifulSoup(resp.text, "html.parser")
    title = (soup.find("title").get_text(strip=True) if soup.find("title") else "")
    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else ""
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")[:15]]
    body = soup.get_text(" ", strip=True)
    desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = desc_tag.get("content", "") if desc_tag else ""

    schemas: list[Any] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            schemas.append(json.loads(script.string or "{}"))
        except (json.JSONDecodeError, TypeError):
            pass

    slug = urlparse(url).path.strip("/")
    extracted = extract_entities_from_text(
        body, title=title, seed_keyword=seed_keyword, location=location,
    )
    for sch in schemas:
        extracted["entities"].extend(_parse_schema_entities(sch))

    faq_questions = [q for q in h2s if "?" in q or q.lower().startswith(("sık", "sss"))]

    mini_nodes = [
        {"id": _node_id("page", title or url), "type": "page", "label": title or url, "score": 60},
    ]
    if seed_keyword:
        mini_nodes.append({"id": _node_id("keyword", seed_keyword), "type": "keyword", "label": seed_keyword, "score": 70})
    if location:
        mini_nodes.append({"id": _node_id("location", location), "type": "location", "label": location, "score": 65})
    for ent in extracted["entities"][:15]:
        mini_nodes.append({"id": _node_id("entity", ent), "type": "entity", "label": ent, "score": 50})

    return {
        "success": True,
        "url": url,
        "title": title,
        "h1": h1_text,
        "meta_description": meta_desc,
        "h2_headings": h2s,
        "faq_questions": faq_questions,
        "entities": extracted,
        "schema_count": len(schemas),
        "word_count": len(_word_tokens(body)),
        "nodes": mini_nodes,
    }


def _latest_graph_for_project(project_id: str) -> dict[str, Any] | None:
    state = _load_state()
    graphs = state.get("graphs") or {}
    matches = [g for g in graphs.values() if g.get("project_id") == project_id]
    if not matches:
        return None
    return sorted(matches, key=lambda g: g.get("created_at", ""), reverse=True)[0]


def list_graphs(limit: int = 50) -> dict[str, Any]:
    state = _load_state()
    graphs = list((state.get("graphs") or {}).values())
    graphs.sort(key=lambda g: g.get("created_at", ""), reverse=True)
    brief = [
        {
            "graph_id": g.get("graph_id"),
            "project_id": g.get("project_id"),
            "domain": g.get("domain"),
            "node_count": g.get("summary", {}).get("node_count", 0),
            "edge_count": g.get("summary", {}).get("edge_count", 0),
            "created_at": g.get("created_at"),
        }
        for g in graphs[:limit]
    ]
    return {"success": True, "graphs": brief, "count": len(brief)}


def get_graph(graph_id: str) -> dict[str, Any]:
    graph_id = (graph_id or "").strip()
    if not graph_id or ".." in graph_id or "/" in graph_id:
        return {"success": False, "error": "Geçersiz graph_id"}
    state = _load_state()
    graph = (state.get("graphs") or {}).get(graph_id)
    if not graph:
        path = REPORTS_DIR / f"entity_geo_graph_{graph_id}.json"
        if path.is_file():
            try:
                graph = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    if not graph:
        return {"success": False, "error": "Graph bulunamadı"}
    return {"success": True, **graph}


def export_graph(graph_id: str, fmt: str = "json") -> dict[str, Any]:
    result = get_graph(graph_id)
    if not result.get("success"):
        return result
    graph = {k: v for k, v in result.items() if k != "success"}
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fmt = (fmt or "json").lower()
    if fmt == "md":
        path = REPORTS_DIR / f"entity_geo_graph_{graph_id}.md"
        lines = [
            f"# Entity & GEO Graph — {graph_id}",
            "",
            f"- **Proje:** {graph.get('project_id')}",
            f"- **Domain:** {graph.get('domain')}",
            f"- **Seed:** {graph.get('seed_keyword')}",
            f"- **Lokasyon:** {graph.get('location')}",
            f"- **Oluşturulma:** {graph.get('created_at')}",
            "",
            "## Skorlar",
            "",
        ]
        sm = graph.get("summary") or {}
        lines.extend([
            f"- Entity strength: **{sm.get('entity_strength_score', 0)}**",
            f"- GEO coverage: **{sm.get('geo_coverage_score', 0)}**",
            f"- Topic authority: **{sm.get('topic_authority_score', 0)}**",
            "",
            f"## Nodes ({sm.get('node_count', 0)})",
            "",
        ])
        for n in (graph.get("nodes") or [])[:50]:
            lines.append(f"- `{n.get('type')}` **{n.get('label')}** (score {n.get('score', 0)})")
        lines.extend(["", f"## Edges ({sm.get('edge_count', 0)})", ""])
        for e in (graph.get("edges") or [])[:50]:
            lines.append(f"- {e.get('source')} —{e.get('type')}→ {e.get('target')}")
        if sm.get("missing_pages"):
            lines.extend(["", "## Eksik Sayfalar", ""])
            for p in sm["missing_pages"][:20]:
                lines.append(f"- {p}")
        path.write_text("\n".join(lines), encoding="utf-8")
        rel = str(path.relative_to(ROOT)) if str(path).startswith(str(ROOT)) else str(path)
        return {"success": True, "format": "md", "path": rel, "graph_id": graph_id}
    path = REPORTS_DIR / f"entity_geo_graph_{graph_id}.json"
    path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    rel = str(path.relative_to(ROOT)) if str(path).startswith(str(ROOT)) else str(path)
    return {"success": True, "format": "json", "path": rel, "graph_id": graph_id}


def get_project_scores(project_id: str) -> dict[str, Any]:
    """SEO Quality Gate ve diğer modüller için skor özeti."""
    graph = _latest_graph_for_project(_safe_project_id(project_id))
    if not graph:
        return {"success": False, "error": "Graph yok"}
    sm = graph.get("summary") or {}
    return {
        "success": True,
        "graph_id": graph.get("graph_id"),
        "entity_strength_score": sm.get("entity_strength_score", 0),
        "geo_coverage_score": sm.get("geo_coverage_score", 0),
        "topic_authority_score": sm.get("topic_authority_score", 0),
    }


def get_astro_plan_suggestions(
    seed_keyword: str,
    location: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """Astro Factory generate_site_plan entegrasyonu."""
    missing = missing_entities(project_id=project_id, location=location, seed_keyword=seed_keyword)
    return {
        "success": True,
        "recommended_pages": missing.get("recommended_pages", [])[:15],
        "missing_entities": missing.get("missing_entities", [])[:15],
        "warnings": missing.get("warnings", []),
    }


def page_hub_payloads(recommended_pages: list[dict[str, Any]], city: str = "Aydın", district: str = "") -> list[dict[str, Any]]:
    """Page Hub'a gönderilecek sayfa önerileri."""
    out: list[dict[str, Any]] = []
    for page in recommended_pages:
        out.append({
            "kind": "landing" if page.get("page_type") == "geo_landing" else "sss",
            "title": page.get("title", ""),
            "slug": page.get("slug", ""),
            "keyword": page.get("target_keyword") or page.get("entity", ""),
            "city": city,
            "district": district or page.get("location", ""),
        })
    return out


def health() -> dict[str, Any]:
    state = _load_state()
    nominatim_ok = False
    nominatim_error = ""
    try:
        r = requests.get(
            f"{_nominatim_url()}/status",
            headers={"User-Agent": USER_AGENT},
            timeout=5,
        )
        nominatim_ok = r.status_code == 200
    except requests.RequestException as exc:
        nominatim_error = str(exc)

    llm_available = False
    try:
        from app import config as app_config
        llm_available = bool(
            (app_config.get("OPENROUTER_API_KEY") or "").strip()
            or (app_config.get("OLLAMA_URL") or "").strip()
        )
    except Exception:
        pass

    return {
        "success": True,
        "status": "ok",
        "module": "Entity & GEO Graph",
        "graphs_count": len(state.get("graphs") or {}),
        "max_nodes": _max_nodes(),
        "nominatim_url": _nominatim_url(),
        "nominatim_reachable": nominatim_ok,
        "nominatim_error": nominatim_error or None,
        "llm_enrichment_available": llm_available,
        "generated_sites_dir": str(GENERATED_DIR),
        "reports_dir": str(REPORTS_DIR),
    }


entity_geo_graph = type("EntityGeoGraph", (), {
    "health": staticmethod(health),
    "build_project_graph": staticmethod(build_project_graph),
    "analyze_url": staticmethod(analyze_url),
    "geo_expand": staticmethod(geo_expand),
    "topic_clusters": staticmethod(topic_clusters),
    "internal_link_plan": staticmethod(internal_link_plan),
    "missing_entities": staticmethod(missing_entities),
    "list_graphs": staticmethod(list_graphs),
    "get_graph": staticmethod(get_graph),
    "export_graph": staticmethod(export_graph),
    "get_project_scores": staticmethod(get_project_scores),
    "get_astro_plan_suggestions": staticmethod(get_astro_plan_suggestions),
    "page_hub_payloads": staticmethod(page_hub_payloads),
    "extract_entities_from_text": staticmethod(extract_entities_from_text),
})()
