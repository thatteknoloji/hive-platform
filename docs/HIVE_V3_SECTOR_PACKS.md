# HIVE V3 SECTOR PACKS

> Referans: [HIVE_V3_MASTER_ARCHITECTURE.md](./HIVE_V3_MASTER_ARCHITECTURE.md) · [HIVE_V3_MODULE_REGISTRY.md](./HIVE_V3_MODULE_REGISTRY.md) · [HIVE_V3_PROJECT_ENGINE.md](./HIVE_V3_PROJECT_ENGINE.md)

---

## 1. Sector Pack Amacı

Sector Pack (sektör paketi), HIVE V3'te **yeni proje oluşturulurken** sitenin iskeletini, içerik şablonlarını ve büyüme stratejisini tek seferde tanımlayan yapılandırılmış şablondur.

**Ne üretir:**

- Varsayılan sayfa yapısı ve blok seti
- Schema.org tipleri ve yerel SEO/GEO/AEO stratejisi
- CTA dili ve tasarım yönü önerileri
- Growth ve Publishing için başlangıç planı

**Ne yapmaz (HIVE prensibi):**

- Muhasebe, ödeme tahsilatı, kargo operasyonu, stok ERP veya POS işlemlerini yürütmez
- Pazaryeri sipariş yönetimi yapmaz
- Bu alanlar yalnızca **integration requirement** olarak tanımlanır; HIVE ilgili adaptörlere bağlanır

Kullanıcı sektör seçer → sistem paketi yükler → Builder ve Project Engine somut site + proje üretir. Kullanıcı modül veya paket JSON'u görmez; sonuç görür.

---

## 2. Sector Pack JSON Yapısı

Her paket versiyonlu bir JSON dosyasıdır (ör. `packs/v1/hotel_pack.json`). Project oluşturulurken `metadata.sector_package_version` ile sabitlenir.

```json
{
  "pack_id": "hotel_pack",
  "version": "1.0.0",
  "group": "konaklama",
  "display_name": "Otel / Pansiyon / Villa / Bungalov",
  "description": "Konaklama tesisleri için tam site + yerel GEO şablonu",
  "site_engine_default": "astro",
  "cms_block_schema_version": "2026.06",

  "default_pages": [
    { "slug": "", "title": "Ana Sayfa", "template": "home", "sections": ["hero", "amenities", "gallery", "faq", "cta"] },
    { "slug": "odalar", "title": "Odalar", "template": "listing", "sections": ["hero", "product_grid", "cta"] },
    { "slug": "iletisim", "title": "İletişim", "template": "contact", "sections": ["hero", "map", "form"] }
  ],

  "default_blocks": ["Hero", "Gallery", "FAQ", "CTA", "Map", "Form", "Testimonials", "Pricing"],

  "schema_types": ["Hotel", "LodgingBusiness", "LocalBusiness", "FAQPage", "BreadcrumbList"],

  "seo_keyword_strategy": {
    "primary_patterns": ["{city} otel", "{brand} konaklama", "{city} pansiyon"],
    "secondary_patterns": ["{city} tatil", "uygun fiyatlı otel {city}"],
    "intent_mix": { "transactional": 0.4, "local": 0.5, "informational": 0.1 },
    "internal_link_rules": ["odalar → ana", "sss → odalar", "blog → geo landing"]
  },

  "geo_strategy": {
    "entity_type": "lodging",
    "cluster_pages": ["{city} konaklama rehberi", "{district} otelleri"],
    "support_hubs": ["google_sites", "blogger"],
    "citation_targets": ["Google Business Profile", "local directories"],
    "nap_consistency": true
  },

  "aeo_strategy": {
    "faq_min_count": 6,
    "answer_box_blocks": true,
    "paa_expansion": true
  },

  "cta_language": {
    "primary": "Rezervasyon yapın",
    "secondary": "Müsaitlik sorun",
    "tone": "güven veren, samimi, net"
  },

  "design_direction": {
    "layout": "spacious imagery, card grid",
    "typography": "serif headline + sans body",
    "color_mood": "warm neutral, accent gold or teal",
    "imagery": "oda, manzara, tesis"
  },

  "required_integrations": [],
  "optional_integrations": [
    { "type": "payment", "providers": ["iyzico", "stripe"], "purpose": "online ön ödeme / depozito" },
    { "type": "crm", "providers": ["hubspot"], "purpose": "rezervasyon lead" },
    { "type": "whatsapp", "providers": ["whatsapp_qr"], "purpose": "hızlı iletişim" }
  ],

  "publishing_network_defaults": {
    "enabled_channels": ["google_sites", "blogger", "pinterest"],
    "content_types": ["geo_landing", "seasonal_guide", "faq_hub"]
  },

  "growth_modules": [
    "seo_quality_gate",
    "entity_geo_graph",
    "schema_engine",
    "rank_index_watcher"
  ],

  "marketplace_adapter": null,

  "visibility": "public"
}
```

**Zorunlu üst alanlar:** `pack_id`, `version`, `group`, `display_name`, `default_pages`, `default_blocks`, `schema_types`, `seo_keyword_strategy`, `geo_strategy`, `cta_language`, `design_direction`.

**Integration alanı kuralı:** `required_integrations` boş olabilir; ödeme/muhasebe/kargo asla `required` yapılmaz — yalnızca iş modeli gerçekten zorunlu kılıyorsa `optional_integrations` içinde `purpose` ile belirtilir.

---

## 3. İlk Sektör Grupları

Master Architecture'daki sektör listesi gruplara map edilir. Her grup altında bir veya daha fazla `pack_id` bulunur.

### Konaklama

| pack_id | Görünen ad |
|---------|------------|
| `hotel_pack` | Otel / Pansiyon / Villa / Bungalov |

### E-Ticaret

| pack_id | Görünen ad |
|---------|------------|
| `ecommerce_pack` | E-Ticaret (genel) |
| `fashion_pack` | Giyim / Ayakkabı / İç Giyim |
| `cosmetics_pack` | Kozmetik |
| `furniture_pack` | Mobilya |

### Emlak

| pack_id | Görünen ad |
|---------|------------|
| `real_estate_pack` | Emlak |

### Sağlık

| pack_id | Görünen ad |
|---------|------------|
| `clinic_pack` | Klinik |
| `dental_clinic_pack` | Diş Kliniği |
| `beauty_center_pack` | Güzellik Merkezi |

### Veteriner / Pet

| pack_id | Görünen ad |
|---------|------------|
| `veterinary_pack` | Veteriner |
| `petshop_pack` | Petshop |

### Moda / Perakende

| pack_id | Görünen ad |
|---------|------------|
| `bridal_pack` | Gelinlik / Damatlık / Abiye |
| `fashion_pack` | (E-Ticaret ile paylaşımlı) |

### Hizmet

| pack_id | Görünen ad |
|---------|------------|
| `rent_a_car_pack` | Rent A Car |
| `auto_service_pack` | Oto Servis |
| `barber_pack` | Kuaför / Barber |
| `lawyer_pack` | Avukat |
| `accountant_pack` | Mali Müşavir |
| `education_pack` | Eğitim |
| `corporate_pack` | Kurumsal |

### Yeme İçme

| pack_id | Görünen ad |
|---------|------------|
| `restaurant_pack` | Restoran / Kafe |
| `nightlife_pack` | Gece Hayatı |

### Platform / İlan

| pack_id | Görünen ad |
|---------|------------|
| `listing_pack` | İlan Sitesi |
| `dating_pack` | Arkadaşlık Sitesi |

### Medya / Blog

| pack_id | Görünen ad |
|---------|------------|
| `media_blog_pack` | Haber / Blog / Rehber |

### Özel

| pack_id | Görünen ad |
|---------|------------|
| `custom_pack` | Özel — minimal şablon, kullanıcı/Architect genişletir |

---

## 4. Sektör Grubu Özet Matrisi

Her grup için paketlerin ortak DNA'sı (detaylı örnekler Bölüm 5'te).

| Grup | default pages (tipik) | default blocks | schema types | SEO odak | GEO odak | CTA tonu | design direction |
|------|----------------------|----------------|--------------|----------|----------|----------|------------------|
| Konaklama | Ana, Odalar, Olanaklar, Galeri, İletişim | Hero, Gallery, Pricing, FAQ, Map, Form | Hotel, LodgingBusiness | yerel + marka | şehir/bölge cluster | rezervasyon, müsaitlik | sıcak, görsel ağırlıklı |
| E-Ticaret | Ana, Kategori, Ürün şablonu, SSS, İletişim | ProductGrid, CategoryGrid, FAQ, CTA | Product, Offer, Organization | ürün + kategori long-tail | marka + kategori GEO sayfaları | satın al, sepete ekle | temiz grid, ürün odaklı |
| Emlak | Ana, İlan listesi, İlan detay, Bölgeler, İletişim | ProductGrid, Map, Form, FAQ | RealEstateListing, Place | bölge + tip + fiyat | mahalle/ilçe landing | ilan incele, randevu | harita + kart, güven |
| Sağlık | Ana, Hizmetler, Doktorlar, SSS, Randevu | FAQ, Testimonials, Form, CTA | MedicalBusiness, Physician | hizmet + şehir | klinik entity graph | randevu al, bilgi al | sakin, profesyonel |
| Veteriner / Pet | Ana, Hizmetler, Ürünler, SSS | ProductGrid, FAQ, Form | VeterinaryCare, PetStore | yerel + hizmet | pet + bölge | randevu, sipariş ver | dostane, canlı renk |
| Moda / Perakende | Ana, Koleksiyon, Mağaza, İletişim | Gallery, ProductGrid, CTA | Store, Product | trend + marka | lookbook GEO | keşfet, mağazaya git | editorial, görsel |
| Hizmet | Ana, Hizmetler, Hakkımızda, İletişim | FAQ, CTA, Form, Pricing | LocalBusiness, Service | hizmet + lokasyon | hizmet alanı cluster | teklif al, ara | kurumsal veya dinamik |
| Yeme İçme | Ana, Menü, Rezervasyon, Galeri | Gallery, Map, Form, FAQ | Restaurant, FoodEstablishment | menü + lokasyon | şehir yeme-içme | rezervasyon, yol tarifi | iştah açıcı görseller |
| Platform / İlan | Ana, Kategori, İlan detay, Kayıt | CategoryGrid, Form, BlogList | WebSite, ItemList | kategori + long-tail | çok sayfa GEO mesh | ilan ver, ara | liste + filtre UI |
| Medya / Blog | Ana, Kategori, Makale, Hakkımızda | BlogList, FAQ, CTA | Article, NewsArticle | topical authority | entity + citation | abone ol, oku | okunabilir, tipografi |
| Özel | Ana, Hakkımızda, İletişim | Hero, CTA, Form | Organization | kullanıcı tanımlı | Architect yapılandırır | nötr | nötr tema |

**Required integrations (grup geneli):** çoğu grupta **boş**. HIVE operasyonel sistem değildir.

**Optional integrations (grup geneli):**

| Grup | Opsiyonel |
|------|-----------|
| E-Ticaret | payment, marketplace (Trendyol, Shopify), accounting |
| Emlak | crm, whatsapp |
| Sağlık | crm, whatsapp, sms |
| Platform / İlan | payment (ilan ücreti), email |
| Diğer | whatsapp, crm, payment (ihtiyaca göre) |

---

## 5. Örnek Detaylı Paketler

### `hotel_pack`

| Alan | Değer |
|------|--------|
| **default pages** | `/` Ana, `/odalar`, `/olanaklar`, `/galeri`, `/sss`, `/iletisim`, `/blog` (opsiyonel GEO) |
| **default blocks** | Hero, Gallery, Pricing, FAQ, Map, Form, Testimonials |
| **schema types** | `Hotel`, `LodgingBusiness`, `LocalBusiness`, `FAQPage` |
| **SEO keyword strategy** | `{şehir} otel`, `{marka} konaklama`, `{bölge} villa`; yerel intent %50 |
| **GEO strategy** | Şehir/bölge rehber sayfaları; Google Sites support hub; NAP + GBP citation |
| **CTA language** | "Rezervasyon yapın", "Müsaitlik sorun", "Fiyat teklifi alın" |
| **design direction** | Geniş görseller, oda kartları, sıcak nötr palet |
| **required integrations** | — |
| **optional integrations** | payment (ön ödeme), whatsapp, crm |

---

### `ecommerce_pack`

| Alan | Değer |
|------|--------|
| **default pages** | `/` Ana, `/kategoriler`, `/urun/{slug}`, `/hakkimizda`, `/sss`, `/iletisim`, `/iade-politikasi` |
| **default blocks** | Hero, ProductGrid, CategoryGrid, FAQ, CTA, Testimonials |
| **schema types** | `Product`, `Offer`, `Organization`, `BreadcrumbList`, `FAQPage` |
| **SEO keyword strategy** | ürün adı + kategori + marka; transactional %60; internal link kategori → ürün |
| **GEO strategy** | Marka + kategori GEO landing; `entity_geo_graph` ile cluster; Medium/Blogger destek |
| **CTA language** | "Sepete ekle", "Hemen incele", "Kampanyaları gör" |
| **design direction** | Grid layout, net tipografi, güven rozetleri (kargo/iade metni — operasyon HIVE'de değil) |
| **required integrations** | — |
| **optional integrations** | payment (iyzico, PayTR), marketplace (Trendyol, Hepsiburada, Shopify), accounting (Paraşüt) — **ürün senkronu için**, stok/kargo HIVE dışı |

---

### `real_estate_pack`

| Alan | Değer |
|------|--------|
| **default pages** | `/` Ana, `/ilanlar`, `/ilan/{id}`, `/bolgeler`, `/danismanlar`, `/iletisim` |
| **default blocks** | Hero, ProductGrid (ilan kartı), Map, Form, FAQ, CTA |
| **schema types** | `RealEstateListing`, `Place`, `LocalBusiness`, `FAQPage` |
| **SEO keyword strategy** | `{ilçe} satılık daire`, `{tip} {şehir}`; local %55 |
| **GEO strategy** | İlçe/mahalle landing sayfaları; citation yerel dizinler; entity graph emlak ofisi |
| **CTA language** | "İlanı incele", "Randevu al", "Danışmanla görüş" |
| **design direction** | Harita öne çıkan, güvenilir kurumsal |
| **required integrations** | — |
| **optional integrations** | crm (lead), whatsapp, xml_importer (ilan feed) |

---

### `clinic_pack`

| Alan | Değer |
|------|--------|
| **default pages** | `/` Ana, `/hizmetler`, `/doktorlar`, `/sss`, `/randevu`, `/iletisim` |
| **default blocks** | Hero, FAQ, Testimonials, Form, CTA, Pricing (paket bilgi — fiyat tıbbi onay gerektirebilir) |
| **schema types** | `MedicalBusiness`, `Physician`, `MedicalProcedure`, `FAQPage` |
| **SEO keyword strategy** | `{hizmet} {şehir}`, `{klinik adı}`; informational + local |
| **GEO strategy** | Hizmet bazlı GEO cluster; Google Sites SSS hub; entity health graph |
| **CTA language** | "Randevu alın", "Ücretsiz bilgi alın", "Hizmetleri inceleyin" |
| **design direction** | Sakin, beyaz/mavi, erişilebilir tipografi |
| **required integrations** | — |
| **optional integrations** | crm, whatsapp, sms (hatırlatma — harici sistem) |

---

### `rent_a_car_pack`

| Alan | Değer |
|------|--------|
| **default pages** | `/` Ana, `/araclar`, `/arac/{slug}`, `/ofisler`, `/sss`, `/rezervasyon`, `/iletisim` |
| **default blocks** | Hero, ProductGrid, Pricing, FAQ, Map, Form, CTA |
| **schema types** | `AutoRental`, `LocalBusiness`, `Product`, `FAQPage` |
| **SEO keyword strategy** | `{şehir} araç kiralama`, `{havalimanı} rent a car`; transactional + local |
| **GEO strategy** | Şehir/havalimanı landing; çok lokasyon NAP; support network blogger |
| **CTA language** | "Hemen kirala", "Fiyat hesapla", "Müsaitlik kontrol et" |
| **design direction** | Dinamik, araç görselleri, kontrast CTA |
| **required integrations** | — |
| **optional integrations** | payment (depozito), crm, whatsapp |

---

### `listing_pack`

| Alan | Değer |
|------|--------|
| **default pages** | `/` Ana, `/kategoriler`, `/ilan/{id}`, `/ilan-ver`, `/giris`, `/sss`, `/iletisim` |
| **default blocks** | CategoryGrid, Form, BlogList, FAQ, CTA, Map (opsiyonel) |
| **schema types** | `WebSite`, `ItemList`, `Product` veya `Offer`, `FAQPage` |
| **SEO keyword strategy** | kategori + long-tail arama; programmatic SEO sayfaları (kalite kapısı zorunlu) |
| **GEO strategy** | Kategori × bölge mesh; `authority_mesh_engine`; çoklu publisher |
| **CTA language** | "İlan ver", "Ara", "Ücretsiz kayıt ol" |
| **design direction** | Liste/filtre öncelikli, yoğun bilgi mimarisi |
| **required integrations** | — |
| **optional integrations** | payment (premium ilan), email, crm; xml/csv importer — **ilan verisi**, sipariş değil |

---

## 6. Builder Wizard ile İlişkisi

Master Architecture Builder akışı:

1. Sektör seç → **pack listesi `group` altında sunulur**
2. İşletmeyi anlat → `business_brief` paket CTA/keyword şablonlarına enjekte edilir
3. Domain ekle
4. Tasarım karakteri seç → `design_direction` paket default'u üzerine override
5. Yayın modelini seç → `deploy_mode` + `publishing_network_defaults`
6. Oluştur → `POST /api/v3/projects` + `pack_id` + `version` snapshot

Wizard adım 1'de kullanıcı yalnızca sektör adını görür (`Otel`, `E-Ticaret`). `hotel_pack` gibi `pack_id` Architect Mode'da görünür.

`custom_pack` seçilirse minimal sayfa seti yüklenir; Architect veya ileri kullanıcı CMS ile genişletir.

---

## 7. Project Engine ile İlişkisi

Project Engine ([HIVE_V3_PROJECT_ENGINE.md](./HIVE_V3_PROJECT_ENGINE.md)):

- `Project.sector` = `pack_id` veya grup + alt pack referansı
- `metadata.sector_package_version` = paket semver
- `POST .../build` → `default_pages` + `default_blocks` → `astro_factory` + `page_engine` / `block_engine`
- `Site.theme_id` = `design_direction` + sektörden türetilir
- `growth_profile` = paketteki `seo_keyword_strategy`, `geo_strategy`, `aeo_strategy` özetinden kopyalanır

Build başarısız olursa `quality_gate` paket kurallarına göre raporlar; proje `error` durumuna geçebilir.

---

## 8. Growth Engine ile İlişkisi

Growth Engine (SEO, GEO, AEO, Entity, Schema, Citation, Rank, Index, Quality Gate) paketten **başlangıç planı** alır.

| Paket alanı | Growth modülü (Registry) |
|-------------|--------------------------|
| `seo_keyword_strategy` | `seo_quality_gate`, `meta_engine`, `slug_engine`, `internal_link_engine` |
| `geo_strategy` | `entity_geo_graph`, `geo_cluster_engine`, `citation_engine`, `authority_mesh_engine` |
| `aeo_strategy` | `faq_generator`, `answer_engine`, `ai_overview_optimizer` |
| `schema_types` | `schema_engine` |
| `growth_modules[]` | Orchestrator'ın yükleme listesi |

Kullanıcı UI: **Growth / SEO Health**, **Growth / GEO Network**, **Growth / AEO** — modül adı görünmez.

Paket, keyword ve cluster **şablonlarını** verir; gerçek sıralama/indeks verisi `rank_index_watcher` ile Monitoring'e akar.

---

## 9. Publishing Network ile İlişkisi

`publishing_network_defaults` her pakette tanımlıdır.

| Paket tipi | Tipik kanallar | İçerik türü |
|------------|----------------|-------------|
| Konaklama | google_sites, blogger, pinterest | sezon rehberi, GEO landing |
| E-Ticaret | medium, blogger, pinterest, x | kategori rehberi, ürün hikayesi |
| Emlak | google_sites, blogger | bölge rehberi |
| Sağlık | google_sites, blogger | SSS hub, hizmet bilgi |
| İlan | google_sites, medium, tumblr | kategori destek, authority mesh |
| Medya/Blog | medium, x, linkedin | ana yayın kanalı |

Publishing modülleri (`google_sites_worker`, `blogger_worker`, `medium_worker`, vb.) Module Registry'de **project_scoped** ve çoğunlukla `architect` visibility ile kayıtlıdır.

`POST .../publish` sırasında proje paketindeki `enabled_channels` kuyruğa alınır. Kullanıcı: **Publishing Network** ekranında "Aktif kanallar" görür.

---

## 10. Gelecekte Yeni Sektör Ekleme Kuralları

1. **Yeni pack_id** — snake_case, sonek `_pack` (ör. `spa_wellness_pack`)
2. **Grup** — mevcut 11 gruptan biri veya Architect onayı ile yeni grup
3. **Versiyon** — semver; breaking değişiklik → major bump; mevcut projeler eski `metadata.sector_package_version` ile kalır
4. **Zorunlu JSON alanları** — Bölüm 2'deki şema tam doldurulmalı
5. **Integration kuralı** — ödeme/muhasebe/kargo/stok **required** yapılamaz; yalnızca `optional_integrations` + `purpose`
6. **Quality Gate** — yeni paket `seo_quality_gate` test senaryolarından geçmeden `visibility: public` olamaz
7. **Registry kaydı** — Module Registry'de pack, Architect / Experimental altında `sector_pack` metadata ile listelenir
8. **Wizard** — `display_name` + kısa açıklama + önizleme görseli; teknik ID gizli
9. **Çakışma** — benzer pack'ler inherit edebilir (`extends: "ecommerce_pack"`) — implementasyon Architect dokümantasyonunda
10. **Deprecated** — kullanımdan kalkan pack'ler silinmez; `deprecated: true` + yeni pack'e `migrates_to` alanı

---

## Özet

Sector Pack, HIVE V3'te **site + içerik + SEO/GEO stratejisini** tek yapılandırılmış birimde toplar. Builder Wizard seçimi tetikler; Project Engine build/publish yürütür; Growth ve Publishing paket defaults ile beslenir. Operasyonel iş sistemleri (muhasebe, ödeme, kargo, stok) pakette yalnızca entegrasyon ihtiyacı olarak geçer — HIVE bunların yerine geçmez, dijital varlık ve büyüme motorudur.
