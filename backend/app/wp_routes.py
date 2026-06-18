"""WordPress yönetim endpoint'leri — HIVE Panel."""

from __future__ import annotations

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel, ConfigDict

from app.database import log_module_run
from app.moduller.wp_rate_limit import check_wp_rate_limit
from app.moduller.wordpress_api import PROFILE_META_KEYS, ensure_wp_connected, wp_api

router = APIRouter(prefix="/api/wp", tags=["WordPress"])


class WPRequest(BaseModel):
    model_config = ConfigDict(extra="allow")


def _log(action: str, req: dict, res: dict) -> None:
    try:
        log_module_run("wordpress", action, req, res)
    except Exception:
        pass


def _api(domain_id: int = 0):
    return wp_api(domain_id)


@router.post("/login")
def wp_login(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    api = _api(int(getattr(req, "domain_id", 0) or 0))
    res = api.login(
        getattr(req, "url", ""),
        getattr(req, "username", ""),
        getattr(req, "password", ""),
    )
    _log("WP Login", dict(req), res)
    return {"status": "aktif", "modul": "WordPress Manager", **res}


@router.post("/connect")
def wp_connect(req: WPRequest, request: Request):
    return wp_login(req, request)


@router.post("/disconnect")
def wp_disconnect(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    res = _api(int(getattr(req, "domain_id", 0) or 0)).disconnect()
    return {"status": "aktif", "modul": "WordPress Manager", **res}


@router.get("/status")
def wp_status(request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    api = _api(domain_id)
    if api.connected:
        st = api.status()
        st["auto_connected"] = False
    else:
        st = ensure_wp_connected(domain_id)
    return {"status": "aktif", "modul": "WordPress Manager", **st}


@router.post("/auto-connect")
def wp_auto_connect(request: Request, domain_id: int = 0):
    """.env bilgileriyle otomatik WP bağlantısı."""
    check_wp_rate_limit(request)
    st = ensure_wp_connected(domain_id, verify=True)
    _log("WP Auto-Connect", {"domain_id": domain_id}, st)
    return {"status": "aktif", "modul": "WordPress Manager", **st}


# ── Posts ──
@router.get("/posts")
def wp_get_posts(request: Request, page: int = 1, per_page: int = 20, search: str = "", domain_id: int = 0):
    check_wp_rate_limit(request)
    res = _api(domain_id).get_posts(page, per_page, search)
    return {"status": "aktif", **res}


@router.post("/posts")
def wp_create_post(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    did = int(getattr(req, "domain_id", 0) or 0)
    res = _api(did).create_post(
        getattr(req, "title", ""),
        getattr(req, "content", ""),
        getattr(req, "status", "draft"),
    )
    _log("WP Post Create", dict(req), res)
    return {"status": "aktif", **res}


@router.put("/posts/{post_id}")
def wp_update_post(post_id: int, req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    fields = {k: v for k, v in req.model_dump().items() if k not in ("domain_id",)}
    res = _api(int(getattr(req, "domain_id", 0) or 0)).update_post(post_id, **fields)
    return {"status": "aktif", **res}


@router.delete("/posts/{post_id}")
def wp_delete_post(post_id: int, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    res = _api(domain_id).delete_post(post_id)
    return {"status": "aktif", **res}


# ── Pages ──
@router.get("/pages")
def wp_get_pages(request: Request, page: int = 1, per_page: int = 20, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_pages(page, per_page)}


@router.post("/pages")
def wp_create_page(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    res = _api(int(getattr(req, "domain_id", 0) or 0)).create_page(
        getattr(req, "title", ""), getattr(req, "content", ""), getattr(req, "status", "draft")
    )
    return {"status": "aktif", **res}


@router.put("/pages/{page_id}")
def wp_update_page(page_id: int, req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    fields = {k: v for k, v in req.model_dump().items() if k != "domain_id"}
    return {"status": "aktif", **_api(int(getattr(req, "domain_id", 0) or 0)).update_page(page_id, **fields)}


@router.delete("/pages/{page_id}")
def wp_delete_page(page_id: int, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).delete_page(page_id)}


# ── Profiles ──
@router.get("/profiles")
def wp_get_profiles(request: Request, page: int = 1, per_page: int = 20, search: str = "", domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_profiles(page, per_page, search)}


@router.post("/profiles")
def wp_create_profile(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    meta = {k: getattr(req, k, "") for k in PROFILE_META_KEYS if hasattr(req, k) and getattr(req, k)}
    res = _api(int(getattr(req, "domain_id", 0) or 0)).create_profile(
        getattr(req, "title", ""),
        getattr(req, "content", ""),
        getattr(req, "status", "publish"),
        meta=meta or None,
        categories=getattr(req, "categories", None),
    )
    return {"status": "aktif", **res}


@router.put("/profiles/{profile_id}")
def wp_update_profile(profile_id: int, req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    fields = {k: v for k, v in req.model_dump().items() if k not in ("domain_id",)}
    meta = {k: fields.pop(k) for k in list(fields) if k in PROFILE_META_KEYS}
    if meta:
        fields["meta"] = meta
    return {"status": "aktif", **_api(int(getattr(req, "domain_id", 0) or 0)).update_profile(profile_id, **fields)}


@router.delete("/profiles/{profile_id}")
def wp_delete_profile(profile_id: int, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).delete_profile(profile_id)}


# ── Categories ──
@router.get("/categories")
def wp_get_categories(request: Request, taxonomy: str = "companion_category", domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_categories(taxonomy)}


@router.post("/categories")
def wp_create_category(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    res = _api(int(getattr(req, "domain_id", 0) or 0)).create_category(
        getattr(req, "name", ""),
        getattr(req, "taxonomy", "companion_category"),
        int(getattr(req, "parent", 0) or 0),
        getattr(req, "slug", ""),
    )
    return {"status": "aktif", **res}


@router.put("/categories/{term_id}")
def wp_update_category(term_id: int, req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    fields = {k: v for k, v in req.model_dump().items() if k not in ("domain_id", "taxonomy")}
    return {"status": "aktif", **_api(int(getattr(req, "domain_id", 0) or 0)).update_category(
        term_id, getattr(req, "taxonomy", "companion_category"), **fields
    )}


@router.delete("/categories/{term_id}")
def wp_delete_category(term_id: int, request: Request, taxonomy: str = "companion_category", domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).delete_category(term_id, taxonomy)}


# ── Tags ──
@router.get("/tags")
def wp_get_tags(request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_tags()}


@router.post("/tags")
def wp_create_tag(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(int(getattr(req, "domain_id", 0) or 0)).create_tag(getattr(req, "name", ""))}


# ── Media ──
@router.get("/media")
def wp_get_media(request: Request, page: int = 1, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_media(page)}


@router.post("/media/upload")
async def wp_upload_media(request: Request, file: UploadFile = File(...), domain_id: int = 0):
    check_wp_rate_limit(request)
    content = await file.read()
    mime = file.content_type or "application/octet-stream"
    res = _api(domain_id).upload_media(file.filename or "upload.bin", content, mime)
    return {"status": "aktif", **res}


@router.delete("/media/{media_id}")
def wp_delete_media(media_id: int, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).delete_media(media_id)}


# ── Users ──
@router.get("/users")
def wp_get_users(request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_users()}


@router.post("/users")
def wp_create_user(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    res = _api(int(getattr(req, "domain_id", 0) or 0)).create_user(
        getattr(req, "username", ""),
        getattr(req, "email", ""),
        getattr(req, "password", ""),
        getattr(req, "roles", None),
    )
    return {"status": "aktif", **res}


@router.delete("/users/{user_id}")
def wp_delete_user(user_id: int, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).delete_user(user_id)}


# ── Comments ──
@router.get("/comments")
def wp_get_comments(request: Request, page: int = 1, status: str = "hold", domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_comments(page, status)}


@router.post("/comments/{comment_id}/approve")
def wp_approve_comment(comment_id: int, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).approve_comment(comment_id)}


@router.delete("/comments/{comment_id}")
def wp_delete_comment(comment_id: int, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).delete_comment(comment_id)}


# ── Plugins / Themes / Settings ──
@router.get("/plugins")
def wp_plugins(request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_plugins()}


@router.post("/plugins/{plugin_slug}/activate")
def wp_activate_plugin(plugin_slug: str, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).activate_plugin(plugin_slug)}


@router.post("/plugins/{plugin_slug}/deactivate")
def wp_deactivate_plugin(plugin_slug: str, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).deactivate_plugin(plugin_slug)}


@router.get("/themes")
def wp_themes(request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_themes()}


@router.post("/themes/{stylesheet}/activate")
def wp_activate_theme(stylesheet: str, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).activate_theme(stylesheet)}


@router.get("/settings")
def wp_settings_get(request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_settings()}


@router.put("/settings")
def wp_settings_put(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    fields = {k: v for k, v in req.model_dump().items() if k != "domain_id"}
    return {"status": "aktif", **_api(int(getattr(req, "domain_id", 0) or 0)).update_settings(**fields)}


# ── Multisite ──
@router.get("/sites")
def wp_sites(request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).get_sites()}


@router.post("/sites")
def wp_sites_create(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    res = _api(int(getattr(req, "domain_id", 0) or 0)).create_site(
        getattr(req, "domain", ""),
        getattr(req, "title", ""),
        getattr(req, "email", ""),
        getattr(req, "path", "/"),
    )
    return {"status": "aktif", **res}


@router.delete("/sites/{blog_id}")
def wp_sites_delete(blog_id: int, request: Request, domain_id: int = 0):
    check_wp_rate_limit(request)
    return {"status": "aktif", **_api(domain_id).delete_site(blog_id)}


@router.post("/sites/bulk")
def wp_sites_bulk(req: WPRequest, request: Request):
    check_wp_rate_limit(request)
    sites = getattr(req, "sites", []) or []
    did = int(getattr(req, "domain_id", 0) or 0)
    api = _api(did)
    results = []
    ok = err = 0
    for s in sites:
        r = api.create_site(
            s.get("domain", ""),
            s.get("title", s.get("domain", "")),
            s.get("email", f"admin@{s.get('domain', 'local')}"),
            s.get("path", "/"),
        )
        results.append({"domain": s.get("domain"), **r})
        if r.get("success"):
            ok += 1
        else:
            err += 1
    return {"status": "aktif", "success": True, "total": len(sites), "success_count": ok, "error_count": err, "results": results}


@router.get("/head-injections")
def wp_head_injections_get(domain_id: int = 0):
    api = _api(domain_id)
    if not api.connected:
        return {"success": False, "error": "WP bağlantısı yok"}
    res = api.get_head_injections()
    _log("Head Injections GET", {"domain_id": domain_id}, res)
    return res


@router.put("/head-injections")
def wp_head_injections_put(req: WPRequest, domain_id: int = 0):
    api = _api(domain_id)
    if not api.connected:
        return {"success": False, "error": "WP bağlantısı yok"}
    injections = getattr(req, "injections", None) or []
    res = api.update_head_injections(injections)
    _log("Head Injections PUT", {"domain_id": domain_id, "count": len(injections)}, res)
    return res
