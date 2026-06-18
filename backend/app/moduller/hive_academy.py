"""
HIVE Academy V1 — modül ansiklopedisi, workflow haritaları ve rehberler.

Mevcut SEO motorlarını değiştirmez; yalnızca öğretme ve dokümantasyon katmanıdır.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.moduller.hive_learn_content import (
    EXTRA_ENCYCLOPEDIA,
    EXTRA_GLOSSARY,
    GUIDE_DETAILS,
)

STATE_FILE = Path(__file__).resolve().parent.parent / "hive_academy_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("viewed_modules", [])
                data.setdefault("completed_guides", [])
                data.setdefault("completed_workflows", [])
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"viewed_modules": [], "completed_guides": [], "completed_workflows": [], "history": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_brain(reason: str, *, result: dict | None = None, metadata: dict | None = None) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            "module_action",
            "hive_academy",
            reason=reason,
            result=result or {},
            metadata={"engine": "hive_academy", **(metadata or {})},
        )
    except Exception as exc:
        logger.debug("brain: %s", exc)


def _entry(
    module_id: str,
    title: str,
    *,
    purpose: str,
    what_it_does: str,
    when_to_use: str,
    when_not_to_use: str,
    inputs: list[str],
    outputs: list[str],
    related: list[str],
    example: str,
    common_mistakes: list[str],
    pro_tips: list[str],
    guide_id: str = "",
    category: str = "tools",
    icon: str = "📦",
    first_steps: list[str] | None = None,
    env_keys: list[str] | None = None,
    api_prefix: str = "",
) -> dict[str, Any]:
    return {
        "module_id": module_id,
        "title": title,
        "purpose": purpose,
        "what_it_does": what_it_does,
        "when_to_use": when_to_use,
        "when_not_to_use": when_not_to_use,
        "inputs": inputs,
        "outputs": outputs,
        "related_modules": related,
        "example_usage": example,
        "common_mistakes": common_mistakes,
        "advanced_tips": pro_tips,
        "guide_id": guide_id or f"guide_{module_id}",
        "category": category,
        "icon": icon,
        "first_steps": first_steps or [],
        "env_keys": env_keys or [],
        "api_prefix": api_prefix,
    }


ENCYCLOPEDIA: dict[str, dict[str, Any]] = {
    "mission_control_center": _entry(
        "mission_control_center", "Mission Control / Command Center",
        category="command", icon="◆", api_prefix="/api/mission-control",
        first_steps=[
            "Sidebar COMMAND → Mission Control açın",
            "Operation Summary Bar — tehdit, fırsat, kuyruk sayılarına bakın",
            "HiveRecommendation kartındaki birincil aksiyonu uygulayın",
            "Module Status Wall'da not_configured modül varsa Wizard'a gidin",
        ],
        purpose="HIVE SEO OS'un merkezi operasyon kokpiti.",
        what_it_does="Sistem sağlığı, tehditler, fırsatlar, görevler ve modül durumlarını tek ekranda toplar.",
        when_to_use="Her gün işe başlarken; öncelik belirlemek ve hangi modüle gideceğinize karar vermek için.",
        when_not_to_use="Derin analiz veya içerik üretimi için — ilgili modüle gidin.",
        inputs=["Tüm modül durumları", "Brain timeline", "Agent görevleri"],
        outputs=["Önerilen aksiyonlar", "Günlük görev listesi", "Sistem sağlık skoru"],
        related=["hive_brain_engine", "autonomous_seo_agent", "serp_defense_engine", "opportunity_engine"],
        example="Sabah Mission Control aç → Active Threats kontrol → Today's Mission'dan ilk görevi seç.",
        common_mistakes=["Sadece KPI'ya bakıp aksiyon almamak", "Refresh etmeden eski veriye güvenmek"],
        pro_tips=["Live Event Stream ile son aktiviteleri takip edin", "Learning Progress kartından Academy ilerlemenizi görün"],
    ),
    "hive_brain_engine": _entry(
        "hive_brain_engine", "HIVE Brain",
        category="command", icon="🧠", api_prefix="/api/hive-brain",
        first_steps=[
            "Dashboard sekmesinde total_events kontrol edin — 0 ise Backfill çalıştırın",
            "Timeline sekmesinde son 14 gün aktivitesine bakın",
            "Project Memory için astro-proj-xxx gibi project_id ile arama yapın",
        ],
        purpose="Merkezi hafıza ve karar geçmişi katmanı.",
        what_it_does="Modül olaylarını, kararları ve proje hikayesini kaydeder; timeline oluşturur.",
        when_to_use="Geçmiş operasyonları incelemek, proje hafızasını görmek, audit için.",
        when_not_to_use="Yeni keyword analizi veya içerik üretimi başlatmak için.",
        inputs=["Modül event'leri", "Karar kayıtları", "Proje/domain/keyword meta"],
        outputs=["Timeline", "Project memory", "Decision log"],
        related=["mission_control_center", "autonomous_seo_agent"],
        example="Bir deploy sonrası Brain timeline'da publish event'lerini filtreleyin.",
        common_mistakes=["Brain'i pasif log sanmak — Mission Control bu veriyi kullanır"],
        pro_tips=["project_id tutarlı kullanın; backfill ile eski logları içe aktarın"],
    ),
    "autonomous_seo_agent": _entry(
        "autonomous_seo_agent", "Autonomous SEO Agent",
        category="command", icon="🤖", api_prefix="/api/autonomous-agent",
        first_steps=[
            "Dashboard → latest daily mission okuyun",
            "CRITICAL priority görevleri Action Orchestrator'a aktarın",
            "Haftalık mission ile crawl gap planlayın",
        ],
        purpose="Günlük ve haftalık SEO görev planı üretir.",
        what_it_does="Tehdit, fırsat ve modül verilerinden öncelikli görev listesi oluşturur.",
        when_to_use="Bugün ne yapmalıyım sorusuna yapılandırılmış cevap istediğinizde.",
        when_not_to_use="Tek keyword için derin SERP analizi — SERP Defense kullanın.",
        inputs=["SERP verisi", "Opportunity skorları", "Refresh kuyruğu", "Publisher durumu"],
        outputs=["Daily mission", "Weekly mission", "Suggested actions"],
        related=["mission_control_center", "serp_defense_engine", "opportunity_engine"],
        example="Agent daily mission → ilk CRITICAL görevi Publisher veya SERP modülünde tamamlayın.",
        common_mistakes=["Mission üretmeden manuel dağınık çalışmak"],
        pro_tips=["Haftalık mission ile crawl gap ve network gap'leri planlayın"],
    ),
    "serp_defense_engine": _entry(
        "serp_defense_engine", "SERP Defense Engine",
        category="seo_core", icon="🛡", api_prefix="/api/serp-defense",
        first_steps=[
            "Rank Watcher alert varsa keyword'ü not edin",
            "SERP Defense dashboard → top_risks listesi",
            "Fortress < 50 ise Content Refresh + internal link planı",
        ],
        purpose="Keyword pozisyon savunması ve fortress analizi.",
        what_it_does="Fortress Score, baskı seviyesi ve savunma stratejisi üretir.",
        when_to_use="Rank düşüşü, rakip baskısı veya kritik keyword savunması gerektiğinde.",
        when_not_to_use="Yeni keyword keşfi — Opportunity Engine kullanın.",
        inputs=["Keyword listesi", "Rank Watcher verisi", "SERP snapshot"],
        outputs=["Fortress raporu", "Risk listesi", "Savunma planı"],
        related=["rank_index_watcher", "opportunity_engine", "content_refresh_engine"],
        example="Kuşadası gece hayatı keyword'ünde fortress 61 → Content Refresh + internal link güçlendirme.",
        common_mistakes=["Fortress skorunu rank ile karıştırmak", "Savunma planını uygulamadan izlemek"],
        pro_tips=["Fortress düşük + yüksek trafik = öncelik CRITICAL"],
        guide_id="guide_serp_defense",
    ),
    "opportunity_engine": _entry(
        "opportunity_engine", "Opportunity Engine",
        category="seo_core", icon="⚡", api_prefix="/api/opportunity",
        first_steps=[
            "Dashboard → top_opportunities (score > 75)",
            "Crawl Gap export ile cross-reference",
            "En iyi 3 quick win'i Publisher kuyruğuna alın",
        ],
        purpose="Büyüme fırsatlarını ve quick win'leri tespit eder.",
        what_it_does="Trafik potansiyeli, zorluk ve opportunity skoru hesaplar.",
        when_to_use="Yeni keyword hedeflemek, quick win listesi oluşturmak, büyüme planı yapmak.",
        when_not_to_use="Aktif SERP tehdidi varken — önce SERP Defense.",
        inputs=["Keyword verisi", "Crawl Gap export", "Rank verisi"],
        outputs=["Quick wins", "Opportunity skorları", "Öncelik listesi"],
        related=["crawl_gap_engine", "publisher_hub", "question_intelligence_engine"],
        example="18 quick win bulundu → en yüksek trafik skorlu 3 keyword için içerik planı.",
        common_mistakes=["Düşük zorluk filtresini çok gevşek bırakmak"],
        pro_tips=["Crawl Gap'ten export alıp Opportunity'ye aktarın"],
        guide_id="guide_opportunity",
    ),
    "crawl_gap_engine": _entry(
        "crawl_gap_engine", "Crawl & Gap Engine",
        category="seo_core", icon="🕷", api_prefix="/api/crawl-gap",
        first_steps=[
            "analyze-domain ile crawl başlatın",
            "Job bitince critical_gaps sayısına bakın",
            "FAQ cluster üret → Opportunity export",
        ],
        purpose="Site crawl sonrası entity, FAQ, GEO ve cluster açıklarını bulur.",
        what_it_does="Gap analizi yapar; FAQ/entity eksiklerini raporlar.",
        when_to_use="Yeni site audit, içerik boşluk analizi, FAQ cluster planı.",
        when_not_to_use="Canlı rank takibi — Rank Watcher.",
        inputs=["Site URL", "Crawl config", "Proje ID"],
        outputs=["FAQ gaps", "Entity gaps", "Critical gaps", "Opportunity export"],
        related=["opportunity_engine", "question_intelligence_engine", "astro_factory"],
        example="73 FAQ açığı → Generate Cluster → Publisher kuyruğuna aktar.",
        common_mistakes=["Crawl bitmeden gap sayılarına güvenmek"],
        pro_tips=["Critical gaps'i haftalık Agent mission'a bağlayın"],
        guide_id="guide_crawl_gap",
    ),
    "rank_index_watcher": _entry(
        "rank_index_watcher", "Rank & Index Watcher",
        category="seo_core", icon="📈", api_prefix="/api/rank-watcher",
        first_steps=[
            "New Project → domain + isim",
            "Min 5 money keyword ekleyin",
            "Mission Control rank_status doğrulayın",
        ],
        purpose="Pozisyon ve indeks sağlığı izleme.",
        what_it_does="Rank drop/gain alertleri, index issue tespiti.",
        when_to_use="Keyword pozisyon takibi, deploy sonrası index kontrolü.",
        when_not_to_use="İçerik üretimi — Publisher veya Astro.",
        inputs=["Domain", "Keyword listesi", "GSC bağlantısı (opsiyonel)"],
        outputs=["Rank alerts", "Index issues", "Project health"],
        related=["serp_defense_engine", "mission_control_center"],
        example="İlk proje oluştur → kritik keyword'leri ekle → Mission Control'de rank drop alert.",
        common_mistakes=["Proje oluşturmadan SERP Defense'e geçmek"],
        pro_tips=["Deploy sonrası 48 saat içinde index kontrolü yapın"],
        guide_id="guide_rank_watcher",
    ),
    "publisher_hub": _entry(
        "publisher_hub", "Publisher Hub",
        category="content", icon="📢", api_prefix="/api/publisher",
        first_steps=[
            "Dashboard queued/drafts/published sayaçları",
            "Draft oluştur veya CRE export import",
            "Quality Gate pass → kanal publish",
        ],
        purpose="İçerik yayın pipeline'ı ve kanal yönetimi.",
        what_it_does="Taslak, kuyruk, yayın ve kanal entegrasyonlarını yönetir.",
        when_to_use="İçerik hazır → yayın kuyruğuna al → kanallara dağıt.",
        when_not_to_use="Keyword araştırması — Opportunity veya QIE.",
        inputs=["Taslaklar", "CRE/Refresh export", "Kanal credentials"],
        outputs=["Published URL'ler", "Queue status", "Channel health"],
        related=["content_refresh_engine", "astro_auto_publisher", "authority_mesh_engine"],
        example="7 içerik kuyrukta → SEO Gate geç → WordPress/Blogger'a yayınla.",
        common_mistakes=["Quality Gate atlamak", "Kuyruğu boş bırakıp deploy beklemek"],
        pro_tips=["CRE requeue ile refresh adaylarını otomatik kuyruğa alın"],
        guide_id="guide_publisher",
    ),
    "authority_mesh_engine": _entry(
        "authority_mesh_engine", "Authority Mesh Engine",
        category="network", icon="🌎", api_prefix="/api/authority-mesh",
        env_keys=["GITHUB_TOKEN", "GOOGLE_REFRESH_TOKEN"],
        first_steps=[
            "Mesh plan oluştur (keyword + money site URL)",
            "Google Sites + GitHub Pages worker health kontrol",
            "Task publish — login_required=0 olmalı",
        ],
        purpose="Support site ağı ve authority dağıtımı.",
        what_it_does="Google Sites, GitHub Pages ve mesh planları ile authority inşa eder.",
        when_to_use="Money site'e destek ağı kurmak, geo hub oluşturmak.",
        when_not_to_use="Tek blog yazısı yayınlamak — Publisher Hub.",
        inputs=["Keyword", "Money site URL", "Mesh plan", "Worker credentials"],
        outputs=["Published support sites", "Task queue", "Link policy"],
        related=["support_network_engine", "google_sites_worker", "github_pages_worker"],
        example="Kuşadası gece hayatı → 4 support site planı → Google Sites worker ile yayın.",
        common_mistakes=["Login required task'ları görmezden gelmek"],
        pro_tips=["Browser worker health'i Mission Control'den izleyin"],
        guide_id="guide_authority_mesh",
    ),
    "content_refresh_engine": _entry(
        "content_refresh_engine", "Content Refresh Engine",
        category="content", icon="♻️", api_prefix="/api/content-refresh",
        first_steps=[
            "Scan çalıştır → critical_pages listesi",
            "Refresh plan oluştur → queue",
            "Publisher requeue ile yayına al",
        ],
        purpose="Decay gösteren sayfaları tespit edip yenileme kuyruğu oluşturur.",
        what_it_does="Critical/high priority sayfa listesi ve refresh pipeline.",
        when_to_use="Rank düşüşü, eski içerik, SERP savunması desteği.",
        when_not_to_use="Sıfırdan yeni site — Astro Factory.",
        inputs=["Site crawl", "Rank signals", "Decay rules"],
        outputs=["Refresh queue", "Priority pages", "Last refresh log"],
        related=["serp_defense_engine", "publisher_hub"],
        example="12 critical page → refresh plan → Publisher kuyruğu.",
        common_mistakes=["Critical sayfaları haftalarca kuyrukta bırakmak"],
        pro_tips=["SERP Defense risk keyword'leri ile cross-reference yapın"],
    ),
    "astro_factory": _entry(
        "astro_factory", "Astro Site Factory",
        purpose="Statik Astro site üretimi.",
        what_it_does="Template ve içerikten deploy-ready Astro projeleri oluşturur.",
        when_to_use="Yeni geo/micro site, hızlı landing cluster.",
        when_not_to_use="Mevcut WordPress içeriği güncelleme.",
        inputs=["Template", "Content bundle", "Domain config"],
        outputs=["Astro project", "Build artifact"],
        related=["astro_auto_publisher", "publisher_hub"],
        example="İlk Astro projesi → Factory'de oluştur → Auto Publisher'a aktar.",
        common_mistakes=["Build almadan publish denemek"],
        pro_tips=["Wizard adım 4'te ilk projeyi tamamlayın"],
    ),
    "astro_auto_publisher": _entry(
        "astro_auto_publisher", "Astro Auto Publisher",
        purpose="Astro projelerini otomatik deploy eder.",
        what_it_does="Queue, quality gate ve deploy pipeline.",
        when_to_use="Factory çıktısını canlıya almak.",
        when_not_to_use="Manuel WordPress edit — WP Manager.",
        inputs=["Astro queue", "Deploy target", "Quality rules"],
        outputs=["Deploy URL", "Queue status"],
        related=["astro_factory", "seo_quality_gate"],
        example="Queued deploy → quality pass → live URL Mission Control Last Deploy'da görünür.",
        common_mistakes=["Quality fail sonrası tekrar denemeden bırakmak"],
        pro_tips=["Deploy sonrası Rank Watcher'a URL ekleyin"],
    ),
    "support_network_engine": _entry(
        "support_network_engine", "Support Network Engine",
        purpose="Backlink ve support site ağı haritası.",
        what_it_does="Network gap, authority map ve replikasyon önerileri.",
        when_to_use="Network büyütme, gap kapatma, replikator planı.",
        when_not_to_use="Tek site publish — Authority Mesh.",
        inputs=["Site listesi", "Link graph", "Gap rules"],
        outputs=["Network score", "Gap list", "Replication hints"],
        related=["authority_mesh_engine", "network_replicator"],
        example="Network gap 5 → mesh plan oluştur → Authority Mesh task.",
        common_mistakes=["Support site olmadan sadece money site link spam"],
        pro_tips=["Workflow: Network büyütme haritasını takip edin"],
    ),
    "question_intelligence_engine": _entry(
        "question_intelligence_engine", "Question Intelligence Engine (QIE)",
        purpose="Soru-cevap ve FAQ intelligence.",
        what_it_does="People Also Ask, SSS zinciri ve FAQ cluster üretir.",
        when_to_use="FAQ içerik planı, AEO/GEO optimizasyonu.",
        when_not_to_use="Raw crawl — Crawl Gap.",
        inputs=["Keyword", "SERP questions", "Entity context"],
        outputs=["FAQ clusters", "SSS chains", "QIE export"],
        related=["crawl_gap_engine", "publisher_hub", "sss_automation"],
        example="FAQ gap bulundu → QIE ile soru seti → Publisher draft.",
        common_mistakes=["Soruları cevaplamadan sadece listelemek"],
        pro_tips=["Crawl Gap FAQ export ile birleştirin"],
    ),
    "talon": _entry(
        "talon", "Talon SEO Karar Merkezi",
        purpose="Üst düzey SEO karar ve orchestration hub.",
        what_it_does="Modüller arası karar akışını koordine eder.",
        when_to_use="Stratejik öncelik belirleme, multi-modül plan.",
        when_not_to_use="Günlük operasyon — Mission Control.",
        inputs=["Proje hedefleri", "Modül durumları"],
        outputs=["Karar önerileri", "Orchestration planı"],
        related=["mission_control_center", "hive_brain_engine"],
        example="Yeni geo vertical açılışı → Talon'da plan → modüllere dağıt.",
        common_mistakes=["Talon'u tek modül sanmak"],
        pro_tips=["SSS ve Page Hub'a hızlı geçiş linklerini kullanın"],
    ),
    "wordpress": _entry(
        "wordpress", "WordPress Manager",
        purpose="WordPress multisite bağlantı ve yayın.",
        what_it_does="WP REST API oturumu, site listesi, içerik yönetimi.",
        when_to_use="Ana WP ağına bağlanmak, First Run Wizard adım 1.",
        when_not_to_use="Statik site — Astro veya GitHub Pages.",
        inputs=["WP URL", "Credentials", "Application password"],
        outputs=["Connected session", "Site list", "Publish result"],
        related=["publisher_hub", "first_run_wizard"],
        example="Wizard: WP bağlantısı → Publisher kanalı aktif.",
        common_mistakes=["Application password yerine admin şifresi kullanmak"],
        pro_tips=[".env + session dosyasını yedekleyin"],
        guide_id="guide_wordpress",
    ),
    "blogger": _entry(
        "blogger", "Blogger Yöneticisi",
        category="workers", icon="📰", api_prefix="/api/blogger",
        env_keys=["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"],
        first_steps=[
            "Google OAuth credentials .env'e ekleyin",
            "Blogger → OAuth bağlantısı",
            "Default blog seç → Publisher kanalı aktif",
        ],
        purpose="Google Blogger OAuth ve yayın.",
        what_it_does="Blog listesi, post oluşturma ve publish.",
        when_to_use="Blogger support channel, Wizard adım 3.",
        when_not_to_use="Ana money site WP ise — WordPress.",
        inputs=["Google OAuth", "Blog ID", "Post content"],
        outputs=["Published post URL"],
        related=["publisher_hub", "authority_mesh_engine"],
        example="OAuth tamam → default blog seç → Publisher'dan cross-post.",
        common_mistakes=["Refresh token süresi dolunca yenilememek"],
        pro_tips=["GOOGLE_REFRESH_TOKEN'ı .env'de güvenli tutun"],
    ),
}


ENCYCLOPEDIA.update(EXTRA_ENCYCLOPEDIA)


WORKFLOWS: list[dict[str, Any]] = [
    {
        "workflow_id": "new_site_launch",
        "title": "Yeni Site Açma",
        "description": "Sıfırdan geo/micro site ve ilk deploy.",
        "steps": [
            {"order": 1, "title": "Astro Factory'de proje oluştur", "module_id": "astro_factory", "deep_link": "astro_factory"},
            {"order": 2, "title": "Quality Gate'den geçir", "module_id": "seo_quality_gate", "deep_link": "seo_quality_gate"},
            {"order": 3, "title": "Auto Publisher ile deploy", "module_id": "astro_auto_publisher", "deep_link": "astro_auto_publisher"},
            {"order": 4, "title": "Rank Watcher projesi aç", "module_id": "rank_index_watcher", "deep_link": "rank_index_watcher"},
            {"order": 5, "title": "Mission Control'de doğrula", "module_id": "mission_control_center", "deep_link": "mission_control_center"},
        ],
    },
    {
        "workflow_id": "keyword_growth",
        "title": "Keyword Büyütme",
        "description": "Yeni keyword vertical açma ve trafik büyütme.",
        "steps": [
            {"order": 1, "title": "Opportunity Engine quick win tara", "module_id": "opportunity_engine", "deep_link": "opportunity_engine"},
            {"order": 2, "title": "Crawl Gap ile içerik boşlukları", "module_id": "crawl_gap_engine", "deep_link": "crawl_gap_engine"},
            {"order": 3, "title": "QIE ile FAQ cluster", "module_id": "question_intelligence_engine", "deep_link": "question_intelligence_engine"},
            {"order": 4, "title": "Publisher ile yayınla", "module_id": "publisher_hub", "deep_link": "publisher_hub"},
            {"order": 5, "title": "Rank Watcher ile takip", "module_id": "rank_index_watcher", "deep_link": "rank_index_watcher"},
        ],
    },
    {
        "workflow_id": "serp_defense",
        "title": "SERP Savunması",
        "description": "Mevcut keyword pozisyonunu koruma.",
        "steps": [
            {"order": 1, "title": "Rank Watcher alert kontrol", "module_id": "rank_index_watcher", "deep_link": "rank_index_watcher"},
            {"order": 2, "title": "SERP Defense fortress analizi", "module_id": "serp_defense_engine", "deep_link": "serp_defense_engine"},
            {"order": 3, "title": "Content Refresh critical sayfalar", "module_id": "content_refresh_engine", "deep_link": "content_refresh_engine"},
            {"order": 4, "title": "Autonomous Agent savunma görevi", "module_id": "autonomous_seo_agent", "deep_link": "autonomous_seo_agent"},
        ],
    },
    {
        "workflow_id": "authority_building",
        "title": "Authority Kurma",
        "description": "Support site ağı ve mesh plan.",
        "steps": [
            {"order": 1, "title": "Support Network gap analizi", "module_id": "support_network_engine", "deep_link": "support_network_engine"},
            {"order": 2, "title": "Authority Mesh plan oluştur", "module_id": "authority_mesh_engine", "deep_link": "authority_mesh_engine"},
            {"order": 3, "title": "Google Sites / GitHub worker", "module_id": "authority_mesh_engine", "deep_link": "authority_mesh_engine"},
            {"order": 4, "title": "Publisher cross-link", "module_id": "publisher_hub", "deep_link": "publisher_hub"},
        ],
    },
    {
        "workflow_id": "content_publishing",
        "title": "İçerik Yayınlama",
        "description": "Taslaktan canlı yayına pipeline.",
        "steps": [
            {"order": 1, "title": "İçerik kaynağı tara (CRE/Astro/QIE)", "module_id": "content_refresh_engine", "deep_link": "content_refresh_engine"},
            {"order": 2, "title": "Publisher kuyruğa al", "module_id": "publisher_hub", "deep_link": "publisher_hub"},
            {"order": 3, "title": "SEO Quality Gate", "module_id": "seo_quality_gate", "deep_link": "seo_quality_gate"},
            {"order": 4, "title": "Kanal seç (WP/Blogger/Tumblr)", "module_id": "publisher_hub", "deep_link": "publisher_hub"},
            {"order": 5, "title": "Brain'de publish event doğrula", "module_id": "hive_brain_engine", "deep_link": "hive_brain_engine"},
        ],
    },
    {
        "workflow_id": "network_growth",
        "title": "Network Büyütme",
        "description": "Replikasyon ve ağ genişletme.",
        "steps": [
            {"order": 1, "title": "Network Replicator plan", "module_id": "network_replicator", "deep_link": "network_replicator"},
            {"order": 2, "title": "Site Replicator clone", "module_id": "site_replicator", "deep_link": "site_replicator"},
            {"order": 3, "title": "Authority Mesh yeni site", "module_id": "authority_mesh_engine", "deep_link": "authority_mesh_engine"},
            {"order": 4, "title": "Support Network skor kontrol", "module_id": "support_network_engine", "deep_link": "support_network_engine"},
        ],
    },
]


GUIDES: list[dict[str, Any]] = [
    {"guide_id": "guide_publisher", "title": "Publisher Rehberi", "module_id": "publisher_hub", "summary": "Kuyruk, taslak ve kanal yayın pipeline'ı."},
    {"guide_id": "guide_serp_defense", "title": "SERP Savunma Rehberi", "module_id": "serp_defense_engine", "summary": "Fortress Score ve savunma stratejisi."},
    {"guide_id": "guide_opportunity", "title": "Opportunity Rehberi", "module_id": "opportunity_engine", "summary": "Quick win seçimi ve trafik tahmini."},
    {"guide_id": "guide_crawl_gap", "title": "Crawl Gap Rehberi", "module_id": "crawl_gap_engine", "summary": "FAQ ve entity gap kapatma."},
    {"guide_id": "guide_rank_watcher", "title": "Rank Watcher Rehberi", "module_id": "rank_index_watcher", "summary": "İlk proje ve alert kurulumu."},
    {"guide_id": "guide_authority_mesh", "title": "Authority Mesh Rehberi", "module_id": "authority_mesh_engine", "summary": "Support site ağı kurulumu."},
    {"guide_id": "guide_wordpress", "title": "WordPress Bağlantı Rehberi", "module_id": "wordpress", "summary": "İlk WP oturumu ve Wizard adım 1."},
    {"guide_id": "guide_github_pages", "title": "GitHub Pages Rehberi", "module_id": "github_pages_worker", "summary": "Token ve ilk Pages deploy."},
    {"guide_id": "guide_google_sites", "title": "Google Sites Rehberi", "module_id": "google_sites_worker", "summary": "Playwright oturumu ve Sites publish."},
    {"guide_id": "guide_getting_started", "title": "HIVE'e Başlangıç", "module_id": "first_run_wizard", "summary": "First Run Wizard ile 8 adımlı onboarding."},
]

GLOSSARY: dict[str, str] = {
    "authority_score": "Support site ağının money site'e sağladığı güven sinyali. Yüksek = daha güçlü link equity dağılımı.",
    "fortress_score": "Bir keyword'ün SERP'te savunma gücü (0-100). Düşük fortress = position loss riski yüksek.",
    "opportunity_score": "Keyword büyüme potansiyeli; trafik, zorluk ve mevcut pozisyon birleşimi.",
    "publish_queue": "Yayına hazır içeriklerin beklediği Publisher Hub kuyruğu. Boş kuyruk = deploy fırsatı kaçırılıyor.",
    "rank_drop": "Rank Watcher'ın tespit ettiği pozisyon düşüşü. SERP Defense ile birlikte değerlendirilir.",
    "gap_score": "Crawl Gap analizinde sayfa/cluster eksiklik derecesi. Yüksek gap = acil içerik ihtiyacı.",
    "quick_win": "Düşük zorluk + yüksek trafik potansiyelli keyword fırsatı.",
    "mesh_plan": "Authority Mesh'te support site rol ve link dağılım planı.",
}
GLOSSARY.update(EXTRA_GLOSSARY)


def _generic_module(module_id: str) -> dict[str, Any]:
    label = module_id.replace("_", " ").title()
    return _entry(
        module_id, label,
        purpose=f"{label} modülü — HIVE SEO OS bileşeni.",
        what_it_does="Modül dokümantasyonu Academy'de genişletiliyor.",
        when_to_use="İlgili SEO görevi için Mission Control veya Mentor önerisine bakın.",
        when_not_to_use="Yanlış modül seçimi zaman kaybettirir — HIVE Mentor'a sorun.",
        inputs=["Modüle özel girdiler"],
        outputs=["Modüle özel çıktılar"],
        related=["mission_control_center", "hive_mentor"],
        example=f"{label} modülünü sidebar'dan açın ve dashboard'u inceleyin.",
        common_mistakes=["Modül amacını okumadan çalıştırmak"],
        pro_tips=["HIVE Academy'de workflow haritalarına göz atın"],
    )


def _progress_percent(state: dict[str, Any]) -> int:
    total = len(ENCYCLOPEDIA) + len(GUIDES) + len(WORKFLOWS)
    if total == 0:
        return 0
    viewed = len(set(state.get("viewed_modules") or []))
    guides = len(set(state.get("completed_guides") or []))
    workflows = len(set(state.get("completed_workflows") or []))
    pct = int(((viewed + guides + workflows) / total) * 100)
    return min(100, max(0, pct))


def health() -> dict[str, Any]:
    record_academy_opened()
    state = _load_state()
    return {
        "success": True,
        "module": "hive_academy",
        "modules_total": len(ENCYCLOPEDIA),
        "guides_total": len(GUIDES),
        "workflows_total": len(WORKFLOWS),
        "modules_viewed": len(set(state.get("viewed_modules") or [])),
        "guides_completed": len(set(state.get("completed_guides") or [])),
        "workflows_completed": len(set(state.get("completed_workflows") or [])),
        "progress_percent": _progress_percent(state),
    }


def list_modules() -> dict[str, Any]:
    items = [
        {
            "module_id": mid,
            "title": entry["title"],
            "purpose": entry["purpose"][:160],
            "guide_id": entry.get("guide_id", ""),
            "category": entry.get("category", "tools"),
            "icon": entry.get("icon", "📦"),
        }
        for mid, entry in ENCYCLOPEDIA.items()
    ]
    return {"success": True, "modules": items, "count": len(items)}


def get_module(module_id: str, *, record_view: bool = True) -> dict[str, Any]:
    if not module_id:
        return {"success": False, "error": "module_id gerekli"}
    entry = ENCYCLOPEDIA.get(module_id) or _generic_module(module_id)
    if record_view:
        st = _load_state()
        viewed = st.setdefault("viewed_modules", [])
        if module_id not in viewed:
            viewed.append(module_id)
            st.setdefault("history", []).insert(0, {"type": "module_viewed", "module_id": module_id, "at": _now()})
            _save_state(st)
    return {"success": True, "module": entry}


def list_workflows() -> dict[str, Any]:
    return {"success": True, "workflows": WORKFLOWS, "count": len(WORKFLOWS)}


def list_guides() -> dict[str, Any]:
    guides = []
    for g in GUIDES:
        detail = GUIDE_DETAILS.get(g["guide_id"], {})
        guides.append({**g, "estimated_time": detail.get("estimated_time", ""), "step_count": len(detail.get("steps") or [])})
    return {"success": True, "guides": guides, "glossary": GLOSSARY, "count": len(guides)}


def get_guide(guide_id: str) -> dict[str, Any]:
    if not guide_id:
        return {"success": False, "error": "guide_id gerekli"}
    detail = GUIDE_DETAILS.get(guide_id)
    if not detail:
        base = next((g for g in GUIDES if g["guide_id"] == guide_id), None)
        if not base:
            return {"success": False, "error": f"Rehber bulunamadı: {guide_id}"}
        return {"success": True, "guide": {**base, "steps": [], "checklist": [], "troubleshooting": []}}
    return {"success": True, "guide": detail}


def mark_guide_complete(guide_id: str) -> dict[str, Any]:
    if not guide_id:
        return {"success": False, "error": "guide_id gerekli"}
    st = _load_state()
    completed = st.setdefault("completed_guides", [])
    if guide_id not in completed:
        completed.append(guide_id)
        st.setdefault("history", []).insert(0, {"type": "guide_completed", "guide_id": guide_id, "at": _now()})
        _save_state(st)
        _record_brain("academy_completed", metadata={"learn_event": "academy_completed", "guide_id": guide_id})
    return {"success": True, "guide_id": guide_id, "progress_percent": _progress_percent(st)}


def record_academy_opened() -> None:
    st = _load_state()
    last = st.get("last_opened_at") or ""
    now_ts = datetime.now(timezone.utc)
    if last:
        try:
            prev = datetime.strptime(last, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
            if (now_ts - prev).total_seconds() < 60:
                return
        except ValueError:
            pass
    st["last_opened_at"] = _now()
    _save_state(st)
    _record_brain("academy_opened", metadata={"learn_event": "academy_opened"})


def export_academy(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    payload = {
        "exported_at": _now(),
        "report_type": report_type,
        "health": health(),
        "modules": list_modules()["modules"],
        "workflows": WORKFLOWS,
        "guides": GUIDES,
        "progress": state,
    }
    fname = f"hive_academy_{report_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    path = REPORTS_DIR / fname
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path), "filename": fname}
