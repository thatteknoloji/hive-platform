from fastapi import FastAPI, Request, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app import config
from app.database import log_module_run, get_module_history, get_module_stats, get_all_logs, delete_module_history, get_son_aktiviteler, get_gunluk_aktivite
from app.moduller import (
    MODULLER, MODUL_MAP,
    anahtar_kelime_uret, kelime_grupla, export_kelimeler,
    gecmis_listele, gecmis_getir, gecmis_sil,
    favori_ekle, favori_kaldir, favori_listele, api_durum, kefen_analiz, 
    rakip_backlink_analizi, btk_sikayet_gonder, spam_backlink_gonder, rapor_uret, parazit_yerlestir,
    spam_tara, disavow_olustur, misilleme_yap,
    entry_gonder, reddit_yorum, maps_yorum,
    sikayet_gonder, domain_bul, cal,
    zehirle, takip_et, sorgula, penalty_analiz,
    koruma_aktif, bildir, blast_yap,
    mesaj_gonder, gizlilik_tara, cluster_olustur,
    optimize_et, agent_gonder, hikaye_uret,
    yorum_yap, saldir, ara, aktiflestir, deaktiflestir,
    bildirim_gonder, brand_tara, denetle,
    content_olustur, paylas, email_gonder,
    kazi, arastir, competitor_analiz, insa,
    yonet, sitemap_olustur, duzenle, ekle,
    speed_optimize, kontrol_et, raporla,
    conversion_takip, baslat, heatmap_olustur,
    user_analiz, funnel_analiz, topla,
    yayinla, dondur, cevir, local_optimize,
    citation_olustur, review_topla, reputation_tara,
    izle, trend_analiz, sentiment_analiz,
    parazit_listele, parazit_sil, platform_analiz, zeus_health,
    mystic_export,
    keyword_kaydet, keyword_sil, keyword_listele, toplu_kontrol, ranktracker_export,
    entry_listele, entry_sil, entry_analiz,
    avla, dogrula, tam_tarama, apihunter_rapor,
    apihunter_listele, apihunter_temizle,
    apihunter_hedef_ekle, apihunter_hedef_listele, apihunter_hedef_sil, apihunter_export,
    post_ac, post_listele, reddit_yorum_listele, reddit_yorum_sil,
    maps_yorum_listele, yorum_istatistik, maps_hedef_ekle, maps_export,
    sikayet_sorgula, sikayet_listele, sikayet_iptal, btk_istatistik,
    domain_kaydet, expired_domain_listele, domain_sil, expired_export,
    calinan_listele, hijacker_analiz, hedef_tara, hijacker_export,
    find_broken_backlinks, steal_backlink, hijacker_health,
    zehirleme_listele, spam_hedef_ekle, spam_hedef_listele, spam_rapor,
    # new analytics
    tum_raporlar, analytics_sil, ozet,
    # new conversion
    conversion_listele, conversion_istatistik,
    # new abtest
    abtest_listele, sonlandir, abtest_istatistik, abtest_rapor,
    # new heatmap
    heatmap_listele, heatmap_detay, heatmap_sil,
    # new funnel
    funnel_listele, funnel_detay,
    # new citation
    citation_listele, dogrula, citation_export,
    # new review
    review_listele, yanitla, review_istatistik,
    # new trend
    trend_listele, populer, trend_grafik,
    # new sentiment
    toplu_analiz, sentiment_gecmis, sentiment_istatistik,
    # new forecast
    tahmin_et, forecast_listele, forecast_karsilastir, forecast_export,
    # new alert
    alert_olustur, alert_listele, alert_sil, alert_kontrol, alert_gecmis,
    # new notification
    notification_gonder, notification_listele, oku, notification_temizle, notification_ayarlar,
    # new report
    report_olustur, report_listele, report_sil, report_indir, zamanla,
    # new schedule
    schedule_olustur, schedule_listele, schedule_sil, duraklat, devam_ettir,
    # new backup
    backup_olustur, backup_listele, backup_sil, backup_indir, otomatik_zamanla,
    # new restore
    onizle, geri_yukle, restore_listele, restore_sil,
    # new log
    log_listele, log_detay, log_temizle, log_ara, log_istatistik,
    # new monitor
    monitor_kontrol, monitor_listele, monitor_detay, monitor_ayarlar, ayarlari_kaydet,
    # new debug
    modul_test, hata_ayikla, performans, log_incele, sema_dogrula,
    # api key manager
    get_key, set_key, get_all_keys,
    # search & github
    search_serpapi, github_repos, github_create_gist,
    # ai chat
    sor,
)
from app.moduller.exposed_key_hunter import hunter_instance
from app.moduller.openseo_integration import openseo_keyword_research
from app.moduller.serpbear_integration import serpbear_ekle, serpbear_goruntule, serpbear_sil, serpbear_liste, serpbear_simulasyon_sonuclari
from app.moduller.seointel_integration import seointel_olustur, seointel_rapor_getir, seointel_ai_gorunurluk, seointel_backlinks
from app.moduller.dataseo_integration import dataseo_backlinks, dataseo_keyword_ideas, dataseo_keyword_difficulty, dataseo_traffic
from app.moduller.seoagent_integration import seoagent_crawl, seoagent_audit_page
from app.moduller.wordpress_manager import site_olustur, site_listele, site_sil, site_sifirla, site_icerik_doldur, site_batch_plugin
from app.moduller.domain_manager import domain_ekle, domain_listele, domain_wp_kur, domain_batch_ekle
from app.moduller.domain_manager import domain_batch_sil, domain_batch_sifirla, domain_batch_plugin_yukle
from app.moduller.domain_manager import domain_cloudflare_import, domain_saglik_kontrol, domain_toplu_saglik_kontrol
from app.moduller.domain_manager import domain_yedek_al, domain_restore, domain_yedek_listele, domain_otonom_kur
from app.moduller.domain_manager import check_domain_availability, check_bulk_domain_availability
from app.moduller.domain_manager import wp_connect, wp_disconnect, wp_list_sites, wp_create_site, wp_delete_site, wp_bulk_create_sites, wp_connection_status
from app.moduller.subdomain_manager import subdomain_ekle, subdomain_listele, subdomain_sil, subdomain_duzenle
from app.moduller.subdomain_manager import subdomain_talondan_olustur, subdomain_batch_sil, subdomain_batch_sifirla, subdomain_batch_plugin
from app.wp_routes import router as wp_router
from app.panel_routes import router as panel_router
from app.v3_routes import router as v3_router
from app.academy_routes import router as academy_router
from app.moduller.hive_cloud_deploy import PUBLIC_ROOT as HIVE_PUBLIC_SITES_ROOT
from app import panel_identity
from app.moduller.tumblr_api import (
    get_request_token,
    get_authorize_url,
    get_access_token,
    post_to_tumblr,
    connection_status,
    get_pending_secret,
    fetch_user_blogs,
)

_disable_docs = config.get("HIVE_DISABLE_DOCS", "").lower() in ("1", "true", "yes")
app = FastAPI(
    title="HIVE Panel",
    version="3.0",
    docs_url=None if _disable_docs else "/docs",
    redoc_url=None if _disable_docs else "/redoc",
    openapi_url=None if _disable_docs else "/openapi.json",
)
app.include_router(wp_router)
app.include_router(panel_router)
app.include_router(v3_router)
app.include_router(academy_router)

HIVE_PUBLIC_SITES_ROOT.mkdir(parents=True, exist_ok=True)
app.mount(
    "/sites",
    StaticFiles(directory=str(HIVE_PUBLIC_SITES_ROOT), html=True),
    name="hive_public_sites",
)


def _brain_emit(path: str, req, result, module: str = "", event_type: str = ""):
    """Brain memory hook — modül dosyalarına dokunmadan main.py'den çağrılır."""
    try:
        from app.moduller.brain_hooks import emit_brain_event
        req_d = req.model_dump() if hasattr(req, "model_dump") else (dict(req) if isinstance(req, dict) else {})
        res_d = dict(result) if isinstance(result, dict) else {}
        emit_brain_event(path, req_d, res_d, module=module, event_type=event_type)
    except Exception:
        pass


@app.on_event("startup")
def _startup_services():
    try:
        panel_identity.bootstrap()
    except Exception:
        pass
    try:
        from app.moduller import llm_router
        llm_router.ensure_ollama_running()
    except Exception:
        pass
    try:
        from app.moduller.wordpress_api import ensure_wp_connected
        wp_st = ensure_wp_connected(verify=True)
        if wp_st.get("connected"):
            print(f"[HIVE] WordPress bağlı: {wp_st.get('url')} (auto={wp_st.get('auto_connected')})")
        else:
            print(f"[HIVE] WordPress bağlantısı yok: {wp_st.get('error', 'bilinmiyor')}")
    except Exception as e:
        print(f"[HIVE] WordPress auto-connect hatası: {e}")
    try:
        from app.moduller.astro_auto_publisher import astro_auto_publisher
        astro_auto_publisher.start_scheduler()
        print("[HIVE] Astro Auto Publisher scheduler başlatıldı")
    except Exception as e:
        print(f"[HIVE] Astro Auto Publisher scheduler hatası: {e}")


HIVE_API_KEY = config.get("HIVE_API_KEY", "")
HIVE_DISABLE_DOCS = config.get("HIVE_DISABLE_DOCS", "").lower() in ("1", "true", "yes")
HIVE_RATE_LIMIT = int(config.get("HIVE_RATE_LIMIT_PER_MIN", "120") or "120")

_RATE_BUCKET: dict[str, list[float]] = {}


def _cors_origins() -> list[str]:
    defaults = [
        "http://localhost:4000",
        "http://127.0.0.1:4000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://hive.thiqos.com",
    ]
    raw = config.get("HIVE_CORS_ORIGINS", "").strip()
    if raw:
        extras = [o.strip() for o in raw.split(",") if o.strip()]
        return list(dict.fromkeys(extras + defaults))
    return defaults


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _public_paths() -> set[str]:
    paths = {
        "/health",
        "/favicon.ico",
        "/api/talon/health",
        "/api/revenue-leads/track",
        "/api/revenue-leads/track-redirect",
        "/api/auth/login",
        "/api/auth/me",
    }
    if not HIVE_DISABLE_DOCS:
        paths.update({"/docs", "/openapi.json", "/redoc"})
    return paths


def _is_public_request(path: str) -> bool:
    if path in _public_paths():
        return True
    return path == "/sites" or path.startswith("/sites/")


class AuthLoginBody(BaseModel):
    email: str = ""
    password: str = ""


@app.post("/api/auth/login")
def auth_login(req: AuthLoginBody):
    from app.auth import auth_enabled, login
    if not auth_enabled():
        raise HTTPException(status_code=503, detail="Panel auth not configured on server")
    result = login(req.email, req.password)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return result


@app.post("/api/auth/logout")
def auth_logout():
    return {"success": True}


@app.get("/api/auth/me")
def auth_me(request: Request):
    from app.auth import auth_enabled, me_from_token, verify_access_token
    if not auth_enabled():
        return {"success": True, "authenticated": True, "auth_required": False, "user": {"email": "dev"}}
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return me_from_token(auth_header[7:])
    api_key = request.headers.get("X-API-Key", "")
    if api_key and api_key == HIVE_API_KEY:
        return {"success": True, "authenticated": True, "user": {"email": "api_key"}, "via": "api_key"}
    return {"success": True, "authenticated": False, "auth_required": True}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    import time
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
    now = time.time()
    bucket = _RATE_BUCKET.setdefault(ip, [])
    bucket[:] = [t for t in bucket if now - t < 60]
    if len(bucket) >= HIVE_RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    bucket.append(now)
    return await call_next(request)


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    if _is_public_request(request.url.path):
        return await call_next(request)

    from app.auth import auth_enabled, verify_access_token

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        payload = verify_access_token(auth_header[7:])
        if payload:
            user = panel_identity.get_user_by_email(payload.get("sub", ""))
            if not user or user.get("status") != "active":
                return JSONResponse(status_code=401, content={"detail": "Unauthorized: user disabled"})
            request.state.hive_user = panel_identity.sanitize_user(user)
            module = panel_identity.module_for_path(request.url.path)
            if module:
                action = "view" if request.method == "GET" else "run"
                if request.method == "POST":
                    action = "create"
                elif request.method in ("PATCH", "PUT"):
                    action = "edit"
                elif request.method == "DELETE":
                    action = "delete"
                if not panel_identity.has_permission(user.get("role", ""), module, action):
                    return JSONResponse(status_code=403, content={"detail": "Permission denied"})
            return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if api_key and api_key == HIVE_API_KEY:
        return await call_next(request)

    if not auth_enabled():
        if api_key != HIVE_API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized: Missing or invalid API key"})
        return await call_next(request)

    return JSONResponse(status_code=401, content={"detail": "Unauthorized: login required"})


_MCC_BRAIN_LAST_EMIT: float = 0.0
_MCC_BRAIN_DEBOUNCE_SEC = 300


@app.middleware("http")
async def performance_timing_middleware(request: Request, call_next):
    """API yanıt sürelerini system_performance_engine'e kaydet."""
    import time
    start = time.perf_counter()
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        elapsed_ms = (time.perf_counter() - start) * 1000
        try:
            from app.moduller.mission_control_center import record_request_timing
            cl = response.headers.get("content-length")
            payload_bytes = int(cl) if cl and cl.isdigit() else 0
            record_request_timing(request.url.path, elapsed_ms, response.status_code, payload_bytes)
        except Exception:
            pass
    return response

class ModulRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

class TalonRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    ana_kelime: str = "kuşadası escort"
    adet: int = 10
    sehir: str = "kuşadası"
    negatif_filtre: str | None = None
    sektor: str = "escort"

class TalonTransferBody(BaseModel):
    kelimeler: list = []
    domain: str = ""
    sehir: str = ""

class TalonTrendBody(BaseModel):
    kelimeler: list = []
    sehir: str = ""

class TalonGapBody(BaseModel):
    bizim_kelimeler: list = []
    rakip_domain: str = ""
    hedef_domain: str = ""
    limit: int = 30

class TalonMigrateBody(BaseModel):
    dry_run: bool = False

class TalonSearchQueryBody(BaseModel):
    query: str = ""
    seed_keyword: str = ""
    location_keyword: str = ""
    num_results: int = 10
    domain: str = ""
    limit: int = 30

class TalonOrchestratorBody(BaseModel):
    seed_keyword: str = ""
    keyword: str = ""
    location: str = ""
    limit: int = 50

class TalonGruplaRequest(BaseModel):
    kelimeler: list

class TalonFavoriRequest(BaseModel):
    kelime: str
    rekabet: str = "orta"
    arama_hacmi: str = "100-500"
    rakip_var: bool = False

class TalonSettingsBody(BaseModel):
    tavily: str = ""
    exa: str = ""
    searxng_url: str = ""
    openrouter: str = ""
    ollama_host: str = ""
    # Legacy — yalnızca TALON_USE_LEGACY_APIS=true iken kullanılır
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    serpapi: str = ""

@app.post("/prompt")
def prompt_handler(req: ModulRequest):
    return {"cevap": f"Ollama bağlantısı henüz kurulmadı. Prompt: {req.prompt if hasattr(req,'prompt') else ''}"}

@app.get("/api/moduller")
def modul_listesi():
    return {"toplam": len(MODULLER), "moduller": MODULLER}

POST_HANDLERS = {

    "kefen":           lambda d: kefen_analiz(getattr(d, "domain", "")),
    "zeus":            lambda d: parazit_yerlestir(
        getattr(d, "platform", "Medium"),
        getattr(d, "konu", "") or getattr(d, "title", ""),
        getattr(d, "hedef_url", "") or getattr(d, "url", ""),
        getattr(d, "subreddit", ""),
        getattr(d, "video_id", ""),
    ),
    "eksisozluk":      lambda d: entry_gonder(getattr(d, "baslik", ""), getattr(d, "entry", "")),
    "medium_bot":    lambda d: __import__("app.moduller.medium_bot", fromlist=["publish_to_medium"]).publish_to_medium(getattr(d, "title", ""), getattr(d, "content", ""), getattr(d, "tags", None)),
    "seo_poisoning": lambda d: __import__("app.moduller.seo_poisoning", fromlist=["run_campaign"]).run_campaign(getattr(d, "target_domain", ""), getattr(d, "keywords", None), getattr(d, "platforms", None)),
    "reddit":          lambda d: reddit_yorum(getattr(d, "baslik", ""), getattr(d, "yorum", "")),
    "maps":            lambda d: maps_yorum(getattr(d, "isletme", ""), getattr(d, "adet", 5)),
    "btk":             lambda d: sikayet_gonder(getattr(d, "domain", "")),
    "expireddomain":   lambda d: domain_bul(getattr(d, "kelime", "")),
    "backlinkhijacker": lambda d: cal(getattr(d, "domain", "")),
    "spambacklink":    lambda d: zehirle(getattr(d, "domain", ""), getattr(d, "adet", 1000)),
    "ranktracker":     lambda d: takip_et(
        getattr(d, "kelime", ""),
        getattr(d, "domain", ""),
        getattr(d, "sehir", ""),
    ),
    "ai_citation":     lambda d: sorgula(getattr(d, "marka", "")),
    "penalty":         lambda d: penalty_analiz(getattr(d, "domain", "")),
    "indexing":        lambda d: bildir(getattr(d, "url", "")),
    "brandmention":    lambda d: blast_yap(getattr(d, "marka", "")),
    "messenger":       lambda d: mesaj_gonder(getattr(d, "mesaj", "")),
    "veri":            lambda d: gizlilik_tara(getattr(d, "veri", "")),
    "topiccluster":    lambda d: cluster_olustur(getattr(d, "konu", "")),
    "internallink":    lambda d: optimize_et(getattr(d, "url", "")),
    "aiagent":         lambda d: agent_gonder(getattr(d, "hedef", "")),
    "hyperlocal":      lambda d: hikaye_uret(getattr(d, "lokasyon", "")),
    "yorum":           lambda d: yorum_yap(getattr(d, "url", ""), getattr(d, "adet", 5)),
    "phishing":        lambda d: saldir(getattr(d, "hedef", "")),
    "zeroday":         lambda d: ara(getattr(d, "hedef", "")),
    "indexnow":        lambda d: bildirim_gonder(getattr(d, "url", "")),
    "brandmentions":   lambda d: brand_tara(getattr(d, "marka", "")),
    "seoaudit":        lambda d: denetle(getattr(d, "url", "")),
    "contentgen":      lambda d: content_olustur(getattr(d, "konu", ""), getattr(d, "adet", 3)),
    "socialmedia":     lambda d: paylas(getattr(d, "platform", "Twitter"), getattr(d, "mesaj", "")),
    "emailblast":      lambda d: email_gonder(getattr(d, "konu", ""), getattr(d, "adet", 100)),
    "webscraper":      lambda d: kazi(
        getattr(d, "url", ""),
        int(getattr(d, "derinlik", 1) or 1),
        int(getattr(d, "max_pages", 10) or 10),
    ),
    "keywordresearch": lambda d: arastir(getattr(d, "kelime", "")),
    "competitor":      lambda d: competitor_analiz(getattr(d, "domain", "")),
    "linkbuilder":     lambda d: insa(getattr(d, "kelime", ""), getattr(d, "adet", 10)),
    "redirect":        lambda d: yonet(getattr(d, "url", "")),
    "sitemap":         lambda d: sitemap_olustur(getattr(d, "url", "")),
    "robots":          lambda d: duzenle(getattr(d, "url", "")),
    "schemamarkup":    lambda d: ekle(getattr(d, "url", "")),
    "speedopt":        lambda d: speed_optimize(getattr(d, "url", "")),
    "mobilecheck":     lambda d: kontrol_et(getattr(d, "url", "")),
    "analytics":       lambda d: raporla(getattr(d, "url", "")),
    "conversion":      lambda d: conversion_takip(getattr(d, "url", "")),
    "abtest":          lambda d: baslat(getattr(d, "varyant_a", ""), getattr(d, "varyant_b", "")),
    "heatmap":         lambda d: heatmap_olustur(getattr(d, "url", "")),
    "userbehavior":    lambda d: user_analiz(getattr(d, "url", "")),
    "funnel":          lambda d: funnel_analiz(getattr(d, "url", "")),
    "leadscraper":     lambda d: topla(
        getattr(d, "kelime", ""),
        int(getattr(d, "adet", 50) or 50),
        getattr(d, "url", ""),
    ),
    "autoblog":        lambda d: yayinla(getattr(d, "konu", "")),
    "spinner":         lambda d: dondur(getattr(d, "metin", "")),
    "translator":      lambda d: cevir(getattr(d, "metin", ""), getattr(d, "dil", "İngilizce")),
    "localseo":        lambda d: local_optimize(getattr(d, "isletme", ""), getattr(d, "adres", "")),
    "citation":        lambda d: citation_olustur(getattr(d, "isletme", "")),
    "review":          lambda d: review_topla(getattr(d, "url", "")),
    "reputation":      lambda d: reputation_tara(getattr(d, "marka", "")),
    "crisis":          lambda d: izle(getattr(d, "marka", "")),
    "trend":           lambda d: trend_analiz(getattr(d, "konu", "")),
    "sentiment":       lambda d: sentiment_analiz(getattr(d, "metin", "")),
    "openseo":         lambda d: openseo_keyword_research(getattr(d, "kelime", "")),
    "serpbear":        lambda d: serpbear_goruntule(getattr(d, "keyword", "")),
    "seointel":        lambda d: seointel_ai_gorunurluk(getattr(d, "marka", "")),
    "dataseo":         lambda d: dataseo_backlinks(getattr(d, "domain", "")),
    "seoagent":        lambda d: seoagent_crawl(getattr(d, "domain", "")),
    "wordpress":       lambda d: site_listele(),
    "apihunter":       lambda d: tam_tarama(
        getattr(d, "kelime", ""),
        getattr(d, "domain", ""),
        getattr(d, "kaynaklar", None),
    ),
    "forecast":       lambda d: tahmin_et(getattr(d, "veri_tipi", "trend")),
    "alert":          lambda d: alert_olustur(getattr(d, "hedef", ""), getattr(d, "kosul", ">"), getattr(d, "esik", 0)),
    "notification":   lambda d: notification_gonder(getattr(d, "kanal", "panel"), getattr(d, "baslik", ""), getattr(d, "mesaj", "")),
    "report":         lambda d: report_olustur(getattr(d, "modul_id", ""), getattr(d, "format", "csv")),
    "schedule":       lambda d: schedule_olustur(getattr(d, "modul_id", ""), getattr(d, "zaman", ""), getattr(d, "parametreler", {})),
    "backup":         lambda d: backup_olustur(getattr(d, "module_id", "")),
    "restore":        lambda d: geri_yukle(getattr(d, "yedek_id", "")),
    "ai_chat":        lambda d: sor(getattr(d, "prompt", "")),
    "monitor":        lambda d: monitor_kontrol(),
    "debug":          lambda d: modul_test(getattr(d, "modul_id", "")),
    "log":            lambda d: log_listele(getattr(d, "module_id", ""), getattr(d, "seviye", "")),
}

for mod_id, handler in POST_HANDLERS.items():
    mod_entry = MODUL_MAP.get(mod_id)
    if not mod_entry:
        continue
    mod_ad = mod_entry["ad"]
    exec(f"""
@app.post(\"/api/{mod_id}\", name=\"{mod_id}\")
def {mod_id}_post(req: ModulRequest):
    sonuc = POST_HANDLERS[\"{mod_id}\"](req)
    try: log_module_run(\"{mod_id}\", \"{mod_ad}\", dict(req), dict(sonuc))
    except: pass
    return {{"status\": \"aktif\", \"modul\": \"{mod_ad}\", **sonuc}}

@app.get(\"/api/{mod_id}\")
def {mod_id}_get():
    return {{"status\": \"aktif\", \"modul\": \"{mod_ad}\", \"id\": \"{mod_id}\"}}
""")

@app.post("/api/wp/site/create")
def wp_site_create(req: ModulRequest):
    sonuc = site_olustur(
        getattr(req, "subdomain", ""),
        getattr(req, "baslik", ""),
        getattr(req, "email", ""),
        getattr(req, "domain", ""),
    )
    return {"status": "aktif", "modul": "WordPress Site Manager", **sonuc}

@app.get("/api/wp/sites/list")
def wp_sites_list():
    sonuc = site_listele()
    return {"status": "aktif", "modul": "WordPress Site Manager", **sonuc}

@app.delete("/api/wp/site/{site_id}")
def wp_site_delete(site_id: int):
    sonuc = site_sil(site_id)
    return {"status": "aktif", "modul": "WordPress Site Manager", **sonuc}

@app.post("/api/wp/site/reset-password")
def wp_site_reset(req: ModulRequest):
    sonuc = site_sifirla(int(getattr(req, "site_id", 0)), getattr(req, "yeni_sifre", ""))
    return {"status": "aktif", "modul": "WordPress Site Manager", **sonuc}

@app.post("/api/domain/add")
def domain_add(req: ModulRequest):
    sonuc = domain_ekle(
        getattr(req, "domain", ""),
        getattr(req, "ip", ""),
        getattr(req, "ssh_user", ""),
        getattr(req, "ssh_pass", ""),
        getattr(req, "db_name", ""),
        getattr(req, "db_user", ""),
        getattr(req, "db_pass", ""),
    )
    return {"status": "aktif", "modul": "Domain Manager", **sonuc}

@app.get("/api/domain/list")
def domain_list():
    sonuc = domain_listele()
    return {"status": "aktif", "modul": "Domain Manager", **sonuc}

@app.post("/api/domain/install-wp/{domain_id}")
def domain_install_wp(domain_id: int):
    sonuc = domain_wp_kur(domain_id)
    return {"status": "aktif", "modul": "Domain Manager", **sonuc}

@app.post("/api/domain/batch")
def domain_batch(req: ModulRequest):
    sonuc = domain_batch_ekle(getattr(req, "domainler", []))
    return {"status": "aktif", "modul": "Domain Manager", **sonuc}

@app.post("/api/subdomain/add")
def subdomain_add(req: ModulRequest):
    sonuc = subdomain_ekle(
        int(getattr(req, "domain_id", 0)),
        getattr(req, "subdomain", ""),
        getattr(req, "site_title", ""),
        getattr(req, "admin_email", ""),
        getattr(req, "parent_domain", ""),
    )
    return {"status": "aktif", "modul": "Subdomain Manager", **sonuc}

@app.get("/api/subdomain/list/{domain_id}")
def subdomain_list(domain_id: int):
    sonuc = subdomain_listele(domain_id)
    return {"status": "aktif", "modul": "Subdomain Manager", **sonuc}

@app.delete("/api/subdomain/{sub_id}")
def subdomain_delete(sub_id: int):
    sonuc = subdomain_sil(sub_id)
    return {"status": "aktif", "modul": "Subdomain Manager", **sonuc}

@app.post("/api/subdomain/update")
def subdomain_update(req: ModulRequest):
    sonuc = subdomain_duzenle(
        int(getattr(req, "sub_id", 0)),
        getattr(req, "site_title", ""),
        getattr(req, "admin_email", ""),
    )
    return {"status": "aktif", "modul": "Subdomain Manager", **sonuc}

# WP connect/posts/profiles/... → app/wp_routes.py

@app.post("/api/talon/generate")
def talon_generate(req: TalonRequest):
    try:
        from app.moduller.talon_utils import SerpAPIService
        detayli, search_id = anahtar_kelime_uret(
            req.ana_kelime, req.adet, req.sehir, req.negatif_filtre, req.sektor,
        )
        api_aktif = SerpAPIService.is_configured()
        sonuc = {
            "kelimeler": detayli,
            "search_id": search_id,
            "api_kullanildi": api_aktif,
            "simulasyon": not api_aktif,
            "stack": "v2-free",
        }
        try: log_module_run("talon", "Talon", dict(req), dict(sonuc))
        except: pass
        return {"status": "aktif", "modul": "Talon", **sonuc}
    except Exception as e:
        return {"status": "hata", "modul": "Talon", "hata": str(e)}

@app.post("/api/talon")
def talon_post(req: TalonRequest):
    return talon_generate(req)

@app.get("/api/talon")
def talon_get():
    return {"status": "aktif", "modul": "Talon", "id": "talon"}

@app.post("/api/talon/grupla")
def talon_grupla(req: TalonGruplaRequest):
    try:
        gruplar = kelime_grupla(req.kelimeler)
        return {"status": "aktif", "gruplar": gruplar}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

@app.get("/api/talon/export/{format}")
def talon_export(format: str, kelime: str = ""):
    if format not in ("csv", "json", "txt"):
        return {"status": "hata", "hata": "Geçersiz format. csv, json veya txt olmalı"}
    try:
        import json as _json
        items = _json.loads(kelime) if kelime else []
        sonuc = export_kelimeler(items, format)
        return {"status": "aktif", **sonuc}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

@app.post("/api/talon/export/{format}")
def talon_export_post(format: str, req: TalonGruplaRequest):
    if format not in ("csv", "json", "txt"):
        return {"status": "hata", "hata": "Geçersiz format. csv, json veya txt olmalı"}
    try:
        sonuc = export_kelimeler(req.kelimeler, format)
        return {"status": "aktif", **sonuc}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

@app.get("/api/talon/history")
def talon_history():
    return {"status": "aktif", "kayitlar": gecmis_listele()}

@app.get("/api/talon/history/{search_id}")
def talon_history_get(search_id: str):
    kayit = gecmis_getir(search_id)
    if not kayit:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    return {"status": "aktif", **kayit}

@app.delete("/api/talon/history/{search_id}")
def talon_history_sil(search_id: str):
    gecmis_sil(search_id)
    return {"status": "silindi", "id": search_id}

@app.get("/api/talon/gecmis")
def talon_gecmis():
    return {"status": "aktif", "kayitlar": gecmis_listele()}

@app.delete("/api/talon/gecmis/{kayit_id}")
def talon_gecmis_sil(kayit_id: str):
    gecmis_sil(kayit_id)
    return {"status": "silindi", "id": kayit_id}

@app.get("/api/talon/favoriler")
def talon_favori_listele():
    return {"status": "aktif", "favoriler": favori_listele()}

@app.post("/api/talon/favoriler")
def talon_favori_ekle(req: TalonFavoriRequest):
    ok = favori_ekle(req.kelime, req.rekabet, req.arama_hacmi, req.rakip_var)
    return {"status": "eklendi" if ok else "zaten_var", "kelime": req.kelime}

@app.delete("/api/talon/favoriler/{kelime}")
def talon_favori_sil(kelime: str):
    import urllib.parse
    kelime = urllib.parse.unquote(kelime)
    ok = favori_kaldir(kelime)
    return {"status": "silindi" if ok else "bulunamadi", "kelime": kelime}

@app.get("/api/talon/status")
def talon_status():
    return {"status": "aktif", "api": api_durum()}

@app.post("/api/talon/settings")
def talon_settings(req: TalonSettingsBody):
    from app.moduller.talon import talon_settings_kaydet
    result = talon_settings_kaydet(req.model_dump(exclude_none=True))
    return {"status": "kaydedildi", **result}


@app.get("/api/talon/sektorler")
def talon_sektorler():
    from app.moduller.talon_extensions import liste_sektorler
    return {"status": "aktif", "sektorler": liste_sektorler()}


@app.post("/api/talon/ranktracker-transfer")
def talon_ranktracker_transfer(req: TalonTransferBody):
    from app.moduller.talon_extensions import rank_tracker_aktar
    result = rank_tracker_aktar(req.kelimeler, req.domain, req.sehir)
    log_module_run("talon", "Rank Tracker Aktarım", req.model_dump(), result)
    return result


@app.post("/api/talon/trend-analiz")
def talon_trend_analiz(req: TalonTrendBody):
    from app.moduller.talon_extensions import trend_analiz
    return trend_analiz(req.kelimeler, req.sehir)


@app.post("/api/talon/rakip-gap")
def talon_rakip_gap(req: TalonGapBody):
    from app.moduller.talon_extensions import rakip_keyword_gap
    return rakip_keyword_gap(req.bizim_kelimeler, req.rakip_domain, req.hedef_domain, req.limit)


@app.post("/api/talon/migrate")
def talon_migrate(req: TalonMigrateBody):
    from app.moduller.talon_extensions import gecmis_migrate, favoriler_migrate
    hist = gecmis_migrate(req.dry_run)
    fav = favoriler_migrate(req.dry_run)
    return {"status": "aktif", "gecmis": hist, "favoriler": fav}


@app.get("/api/talon/health")
def talon_health():
    from app.moduller.talon_stack.services.talon_search_service import talon_search_service
    return talon_search_service.health()


@app.post("/api/talon/search")
def talon_search(req: TalonSearchQueryBody):
    from app.moduller.talon_stack.services.talon_search_service import talon_search_service
    q = req.query or req.seed_keyword
    if not q:
        raise HTTPException(status_code=400, detail="query gerekli")
    return talon_search_service.search_web(q, {"num_results": req.num_results})


@app.post("/api/talon/research")
def talon_research(req: TalonSearchQueryBody):
    from app.moduller.talon_stack.services.talon_search_service import talon_search_service
    q = req.query or req.seed_keyword
    if not q:
        raise HTTPException(status_code=400, detail="query gerekli")
    return talon_search_service.research_topic(q, {"num_results": req.num_results})


@app.post("/api/talon/keywords")
def talon_keywords(req: TalonSearchQueryBody):
    from app.moduller.talon_stack.services.talon_search_service import talon_search_service
    q = req.seed_keyword or req.query
    if not q:
        raise HTTPException(status_code=400, detail="seed_keyword gerekli")
    return talon_search_service.generate_keyword_ideas(q)


@app.post("/api/talon/faq")
def talon_faq(req: TalonSearchQueryBody):
    from app.moduller.talon_stack.services.talon_search_service import talon_search_service
    q = req.seed_keyword or req.query
    if not q:
        raise HTTPException(status_code=400, detail="seed_keyword gerekli")
    return talon_search_service.generate_faq_ideas(q)


@app.post("/api/talon/geo")
def talon_geo(req: TalonSearchQueryBody):
    from app.moduller.talon_stack.services.talon_search_service import talon_search_service
    q = req.location_keyword or req.query or req.seed_keyword
    if not q:
        raise HTTPException(status_code=400, detail="location_keyword gerekli")
    return talon_search_service.geo_seo_research(q)


@app.post("/api/talon/full-seo-research")
def talon_full_seo_research(req: TalonSearchQueryBody):
    from app.moduller.talon_stack.services.talon_search_service import talon_search_service
    q = req.seed_keyword or req.query
    if not q:
        raise HTTPException(status_code=400, detail="seed_keyword gerekli")
    result = talon_search_service.full_seo_research(q, {"num_results": req.num_results})
    log_module_run("talon", "Full SEO Research", req.model_dump(), {"count": len(result.get("autocompleteKeywords", []))})
    return result


@app.get("/api/talon/orchestrator/health")
def talon_orchestrator_health():
    from app.moduller.talon_orchestrator import health
    return health()


@app.post("/api/talon/orchestrator/discover")
def talon_orchestrator_discover(req: TalonOrchestratorBody):
    from app.moduller.talon_orchestrator import keyword_discovery
    if not req.seed_keyword.strip():
        raise HTTPException(status_code=400, detail="seed_keyword gerekli")
    return keyword_discovery(req.seed_keyword, req.location or None)


@app.post("/api/talon/orchestrator/intent")
def talon_orchestrator_intent(req: TalonOrchestratorBody):
    from app.moduller.talon_orchestrator import intent_classifier
    kw = (req.keyword or req.seed_keyword).strip()
    if not kw:
        raise HTTPException(status_code=400, detail="keyword gerekli")
    return {"success": True, "keyword": kw, "intent": intent_classifier(kw)}


@app.post("/api/talon/orchestrator/geo-cluster")
def talon_orchestrator_geo_cluster(req: TalonOrchestratorBody):
    from app.moduller.talon_orchestrator import geo_cluster_builder
    seed = (req.seed_keyword or req.keyword).strip()
    if not seed:
        raise HTTPException(status_code=400, detail="seed_keyword gerekli")
    return geo_cluster_builder(seed, req.location or "Kuşadası")


@app.post("/api/talon/orchestrator/competitors")
def talon_orchestrator_competitors(req: TalonOrchestratorBody):
    from app.moduller.talon_orchestrator import competitor_discovery
    kw = (req.keyword or req.seed_keyword).strip()
    if not kw:
        raise HTTPException(status_code=400, detail="keyword gerekli")
    return competitor_discovery(kw)


@app.post("/api/talon/orchestrator/serp-gap")
def talon_orchestrator_serp_gap(req: TalonOrchestratorBody):
    from app.moduller.talon_orchestrator import serp_gap_analysis
    kw = (req.keyword or req.seed_keyword).strip()
    if not kw:
        raise HTTPException(status_code=400, detail="keyword gerekli")
    return serp_gap_analysis(kw)


@app.post("/api/talon/orchestrator/content-brief")
def talon_orchestrator_content_brief(req: TalonOrchestratorBody):
    from app.moduller.talon_orchestrator import content_brief_generator, intent_classifier
    kw = (req.keyword or req.seed_keyword).strip()
    if not kw:
        raise HTTPException(status_code=400, detail="keyword gerekli")
    intent = intent_classifier(kw)
    return content_brief_generator(kw, req.location, intent)


@app.post("/api/talon/orchestrator/publish-priority")
def talon_orchestrator_publish_priority(req: TalonOrchestratorBody):
    from app.moduller.talon_orchestrator import build_keyword_record, publish_priority_score
    kw = (req.keyword or req.seed_keyword).strip()
    if not kw:
        raise HTTPException(status_code=400, detail="keyword gerekli")
    record = build_keyword_record(kw, req.location or "Kuşadası")
    return {"success": True, "keyword": kw, "record": record, "score": publish_priority_score(record)}


@app.post("/api/talon/orchestrator/full-research")
def talon_orchestrator_full_research(req: TalonOrchestratorBody):
    from app.moduller.talon_orchestrator import full_research
    if not req.seed_keyword.strip():
        raise HTTPException(status_code=400, detail="seed_keyword gerekli")
    result = full_research(req.seed_keyword, req.location or "Kuşadası", limit=req.limit)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Araştırma başarısız"))
    log_module_run("talon_orchestrator", "Full Research", req.model_dump(), {
        "keywords": len(result.get("keywords", [])),
        "astro_ready": len(result.get("astro_factory_ready", [])),
    })
    return result


@app.get("/api/talon/orchestrator/history")
def talon_orchestrator_history(limit: int = 20):
    from app.moduller.talon_orchestrator import list_history
    return list_history(limit)


@app.post("/api/kefen/analiz")
def kefen_analiz_endpoint(req: ModulRequest):
    domain = getattr(req, "domain", "")
    sonuc = rakip_backlink_analizi(domain)
    try: log_module_run("kefen", "KEFEN - Backlink Analizi", dict(req), dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "KEFEN", **sonuc}

@app.post("/api/kefen/btk")
def kefen_btk_endpoint(req: ModulRequest):
    domain = getattr(req, "domain", "")
    sonuc = btk_sikayet_gonder(domain)
    try: log_module_run("kefen", "KEFEN - BTK Şikayeti", dict(req), dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "KEFEN", **sonuc}

@app.post("/api/kefen/spam")
def kefen_spam_endpoint(req: ModulRequest):
    domain = getattr(req, "domain", "")
    adet = getattr(req, "adet", 100)
    sonuc = spam_backlink_gonder(domain, adet)
    try: log_module_run("kefen", "KEFEN - Spam Backlink", dict(req), dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "KEFEN", **sonuc}

@app.post("/api/kefen/rapor")
def kefen_rapor_endpoint(req: ModulRequest):
    domain = getattr(req, "domain", "")
    sonuc = rapor_uret(domain)
    try: log_module_run("kefen", "KEFEN - Kapsamlı Rapor", dict(req), dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "KEFEN", **sonuc}

def log_and_return(mod_id, mod_ad, req, sonuc):
    try: log_module_run(mod_id, mod_ad, dict(req), dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": mod_ad, **sonuc}

@app.post("/api/mystic")
def mystic_post(req: ModulRequest):
    return log_and_return("mystic", "Mystic - Spam Tara", req, spam_tara(getattr(req, "domain", "")))

@app.post("/api/mystic/tara")
def mystic_tara(req: ModulRequest):
    return log_and_return("mystic", "Mystic - Spam Tara", req, spam_tara(getattr(req, "domain", "")))

@app.post("/api/mystic/disavow")
def mystic_disavow(req: ModulRequest):
    return log_and_return("mystic", "Mystic - Disavow", req, disavow_olustur(getattr(req, "domain", "")))

@app.post("/api/mystic/misilleme")
def mystic_misilleme(req: ModulRequest):
    return log_and_return("mystic", "Mystic - Misilleme", req, misilleme_yap(getattr(req, "hedef", "")))

@app.post("/api/ddos")
def ddos_post(req: ModulRequest):
    sonuc = koruma_aktif(getattr(req, "url", ""))
    return log_and_return("ddos", "DDoS", req, sonuc)

@app.get("/api/ddos")
def ddos_get():
    sonuc = koruma_aktif()
    try: log_module_run("ddos", "DDoS", {}, dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "DDoS", **sonuc}

@app.get("/api/blackops")
def blackops_get():
    sonuc = aktiflestir()
    try: log_module_run("blackops", "Black Ops", {}, dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "Black Ops", **sonuc}

@app.get("/api/blackops/deactivate")
def blackops_deactivate():
    sonuc = deaktiflestir()
    try: log_module_run("blackops", "Black Ops - Deactivate", {}, dict(sonuc))
    except: pass
    return {"status": "pasif", "modul": "Black Ops", **sonuc}

@app.get("/api/modul/{mod_id}")
def modul_detay(mod_id: str):
    mod = MODUL_MAP.get(mod_id)
    if not mod:
        return {"status": "hata", "mesaj": "Modül bulunamadı"}
    return {"status": "aktif", "modul": mod["ad"], "id": mod_id, "aciklama": mod["aciklama"], "grup": mod.get("grup", "")}

@app.get("/api/modul-tarihce/{mod_id}")
def modul_tarihce(mod_id: str):
    return get_module_history(mod_id)

@app.get("/api/modul-istatistik/{mod_id}")
def modul_istatistik(mod_id: str):
    logs = get_module_history(mod_id)
    return {
        "toplam": len(logs),
        "son_calisma": logs[-1]["timestamp"] if logs else None,
        "logs": logs[-5:]
    }

@app.get("/api/son-aktiviteler")
def son_aktiviteler():
    return get_all_logs(20)

@app.delete("/api/modul-tarihce/{mod_id}")
def modul_tarihce_sil(mod_id: str):
    return delete_module_history(mod_id)

@app.get("/api/dashboard/stats")
def dashboard_stats():
    from app.moduller.wordpress_api import wp_api

    bugun = datetime.now().date().isoformat()
    logs = get_all_logs(500)
    bugun_calistirma = sum(1 for l in logs if l.get("timestamp", "")[:10] == bugun)
    aktif_ids = set(l.get("mod_id", "") for l in logs if l.get("mod_id"))

    wp = wp_api()
    wp_stats: dict = {"connected": False}
    if wp.connected:
        profiles = wp.count_post_type("companion_profile")
        stories = wp.count_post_type("erotic_story")
        gece = wp.count_post_type("gece_hayati")
        wp_stats = {
            "connected": True,
            "url": wp.status().get("url", ""),
            "profiles": profiles.get("total", 0) if profiles.get("success") else None,
            "stories": stories.get("total", 0) if stories.get("success") else None,
            "gece_hayati": gece.get("total", 0) if gece.get("success") else None,
        }

    return {
        "toplam_modul": len(MODULLER),
        "aktif_modul": max(1, len(aktif_ids)),
        "bugun_calistirma": bugun_calistirma,
        "versiyon": "3.0",
        "wordpress": wp_stats,
    }

@app.get("/api/dashboard/activities")
def dashboard_activities():
    return get_son_aktiviteler(10)

@app.get("/api/dashboard/chart")
def dashboard_chart():
    return get_gunluk_aktivite(7)

@app.post("/api/openseo/keyword")
def openseo_keyword(req: ModulRequest):
    return log_and_return("openseo", "OpenSEO - Keyword Research", req, openseo_keyword_research(getattr(req, "kelime", "")))

@app.post("/api/serpbear/track")
def serpbear_track(req: ModulRequest):
    return log_and_return("serpbear", "SerpBear - Rank Track", req, serpbear_goruntule(getattr(req, "keyword", "")))

@app.post("/api/serpbear/register")
def serpbear_register(req: ModulRequest):
    return log_and_return("serpbear", "SerpBear - Register Keyword", req, serpbear_ekle(getattr(req, "keyword", ""), getattr(req, "domain", "")))

@app.get("/api/serpbear/keywords")
def serpbear_keywords():
    return {"status": "aktif", "keywords": serpbear_liste()}

@app.post("/api/serpbear/delete")
def serpbear_delete(req: ModulRequest):
    return log_and_return("serpbear", "SerpBear - Delete Keyword", req, serpbear_sil(getattr(req, "keyword", "")))

@app.post("/api/serpbear/history")
def serpbear_history(req: ModulRequest):
    return log_and_return("serpbear", "SerpBear - History", req, serpbear_simulasyon_sonuclari(getattr(req, "keyword", "")))

@app.post("/api/serpbear/serp")
def serpbear_serp(req: ModulRequest):
    return log_and_return("serpbear", "SerpBear - SERP Snapshot", req, serpbear_simulasyon_sonuclari(getattr(req, "keyword", "")))

@app.post("/api/seointel/ai-visibility")
def seointel_visibility(req: ModulRequest):
    return log_and_return("seointel", "SEOIntel - AI Visibility", req, seointel_ai_gorunurluk(getattr(req, "marka", "")))

@app.post("/api/seointel/brand-presence")
def seointel_brand_presence(req: ModulRequest):
    return log_and_return("seointel", "SEOIntel - Brand Presence", req, seointel_olustur(getattr(req, "marka", "")))

@app.get("/api/seointel/leaderboard")
def seointel_leaderboard():
    return {"status": "aktif", "leaderboard": seointel_ai_gorunurluk("leaderboard")}

@app.post("/api/seointel/prompt")
def seointel_prompt(req: ModulRequest):
    return log_and_return("seointel", "SEOIntel - Simulate Prompt", req, seointel_olustur(getattr(req, "sorgu", "")))

@app.post("/api/seointel/backlinks")
def seointel_backlinks_endpoint(req: ModulRequest):
    return log_and_return("seointel", "SEOIntel - AI Backlinks", req, seointel_backlinks(getattr(req, "domain", "")))

@app.post("/api/dataseo/backlinks")
def dataseo_backlinks_endpoint(req: ModulRequest):
    return log_and_return("dataseo", "DataSEO - Backlink Overview", req, dataseo_backlinks(getattr(req, "domain", "")))

@app.post("/api/dataseo/backlinks/list")
def dataseo_backlinks_list(req: ModulRequest):
    return log_and_return("dataseo", "DataSEO - Backlink List", req, dataseo_backlinks(getattr(req, "domain", "")))

@app.post("/api/dataseo/backlinks/domains")
def dataseo_backlinks_domains(req: ModulRequest):
    return log_and_return("dataseo", "DataSEO - Referring Domains", req, dataseo_backlinks(getattr(req, "domain", "")))

@app.post("/api/dataseo/keyword-ideas")
def dataseo_keyword_ideas_endpoint(req: ModulRequest):
    return log_and_return("dataseo", "DataSEO - Keyword Ideas", req, dataseo_keyword_ideas(getattr(req, "kelime", "")))

@app.post("/api/dataseo/keyword-difficulty")
def dataseo_keyword_difficulty_endpoint(req: ModulRequest):
    return log_and_return("dataseo", "DataSEO - Keyword Difficulty", req, dataseo_keyword_difficulty(getattr(req, "kelime", "")))

@app.post("/api/dataseo/traffic")
def dataseo_traffic_endpoint(req: ModulRequest):
    return log_and_return("dataseo", "DataSEO - Traffic Estimate", req, dataseo_traffic(getattr(req, "domain", "")))

@app.post("/api/domain/cloudflare-import")
def domain_cf_import(req: ModulRequest):
    sonuc = domain_cloudflare_import(getattr(req, "api_token", ""), getattr(req, "api_email", ""))
    return {"status": "aktif", "modul": "Domain Manager - Cloudflare Import", **sonuc}

@app.get("/api/domain/check/{domain}")
def domain_check_availability(domain: str):
    sonuc = check_domain_availability(domain)
    return {"status": "aktif", "modul": "Domain Manager - Availability Check", **sonuc}

@app.post("/api/domain/check-bulk")
def domain_check_bulk(req: ModulRequest):
    sonuc = check_bulk_domain_availability(getattr(req, "domains", None) or getattr(req, "domainler", []))
    return {"status": "aktif", "modul": "Domain Manager - Bulk Availability", **sonuc}

@app.get("/api/free-providers/health")
def free_providers_health():
    from app.moduller.free_provider_clients import provider_health
    return {"status": "aktif", "modul": "Free Providers", **provider_health()}


class ProviderSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/provider-settings/health")
def provider_settings_health():
    from app.moduller.provider_settings import health
    return health()


@app.get("/api/provider-settings")
def provider_settings_get():
    from app.moduller.provider_settings import get_settings, health
    return {"success": True, "settings": get_settings(), "health": health()}


@app.post("/api/provider-settings")
def provider_settings_update(req: ProviderSettingsBody):
    from app.moduller.provider_settings import update_settings, health
    patch = req.model_dump(exclude_unset=True)
    settings = update_settings(patch)
    return {"success": True, "settings": settings, "health": health()}

@app.post("/api/domain/health/{domain_id}")
def domain_health(domain_id: int):
    sonuc = domain_saglik_kontrol(domain_id)
    return {"status": "aktif", "modul": "Domain Manager - Health Check", **sonuc}

@app.get("/api/domain/health-all")
def domain_health_all():
    sonuc = domain_toplu_saglik_kontrol()
    return {"status": "aktif", "modul": "Domain Manager - Toplu Health Check", **sonuc}

@app.post("/api/domain/backup")
def domain_backup(req: ModulRequest):
    sonuc = domain_yedek_al(int(getattr(req, "domain_id", 0)), getattr(req, "bulut", ""))
    return {"status": "aktif", "modul": "Domain Manager - Backup", **sonuc}

@app.post("/api/domain/restore")
def domain_restore_endpoint(req: ModulRequest):
    sonuc = domain_restore(int(getattr(req, "domain_id", 0)), int(getattr(req, "backup_id", 0)))
    return {"status": "aktif", "modul": "Domain Manager - Restore", **sonuc}

@app.get("/api/domain/backups")
@app.get("/api/domain/backups/{domain_id}")
def domain_backup_list(domain_id: int = 0):
    sonuc = domain_yedek_listele(domain_id)
    return {"status": "aktif", "modul": "Domain Manager - Backups", **sonuc}

@app.post("/api/domain/batch-delete")
def domain_batch_delete(req: ModulRequest):
    sonuc = domain_batch_sil(getattr(req, "domain_ids", []))
    return {"status": "aktif", "modul": "Domain Manager - Batch Delete", **sonuc}

@app.post("/api/domain/batch-reset")
def domain_batch_reset(req: ModulRequest):
    sonuc = domain_batch_sifirla(getattr(req, "domain_ids", []))
    return {"status": "aktif", "modul": "Domain Manager - Batch Reset", **sonuc}

@app.post("/api/domain/batch-plugin")
def domain_batch_plugin(req: ModulRequest):
    sonuc = domain_batch_plugin_yukle(getattr(req, "domain_ids", []), getattr(req, "plugin_adi", ""))
    return {"status": "aktif", "modul": "Domain Manager - Batch Plugin", **sonuc}

@app.post("/api/domain/autonomous")
def domain_autonomous(req: ModulRequest):
    sonuc = domain_otonom_kur(getattr(req, "ana_domain", ""), int(getattr(req, "adet", 10)))
    return {"status": "aktif", "modul": "Domain Manager - Autonomous Mode", **sonuc}

@app.post("/api/subdomain/talon-create")
def subdomain_talon_create(req: ModulRequest):
    sonuc = subdomain_talondan_olustur(
        int(getattr(req, "domain_id", 0)),
        getattr(req, "kelimeler", None),
        getattr(req, "parent_domain", ""),
        bool(getattr(req, "icerik_doldur", True)),
    )
    return {"status": "aktif", "modul": "Subdomain Manager - Talon Integration", **sonuc}

@app.post("/api/subdomain/batch-delete")
def subdomain_batch_delete(req: ModulRequest):
    sonuc = subdomain_batch_sil(getattr(req, "sub_ids", []))
    return {"status": "aktif", "modul": "Subdomain Manager - Batch Delete", **sonuc}

@app.post("/api/subdomain/batch-reset")
def subdomain_batch_reset(req: ModulRequest):
    sonuc = subdomain_batch_sifirla(getattr(req, "sub_ids", []))
    return {"status": "aktif", "modul": "Subdomain Manager - Batch Reset", **sonuc}

@app.post("/api/subdomain/batch-plugin")
def subdomain_batch_plugin_endpoint(req: ModulRequest):
    sonuc = subdomain_batch_plugin(getattr(req, "sub_ids", []), getattr(req, "plugin_adi", ""))
    return {"status": "aktif", "modul": "Subdomain Manager - Batch Plugin", **sonuc}

@app.post("/api/wp/site/content-fill")
def wp_content_fill(req: ModulRequest):
    sonuc = site_icerik_doldur(int(getattr(req, "domain_id", 0)))
    return {"status": "aktif", "modul": "WordPress - Auto Content Fill", **sonuc}

@app.post("/api/wp/site/batch-plugin")
def wp_batch_plugin(req: ModulRequest):
    sonuc = site_batch_plugin(getattr(req, "domain_ids", []), getattr(req, "plugin_adi", ""))
    return {"status": "aktif", "modul": "WordPress - Batch Plugin Install", **sonuc}

# ==================== ZEUS EK ENDPOINTS ====================
@app.get("/api/zeus/listele")
@app.get("/api/zeus/listele/{platform}")
def zeus_listele(platform: str = ""):
    return log_and_return("zeus", "Zeus - Parazit Listele", None, parazit_listele(platform))

@app.delete("/api/zeus/sil/{page_id}")
def zeus_sil(page_id: str):
    return log_and_return("zeus", "Zeus - Parazit Sil", None, parazit_sil(page_id))

@app.get("/api/zeus/analiz")
def zeus_analiz():
    return log_and_return("zeus", "Zeus - Platform Analiz", None, platform_analiz())

@app.get("/api/zeus/health")
def zeus_health_endpoint():
    return log_and_return("zeus", "Zeus - Health", None, zeus_health())

@app.post("/api/zeus/publish")
def zeus_publish(req: ModulRequest):
    return log_and_return(
        "zeus",
        "Zeus - Parazit Yayınla",
        req,
        parazit_yerlestir(
            getattr(req, "platform", "Medium"),
            getattr(req, "konu", "") or getattr(req, "title", ""),
            getattr(req, "hedef_url", "") or getattr(req, "url", ""),
            getattr(req, "subreddit", ""),
            getattr(req, "video_id", ""),
        ),
    )

# ==================== MYSTIC EK ENDPOINTS ====================
@app.post("/api/mystic/export")
def mystic_export_endpoint(req: ModulRequest):
    return log_and_return("mystic", "Mystic - Export", req, mystic_export(getattr(req, "domain", ""), getattr(req, "format", "csv")))

# ==================== WEB SCRAPER / LEAD SCRAPER ====================
@app.get("/api/webscraper/health")
def webscraper_health():
    from app.moduller.webscraper import health
    return health()


@app.post("/api/webscraper/crawl")
def webscraper_crawl(req: ModulRequest):
    from app.moduller.webscraper import kazi
    return kazi(
        getattr(req, "url", ""),
        int(getattr(req, "derinlik", 1) or 1),
        int(getattr(req, "max_pages", 10) or 10),
    )


@app.post("/api/webscraper/export")
def webscraper_export(req: ModulRequest):
    from app.moduller.webscraper import export
    return export(
        getattr(req, "url", ""),
        getattr(req, "format", "csv"),
        int(getattr(req, "derinlik", 1) or 1),
    )


@app.get("/api/webscraper/jobs")
def webscraper_jobs(limit: int = 20):
    from app.moduller.webscraper import list_jobs
    return list_jobs(limit)


@app.get("/api/leadscraper/health")
def leadscraper_health():
    from app.moduller.leadscraper import health
    return health()


@app.post("/api/leadscraper/collect")
def leadscraper_collect(req: ModulRequest):
    from app.moduller.leadscraper import topla
    return topla(
        getattr(req, "kelime", ""),
        int(getattr(req, "adet", 50) or 50),
        getattr(req, "url", ""),
    )


@app.post("/api/leadscraper/export")
def leadscraper_export(req: ModulRequest):
    from app.moduller.leadscraper import export_leads
    return export_leads(
        getattr(req, "kelime", ""),
        int(getattr(req, "adet", 50) or 50),
        getattr(req, "url", ""),
        getattr(req, "format", "csv"),
    )


# ==================== OPPORTUNITY ENGINE ====================
class OpportunityAnalyzeProjectBody(BaseModel):
    project_id: str = ""
    network_id: str = ""
    location: str = ""
    seed_keyword: str = ""


class OpportunityAnalyzeDomainBody(BaseModel):
    domain: str = ""
    network_id: str = ""


class OpportunityPlanBody(BaseModel):
    project_id: str = ""
    network_id: str = ""


class OpportunityExportBody(BaseModel):
    project_id: str = ""
    report_type: str = "overview"


class OpportunitySettingsBody(BaseModel):
    quick_win_threshold: int | None = None
    high_impact_threshold: int | None = None
    low_competition_max_difficulty: int | None = None


@app.get("/api/opportunity/health")
def opportunity_health():
    from app.moduller.opportunity_engine import opportunity_engine
    return opportunity_engine.health()


@app.get("/api/opportunity/dashboard")
def opportunity_dashboard(project_id: str = ""):
    from app.moduller.opportunity_engine import opportunity_engine
    return opportunity_engine.dashboard(project_id)


@app.post("/api/opportunity/analyze-project")
def opportunity_analyze_project(req: OpportunityAnalyzeProjectBody):
    from app.moduller.opportunity_engine import opportunity_engine
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = opportunity_engine.analyze_project(
        req.project_id.strip(),
        network_id=req.network_id,
        location=req.location,
        seed_keyword=req.seed_keyword,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("mesaj") or result.get("error"))
    _brain_emit("/api/opportunity/analyze-project", req, result, module="opportunity_engine")
    return result


@app.post("/api/opportunity/analyze-domain")
def opportunity_analyze_domain(req: OpportunityAnalyzeDomainBody):
    from app.moduller.opportunity_engine import opportunity_engine
    if not req.domain.strip():
        raise HTTPException(status_code=400, detail="domain gerekli")
    result = opportunity_engine.analyze_domain(req.domain.strip(), network_id=req.network_id)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("mesaj") or result.get("error"))
    return result


@app.get("/api/opportunity/keywords")
def opportunity_keywords(project_id: str = ""):
    from app.moduller.opportunity_engine import opportunity_engine
    return opportunity_engine.list_keywords(project_id)


@app.get("/api/opportunity/entities")
def opportunity_entities(project_id: str = ""):
    from app.moduller.opportunity_engine import opportunity_engine
    return opportunity_engine.list_entities(project_id)


@app.get("/api/opportunity/geo")
def opportunity_geo(project_id: str = "", location: str = ""):
    from app.moduller.opportunity_engine import opportunity_engine
    result = opportunity_engine.list_geo(project_id, location)
    if not result.get("success") and result.get("error") == "provider_missing":
        raise HTTPException(status_code=422, detail=result.get("mesaj") or result.get("error"))
    return result


@app.get("/api/opportunity/authority")
def opportunity_authority(network_id: str = ""):
    from app.moduller.opportunity_engine import opportunity_engine
    result = opportunity_engine.list_authority(network_id)
    if not result.get("success") and result.get("error") == "provider_missing":
        raise HTTPException(status_code=422, detail=result.get("mesaj") or result.get("error"))
    return result


@app.get("/api/opportunity/ai")
def opportunity_ai(project_id: str = ""):
    from app.moduller.opportunity_engine import opportunity_engine
    result = opportunity_engine.list_ai(project_id)
    if not result.get("success") and result.get("error") == "provider_missing":
        raise HTTPException(status_code=422, detail=result.get("mesaj") or result.get("error"))
    return result


@app.get("/api/opportunity/quickwins")
def opportunity_quickwins(project_id: str = ""):
    from app.moduller.opportunity_engine import opportunity_engine
    return opportunity_engine.quick_wins(project_id)


@app.post("/api/opportunity/one-click-plan")
def opportunity_one_click_plan(req: OpportunityPlanBody):
    from app.moduller.opportunity_engine import opportunity_engine
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = opportunity_engine.generate_one_click_plan(req.project_id.strip(), req.network_id)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error") or result.get("mesaj"))
    _brain_emit("/api/opportunity/one-click-plan", req, result, module="opportunity_engine")
    return result


@app.get("/api/opportunity/settings")
def opportunity_get_settings():
    from app.moduller.opportunity_engine import opportunity_engine
    return {"success": True, "settings": opportunity_engine.get_settings()}


@app.post("/api/opportunity/settings")
def opportunity_update_settings(req: OpportunitySettingsBody):
    from app.moduller.opportunity_engine import opportunity_engine
    return {"success": True, "settings": opportunity_engine.update_settings(req.model_dump(exclude_unset=True))}


@app.post("/api/opportunity/export-report")
def opportunity_export_report(req: OpportunityExportBody):
    from app.moduller.opportunity_engine import opportunity_engine
    return opportunity_engine.export_report(req.project_id, req.report_type)


# ==================== HIVE BRAIN / MEMORY ENGINE ====================
class BrainRecordEventBody(BaseModel):
    event_type: str = "module_action"
    module: str = "manual"
    project_id: str = ""
    domain: str = ""
    keyword: str = ""
    entity: str = ""
    content_id: str = ""
    status: str = "ok"
    result: dict = {}
    metadata: dict = {}
    reason: str = ""


class BrainRecordDecisionBody(BaseModel):
    module: str = "manual"
    recommendation: str = ""
    reason: str = ""
    project_id: str = ""
    domain: str = ""
    keyword: str = ""
    applied: bool | None = None
    outcome: str = ""
    metadata: dict = {}


class BrainExportBody(BaseModel):
    project_id: str = ""


@app.get("/api/hive-brain/health")
def hive_brain_health():
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.health()


@app.get("/api/hive-brain/dashboard")
def hive_brain_dashboard():
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.dashboard()


@app.get("/api/hive-brain/events")
def hive_brain_events(
    limit: int = 50,
    project_id: str = "",
    domain: str = "",
    keyword: str = "",
    event_type: str = "",
    module: str = "",
):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.list_events(limit, project_id, domain, keyword, event_type, module)


@app.get("/api/hive-brain/timeline")
def hive_brain_timeline(days: int = 14, project_id: str = ""):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.get_timeline(days, project_id)


@app.get("/api/hive-brain/projects")
def hive_brain_projects():
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.list_projects()


@app.get("/api/hive-brain/project/{project_id}")
def hive_brain_project_memory(project_id: str):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.get_project_memory(project_id)


@app.get("/api/hive-brain/project/{project_id}/story")
def hive_brain_project_story(project_id: str):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.get_project_story(project_id)


@app.get("/api/hive-brain/domain/{domain}")
def hive_brain_domain_memory(domain: str):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.get_domain_memory(domain)


@app.get("/api/hive-brain/keyword/{keyword}")
def hive_brain_keyword_memory(keyword: str):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.get_keyword_memory(keyword)


@app.get("/api/hive-brain/decisions")
def hive_brain_decisions(limit: int = 30, project_id: str = ""):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.list_decisions(limit, project_id)


@app.post("/api/hive-brain/record-event")
def hive_brain_record_event(req: BrainRecordEventBody):
    from app.moduller.hive_brain_engine import hive_brain
    if not req.module.strip():
        raise HTTPException(status_code=400, detail="module gerekli")
    return hive_brain.record_event(
        req.event_type,
        req.module,
        project_id=req.project_id,
        domain=req.domain,
        keyword=req.keyword,
        entity=req.entity,
        content_id=req.content_id,
        status=req.status,
        result=req.result,
        metadata=req.metadata,
        reason=req.reason,
    )


@app.post("/api/hive-brain/record-decision")
def hive_brain_record_decision(req: BrainRecordDecisionBody):
    from app.moduller.hive_brain_engine import hive_brain
    if not req.recommendation.strip():
        raise HTTPException(status_code=400, detail="recommendation gerekli")
    return hive_brain.record_decision(
        req.module,
        req.recommendation,
        req.reason,
        project_id=req.project_id,
        domain=req.domain,
        keyword=req.keyword,
        applied=req.applied,
        outcome=req.outcome,
        metadata=req.metadata,
    )


@app.post("/api/hive-brain/backfill/logs")
def hive_brain_backfill_logs(limit: int = 300):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.backfill_from_activity_logs(limit)


@app.post("/api/hive-brain/backfill/states")
def hive_brain_backfill_states():
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.backfill_from_engine_states()


@app.post("/api/hive-brain/export-report")
def hive_brain_export_report(req: BrainExportBody):
    from app.moduller.hive_brain_engine import hive_brain
    return hive_brain.export_report(req.project_id)


# ==================== RANKTRACKER EK ENDPOINTS ====================
@app.get("/api/ranktracker/health")
def ranktracker_health():
    from app.moduller.ranktracker import health
    return health()


@app.post("/api/ranktracker/keyword")
def ranktracker_kaydet(req: ModulRequest):
    return log_and_return("ranktracker", "Rank Tracker - Keyword Kaydet", req, keyword_kaydet(getattr(req, "kelime", ""), getattr(req, "domain", "")))

@app.delete("/api/ranktracker/keyword/{kelime}")
def ranktracker_sil(kelime: str):
    import urllib.parse; kelime = urllib.parse.unquote(kelime)
    return log_and_return("ranktracker", "Rank Tracker - Keyword Sil", None, keyword_sil(kelime))

@app.get("/api/ranktracker/keywordlar")
def ranktracker_listele():
    return log_and_return("ranktracker", "Rank Tracker - Keyword Listele", None, keyword_listele())

@app.post("/api/ranktracker/toplu")
def ranktracker_toplu(req: ModulRequest):
    return log_and_return("ranktracker", "Rank Tracker - Toplu Kontrol", req, toplu_kontrol(getattr(req, "kelimeler", [])))

@app.post("/api/ranktracker/export")
def ranktracker_export_endpoint(req: ModulRequest):
    return log_and_return("ranktracker", "Rank Tracker - Export", req, ranktracker_export(getattr(req, "kelime", ""), getattr(req, "format", "csv")))

# ==================== EKŞİSÖZLÜK EK ENDPOINTS ====================
@app.get("/api/eksisozluk/listele")
def eksisozluk_listele():
    return log_and_return("eksisozluk", "Ekşisözlük - Entry Listele", None, entry_listele())

@app.delete("/api/eksisozluk/sil/{entry_id}")
def eksisozluk_sil(entry_id: int):
    return log_and_return("eksisozluk", "Ekşisözlük - Entry Sil", None, entry_sil(entry_id))

@app.get("/api/eksisozluk/analiz")
def eksisozluk_analiz():
    return log_and_return("eksisozluk", "Ekşisözlük - Entry Analiz", None, entry_analiz())

# ==================== MEDIUM BOT ====================


class MediumPublishBody(BaseModel):
    title: str = ""
    content: str = ""
    tags: list[str] = Field(default_factory=list)


class MediumCommentBody(BaseModel):
    article_url: str = ""
    comment_text: str = ""


@app.get("/api/medium-bot/health")
def medium_bot_health():
    from app.moduller.medium_bot import health
    return health()


@app.get("/api/medium-bot/me")
def medium_bot_me():
    from app.moduller.medium_bot import get_me
    return get_me()


@app.post("/api/medium-bot/publish")
def medium_bot_publish(req: MediumPublishBody):
    from app.moduller.medium_bot import publish_to_medium
    return publish_to_medium(req.title, req.content, req.tags)


@app.post("/api/medium-bot/comment")
def medium_bot_comment(req: MediumCommentBody):
    from app.moduller.medium_bot import comment_on_article
    return comment_on_article(req.article_url, req.comment_text)


@app.get("/api/medium-bot/activity")
def medium_bot_activity(limit: int = 50):
    from app.moduller.medium_bot import list_activity
    return list_activity(limit)


# ==================== SEO POISONING ====================


class SEOPoisoningBody(BaseModel):
    target_domain: str = ""
    keywords: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)


@app.get("/api/seo-poisoning/health")
def seo_poisoning_health():
    from app.moduller.seo_poisoning import health
    return health()


@app.post("/api/seo-poisoning/generate")
def seo_poisoning_generate(req: SEOPoisoningBody):
    from app.moduller.seo_poisoning import generate_negative_content
    return generate_negative_content(req.target_domain, req.keywords or None)


@app.post("/api/seo-poisoning/publish")
def seo_poisoning_publish(req: dict):
    from app.moduller.seo_poisoning import publish_to_platforms
    content = req.get("content") or req
    platforms = req.get("platforms")
    return publish_to_platforms(content, platforms)


@app.post("/api/seo-poisoning/campaign")
def seo_poisoning_campaign(req: SEOPoisoningBody):
    from app.moduller.seo_poisoning import run_campaign
    return run_campaign(req.target_domain, req.keywords or None, req.platforms or None)


@app.get("/api/seo-poisoning/campaigns")
def seo_poisoning_campaigns(limit: int = 30):
    from app.moduller.seo_poisoning import list_campaigns
    return list_campaigns(limit)


# ==================== MAPS (SİMÜLASYON) ====================


class MapsSimulateBody(BaseModel):
    place_name: str = ""
    isletme: str = ""
    rating: int = 5
    puan: int = 0
    comment: str = ""
    adet: int = 1


@app.get("/api/maps/health")
def maps_health():
    from app.moduller.maps import health
    return health()


@app.post("/api/maps/simulate")
def maps_simulate(req: MapsSimulateBody):
    from app.moduller.maps import simulate_review
    place = (req.place_name or req.isletme or "").strip()
    rating = req.rating or req.puan or 5
    return simulate_review(place, rating, req.comment)


# ==================== REDDIT EK ENDPOINTS ====================
@app.post("/api/reddit/post")
def reddit_post_ac_endpoint(req: ModulRequest):
    return log_and_return("reddit", "Reddit - Post Aç", req, post_ac(getattr(req, "konu", ""), getattr(req, "icerik", "")))

@app.get("/api/reddit/yorumlar")
@app.get("/api/reddit/yorumlar/{subreddit}")
def reddit_yorum_listele_endpoint(subreddit: str = ""):
    return log_and_return("reddit", "Reddit - Yorum Listele", None, reddit_yorum_listele(subreddit))

@app.delete("/api/reddit/yorum/{yorum_id}")
def reddit_yorum_sil_endpoint(yorum_id: int):
    return log_and_return("reddit", "Reddit - Yorum Sil", None, reddit_yorum_sil(yorum_id))

@app.get("/api/reddit/postlar")
def reddit_post_listele_endpoint():
    return log_and_return("reddit", "Reddit - Post Listele", None, post_listele())

# ==================== REDDIRECT MCP ====================
from app.moduller.reddit_mcp import reddit_mcp


class RedditMCPCommentBody(BaseModel):
    post_url: str
    text: str


class RedditMCPPostBody(BaseModel):
    subreddit: str
    title: str
    text: str


@app.get("/api/reddit/mcp/status")
def reddit_mcp_status():
    try:
        session = reddit_mcp.check_session()
        tools = reddit_mcp.list_tools()
        return {"success": True, "session": session, "tools_count": len(tools), "engine": "reddirect"}
    except HTTPException as e:
        return {"success": False, "error": e.detail, "engine": "reddirect"}


@app.get("/api/reddit/mcp/tools")
def reddit_mcp_tools():
    return {"tools": reddit_mcp.list_tools()}


@app.post("/api/reddit/authorize")
def reddit_mcp_authorize():
    result = reddit_mcp.authorize()
    try:
        log_module_run("reddit", "Reddirect authorize", {}, result)
    except Exception:
        pass
    return {"success": True, "result": result, "message": "Tarayıcıda Reddit girişi tamamlayın (~24 saat geçerli)"}


@app.get("/api/reddit/search")
def reddit_mcp_search(query: str, limit: int = 20, subreddit: str = ""):
    if not query.strip():
        raise HTTPException(status_code=400, detail="query gerekli")
    result = reddit_mcp.search(query.strip(), limit=limit, subreddit=subreddit)
    try:
        log_module_run("reddit", "Reddirect search", {"query": query}, {"count": len(result.get("results", []))})
    except Exception:
        pass
    return result


@app.get("/api/reddit/subreddit")
def reddit_mcp_subreddit(subreddit: str, limit: int = 20, sort: str = "hot"):
    if not subreddit.strip():
        raise HTTPException(status_code=400, detail="subreddit gerekli")
    result = reddit_mcp.browse_subreddit(subreddit.strip(), limit=limit, sort=sort)
    return result


@app.get("/api/reddit/post")
def reddit_mcp_get_post(post_url: str):
    if not post_url.strip():
        raise HTTPException(status_code=400, detail="post_url gerekli")
    return reddit_mcp.get_post(post_url.strip())


@app.post("/api/reddit/comment")
def reddit_mcp_comment(req: RedditMCPCommentBody):
    if not req.post_url.strip() or not req.text.strip():
        raise HTTPException(status_code=400, detail="post_url ve text gerekli")
    result = reddit_mcp.submit_comment(req.post_url.strip(), req.text.strip())
    try:
        log_module_run("reddit", "Reddirect submit_comment", {"url": req.post_url[:80]}, result)
    except Exception:
        pass
    return result


@app.post("/api/reddit/mcp/post")
def reddit_mcp_create_post(req: RedditMCPPostBody):
    if not req.subreddit.strip() or not req.title.strip():
        raise HTTPException(status_code=400, detail="subreddit ve title gerekli")
    result = reddit_mcp.submit_post(req.subreddit.strip(), req.title.strip(), req.text.strip())
    try:
        log_module_run("reddit", "Reddirect submit_post", {"subreddit": req.subreddit}, result)
    except Exception:
        pass
    return result

# ==================== MAPS EK ENDPOINTS ====================
@app.get("/api/maps/yorumlar")
@app.get("/api/maps/yorumlar/{isletme}")
def maps_yorum_listele_endpoint(isletme: str = ""):
    return log_and_return("maps", "Maps - Yorum Listele", None, maps_yorum_listele(isletme))

@app.get("/api/maps/istatistik")
@app.get("/api/maps/istatistik/{isletme}")
def maps_istatistik_endpoint(isletme: str = ""):
    return log_and_return("maps", "Maps - İstatistik", None, yorum_istatistik(isletme))

@app.post("/api/maps/hedef")
def maps_hedef_ekle_endpoint(req: ModulRequest):
    return log_and_return("maps", "Maps - Hedef Ekle", req, maps_hedef_ekle(getattr(req, "isletme", ""), getattr(req, "adres", "")))

@app.post("/api/maps/export")
def maps_export_endpoint(req: ModulRequest):
    return log_and_return("maps", "Maps - Export", req, maps_export(getattr(req, "isletme", ""), getattr(req, "format", "csv")))

# ==================== BTK EK ENDPOINTS ====================
@app.post("/api/btk/sorgula")
def btk_sorgula_endpoint(req: ModulRequest):
    return log_and_return("btk", "BTK - Şikayet Sorgula", req, sikayet_sorgula(getattr(req, "referans_no", "")))

@app.get("/api/btk/listele")
def btk_listele():
    return log_and_return("btk", "BTK - Şikayet Listele", None, sikayet_listele())

@app.post("/api/btk/iptal")
def btk_iptal_endpoint(req: ModulRequest):
    return log_and_return("btk", "BTK - Şikayet İptal", req, sikayet_iptal(int(getattr(req, "sikayet_id", 0))))

@app.get("/api/btk/istatistik")
def btk_istatistik_endpoint():
    return log_and_return("btk", "BTK - İstatistik", None, btk_istatistik())

# ==================== EXPIRED DOMAIN EK ENDPOINTS ====================
@app.post("/api/expireddomain/kaydet")
def expireddomain_kaydet(req: ModulRequest):
    return log_and_return("expireddomain", "Expired Domain - Kaydet", req, domain_kaydet(getattr(req, "domain", ""), int(getattr(req, "dr", 0))))


@app.post("/api/expireddomain/check")
def expireddomain_check(req: ModulRequest):
    from app.moduller.expireddomain import check_domain
    domain = getattr(req, "domain", "") or getattr(req, "kelime", "")
    if not domain.strip():
        raise HTTPException(status_code=400, detail="domain gerekli")
    return log_and_return("expireddomain", "Expired Domain - Check", req, check_domain(domain.strip()))


@app.post("/api/expireddomain/check-bulk")
def expireddomain_check_bulk(req: ModulRequest):
    from app.moduller.expireddomain import check_bulk_domains
    domains = getattr(req, "domains", None) or getattr(req, "domain_list", None) or []
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(",") if d.strip()]
    if not domains:
        raise HTTPException(status_code=400, detail="domains listesi gerekli")
    return log_and_return("expireddomain", "Expired Domain - Bulk Check", req, {"results": check_bulk_domains(domains)})


@app.get("/api/expireddomain/health")
def expireddomain_health():
    from app.moduller.expireddomain import health
    return health()

@app.get("/api/expireddomain/listele")
def expireddomain_listele():
    return log_and_return("expireddomain", "Expired Domain - Listele", None, expired_domain_listele())

@app.delete("/api/expireddomain/sil/{domain}")
def expireddomain_sil(domain: str):
    import urllib.parse; domain = urllib.parse.unquote(domain)
    return log_and_return("expireddomain", "Expired Domain - Sil", None, domain_sil(domain))

@app.post("/api/expireddomain/export")
def expireddomain_export_endpoint(req: ModulRequest):
    return log_and_return("expireddomain", "Expired Domain - Export", req, expired_export(getattr(req, "kelime", ""), getattr(req, "format", "csv")))


@app.get("/api/expireddomain/dashboard")
def expireddomain_dashboard_endpoint():
    from app.moduller.expireddomain import dashboard
    return dashboard()


@app.get("/api/expireddomain/expiring")
def expireddomain_expiring_endpoint(within_days: int = 90):
    from app.moduller.expireddomain import list_expiring
    return list_expiring(within_days)


@app.post("/api/expireddomain/expiry/refresh")
def expireddomain_expiry_refresh(req: ModulRequest):
    from app.moduller.expireddomain import refresh_expiry_watch
    domain = getattr(req, "domain", "") or ""
    return log_and_return("expireddomain", "Expired Domain - Expiry Refresh", req, refresh_expiry_watch(domain or None))


@app.get("/api/expireddomain/expiry/{domain}")
def expireddomain_expiry_check(domain: str):
    import urllib.parse
    from app.moduller.expireddomain import check_expiry
    return check_expiry(urllib.parse.unquote(domain))


@app.get("/api/expireddomain/authority/{domain}")
def expireddomain_authority(domain: str):
    import urllib.parse
    from app.moduller.expireddomain import discover_authority
    return discover_authority(urllib.parse.unquote(domain))


@app.post("/api/expireddomain/score")
def expireddomain_score(req: ModulRequest):
    from app.moduller.expireddomain import compute_domain_score
    domain = getattr(req, "domain", "") or getattr(req, "kelime", "")
    keyword = getattr(req, "keyword", "") or ""
    if not domain.strip():
        raise HTTPException(status_code=400, detail="domain gerekli")
    return log_and_return("expireddomain", "Expired Domain - Score", req, compute_domain_score(domain.strip(), keyword))


@app.get("/api/expireddomain/scores")
def expireddomain_scores():
    from app.moduller.expireddomain import list_scores
    return list_scores()


@app.get("/api/expireddomain/watchlist")
def expireddomain_watchlist_endpoint():
    from app.moduller.expireddomain import watchlist
    return watchlist()


@app.get("/api/expireddomain/integrations")
def expireddomain_integrations():
    from app.moduller.expireddomain import hive_integrations
    return hive_integrations()


@app.get("/api/expireddomain/reports")
def expireddomain_reports(report_type: str = "overview"):
    from app.moduller.expireddomain import reports
    return reports(report_type)

# ==================== DATA MINER ENGINE ====================
@app.get("/api/data-miner/health")
def data_miner_health():
    from app.moduller.data_miner_engine import data_miner_engine
    return data_miner_engine.health()


@app.get("/api/data-miner/dashboard")
def data_miner_dashboard():
    from app.moduller.data_miner_engine import data_miner_engine
    return data_miner_engine.dashboard()


@app.post("/api/data-miner/crawl-url")
def data_miner_crawl_url(req: ModulRequest):
    from app.moduller.data_miner_engine import data_miner_engine
    url = getattr(req, "url", "") or getattr(req, "kelime", "")
    engine = getattr(req, "engine", "auto") or "auto"
    if not str(url).strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    result = data_miner_engine.crawl_url(str(url).strip(), engine=engine)
    return log_and_return("data_miner_engine", "Data Miner - Crawl URL", req, result)


@app.post("/api/data-miner/crawl-keyword")
def data_miner_crawl_keyword(req: ModulRequest):
    from app.moduller.data_miner_engine import data_miner_engine
    keyword = getattr(req, "keyword", "") or getattr(req, "kelime", "")
    limit = int(getattr(req, "limit", 5) or 5)
    engine = getattr(req, "engine", "auto") or "auto"
    if not str(keyword).strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = data_miner_engine.crawl_keyword(str(keyword).strip(), limit=limit, engine=engine)
    return log_and_return("data_miner_engine", "Data Miner - Crawl Keyword", req, result)


@app.post("/api/data-miner/crawl-domain")
def data_miner_crawl_domain(req: ModulRequest):
    from app.moduller.data_miner_engine import data_miner_engine
    domain = getattr(req, "domain", "") or getattr(req, "url", "")
    limit = int(getattr(req, "limit", 8) or 8)
    engine = getattr(req, "engine", "auto") or "auto"
    if not str(domain).strip():
        raise HTTPException(status_code=400, detail="domain gerekli")
    result = data_miner_engine.crawl_domain(str(domain).strip(), limit=limit, engine=engine)
    return log_and_return("data_miner_engine", "Data Miner - Crawl Domain", req, result)


@app.get("/api/data-miner/jobs")
def data_miner_jobs(limit: int = 50):
    from app.moduller.data_miner_engine import data_miner_engine
    return data_miner_engine.list_jobs(limit)


@app.get("/api/data-miner/results/{job_id}")
def data_miner_results(job_id: str):
    import urllib.parse
    from app.moduller.data_miner_engine import data_miner_engine
    return data_miner_engine.get_results(urllib.parse.unquote(job_id))


@app.get("/api/data-miner/datasets")
def data_miner_datasets():
    from app.moduller.data_miner_engine import data_miner_engine
    return data_miner_engine.list_datasets()


@app.get("/api/data-miner/settings")
def data_miner_settings_get():
    from app.moduller.data_miner_engine import data_miner_engine
    return data_miner_engine.get_settings()


@app.post("/api/data-miner/settings")
def data_miner_settings_post(req: ModulRequest):
    from app.moduller.data_miner_engine import data_miner_engine
    patch = req.model_dump() if hasattr(req, "model_dump") else dict(req)
    return log_and_return("data_miner_engine", "Data Miner - Settings", req, data_miner_engine.update_settings(patch))


@app.post("/api/data-miner/export-report")
def data_miner_export_report(req: ModulRequest):
    from app.moduller.data_miner_engine import data_miner_engine
    job_id = getattr(req, "job_id", "") or ""
    fmt = getattr(req, "format", "json") or "json"
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id gerekli")
    return log_and_return("data_miner_engine", "Data Miner - Export", req, data_miner_engine.export_report(job_id, fmt))


@app.get("/api/data-miner/integrations")
def data_miner_integrations():
    from app.moduller.data_miner_engine import data_miner_engine
    return data_miner_engine.hive_integrations()

# ==================== BACKLINK HIJACKER EK ENDPOINTS ====================
@app.get("/api/backlinkhijacker/listele")
def backlinkhijacker_listele():
    return log_and_return("backlinkhijacker", "Backlink Hijacker - Çalınan Listele", None, calinan_listele())

@app.get("/api/backlinkhijacker/analiz")
def backlinkhijacker_analiz():
    return log_and_return("backlinkhijacker", "Backlink Hijacker - Analiz", None, hijacker_analiz())

@app.get("/api/backlinkhijacker/health")
def backlinkhijacker_health_endpoint():
    return log_and_return("backlinkhijacker", "Backlink Hijacker - Health", None, hijacker_health())

@app.post("/api/backlinkhijacker/broken-links")
def backlinkhijacker_broken_links(req: ModulRequest):
    return log_and_return(
        "backlinkhijacker",
        "Backlink Hijacker - Kırık Backlink Bul",
        req,
        find_broken_backlinks(getattr(req, "domain", "")),
    )

@app.post("/api/backlinkhijacker/steal")
def backlinkhijacker_steal(req: ModulRequest):
    return log_and_return(
        "backlinkhijacker",
        "Backlink Hijacker - Outreach Kaydı",
        req,
        steal_backlink(
            getattr(req, "source_url", "") or getattr(req, "url", ""),
            getattr(req, "target_url", "") or getattr(req, "hedef_url", ""),
            getattr(req, "broken_url", ""),
        ),
    )

@app.post("/api/backlinkhijacker/tara")
def backlinkhijacker_tara(req: ModulRequest):
    return log_and_return("backlinkhijacker", "Backlink Hijacker - Hedef Tara", req, hedef_tara(getattr(req, "domain", "")))

@app.post("/api/backlinkhijacker/export")
def backlinkhijacker_export_endpoint(req: ModulRequest):
    return log_and_return("backlinkhijacker", "Backlink Hijacker - Export", req, hijacker_export(getattr(req, "domain", ""), getattr(req, "format", "csv")))

# ==================== SPAM BACKLINK EK ENDPOINTS ====================
@app.get("/api/spambacklink/listele")
def spambacklink_listele():
    return log_and_return("spambacklink", "Spam Backlink - Zehirleme Listele", None, zehirleme_listele())

@app.post("/api/spambacklink/hedef")
def spambacklink_hedef_ekle_endpoint(req: ModulRequest):
    return log_and_return("spambacklink", "Spam Backlink - Hedef Ekle", req, spam_hedef_ekle(getattr(req, "domain", ""), getattr(req, "aciklama", "")))

@app.get("/api/spambacklink/hedefler")
def spambacklink_hedef_listele():
    return log_and_return("spambacklink", "Spam Backlink - Hedef Listele", None, spam_hedef_listele())

@app.get("/api/spambacklink/rapor")
def spambacklink_rapor():
    return log_and_return("spambacklink", "Spam Backlink - Rapor", None, spam_rapor())

# ==================== API HUNTER ULTRA EK ENDPOINTS ====================
@app.post("/api/apihunter/tara")
def apihunter_tara_endpoint(req: ModulRequest):
    return log_and_return("apihunter", "API Hunter - Tarama", req, tam_tarama(getattr(req, "kelime", ""), getattr(req, "domain", ""), getattr(req, "kaynaklar", None)))

@app.post("/api/apihunter/dogrula")
def apihunter_dogrula_endpoint(req: ModulRequest):
    return log_and_return("apihunter", "API Hunter - Doğrulama", req, dogrula(getattr(req, "bulunanlar", None)))

@app.get("/api/apihunter/listele")
def apihunter_listele_endpoint():
    return log_and_return("apihunter", "API Hunter - Listele", None, apihunter_listele())

@app.get("/api/apihunter/rapor")
def apihunter_rapor_endpoint():
    return log_and_return("apihunter", "API Hunter - Rapor", None, apihunter_rapor())

@app.delete("/api/apihunter/temizle")
def apihunter_temizle_endpoint():
    return log_and_return("apihunter", "API Hunter - Temizle", None, apihunter_temizle())

@app.post("/api/apihunter/hedef")
def apihunter_hedef_ekle_endpoint(req: ModulRequest):
    return log_and_return("apihunter", "API Hunter - Hedef Ekle", req, apihunter_hedef_ekle(getattr(req, "domain", ""), getattr(req, "aciklama", "")))

@app.get("/api/apihunter/hedefler")
def apihunter_hedef_listele_endpoint():
    return log_and_return("apihunter", "API Hunter - Hedef Listele", None, apihunter_hedef_listele())

@app.delete("/api/apihunter/hedef/{domain}")
def apihunter_hedef_sil_endpoint(domain: str):
    import urllib.parse; domain = urllib.parse.unquote(domain)
    return log_and_return("apihunter", "API Hunter - Hedef Sil", None, apihunter_hedef_sil(domain))

@app.post("/api/apihunter/export")
def apihunter_export_endpoint(req: ModulRequest):
    return log_and_return("apihunter", "API Hunter - Export", req, apihunter_export(getattr(req, "format", "csv")))

# ==================== ANALYTICS EXTRA ====================
class GA4SetupBody(BaseModel):
    measurement_id: str = ""
    property_id: str = ""
    sync_wordpress: bool = True


@app.get("/api/analytics/ga-status")
def analytics_ga_status():
    from app import config
    from app.moduller.ga4_data import data_api_ready
    from app.moduller.wordpress_api import wp_api

    mid = (config.get("GA4_MEASUREMENT_ID") or "").strip()
    prop = (config.get("GA4_PROPERTY_ID") or "").strip()
    gsc_url = (config.get("GSC_SITE_URL") or "").strip()
    api_ready = data_api_ready()
    wp = wp_api()
    wp_ga = ""
    if wp.connected:
        settings = wp.get_settings()
        if settings.get("success") and settings.get("settings"):
            wp_ga = settings["settings"].get("ga4_measurement_id", "") or ""
    return {
        "ga4_configured": bool(mid),
        "measurement_id": mid,
        "property_id": prop,
        "gsc_site_url": gsc_url,
        "wp_connected": wp.connected,
        "wp_ga4_measurement_id": wp_ga,
        "site_tracking_active": bool(mid or wp_ga),
        "data_api": api_ready,
        "analytics_hub_mode": "live" if api_ready.get("ready") else "tracking_only",
        "ga_console_url": "https://analytics.google.com/",
        "gsc_console_url": "https://search.google.com/search-console",
    }


@app.get("/api/analytics/ga-realtime")
def analytics_ga_realtime():
    from app.moduller.ga4_data import get_realtime
    return get_realtime()


@app.get("/api/analytics/ga-chart")
def analytics_ga_chart(days: int = 7):
    from app.moduller.ga4_data import get_chart
    return get_chart(days=days)


@app.get("/api/analytics/ga-top-pages")
def analytics_ga_top_pages(limit: int = 10):
    from app.moduller.ga4_data import get_top_pages
    return get_top_pages(limit=limit)


@app.post("/api/analytics/ga-credentials")
async def analytics_ga_credentials(file: UploadFile = File(...)):
    from app.moduller.ga4_data import save_service_account_json
    content = await file.read()
    result = save_service_account_json(content)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Kayıt başarısız"))
    return result


@app.post("/api/analytics/ga-discover")
def analytics_ga_discover():
    from app.moduller.ga4_data import discover_property_id
    result = discover_property_id()
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Mülk bulunamadı"))
    return result


@app.post("/api/analytics/ga-setup")
def analytics_ga_setup(req: GA4SetupBody):
    from app.moduller.api_key_manager import set_key
    from app.moduller.wordpress_api import wp_api

    mid = req.measurement_id.strip().upper()
    if mid and not mid.startswith("G-"):
        raise HTTPException(status_code=400, detail="Measurement ID G- ile başlamalı (ör. G-ABC123XYZ)")
    if mid:
        set_key("ga4_measurement_id", mid)
    if req.property_id.strip():
        set_key("ga4_property_id", req.property_id.strip())

    wp_sync = None
    if req.sync_wordpress and mid:
        wp = wp_api()
        if not wp.connected:
            wp_sync = {"success": False, "error": "WP bağlantısı yok — önce WP Manager'dan giriş yap"}
        else:
            wp_sync = wp.update_settings(ga4_measurement_id=mid)

    return {
        "success": True,
        "message": "GA4 ayarları kaydedildi" + (" ve WordPress'e gönderildi" if wp_sync and wp_sync.get("success") else ""),
        "measurement_id": mid,
        "wordpress_sync": wp_sync,
    }


@app.get("/api/analytics/liste")
def analytics_liste():
    return log_and_return("analytics", "Analytics - Tüm Raporlar", None, tum_raporlar())

@app.get("/api/analytics/ozet")
def analytics_ozet():
    return log_and_return("analytics", "Analytics - Özet", None, ozet())

@app.delete("/api/analytics/sil/{url}")
def analytics_sil_endpoint(url: str):
    return log_and_return("analytics", "Analytics - Sil", None, analytics_sil(url))

# ==================== CONVERSION EXTRA ====================
@app.get("/api/conversion/liste")
def conversion_liste():
    return log_and_return("conversion", "Conversion - Liste", None, conversion_listele())

@app.get("/api/conversion/istatistik")
def conversion_istatistik():
    return log_and_return("conversion", "Conversion - İstatistik", None, conversion_istatistik())

@app.post("/api/conversion/hedef")
def conversion_hedef_ekle(req: ModulRequest):
    return log_and_return("conversion", "Conversion - Hedef Ekle", req, hedef_ekle(getattr(req, "hedef", "")))

@app.delete("/api/conversion/hedef/{hedef}")
def conversion_hedef_sil(hedef: str):
    return log_and_return("conversion", "Conversion - Hedef Sil", None, hedef_sil(hedef))

# ==================== ABTEST EXTRA ====================
@app.get("/api/abtest/liste")
def abtest_liste():
    return log_and_return("abtest", "A/B Test - Liste", None, abtest_listele())

@app.post("/api/abtest/sonlandir")
def abtest_sonlandir(req: ModulRequest):
    return log_and_return("abtest", "A/B Test - Sonlandır", req, sonlandir(getattr(req, "test_id", "")))

@app.post("/api/abtest/istatistik")
def abtest_istatistik_endpoint(req: ModulRequest):
    return log_and_return("abtest", "A/B Test - İstatistik", req, abtest_istatistik(getattr(req, "test_id", "")))

@app.post("/api/abtest/rapor")
def abtest_rapor_endpoint(req: ModulRequest):
    return log_and_return("abtest", "A/B Test - Rapor", req, abtest_rapor(getattr(req, "test_id", "")))

# ==================== HEATMAP EXTRA ====================
@app.get("/api/heatmap/liste")
def heatmap_liste():
    return log_and_return("heatmap", "Heatmap - Liste", None, heatmap_listele())

@app.get("/api/heatmap/detay/{hid}")
def heatmap_detay_endpoint(hid: str):
    return log_and_return("heatmap", "Heatmap - Detay", None, heatmap_detay(hid))

@app.delete("/api/heatmap/sil/{hid}")
def heatmap_sil_endpoint(hid: str):
    return log_and_return("heatmap", "Heatmap - Sil", None, heatmap_sil(hid))

# ==================== FUNNEL EXTRA ====================
@app.get("/api/funnel/liste")
def funnel_liste():
    return log_and_return("funnel", "Funnel - Liste", None, funnel_listele())

@app.get("/api/funnel/detay/{fid}")
def funnel_detay_endpoint(fid: str):
    return log_and_return("funnel", "Funnel - Detay", None, funnel_detay(fid))

@app.post("/api/funnel/optimize")
def funnel_optimize(req: ModulRequest):
    return log_and_return("funnel", "Funnel - Optimize", req, optimize_et(getattr(req, "funnel_id", "")))

# ==================== CITATION EXTRA ====================
@app.get("/api/citation/liste")
def citation_liste():
    return log_and_return("citation", "Citation - Liste", None, citation_listele())

@app.post("/api/citation/dogrula")
def citation_dogrula(req: ModulRequest):
    return log_and_return("citation", "Citation - Doğrula", req, dogrula(getattr(req, "isletme", "")))

@app.post("/api/citation/export")
def citation_export_endpoint(req: ModulRequest):
    return log_and_return("citation", "Citation - Export", req, citation_export(getattr(req, "format", "csv")))

# ==================== REVIEW EXTRA ====================
@app.get("/api/review/liste")
def review_liste():
    return log_and_return("review", "Review - Liste", None, review_listele())

@app.post("/api/review/yanitla")
def review_yanitla(req: ModulRequest):
    return log_and_return("review", "Review - Yanıtla", req, yanitla(getattr(req, "review_id", ""), getattr(req, "yanit", "")))

@app.get("/api/review/istatistik")
def review_istatistik():
    return log_and_return("review", "Review - İstatistik", None, review_istatistik())

# ==================== TREND EXTRA ====================
@app.get("/api/trend/liste")
def trend_liste():
    return log_and_return("trend", "Trend - Liste", None, trend_listele())

@app.get("/api/trend/populer")
def trend_populer():
    return log_and_return("trend", "Trend - Popüler", None, populer())

@app.post("/api/trend/grafik")
def trend_grafik_endpoint(req: ModulRequest):
    return log_and_return("trend", "Trend - Grafik", req, trend_grafik(getattr(req, "konu", "")))

# ==================== SENTIMENT EXTRA ====================
@app.post("/api/sentiment/toplu")
def sentiment_toplu(req: ModulRequest):
    return log_and_return("sentiment", "Sentiment - Toplu Analiz", req, toplu_analiz(getattr(req, "metinler", [])))

@app.get("/api/sentiment/gecmis")
def sentiment_gecmis():
    return log_and_return("sentiment", "Sentiment - Geçmiş", None, sentiment_gecmis())

@app.get("/api/sentiment/istatistik")
def sentiment_istatistik():
    return log_and_return("sentiment", "Sentiment - İstatistik", None, sentiment_istatistik())

# ==================== FORECAST EXTRA ====================
@app.get("/api/forecast/liste")
def forecast_liste():
    return log_and_return("forecast", "Forecast - Liste", None, forecast_listele())

@app.post("/api/forecast/karsilastir")
def forecast_karsilastir(req: ModulRequest):
    return log_and_return("forecast", "Forecast - Karşılaştır", req, forecast_karsilastir(getattr(req, "tahmin_id", "")))

@app.post("/api/forecast/export")
def forecast_export_endpoint(req: ModulRequest):
    return log_and_return("forecast", "Forecast - Export", req, forecast_export(getattr(req, "format", "csv")))

# ==================== ALERT EXTRA ====================
@app.get("/api/alert/liste")
def alert_liste():
    return log_and_return("alert", "Alert - Liste", None, alert_listele())

@app.post("/api/alert/sil")
def alert_sil_endpoint(req: ModulRequest):
    return log_and_return("alert", "Alert - Sil", req, alert_sil(getattr(req, "alert_id", "")))

@app.get("/api/alert/kontrol")
def alert_kontrol():
    return log_and_return("alert", "Alert - Kontrol", None, alert_kontrol())

@app.get("/api/alert/gecmis")
def alert_gecmis():
    return log_and_return("alert", "Alert - Geçmiş", None, alert_gecmis())

# ==================== NOTIFICATION EXTRA ====================
@app.get("/api/notification/liste")
def notification_liste():
    return log_and_return("notification", "Notification - Liste", None, notification_listele())

@app.post("/api/notification/oku")
def notification_oku(req: ModulRequest):
    return log_and_return("notification", "Notification - Oku", req, oku(getattr(req, "bildirim_id", "")))

@app.delete("/api/notification/temizle")
def notification_temizle():
    return log_and_return("notification", "Notification - Temizle", None, notification_temizle())

@app.get("/api/notification/ayarlar")
def notification_ayarlar():
    return log_and_return("notification", "Notification - Ayarlar", None, notification_ayarlar())

# ==================== REPORT EXTRA ====================
@app.get("/api/report/liste")
def report_liste():
    return log_and_return("report", "Report - Liste", None, report_listele())

@app.post("/api/report/sil")
def report_sil_endpoint(req: ModulRequest):
    return log_and_return("report", "Report - Sil", req, report_sil(getattr(req, "rapor_id", "")))

@app.post("/api/report/indir")
def report_indir_endpoint(req: ModulRequest):
    return log_and_return("report", "Report - İndir", req, report_indir(getattr(req, "rapor_id", "")))

@app.post("/api/report/zamanla")
def report_zamanla(req: ModulRequest):
    return log_and_return("report", "Report - Zamanla", req, zamanla(getattr(req, "rapor_id", ""), getattr(req, "periyot", "")))

# ==================== SCHEDULE EXTRA ====================
@app.get("/api/schedule/liste")
def schedule_liste():
    return log_and_return("schedule", "Schedule - Liste", None, schedule_listele())

@app.delete("/api/schedule/sil/{sid}")
def schedule_sil_endpoint(sid: str):
    return log_and_return("schedule", "Schedule - Sil", None, schedule_sil(sid))

@app.post("/api/schedule/duraklat")
def schedule_duraklat(req: ModulRequest):
    return log_and_return("schedule", "Schedule - Duraklat", req, duraklat(getattr(req, "schedule_id", "")))

@app.post("/api/schedule/devam-ettir")
def schedule_devam_ettir(req: ModulRequest):
    return log_and_return("schedule", "Schedule - Devam Ettir", req, devam_ettir(getattr(req, "schedule_id", "")))

# ==================== BACKUP EXTRA ====================
@app.get("/api/backup/liste")
def backup_liste():
    return log_and_return("backup", "Backup - Liste", None, backup_listele())

@app.delete("/api/backup/sil/{bid}")
def backup_sil_endpoint(bid: str):
    return log_and_return("backup", "Backup - Sil", None, backup_sil(bid))

@app.post("/api/backup/indir")
def backup_indir_endpoint(req: ModulRequest):
    return log_and_return("backup", "Backup - İndir", req, backup_indir(getattr(req, "yedek_id", "")))

@app.post("/api/backup/otomatik")
def backup_otomatik(req: ModulRequest):
    return log_and_return("backup", "Backup - Otomatik", req, otomatik_zamanla(getattr(req, "periyot", "daily")))

# ==================== RESTORE EXTRA ====================
@app.post("/api/restore/onizle")
def restore_onizle(req: ModulRequest):
    return log_and_return("restore", "Restore - Önizle", req, onizle(getattr(req, "yedek_id", "")))

@app.post("/api/restore/geri-yukle")
def restore_geri_yukle(req: ModulRequest):
    return log_and_return("restore", "Restore - Geri Yükle", req, geri_yukle(getattr(req, "yedek_id", "")))

@app.get("/api/restore/liste")
def restore_liste():
    return log_and_return("restore", "Restore - Liste", None, restore_listele())

# ==================== LOG EXTRA ====================
@app.get("/api/log/liste")
def log_liste():
    return log_and_return("log", "Log - Liste", None, log_listele("", ""))

@app.get("/api/log/detay/{lid}")
def log_detay_endpoint(lid: str):
    return log_and_return("log", "Log - Detay", None, log_detay(lid))

@app.delete("/api/log/temizle")
def log_temizle():
    return log_and_return("log", "Log - Temizle", None, log_temizle())

@app.get("/api/log/ara")
def log_ara_sorgu(sorgu: str = ""):
    return log_and_return("log", "Log - Ara", None, log_ara(sorgu))

@app.get("/api/log/istatistik")
def log_istatistik():
    return log_and_return("log", "Log - İstatistik", None, log_istatistik())

# ==================== MONITOR EXTRA ====================
@app.get("/api/monitor/kontrol")
def monitor_kontrol():
    return log_and_return("monitor", "Monitor - Kontrol", None, monitor_kontrol())

@app.get("/api/monitor/liste")
def monitor_liste():
    return log_and_return("monitor", "Monitor - Liste", None, monitor_listele())

@app.get("/api/monitor/detay/{mid}")
def monitor_detay_endpoint(mid: str):
    return log_and_return("monitor", "Monitor - Detay", None, monitor_detay(mid))

@app.get("/api/monitor/ayarlar")
def monitor_ayarlar():
    return log_and_return("monitor", "Monitor - Ayarlar", None, monitor_ayarlar())

@app.post("/api/monitor/ayarlar")
def monitor_ayarlari_kaydet(req: ModulRequest):
    return log_and_return("monitor", "Monitor - Ayarları Kaydet", req, ayarlari_kaydet(dict(req)))

# ==================== DEBUG EXTRA ====================
@app.post("/api/debug/test")
def debug_test(req: ModulRequest):
    return log_and_return("debug", "Debug - Test", req, modul_test(getattr(req, "modul_id", "")))

@app.post("/api/debug/hata-ayikla")
def debug_hata_ayikla(req: ModulRequest):
    return log_and_return("debug", "Debug - Hata Ayıkla", req, hata_ayikla(getattr(req, "modul_id", ""), dict(getattr(req, "parametreler", {}))))

@app.post("/api/debug/performans")
def debug_performans(req: ModulRequest):
    return log_and_return("debug", "Debug - Performans", req, performans(getattr(req, "modul_id", "")))

@app.post("/api/debug/log-incele")
def debug_log_incele(req: ModulRequest):
    return log_and_return("debug", "Debug - Log İncele", req, log_incele(getattr(req, "modul_id", ""), int(getattr(req, "satir", 50))))

@app.post("/api/debug/sema")
def debug_sema(req: ModulRequest):
    return log_and_return("debug", "Debug - Şema", req, sema_dogrula(getattr(req, "modul_id", "")))

# ==================== API KEY SETTINGS ====================
@app.get("/api/settings/apikeys")
def settings_apikeys_get():
    keys = get_all_keys()
    return {"status": "aktif", "keys": keys}

@app.post("/api/settings/apikeys")
def settings_apikeys_set(req: ModulRequest):
    kaydedilen = []
    for servis in get_all_keys().keys():
        val = getattr(req, servis, None)
        if val is not None:
            set_key(servis, str(val))
            kaydedilen.append(servis)
    return {"status": "aktif", "mesaj": f"{len(kaydedilen)} API anahtarı kaydedildi", "kaydedilen": kaydedilen}

# ==================== SEARCH (SERPAPI) ====================
@app.post("/api/search")
def search_endpoint(req: ModulRequest):
    sonuc = search_serpapi(getattr(req, "query", ""), int(getattr(req, "num", 10)))
    try: log_module_run("search", "Search - SERPAPI", dict(req), dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "Search Engine", **sonuc}

# ==================== GITHUB ====================
@app.get("/api/github/repos")
def github_repos_endpoint():
    sonuc = github_repos()
    try: log_module_run("github", "GitHub - Repolar", {}, dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "GitHub Integration", **sonuc}

@app.post("/api/github/create_gist")
def github_create_gist_endpoint(req: ModulRequest):
    sonuc = github_create_gist(
        getattr(req, "filename", "hive_config_backup.json"),
        getattr(req, "content", ""),
        getattr(req, "description", "HIVE config backup"),
        bool(getattr(req, "public", False)),
    )
    try: log_module_run("github", "GitHub - Gist Oluştur", dict(req), dict(sonuc))
    except: pass
    return {"status": "aktif", "modul": "GitHub Integration", **sonuc}

# ==================== EXPOSED KEY HUNTER (Kingfisher) ====================
@app.post("/api/hunter/scan")
async def hunter_scan_endpoint(req: ModulRequest):
    query = getattr(req, "query", "openai")
    limit = int(getattr(req, "limit", 50))
    results = hunter_instance.scan(query, limit)
    try: log_module_run("exposedkeyhunter", "Exposed Key Hunter - Scan", {"query": query, "limit": limit}, {"count": len(results)})
    except: pass
    return {"status": "aktif", "modul": "Exposed Key Hunter", "success": True, "count": len(results), "results": results}

@app.get("/api/hunter/template")
def hunter_template(repo_url: str = "", key_type: str = "", file_path: str = "", line: int = 0):
    template = "\n".join([
        "Konu: Guvenlik Acigi Tespiti - " + key_type,
        "",
        "Merhaba,",
        "",
        repo_url + " reposunda bir API anahtariniz acikta.",
        "",
        "- Tip: " + key_type,
        "- Dosya: " + file_path,
        "- Satir: " + str(line),
        "",
        "Herhangi bir islem yapmadik, sadece bilgi amacli.",
        "",
        "Iyi calismalar.",
    ])
    return {"template": template}

# ==================== THE REPLICATOR V3 ====================
from app.moduller.replicator import replicator


class ReplicatorRedirectBody(BaseModel):
    domains: list[str]


@app.post("/api/replicator/redirect")
def replicator_redirect(req: ReplicatorRedirectBody):
    if not req.domains:
        raise HTTPException(status_code=400, detail="Domain listesi boş")
    result = replicator.start_redirect_all(req.domains)
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Başlatılamadı"))
    try:
        log_module_run("replicator", "301 Redirect başlat", {"domains": req.domains}, result)
    except Exception:
        pass
    return result


@app.get("/api/replicator/status")
def replicator_status():
    return replicator.get_status()


# ==================== STORYFORGE V2 ====================
from app.moduller.storyforge_v2 import storyforge


class StoryForgeFetchBody(BaseModel):
    url: str


class StoryForgePublishBody(BaseModel):
    title: str
    content: str
    lokasyon: str = ""
    excerpt: str = ""
    category_slug: str = "gece-hikaye"
    status: str = "publish"
    pending_id: str = ""
    featured_media_id: int = 0


class StoryForgeGenerateBody(BaseModel):
    count: int = 10
    auto_publish: bool = True
    category_slug: str = ""
    delay_sec: float = 1.0


class StoryForgeBatchUrlsBody(BaseModel):
    urls: list[str]
    auto_publish: bool = True
    category_slug: str = "gece-hikaye"
    delay_sec: float = 2.0


class StoryForgeBulkRewriteBody(BaseModel):
    import_id: str
    auto_publish: bool = True
    category_slug: str = "gece-hikaye"
    delay_sec: float = 3.0
    offset: int = 0
    limit: int = 0


class StoryForgeQuickBody(BaseModel):
    text: str
    title: str = ""
    auto_publish: bool = True
    preview_only: bool = False
    category_slug: str = "gece-hikaye"


class StoryForgePasteBody(BaseModel):
    text: str
    filename: str = "paste.txt"


class StoryForgePasteRunBody(BaseModel):
    text: str
    filename: str = "paste.txt"
    auto_publish: bool = True
    category_slug: str = "gece-hikaye"
    delay_sec: float = 2.0
    offset: int = 0
    limit: int = 0


class StoryForgeRulesBody(BaseModel):
    city: str = ""
    district: str = ""
    locations: list[str] = []
    character_names: list[str] = []
    keywords: list[str] = []
    custom_rules: str = ""
    title_template: str = ""
    min_words: int = 0
    seo_title_max: int = 0
    site_url: str = ""
    geo_inject: bool | None = None
    max_words: int = 0
    auto_category: bool | None = None


@app.get("/api/storyforge/stats")
def storyforge_stats():
    return storyforge.get_stats()


@app.get("/api/storyforge/ai-engines")
def storyforge_ai_engines():
    from app.moduller import llm_router
    llm_router.ensure_ollama_running()
    return llm_router.list_engines()


@app.get("/api/storyforge/photos")
def storyforge_list_photos():
    photos = storyforge.list_photos()
    return {"photos": photos, "count": len(photos)}


@app.delete("/api/storyforge/photos")
def storyforge_clear_photos():
    return storyforge.clear_photos()


@app.post("/api/storyforge/photos")
async def storyforge_upload_photos(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="En az bir fotoğraf seçin")
    if len(files) > 500:
        raise HTTPException(status_code=400, detail="Tek seferde en fazla 500 fotoğraf")
    payload: list[tuple[str, bytes, str]] = []
    for f in files:
        data = await f.read()
        payload.append((f.filename or "story.jpg", data, f.content_type or "image/jpeg"))
    result = storyforge.upload_photos(payload)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Yükleme başarısız"))
    return result


@app.get("/api/storyforge/jobs")
def storyforge_jobs(limit: int = 20):
    return {"jobs": storyforge.list_jobs(limit=limit)}


@app.get("/api/storyforge/jobs/{job_id}")
def storyforge_job_detail(job_id: str):
    job = storyforge.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    return job


@app.post("/api/storyforge/generate")
def storyforge_generate(req: StoryForgeGenerateBody):
    result = storyforge.start_generate_job(
        count=req.count,
        auto_publish=req.auto_publish,
        category_slug=req.category_slug.strip(),
        delay_sec=max(0.0, req.delay_sec),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Üretim başlatılamadı"))
    try:
        log_module_run("storyforge", "Batch generate", req.model_dump(), result)
    except Exception:
        pass
    return result


@app.post("/api/storyforge/batch-urls")
def storyforge_batch_urls(req: StoryForgeBatchUrlsBody):
    result = storyforge.start_url_batch_job(
        urls=req.urls,
        auto_publish=req.auto_publish,
        category_slug=req.category_slug.strip() or "gece-hikaye",
        delay_sec=max(0.0, req.delay_sec),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Toplu iş başlatılamadı"))
    try:
        log_module_run("storyforge", "Batch URLs", {"count": len(req.urls)}, result)
    except Exception:
        pass
    return result


@app.post("/api/storyforge/fetch")
def storyforge_fetch(req: StoryForgeFetchBody):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL gerekli")
    result = storyforge.fetch_and_rewrite(req.url.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Hikaye alınamadı"))
    try:
        log_module_run("storyforge", "Fetch & rewrite", {"url": req.url}, {"pending_id": result.get("pending_id")})
    except Exception:
        pass
    return result


@app.get("/api/storyforge/pending")
def storyforge_pending():
    return {"pending": storyforge.list_pending()}


@app.get("/api/storyforge/published")
def storyforge_published(limit: int = 40):
    items = storyforge.list_published(limit=limit)
    return {"published": items, "count": len(items)}


@app.get("/api/storyforge/verify-link")
def storyforge_verify_link(url: str):
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="url parametresi gerekli")
    return storyforge.verify_live_url(url.strip())


from app.moduller.storyforge_bulk import (
    get_import_info,
    import_from_text,
    load_rules,
    parse_bulk_content,
    parse_docx_bytes,
    preview_bulk_text,
    save_import_stories,
    save_rules,
)


@app.get("/api/storyforge/categories")
def storyforge_categories():
    from app.moduller.storyforge_categories import list_category_tree
    from app.moduller.wordpress_api import wp_api
    tree = list_category_tree()
    wp_cats = wp_api().list_story_categories()
    return {**tree, "wp_terms": wp_cats.get("terms", []), "wp_count": wp_cats.get("count", 0)}


@app.post("/api/storyforge/categories/sync")
def storyforge_categories_sync():
    from app.moduller.storyforge_categories import sync_categories_to_wordpress
    from app.moduller.wordpress_api import wp_api
    result = sync_categories_to_wordpress(wp_api())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Senkron başarısız"))
    return result


class StoryForgeCategoryKeywordsBody(BaseModel):
    keywords: str
    parent_name: str = ""
    parent_slug: str = ""
    save_map: bool = True


class StoryForgeCategoryPredictBody(BaseModel):
    title: str = ""
    content: str = ""
    lokasyon: str = ""
    category_slug: str = "auto"


@app.post("/api/storyforge/categories/predict")
def storyforge_categories_predict(req: StoryForgeCategoryPredictBody):
    from app.moduller.storyforge_categories import resolve_category_assignment
    from app.moduller.wordpress_api import wp_api
    api = wp_api()
    wp_terms: list = []
    if api.connected:
        listed = api.list_story_categories()
        if listed.get("success"):
            wp_terms = listed.get("terms", [])
    picked = resolve_category_assignment(
        category_slug=req.category_slug,
        title=req.title,
        content=req.content,
        lokasyon=req.lokasyon,
        wp_terms=wp_terms,
    )
    return {
        "success": True,
        "picked": picked,
        "auto_create": True,
        "path": " → ".join(
            p for p in [
                picked.get("main_name") or picked.get("main_slug"),
                picked.get("sub_name") or (picked.get("sub_slug") if picked.get("sub_slug") else ""),
            ] if p
        ),
    }


@app.post("/api/storyforge/categories/preview")
def storyforge_categories_preview(req: StoryForgeCategoryKeywordsBody):
    from app.moduller.storyforge_categories import preview_keywords
    result = preview_keywords(req.keywords, req.parent_name, req.parent_slug)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Önizleme başarısız"))
    return result


@app.post("/api/storyforge/categories/from-keywords")
def storyforge_categories_from_keywords(req: StoryForgeCategoryKeywordsBody):
    from app.moduller.storyforge_categories import create_from_keywords
    from app.moduller.wordpress_api import wp_api
    result = create_from_keywords(
        wp_api(),
        req.keywords,
        req.parent_name,
        req.parent_slug,
        req.save_map,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Kategori oluşturulamadı"))
    try:
        log_module_run("storyforge", "Category from keywords", {"lines": len(req.keywords.splitlines())}, result)
    except Exception:
        pass
    return result


# ── Kategori Merkezi ──
class CategoryHubCreateBody(BaseModel):
    kind: str = "ilan"
    name: str = ""
    slug: str = ""
    parent_id: int = 0
    force: bool = False


class CategoryHubBulkBody(BaseModel):
    kind: str = "hikaye"
    keywords: str = ""
    parent_name: str = ""
    parent_slug: str = ""
    force: bool = False


class CategoryHubAssignBody(BaseModel):
    kind: str = "ilan"
    post_ids: list[int] = []
    term_ids: list[int] = []
    mode: str = "add"


class CategoryHubPublishProfileBody(BaseModel):
    title: str = ""
    content: str = ""
    term_ids: list[int] = []
    status: str = "publish"


class CategoryHubPublishStoryBody(BaseModel):
    text: str = ""
    title: str = ""
    term_slug: str = "auto"
    auto_publish: bool = True


class CategoryHubUpdateBody(BaseModel):
    kind: str = "ilan"
    term_id: int = 0
    name: str = ""
    slug: str = ""
    description: str = ""


class CategoryHubMergeBody(BaseModel):
    kind: str = "ilan"
    source_id: int = 0
    target_id: int = 0


@app.get("/api/category-hub/status")
def category_hub_status():
    from app.moduller.category_hub import hub_status
    return hub_status()


@app.post("/api/category-hub/connect")
def category_hub_connect():
    from app.moduller.category_hub import connect_wordpress
    result = connect_wordpress()
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or "WordPress bağlanamadı")
    return result


@app.get("/api/category-hub/tree")
def category_hub_tree(kind: str = "ilan", search: str = ""):
    from app.moduller.category_hub import get_tree
    return get_tree(kind, search)


@app.get("/api/category-hub/check-duplicate")
def category_hub_check_duplicate(kind: str = "ilan", name: str = "", slug: str = "", parent_id: int = 0):
    from app.moduller.category_hub import check_duplicate
    return check_duplicate(kind, name, slug, parent_id)


@app.post("/api/category-hub/create")
def category_hub_create(req: CategoryHubCreateBody):
    from app.moduller.category_hub import create_category
    result = create_category(req.kind, req.name, req.slug, req.parent_id, req.force)
    if not result.get("success"):
        code = 409 if result.get("needs_confirm") else 422
        raise HTTPException(status_code=code, detail=result.get("error", "Oluşturulamadı"))
    return result


@app.post("/api/category-hub/bulk-keywords")
def category_hub_bulk_keywords(req: CategoryHubBulkBody):
    from app.moduller.category_hub import create_bulk_keywords
    result = create_bulk_keywords(req.kind, req.keywords, req.parent_name, req.parent_slug, req.force)
    if not result.get("success"):
        code = 409 if result.get("needs_confirm") else 422
        raise HTTPException(status_code=422, detail=result.get("error", "Toplu oluşturma başarısız"))
    return result


@app.post("/api/category-hub/sync-default")
def category_hub_sync_default(kind: str = "hikaye"):
    from app.moduller.category_hub import sync_default_tree
    result = sync_default_tree(kind)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Senkron başarısız"))
    return result


@app.get("/api/category-hub/content")
def category_hub_content(kind: str = "ilan", term_id: int = 0, page: int = 1):
    from app.moduller.category_hub import list_term_content
    return list_term_content(kind, term_id, page)


@app.get("/api/category-hub/queue")
def category_hub_queue(kind: str = "ilan", limit: int = 50):
    from app.moduller.category_hub import list_uncategorized
    return list_uncategorized(kind, limit)


@app.post("/api/category-hub/assign")
def category_hub_assign(req: CategoryHubAssignBody):
    from app.moduller.category_hub import assign_content
    result = assign_content(req.kind, req.post_ids, req.term_ids, req.mode)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("errors", ["Atama başarısız"])[0])
    return result


@app.post("/api/category-hub/publish-profile")
def category_hub_publish_profile(req: CategoryHubPublishProfileBody):
    from app.moduller.category_hub import publish_profile
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="İlan başlığı gerekli")
    result = publish_profile(req.title.strip(), req.content, req.term_ids or None, req.status)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "İlan yayınlanamadı"))
    return result


@app.post("/api/category-hub/publish-story")
def category_hub_publish_story(req: CategoryHubPublishStoryBody):
    from app.moduller.category_hub import publish_story
    if len((req.text or "").strip()) < 80:
        raise HTTPException(status_code=400, detail="Hikaye en az 80 karakter olmalı")
    result = publish_story(req.text.strip(), req.title.strip(), req.term_slug, req.auto_publish)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Hikaye yayınlanamadı"))
    return result


@app.put("/api/category-hub/term")
def category_hub_update_term(req: CategoryHubUpdateBody):
    from app.moduller.category_hub import update_term
    result = update_term(req.kind, req.term_id, req.name, req.slug, req.description)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Güncellenemedi"))
    return result


@app.post("/api/category-hub/merge")
def category_hub_merge(req: CategoryHubMergeBody):
    from app.moduller.category_hub import merge_terms
    result = merge_terms(req.kind, req.source_id, req.target_id)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Birleştirme başarısız"))
    return result


@app.get("/api/category-hub/verify")
def category_hub_verify(kind: str = "ilan", term_id: int = 0):
    from app.moduller.category_hub import verify_term_url
    return verify_term_url(kind, term_id)


@app.get("/api/category-hub/talon-keywords")
def category_hub_talon_keywords(limit: int = 30):
    from app.moduller.category_hub import talon_keywords
    return talon_keywords(limit)


class PageHubCreateBody(BaseModel):
    kind: str = "page"
    title: str = ""
    slug: str = ""
    content: str = ""
    parent_id: int = 0
    status: str = "draft"
    excerpt: str = ""
    force: bool = False
    keyword: str = ""
    city: str = "Aydın"
    district: str = "Kuşadası"
    category: str = "Gece Hayatı"
    subcategory: str = "Eğlence"
    notify_index: bool = False


class PageHubBulkBody(BaseModel):
    kind: str = "page"
    keywords: str = ""
    parent_id: int = 0
    status: str = "draft"
    force: bool = False
    city: str = "Aydın"
    district: str = "Kuşadası"
    notify_index: bool = False


class PageHubPublishBody(BaseModel):
    kind: str = "page"
    page_id: int = 0
    status: str = "publish"
    notify_index: bool = True


class PageHubBulkPublishBody(BaseModel):
    kind: str = "page"
    page_ids: list[int] = []
    notify_index: bool = True


class PageHubUpdateBody(BaseModel):
    kind: str = "page"
    page_id: int = 0
    title: str = ""
    slug: str = ""
    content: str = ""
    excerpt: str = ""
    parent_id: int | None = None


class PageHubPreviewBody(BaseModel):
    kind: str = "landing"
    keyword: str = ""
    city: str = "Aydın"
    district: str = "Kuşadası"
    category: str = "Gece Hayatı"
    subcategory: str = "Eğlence"


class PageHubIndexNowBody(BaseModel):
    url: str = ""


@app.get("/api/page-hub/status")
def page_hub_status():
    from app.moduller.page_hub import hub_status
    return hub_status()


@app.post("/api/page-hub/connect")
def page_hub_connect():
    from app.moduller.page_hub import connect_wordpress
    result = connect_wordpress()
    if not result.get("wp_connected"):
        return result
    return result


@app.get("/api/page-hub/tree")
def page_hub_tree(kind: str = "page", search: str = ""):
    from app.moduller.page_hub import get_tree
    return get_tree(kind, search)


@app.get("/api/page-hub/check-duplicate")
def page_hub_check_duplicate(kind: str = "page", title: str = "", slug: str = "", parent_id: int = 0):
    from app.moduller.page_hub import check_duplicate
    return check_duplicate(kind, title, slug, parent_id)


@app.post("/api/page-hub/create")
def page_hub_create(req: PageHubCreateBody):
    from app.moduller.page_hub import create_page
    result = create_page(
        req.kind, req.title, req.slug, req.content, req.parent_id,
        req.status, req.excerpt, req.force, req.keyword,
        req.city, req.district, req.category, req.subcategory, req.notify_index,
    )
    if not result.get("success"):
        code = 409 if result.get("needs_confirm") else 422
        raise HTTPException(status_code=code, detail=result.get("error", "Oluşturulamadı"))
    return result


@app.post("/api/page-hub/bulk-keywords")
def page_hub_bulk_keywords(req: PageHubBulkBody):
    from app.moduller.page_hub import create_bulk_keywords
    result = create_bulk_keywords(
        req.kind, req.keywords, req.parent_id, req.status,
        req.force, req.city, req.district, req.notify_index,
    )
    if not result.get("success") and not result.get("created"):
        raise HTTPException(status_code=422, detail=result.get("error", "Toplu oluşturma başarısız"))
    return result


@app.get("/api/page-hub/queue")
def page_hub_queue(kind: str = "page", limit: int = 50):
    from app.moduller.page_hub import list_queue
    return list_queue(kind, limit)


@app.get("/api/page-hub/detail")
def page_hub_detail(kind: str = "page", page_id: int = 0):
    from app.moduller.page_hub import get_page_detail
    return get_page_detail(kind, page_id)


@app.post("/api/page-hub/publish")
def page_hub_publish(req: PageHubPublishBody):
    from app.moduller.page_hub import publish_page
    if not req.page_id:
        raise HTTPException(status_code=400, detail="page_id gerekli")
    result = publish_page(req.kind, req.page_id, req.status, req.notify_index)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Yayınlanamadı"))
    return result


@app.post("/api/page-hub/bulk-publish")
def page_hub_bulk_publish(req: PageHubBulkPublishBody):
    from app.moduller.page_hub import bulk_publish
    if not req.page_ids:
        raise HTTPException(status_code=400, detail="page_ids gerekli")
    return bulk_publish(req.kind, req.page_ids, req.notify_index)


@app.put("/api/page-hub/page")
def page_hub_update(req: PageHubUpdateBody):
    from app.moduller.page_hub import update_page_fields
    if not req.page_id:
        raise HTTPException(status_code=400, detail="page_id gerekli")
    result = update_page_fields(
        req.kind, req.page_id, req.title, req.slug, req.content, req.excerpt, req.parent_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Güncellenemedi"))
    return result


@app.get("/api/page-hub/verify")
def page_hub_verify(kind: str = "page", page_id: int = 0):
    from app.moduller.page_hub import verify_page_url
    return verify_page_url(kind, page_id)


@app.get("/api/page-hub/talon-keywords")
def page_hub_talon_keywords(limit: int = 30, seed_keyword: str = "", location: str = ""):
    from app.moduller.page_hub import talon_keyword_queue, talon_keywords
    if seed_keyword.strip():
        return talon_keyword_queue(seed_keyword, location or "Kuşadası", limit)
    return talon_keywords(limit)


@app.post("/api/page-hub/preview")
def page_hub_preview(req: PageHubPreviewBody):
    from app.moduller.page_hub import generate_preview
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = generate_preview(
        req.kind, req.keyword, req.city, req.district, req.category, req.subcategory,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Önizleme üretilemedi"))
    return result


@app.post("/api/page-hub/indexnow")
def page_hub_indexnow(req: PageHubIndexNowBody):
    from app.moduller.page_hub import notify_indexnow
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    return notify_indexnow(req.url.strip())


class AstroFactoryCreateBody(BaseModel):
    site_name: str = ""
    domain: str = ""
    seed_keyword: str = ""
    location: str = "Kuşadası"
    niche: str = "Yerel rehber"
    language: str = "tr"
    main_site_url: str = ""
    source_site: str = ""
    deploy_target: str = "cloudflare_pages"
    slug: str = ""


class AstroFactoryPlanBody(BaseModel):
    project_id: str = ""
    seed_keyword: str = ""
    location: str = "Kuşadası"
    niche: str = "Yerel rehber"
    page_count: int = 10
    domain: str = ""


class AstroFactoryProjectBody(BaseModel):
    project_id: str = ""


class AstroFactoryCloudflareCreateBody(BaseModel):
    project_id: str = ""
    cloudflare_project_name: str = ""


class AstroFactoryGeoBody(BaseModel):
    project_id: str = ""
    keywords: list[str] = []
    locations: list[str] = []


class AstroFactoryFaqBody(BaseModel):
    project_id: str = ""
    questions: list[str] = []


class AstroFactoryBlogBody(BaseModel):
    project_id: str = ""
    topics: list[str] = []


@app.get("/api/astro-factory/health")
def astro_factory_health():
    from app.moduller.astro_factory import health
    return health()


@app.post("/api/astro-factory/create-project")
def astro_factory_create_project(req: AstroFactoryCreateBody):
    from app.moduller.astro_factory import create_project
    result = create_project(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Proje oluşturulamadı"))
    _brain_emit("/api/astro-factory/create-project", req, result, module="astro_factory", event_type="project_created")
    return result


@app.post("/api/astro-factory/generate-plan")
def astro_factory_generate_plan(req: AstroFactoryPlanBody):
    from app.moduller.astro_factory import generate_site_plan
    if not req.seed_keyword.strip() and not req.project_id:
        raise HTTPException(status_code=400, detail="seed_keyword veya project_id gerekli")
    seed = req.seed_keyword.strip()
    domain = req.domain
    if req.project_id and not seed:
        from app.moduller.astro_factory import get_project
        try:
            p = get_project(req.project_id).get("project", {})
            seed = p.get("seed_keyword", "")
            domain = domain or p.get("domain", "")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
    result = generate_site_plan(
        seed, req.location, req.niche, req.page_count, req.project_id, domain,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Plan üretilemedi"))
    return result


@app.post("/api/astro-factory/generate-pages")
def astro_factory_generate_pages(req: AstroFactoryProjectBody):
    from app.moduller.astro_factory import generate_pages
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        return generate_pages(req.project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/astro-factory/generate-faq")
def astro_factory_generate_faq(req: AstroFactoryFaqBody):
    from app.moduller.astro_factory import generate_faq_pages
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        return generate_faq_pages(req.project_id, req.questions or None)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/astro-factory/generate-blog")
def astro_factory_generate_blog(req: AstroFactoryBlogBody):
    from app.moduller.astro_factory import generate_blog_posts
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        return generate_blog_posts(req.project_id, req.topics or None)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/astro-factory/build")
def astro_factory_build(req: AstroFactoryProjectBody):
    from app.moduller.astro_factory import build_astro_project
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = build_astro_project(req.project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": result.get("error", "Build başarısız"),
                "build_log": result.get("build_log", ""),
                "dist_exists": result.get("dist_exists", False),
            },
        )
    return result


@app.post("/api/astro-factory/export")
def astro_factory_export(req: AstroFactoryProjectBody):
    from app.moduller.astro_factory import export_project
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = export_project(req.project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Export başarısız"))
    return result


@app.get("/api/astro-factory/projects")
def astro_factory_list_projects():
    from app.moduller.astro_factory import list_projects
    return list_projects()


@app.get("/api/astro-factory/project/{project_id}")
def astro_factory_get_project(project_id: str):
    from app.moduller.astro_factory import get_project
    try:
        return get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.delete("/api/astro-factory/project/{project_id}")
def astro_factory_delete_project(project_id: str):
    from app.moduller.astro_factory import delete_project
    result = delete_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Silinemedi"))
    return result


@app.get("/api/astro-factory/cloudflare/status")
def astro_factory_cloudflare_status():
    from app.moduller.cloudflare_pages_deploy import cf_status
    return cf_status()


@app.post("/api/astro-factory/cloudflare/create-project")
def astro_factory_cloudflare_create_project(req: AstroFactoryCloudflareCreateBody):
    from app.moduller.cloudflare_pages_deploy import create_pages_project
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = create_pages_project(req.project_id, req.cloudflare_project_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Cloudflare proje oluşturulamadı"))
    return result


@app.post("/api/astro-factory/cloudflare/deploy")
def astro_factory_cloudflare_deploy(req: AstroFactoryProjectBody):
    from app.moduller.cloudflare_pages_deploy import deploy_to_cloudflare
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = deploy_to_cloudflare(req.project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": result.get("error", "Deploy başarısız"),
                "log": result.get("log", ""),
                "deployment": result.get("deployment"),
            },
        )
    return result


@app.get("/api/astro-factory/cloudflare/deployments/{project_id}")
def astro_factory_cloudflare_deployments(project_id: str):
    from app.moduller.cloudflare_pages_deploy import get_deployments
    try:
        return get_deployments(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


class AstroAutoSyncBody(BaseModel):
    project_id: str = ""
    auto_deploy: bool = False
    auto_build: bool | None = None
    max_items: int | None = None


class AstroAutoProjectBody(BaseModel):
    project_id: str = ""


class AstroAutoScanBody(BaseModel):
    project_id: str = ""
    sources: dict[str, bool] | None = None
    include_outdated: bool = True


class AstroAutoExportBody(BaseModel):
    project_id: str = ""
    job_id: str = ""


class AstroAutoQueueIgnoreBody(BaseModel):
    queue_id: str = ""


class AstroAutoSettingsBody(BaseModel):
    enabled: bool | None = None
    interval_minutes: int | None = None
    auto_build: bool | None = None
    auto_deploy: bool | None = None
    require_quality_gate_pass: bool | None = None
    min_quality_score: int | None = None
    max_items_per_run: int | None = None
    target_project_id: str | None = None
    sources: dict[str, bool] | None = None


@app.get("/api/astro-auto/health")
def astro_auto_health():
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    return astro_auto_publisher.health()


@app.get("/api/astro-auto/settings")
def astro_auto_get_settings():
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    return {"success": True, "settings": astro_auto_publisher.get_settings()}


@app.post("/api/astro-auto/settings")
def astro_auto_update_settings(req: AstroAutoSettingsBody):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    payload = {k: v for k, v in req.model_dump().items() if v is not None}
    return astro_auto_publisher.update_settings(payload)


@app.post("/api/astro-auto/sync-all")
def astro_auto_sync_all(req: AstroAutoSyncBody):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = astro_auto_publisher.sync_all(
        req.project_id.strip(),
        auto_deploy=req.auto_deploy,
        auto_build=req.auto_build,
        max_items=req.max_items,
    )
    if not result.get("success") and result.get("error"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("astro_auto_publisher", "Sync All", req.model_dump(), result.get("summary", {}))
    return result


@app.post("/api/astro-auto/scan-missing")
def astro_auto_scan_missing(req: AstroAutoScanBody):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = astro_auto_publisher.scan_missing(
        req.project_id.strip(),
        sources=req.sources,
        include_outdated=req.include_outdated,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/astro-auto/queue-missing")
def astro_auto_queue_missing(req: AstroAutoScanBody):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = astro_auto_publisher.queue_missing(
        req.project_id.strip(),
        include_outdated=req.include_outdated,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/astro-auto/process-queue")
def astro_auto_process_queue(req: AstroAutoSyncBody):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = astro_auto_publisher.process_queue(
        req.project_id.strip(),
        auto_deploy=req.auto_deploy,
        auto_build=req.auto_build,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Kuyruk işlenemedi"))
    log_module_run("astro_auto_publisher", "Process Queue", req.model_dump(), result.get("summary", {}))
    return result


@app.post("/api/astro-auto/deploy")
def astro_auto_deploy(req: AstroAutoProjectBody):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = astro_auto_publisher.deploy(req.project_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Deploy başarısız"))
    log_module_run("astro_auto_publisher", "Deploy", req.model_dump(), {"url": result.get("url")})
    return result


@app.get("/api/astro-auto/jobs")
def astro_auto_jobs(limit: int = 20):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    return astro_auto_publisher.list_jobs(limit=limit)


@app.get("/api/astro-auto/job/{job_id}")
def astro_auto_job_detail(job_id: str):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    result = astro_auto_publisher.get_job_detail(job_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/astro-auto/queue")
def astro_auto_queue():
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    return astro_auto_publisher.get_queue()


@app.post("/api/astro-auto/export-report")
def astro_auto_export_report(req: AstroAutoExportBody):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    result = astro_auto_publisher.export_report(
        project_id=req.project_id.strip(),
        job_id=req.job_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/astro-auto/queue-ignore-warning")
def astro_auto_queue_ignore_warning(req: AstroAutoQueueIgnoreBody):
    from app.moduller.astro_auto_publisher import astro_auto_publisher
    if not req.queue_id.strip():
        raise HTTPException(status_code=400, detail="queue_id gerekli")
    result = astro_auto_publisher.ignore_queue_warning(req.queue_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


class ContentRefreshSettingsBody(BaseModel):
    enabled: bool | None = None
    auto_refresh: bool | None = None
    auto_publish: bool | None = None
    auto_deploy: bool | None = None
    refresh_interval_hours: int | None = None
    priority_threshold: int | None = None
    max_pages_per_run: int | None = None


class ContentRefreshProjectBody(BaseModel):
    project_id: str = ""


class ContentRefreshPageBody(BaseModel):
    project_id: str = ""
    page_id: str = ""


class ContentRefreshQueueBody(BaseModel):
    project_id: str = ""
    page_ids: list[str] | None = None


class ContentRefreshProcessBody(BaseModel):
    project_id: str = ""
    auto_publish: bool | None = None
    auto_deploy: bool | None = None


class ContentRefreshExportBody(BaseModel):
    project_id: str = ""
    job_id: str = ""


@app.get("/api/content-refresh/health")
def content_refresh_health():
    from app.moduller.content_refresh_engine import content_refresh_engine
    return content_refresh_engine.health()


@app.get("/api/content-refresh/settings")
def content_refresh_get_settings():
    from app.moduller.content_refresh_engine import content_refresh_engine
    return {"success": True, "settings": content_refresh_engine.get_settings()}


@app.post("/api/content-refresh/settings")
def content_refresh_update_settings(req: ContentRefreshSettingsBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    payload = {k: v for k, v in req.model_dump().items() if v is not None}
    return content_refresh_engine.update_settings(payload)


@app.post("/api/content-refresh/scan")
def content_refresh_scan(req: ContentRefreshProjectBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = content_refresh_engine.scan(req.project_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/content-refresh/analyze-page")
def content_refresh_analyze_page(req: ContentRefreshPageBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    if not req.project_id.strip() or not req.page_id.strip():
        raise HTTPException(status_code=400, detail="project_id ve page_id gerekli")
    result = content_refresh_engine.analyze_page(req.project_id.strip(), req.page_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/content-refresh/analyze-project")
def content_refresh_analyze_project(req: ContentRefreshProjectBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = content_refresh_engine.analyze_project(req.project_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/content-refresh/create-refresh-plan")
def content_refresh_create_plan(req: ContentRefreshPageBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = content_refresh_engine.create_refresh_plan(
        req.project_id.strip(),
        req.page_id.strip() if req.page_id else "",
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/content-refresh/queue")
def content_refresh_queue(req: ContentRefreshQueueBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    return content_refresh_engine.queue_pages(req.project_id.strip(), req.page_ids)


@app.post("/api/content-refresh/process")
def content_refresh_process(req: ContentRefreshProcessBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = content_refresh_engine.process_queue(
        req.project_id.strip(),
        auto_publish=req.auto_publish,
        auto_deploy=req.auto_deploy,
    )
    if not result.get("success") and result.get("error"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("content_refresh_engine", "Process", req.model_dump(), result.get("summary", {}))
    return result


@app.post("/api/content-refresh/refresh-project")
def content_refresh_refresh_project(req: ContentRefreshProcessBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = content_refresh_engine.refresh_project(
        req.project_id.strip(),
        auto_publish=req.auto_publish,
        auto_deploy=req.auto_deploy,
    )
    if not result.get("success") and result.get("error"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("content_refresh_engine", "Refresh Project", req.model_dump(), result.get("summary", {}))
    return result


@app.post("/api/content-refresh/export-report")
def content_refresh_export_report(req: ContentRefreshExportBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    result = content_refresh_engine.export_report(
        project_id=req.project_id.strip(),
        job_id=req.job_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/content-refresh/jobs")
def content_refresh_jobs(limit: int = 20):
    from app.moduller.content_refresh_engine import content_refresh_engine
    return content_refresh_engine.list_jobs(limit=limit)


@app.get("/api/content-refresh/job/{job_id}")
def content_refresh_job_detail(job_id: str):
    from app.moduller.content_refresh_engine import content_refresh_engine
    result = content_refresh_engine.get_job_detail(job_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/content-refresh/queue")
def content_refresh_queue_list():
    from app.moduller.content_refresh_engine import content_refresh_engine
    return content_refresh_engine.get_queue()


class ContentRefreshRefreshPageBody(BaseModel):
    project_id: str = ""
    page_id: str = ""
    auto_publish: bool | None = None
    auto_deploy: bool | None = None


@app.post("/api/content-refresh/refresh-page")
def content_refresh_refresh_page_v2(req: ContentRefreshRefreshPageBody):
    from app.moduller.content_refresh_engine import content_refresh_engine
    if not req.project_id.strip() or not req.page_id.strip():
        raise HTTPException(status_code=400, detail="project_id ve page_id gerekli")
    result = content_refresh_engine.refresh_page(
        req.project_id.strip(), req.page_id.strip(),
        auto_publish=req.auto_publish, auto_deploy=req.auto_deploy,
    )
    if not result.get("success") and result.get("error"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("content_refresh_engine", "Refresh Page", req.model_dump(), {"page_id": req.page_id})
    return result


class QuestionIntelligenceBody(BaseModel):
    keyword: str = ""
    location: str = "Kuşadası"
    city: str = "Aydın"
    district: str = ""
    category: str = "gece hayatı"
    subcategory: str = ""
    project_id: str = ""
    write_astro: bool = False
    push_entity_graph: bool = True
    append_place_seo: bool = False
    count: int = 6
    secondary_keywords: str = ""


class QuestionIntelligenceExportBody(BaseModel):
    job_id: str = ""
    format: str = "json"


class QuestionIntelligenceEntitiesBody(QuestionIntelligenceBody):
    entities: list[str] | None = None
    locations: list[str] | None = None


@app.get("/api/question-intelligence/health")
def question_intelligence_health():
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    return question_intelligence_engine.health()


@app.post("/api/question-intelligence/generate-faq")
def question_intelligence_generate_faq(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = question_intelligence_engine.generate_faq(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("question_intelligence_engine", "Generate FAQ", req.model_dump(), {"count": result.get("count")})
    return result


@app.post("/api/question-intelligence/generate-far")
def question_intelligence_generate_far(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = question_intelligence_engine.generate_far(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/generate-comparisons")
def question_intelligence_generate_comparisons(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    result = question_intelligence_engine.generate_comparisons(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/generate-bestof")
def question_intelligence_generate_bestof(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    result = question_intelligence_engine.generate_bestof(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/generate-problem-solution")
def question_intelligence_generate_problem_solution(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    result = question_intelligence_engine.generate_problem_solution(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/generate-local-intent")
def question_intelligence_generate_local_intent(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    result = question_intelligence_engine.generate_local_intent(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/generate-objections")
def question_intelligence_generate_objections(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    result = question_intelligence_engine.generate_objections(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/generate-ai-overview")
def question_intelligence_generate_ai_overview(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = question_intelligence_engine.generate_ai_overview(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/generate-people-also-ask")
def question_intelligence_generate_paa(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = question_intelligence_engine.generate_people_also_ask(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/generate-autocomplete")
def question_intelligence_generate_autocomplete(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    return question_intelligence_engine.generate_autocomplete(req.model_dump())


@app.post("/api/question-intelligence/generate-related-searches")
def question_intelligence_generate_related(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    return question_intelligence_engine.generate_related_searches(req.model_dump())


@app.post("/api/question-intelligence/generate-reddit-intent")
def question_intelligence_generate_reddit(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    return question_intelligence_engine.generate_reddit_intent(req.model_dump())


@app.post("/api/question-intelligence/generate-decision")
def question_intelligence_generate_decision(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    return question_intelligence_engine.generate_decision(req.model_dump())


@app.post("/api/question-intelligence/generate-entity-questions")
def question_intelligence_generate_entity_questions(req: QuestionIntelligenceEntitiesBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    return question_intelligence_engine.generate_entity_questions(req.model_dump())


@app.post("/api/question-intelligence/generate-location-questions")
def question_intelligence_generate_location_questions(req: QuestionIntelligenceEntitiesBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    return question_intelligence_engine.generate_location_questions(req.model_dump())


@app.post("/api/question-intelligence/generate-all")
def question_intelligence_generate_all(req: QuestionIntelligenceBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = question_intelligence_engine.generate_all(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Üretim başarısız"))
    log_module_run("question_intelligence_engine", "Generate All", req.model_dump(), {"count": result.get("count")})
    return result


@app.get("/api/question-intelligence/jobs")
def question_intelligence_jobs(limit: int = 20):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    return question_intelligence_engine.list_jobs(limit=limit)


@app.get("/api/question-intelligence/job/{job_id}")
def question_intelligence_job_detail(job_id: str):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    result = question_intelligence_engine.get_job_detail(job_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/question-intelligence/export-report")
def question_intelligence_export_report(req: QuestionIntelligenceExportBody):
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    result = question_intelligence_engine.export_report(
        job_id=req.job_id.strip(),
        export_format=req.format.strip() or "json",
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


class SiteReplicatorCloneBody(BaseModel):
    source_project_id: str = ""
    target_domain: str = ""
    target_site_name: str = ""
    content_strategy: str = "rewrite_all"
    theme_variation: bool = True
    auto_build: bool = True
    auto_deploy: bool = False
    main_site_url: str = ""


class SiteReplicatorVariantBody(BaseModel):
    base_project_id: str = ""
    domain_role: str = "faq_center"
    target_domain: str = ""
    main_site_url: str = ""


class SiteReplicatorBlueprintBody(BaseModel):
    url: str = ""


class SiteReplicatorTemplateBody(BaseModel):
    blueprint_id: str = ""
    target_domain: str = ""
    site_name: str = ""
    main_site_url: str = ""
    auto_build: bool = False


class SiteReplicatorProjectBody(BaseModel):
    project_id: str = ""


class SiteReplicatorJobBody(BaseModel):
    job_id: str = ""


@app.get("/api/site-replicator/health")
def site_replicator_health():
    from app.moduller.site_replicator import site_replicator
    return site_replicator.health()


@app.post("/api/site-replicator/clone-owned-site")
def site_replicator_clone(req: SiteReplicatorCloneBody):
    from app.moduller.site_replicator import site_replicator
    if not req.source_project_id.strip() or not req.target_domain.strip():
        raise HTTPException(status_code=400, detail="source_project_id ve target_domain gerekli")
    result = site_replicator.clone_owned_site(
        req.source_project_id.strip(),
        req.target_domain.strip(),
        req.target_site_name.strip() or req.target_domain.strip(),
        content_strategy=req.content_strategy,
        theme_variation=req.theme_variation,
        auto_build=req.auto_build,
        auto_deploy=req.auto_deploy,
        main_site_url=req.main_site_url,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("site_replicator", "Clone Owned Site", req.model_dump(), result.get("summary", {}))
    return result


@app.post("/api/site-replicator/create-domain-variant")
def site_replicator_variant(req: SiteReplicatorVariantBody):
    from app.moduller.site_replicator import site_replicator
    if not req.base_project_id.strip() or not req.target_domain.strip():
        raise HTTPException(status_code=400, detail="base_project_id ve target_domain gerekli")
    result = site_replicator.create_domain_variant(
        req.base_project_id.strip(),
        req.domain_role.strip(),
        req.target_domain.strip(),
        req.main_site_url,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("site_replicator", "Domain Variant", req.model_dump(), result.get("summary", {}))
    return result


@app.post("/api/site-replicator/analyze-competitor-blueprint")
def site_replicator_blueprint(req: SiteReplicatorBlueprintBody):
    from app.moduller.site_replicator import site_replicator
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    result = site_replicator.analyze_competitor_blueprint(req.url.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("site_replicator", "Competitor Blueprint", {"url": req.url}, {"blueprint_id": result.get("blueprint_id")})
    return result


@app.post("/api/site-replicator/generate-original-template")
def site_replicator_template(req: SiteReplicatorTemplateBody):
    from app.moduller.site_replicator import site_replicator
    if not req.blueprint_id.strip() or not req.target_domain.strip():
        raise HTTPException(status_code=400, detail="blueprint_id ve target_domain gerekli")
    result = site_replicator.generate_original_template(
        req.blueprint_id.strip(),
        req.target_domain.strip(),
        req.site_name.strip() or req.target_domain.strip(),
        req.main_site_url,
        auto_build=req.auto_build,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/site-replicator/build")
def site_replicator_build(req: SiteReplicatorProjectBody):
    from app.moduller.site_replicator import site_replicator
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = site_replicator.build_project(req.project_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Build başarısız"))
    return result


@app.post("/api/site-replicator/deploy-cloudflare")
def site_replicator_deploy(req: SiteReplicatorProjectBody):
    from app.moduller.site_replicator import site_replicator
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = site_replicator.deploy_cloudflare(req.project_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Deploy başarısız"))
    log_module_run("site_replicator", "Deploy Cloudflare", req.model_dump(), {"url": result.get("url")})
    return result


@app.get("/api/site-replicator/jobs")
def site_replicator_jobs(limit: int = 20):
    from app.moduller.site_replicator import site_replicator
    return site_replicator.list_jobs(limit=limit)


@app.get("/api/site-replicator/job/{job_id}")
def site_replicator_job_detail(job_id: str):
    from app.moduller.site_replicator import site_replicator
    result = site_replicator.get_job_detail(job_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/site-replicator/export-report")
def site_replicator_export(req: SiteReplicatorJobBody):
    from app.moduller.site_replicator import site_replicator
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = site_replicator.export_report(req.job_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


class NetworkReplicatorCreateBody(BaseModel):
    main_domain: str = ""
    name: str = ""


class NetworkReplicatorAddDomainBody(BaseModel):
    network_id: str = ""
    domain: str = ""
    role: str = ""
    project_id: str = ""


class NetworkReplicatorCloneBody(BaseModel):
    source_project_id: str = ""
    target_domain: str = ""
    target_site_name: str = ""
    network_id: str = ""
    role: str = ""
    main_site_url: str = ""


class NetworkReplicatorCloneManyBody(BaseModel):
    source_project_id: str = ""
    domains: list[str] = Field(default_factory=list)
    network_id: str = ""
    rewrite_mode: str = "balanced"
    retheme_style: str = "modern"
    auto_build: bool = True
    auto_deploy: bool = False
    main_site_url: str = ""


class NetworkReplicatorRewriteBody(BaseModel):
    project_id: str = ""
    mode: str = "balanced"


class NetworkReplicatorRethemeBody(BaseModel):
    project_id: str = ""
    style: str = "modern"


class NetworkReplicatorBlueprintBody(BaseModel):
    url: str = ""


class NetworkReplicatorVariantBody(BaseModel):
    blueprint_id: str = ""
    target_domain: str = ""
    site_name: str = ""
    role: str = "brand_hub"
    network_id: str = ""
    main_site_url: str = ""
    auto_build: bool = False


class NetworkReplicatorNetworkBody(BaseModel):
    network_id: str = ""


class NetworkReplicatorExportBody(BaseModel):
    network_id: str = ""
    job_id: str = ""


@app.get("/api/network-replicator/health")
def network_replicator_health():
    from app.moduller.network_replicator import network_replicator
    return network_replicator.health()


@app.post("/api/network-replicator/create-network")
def network_replicator_create(req: NetworkReplicatorCreateBody):
    from app.moduller.network_replicator import network_replicator
    if not req.main_domain.strip():
        raise HTTPException(status_code=400, detail="main_domain gerekli")
    result = network_replicator.create_network(req.main_domain.strip(), req.name.strip())
    _brain_emit("/api/network-replicator/create-network", req, result, module="network_replicator", event_type="network_created")
    return result


@app.post("/api/network-replicator/add-domain")
def network_replicator_add_domain(req: NetworkReplicatorAddDomainBody):
    from app.moduller.network_replicator import network_replicator
    if not req.network_id.strip() or not req.domain.strip():
        raise HTTPException(status_code=400, detail="network_id ve domain gerekli")
    result = network_replicator.add_domain(req.network_id.strip(), req.domain.strip(), req.role.strip(), req.project_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/network-replicator/clone-site")
def network_replicator_clone(req: NetworkReplicatorCloneBody):
    from app.moduller.network_replicator import network_replicator
    if not req.source_project_id.strip() or not req.target_domain.strip():
        raise HTTPException(status_code=400, detail="source_project_id ve target_domain gerekli")
    result = network_replicator.clone_site(
        req.source_project_id.strip(), req.target_domain.strip(), req.target_site_name.strip(),
        network_id=req.network_id.strip(), role=req.role.strip(), main_site_url=req.main_site_url,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("network_replicator", "Clone Site", req.model_dump(), {"target_project_id": result.get("target_project_id")})
    return result


@app.post("/api/network-replicator/clone-to-many")
def network_replicator_clone_many(req: NetworkReplicatorCloneManyBody):
    from app.moduller.network_replicator import network_replicator
    if not req.source_project_id.strip() or not req.domains:
        raise HTTPException(status_code=400, detail="source_project_id ve domains gerekli")
    result = network_replicator.clone_to_many(
        req.source_project_id.strip(), req.domains,
        network_id=req.network_id.strip(), rewrite_mode=req.rewrite_mode,
        retheme_style=req.retheme_style, auto_build=req.auto_build, auto_deploy=req.auto_deploy,
        main_site_url=req.main_site_url,
    )
    return result


@app.post("/api/network-replicator/rewrite-content")
def network_replicator_rewrite(req: NetworkReplicatorRewriteBody):
    from app.moduller.network_replicator import network_replicator
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = network_replicator.rewrite_content(req.project_id.strip(), req.mode)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/network-replicator/retheme-site")
def network_replicator_retheme(req: NetworkReplicatorRethemeBody):
    from app.moduller.network_replicator import network_replicator
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = network_replicator.retheme_site(req.project_id.strip(), req.style)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/network-replicator/build-network")
def network_replicator_build(req: NetworkReplicatorNetworkBody):
    from app.moduller.network_replicator import network_replicator
    if not req.network_id.strip():
        raise HTTPException(status_code=400, detail="network_id gerekli")
    return network_replicator.build_network(req.network_id.strip())


@app.post("/api/network-replicator/deploy-network")
def network_replicator_deploy(req: NetworkReplicatorNetworkBody):
    from app.moduller.network_replicator import network_replicator
    if not req.network_id.strip():
        raise HTTPException(status_code=400, detail="network_id gerekli")
    result = network_replicator.deploy_network(req.network_id.strip())
    log_module_run("network_replicator", "Deploy Network", req.model_dump(), {"deployed": result.get("deployed")})
    return result


@app.post("/api/network-replicator/analyze-blueprint")
def network_replicator_blueprint(req: NetworkReplicatorBlueprintBody):
    from app.moduller.network_replicator import network_replicator
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    result = network_replicator.analyze_blueprint(req.url.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/network-replicator/generate-variant")
def network_replicator_variant(req: NetworkReplicatorVariantBody):
    from app.moduller.network_replicator import network_replicator
    if not req.blueprint_id.strip() or not req.target_domain.strip():
        raise HTTPException(status_code=400, detail="blueprint_id ve target_domain gerekli")
    result = network_replicator.generate_variant(
        req.blueprint_id.strip(), req.target_domain.strip(), req.site_name.strip(),
        role=req.role.strip() or "brand_hub", network_id=req.network_id.strip(),
        main_site_url=req.main_site_url, auto_build=req.auto_build,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Variant üretilemedi"))
    return result


@app.get("/api/network-replicator/networks")
def network_replicator_list():
    from app.moduller.network_replicator import network_replicator
    return network_replicator.list_networks()


@app.get("/api/network-replicator/network/{network_id}")
def network_replicator_detail(network_id: str):
    from app.moduller.network_replicator import network_replicator
    result = network_replicator.get_network(network_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/network-replicator/export-report")
def network_replicator_export(req: NetworkReplicatorExportBody):
    from app.moduller.network_replicator import network_replicator
    result = network_replicator.export_report(network_id=req.network_id.strip(), job_id=req.job_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


class SEOQualityGateAnalyzeProjectBody(BaseModel):
    project_id: str = ""
    target_keyword: str = ""
    main_site_url: str = ""
    strict_mode: bool = True

class SEOQualityGateAnalyzeUrlBody(BaseModel):
    url: str = ""
    target_keyword: str = ""
    strict_mode: bool = True

class SEOQualityGateFixBody(BaseModel):
    report_id: str = ""
    use_llm: bool = True

class SEOQualityGateExportBody(BaseModel):
    report_id: str = ""
    format: str = "json"


@app.get("/api/seo-quality-gate/health")
def seo_quality_gate_health():
    from app.moduller.seo_quality_gate import health
    return health()


@app.post("/api/seo-quality-gate/analyze-project")
def seo_quality_gate_analyze_project(req: SEOQualityGateAnalyzeProjectBody):
    from app.moduller.seo_quality_gate import analyze_project
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = analyze_project(
            req.project_id.strip(),
            target_keyword=req.target_keyword,
            main_site_url=req.main_site_url,
            strict_mode=req.strict_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Analiz başarısız"))
    log_module_run("seo_quality_gate", "Analyze Project", req.model_dump(), {
        "score": result.get("overall_score"), "status": result.get("status"),
    })
    return result


@app.post("/api/seo-quality-gate/analyze-url")
def seo_quality_gate_analyze_url(req: SEOQualityGateAnalyzeUrlBody):
    from app.moduller.seo_quality_gate import analyze_url
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    result = analyze_url(req.url.strip(), req.target_keyword, req.strict_mode)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "URL analizi başarısız"))
    return result


@app.get("/api/seo-quality-gate/reports")
def seo_quality_gate_reports(limit: int = 50):
    from app.moduller.seo_quality_gate import list_reports
    return list_reports(limit)


@app.get("/api/seo-quality-gate/report/{report_id}")
def seo_quality_gate_report(report_id: str):
    from app.moduller.seo_quality_gate import get_report
    result = get_report(report_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Rapor yok"))
    return result


@app.post("/api/seo-quality-gate/fix-suggestions")
def seo_quality_gate_fix_suggestions(req: SEOQualityGateFixBody):
    from app.moduller.seo_quality_gate import fix_suggestions
    if not req.report_id.strip():
        raise HTTPException(status_code=400, detail="report_id gerekli")
    result = fix_suggestions(req.report_id.strip(), use_llm=req.use_llm)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Öneri üretilemedi"))
    return result


@app.post("/api/seo-quality-gate/export-report")
def seo_quality_gate_export_report(req: SEOQualityGateExportBody):
    from app.moduller.seo_quality_gate import export_report
    if not req.report_id.strip():
        raise HTTPException(status_code=400, detail="report_id gerekli")
    fmt = (req.format or "json").strip().lower()
    if fmt not in ("json", "md"):
        raise HTTPException(status_code=400, detail="format: json veya md")
    result = export_report(req.report_id.strip(), fmt)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Export başarısız"))
    return result


class RankWatcherRegisterBody(BaseModel):
    project_id: str = ""
    domain: str = ""


class RankWatcherUrlBody(BaseModel):
    url: str = ""
    project_id: str = ""


class RankWatcherDomainBody(BaseModel):
    domain: str = ""
    project_id: str = ""


class RankWatcherKeywordBody(BaseModel):
    keyword: str = ""
    domain: str = ""
    project_id: str = ""


class RankWatcherProjectBody(BaseModel):
    project_id: str = ""


class RankWatcherExportBody(BaseModel):
    project_id: str = ""
    format: str = "json"


@app.get("/api/rank-watcher/health")
def rank_watcher_health():
    from app.moduller.rank_index_watcher import rank_index_watcher
    return rank_index_watcher.health()


@app.get("/api/rank-watcher/projects")
def rank_watcher_projects():
    from app.moduller.rank_index_watcher import rank_index_watcher
    return rank_index_watcher.list_projects()


@app.get("/api/rank-watcher/project/{project_id}")
def rank_watcher_project(project_id: str):
    from app.moduller.rank_index_watcher import rank_index_watcher
    result = rank_index_watcher.get_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Proje yok"))
    return result


@app.post("/api/rank-watcher/register-project")
def rank_watcher_register(req: RankWatcherRegisterBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.project_id.strip() or not req.domain.strip():
        raise HTTPException(status_code=400, detail="project_id ve domain gerekli")
    try:
        return rank_index_watcher.register_project(req.project_id.strip(), req.domain.strip())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/rank-watcher/index-status")
def rank_watcher_index_status(req: RankWatcherUrlBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    result = rank_index_watcher.index_status(
        req.url.strip(),
        project_id=req.project_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    return result


@app.post("/api/rank-watcher/sitemap-status")
def rank_watcher_sitemap_status(req: RankWatcherDomainBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.domain.strip():
        raise HTTPException(status_code=400, detail="domain gerekli")
    try:
        return rank_index_watcher.sitemap_status(req.domain.strip())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/rank-watcher/track-keyword")
def rank_watcher_track_keyword(req: RankWatcherKeywordBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.keyword.strip() or not req.domain.strip():
        raise HTTPException(status_code=400, detail="keyword ve domain gerekli")
    result = rank_index_watcher.track_keyword(
        req.keyword.strip(),
        req.domain.strip(),
        project_id=req.project_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    return result


@app.post("/api/rank-watcher/bulk-track")
def rank_watcher_bulk_track(req: RankWatcherProjectBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = rank_index_watcher.bulk_track(req.project_id.strip())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/rank-watcher/ai-overview")
def rank_watcher_ai_overview(req: RankWatcherKeywordBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = rank_index_watcher.ai_overview(req.keyword.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    return result


@app.post("/api/rank-watcher/performance")
def rank_watcher_performance(req: RankWatcherDomainBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.domain.strip():
        raise HTTPException(status_code=400, detail="domain gerekli")
    result = rank_index_watcher.performance(
        req.domain.strip(),
        project_id=req.project_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    return result


@app.post("/api/rank-watcher/decay")
def rank_watcher_decay(req: RankWatcherProjectBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        return rank_index_watcher.decay_detector(req.project_id.strip())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/rank-watcher/opportunities")
def rank_watcher_opportunities(req: RankWatcherProjectBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        return rank_index_watcher.opportunity_finder(req.project_id.strip())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


class RankWatcherTalonHookBody(BaseModel):
    project_id: str = ""
    keywords: list[str] = []


@app.post("/api/rank-watcher/talon-hook")
def rank_watcher_talon_hook(req: RankWatcherTalonHookBody):
    """Talon Orchestrator — ileride keyword önceliği entegrasyonu."""
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        return rank_index_watcher.on_talon_keyword_priority(
            req.project_id.strip(),
            req.keywords or [],
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/rank-watcher/export")
def rank_watcher_export(req: RankWatcherExportBody):
    from app.moduller.rank_index_watcher import rank_index_watcher
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    fmt = (req.format or "json").strip().lower()
    if fmt not in ("json", "md"):
        raise HTTPException(status_code=400, detail="format: json veya md")
    try:
        result = rank_index_watcher.export_report(req.project_id.strip(), fmt)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


class EntityGeoGraphBuildBody(BaseModel):
    project_id: str = ""
    domain: str = ""
    seed_keyword: str = ""
    location: str = ""
    main_site_url: str = ""


class EntityGeoGraphProjectBody(BaseModel):
    project_id: str = ""


class EntityGeoGraphGeoExpandBody(BaseModel):
    location: str = ""
    radius_km: float = 30
    seed_keyword: str = ""


class EntityGeoGraphLinkPlanBody(BaseModel):
    project_id: str = ""
    max_links_per_page: int = 5


class EntityGeoGraphMissingBody(BaseModel):
    project_id: str = ""
    location: str = ""
    seed_keyword: str = ""


class EntityGeoGraphAnalyzeUrlBody(BaseModel):
    url: str = ""
    seed_keyword: str = ""
    location: str = ""


class EntityGeoGraphExportBody(BaseModel):
    graph_id: str = ""
    format: str = "json"


class ListingCreateBody(BaseModel):
    model_config = ConfigDict(extra="allow")


class ListingUpdateBody(BaseModel):
    model_config = ConfigDict(extra="allow")


class ListingBulkImportBody(BaseModel):
    format: str = "csv"
    mapping: dict[str, str] = {}
    preview_only: bool = False
    publish: bool = False


class ListingGenerateDescBody(BaseModel):
    use_llm: bool = True


class ListingFeatureBody(BaseModel):
    featured: bool = True
    vip: bool | None = None


class ListingMediaReorderBody(BaseModel):
    order: list[str] = []
    private: bool = False


class ListingMediaUrlBody(BaseModel):
    url: str = ""


class ListingSetCoverBody(BaseModel):
    media_id: str = ""


class ListingDeleteMediaBody(BaseModel):
    media_id: str = ""


class ListingImportCommitBody(BaseModel):
    job_id: str = ""


class ListingNameBody(BaseModel):
    name: str = ""
    slug: str = ""


class PlaceSEOPipelineJobBody(BaseModel):
    job_id: str = ""


class PlaceSEOPipelinePlanBody(BaseModel):
    job_id: str = ""
    main_site_url: str = ""


class PlaceSEOPipelineDryRunBody(BaseModel):
    job_id: str = ""
    main_site_url: str = ""
    dry_run: bool = False
    force: bool = False


class PlaceSEOPipelinePublishAllBody(BaseModel):
    job_id: str = ""
    main_site_url: str = ""
    run_gate: bool = True
    force: bool = False
    include_astro: bool = True


class PlaceSEOPipelineParseBody(BaseModel):
    upload_id: str = ""
    file_path: str = ""


class EntityDetailSelectTier1Body(BaseModel):
    source_job_id: str = ""
    job_id: str = ""
    main_site_url: str = ""
    threshold: int = 70
    manual_selections: dict[str, bool] = Field(default_factory=dict)


class EntityDetailJobBody(BaseModel):
    job_id: str = ""


class EntityDetailGenerateBody(BaseModel):
    job_id: str = ""
    main_site_url: str = ""
    entity_ids: list[str] = Field(default_factory=list)
    publish_wordpress: bool = True
    force: bool = False


class EntityDetailAstroBody(BaseModel):
    job_id: str = ""
    project_id: str = ""
    main_site_url: str = ""


class EntityDetailManualBody(BaseModel):
    job_id: str = ""
    selections: dict[str, bool] = Field(default_factory=dict)


@app.get("/api/listings")
def listings_list(status: str = "", search: str = "", limit: int = 100, offset: int = 0):
    from app.moduller.listing_hub import listing_hub
    return listing_hub.list_listings(status=status, search=search, limit=limit, offset=offset)


@app.get("/api/listing-hub/health")
def listing_hub_health():
    from app.moduller.listing_hub import listing_hub
    return listing_hub.health()


@app.get("/api/listing/{listing_id}")
def listing_get(listing_id: str):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.get_listing(listing_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "İlan yok"))
    return result


@app.post("/api/listing/create")
def listing_create(req: ListingCreateBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.create_listing(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Oluşturulamadı"))
    log_module_run("listing_hub", "İlan Oluştur", req.model_dump(), {"id": result["listing"]["id"]})
    return result


@app.put("/api/listing/update/{listing_id}")
def listing_update(listing_id: str, req: ListingUpdateBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.update_listing(listing_id, req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Güncellenemedi"))
    return result


@app.delete("/api/listing/delete/{listing_id}")
def listing_delete(listing_id: str, force: bool = False):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.delete_listing(listing_id, force=force)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Silinemedi"))
    return result


@app.post("/api/listing/publish/{listing_id}")
def listing_publish(listing_id: str):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.publish_listing(listing_id)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Yayınlanamadı"))
    log_module_run("listing_hub", "İlan Yayınla", {"listing_id": listing_id}, result.get("integrations", {}))
    return result


@app.post("/api/listing/unpublish/{listing_id}")
def listing_unpublish(listing_id: str):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.unpublish_listing(listing_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/generate-seo/{listing_id}")
def listing_generate_seo(listing_id: str):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.generate_seo(listing_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/generate-description/{listing_id}")
def listing_generate_description(listing_id: str, req: ListingGenerateDescBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.generate_description(listing_id, use_llm=req.use_llm)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/feature/{listing_id}")
def listing_feature(listing_id: str, req: ListingFeatureBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.feature_listing(listing_id, featured=req.featured, vip=req.vip)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/expire/{listing_id}")
def listing_expire(listing_id: str):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.expire_listing(listing_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/bulk-import")
async def listing_bulk_import(
    file: UploadFile = File(...),
    format: str = "csv",
    preview_only: bool = False,
    publish: bool = False,
    mapping: str = "{}",
):
    import json as _json
    from app.moduller.listing_hub import listing_hub
    raw = await file.read()
    try:
        mapping_dict = _json.loads(mapping) if mapping else {}
    except _json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="mapping geçerli JSON olmalı") from None
    fmt = format or (file.filename or "").rsplit(".", 1)[-1].lower()
    result = listing_hub.bulk_import(raw, fmt, mapping=mapping_dict, preview_only=preview_only, publish=publish)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/listing/bulk-media")
async def listing_bulk_media(file: UploadFile = File(...)):
    from app.moduller.listing_hub import listing_hub
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="ZIP dosyası gerekli")
    raw = await file.read()
    result = listing_hub.bulk_media_zip(raw)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/listing/upload-media/{listing_id}")
@app.post("/api/listing/{listing_id}/media")
async def listing_upload_media(
    listing_id: str,
    file: UploadFile = File(...),
    set_cover: bool = False,
):
    from app.moduller.listing_hub import listing_hub
    raw = await file.read()
    result = listing_hub.upload_media(
        listing_id, file.filename or "upload.jpg", raw, file.content_type or "", set_cover=set_cover,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/listing/upload-private-media/{listing_id}")
async def listing_upload_private_media(listing_id: str, file: UploadFile = File(...)):
    from app.moduller.listing_hub import listing_hub
    raw = await file.read()
    result = listing_hub.upload_private_media(listing_id, file.filename or "private.jpg", raw, file.content_type or "")
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/listing/set-cover/{listing_id}")
def listing_set_cover(listing_id: str, req: ListingSetCoverBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.set_cover(listing_id, req.media_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/reorder-media/{listing_id}")
@app.post("/api/listing/{listing_id}/media/reorder")
def listing_reorder_media(listing_id: str, req: ListingMediaReorderBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.reorder_media(listing_id, req.order, private=req.private)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/delete-media/{listing_id}")
def listing_delete_media(listing_id: str, req: ListingDeleteMediaBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.delete_media(listing_id, req.media_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/{listing_id}/media/from-url")
def listing_media_from_url(listing_id: str, req: ListingMediaUrlBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.import_media_from_url(listing_id, req.url)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/listing/run-quality-gate/{listing_id}")
def listing_run_quality_gate(listing_id: str):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.run_quality_gate(listing_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/listing/import-preview")
async def listing_import_preview(
    file: UploadFile = File(...),
    format: str = "csv",
    mapping: str = "{}",
):
    import json as _json
    from app.moduller.listing_hub import listing_hub
    raw = await file.read()
    try:
        mapping_dict = _json.loads(mapping) if mapping else {}
    except _json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="mapping geçerli JSON olmalı") from None
    fmt = format or (file.filename or "").rsplit(".", 1)[-1].lower()
    result = listing_hub.import_preview(raw, fmt, mapping=mapping_dict)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/listing/import-commit")
def listing_import_commit(req: ListingImportCommitBody):
    from app.moduller.listing_hub import listing_hub
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = listing_hub.import_commit(req.job_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.get("/api/listing/categories")
def listing_categories():
    from app.moduller.listing_hub import listing_hub
    return listing_hub.list_categories()


@app.post("/api/listing/categories/sync-from-category-hub")
def listing_categories_sync():
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.sync_categories_from_hub()
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.get("/api/listing/services")
def listing_services():
    from app.moduller.listing_hub import listing_hub
    return listing_hub.list_services()


@app.post("/api/listing/services/create")
def listing_service_create(req: ListingNameBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.create_service(req.name, req.slug)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.get("/api/listing/home-sections")
def listing_home_sections():
    from app.moduller.listing_hub import listing_hub
    return listing_hub.list_home_sections()


@app.post("/api/listing/home-sections/create")
def listing_home_section_create(req: ListingNameBody):
    from app.moduller.listing_hub import listing_hub
    result = listing_hub.create_home_section(req.name, req.slug)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.get("/api/place-seo/health")
def place_seo_health():
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    return place_seo_pipeline.health()


@app.post("/api/place-seo/upload")
async def place_seo_upload(file: UploadFile = File(...)):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    raw = await file.read()
    result = place_seo_pipeline.upload_file(file.filename or "upload.txt", raw, file.content_type or "")
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/place-seo/upload-batch")
async def place_seo_upload_batch(
    files: list[UploadFile] = File(...),
    main_site_url: str = Form(""),
    auto_pipeline: bool = Form(True),
):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not files:
        raise HTTPException(status_code=400, detail="En az 1 dosya seçin")
    items: list[tuple[str, bytes, str]] = []
    for f in files:
        raw = await f.read()
        items.append((f.filename or "upload.txt", raw, f.content_type or ""))
    result = place_seo_pipeline.process_batch_upload(
        items, main_site_url=main_site_url, auto_pipeline=auto_pipeline,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("place_seo_pipeline", "Batch Upload", {"files": len(items)}, {"job_id": result.get("job_id")})
    return result


@app.post("/api/place-seo/parse")
def place_seo_parse(req: PlaceSEOPipelineParseBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    result = place_seo_pipeline.parse_upload(upload_id=req.upload_id, file_path=req.file_path)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/place-seo/extract-signals")
def place_seo_extract_signals(req: PlaceSEOPipelineJobBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = place_seo_pipeline.extract_signals_for_job(req.job_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/place-seo/generate-content-plan")
def place_seo_generate_plan(req: PlaceSEOPipelinePlanBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    if not req.main_site_url.strip():
        raise HTTPException(status_code=400, detail="main_site_url zorunlu")
    result = place_seo_pipeline.generate_plan(req.job_id.strip(), req.main_site_url.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("place_seo_pipeline", "Generate Content Plan", req.model_dump(), {"pages": result.get("plan", {}).get("summary")})
    return result


@app.post("/api/place-seo/create-category-pages")
def place_seo_create_category_pages(req: PlaceSEOPipelineDryRunBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli — önce dosya yükleyin")
    result = place_seo_pipeline.create_category_pages(req.job_id.strip(), req.main_site_url, dry_run=req.dry_run, force=req.force)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/place-seo/create-geo-pages")
def place_seo_create_geo_pages(req: PlaceSEOPipelineDryRunBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli — önce dosya yükleyin")
    result = place_seo_pipeline.create_geo_pages(req.job_id.strip(), req.main_site_url, dry_run=req.dry_run, force=req.force)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/place-seo/create-faq-pages")
def place_seo_create_faq_pages(req: PlaceSEOPipelineDryRunBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli — önce dosya yükleyin")
    result = place_seo_pipeline.create_faq_pages(req.job_id.strip(), req.main_site_url, dry_run=req.dry_run, force=req.force)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/place-seo/publish-all")
def place_seo_publish_all(req: PlaceSEOPipelinePublishAllBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = place_seo_pipeline.publish_all_to_wordpress(
        req.job_id.strip(),
        req.main_site_url,
        run_gate=req.run_gate,
        force=req.force,
        include_astro=req.include_astro,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Yayın başarısız"))
    log_module_run("place_seo_pipeline", "Publish All", req.model_dump(), {
        "published": result.get("publish_report", {}).get("total_published"),
    })
    return result


@app.post("/api/place-seo/create-astro-support-site")
def place_seo_create_astro(req: PlaceSEOPipelinePlanBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = place_seo_pipeline.create_astro_support_site(req.job_id.strip(), req.main_site_url.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/place-seo/run-quality-gate")
def place_seo_quality_gate(req: PlaceSEOPipelineJobBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = place_seo_pipeline.run_quality_gate(req.job_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/place-seo/export-report")
def place_seo_export_report(req: PlaceSEOPipelineJobBody):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = place_seo_pipeline.export_report(req.job_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/place-seo/jobs")
def place_seo_jobs(limit: int = 50):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    return place_seo_pipeline.list_jobs(limit=limit)


@app.post("/api/place-seo/connect-wordpress")
def place_seo_connect_wordpress():
    from app.moduller.wordpress_api import ensure_wp_connected
    result = ensure_wp_connected(verify=True)
    if not result.get("connected"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=result.get("error", "WordPress bağlantısı kurulamadı"))
    return {"success": True, **result}


@app.get("/api/place-seo/job/{job_id}")
def place_seo_job_detail(job_id: str):
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    result = place_seo_pipeline.get_job_detail(job_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/entity-detail/health")
def entity_detail_health():
    from app.moduller.entity_detail_generator import entity_detail_generator
    return entity_detail_generator.health()


@app.post("/api/entity-detail/select-tier1")
def entity_detail_select_tier1(req: EntityDetailSelectTier1Body):
    from app.moduller.entity_detail_generator import entity_detail_generator
    if not req.source_job_id.strip():
        raise HTTPException(status_code=400, detail="source_job_id gerekli")
    result = entity_detail_generator.select_tier1(
        req.source_job_id.strip(),
        job_id=req.job_id.strip(),
        main_site_url=req.main_site_url,
        threshold=req.threshold,
        manual_selections=req.manual_selections or None,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("entity_detail_generator", "Select Tier1", req.model_dump(), {
        "job_id": result.get("job_id"),
        "tier1_selected": result.get("tier1_selected"),
    })
    return result


@app.post("/api/entity-detail/manual-selection")
def entity_detail_manual_selection(req: EntityDetailManualBody):
    from app.moduller.entity_detail_generator import entity_detail_generator
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = entity_detail_generator.update_manual_selection(req.job_id.strip(), req.selections or {})
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/entity-detail/generate-pages")
def entity_detail_generate_pages(req: EntityDetailGenerateBody):
    from app.moduller.entity_detail_generator import entity_detail_generator
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = entity_detail_generator.generate_pages(
        req.job_id.strip(),
        req.main_site_url,
        entity_ids=req.entity_ids or None,
        publish_wordpress=req.publish_wordpress,
        force=req.force,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("entity_detail_generator", "Generate Pages", req.model_dump(), {
        "generated_count": result.get("generated_count"),
        "published_count": result.get("published_count"),
    })
    return result


@app.post("/api/entity-detail/create-astro-pages")
def entity_detail_create_astro(req: EntityDetailAstroBody):
    from app.moduller.entity_detail_generator import entity_detail_generator
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = entity_detail_generator.create_astro_pages(
        req.job_id.strip(),
        project_id=req.project_id.strip(),
        main_site_url=req.main_site_url,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    log_module_run("entity_detail_generator", "Create Astro Pages", req.model_dump(), {
        "entity_pages_written": result.get("entity_pages_written"),
    })
    return result


@app.post("/api/entity-detail/run-quality-gate")
def entity_detail_quality_gate(req: EntityDetailJobBody):
    from app.moduller.entity_detail_generator import entity_detail_generator
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = entity_detail_generator.run_quality_gate(req.job_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    log_module_run("entity_detail_generator", "Quality Gate", req.model_dump(), {
        "deploy_allowed": result.get("deploy_allowed"),
    })
    return result


@app.post("/api/entity-detail/export-report")
def entity_detail_export_report(req: EntityDetailJobBody):
    from app.moduller.entity_detail_generator import entity_detail_generator
    if not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id gerekli")
    result = entity_detail_generator.export_report(req.job_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/entity-detail/jobs")
def entity_detail_jobs(limit: int = 20):
    from app.moduller.entity_detail_generator import entity_detail_generator
    return entity_detail_generator.list_jobs(limit=limit)


@app.get("/api/entity-detail/job/{job_id}")
def entity_detail_job_detail(job_id: str):
    from app.moduller.entity_detail_generator import entity_detail_generator
    result = entity_detail_generator.get_job_detail(job_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/entity-geo-graph/health")
def entity_geo_graph_health():
    from app.moduller.entity_geo_graph import entity_geo_graph
    return entity_geo_graph.health()


@app.post("/api/entity-geo-graph/build-project-graph")
def entity_geo_graph_build(req: EntityGeoGraphBuildBody):
    from app.moduller.entity_geo_graph import entity_geo_graph
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = entity_geo_graph.build_project_graph(
            req.project_id.strip(),
            domain=req.domain,
            seed_keyword=req.seed_keyword,
            location=req.location,
            main_site_url=req.main_site_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Graph oluşturulamadı"))
    log_module_run("entity_geo_graph", "Build Project Graph", req.model_dump(), {
        "graph_id": result.get("graph_id"),
        "nodes": result.get("summary", {}).get("node_count"),
    })
    return result


@app.post("/api/entity-geo-graph/analyze-url")
def entity_geo_graph_analyze_url(req: EntityGeoGraphAnalyzeUrlBody):
    from app.moduller.entity_geo_graph import entity_geo_graph
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    result = entity_geo_graph.analyze_url(req.url.strip(), req.seed_keyword, req.location)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "URL analizi başarısız"))
    return result


@app.post("/api/entity-geo-graph/geo-expand")
def entity_geo_graph_geo_expand(req: EntityGeoGraphGeoExpandBody):
    from app.moduller.entity_geo_graph import entity_geo_graph
    if not req.location.strip():
        raise HTTPException(status_code=400, detail="location gerekli")
    return entity_geo_graph.geo_expand(req.location.strip(), req.radius_km, req.seed_keyword)


@app.post("/api/entity-geo-graph/topic-clusters")
def entity_geo_graph_topic_clusters(req: EntityGeoGraphProjectBody):
    from app.moduller.entity_geo_graph import entity_geo_graph
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = entity_geo_graph.topic_clusters(req.project_id.strip())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/entity-geo-graph/internal-link-plan")
def entity_geo_graph_internal_link_plan(req: EntityGeoGraphLinkPlanBody):
    from app.moduller.entity_geo_graph import entity_geo_graph
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    try:
        result = entity_geo_graph.internal_link_plan(
            req.project_id.strip(), req.max_links_per_page,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/entity-geo-graph/missing-entities")
def entity_geo_graph_missing_entities(req: EntityGeoGraphMissingBody):
    from app.moduller.entity_geo_graph import entity_geo_graph
    try:
        result = entity_geo_graph.missing_entities(
            req.project_id.strip(),
            location=req.location,
            seed_keyword=req.seed_keyword,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.get("/api/entity-geo-graph/graphs")
def entity_geo_graph_list(limit: int = 50):
    from app.moduller.entity_geo_graph import entity_geo_graph
    return entity_geo_graph.list_graphs(limit)


@app.get("/api/entity-geo-graph/graph/{graph_id}")
def entity_geo_graph_get(graph_id: str):
    from app.moduller.entity_geo_graph import entity_geo_graph
    result = entity_geo_graph.get_graph(graph_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Graph yok"))
    return result


@app.post("/api/entity-geo-graph/export")
def entity_geo_graph_export(req: EntityGeoGraphExportBody):
    from app.moduller.entity_geo_graph import entity_geo_graph
    if not req.graph_id.strip():
        raise HTTPException(status_code=400, detail="graph_id gerekli")
    fmt = (req.format or "json").strip().lower()
    if fmt not in ("json", "md"):
        raise HTTPException(status_code=400, detail="format: json veya md")
    result = entity_geo_graph.export_graph(req.graph_id.strip(), fmt)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Export başarısız"))
    return result


@app.get("/api/storyforge/rules")
def storyforge_get_rules():
    return {"rules": load_rules()}


@app.post("/api/storyforge/rules")
def storyforge_save_rules(req: StoryForgeRulesBody):
    payload = {k: v for k, v in req.model_dump().items() if v not in (None, "", [], 0)}
    merged = save_rules(payload)
    return {"success": True, "rules": merged}


@app.post("/api/storyforge/quick")
def storyforge_quick(req: StoryForgeQuickBody):
    if not req.text or len(req.text.strip()) < 80:
        raise HTTPException(status_code=400, detail="Hikaye metni en az 80 karakter olmalı")
    result = storyforge.quick_rewrite_publish(
        text=req.text.strip(),
        title=req.title.strip(),
        auto_publish=req.auto_publish,
        category_slug=req.category_slug.strip() or "gece-hikaye",
        preview_only=req.preview_only,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", result.get("publish_error", "İşlem başarısız")))
    try:
        log_module_run("storyforge", "Quick paste", {"chars": len(req.text), "published": result.get("published")}, result)
    except Exception:
        pass
    return result


@app.post("/api/storyforge/paste-preview")
def storyforge_paste_preview(req: StoryForgePasteBody):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Metin gerekli")
    return preview_bulk_text(req.text, req.filename or "paste.txt")


@app.post("/api/storyforge/paste-run")
def storyforge_paste_run(req: StoryForgePasteRunBody):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Metin gerekli")
    result = storyforge.paste_and_run_bulk(
        text=req.text,
        filename=req.filename or "paste.txt",
        auto_publish=req.auto_publish,
        category_slug=req.category_slug.strip() or "gece-hikaye",
        delay_sec=max(0.0, req.delay_sec),
        offset=max(0, req.offset),
        limit=max(0, req.limit),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Toplu iş başlatılamadı"))
    try:
        log_module_run("storyforge", "Paste bulk run", {"count": result.get("import_count")}, result)
    except Exception:
        pass
    return result


@app.post("/api/storyforge/import-text")
def storyforge_import_text(req: StoryForgePasteBody):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Metin gerekli")
    result = import_from_text(req.text, req.filename or "paste.txt")
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "İçe aktarma başarısız"))
    return result


@app.post("/api/storyforge/import")
async def storyforge_import(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya gerekli")
    raw = await file.read()
    if len(raw) > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Dosya en fazla 500 MB olabilir")
    fname = file.filename or ""
    if fname.lower().endswith(".docx"):
        text = parse_docx_bytes(raw)
        if not text:
            raise HTTPException(status_code=422, detail="Word dosyası okunamadı")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")
    stories = parse_bulk_content(text, fname)
    result = save_import_stories(stories)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Parse başarısız"))
    try:
        log_module_run("storyforge", "Bulk import", {"filename": file.filename, "count": result["count"]}, result)
    except Exception:
        pass
    return result


@app.get("/api/storyforge/import/{import_id}")
def storyforge_import_info(import_id: str):
    info = get_import_info(import_id)
    if not info.get("success"):
        raise HTTPException(status_code=404, detail=info.get("error", "Import bulunamadı"))
    return info


@app.post("/api/storyforge/bulk-rewrite")
def storyforge_bulk_rewrite(req: StoryForgeBulkRewriteBody):
    if not req.import_id.strip():
        raise HTTPException(status_code=400, detail="import_id gerekli")
    result = storyforge.start_bulk_import_job(
        import_id=req.import_id.strip(),
        auto_publish=req.auto_publish,
        category_slug=req.category_slug.strip() or "gece-hikaye",
        delay_sec=max(0.0, req.delay_sec),
        offset=max(0, req.offset),
        limit=max(0, req.limit),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Toplu iş başlatılamadı"))
    try:
        log_module_run("storyforge", "Bulk rewrite", req.model_dump(), result)
    except Exception:
        pass
    return result


@app.post("/api/storyforge/publish")
def storyforge_publish(req: StoryForgePublishBody):
    if not req.title.strip() or not req.content.strip():
        raise HTTPException(status_code=400, detail="Başlık ve içerik gerekli")
    featured_id = req.featured_media_id or None
    if not featured_id:
        featured_id = storyforge.pick_photo_media_id(0)
    result = storyforge.publish_to_wordpress(
        title=req.title.strip(),
        content=req.content,
        lokasyon=req.lokasyon.strip(),
        excerpt=req.excerpt.strip(),
        category_slug=req.category_slug.strip() or "gece-hikaye",
        status=req.status or "publish",
        pending_id=req.pending_id.strip() or None,
        featured_media_id=featured_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Yayınlanamadı"))
    try:
        log_module_run("storyforge", "Publish", {"title": req.title}, result)
    except Exception:
        pass
    return result


# ==================== STORYFORGE V3 (fastCRW + Ollama + WP) ====================
class StoryForgeV3ProcessBody(BaseModel):
    url: str = ""
    title: str = ""
    auto_publish: bool = True
    category_slug: str = "gece-hikaye"


class StoryForgeV3RewriteBody(BaseModel):
    text: str = ""
    title: str = ""
    custom_rules: str = ""


class StoryForgeV3ScrapeBody(BaseModel):
    url: str = ""


class StoryForgeV3PublishPreviewBody(BaseModel):
    title: str = ""
    content: str = ""
    lokasyon: str = ""
    excerpt: str = ""
    category_slug: str = "gece-hikaye"


class StoryForgeV3PublishBody(BaseModel):
    title: str = ""
    content: str = ""
    lokasyon: str = ""
    excerpt: str = ""
    category_slug: str = "gece-hikaye"
    source_url: str = ""


@app.get("/api/storyforge-v3/health")
def storyforge_v3_health():
    from app.moduller.storyforge_v3 import storyforge_v3
    return storyforge_v3.health()


@app.get("/api/storyforge-v3/smoke-test")
def storyforge_v3_smoke_test():
    from app.moduller.storyforge_v3 import storyforge_v3
    result = storyforge_v3.smoke_test()
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Smoke test başarısız"))
    return result


@app.get("/api/storyforge-v3/history")
def storyforge_v3_history(limit: int = 20):
    from app.moduller.storyforge_v3 import storyforge_v3
    return storyforge_v3.list_history(limit=limit)


@app.post("/api/storyforge-v3/scrape")
def storyforge_v3_scrape(req: StoryForgeV3ScrapeBody):
    from app.moduller.storyforge_v3 import storyforge_v3
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    try:
        result = storyforge_v3.scrape_url(req.url.strip())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Scrape başarısız"))
    return result


@app.get("/api/storyforge-v3/rules")
def storyforge_v3_rules():
    from app.moduller.storyforge_v3 import storyforge_v3
    return storyforge_v3.get_rules()


@app.post("/api/storyforge-v3/rewrite")
def storyforge_v3_rewrite(req: StoryForgeV3RewriteBody):
    from app.moduller.storyforge_v3 import storyforge_v3
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text gerekli")
    result = storyforge_v3.rewrite_story(
        req.text.strip(),
        req.title.strip(),
        custom_rules=req.custom_rules.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Yeniden yazma başarısız"))
    return result


@app.post("/api/storyforge-v3/preview-publish")
def storyforge_v3_preview_publish(req: StoryForgeV3PublishPreviewBody):
    from app.moduller.storyforge_v3 import storyforge_v3
    if not req.title.strip() or not req.content.strip():
        raise HTTPException(status_code=400, detail="title ve content gerekli")
    result = storyforge_v3.preview_publish(
        req.title.strip(),
        req.content.strip(),
        lokasyon=req.lokasyon.strip(),
        excerpt=req.excerpt.strip(),
        category_slug=req.category_slug.strip() or "gece-hikaye",
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Önizleme üretilemedi"))
    return result


@app.post("/api/storyforge-v3/publish")
def storyforge_v3_publish(req: StoryForgeV3PublishBody):
    from app.moduller.storyforge_v3 import storyforge_v3
    if not req.title.strip() or not req.content.strip():
        raise HTTPException(status_code=400, detail="title ve content gerekli")
    result = storyforge_v3.publish_story(
        req.title.strip(),
        req.content.strip(),
        lokasyon=req.lokasyon.strip(),
        excerpt=req.excerpt.strip(),
        category_slug=req.category_slug.strip() or "gece-hikaye",
        source_url=req.source_url.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Yayın başarısız"))
    return result


@app.get("/api/storyforge-v3/verify/{post_id}")
def storyforge_v3_verify(post_id: int, link: str = ""):
    from app.moduller.storyforge_v3 import storyforge_v3
    return storyforge_v3.verify_publication(post_id, link)


@app.get("/api/storyforge/scraper/health")
def storyforge_scraper_health():
    return storyforge_v3_health()


@app.get("/api/storyforge/scraper/history")
def storyforge_scraper_history(limit: int = 20):
    return storyforge_v3_history(limit=limit)


@app.post("/api/storyforge/scrape")
def storyforge_scrape(req: StoryForgeV3ScrapeBody):
    return storyforge_v3_scrape(req)


@app.post("/api/storyforge/scrape/rewrite")
def storyforge_scrape_rewrite(req: StoryForgeV3RewriteBody):
    return storyforge_v3_rewrite(req)


@app.post("/api/storyforge/scrape/preview-publish")
def storyforge_scrape_preview_publish(req: StoryForgeV3PublishPreviewBody):
    return storyforge_v3_preview_publish(req)


@app.post("/api/storyforge/scrape/publish")
def storyforge_scrape_publish(req: StoryForgeV3PublishBody):
    return storyforge_v3_publish(req)


@app.get("/api/storyforge/scrape/verify/{post_id}")
def storyforge_scrape_verify(post_id: int, link: str = ""):
    return storyforge_v3_verify(post_id, link)


@app.post("/api/storyforge-v3/process")
@app.post("/api/storyforge/process")
def storyforge_v3_process(req: StoryForgeV3ProcessBody):
    from app.moduller.storyforge_v3 import storyforge_v3
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url gerekli")
    try:
        result = storyforge_v3.process_story(
            req.url.strip(),
            title=req.title.strip(),
            auto_publish=req.auto_publish,
            category_slug=req.category_slug.strip() or "gece-hikaye",
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "İşlem başarısız"))
    try:
        log_module_run("storyforge_v3", "Process", {"url": req.url}, {"published": result.get("published")})
    except Exception:
        pass
    return result


# ==================== TUMBLR OAuth 1.0a ====================
@app.get("/api/tumblr/connect")
def tumblr_connect():
    request_token = get_request_token()
    auth_url = get_authorize_url(request_token["oauth_token"])
    return {
        "authorize_url": auth_url,
        "oauth_token": request_token["oauth_token"],
        "callback_url": request_token.get("callback_url", ""),
    }


@app.get("/api/tumblr/callback")
def tumblr_callback(oauth_token: str, oauth_verifier: str):
    oauth_token_secret = get_pending_secret(oauth_token)
    access_token_data = get_access_token(oauth_token, oauth_verifier, oauth_token_secret)
    try:
        log_module_run("tumblr", "Tumblr OAuth bağlantı", {"oauth_token": oauth_token[:8] + "..."}, {"connected": True})
    except Exception:
        pass
    return {"message": "Tumblr başarıyla bağlandı!", "token": access_token_data}


@app.get("/api/tumblr/status")
def tumblr_status():
    return connection_status()


@app.get("/api/tumblr/blogs")
def tumblr_blogs():
    blogs = fetch_user_blogs()
    if not blogs:
        raise HTTPException(status_code=401, detail="Tumblr bağlı değil veya blog listesi alınamadı")
    return {"blogs": blogs}


@app.post("/api/tumblr/post")
def tumblr_post(req: ModulRequest):
    blog_name = getattr(req, "blog_name", "") or ""
    content = getattr(req, "content", "")
    title = getattr(req, "title", "") or ""
    tags = getattr(req, "tags", None) or []
    oauth_token = getattr(req, "oauth_token", None)
    oauth_token_secret = getattr(req, "oauth_token_secret", None)
    state = getattr(req, "state", "published") or "published"

    result = post_to_tumblr(
        blog_name,
        content,
        title,
        tags,
        oauth_token,
        oauth_token_secret,
        state=state,
    )
    post_id = (result.get("response") or {}).get("id")
    try:
        log_module_run("tumblr", "Tumblr post", {"blog_name": blog_name, "title": title}, {"post_id": post_id})
    except Exception:
        pass
    return {"success": True, "post_id": post_id, "response": result}


@app.post("/api/tumblr/disconnect")
def tumblr_disconnect():
    from app.moduller.tumblr_api import TOKEN_FILE
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    return {"success": True, "message": "Tumblr token dosyası silindi"}


class TumblrAutoBody(BaseModel):
    topic: str
    city: str = "Kuşadası"
    district: str = ""
    site_url: str = ""
    extra_keywords: list[str] = []
    blog_name: str = ""
    publish: bool = True


@app.post("/api/tumblr/generate")
def tumblr_generate(req: TumblrAutoBody):
    from app.moduller.tumblr_content import generate_tumblr_content

    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Konu (topic) gerekli")
    result = generate_tumblr_content(
        topic=req.topic,
        city=req.city,
        district=req.district,
        site_url=req.site_url,
        extra_keywords=req.extra_keywords,
    )
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "İçerik üretilemedi"))
    return result


@app.post("/api/tumblr/auto-post")
def tumblr_auto_post(req: TumblrAutoBody):
    from app.moduller.tumblr_content import auto_publish, generate_tumblr_content

    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Konu (topic) gerekli")

    if req.publish:
        result = auto_publish(
            topic=req.topic,
            city=req.city,
            district=req.district,
            site_url=req.site_url,
            extra_keywords=req.extra_keywords,
            blog_name=req.blog_name,
        )
    else:
        result = generate_tumblr_content(
            topic=req.topic,
            city=req.city,
            district=req.district,
            site_url=req.site_url,
            extra_keywords=req.extra_keywords,
        )

    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "İşlem başarısız"))
    try:
        log_module_run(
            "tumblr",
            "Tumblr otomatik yayın" if req.publish else "Tumblr içerik üret",
            {"topic": req.topic, "city": req.city},
            {"post_id": result.get("post_id"), "mode": result.get("mode")},
        )
    except Exception:
        pass
    return result


# ==================== BLOGGER ====================
class BloggerPostBody(BaseModel):
    title: str = ""
    content: str = ""
    blog_id: str = ""
    labels: list[str] = []
    publish: bool = True


@app.get("/api/blogger/status")
def blogger_status():
    from app.moduller.blogger_api import get_status
    return get_status()


@app.get("/api/blogger/blogs")
def blogger_blogs():
    from app.moduller.blogger_api import list_blogs, is_configured
    if not is_configured():
        raise HTTPException(status_code=400, detail="Blogger OAuth yapılandırılmamış")
    try:
        return list_blogs()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/blogger/posts")
def blogger_posts(blog_id: str = "", status: str = "live", limit: int = 20):
    from app.moduller.blogger_api import list_posts, is_configured
    if not is_configured():
        raise HTTPException(status_code=400, detail="Blogger OAuth yapılandırılmamış")
    try:
        return list_posts(blog_id=blog_id or None, max_results=limit, status=status)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/blogger/post")
def blogger_create_post(req: BloggerPostBody):
    from app.moduller.blogger_api import create_post, is_configured
    if not is_configured():
        raise HTTPException(status_code=400, detail="Blogger OAuth yapılandırılmamış")
    try:
        result = create_post(
            title=req.title,
            content=req.content,
            blog_id=req.blog_id or None,
            labels=req.labels,
            publish=req.publish,
        )
        log_module_run("blogger", "Blogger post", {"title": req.title, "publish": req.publish}, result)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/blogger/publish/{post_id}")
def blogger_publish_post(post_id: str, blog_id: str = ""):
    from app.moduller.blogger_api import publish_post, is_configured
    if not is_configured():
        raise HTTPException(status_code=400, detail="Blogger OAuth yapılandırılmamış")
    try:
        return publish_post(post_id, blog_id or None)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ==================== PUBLISHER HUB V1 ====================
class PublisherEnqueueBody(BaseModel):
    source: str = ""
    source_id: str = ""
    content_type: str = "blog"
    title: str = ""
    content_html: str = ""
    slug: str = ""
    keyword: str = ""
    canonical_url: str = ""
    tags: list[str] = []
    project_id: str = ""
    network_id: str = ""
    domain: str = ""
    channels: list[str] = []
    skip_quality: bool = False


class PublisherSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


class PublisherApproveBody(BaseModel):
    publish_id: str
    channels: list[str] = []


class PublisherPublishBody(BaseModel):
    publish_id: str
    channels: list[str] = []


class PublisherRequeueBody(BaseModel):
    project_id: str = ""
    page_id: str = ""


@app.get("/api/publisher-hub/health")
def publisher_hub_health():
    from app.moduller.publisher_hub import health
    return health()


@app.get("/api/publisher-hub/settings")
def publisher_hub_get_settings():
    from app.moduller.publisher_hub import get_settings
    return {"settings": get_settings()}


@app.post("/api/publisher-hub/settings")
def publisher_hub_update_settings(req: PublisherSettingsBody):
    from app.moduller.publisher_hub import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


@app.get("/api/publisher-hub/channels")
def publisher_hub_channels():
    from app.moduller.publisher_hub import list_channels
    return {"channels": list_channels()}


@app.get("/api/publisher-hub/sources/scan")
def publisher_hub_scan_sources(source: str = ""):
    from app.moduller.publisher_hub import scan_sources
    return scan_sources(source)


@app.post("/api/publisher-hub/enqueue")
def publisher_hub_enqueue(req: PublisherEnqueueBody):
    from app.moduller.publisher_hub import enqueue
    result = enqueue(req.model_dump(), channels=req.channels or None, skip_quality=req.skip_quality)
    if not result.get("success") and result.get("status") != "review_required":
        raise HTTPException(status_code=400, detail=result.get("error", "Kuyruğa alınamadı"))
    return result


@app.post("/api/publisher-hub/approve")
def publisher_hub_approve(req: PublisherApproveBody):
    from app.moduller.publisher_hub import approve_draft
    result = approve_draft(req.publish_id, req.channels or None)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Onaylanamadı"))
    return result


@app.post("/api/publisher-hub/publish")
def publisher_hub_publish(req: PublisherPublishBody):
    from app.moduller.publisher_hub import publish_item
    result = publish_item(req.publish_id, req.channels or None)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Yayın başarısız"))
    _brain_emit("/api/publisher-hub/publish", req, result, module="publisher_hub", event_type="publisher_success")
    return result


@app.post("/api/publisher-hub/process")
def publisher_hub_process(max_items: int = 0):
    from app.moduller.publisher_hub import process_queue
    return process_queue(max_items or None)


@app.post("/api/publisher-hub/requeue-refresh")
def publisher_hub_requeue_refresh(req: PublisherRequeueBody):
    from app.moduller.publisher_hub import requeue_from_refresh
    return requeue_from_refresh(req.project_id, req.page_id)


@app.get("/api/publisher-hub/queue")
def publisher_hub_queue():
    from app.moduller.publisher_hub import get_queue
    return get_queue()


@app.get("/api/publisher-hub/drafts")
def publisher_hub_drafts():
    from app.moduller.publisher_hub import get_drafts
    return get_drafts()


@app.get("/api/publisher-hub/published")
def publisher_hub_published(limit: int = 50):
    from app.moduller.publisher_hub import get_published
    return get_published(limit)


@app.get("/api/publisher-hub/jobs")
def publisher_hub_jobs(limit: int = 30):
    from app.moduller.publisher_hub import get_jobs
    return get_jobs(limit)


@app.post("/api/publisher-hub/export-report")
def publisher_hub_export(job_id: str = "", publish_id: str = ""):
    from app.moduller.publisher_hub import export_report
    return export_report(job_id=job_id, publish_id=publish_id)


class SupportNetworkSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


class SupportNetworkRoleBody(BaseModel):
    domain: str
    index: int = 0


class SupportNetworkReportBody(BaseModel):
    report_type: str = "overview"
    network_id: str = ""
    format: str = "json"


@app.get("/api/support-network/health")
def support_network_health():
    from app.moduller.support_network_engine import health
    return health()


@app.get("/api/support-network/dashboard")
def support_network_dashboard(network_id: str = ""):
    from app.moduller.support_network_engine import dashboard
    return dashboard(network_id)


@app.get("/api/support-network/networks")
def support_network_list_networks():
    from app.moduller.support_network_engine import list_networks_api
    return list_networks_api()


@app.get("/api/support-network/domains")
def support_network_domains(network_id: str = ""):
    from app.moduller.support_network_engine import list_domains
    return list_domains(network_id)


@app.get("/api/support-network/network/{network_id}")
def support_network_get_network(network_id: str):
    from app.moduller.support_network_engine import get_network
    result = get_network(network_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Network bulunamadı"))
    return result


@app.get("/api/support-network/domain/{domain}")
def support_network_get_domain(domain: str):
    from app.moduller.support_network_engine import get_domain
    result = get_domain(domain)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Domain bulunamadı"))
    return result


@app.get("/api/support-network/authority")
def support_network_authority(network_id: str = ""):
    from app.moduller.support_network_engine import authority_map
    result = authority_map(network_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Authority analizi yapılamadı"))
    return result


@app.get("/api/support-network/links")
def support_network_links(network_id: str = "", max_per_domain: int = 5):
    from app.moduller.support_network_engine import link_strategy
    result = link_strategy(network_id, max_per_domain=max_per_domain)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Link planı üretilemedi"))
    return result


@app.get("/api/support-network/keywords")
def support_network_keywords(network_id: str = ""):
    from app.moduller.support_network_engine import keyword_distribution
    return keyword_distribution(network_id)


@app.get("/api/support-network/gaps")
def support_network_gaps(network_id: str = ""):
    from app.moduller.support_network_engine import network_gaps
    return network_gaps(network_id)


@app.get("/api/support-network/opportunities")
def support_network_opportunities(network_id: str = ""):
    from app.moduller.support_network_engine import growth_opportunities
    return growth_opportunities(network_id)


@app.get("/api/support-network/publishers")
def support_network_publishers(network_id: str = ""):
    from app.moduller.support_network_engine import publisher_channels_view
    return publisher_channels_view(network_id)


@app.get("/api/support-network/settings")
def support_network_get_settings():
    from app.moduller.support_network_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/support-network/settings")
def support_network_update_settings(req: SupportNetworkSettingsBody):
    from app.moduller.support_network_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


@app.post("/api/support-network/sync")
def support_network_sync(network_id: str = ""):
    from app.moduller.support_network_engine import sync_network
    result = sync_network(network_id)
    _brain_emit("/api/support-network/sync", {"network_id": network_id}, result, module="support_network_engine", event_type="network_updated")
    return result


@app.post("/api/support-network/suggest-role")
def support_network_suggest_role(req: SupportNetworkRoleBody):
    from app.moduller.support_network_engine import suggest_role
    return suggest_role(req.domain, req.index)


@app.post("/api/support-network/report")
def support_network_report(report_type: str = "overview", network_id: str = ""):
    from app.moduller.support_network_engine import export_report
    return export_report(report_type=report_type, network_id=network_id)


@app.post("/api/support-network/report/export")
def support_network_report_export(req: SupportNetworkReportBody):
    from app.moduller.support_network_engine import export_report
    return export_report(report_type=req.report_type, network_id=req.network_id)


class SerpDefenseAnalyzeBody(BaseModel):
    keyword: str = ""
    project_id: str = ""
    domain: str = ""


class SerpDefensePlanBody(BaseModel):
    keyword: str = ""
    project_id: str = ""


class SerpDefenseExecuteBody(BaseModel):
    plan_id: str = ""
    keyword: str = ""
    project_id: str = ""
    auto_publish: bool | None = None
    auto_deploy: bool | None = None


class SerpDefenseRefreshLiveBody(BaseModel):
    project_id: str = ""
    keyword: str = ""
    domain: str = ""
    refresh_gsc: bool = True
    refresh_rank: bool = True
    refresh_ai: bool = False


class SerpDefenseSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/serp-defense/health")
def serp_defense_health():
    from app.moduller.serp_defense_engine import health
    return health()


@app.get("/api/serp-defense/dashboard")
def serp_defense_dashboard(project_id: str = ""):
    from app.moduller.serp_defense_engine import dashboard
    return dashboard(project_id)


@app.post("/api/serp-defense/analyze-keyword")
def serp_defense_analyze_keyword(req: SerpDefenseAnalyzeBody):
    from app.moduller.serp_defense_engine import analyze_keyword
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = analyze_keyword(req.keyword, project_id=req.project_id, domain=req.domain)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Analiz başarısız"))
    _brain_emit("/api/serp-defense/analyze-keyword", req, result, module="serp_defense_engine", event_type="serp_defense_triggered")
    return result


@app.post("/api/serp-defense/analyze-project")
def serp_defense_analyze_project(project_id: str = "", req: SerpDefenseAnalyzeBody | None = None):
    from app.moduller.serp_defense_engine import analyze_project
    pid = (req.project_id if req else "") or project_id
    if not pid:
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = analyze_project(pid)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Proje analizi başarısız"))
    return result


@app.get("/api/serp-defense/fortress")
def serp_defense_fortress(project_id: str = ""):
    from app.moduller.serp_defense_engine import fortress_list
    return fortress_list(project_id)


@app.get("/api/serp-defense/attack-surface")
def serp_defense_attack_surface(project_id: str = ""):
    from app.moduller.serp_defense_engine import attack_surface_list
    return attack_surface_list(project_id)


@app.get("/api/serp-defense/pressure")
def serp_defense_pressure(project_id: str = ""):
    from app.moduller.serp_defense_engine import pressure_overview
    return pressure_overview(project_id)


@app.get("/api/serp-defense/opportunities")
def serp_defense_opportunities(project_id: str = ""):
    from app.moduller.serp_defense_engine import defense_opportunities
    return defense_opportunities(project_id)


@app.post("/api/serp-defense/generate-plan")
def serp_defense_generate_plan(req: SerpDefensePlanBody):
    from app.moduller.serp_defense_engine import generate_plan
    result = generate_plan(keyword=req.keyword, project_id=req.project_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Plan üretilemedi"))
    _brain_emit("/api/serp-defense/generate-plan", req, result, module="serp_defense_engine", event_type="serp_defense_triggered")
    return result


@app.post("/api/serp-defense/execute-plan")
def serp_defense_execute_plan(req: SerpDefenseExecuteBody):
    from app.moduller.serp_defense_engine import execute_defense_plan
    result = execute_defense_plan(
        plan_id=req.plan_id,
        keyword=req.keyword,
        project_id=req.project_id,
        auto_publish=req.auto_publish,
        auto_deploy=req.auto_deploy,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or result.get("message") or "Plan uygulanamadı")
    _brain_emit("/api/serp-defense/execute-plan", req, result, module="serp_defense_engine", event_type="serp_defense_executed")
    return result


@app.post("/api/serp-defense/refresh-live-data")
def serp_defense_refresh_live_data(req: SerpDefenseRefreshLiveBody):
    from app.moduller.serp_defense_engine import refresh_live_data
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = refresh_live_data(
        req.project_id,
        req.keyword,
        req.domain,
        refresh_gsc=req.refresh_gsc,
        refresh_rank=req.refresh_rank,
        refresh_ai=req.refresh_ai,
    )
    return result


@app.post("/api/serp-defense/export-report")
def serp_defense_export_report(report_type: str = "fortress", project_id: str = "", keyword: str = ""):
    from app.moduller.serp_defense_engine import export_report
    return export_report(report_type=report_type, project_id=project_id, keyword=keyword)


@app.get("/api/serp-defense/settings")
def serp_defense_get_settings():
    from app.moduller.serp_defense_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/serp-defense/settings")
def serp_defense_update_settings(req: SerpDefenseSettingsBody):
    from app.moduller.serp_defense_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class CrawlGapAnalyzeDomainBody(BaseModel):
    own_domain: str = ""
    competitor_domains: list[str] = Field(default_factory=list)
    project_id: str = ""
    export_to_opportunity: bool = False


class CrawlGapAnalyzeProjectBody(BaseModel):
    project_id: str = ""
    competitor_domains: list[str] = Field(default_factory=list)
    export_to_opportunity: bool = False


class CrawlGapSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/crawl-gap/health")
def crawl_gap_health():
    from app.moduller.crawl_gap_engine import health
    return health()


@app.get("/api/crawl-gap/dashboard")
def crawl_gap_dashboard(project_id: str = ""):
    from app.moduller.crawl_gap_engine import dashboard
    return dashboard(project_id)


@app.post("/api/crawl-gap/analyze-domain")
def crawl_gap_analyze_domain(req: CrawlGapAnalyzeDomainBody):
    from app.moduller.crawl_gap_engine import analyze_domain
    if not req.own_domain.strip() and not req.competitor_domains:
        raise HTTPException(status_code=400, detail="own_domain veya competitor_domains gerekli")
    result = analyze_domain(
        own_domain=req.own_domain.strip(),
        competitor_domains=req.competitor_domains,
        project_id=req.project_id.strip(),
        export_to_opportunity=req.export_to_opportunity,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    _brain_emit("/api/crawl-gap/analyze-domain", req, result, module="crawl_gap_engine")
    return result


@app.post("/api/crawl-gap/analyze-project")
def crawl_gap_analyze_project(req: CrawlGapAnalyzeProjectBody):
    from app.moduller.crawl_gap_engine import analyze_project
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = analyze_project(
        req.project_id.strip(),
        competitor_domains=req.competitor_domains,
        export_to_opportunity=req.export_to_opportunity,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    _brain_emit("/api/crawl-gap/analyze-project", req, result, module="crawl_gap_engine")
    return result


class CrawlGapCompetitorBody(BaseModel):
    competitor_domain: str = ""
    own_domain: str = ""
    project_id: str = ""


class CrawlGapCompareBody(BaseModel):
    own_domain: str = ""
    competitor_domain: str = ""
    project_id: str = ""


@app.post("/api/crawl-gap/analyze-competitor")
def crawl_gap_analyze_competitor(req: CrawlGapCompetitorBody):
    from app.moduller.crawl_gap_engine import analyze_competitor
    if not req.competitor_domain.strip():
        raise HTTPException(status_code=400, detail="competitor_domain gerekli")
    result = analyze_competitor(
        req.competitor_domain.strip(),
        own_domain=req.own_domain.strip(),
        project_id=req.project_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    _brain_emit("/api/crawl-gap/analyze-competitor", req, result, module="crawl_gap_engine")
    return result


@app.post("/api/crawl-gap/compare-domain")
def crawl_gap_compare_domain(req: CrawlGapCompareBody):
    from app.moduller.crawl_gap_engine import compare_domain
    if not req.own_domain.strip() or not req.competitor_domain.strip():
        raise HTTPException(status_code=400, detail="own_domain ve competitor_domain gerekli")
    result = compare_domain(
        req.own_domain.strip(),
        req.competitor_domain.strip(),
        project_id=req.project_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    return result


@app.get("/api/crawl-gap/jobs")
def crawl_gap_jobs(limit: int = 50):
    from app.moduller.crawl_gap_engine import list_jobs
    return list_jobs(limit)


@app.get("/api/crawl-gap/job/{job_id}")
def crawl_gap_job(job_id: str):
    from app.moduller.crawl_gap_engine import get_job
    result = get_job(job_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Job bulunamadı"))
    return result


@app.get("/api/crawl-gap/entities")
def crawl_gap_entities(project_id: str = "", domain: str = ""):
    from app.moduller.crawl_gap_engine import list_entities
    result = list_entities(project_id, domain)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message") or result.get("error"))
    return result


@app.get("/api/crawl-gap/faqs")
def crawl_gap_faqs(project_id: str = "", domain: str = ""):
    from app.moduller.crawl_gap_engine import list_faqs
    result = list_faqs(project_id, domain)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message") or result.get("error"))
    return result


@app.get("/api/crawl-gap/geo")
def crawl_gap_geo(project_id: str = "", domain: str = ""):
    from app.moduller.crawl_gap_engine import list_geo
    result = list_geo(project_id, domain)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message") or result.get("error"))
    return result


@app.get("/api/crawl-gap/clusters")
def crawl_gap_clusters(project_id: str = "", domain: str = ""):
    from app.moduller.crawl_gap_engine import list_clusters
    result = list_clusters(project_id, domain)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message") or result.get("error"))
    return result


@app.get("/api/crawl-gap/ai")
def crawl_gap_ai(project_id: str = "", domain: str = ""):
    from app.moduller.crawl_gap_engine import list_ai
    result = list_ai(project_id, domain)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message") or result.get("error"))
    return result


@app.get("/api/crawl-gap/opportunities")
def crawl_gap_opportunities(project_id: str = "", export: bool = False):
    from app.moduller.crawl_gap_engine import list_opportunities
    return list_opportunities(project_id, export=export)


@app.post("/api/crawl-gap/export-report")
def crawl_gap_export_report(report_type: str = "overview", project_id: str = "", domain: str = ""):
    from app.moduller.crawl_gap_engine import export_report
    return export_report(report_type=report_type, project_id=project_id, domain=domain)


@app.get("/api/crawl-gap/settings")
def crawl_gap_get_settings():
    from app.moduller.crawl_gap_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/crawl-gap/settings")
def crawl_gap_update_settings(req: CrawlGapSettingsBody):
    from app.moduller.crawl_gap_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class AuthorityMeshCreatePlanBody(BaseModel):
    keyword: str = ""
    money_site: str = ""
    project_id: str = ""
    network_id: str = ""
    mesh_counts: dict[str, int] | None = None


class AuthorityMeshPublisherPlanBody(BaseModel):
    plan_id: str = ""
    keyword: str = ""
    money_site: str = ""
    project_id: str = ""


class AuthorityMeshProcessPlanBody(BaseModel):
    plan_id: str = ""
    auto_publish: bool = True


class AuthorityMeshGoogleSiteTaskBody(BaseModel):
    site_title: str = ""
    target_keyword: str = ""
    target_money_site: str = ""
    account_profile: str = "default"
    link_policy: dict | None = None
    pages: list | None = None
    content_fingerprint: str = ""


class AuthorityMeshProcessGoogleSiteBody(BaseModel):
    task_id: str = ""


class AuthorityMeshExportReportBody(BaseModel):
    report_type: str = "overview"


class AuthorityMeshSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/authority-mesh/health")
def authority_mesh_health():
    from app.moduller.authority_mesh_engine import health
    return health()


@app.get("/api/authority-mesh/dashboard")
def authority_mesh_dashboard():
    from app.moduller.authority_mesh_engine import dashboard
    return dashboard()


@app.get("/api/authority-mesh/sites")
def authority_mesh_sites(keyword: str = "", project_id: str = ""):
    from app.moduller.authority_mesh_engine import list_sites
    return list_sites(project_id=project_id, keyword=keyword)


@app.post("/api/authority-mesh/create-site-plan")
def authority_mesh_create_site_plan(req: AuthorityMeshCreatePlanBody):
    from app.moduller.authority_mesh_engine import create_site_plan
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = create_site_plan(
        req.keyword.strip(),
        money_site=req.money_site.strip(),
        project_id=req.project_id.strip(),
        network_id=req.network_id.strip(),
        mesh_counts=req.mesh_counts,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/authority-mesh/create-site-plan", req, result, module="authority_mesh_engine")
    return result


@app.post("/api/authority-mesh/create-publisher-plan")
def authority_mesh_create_publisher_plan(req: AuthorityMeshPublisherPlanBody):
    from app.moduller.authority_mesh_engine import create_publisher_plan
    if not req.plan_id.strip() and not req.keyword.strip():
        raise HTTPException(status_code=400, detail="plan_id veya keyword gerekli")
    result = create_publisher_plan(
        plan_id=req.plan_id.strip(),
        keyword=req.keyword.strip(),
        money_site=req.money_site.strip(),
        project_id=req.project_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.post("/api/authority-mesh/process-plan")
def authority_mesh_process_plan(req: AuthorityMeshProcessPlanBody):
    from app.moduller.authority_mesh_engine import process_plan
    if not req.plan_id.strip():
        raise HTTPException(status_code=400, detail="plan_id gerekli")
    result = process_plan(req.plan_id.strip(), auto_publish=req.auto_publish)
    if not result.get("success") and result.get("error") == "plan_not_found":
        raise HTTPException(status_code=404, detail=result.get("error"))
    _brain_emit("/api/authority-mesh/process-plan", req, result, module="authority_mesh_engine")
    return result


@app.post("/api/authority-mesh/create-google-site-task")
def authority_mesh_create_google_site_task(req: AuthorityMeshGoogleSiteTaskBody):
    from app.moduller.authority_mesh_engine import create_google_site_task
    if not req.site_title.strip() and not req.target_keyword.strip():
        raise HTTPException(status_code=400, detail="site_title veya target_keyword gerekli")
    result = create_google_site_task(
        site_title=req.site_title.strip(),
        target_keyword=req.target_keyword.strip(),
        target_money_site=req.target_money_site.strip(),
        account_profile=req.account_profile.strip() or "default",
        link_policy=req.link_policy,
        pages=req.pages,
        content_fingerprint=req.content_fingerprint.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error") or result.get("message"))
    _brain_emit("/api/authority-mesh/create-google-site-task", req, result, module="authority_mesh_engine")
    return result


@app.post("/api/authority-mesh/process-google-sites-task")
def authority_mesh_process_google_sites_task(req: AuthorityMeshProcessGoogleSiteBody):
    from app.moduller.authority_mesh_engine import process_google_sites_task
    if not req.task_id.strip():
        raise HTTPException(status_code=400, detail="task_id gerekli")
    result = process_google_sites_task(req.task_id.strip())
    if not result.get("success") and result.get("error") == "task_not_found":
        raise HTTPException(status_code=404, detail=result.get("error"))
    _brain_emit("/api/authority-mesh/process-google-sites-task", req, result, module="authority_mesh_engine")
    return result


@app.get("/api/authority-mesh/tasks")
def authority_mesh_tasks(limit: int = 50):
    from app.moduller.authority_mesh_engine import list_tasks
    return list_tasks(limit=limit)


@app.get("/api/authority-mesh/task/{task_id}")
def authority_mesh_task(task_id: str):
    from app.moduller.authority_mesh_engine import get_task
    result = get_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/authority-mesh/reports")
def authority_mesh_reports():
    from app.moduller.authority_mesh_engine import list_reports
    return list_reports()


@app.post("/api/authority-mesh/export-report")
def authority_mesh_export_report(req: AuthorityMeshExportReportBody):
    from app.moduller.authority_mesh_engine import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/authority-mesh/settings")
def authority_mesh_get_settings():
    from app.moduller.authority_mesh_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/authority-mesh/settings")
def authority_mesh_update_settings(req: AuthorityMeshSettingsBody):
    from app.moduller.authority_mesh_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class AuthorityFactoryCreateBatchBody(BaseModel):
    keyword: str = ""
    money_site: str = ""
    name: str = ""
    source: str = "manual"
    role: str = ""
    factory_counts: dict[str, int] | None = None
    mesh_plan_id: str = ""
    project_id: str = ""
    network_id: str = ""
    auto_process: bool | None = None


class AuthorityFactoryExportReportBody(BaseModel):
    report_type: str = "overview"


class AuthorityFactorySettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/authority-factory/health")
def authority_factory_health():
    from app.moduller.authority_factory import health
    return health()


@app.get("/api/authority-factory/dashboard")
def authority_factory_dashboard():
    from app.moduller.authority_factory import dashboard
    return dashboard()


@app.post("/api/authority-factory/create-batch")
def authority_factory_create_batch(req: AuthorityFactoryCreateBatchBody):
    from app.moduller.authority_factory import create_batch
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="keyword gerekli")
    result = create_batch(
        req.keyword.strip(),
        money_site=req.money_site.strip(),
        name=req.name.strip(),
        source=req.source.strip() or "manual",
        role=req.role.strip(),
        factory_counts=req.factory_counts,
        mesh_plan_id=req.mesh_plan_id.strip(),
        project_id=req.project_id.strip(),
        network_id=req.network_id.strip(),
        auto_process=req.auto_process,
    )
    if not result.get("success") and result.get("error") == "authority_factory disabled — settings.enabled=true gerekli":
        raise HTTPException(status_code=403, detail=result.get("error"))
    _brain_emit("/api/authority-factory/create-batch", req, result, module="authority_factory", event_type="authority_factory_batch_created")
    return result


@app.post("/api/authority-factory/process-batch/{batch_id}")
def authority_factory_process_batch(batch_id: str):
    from app.moduller.authority_factory import process_batch
    result = process_batch(batch_id)
    _brain_emit(f"/api/authority-factory/process-batch/{batch_id}", {"batch_id": batch_id}, result, module="authority_factory")
    return result


@app.post("/api/authority-factory/pause-batch/{batch_id}")
def authority_factory_pause_batch(batch_id: str):
    from app.moduller.authority_factory import pause_batch
    return pause_batch(batch_id)


@app.post("/api/authority-factory/resume-batch/{batch_id}")
def authority_factory_resume_batch(batch_id: str):
    from app.moduller.authority_factory import resume_batch
    result = resume_batch(batch_id)
    _brain_emit(f"/api/authority-factory/resume-batch/{batch_id}", {"batch_id": batch_id}, result, module="authority_factory")
    return result


@app.get("/api/authority-factory/batches")
def authority_factory_batches(limit: int = 50, status: str = ""):
    from app.moduller.authority_factory import list_batches
    return list_batches(limit=limit, status=status)


@app.get("/api/authority-factory/batch/{batch_id}")
def authority_factory_batch(batch_id: str):
    from app.moduller.authority_factory import get_batch
    result = get_batch(batch_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/authority-factory/items")
def authority_factory_items(batch_id: str = "", status: str = "", provider: str = "", limit: int = 100):
    from app.moduller.authority_factory import list_items
    return list_items(batch_id=batch_id, status=status, provider=provider, limit=limit)


@app.post("/api/authority-factory/export-report")
def authority_factory_export_report(req: AuthorityFactoryExportReportBody):
    from app.moduller.authority_factory import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/authority-factory/settings")
def authority_factory_get_settings():
    from app.moduller.authority_factory import get_settings
    return {"settings": get_settings()}


@app.post("/api/authority-factory/settings")
def authority_factory_update_settings(req: AuthorityFactorySettingsBody):
    from app.moduller.authority_factory import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class AuthorityFactoryCreateFromCampaignBody(BaseModel):
    campaign_id: str = ""
    provider_mix: dict[str, int] | None = None
    auto_process: bool | None = None


class AuthorityFactoryCreateFromDatasetBody(BaseModel):
    dataset_id: str = ""
    keyword: str = ""
    money_site: str = ""
    provider_mix: dict[str, int] | None = None
    auto_process: bool | None = None


class AuthorityFactoryCreateFromDomainsBody(BaseModel):
    keyword: str = ""
    money_site: str = ""
    domains: list[str] | None = None
    provider_mix: dict[str, int] | None = None
    auto_process: bool | None = None


class AuthorityFactoryProviderMixBody(BaseModel):
    overrides: dict[str, int] | None = None


class AuthorityFactoryValidateBatchBody(BaseModel):
    batch_id: str = ""


class AuthorityFactoryPreviewContentBody(BaseModel):
    item_id: str = ""
    format: str = "html"


@app.post("/api/authority-factory/create-from-campaign")
def authority_factory_create_from_campaign(req: AuthorityFactoryCreateFromCampaignBody):
    from app.moduller.authority_factory import create_from_campaign
    if not req.campaign_id.strip():
        raise HTTPException(status_code=400, detail="campaign_id gerekli")
    result = create_from_campaign(req.campaign_id.strip(), provider_mix=req.provider_mix, auto_process=req.auto_process)
    _brain_emit("/api/authority-factory/create-from-campaign", req, result, module="authority_factory", event_type="authority_factory_v2_batch_created")
    return result


@app.post("/api/authority-factory/create-from-dataset")
def authority_factory_create_from_dataset(req: AuthorityFactoryCreateFromDatasetBody):
    from app.moduller.authority_factory import create_from_dataset
    if not req.dataset_id.strip():
        raise HTTPException(status_code=400, detail="dataset_id gerekli")
    result = create_from_dataset(
        req.dataset_id.strip(),
        keyword=req.keyword.strip(),
        money_site=req.money_site.strip(),
        provider_mix=req.provider_mix,
        auto_process=req.auto_process,
    )
    _brain_emit("/api/authority-factory/create-from-dataset", req, result, module="authority_factory", event_type="authority_factory_v2_batch_created")
    return result


@app.post("/api/authority-factory/create-from-domain-candidates")
def authority_factory_create_from_domains(req: AuthorityFactoryCreateFromDomainsBody):
    from app.moduller.authority_factory import create_from_domain_candidates
    result = create_from_domain_candidates(
        keyword=req.keyword.strip(),
        money_site=req.money_site.strip(),
        domains=req.domains,
        provider_mix=req.provider_mix,
        auto_process=req.auto_process,
    )
    _brain_emit("/api/authority-factory/create-from-domain-candidates", req, result, module="authority_factory", event_type="authority_factory_v2_batch_created")
    return result


@app.post("/api/authority-factory/generate-provider-mix")
def authority_factory_generate_provider_mix(req: AuthorityFactoryProviderMixBody):
    from app.moduller.authority_factory import generate_provider_mix
    return generate_provider_mix(req.overrides)


@app.post("/api/authority-factory/validate-batch")
def authority_factory_validate_batch(req: AuthorityFactoryValidateBatchBody):
    from app.moduller.authority_factory import validate_batch
    if not req.batch_id.strip():
        raise HTTPException(status_code=400, detail="batch_id gerekli")
    return validate_batch(req.batch_id.strip())


@app.post("/api/authority-factory/process-item/{item_id}")
def authority_factory_process_item(item_id: str):
    from app.moduller.authority_factory import process_item
    result = process_item(item_id)
    _brain_emit(f"/api/authority-factory/process-item/{item_id}", {"item_id": item_id}, result, module="authority_factory")
    return result


@app.post("/api/authority-factory/preview-content")
def authority_factory_preview_content(req: AuthorityFactoryPreviewContentBody):
    from app.moduller.authority_factory import preview_content
    if not req.item_id.strip():
        raise HTTPException(status_code=400, detail="item_id gerekli")
    return preview_content(req.item_id.strip(), req.format.strip() or "html")


@app.get("/api/authority-factory/provider-mix")
def authority_factory_provider_mix():
    from app.moduller.authority_factory import get_provider_mix
    return get_provider_mix()


@app.get("/api/authority-factory/datasets")
def authority_factory_datasets(limit: int = 50):
    from app.moduller.authority_factory import list_datasets_for_factory
    return list_datasets_for_factory(limit=limit)


@app.get("/api/authority-factory/domain-candidates")
def authority_factory_domain_candidates(limit: int = 50):
    from app.moduller.authority_factory import list_domain_candidates
    return list_domain_candidates(limit=limit)


class RevenueLeadTrackBody(BaseModel):
    event_type: str = ""
    source_url: str = ""
    keyword: str = ""
    campaign: str = ""
    target: str = ""
    page_title: str = ""
    referrer: str = ""
    utm: dict | None = None
    metadata: dict | None = None
    tracking_secret: str = ""


class RevenueLeadStatusBody(BaseModel):
    status: str = ""
    estimated_value: float | None = None


class RevenueLeadExportReportBody(BaseModel):
    report_type: str = "overview"


class RevenueLeadSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/revenue-leads/health")
def revenue_leads_health():
    from app.moduller.revenue_lead_engine import health
    return health()


@app.get("/api/revenue-leads/dashboard")
def revenue_leads_dashboard():
    from app.moduller.revenue_lead_engine import dashboard
    return dashboard()


@app.post("/api/revenue-leads/track")
async def revenue_leads_track(request: Request, req: RevenueLeadTrackBody | None = None):
    from app.moduller.revenue_lead_engine import track_lead
    body = req
    if body is None or not body.event_type:
        try:
            raw = await request.json()
            body = RevenueLeadTrackBody(**raw) if isinstance(raw, dict) else RevenueLeadTrackBody()
        except Exception:
            body = RevenueLeadTrackBody()
    client_ip = request.client.host if request.client else ""
    secret = body.tracking_secret or request.headers.get("X-Tracking-Secret", "")
    result = track_lead(
        body.event_type,
        source_url=body.source_url,
        keyword=body.keyword,
        campaign=body.campaign,
        target=body.target,
        page_title=body.page_title,
        referrer=body.referrer or request.headers.get("Referer", ""),
        utm=body.utm,
        metadata=body.metadata,
        client_ip=client_ip,
        tracking_secret=secret,
    )
    if not result.get("success") and result.get("error") in ("rate_limit_exceeded", "invalid_tracking_secret"):
        raise HTTPException(status_code=429 if result.get("error") == "rate_limit_exceeded" else 403, detail=result.get("error"))
    _brain_emit("/api/revenue-leads/track", body, result, module="revenue_lead_engine", event_type="lead_created")
    return result


@app.get("/api/revenue-leads/track-redirect")
def revenue_leads_track_redirect(
    request: Request,
    event_type: str = "",
    target: str = "",
    source_url: str = "",
    keyword: str = "",
    campaign: str = "",
    tracking_secret: str = "",
):
    from app.moduller.revenue_lead_engine import track_and_redirect
    client_ip = request.client.host if request.client else ""
    secret = tracking_secret or request.headers.get("X-Tracking-Secret", "")
    result = track_and_redirect(
        event_type,
        target,
        source_url=source_url,
        keyword=keyword,
        campaign=campaign,
        client_ip=client_ip,
        tracking_secret=secret,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return RedirectResponse(url=result["redirect_url"], status_code=302)


@app.get("/api/revenue-leads/leads")
def revenue_leads_list(status: str = "", keyword: str = "", source_domain: str = "", limit: int = 100, offset: int = 0):
    from app.moduller.revenue_lead_engine import list_leads
    return list_leads(status=status, keyword=keyword, source_domain=source_domain, limit=limit, offset=offset)


@app.get("/api/revenue-leads/lead/{lead_id}")
def revenue_leads_get(lead_id: str):
    from app.moduller.revenue_lead_engine import get_lead
    result = get_lead(lead_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/revenue-leads/lead/{lead_id}/status")
def revenue_leads_update_status(lead_id: str, req: RevenueLeadStatusBody):
    from app.moduller.revenue_lead_engine import update_lead_status
    if not req.status.strip():
        raise HTTPException(status_code=400, detail="status gerekli")
    result = update_lead_status(lead_id, req.status.strip(), estimated_value=req.estimated_value)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    _brain_emit(f"/api/revenue-leads/lead/{lead_id}/status", req, result, module="revenue_lead_engine")
    return result


@app.get("/api/revenue-leads/sources")
def revenue_leads_sources(limit: int = 50):
    from app.moduller.revenue_lead_engine import list_sources
    return list_sources(limit=limit)


@app.get("/api/revenue-leads/keywords")
def revenue_leads_keywords(limit: int = 50):
    from app.moduller.revenue_lead_engine import list_keywords
    return list_keywords(limit=limit)


@app.get("/api/revenue-leads/funnel")
def revenue_leads_funnel():
    from app.moduller.revenue_lead_engine import build_funnel
    return build_funnel()


@app.get("/api/revenue-leads/publisher-impact")
def revenue_leads_publisher_impact():
    from app.moduller.revenue_lead_engine import publisher_impact
    return publisher_impact()


@app.get("/api/revenue-leads/authority-impact")
def revenue_leads_authority_impact():
    from app.moduller.revenue_lead_engine import authority_impact
    return authority_impact()


@app.get("/api/revenue-leads/tracking-script")
def revenue_leads_tracking_script(base_api: str = "http://localhost:4001"):
    from app.moduller.revenue_lead_engine import generate_tracking_script
    return {"success": True, "script": generate_tracking_script(base_api=base_api)}


@app.post("/api/revenue-leads/export-report")
def revenue_leads_export_report(req: RevenueLeadExportReportBody):
    from app.moduller.revenue_lead_engine import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/revenue-leads/settings")
def revenue_leads_get_settings():
    from app.moduller.revenue_lead_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/revenue-leads/settings")
def revenue_leads_update_settings(req: RevenueLeadSettingsBody):
    from app.moduller.revenue_lead_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class CitationAnalyzePageBody(BaseModel):
    url: str = ""
    html: str = ""
    project_id: str = ""
    title: str = ""
    competitor_url: str = ""


class CitationAnalyzeProjectBody(BaseModel):
    project_id: str = ""
    urls: list[str] | None = None
    competitor_domains: list[str] | None = None


class CitationExportReportBody(BaseModel):
    report_type: str = "overview"


class CitationSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/citation/health")
def citation_health():
    from app.moduller.citation_engine import health
    return health()


@app.get("/api/citation/dashboard")
def citation_dashboard():
    from app.moduller.citation_engine import dashboard
    return dashboard()


@app.post("/api/citation/analyze-page")
def citation_analyze_page(req: CitationAnalyzePageBody):
    from app.moduller.citation_engine import analyze_page
    if not req.url.strip() and not req.html.strip():
        raise HTTPException(status_code=400, detail="url veya html gerekli")
    result = analyze_page(
        req.url.strip(),
        html=req.html.strip(),
        project_id=req.project_id.strip(),
        title=req.title.strip(),
        competitor_url=req.competitor_url.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/citation/analyze-page", req, result, module="citation_engine", event_type="citation_analysis_completed")
    return result


@app.post("/api/citation/analyze-project")
def citation_analyze_project(req: CitationAnalyzeProjectBody):
    from app.moduller.citation_engine import analyze_project
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id gerekli")
    result = analyze_project(
        req.project_id.strip(),
        urls=req.urls,
        competitor_domains=req.competitor_domains,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/citation/analyze-project", req, result, module="citation_engine", event_type="citation_analysis_completed")
    return result


@app.get("/api/citation/pages")
def citation_pages(project_id: str = "", limit: int = 50):
    from app.moduller.citation_engine import list_pages
    return list_pages(limit=limit, project_id=project_id)


@app.get("/api/citation/entities")
def citation_entities(project_id: str = "", limit: int = 50):
    from app.moduller.citation_engine import list_entities
    return list_entities(limit=limit, project_id=project_id)


@app.get("/api/citation/opportunities")
def citation_opportunities(limit: int = 50):
    from app.moduller.citation_engine import list_opportunities
    return list_opportunities(limit=limit)


@app.get("/api/citation/competitors")
def citation_competitors(limit: int = 30):
    from app.moduller.citation_engine import list_competitors
    return list_competitors(limit=limit)


@app.get("/api/citation/visibility")
def citation_visibility(project_id: str = "", limit: int = 30):
    from app.moduller.citation_engine import get_visibility
    return get_visibility(project_id=project_id, limit=limit)


@app.post("/api/citation/export-report")
def citation_export_report(req: CitationExportReportBody):
    from app.moduller.citation_engine import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/citation/settings")
def citation_get_settings():
    from app.moduller.citation_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/citation/settings")
def citation_update_settings(req: CitationSettingsBody):
    from app.moduller.citation_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class ExecutiveAnalyzeBody(BaseModel):
    project_id: str = ""


class ExecutiveExportBody(BaseModel):
    report_type: str = "overview"


class ExecutiveSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/executive-ai/health")
def executive_ai_health():
    from app.moduller.executive_ai import health
    return health()


@app.get("/api/executive-ai/dashboard")
def executive_ai_dashboard():
    from app.moduller.executive_ai import dashboard
    return dashboard()


@app.post("/api/executive-ai/analyze-project")
def executive_ai_analyze(req: ExecutiveAnalyzeBody):
    from app.moduller.executive_ai import analyze_project
    result = analyze_project(req.project_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/executive-ai/analyze-project", req, result, module="executive_ai", event_type="executive_report_created")
    return result


@app.get("/api/executive-ai/reports")
def executive_ai_reports(limit: int = 20):
    from app.moduller.executive_ai import list_reports
    return list_reports(limit=limit)


@app.get("/api/executive-ai/missions")
def executive_ai_missions(mission_type: str = ""):
    from app.moduller.executive_ai import list_missions
    return list_missions(mission_type)


@app.get("/api/executive-ai/priorities")
def executive_ai_priorities(limit: int = 30):
    from app.moduller.executive_ai import list_priorities
    return list_priorities(limit=limit)


@app.get("/api/executive-ai/forecasts")
def executive_ai_forecasts(project_id: str = ""):
    from app.moduller.executive_ai import get_forecasts
    return get_forecasts(project_id)


@app.post("/api/executive-ai/export-report")
def executive_ai_export(req: ExecutiveExportBody):
    from app.moduller.executive_ai import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/executive-ai/settings")
def executive_ai_get_settings():
    from app.moduller.executive_ai import get_settings
    return {"settings": get_settings()}


@app.post("/api/executive-ai/settings")
def executive_ai_update_settings(req: ExecutiveSettingsBody):
    from app.moduller.executive_ai import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class ProviderCheckBody(BaseModel):
    provider: str = ""


class ProviderExportBody(BaseModel):
    report_type: str = "overview"


class ProviderSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/providers/health")
def providers_health():
    from app.moduller.provider_control_center import health
    return health()


@app.get("/api/providers/dashboard")
def providers_dashboard():
    from app.moduller.provider_control_center import dashboard
    return dashboard()


@app.get("/api/providers/list")
def providers_list(refresh: bool = False):
    from app.moduller.provider_control_center import list_providers
    return list_providers(refresh=refresh)


@app.get("/api/providers/provider/{name}")
def providers_get_one(name: str, refresh: bool = False):
    from app.moduller.provider_control_center import get_provider
    result = get_provider(name, refresh=refresh)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/providers/check")
def providers_check(req: ProviderCheckBody | None = None):
    from app.moduller.provider_control_center import check_all_providers, check_provider
    if req and req.provider.strip():
        result = check_provider(req.provider.strip(), persist=True)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        _brain_emit(
            "/api/providers/check",
            req,
            result,
            module="provider_control_center",
            event_type="provider_health_restored" if result.get("provider", {}).get("status") == "healthy" else "provider_error_detected",
        )
        return result
    result = check_all_providers(persist=True)
    _brain_emit("/api/providers/check", req or {}, result, module="provider_control_center", event_type="provider_health_restored")
    return result


@app.post("/api/providers/export-report")
def providers_export_report(req: ProviderExportBody):
    from app.moduller.provider_control_center import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/providers/settings")
def providers_get_settings():
    from app.moduller.provider_control_center import get_settings
    return {"settings": get_settings()}


@app.post("/api/providers/settings")
def providers_update_settings(req: ProviderSettingsBody):
    from app.moduller.provider_control_center import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class HiveAuditExportBody(BaseModel):
    report_type: str = "overview"


class HiveAuditSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/hive-audit/health")
def hive_audit_health():
    from app.moduller.hive_audit_engine import health
    return health()


@app.get("/api/hive-audit/dashboard")
def hive_audit_dashboard():
    from app.moduller.hive_audit_engine import dashboard
    return dashboard()


@app.post("/api/hive-audit/run")
def hive_audit_run():
    from app.moduller.hive_audit_engine import run_audit
    result = run_audit(persist=True)
    _brain_emit("/api/hive-audit/run", {}, result, module="hive_audit_engine", event_type="audit_completed")
    return result


@app.get("/api/hive-audit/issues")
def hive_audit_issues(category: str = "", severity: str = "", status: str = "", limit: int = 100):
    from app.moduller.hive_audit_engine import list_issues
    return list_issues(category=category, severity=severity, status=status, limit=limit)


@app.get("/api/hive-audit/issue/{issue_id}")
def hive_audit_get_issue(issue_id: str):
    from app.moduller.hive_audit_engine import get_issue
    result = get_issue(issue_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/hive-audit/issue/{issue_id}/ack")
def hive_audit_ack_issue(issue_id: str):
    from app.moduller.hive_audit_engine import ack_issue
    result = ack_issue(issue_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/hive-audit/issue/{issue_id}/resolve")
def hive_audit_resolve_issue(issue_id: str):
    from app.moduller.hive_audit_engine import resolve_issue
    result = resolve_issue(issue_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    _brain_emit(f"/api/hive-audit/issue/{issue_id}/resolve", {"issue_id": issue_id}, result, module="hive_audit_engine", event_type="audit_issue_resolved")
    return result


@app.get("/api/hive-audit/reports")
def hive_audit_reports(limit: int = 20):
    from app.moduller.hive_audit_engine import list_reports
    return list_reports(limit=limit)


@app.post("/api/hive-audit/export-report")
def hive_audit_export_report(req: HiveAuditExportBody):
    from app.moduller.hive_audit_engine import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/hive-audit/settings")
def hive_audit_get_settings():
    from app.moduller.hive_audit_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/hive-audit/settings")
def hive_audit_update_settings(req: HiveAuditSettingsBody):
    from app.moduller.hive_audit_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


class CampaignCreateBody(BaseModel):
    name: str = ""
    target_keyword: str = ""
    target_domain: str = ""
    target_market: str = ""
    goal: str = "ranking"
    campaign_type: str = ""
    priority: str = "medium"
    project_id: str = ""


class CampaignPlanBody(BaseModel):
    campaign_id: str = ""


class CampaignOrchestratorBody(BaseModel):
    campaign_id: str = ""


class CampaignExportBody(BaseModel):
    report_type: str = "overview"


class CampaignDatasetCreateBody(BaseModel):
    dataset_id: str = ""
    target_domain: str = ""
    campaign_type: str = "full_domination"
    goal: str = "ranking"
    market: str = ""
    primary_keyword: str = ""
    name: str = ""
    priority: str = "high"
    project_id: str = ""


class CampaignDatasetAttachBody(BaseModel):
    dataset_id: str = ""


class CampaignAuthorityFactoryBody(BaseModel):
    campaign_id: str = ""
    auto_process: bool = False


class CampaignSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/campaigns/health")
def campaigns_health():
    from app.moduller.campaign_engine import health
    return health()


@app.get("/api/campaigns/dashboard")
def campaigns_dashboard():
    from app.moduller.campaign_engine import dashboard
    return dashboard()


@app.post("/api/campaigns/create")
def campaigns_create(req: CampaignCreateBody):
    from app.moduller.campaign_engine import create_campaign
    result = create_campaign(
        name=req.name.strip(),
        target_keyword=req.target_keyword.strip(),
        target_domain=req.target_domain.strip(),
        target_market=req.target_market.strip(),
        goal=req.goal.strip() or "ranking",
        campaign_type=req.campaign_type.strip(),
        priority=req.priority.strip() or "medium",
        project_id=req.project_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/campaigns/create", req, result, module="campaign_engine", event_type="campaign_created")
    return result


@app.post("/api/campaigns/generate-plan")
def campaigns_generate_plan(req: CampaignPlanBody):
    from app.moduller.campaign_engine import generate_plan
    if not req.campaign_id.strip():
        raise HTTPException(status_code=400, detail="campaign_id gerekli")
    result = generate_plan(req.campaign_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/campaigns/generate-plan", req, result, module="campaign_engine", event_type="campaign_started")
    return result


@app.post("/api/campaigns/send-to-orchestrator")
def campaigns_send_to_orchestrator(req: CampaignOrchestratorBody):
    from app.moduller.campaign_engine import send_to_orchestrator
    if not req.campaign_id.strip():
        raise HTTPException(status_code=400, detail="campaign_id gerekli")
    result = send_to_orchestrator(req.campaign_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    return result


@app.get("/api/campaigns/list")
def campaigns_list(status: str = "", limit: int = 50):
    from app.moduller.campaign_engine import list_campaigns
    return list_campaigns(status=status, limit=limit)


@app.get("/api/campaigns/tasks")
def campaigns_tasks(campaign_id: str = "", status: str = "", limit: int = 200):
    from app.moduller.campaign_engine import list_tasks
    return list_tasks(campaign_id=campaign_id, status=status, limit=limit)


@app.get("/api/campaigns/settings")
def campaigns_get_settings():
    from app.moduller.campaign_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/campaigns/settings")
def campaigns_update_settings(req: CampaignSettingsBody):
    from app.moduller.campaign_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


@app.post("/api/campaigns/export-report")
def campaigns_export_report(req: CampaignExportBody):
    from app.moduller.campaign_engine import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/campaigns/datasets")
def campaigns_list_datasets():
    from app.moduller.campaign_engine import list_datasets_for_campaign
    return list_datasets_for_campaign()


@app.post("/api/campaigns/create-from-dataset")
def campaigns_create_from_dataset(req: CampaignDatasetCreateBody):
    from app.moduller.campaign_engine import create_from_dataset
    if not req.dataset_id.strip():
        raise HTTPException(status_code=400, detail="dataset_id gerekli")
    result = create_from_dataset(
        dataset_id=req.dataset_id.strip(),
        target_domain=req.target_domain.strip(),
        campaign_type=req.campaign_type.strip() or "full_domination",
        goal=req.goal.strip() or "ranking",
        market=req.market.strip(),
        primary_keyword=req.primary_keyword.strip(),
        name=req.name.strip(),
        priority=req.priority.strip() or "high",
        project_id=req.project_id.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/campaigns/create-from-dataset", req, result, module="campaign_engine", event_type="campaign_created_from_dataset")
    return result


@app.post("/api/campaigns/generate-plan-from-dataset")
def campaigns_generate_plan_from_dataset(req: CampaignPlanBody):
    from app.moduller.campaign_engine import generate_plan_from_dataset
    if not req.campaign_id.strip():
        raise HTTPException(status_code=400, detail="campaign_id gerekli")
    result = generate_plan_from_dataset(req.campaign_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/campaigns/generate-plan-from-dataset", req, result, module="campaign_engine", event_type="campaign_dataset_plan_generated")
    return result


@app.post("/api/campaigns/send-to-authority-factory")
def campaigns_send_to_authority_factory(req: CampaignAuthorityFactoryBody):
    from app.moduller.campaign_engine import send_to_authority_factory
    if not req.campaign_id.strip():
        raise HTTPException(status_code=400, detail="campaign_id gerekli")
    result = send_to_authority_factory(req.campaign_id.strip(), auto_process=req.auto_process)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit("/api/campaigns/send-to-authority-factory", req, result, module="campaign_engine", event_type="campaign_sent_to_authority_factory")
    return result


@app.post("/api/campaigns/{campaign_id}/attach-dataset")
def campaigns_attach_dataset(campaign_id: str, req: CampaignDatasetAttachBody):
    from app.moduller.campaign_engine import attach_dataset
    if not req.dataset_id.strip():
        raise HTTPException(status_code=400, detail="dataset_id gerekli")
    result = attach_dataset(campaign_id.strip(), req.dataset_id.strip())
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _brain_emit(f"/api/campaigns/{campaign_id}/attach-dataset", req, result, module="campaign_engine", event_type="campaign_dataset_attached")
    return result


@app.get("/api/campaigns/{campaign_id}")
def campaigns_get_one(campaign_id: str):
    from app.moduller.campaign_engine import get_campaign
    result = get_campaign(campaign_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


class GitHubPagesCreateSiteBody(BaseModel):
    repo_name: str = ""
    site_title: str = ""
    target_keyword: str = ""
    target_money_site: str = ""
    role: str = "support_hub"
    pages: list[dict] | None = None
    link_policy: dict | list | None = None
    visibility: str = ""
    network_id: str = ""


class GitHubPagesPublishBody(BaseModel):
    site_id: str = ""
    network_id: str = ""


class GitHubPagesUpdateBody(BaseModel):
    site_id: str = ""
    files: dict[str, str] | None = None
    pages: list[dict] | None = None
    site_title: str = ""


class GitHubPagesExportReportBody(BaseModel):
    report_type: str = "overview"


@app.get("/api/github-pages/health")
def github_pages_health():
    from app.moduller.github_pages_worker import health
    return health()


@app.post("/api/github-pages/create-site")
def github_pages_create_site(req: GitHubPagesCreateSiteBody):
    from app.moduller.github_pages_worker import create_site
    if not req.repo_name.strip() and not req.site_title.strip() and not req.target_keyword.strip():
        raise HTTPException(status_code=400, detail="repo_name, site_title veya target_keyword gerekli")
    result = create_site(
        repo_name=req.repo_name.strip(),
        site_title=req.site_title.strip(),
        target_keyword=req.target_keyword.strip(),
        target_money_site=req.target_money_site.strip(),
        role=req.role.strip() or "support_hub",
        pages=req.pages,
        link_policy=req.link_policy,
        visibility=req.visibility.strip(),
        network_id=req.network_id.strip(),
    )
    if not result.get("success") and result.get("error") == "provider_missing":
        raise HTTPException(status_code=503, detail=result.get("message") or result.get("error"))
    if not result.get("success") and result.get("error") in ("validation_error",):
        raise HTTPException(status_code=400, detail=result.get("message") or result.get("error"))
    _brain_emit("/api/github-pages/create-site", req, result, module="github_pages_worker")
    return result


@app.post("/api/github-pages/publish-site")
def github_pages_publish_site(req: GitHubPagesPublishBody):
    from app.moduller.github_pages_worker import publish_site
    if not req.site_id.strip():
        raise HTTPException(status_code=400, detail="site_id gerekli")
    result = publish_site(req.site_id.strip(), network_id=req.network_id.strip())
    if not result.get("success") and result.get("error") == "provider_missing":
        raise HTTPException(status_code=503, detail=result.get("message") or result.get("error"))
    if not result.get("success") and result.get("error") == "site_not_found":
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/github-pages/update-site")
def github_pages_update_site(req: GitHubPagesUpdateBody):
    from app.moduller.github_pages_worker import update_site
    if not req.site_id.strip():
        raise HTTPException(status_code=400, detail="site_id gerekli")
    result = update_site(
        req.site_id.strip(),
        files=req.files,
        pages=req.pages,
        site_title=req.site_title.strip(),
    )
    if not result.get("success") and result.get("error") == "provider_missing":
        raise HTTPException(status_code=503, detail=result.get("message") or result.get("error"))
    if not result.get("success") and result.get("error") == "site_not_found":
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/github-pages/sites")
def github_pages_list_sites(limit: int = 50):
    from app.moduller.github_pages_worker import list_sites
    return list_sites(limit=limit)


@app.get("/api/github-pages/site/{site_id}")
def github_pages_get_site(site_id: str):
    from app.moduller.github_pages_worker import get_site
    result = get_site(site_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/github-pages/export-report")
def github_pages_export_report(req: GitHubPagesExportReportBody):
    from app.moduller.github_pages_worker import export_report
    return export_report(req.report_type or "overview")


class GoogleSitesCreateTaskBody(BaseModel):
    site_title: str = ""
    site_slug: str = ""
    target_keyword: str = ""
    target_money_site: str = ""
    account_profile: str = "default"
    pages: list[dict] | None = None
    link_policy: dict | list | None = None


class GoogleSitesProcessTaskBody(BaseModel):
    task_id: str = ""
    network_id: str = ""


class GoogleSitesResumeTaskBody(BaseModel):
    task_id: str = ""
    network_id: str = ""


class GoogleSitesExportReportBody(BaseModel):
    report_type: str = "overview"


@app.get("/api/google-sites/health")
def google_sites_health():
    from app.moduller.google_sites_worker import health
    return health()


@app.post("/api/google-sites/create-task")
def google_sites_create_task(req: GoogleSitesCreateTaskBody):
    from app.moduller.google_sites_worker import create_task
    if not req.site_title.strip() and not req.target_keyword.strip():
        raise HTTPException(status_code=400, detail="site_title veya target_keyword gerekli")
    result = create_task(
        site_title=req.site_title.strip(),
        site_slug=req.site_slug.strip(),
        target_keyword=req.target_keyword.strip(),
        target_money_site=req.target_money_site.strip(),
        account_profile=req.account_profile.strip() or "default",
        pages=req.pages,
        link_policy=req.link_policy,
    )
    if not result.get("success") and result.get("error") in ("validation_error", "duplicate_task_blocked"):
        raise HTTPException(status_code=400, detail=result.get("message") or result.get("error"))
    _brain_emit("/api/google-sites/create-task", req, result, module="google_sites_worker")
    return result


@app.post("/api/google-sites/process-task")
def google_sites_process_task(req: GoogleSitesProcessTaskBody):
    from app.moduller.google_sites_worker import process_task
    if not req.task_id.strip():
        raise HTTPException(status_code=400, detail="task_id gerekli")
    result = process_task(req.task_id.strip(), network_id=req.network_id.strip())
    if not result.get("success") and result.get("error") in ("provider_missing", "browser_missing"):
        raise HTTPException(status_code=503, detail=result.get("message") or result.get("error"))
    if not result.get("success") and result.get("error") == "task_not_found":
        raise HTTPException(status_code=404, detail=result.get("error"))
    _brain_emit("/api/google-sites/process-task", req, result, module="google_sites_worker")
    return result


@app.post("/api/google-sites/resume-task")
def google_sites_resume_task(req: GoogleSitesResumeTaskBody):
    from app.moduller.google_sites_worker import resume_task
    if not req.task_id.strip():
        raise HTTPException(status_code=400, detail="task_id gerekli")
    result = resume_task(req.task_id.strip(), network_id=req.network_id.strip())
    if not result.get("success") and result.get("error") in ("provider_missing", "browser_missing"):
        raise HTTPException(status_code=503, detail=result.get("message") or result.get("error"))
    if not result.get("success") and result.get("error") == "task_not_found":
        raise HTTPException(status_code=404, detail=result.get("error"))
    _brain_emit("/api/google-sites/resume-task", req, result, module="google_sites_worker")
    return result


@app.get("/api/google-sites/tasks")
def google_sites_list_tasks(limit: int = 50):
    from app.moduller.google_sites_worker import list_tasks
    return list_tasks(limit=limit)


@app.get("/api/google-sites/task/{task_id}")
def google_sites_get_task(task_id: str):
    from app.moduller.google_sites_worker import get_task
    result = get_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/api/google-sites/export-report")
def google_sites_export_report(req: GoogleSitesExportReportBody):
    from app.moduller.google_sites_worker import export_report
    return export_report(req.report_type or "overview")


class MissionControlSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


class MissionControlExportReportBody(BaseModel):
    report_type: str = "overview"


@app.get("/api/mission-control/health")
def mission_control_health():
    from app.moduller.mission_control_center import health
    return health()


@app.get("/api/mission-control/dashboard")
def mission_control_dashboard():
    import time
    global _MCC_BRAIN_LAST_EMIT
    from app.moduller.mission_control_center import build_dashboard
    result = build_dashboard(record_open=True, full=False)
    now = time.monotonic()
    if now - _MCC_BRAIN_LAST_EMIT >= _MCC_BRAIN_DEBOUNCE_SEC:
        _brain_emit("/api/mission-control/dashboard", {}, result, module="mission_control_center")
        _MCC_BRAIN_LAST_EMIT = now
    return result


@app.get("/api/mission-control/dashboard-full")
def mission_control_dashboard_full():
    import time
    global _MCC_BRAIN_LAST_EMIT
    from app.moduller.mission_control_center import build_dashboard_full
    result = build_dashboard_full(record_open=False)
    now = time.monotonic()
    if now - _MCC_BRAIN_LAST_EMIT >= _MCC_BRAIN_DEBOUNCE_SEC:
        _brain_emit("/api/mission-control/dashboard-full", {}, result, module="mission_control_center")
        _MCC_BRAIN_LAST_EMIT = now
    return result


@app.get("/api/mission-control/alerts")
def mission_control_alerts():
    from app.moduller.mission_control_center import list_alerts
    return list_alerts()


@app.get("/api/mission-control/today")
def mission_control_today():
    from app.moduller.mission_control_center import today_mission
    return today_mission()


@app.get("/api/mission-control/week")
def mission_control_week():
    from app.moduller.mission_control_center import week_mission
    return week_mission()


@app.get("/api/mission-control/actions")
def mission_control_actions():
    from app.moduller.mission_control_center import list_actions
    return list_actions()


@app.post("/api/mission-control/action/{action_id}/ack")
def mission_control_action_ack(action_id: str):
    from app.moduller.mission_control_center import acknowledge_action
    result = acknowledge_action(action_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    _brain_emit(f"/api/mission-control/action/{action_id}/ack", {}, result, module="mission_control_center")
    return result


@app.post("/api/mission-control/action/{action_id}/done")
def mission_control_action_done(action_id: str):
    from app.moduller.mission_control_center import complete_action
    result = complete_action(action_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    _brain_emit(f"/api/mission-control/action/{action_id}/done", {}, result, module="mission_control_center")
    return result


@app.post("/api/mission-control/export-report")
def mission_control_export_report(req: MissionControlExportReportBody):
    from app.moduller.mission_control_center import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/mission-control/settings")
def mission_control_get_settings():
    from app.moduller.mission_control_center import get_settings
    return {"settings": get_settings()}


@app.post("/api/mission-control/settings")
def mission_control_update_settings(req: MissionControlSettingsBody):
    from app.moduller.mission_control_center import update_settings
    return update_settings(req.model_dump(exclude_unset=True))


# ── HIVE Academy / Mentor / First Run Wizard (Learn Layer) ──


class HiveAcademyExportBody(BaseModel):
    report_type: str = "overview"


class HiveMentorAskBody(BaseModel):
    question: str = ""


class FirstRunCompleteStepBody(BaseModel):
    step_id: str = ""
    manual: bool = True


@app.get("/api/hive-academy/health")
def hive_academy_health():
    from app.moduller.hive_academy import health
    return health()


@app.get("/api/hive-academy/modules")
def hive_academy_modules():
    from app.moduller.hive_academy import list_modules
    return list_modules()


@app.get("/api/hive-academy/module/{module_id}")
def hive_academy_module(module_id: str):
    from app.moduller.hive_academy import get_module
    return get_module(module_id)


@app.get("/api/hive-academy/workflows")
def hive_academy_workflows():
    from app.moduller.hive_academy import list_workflows
    return list_workflows()


@app.get("/api/hive-academy/guides")
def hive_academy_guides():
    from app.moduller.hive_academy import list_guides
    return list_guides()


@app.get("/api/hive-academy/guide/{guide_id}")
def hive_academy_guide(guide_id: str):
    from app.moduller.hive_academy import get_guide
    return get_guide(guide_id)


@app.post("/api/hive-academy/export")
def hive_academy_export(req: HiveAcademyExportBody):
    from app.moduller.hive_academy import export_academy
    return export_academy(req.report_type or "overview")


@app.get("/api/hive-mentor/health")
def hive_mentor_health():
    from app.moduller.hive_mentor import health
    return health()


@app.post("/api/hive-mentor/ask")
def hive_mentor_ask(req: HiveMentorAskBody):
    from app.moduller.hive_mentor import ask
    result = ask(req.question or "")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.get("/api/hive-mentor/recommendations")
def hive_mentor_recommendations(limit: int = 10):
    from app.moduller.hive_mentor import get_recommendations
    return get_recommendations(limit)


@app.get("/api/hive-mentor/context")
def hive_mentor_context():
    from app.moduller.hive_mentor import get_context
    return get_context()


@app.get("/api/first-run/health")
def first_run_health():
    from app.moduller.first_run_wizard import health
    return health()


@app.get("/api/first-run/status")
def first_run_status():
    from app.moduller.first_run_wizard import get_status
    return get_status()


@app.post("/api/first-run/complete-step")
def first_run_complete_step(req: FirstRunCompleteStepBody):
    from app.moduller.first_run_wizard import complete_step
    result = complete_step(req.step_id.strip(), manual=req.manual)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/first-run/reset")
def first_run_reset():
    from app.moduller.first_run_wizard import reset_wizard
    return reset_wizard()


# ── HIVE Success Path V2 ──


class SuccessPathSettingsBody(BaseModel):
    user_id: str | None = None
    role: str | None = None
    auto_start_on_wizard: bool | None = None
    enabled: bool | None = None


class SuccessPathExportBody(BaseModel):
    report_type: str = "overview"


@app.get("/api/success-path/health")
def success_path_health():
    from app.moduller.hive_success_path import health
    return health()


@app.get("/api/success-path/dashboard")
def success_path_dashboard():
    from app.moduller.hive_success_path import dashboard
    return dashboard()


@app.get("/api/success-path/progress")
def success_path_progress():
    from app.moduller.hive_success_path import get_progress
    return get_progress(recalculate=True)


@app.post("/api/success-path/recalculate")
def success_path_recalculate():
    from app.moduller.hive_success_path import recalculate
    result = recalculate()
    _brain_emit("/api/success-path/recalculate", {}, result, module="hive_success_path", event_type="success_step_completed")
    return result


@app.get("/api/success-path/steps")
def success_path_steps():
    from app.moduller.hive_success_path import get_steps
    return get_steps()


@app.get("/api/success-path/recommendations")
def success_path_recommendations(limit: int = 8):
    from app.moduller.hive_success_path import get_recommendations
    return get_recommendations(limit=limit)


@app.post("/api/success-path/export-report")
def success_path_export(req: SuccessPathExportBody):
    from app.moduller.hive_success_path import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/success-path/settings")
def success_path_settings_get():
    from app.moduller.hive_success_path import get_settings
    return {"success": True, "settings": get_settings()}


@app.post("/api/success-path/settings")
def success_path_settings_post(req: SuccessPathSettingsBody):
    from app.moduller.hive_success_path import update_settings
    return update_settings(req.model_dump(exclude_unset=True))


# ── Production Readiness Engine V1 ──


class ReadinessSettingsBody(BaseModel):
    enabled: bool | None = None
    min_production_score: int | None = None
    min_enterprise_score: int | None = None
    block_on_critical_audit: bool | None = None
    block_on_stuck_queue: bool | None = None


class ReadinessExportBody(BaseModel):
    report_type: str = "overview"


@app.get("/api/readiness/health")
def readiness_health():
    from app.moduller.production_readiness_engine import health
    return health()


@app.get("/api/readiness/dashboard")
def readiness_dashboard():
    from app.moduller.production_readiness_engine import dashboard
    return dashboard()


@app.post("/api/readiness/calculate")
def readiness_calculate():
    from app.moduller.production_readiness_engine import calculate
    result = calculate(persist=True)
    _brain_emit("/api/readiness/calculate", {}, result, module="production_readiness_engine", event_type="readiness_calculated")
    return result


@app.get("/api/readiness/report")
def readiness_report():
    from app.moduller.production_readiness_engine import get_report
    return get_report()


@app.get("/api/readiness/blockers")
def readiness_blockers():
    from app.moduller.production_readiness_engine import get_blockers
    return get_blockers()


@app.get("/api/readiness/warnings")
def readiness_warnings():
    from app.moduller.production_readiness_engine import get_warnings
    return get_warnings()


@app.post("/api/readiness/export-report")
def readiness_export(req: ReadinessExportBody):
    from app.moduller.production_readiness_engine import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/readiness/settings")
def readiness_settings_get():
    from app.moduller.production_readiness_engine import get_settings
    return {"success": True, "settings": get_settings()}


@app.post("/api/readiness/settings")
def readiness_settings_post(req: ReadinessSettingsBody):
    from app.moduller.production_readiness_engine import update_settings
    return update_settings(req.model_dump(exclude_unset=True))


# ── Action Orchestrator V1 ──


class ActionOrchestratorImportPlanBody(BaseModel):
    source_module: str = ""
    project_id: str = ""
    plan: dict | None = None


class ActionOrchestratorCreateActionBody(BaseModel):
    model_config = ConfigDict(extra="allow")


class ActionOrchestratorRunActionBody(BaseModel):
    approve: bool = False
    force: bool = False


class ActionOrchestratorExportBody(BaseModel):
    report_type: str = "overview"


class ActionOrchestratorSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/action-orchestrator/health")
def action_orchestrator_health():
    from app.moduller.action_orchestrator import health
    return health()


@app.get("/api/action-orchestrator/dashboard")
def action_orchestrator_dashboard():
    from app.moduller.action_orchestrator import build_dashboard
    return build_dashboard()


@app.post("/api/action-orchestrator/import-plan")
def action_orchestrator_import_plan(req: ActionOrchestratorImportPlanBody):
    from app.moduller.action_orchestrator import import_plan
    result = import_plan(req.source_module, req.plan or {}, project_id=req.project_id or "")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/action-orchestrator/create-action")
def action_orchestrator_create_action(req: ActionOrchestratorCreateActionBody):
    from app.moduller.action_orchestrator import create_action
    data = req.model_dump(exclude_unset=True)
    result = create_action(**data)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/action-orchestrator/run-action/{action_id}")
def action_orchestrator_run_action(action_id: str, req: ActionOrchestratorRunActionBody | None = None):
    from app.moduller.action_orchestrator import run_action
    body = req or ActionOrchestratorRunActionBody()
    result = run_action(action_id, approve=body.approve, force=body.force)
    if not result.get("success") and result.get("error") and "plan_only" not in str(result.get("error", "")):
        if result.get("status") != "waiting_approval":
            raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/action-orchestrator/cancel-action/{action_id}")
def action_orchestrator_cancel_action(action_id: str):
    from app.moduller.action_orchestrator import cancel_action
    result = cancel_action(action_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.get("/api/action-orchestrator/actions")
def action_orchestrator_list_actions(status: str = "", source_module: str = "", pipeline_id: str = "", limit: int = 50):
    from app.moduller.action_orchestrator import list_actions
    return list_actions(status=status, source_module=source_module, pipeline_id=pipeline_id, limit=limit)


@app.get("/api/action-orchestrator/action/{action_id}")
def action_orchestrator_get_action(action_id: str):
    from app.moduller.action_orchestrator import get_action
    result = get_action(action_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/api/action-orchestrator/pipelines")
def action_orchestrator_pipelines(limit: int = 30):
    from app.moduller.action_orchestrator import list_pipelines
    return list_pipelines(limit=limit)


@app.post("/api/action-orchestrator/export-report")
def action_orchestrator_export_report(req: ActionOrchestratorExportBody):
    from app.moduller.action_orchestrator import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/action-orchestrator/settings")
def action_orchestrator_get_settings():
    from app.moduller.action_orchestrator import get_settings
    return {"settings": get_settings()}


@app.post("/api/action-orchestrator/settings")
def action_orchestrator_update_settings(req: ActionOrchestratorSettingsBody):
    from app.moduller.action_orchestrator import update_settings
    result = update_settings(req.model_dump(exclude_unset=True))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


class AutonomousAgentAnalyzeBody(BaseModel):
    project_id: str = ""
    network_id: str = ""
    agents: list[str] | None = None


class AutonomousAgentMissionBody(BaseModel):
    project_id: str = ""
    network_id: str = ""


class AutonomousAgentExportReportBody(BaseModel):
    report_type: str = "overview"


class AutonomousAgentSettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/api/autonomous-agent/health")
def autonomous_agent_health():
    from app.moduller.autonomous_seo_agent import health
    return health()


@app.get("/api/autonomous-agent/dashboard")
def autonomous_agent_dashboard(project_id: str = "", network_id: str = ""):
    from app.moduller.autonomous_seo_agent import dashboard
    return dashboard(project_id, network_id)


@app.post("/api/autonomous-agent/analyze-project")
def autonomous_agent_analyze_project(req: AutonomousAgentAnalyzeBody):
    from app.moduller.autonomous_seo_agent import analyze_project
    result = analyze_project(req.project_id.strip(), req.network_id.strip(), agents=req.agents)
    if not result.get("success") and result.get("error") == "agent_disabled":
        raise HTTPException(status_code=403, detail=result.get("message") or result.get("error"))
    _brain_emit("/api/autonomous-agent/analyze-project", req, result, module="autonomous_seo_agent")
    return result


@app.post("/api/autonomous-agent/generate-daily-mission")
def autonomous_agent_daily_mission(req: AutonomousAgentMissionBody):
    from app.moduller.autonomous_seo_agent import generate_daily_mission
    result = generate_daily_mission(req.project_id.strip(), req.network_id.strip())
    if not result.get("success") and result.get("error") == "agent_disabled":
        raise HTTPException(status_code=403, detail=result.get("message") or result.get("error"))
    return result


@app.post("/api/autonomous-agent/generate-weekly-mission")
def autonomous_agent_weekly_mission(req: AutonomousAgentMissionBody):
    from app.moduller.autonomous_seo_agent import generate_weekly_mission
    result = generate_weekly_mission(req.project_id.strip(), req.network_id.strip())
    if not result.get("success") and result.get("error") == "agent_disabled":
        raise HTTPException(status_code=403, detail=result.get("message") or result.get("error"))
    return result


@app.post("/api/autonomous-agent/generate-action-plan")
def autonomous_agent_action_plan(req: AutonomousAgentMissionBody):
    from app.moduller.autonomous_seo_agent import generate_action_plan
    result = generate_action_plan(req.project_id.strip(), req.network_id.strip())
    if not result.get("success") and result.get("error") == "agent_disabled":
        raise HTTPException(status_code=403, detail=result.get("message") or result.get("error"))
    return result


@app.get("/api/autonomous-agent/decisions")
def autonomous_agent_decisions(limit: int = 50, agent_type: str = "", project_id: str = ""):
    from app.moduller.autonomous_seo_agent import list_decisions
    return list_decisions(limit=limit, agent_type=agent_type, project_id=project_id)


@app.get("/api/autonomous-agent/missions")
def autonomous_agent_missions(mission_type: str = ""):
    from app.moduller.autonomous_seo_agent import list_missions
    return list_missions(mission_type)


@app.get("/api/autonomous-agent/reports")
def autonomous_agent_reports():
    from app.moduller.autonomous_seo_agent import list_reports
    return list_reports()


@app.post("/api/autonomous-agent/export-report")
def autonomous_agent_export_report(req: AutonomousAgentExportReportBody):
    from app.moduller.autonomous_seo_agent import export_report
    return export_report(req.report_type or "overview")


@app.get("/api/autonomous-agent/settings")
def autonomous_agent_get_settings():
    from app.moduller.autonomous_seo_agent import get_settings
    return {"settings": get_settings()}


@app.post("/api/autonomous-agent/settings")
def autonomous_agent_update_settings(req: AutonomousAgentSettingsBody):
    from app.moduller.autonomous_seo_agent import update_settings
    try:
        settings = update_settings(req.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"success": True, "settings": settings}


@app.get("/api/support-network-engine/health")
def support_network_engine_health():
    from app.moduller.support_network_engine import health
    return health()


@app.get("/api/support-network-engine/settings")
def support_network_engine_get_settings():
    from app.moduller.support_network_engine import get_settings
    return {"settings": get_settings()}


@app.post("/api/support-network-engine/settings")
def support_network_engine_update_settings(req: SupportNetworkSettingsBody):
    from app.moduller.support_network_engine import update_settings
    return {"success": True, "settings": update_settings(req.model_dump(exclude_unset=True))}


@app.get("/api/support-network-engine/domains")
def support_network_engine_domains(network_id: str = ""):
    from app.moduller.support_network_engine import list_domains
    return list_domains(network_id)


@app.get("/api/support-network-engine/authority")
def support_network_engine_authority(network_id: str = ""):
    from app.moduller.support_network_engine import authority_map
    result = authority_map(network_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Authority analizi yapılamadı"))
    return result


@app.get("/api/support-network-engine/links")
def support_network_engine_links(network_id: str = "", max_per_domain: int = 5):
    from app.moduller.support_network_engine import link_strategy
    result = link_strategy(network_id, max_per_domain=max_per_domain)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Link planı üretilemedi"))
    return result


@app.get("/api/support-network-engine/keywords")
def support_network_engine_keywords(network_id: str = ""):
    from app.moduller.support_network_engine import keyword_distribution
    return keyword_distribution(network_id)


@app.get("/api/support-network-engine/health-score")
def support_network_engine_health_score(network_id: str = ""):
    from app.moduller.support_network_engine import network_health
    result = network_health(network_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Network health hesaplanamadı"))
    return result


@app.get("/api/support-network-engine/gaps")
def support_network_engine_gaps(network_id: str = ""):
    from app.moduller.support_network_engine import network_gaps
    return network_gaps(network_id)


@app.get("/api/support-network-engine/rank")
def support_network_engine_rank(network_id: str = ""):
    from app.moduller.support_network_engine import rank_overview
    return rank_overview(network_id)


@app.get("/api/support-network-engine/refresh")
def support_network_engine_refresh(network_id: str = ""):
    from app.moduller.support_network_engine import refresh_overview
    return refresh_overview(network_id)


@app.get("/api/support-network-engine/publisher")
def support_network_engine_publisher(network_id: str = ""):
    from app.moduller.support_network_engine import publisher_overview
    return publisher_overview(network_id)


@app.get("/api/support-network-engine/quality")
def support_network_engine_quality(network_id: str = ""):
    from app.moduller.support_network_engine import quality_overview
    return quality_overview(network_id)


@app.post("/api/support-network-engine/suggest-role")
def support_network_engine_suggest_role(req: SupportNetworkRoleBody):
    from app.moduller.support_network_engine import suggest_role
    return suggest_role(req.domain, req.index)


@app.post("/api/support-network-engine/sync")
def support_network_engine_sync(network_id: str = ""):
    from app.moduller.support_network_engine import sync_network
    return sync_network(network_id)


@app.post("/api/support-network-engine/export-report")
def support_network_engine_export(report_type: str = "overview", network_id: str = ""):
    from app.moduller.support_network_engine import export_report
    return export_report(report_type=report_type, network_id=network_id)


@app.delete("/api/blogger/post/{post_id}")
def blogger_delete_post(post_id: str, blog_id: str = ""):
    from app.moduller.blogger_api import delete_post, is_configured
    if not is_configured():
        raise HTTPException(status_code=400, detail="Blogger OAuth yapılandırılmamış")
    try:
        return delete_post(post_id, blog_id or None)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ==================== BACKLINK SUITE ====================
class BacklinkHunterBody(BaseModel):
    competitors: list[str] = []
    our_domain: str = ""
    limit: int = 50
    provider: str = ""  # auto | free | dataforseo


class LinkSprayerBody(BaseModel):
    hedef_url: str = ""
    keyword: str = ""
    site_url: str = ""
    adet: int = 10


class DirectoryBody(BaseModel):
    site_url: str = ""
    site_name: str = ""
    limit: int = 20


class InternalLinkBody(BaseModel):
    min_score: float = 1.0
    limit: int = 30
    max_apply: int = 5
    suggestion_ids: list[int] = []


class CompetitorHijackerBody(BaseModel):
    domain: str = ""
    send_to_hunter: bool = True
    limit: int = 100
    provider: str = ""


class SeoAgentBody(BaseModel):
    konu: str = ""
    keyword: str = ""
    publish: bool = True
    publish_at: str = ""
    delay_minutes: int = 60


class ExportBody(BaseModel):
    format: str = "json"


@app.get("/api/backlink-dashboard")
def backlink_dashboard():
    from app.moduller.backlink_hub import dashboard
    return dashboard()


@app.post("/api/backlink-hunter/opportunities")
def backlink_hunter_opportunities(req: BacklinkHunterBody):
    from app.moduller.backlink_hunter import opportunities
    comps = req.competitors or ["example.com"]
    return log_and_return("backlink_hunter", "Backlink Hunter - Fırsatlar", req, opportunities(comps, req.our_domain, req.limit, provider=req.provider.strip() or None))


@app.get("/api/backlink-hunter/opportunities")
def backlink_hunter_opportunities_get():
    from app.moduller.backlink_hub import get_opportunities
    return {"status": "aktif", "firsatlar": get_opportunities(100)}


@app.post("/api/backlink-hunter/export")
def backlink_hunter_export(req: ExportBody):
    from app.moduller.backlink_hunter import export_opportunities
    return log_and_return("backlink_hunter", "Backlink Hunter - Export", req, export_opportunities(req.format))


@app.get("/api/backlink-hunter/health")
def backlink_hunter_health():
    from app.moduller.backlink_hunter import health
    return health()


@app.post("/api/backlink-hunter/backlinks")
def backlink_hunter_get_backlinks(req: ModulRequest):
    from app.moduller.backlink_hunter import get_backlinks
    domain = getattr(req, "domain", "") or getattr(req, "hedef", "")
    if not domain.strip():
        raise HTTPException(status_code=400, detail="domain gerekli")
    limit = int(getattr(req, "limit", 50) or 50)
    return log_and_return("backlink_hunter", "Backlink Hunter - Get Backlinks", req, get_backlinks(domain.strip(), limit=limit))


@app.post("/api/backlink-hunter/competitor-backlinks")
def backlink_hunter_competitor(req: ModulRequest):
    from app.moduller.backlink_hunter import get_competitor_backlinks
    domain = getattr(req, "domain", "") or getattr(req, "hedef", "")
    if not domain.strip():
        raise HTTPException(status_code=400, detail="domain gerekli")
    limit = int(getattr(req, "limit", 50) or 50)
    return log_and_return("backlink_hunter", "Backlink Hunter - Competitor Backlinks", req, get_competitor_backlinks(domain.strip(), limit=limit))


@app.post("/api/linksprayer/campaign")
def linksprayer_campaign(req: LinkSprayerBody):
    from app.moduller.linksprayer import start_campaign
    return log_and_return("linksprayer", "LinkSprayer - Kampanya", req, start_campaign(req.hedef_url, req.keyword, req.site_url, req.adet))


@app.get("/api/linksprayer/campaign")
def linksprayer_campaign_list(campaign_id: str = ""):
    from app.moduller.linksprayer import campaign_status
    return campaign_status(campaign_id)


@app.get("/api/directory-submitter/directories")
def directory_list():
    from app.moduller.directory_submitter import load_directories
    dirs = load_directories()
    return {"status": "aktif", "toplam": len(dirs), "dizinler": dirs[:50]}


@app.post("/api/directory-submitter/submit")
def directory_submit(req: DirectoryBody):
    from app.moduller.directory_submitter import submit_bulk
    return log_and_return("directory_submitter", "Directory Submitter", req, submit_bulk(req.site_url, req.site_name, req.limit))


@app.get("/api/directory-submitter/status")
def directory_status(job_id: str = ""):
    from app.moduller.directory_submitter import status_report
    return status_report(job_id)


@app.post("/api/internal-link-builder/suggest")
def internal_link_suggest(req: InternalLinkBody):
    from app.moduller.internal_link_builder import suggest_links
    return log_and_return("internal_link_builder", "Internal Link - Öner", req, suggest_links(req.min_score, req.limit))


@app.post("/api/internal-link-builder/apply")
def internal_link_apply(req: InternalLinkBody):
    from app.moduller.internal_link_builder import apply_to_wordpress
    return log_and_return("internal_link_builder", "Internal Link - Uygula", req, apply_to_wordpress(req.suggestion_ids, req.max_apply))


@app.post("/api/competitor-hijacker/analyze")
def competitor_hijacker_analyze(req: CompetitorHijackerBody):
    from app.moduller.competitor_hijacker import analyze_competitor
    return log_and_return("competitor_hijacker", "Competitor Hijacker", req, analyze_competitor(req.domain, req.send_to_hunter, req.limit, provider=req.provider.strip() or None))


@app.post("/api/seo-agent/generate")
def seo_agent_generate(req: SeoAgentBody):
    from app.moduller.seo_content_agent import generate_and_publish
    return log_and_return("seo_content_agent", "SEO Agent - Üret", req, generate_and_publish(req.konu, req.keyword, req.publish))


@app.post("/api/seo-agent/schedule")
def seo_agent_schedule(req: SeoAgentBody):
    from app.moduller.seo_content_agent import schedule_post
    return log_and_return("seo_content_agent", "SEO Agent - Zamanla", req, schedule_post(req.konu, req.keyword, req.publish_at, req.delay_minutes))


@app.get("/api/seo-agent/schedule")
def seo_agent_schedule_list():
    from app.moduller.seo_content_agent import list_scheduled
    return list_scheduled()


@app.post("/api/backlink-suite/run-all")
def backlink_suite_run_all(req: CompetitorHijackerBody):
    """Tüm backlink modüllerini sırayla tetikle."""
    from app.moduller.competitor_hijacker import analyze_competitor
    from app.moduller.backlink_hunter import opportunities
    from app.moduller.internal_link_builder import suggest_links
    from app.moduller.linksprayer import start_campaign
    from app.moduller.directory_submitter import submit_bulk
    from app.moduller.seo_content_agent import generate_and_publish
    from app.moduller.backlink_hub import dashboard

    domain = getattr(req, "domain", "") or "example.com"
    results = {
        "competitor": analyze_competitor(domain, True, 50),
        "hunter": opportunities([domain], domain, 30),
        "internal_links": suggest_links(),
        "linksprayer": start_campaign("", "seo", "", 5),
        "directory": submit_bulk(limit=10),
        "seo_agent": generate_and_publish("SEO Rehberi", "seo", publish=False),
        "dashboard": dashboard(),
    }
    log_module_run("backlink_suite", "Backlink Suite - Hepsini Çalıştır", {"domain": domain}, {"status": "aktif", "moduller": list(results.keys())})
    return {"status": "aktif", "sonuclar": results}


# ==================== INDEXING FIX ====================
class IndexingBody(BaseModel):
    site: str = ""


@app.get("/api/indexing/audit")
def indexing_audit(site: str = ""):
    from app.moduller.indexing_fix import audit_site
    return audit_site(site or None)


@app.post("/api/indexing/fix-all")
def indexing_fix_all(req: IndexingBody):
    from app.moduller.indexing_fix import run_full_fix
    result = run_full_fix(req.site or None)
    log_module_run("indexing", "İndeksleme otomatik düzelt", {"site": req.site}, result)
    return result


@app.post("/api/indexing/indexnow")
def indexing_indexnow(req: IndexingBody):
    from app.moduller.indexing_fix import submit_indexnow, _site_url
    site = (req.site or _site_url()).rstrip("/")
    result = submit_indexnow([site, f"{site}/wp-sitemap.xml"])
    log_module_run("indexnow", "IndexNow sitemap", {"site": site}, result)
    return result


@app.post("/api/indexing/robots-deploy")
def indexing_robots_deploy(req: IndexingBody):
    from app.moduller.indexing_fix import fix_robots_txt, submit_indexnow, _site_url
    site = (req.site or _site_url()).rstrip("/")
    robots_result = fix_robots_txt(site=site, politika="seo")
    indexnow_result = submit_indexnow([f"{site}/robots.txt", f"{site}/wp-sitemap.xml"])
    result = {"site": site, "robots_txt": robots_result, "indexnow": indexnow_result}
    log_module_run("robots", "robots.txt deploy", {"site": site}, result)
    return result


@app.get("/api/indexing/url-inventory")
def indexing_url_inventory(site: str = "", max_urls: int = 5000):
    from app.moduller.indexing_fix import build_url_inventory
    return build_url_inventory(site or None, max_urls=max_urls)


@app.get("/api/indexing/redirect-map")
def indexing_redirect_map(site: str = ""):
    from app.moduller.indexing_fix import build_url_inventory, build_redirect_map
    inv = build_url_inventory(site or None)
    redirects = build_redirect_map(inv.get("inventory") or [])
    return {"redirects": redirects, "count": len(redirects), "inventory_total": inv.get("total_urls", 0)}


@app.post("/api/indexing/balkutusu-recovery")
def indexing_balkutusu_recovery(req: IndexingBody):
    from app.moduller.indexing_fix import run_balkutusu_index_recovery
    result = run_balkutusu_index_recovery(req.site or None)
    log_module_run("indexing", "Balkutusu index recovery", {"site": req.site}, {
        "redirects": result.get("report", {}).get("redirects_generated", 0),
        "report_path": result.get("report_path"),
    })
    return result


@app.get("/api/indexing/robots-preview")
def indexing_robots_preview(site: str = ""):
    from app.moduller.indexing_fix import enhanced_robots_content, _site_url
    site_url = (site or _site_url()).rstrip("/")
    return {"site": site_url, "content": enhanced_robots_content(site_url)}


# ==================== SSS AUTOMATION ====================
from app.moduller.sss_generator import sss_generator
from app.moduller.sss_automation import sss_automation


class SSSGenerateBody(BaseModel):
    city: str = "Aydın"
    district: str = "Kuşadası"
    category: str = "Gece Hayatı"
    subcategory: str = "Barlar, kulüpler, eğlence mekanları"
    main_keyword: str = "kuşadası gece hayatı"
    secondary_keywords: list[str] | str = []


class SSSAutomationStartBody(BaseModel):
    city: str = "Aydın"
    district: str = "Kuşadası"
    category: str = "Gece Hayatı"
    subcategory: str = "Barlar, kulüpler, eğlence mekanları"
    main_keyword: str = "kuşadası gece hayatı"
    secondary_keywords: list[str] | str = []
    keyword_count: int = 50
    domain_id: int = 0
    extra_keywords: list[str] = []


@app.post("/api/sss/generate")
def sss_generate(req: SSSGenerateBody):
    sec = req.secondary_keywords
    if isinstance(sec, list):
        sec = ", ".join(sec)
    result = sss_generator.generate(
        req.city, req.district, req.category, req.subcategory,
        req.main_keyword, sec,
    )
    log_module_run("sss_generator", "SSS Üretici", req.model_dump(), {"status": "aktif", "title": result.get("seo_title")})
    return {"status": "success", "content": result}


@app.post("/api/sss-automation/start")
def sss_automation_start(req: SSSAutomationStartBody, background_tasks: BackgroundTasks):
    result = sss_automation.start(
        city=req.city,
        district=req.district,
        category=req.category,
        subcategory=req.subcategory,
        main_keyword=req.main_keyword,
        secondary_keywords=req.secondary_keywords,
        keyword_count=req.keyword_count,
        domain_id=req.domain_id,
        extra_keywords=req.extra_keywords,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Başlatılamadı"))

    run_args = result.pop("_run_args", None)
    if run_args:
        background_tasks.add_task(sss_automation.run_pipeline_task, *run_args)

    log_module_run("sss_automation", "SSS Otomatik Zincir Başlat", req.model_dump(), result)
    return result


@app.get("/api/sss-automation/status")
def sss_automation_status():
    return sss_automation.get_status()


@app.get("/api/sss-automation/report")
def sss_automation_report():
    return sss_automation.get_report()


@app.post("/api/sss-automation/preview")
def sss_automation_preview(req: SSSGenerateBody):
    sec = req.secondary_keywords
    if isinstance(sec, list):
        sec = ", ".join(sec)
    return sss_automation.preview(
        req.city, req.district, req.category, req.subcategory,
        req.main_keyword, sec,
    )


class SSSRepairBody(BaseModel):
    domain_id: int = 0
    limit: int = 50
    city: str = ""
    district: str = ""
    category: str = ""
    subcategory: str = ""
    secondary_keywords: str = ""


@app.post("/api/sss-automation/repair")
def sss_automation_repair(req: SSSRepairBody):
    result = sss_automation.repair_empty_pages(
        domain_id=req.domain_id,
        limit=req.limit,
        city=req.city,
        district=req.district,
        category=req.category,
        subcategory=req.subcategory,
        secondary_keywords=req.secondary_keywords,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Onarım başarısız"))
    log_module_run("sss_automation", "SSS Boş Sayfa Onarımı", req.model_dump(), result)
    return result


# ==================== HELPER FUNCTIONS ====================
# All helper functions are imported from app.moduller above

@app.get("/health")
def health():
    from app.moduller.talon_stack.providers.base import provider_health

    docker_ok = False
    searxng_live = False
    try:
        import shutil
        docker_ok = shutil.which("docker") is not None
    except Exception:
        pass
    try:
        import requests
        from app import config
        searxng_url = (config.get("SEARXNG_URL") or "").strip().rstrip("/")
        if searxng_url:
            r = requests.get(f"{searxng_url}/search?q=test&format=json", timeout=3)
            searxng_live = r.status_code == 200
    except Exception:
        pass

    ph = provider_health()
    talon_ready = ph.get("tavily") == "configured" or ph.get("exa") == "configured" or searxng_live

    return {
        "durum": "HIVE Panel çalışıyor",
        "versiyon": "3.0",
        "modul_sayisi": len(MODULLER),
        "aktif_modul": len(MODULLER),
        "urls": {
            "panel": "http://localhost:4000",
            "api": "http://localhost:4001",
            "docs": "http://localhost:4001/docs",
        },
        "talon_v2": {
            "ready": talon_ready,
            "providers": ph,
        },
        "docker": {
            "installed": docker_ok,
            "searxng_live": searxng_live,
        },
        "mocks": {
            "openseo": "in-process (port 4001/api/openseo/*)",
            "serpbear": "in-process (port 4001/api/serpbear/*)",
            "seointel": "in-process (port 4001/api/seointel/*)",
            "dataseo": "in-process (port 4001/api/dataseo/*)",
            "seoagent": "in-process (port 4001/api/seoagent/*)",
        },
    }
