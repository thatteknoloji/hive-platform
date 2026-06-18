# HIVE V3 MODULE REGISTRY

## Amaç

Mevcut 1000+ modül silinmez. Kullanıcıya doğrudan gösterilmez.

Modüller HIVE motor odasında yaşar.

Normal kullanıcı:

- Builder
- Content
- Growth
- Publishing
- Integrations

görür.

Architect Mode:

- tüm modülleri
- sağlık durumlarını
- provider durumlarını
- logları
- test sonuçlarını

görür.

---

## Ana Kategoriler

### 1. Site & Deploy

- astro_factory
- cloudflare_pages_worker
- github_pages_worker
- site_factory
- static_exporter
- domain_engine
- ssl_engine
- nginx_deploy_engine
- hive_agent

UI karşılığı:

Builder / Deploy Engine

---

### 2. CMS

- page_engine
- block_engine
- theme_engine
- menu_engine
- media_engine
- form_engine
- gallery_engine
- faq_engine
- blog_engine

UI karşılığı:

Builder / HIVE CMS

---

### 3. SEO

- seo_quality_gate
- technical_seo_engine
- sitemap_engine
- robots_engine
- schema_engine
- internal_link_engine
- meta_engine
- slug_engine

UI karşılığı:

Growth / SEO Health

---

### 4. GEO

- entity_geo_graph
- authority_mesh_engine
- citation_engine
- geo_cluster_engine
- support_network
- google_sites_worker
- blogger_worker
- medium_worker
- github_pages_worker
- cloudflare_pages_worker

UI karşılığı:

Growth / GEO Network

---

### 5. AEO

- faq_generator
- answer_engine
- snippet_engine
- semantic_question_engine
- ai_overview_optimizer

UI karşılığı:

Growth / AEO

---

### 6. Publishing

- publisher_hub
- google_sites_worker
- blogger_worker
- medium_worker
- wordpress_publisher
- linkedin_publisher
- pinterest_publisher
- youtube_publisher
- x_publisher
- instagram_publisher
- tiktok_publisher

UI karşılığı:

Publishing Network

---

### 7. Social / MINE

- mine_engine
- x_extension_engine
- instagram_extension_engine
- pinterest_engine
- linkedin_engine
- youtube_engine
- tiktok_engine

UI karşılığı:

Publishing / Social

---

### 8. Integrations

- whatsapp_qr_engine
- payment_adapter
- accounting_adapter
- crm_adapter
- email_adapter
- sms_adapter
- webhook_engine

UI karşılığı:

Integrations

---

### 9. Marketplace / Data Sources

- trendyol_adapter
- hepsiburada_adapter
- n11_adapter
- amazon_adapter
- etsy_adapter
- shopify_adapter
- woocommerce_adapter
- opencart_adapter
- xml_importer
- csv_importer

UI karşılığı:

Marketplace / Data Sources

---

### 10. Monitoring

- rank_index_watcher
- health_engine
- uptime_monitor
- log_viewer
- performance_engine
- coverage_reporter

UI karşılığı:

Growth / Monitoring

---

### 11. AI

- ai_command_center
- prompt_router
- provider_router
- openai_provider
- claude_provider
- gemini_provider
- openrouter_provider
- ollama_provider

UI karşılığı:

AI Center

---

### 12. Experimental

Yeni ve test aşamasındaki modüller burada durur.

UI karşılığı:

Architect Mode / Experimental

---

### 13. Deprecated

Eski, kullanılmayan veya değiştirilecek modüller burada durur.

UI karşılığı:

Architect Mode / Deprecated

---

## Modül Metadata Formatı

Her modül şu bilgileri taşımalı:

```json
{
  "module_id": "google_sites_worker",
  "name": "Google Sites Worker",
  "category": "geo",
  "ui_area": "Publishing / GEO Network",
  "status": "active",
  "project_scoped": true,
  "requires_provider": true,
  "provider_type": "google_account",
  "health_endpoint": "/api/google-sites/health",
  "actions": [
    "create_task",
    "process_task",
    "publish",
    "health"
  ],
  "visibility": "architect"
}
```

---

## Visibility Kuralları

**public**

Normal kullanıcı görür.

**project**

Sadece ilgili proje içinde görünür.

**architect**

Sadece Architect Mode içinde görünür.

**hidden**

Sadece sistem kullanır.

---

## HIVE V3 Ana Prensip

Modüller ürün değildir.

Modüller ürünün motorudur.

Kullanıcı modül değil, sonuç görür.

Örnek:

Kullanıcı:

GEO Network aktif

Sistem:

- google_sites_worker
- blogger_worker
- medium_worker
- entity_graph
- citation_engine
- index_engine

çalıştırır.
