# HIVE Academy Changelog

## 3.4.0 - 2026-06-27 — Operation Phoenix Step 4 (SEO)

- Customer Journey **SEO** step production hardening: 4 modül (Talon, EntityGeoGraph, QualityGate, CampaignEngine).
- **TalonHub**: full rewrite — HiveShell, HiveAlert, HiveToast, HiveSkeleton, HiveEmptyState, HiveTooltip, loading/error/empty states, provider chips.
- **EntityGeoGraph**: full rewrite — HiveShell, tabs (Build/Summary/GEO Expand/Clusters/Links/Missing/Export), all states covered.
- **SEOQualityGate**: full rewrite — HiveShell, score cards (SEO/GEO/AEO/Overall), readiness report, fix suggestions, export.
- **CampaignEngine**: already complete — added screenshot, academy doc, API docs, changelog.
- Published Academy: talon-nedir, entity-geo-graph-nedir, campaign-engine-nedir (SEO/GEO/AEO kategorisi).
- Modül ansiklopedisi: campaign_engine, entity_geo_graph, seo_quality_gate → published.
- Screenshots: talon-hub-dashboard, entity-geo-graph-dashboard, quality-gate-dashboard, campaign-engine-dashboard.
- CJCR: 37.5% (3/8) — SEO modülleri 93–100%'e yükseldi, demo_scenario hariç tüm kontroller yeşil.

## 3.3.0 - 2026-06-26 — Operation Phoenix Step 3 (Domain)

- Customer Journey **domain_manager** production hardening: DomainManager UI, bind/status API, ActiveProjectContext sync.
- Domain Manager: skeleton, empty state, HiveApiErrorCard, toast, validation, Phoenix demo banner, DNS/SSL/Health panel.
- Published Academy: ilk-domain-nasil-eklenir, domain_manager modül ansiklopedisi, customer-journey-domain demo-flow.
- Screenshots: ilk-domain-nasil-eklenir, domain-manager, customer-journey-domain.
- Backend: `phoenix_journey.py` domain data checks; CJCR hedef 37.5% (3/8).

## 3.2.0 - 2026-06-26 — Operation Phoenix Step 1–2

- Customer Journey: **auth**, **permissions**, **projects**, **active_project_context** production hardening.
- Login: health check, session expired mesajı, Academy linki, geliştirilmiş hata metinleri.
- Projects: skeleton, empty state, toast, aktif proje seçimi, Phoenix demo banner, HiveApiErrorCard.
- Mission Control: CJCR kartı ve journey adım durumları (`GET /api/phoenix/customer-journey`).
- Published Academy: ilk-giris, ilk-firma-nasil-eklenir, active-project-context güncellendi.
- Screenshots: login, users-permissions, projects, active-project-context.

## 3.1.0 - 2026-06-26 — Operation Phoenix Phase 2

- Demo flow odaklı modül önceliklendirme (Groups A–E).
- Published: Users & Permissions, Mission Control dashboard rehberleri.
- Users & Roles UI: HiveShell, skeleton, empty state, toast, tooltips.
- `phoenix-demo-audit.py` — Demo Success Rate metriği.

## 3.0.0 - 2026-06-26

- Interactive Learning Platform (V3) — Operation Phoenix Phase 1 hedefleri.
- Missions, checklist, knowledge graph, Academy AI, command palette.
- Documentation Health, quality score, gamification (XP/level).
- Changelog UI, sidebar live search, mobile drawer, feedback toast.
- Workflow export (SVG/PNG/Print), screenshot gallery önce/sonra.

## 2.0.0 - 2026-06-26

- Enterprise Learning Platform (V2) — Dashboard, ilerleme, rozetler, sertifika placeholder.
- Yeni API: progress, badges, favorites, notes, quiz, dashboard, recommendations, semantic search.
- Öğrenme rotası, doc meta kartları, quiz, favoriler, notlar, gelişmiş geri bildirim.
- Global AI Search (⌘K), Mermaid genişletildi, screenshot galeri + zoom.
- `generate-academy-index.py` living docs index üretici.
- Modül ansiklopedisi AI update slot'ları.

## 1.0.0 - 2026-06-26

- HIVE Academy V1 klasör yapısı oluşturuldu.
- İlk 15 başlangıç dokümanı yazıldı.
- Academy index üretildi (`academy-index.json`).
- Modül ansiklopedisi taslakları üretildi (116 modül, `liste.py`).
- Backend API: `/api/academy/*` endpointleri eklendi.
- Feedback altyapısı hazırlandı (`academy_feedback.json`).
- Frontend: `/academy` docs arayüzü (`HiveAcademy.jsx`).
- Mermaid ve markdown render altyapısı eklendi.
- AI otomatik güncelleme için `<!-- AI_UPDATE_SLOT -->` ve `<!-- TODO -->` işaretleri bırakıldı.
