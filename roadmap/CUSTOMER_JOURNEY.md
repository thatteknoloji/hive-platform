# Customer Journey — Operation Phoenix v2

**Status:** ACTIVE  
**Eski metrik:** Demo Success Rate (modül odaklı) — **deprecated**  
**Yeni metrik:** **Customer Journey Completion Rate (CJCR)** — hedef **100%**

---

## Amaç

Yeni bir kullanıcı aşağıdaki akışı **tek hata almadan** tamamlayabilmelidir:

```
Login
  ↓
Project
  ↓
Domain
  ↓
SEO
  ↓
Authority
  ↓
Publish
  ↓
Deploy
  ↓
Monitoring
```

Sprint yalnızca bu journey'de kullanılan modüllere odaklanır. Journey dışı modüller `roadmap/icebox.md` altında bekler.

---

## Demo Project

| Alan | Değer |
|------|-------|
| Ad | Phoenix Demo — Thiqos Turizm |
| Sektör | tourism |
| Domain | demo.thiqos.com |
| Senaryo | Yerel tur operatörü — Antalya çıkışlı kültür turları, çok dilli SEO + authority mesh |

**Seed:** `python3 scripts/seed-customer-journey-demo.py`  
**Manifest:** `roadmap/demo-project.json` (seed sonrası üretilir)

---

## Journey Adımları

| # | Adım | Route | Modüller |
|---|------|-------|----------|
| 1 | Login | `/login` | auth, permissions |
| 2 | Project | `/projects` | projects, active_project_context |
| 3 | Domain | `/domain-manager` | domain_manager |
| 4 | SEO | `/talon` | talon, entity_geo_graph, seo_quality_gate, campaign_engine |
| 5 | Authority | `/authority-factory` | authority_factory, citation_engine, authority_mesh_engine |
| 6 | Publish | `/publisher-hub` | publisher_hub |
| 7 | Deploy | `/astro-factory` | astro_factory, astro_auto_publisher |
| 8 | Monitoring | `/mission-control` | mission_control_center, rank_index_watcher, serp_defense_engine |

Tam tanım: `roadmap/customer-journey.json`

---

## Başarı Metriği

**Customer Journey Completion Rate (CJCR)**

```
CJCR = (tamamlanan adım sayısı / 8) × 100
```

Bir adım tamamlanmış sayılır ancak:

1. Adımdaki **tüm modüller** Phoenix checklist'ini %100 geçer
2. Adımın **data_checks** koşulları sağlanır (demo proje, aktif proje, domain vb.)

**Audit:** `python3 scripts/phoenix-customer-journey-audit.py`  
**Rapor:** `roadmap/phoenix-customer-journey-audit.json`

---

## Sprint Kuralları

1. Yeni modül ekleme yok — journey modüllerini production'a taşı
2. Journey dışı modül → icebox
3. Her modül: Academy doc (published) + UI polish + hata yönetimi + demo senaryosu
4. QA: seed çalıştır → journey sırasıyla manuel veya otomatik doğrula

---

## Eski Phoenix Phase 2

`roadmap/phoenix-demo-flow.json` ve `scripts/phoenix-demo-audit.py` referans olarak kalır; aktif sprint metriği **CJCR**'dır.
