# HIVE V3 PROJECT ENGINE

> Referans: [HIVE_V3_MASTER_ARCHITECTURE.md](./HIVE_V3_MASTER_ARCHITECTURE.md) · [HIVE_V3_MODULE_REGISTRY.md](./HIVE_V3_MODULE_REGISTRY.md)

---

## 1. Project Engine Amacı

Project Engine, HIVE V3'ün merkezi koordinasyon katmanıdır. Tüm dijital varlık üretimi, yayın, büyüme ve izleme işlemleri **proje** kapsamında yürütülür.

**Ne yapar:**

- İşletmeyi tek bir `Project` entity'si altında toplar
- Site, domain, deploy ve growth ayarlarını bir arada tutar
- Builder Wizard çıktısını somut site + yayın planına dönüştürür
- Arka plandaki modülleri (`astro_factory`, `google_sites_worker`, vb.) proje bağlamında orkestre eder
- Kullanıcıya modül değil, **sonuç** gösterir (Master Architecture prensibi)

**Ne yapmaz:**

- Modül mantığını kendi içinde tekrarlamaz — modülleri çağırır
- ERP, CRM, muhasebe veya kargo operasyonu yürütmez
- Ana HIVE beynini müşteri sunucusuna kurmaz (Customer / Enterprise Agent modellerinde yalnızca agent gider)

**Konum:** Ana katmanlar içinde `Projects` + `Builder` ile doğrudan ilişkilidir. Content, Growth, Publishing ve Integrations ekranları hep aktif proje üzerinden çalışır.

---

## 2. Project Entity Alanları

Her proje aşağıdaki alanları taşır.

| Alan | Tip | Açıklama |
|------|-----|----------|
| `project_id` | string | Benzersiz kimlik (`prj-…`) |
| `name` | string | Görünen proje adı (ör. BalKutusu) |
| `slug` | string | URL-safe kısa ad |
| `sector` | string | Sektör paketi kodu (ör. `ecommerce`, `dental_clinic`) |
| `business_brief` | text | İşletme tanımı — Builder adım 2 çıktısı |
| `status` | enum | `draft` \| `building` \| `active` \| `paused` \| `error` |
| `deploy_mode` | enum | `hive_cloud` \| `customer_agent` \| `enterprise_agent` |
| `site_engine` | string | Varsayılan: `astro` — opsiyonel adaptörler: `wordpress`, `woocommerce`, `opencart`, `nextjs` |
| `publish_model` | string | Yayın stratejisi özeti (ör. `main_site + geo_network`) |
| `design_direction` | object | Tasarım karakteri — renk, ton, layout tercihi |
| `primary_domain_id` | string | FK → Domain entity |
| `site_id` | string | FK → Site entity |
| `seo_score` | number | 0–100, son ölçüm |
| `geo_score` | number | 0–100, son ölçüm |
| `content_count` | number | Sayfa + blog + SSS toplamı |
| `integration_ids` | string[] | Bağlı entegrasyon referansları |
| `growth_profile` | object | SEO / GEO / AEO hedefleri ve eşikler |
| `owner_user_id` | string | Oluşturan kullanıcı |
| `team_ids` | string[] | Proje erişimi olan kullanıcılar |
| `created_at` | datetime | Oluşturulma |
| `updated_at` | datetime | Son güncelleme |
| `built_at` | datetime | Son başarılı build |
| `published_at` | datetime | Son yayın |
| `error_message` | string | `status=error` iken doldurulur |
| `metadata` | object | Sektör paketi versiyonu, wizard snapshot, vb. |

**Örnek (özet):**

```json
{
  "project_id": "prj-balkutusu-001",
  "name": "BalKutusu",
  "slug": "balkutusu",
  "sector": "ecommerce",
  "status": "active",
  "deploy_mode": "hive_cloud",
  "site_engine": "astro",
  "seo_score": 78,
  "geo_score": 65,
  "content_count": 42,
  "primary_domain_id": "dom-balkutusu-com",
  "site_id": "site-balkutusu-001"
}
```

---

## 3. Site Entity Alanları

Bir projenin tek ana sitesi (veya çoklu site senaryosunda alt site) Site entity ile modellenir.

| Alan | Tip | Açıklama |
|------|-----|----------|
| `site_id` | string | Benzersiz kimlik |
| `project_id` | string | FK → Project |
| `title` | string | Site başlığı |
| `engine` | string | `astro` (varsayılan) veya adaptör |
| `cms_enabled` | boolean | HIVE CMS aktif mi |
| `theme_id` | string | Sektör + design direction'dan türetilen tema |
| `page_count` | number | Yayınlanmış sayfa sayısı |
| `block_schema_version` | string | CMS blok şeması versiyonu |
| `live_url` | string | Canlı site URL (deploy sonrası) |
| `preview_url` | string | Staging / preview URL |
| `build_artifact_path` | string | Son build çıktısı (internal) |
| `last_build_status` | enum | `pending` \| `success` \| `failed` |
| `last_build_at` | datetime | Son build zamanı |
| `sitemap_url` | string | Üretilen sitemap |
| `robots_status` | string | robots.txt durumu |
| `schema_enabled` | boolean | Yapılandırılmış veri aktif mi |

**CMS hiyerarşisi** (Master Architecture ile uyumlu):

```
Project → Site → Page → Section → Block
```

Site entity, `page_engine`, `block_engine`, `theme_engine` modüllerinin çalışma kapsamını tanımlar.

---

## 4. Domain Entity Alanları

| Alan | Tip | Açıklama |
|------|-----|----------|
| `domain_id` | string | Benzersiz kimlik |
| `project_id` | string | FK → Project |
| `hostname` | string | ör. `www.balkutusu.com` |
| `apex` | string | Apex domain (ör. `balkutusu.com`) |
| `is_primary` | boolean | Birincil domain mi |
| `ssl_status` | enum | `pending` \| `active` \| `expired` \| `error` |
| `ssl_expires_at` | datetime | Sertifika bitiş |
| `dns_status` | enum | `unverified` \| `verified` \| `misconfigured` |
| `nameservers` | string[] | NS kayıtları |
| `registrar` | string | Opsiyonel kayıt firması |
| `cloudflare_zone_id` | string | Cloudflare bağlıysa |
| `verification_token` | string | DNS doğrulama |
| `verified_at` | datetime | Doğrulama zamanı |

Domain yönetimi `domain_engine`, `ssl_engine`, `nginx_deploy_engine` modülleriyle (Architect / Site & Deploy) entegre çalışır; kullanıcı yalnızca Builder ve Project Detail üzerinden domain durumunu görür.

---

## 5. Deploy Mode Yapısı

Master Architecture Deploy Model ile birebir hizalıdır.

### `hive_cloud`

| Özellik | Değer |
|---------|--------|
| Site nerede çalışır | HIVE sunucusu / HIVE Cloud |
| Müşteri sunucusu | Gerekmez |
| Agent | Yok |
| Tipik modüller | `astro_factory`, `cloudflare_pages_worker`, `nginx_deploy_engine` |
| Kullanım | Küçük-orta işletme, hızlı başlangıç |

Site build çıktısı HIVE altyapısına deploy edilir. SSL ve routing HIVE tarafından yönetilir.

### `customer_agent`

| Özellik | Değer |
|---------|--------|
| Site nerede çalışır | Müşteri sunucusu |
| Müşteri sunucusu | Yalnızca **HIVE Agent** kurulur |
| Ana beyin | HIVE merkezinde kalır — müşteri sunucusuna kurulmaz |
| Tipik modüller | `hive_agent`, `static_exporter`, `nginx_deploy_engine` |
| Kullanım | Müşteri kendi VPS/hosting'inde barındırmak istediğinde |

Agent: build artifact alır, yerel web root'a yazar, health raporlar.

### `enterprise_agent`

| Özellik | Değer |
|---------|--------|
| Site nerede çalışır | Müşteri altyapısı (çoklu node / CDN) |
| Agent | Gelişmiş agent — çoklu site, özel pipeline, audit log |
| Tipik modüller | `hive_agent` (enterprise), `cloudflare_pages_worker`, özel webhook'lar |
| Kullanım | Büyük marka, ajans, çoklu proje tek tenant |

Deploy mode, Project oluşturulurken Builder Wizard adımında seçilir ve sonradan `PATCH /api/v3/projects/{id}` ile değiştirilebilir (aktif yayın varken dikkatli geçiş kuralları uygulanır).

---

## 6. Project Status

| Status | Anlam | Kullanıcı görünümü | Sistem davranışı |
|--------|--------|-------------------|------------------|
| `draft` | Wizard tamamlandı veya yarım kaldı; henüz build yok | "Taslak" — düzenlenebilir | Build/publish çağrılmaz |
| `building` | Build veya ilk deploy devam ediyor | "Oluşturuluyor…" | `astro_factory` vb. çalışır; UI poll |
| `active` | Site yayında, growth modülleri çalışabilir | "Aktif" | Tam erişim: Content, Growth, Publishing |
| `paused` | Kullanıcı veya admin duraklattı | "Duraklatıldı" | Yeni publish durur; mevcut site ayakta kalabilir |
| `error` | Build, deploy veya kritik modül hatası | "Hata" + `error_message` | Architect Mode'da detay log; retry önerilir |

**Geçişler (özet):**

```
draft → building → active
building → error
active → paused → active
active → building (rebuild)
* → error (kritik hata)
```

---

## 7. API Endpoint Tasarımı

Tüm endpoint'ler `X-API-Key` veya JWT ile korunur. Yanıtlar `{ "success": true, ... }` veya `{ "success": false, "error": "..." }` formatındadır.

### `GET /api/v3/projects`

Proje listesi. Filtre: `status`, `sector`, `deploy_mode`. Sayfalama: `limit`, `offset`.

**Yanıt:** `projects[]` — özet alanlar (id, name, slug, status, seo_score, geo_score, primary_domain).

### `POST /api/v3/projects`

Yeni proje oluşturur (Wizard son adımı veya API ile).

**Body (özet):** `name`, `sector`, `business_brief`, `domain` (hostname), `design_direction`, `deploy_mode`, `site_engine` (opsiyonel).

**Yanıt:** `project` tam entity + oluşturulan `site_id`, `domain_id`.

### `GET /api/v3/projects/{project_id}`

Tek proje detayı: Project + ilişkili Site + Domain özetleri + son health snapshot.

### `PATCH /api/v3/projects/{project_id}`

Kısmi güncelleme: `name`, `business_brief`, `design_direction`, `deploy_mode`, `status` (ör. `paused`), `growth_profile`.

`building` veya `error` durumunda bazı alanlar kilitli olabilir.

### `DELETE /api/v3/projects/{project_id}`

Soft-delete veya arşiv (varsayılan: `metadata.archived=true`). Canlı `active` projede onay gerekir.

### `POST /api/v3/projects/{project_id}/build`

Site üretim pipeline'ını tetikler.

1. `status` → `building`
2. Sektör paketinden sayfa/blok şablonları yüklenir
3. `astro_factory` (veya seçilen engine) build çalıştırır
4. Başarı: `built_at`, `last_build_status=success`, `status` → `active` (ilk build) veya `active` kalır
5. Hata: `status` → `error`, `error_message` doldurulur

**Body (opsiyonel):** `force`, `skip_quality_gate`.

### `POST /api/v3/projects/{project_id}/publish`

Build artifact'ı deploy eder ve growth ağını (isteğe bağlı) başlatır.

1. Deploy mode'a göre: `hive_cloud` → cloud deploy; `customer_agent` / `enterprise_agent` → agent push
2. `live_url` güncellenir
3. `published_at` set edilir
4. İsteğe bağlı: GEO network task'ları (`google_sites_worker`, vb.) kuyruğa alınır

**Body (opsiyonel):** `targets[]` (hangi publisher'lar), `run_geo_bootstrap`.

---

## 8. Builder Wizard Akışı

Master Architecture Builder akışı ile aynı sıra; her adım Project Engine state'ine yazılır.

| Adım | Wizard alanı | Project / ilişkili entity |
|------|----------------|---------------------------|
| 1 | **sector** | `Project.sector` + sektör paketi metadata |
| 2 | **business brief** | `Project.business_brief` |
| 3 | **domain** | `Domain.hostname`, DNS doğrulama başlat |
| 4 | **design direction** | `Project.design_direction`, `Site.theme_id` önerisi |
| 5 | **deploy mode** | `Project.deploy_mode` |
| 6 | **create** | `POST /api/v3/projects` → opsiyonel otomatik `build` |

**Sektör paketi etkisi:** sayfa yapısı, blok seti, schema, SEO/GEO stratejisi, CTA dili — `metadata.sector_package_version` ile sabitlenir.

Wizard yarıda bırakılırsa proje `draft` olarak kaydedilir; `Projects Dashboard` üzerinden devam edilebilir.

---

## 9. UI Ekranları

### Projects Dashboard

- Tüm projeler kart/liste görünümü
- Filtre: status, sektör, deploy mode
- Özet metrikler: SEO skoru, GEO skoru, içerik sayısı, son yayın
- Aksiyon: Yeni proje, proje detayına git

**Sol menü:** Projects (Master Architecture)

### New Project Wizard

- 6 adımlı sihirbaz (Bölüm 8)
- Adım validasyonu; geri/ileri
- Son adımda "Oluştur" → API `POST /api/v3/projects`
- Opsiyonel: "Oluştur ve derle" → ardından `build`

**Sol menü:** Builder

### Project Detail

- Proje adı, sektör, status badge
- Domain + canlı URL linki
- Site engine, deploy mode
- Kısayollar: Content, Growth, Publishing, Integrations (proje scoped)
- Aksiyonlar: Düzenle, Build, Publish, Duraklat

### Project Health

- SEO / GEO skor trendi
- Son build / publish zamanı
- Domain SSL + DNS durumu
- Bağlı modül health özeti (kullanıcı dostu etiketler — modül adı değil: "Yayın ağı", "İndeks durumu")
- Architect Mode linki (sadece yetkili roller): ham modül health ve loglar

**Sol menü:** Growth altında veya Project Detail sekmesi

---

## 10. Mevcut Modüllerle İlişki

Modüller ürün değil motordur (Module Registry prensibi). Project Engine, aşağıdaki modülleri **proje bağlamında** orkestre eder; kullanıcı UI'da yalnızca sonuç görür.

| Modül | Registry kategorisi | Project Engine rolü | Tetikleyici |
|-------|-------------------|---------------------|-------------|
| `astro_factory` | Site & Deploy | Varsayılan site build — Astro + HIVE CMS çıktısı | `POST .../build` |
| `cloudflare_pages_worker` | Site & Deploy / GEO | `hive_cloud` veya CDN deploy; edge yayın | `POST .../publish`, deploy_mode |
| `google_sites_worker` | GEO / Publishing | GEO support hub — authority URL üretimi | `publish` + Growth GEO planı |
| `quality_gate` | SEO (`seo_quality_gate`) | Build öncesi/sonrası içerik kalite kontrolü | `build` pipeline adımı |
| `entity_geo_graph` | GEO | Entity ve coğrafi cluster ilişkileri | `active` proje + Growth |
| `rank_index_watcher` | Monitoring | Sıralama ve indeks izleme | `active` proje, periyodik |

**Örnek akış — BalKutusu:**

1. Wizard → `POST /api/v3/projects` → `draft`
2. `POST .../build` → `astro_factory` + `quality_gate` → `building` → `active`
3. `POST .../publish` → `cloudflare_pages_worker` → `live_url` set
4. Growth plan açık → `entity_geo_graph` + `google_sites_worker` task kuyruğu
5. `rank_index_watcher` → Project Health ekranında "İndeks / sıralama" özeti

**Visibility:** Bu modüllerin çoğu Module Registry'de `architect` veya `project` visibility ile kayıtlıdır; normal kullanıcı Project Health'te agregasyon görür, modül listesini görmez.

---

## Özet

Project Engine, HIVE V3'te **her şeyin proje bazlı** olduğu Master Architecture ilkesinin teknik karşılığıdır. Builder Wizard girdisini Project / Site / Domain entity'lerine dönüştürür; build ve publish API'leri ile Site & Deploy modüllerini çalıştırır; Growth ve Publishing katmanlarına proje kapsamı sağlar. Deploy mode, ana beynin müşteri sunucusuna taşınmaması kuralını korur.
