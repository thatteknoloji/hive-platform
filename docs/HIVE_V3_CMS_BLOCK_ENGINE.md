# HIVE V3 CMS BLOCK ENGINE

> Referans: [HIVE_V3_MASTER_ARCHITECTURE.md](./HIVE_V3_MASTER_ARCHITECTURE.md) · [HIVE_V3_PROJECT_ENGINE.md](./HIVE_V3_PROJECT_ENGINE.md) · [HIVE_V3_SECTOR_PACKS.md](./HIVE_V3_SECTOR_PACKS.md)

---

## 1. HIVE CMS Amacı

HIVE CMS, proje sahibinin **ana siteyi güvenle düzenlemesini** sağlayan katmandır. Builder ve Sector Pack ile üretilen site iskeleti üzerinde içerik, görsel, menü ve tema değişiklikleri yapılır; yayın öncesi Quality Gate ile doğrulanır.

**Rol:**

- Project → Site → Page → Section → Block hiyerarşisinde içerik yönetimi
- Sector Pack `default_pages` / `default_blocks` çıktısını düzenlenebilir hale getirmek
- Growth Engine (SEO, GEO, schema) ile uyumlu içerik üretmek
- Astro (varsayılan) veya adaptör motorlarına render-ready veri sunmak

**CMS değildir:**

- ERP, stok, sipariş veya muhasebe paneli
- Ham HTML/CSS layout editörü (core layout engine dışı)
- Sitemap/robots/schema altyapısını kullanıcıya açan “gelişmiş mod”

Kullanıcı sonuç görür: sayfa, blok, tema. `page_engine`, `block_engine`, `theme_engine` modülleri Architect / motor odasında kalır.

---

## 2. Safe Editing Prensibi

> Kullanıcı geniş düzenleme özgürlüğüne sahiptir; responsive, layout, schema, sitemap ve core sistem bütünlüğü korunur.

### Kullanıcı yapabilir

| Alan | Örnek |
|------|--------|
| İçerik | Başlık, metin, görsel, video URL, SSS maddeleri |
| Yapı (sınırlı) | Section içinde blok sırası, yeni izin verilen blok ekleme |
| Tema (token) | Logo, renk paleti, font, radius, spacing |
| Navigasyon | Menü öğeleri, footer linkleri (şablon içinde) |
| Sayfa | Yeni sayfa (izin verilen `page_type` ile), slug önerisi |
| AI Edit | Doğal dil ile ton/CTA/SSS/dil önerisi (onaylı uygulama) |

### Kullanıcı yapamaz

| Kilit | Gerekçe |
|-------|---------|
| Responsive grid / breakpoint override | Mobil bozulma riski |
| Global CSS enjeksiyonu | Layout ve performans |
| Schema `@type` / required property silme | SEO/AEO kırılması |
| `sitemap.xml` / `robots.txt` manuel düzenleme | İndeks kontrolü motorunda |
| Core layout shell (html/head/body iskelet) | Astro renderer sözleşmesi |
| Script tag (keyfi) | Güvenlik ve CSP |
| `custom_html_safe` dışında ham HTML | XSS ve layout kırılması |

### Uygulama katmanları

1. **Field-level lock** — `locked_fields` şemada tanımlı
2. **Block allowlist** — sayfa türüne göre eklenebilir bloklar
3. **Validation** — publish öncesi schema + link + mobile
4. **Revision** — hatalı yayın → rollback

---

## 3. CMS Hiyerarşisi

```
Project
  └── Site
        └── Page
              └── Section
                    └── Block
                          └── Component (atomik UI parçası)
```

| Seviye | Sorumluluk | Örnek |
|--------|------------|--------|
| **Project** | CMS erişim kapsamı, sektör paketi, growth profili | `prj-balkutusu` |
| **Site** | Tema, global header/footer, `block_schema_version` | `site-balkutusu-001` |
| **Page** | `page_type`, slug, meta, section listesi | `/hakkimizda` |
| **Section** | Dikey bölüm; bir veya daha fazla blok container | `main`, `sidebar` |
| **Block** | Kullanıcı düzenlediği birim (hero, faq, …) | `hero_home` |
| **Component** | Block içi atom: Button, Image, Heading, RichText | `cta_button_primary` |

**Component** kullanıcıya doğrudan sürükle-bırak ile gösterilmez; block editörü içinde alan olarak düzenlenir. Architect Mode component şemasını görür.

**Module Registry eşlemesi:** `page_engine` (Page), `block_engine` (Block/Section), `theme_engine` (Site tema), `menu_engine`, `media_engine`, `form_engine`, `gallery_engine`, `faq_engine`, `blog_engine`.

---

## 4. Page Türleri

| `page_type` | Amaç | Tipik sector pack | Varsayılan bloklar |
|-------------|------|-------------------|---------------------|
| `homepage` | Ana giriş, marka + CTA | tüm paketler | hero, banner, cta, testimonials |
| `landing` | Kampanya / GEO hedef sayfa | ecommerce, hotel, real_estate | hero, faq, cta, form |
| `service` | Tek hizmet detayı | clinic, hizmet paketleri | hero, faq, pricing, cta |
| `category` | Kategori listesi | ecommerce, listing | category_grid, cta |
| `product` | Ürün / ilan detayı | ecommerce, emlak | product_grid (detail), cta |
| `blog` | Makale | media_blog, tüm | blog_list (single), faq |
| `faq` | SSS hub | tüm | faq, cta |
| `legal` | KVKK, mesafeli satış, çerez | ecommerce | custom_html_safe (kısıtlı) |
| `contact` | İletişim | tüm | map, form, hero |
| `location` | Şube / şehir / bölge GEO | hotel, rent_a_car, emlak | map, hero, faq, cta |

**Kurallar:**

- Yeni sayfa oluştururken `page_type` seçilir; slug `slug_engine` ile önerilir
- `legal` sayfalarında blok seti kısıtlıdır
- `location` sayfaları GEO cluster ile otomatik internal link önerisi alır

---

## 5. Block Türleri

| `block_type` | Görünen ad | Kullanım |
|--------------|------------|----------|
| `hero` | Hero | Üst fold, başlık + görsel + CTA |
| `banner` | Banner | Kampanya şeridi, duyuru |
| `gallery` | Galeri | Görsel grid / carousel |
| `video` | Video | embed veya hosted |
| `faq` | SSS | AEO / schema FAQPage |
| `cta` | CTA | Dönüşüm bloğu |
| `map` | Harita | Lokasyon embed |
| `form` | Form | Lead / iletişim |
| `blog_list` | Blog listesi | Makale listesi veya tekil gövde |
| `product_grid` | Ürün / ilan grid | Kategori veya detay şablonu |
| `category_grid` | Kategori grid | Kategori keşfi |
| `testimonials` | Referanslar | Sosyal kanıt |
| `pricing` | Fiyatlandırma | Paket / plan kartları |
| `header` | Header | Site üst (çoğunlukla site-level) |
| `footer` | Footer | Site alt, linkler |
| `custom_html_safe` | Güvenli HTML | Yasal metin, sınırlı etiket allowlist |

Sector Pack `default_blocks` bu listeyle birebir hizalıdır ([HIVE_V3_SECTOR_PACKS.md](./HIVE_V3_SECTOR_PACKS.md)).

---

## 6. Block Şema Kuralları

Her blok için: **editable fields**, **locked fields**, **SEO impact**, **GEO impact**, **validation rules**.

### Özet matris

| block_type | SEO impact | GEO impact |
|------------|------------|------------|
| hero | yüksek (H1, meta bağlam) | orta (yerel başlık) |
| banner | düşük | düşük |
| gallery | orta (alt text) | orta |
| video | orta | düşük |
| faq | yüksek (AEO, FAQ schema) | yüksek |
| cta | orta | orta |
| map | orta (NAP) | yüksek |
| form | düşük | orta (lead lokasyon) |
| blog_list | yüksek | orta |
| product_grid | yüksek | orta |
| category_grid | yüksek | yüksek (cluster) |
| testimonials | orta | orta |
| pricing | orta | düşük |
| header | yüksek (nav, site adı) | düşük |
| footer | orta (link graph) | orta (NAP) |
| custom_html_safe | değişken | düşük |

### `hero`

| | |
|--|--|
| **Editable** | `title`, `subtitle`, `background_image`, `background_video`, `cta_primary` (label, url), `cta_secondary`, `overlay_opacity` |
| **Locked** | `layout_variant`, `min_height`, `heading_level` (H1 sabit), `schema_role` |
| **Validation** | `title` max 120 char; görsel max boyut; CTA url https veya relative; en az bir CTA veya subtitle |
| **SEO** | Tek H1; meta description ile uyum önerisi |
| **GEO** | `{city}` placeholder sector pack’ten |

### `banner`

| | |
|--|--|
| **Editable** | `text`, `link`, `dismissible`, `style_token` (info/warning/promo) |
| **Locked** | `position` (below header), `aria_role` |
| **Validation** | metin max 200 char |
| **SEO/GEO** | minimal |

### `gallery`

| | |
|--|--|
| **Editable** | `images[]` (src, alt, caption), `layout` (grid/carousel), `columns` (2–4) |
| **Locked** | `lazy_load`, `aspect_ratio` |
| **Validation** | her görselde `alt` zorunlu; max 24 görsel |
| **SEO** | alt text kalite kapısı |
| **GEO** | lokasyon etiketli caption önerisi |

### `video`

| | |
|--|--|
| **Editable** | `embed_url`, `poster`, `title`, `caption` |
| **Locked** | `iframe_sandbox`, `provider_allowlist` (youtube, vimeo) |
| **Validation** | URL allowlist |
| **SEO** | VideoObject schema opsiyonel (locked template) |

### `faq`

| | |
|--|--|
| **Editable** | `items[]` (question, answer), `expand_first` |
| **Locked** | `schema_faqpage` (otomatik), `accordion_component` |
| **Validation** | min 3 soru (sector pack `aeo_strategy`); cevap min 40 char |
| **SEO** | yüksek — FAQ rich results |
| **GEO** | yerel soru şablonları sector pack’ten |

### `cta`

| | |
|--|--|
| **Editable** | `headline`, `body`, `button_label`, `button_url`, `style` (primary/secondary) |
| **Locked** | `button_component`, `tracking_attributes` |
| **Validation** | button_label max 40; url validasyonu |
| **SEO** | internal link equity |
| **GEO** | CTA dili sector `cta_language` ile uyum |

### `map`

| | |
|--|--|
| **Editable** | `address`, `lat`, `lng`, `zoom`, `marker_label` |
| **Locked** | `embed_provider`, `privacy_lazy_load` |
| **Validation** | geçerli koordinat veya doğrulanmış adres |
| **SEO** | NAP tutarlılığı |
| **GEO** | yüksek — LocalBusiness bağlantısı |

### `form`

| | |
|--|--|
| **Editable** | `fields[]` (allowlist: text, email, phone, textarea, select), `submit_label`, `success_message` |
| **Locked** | `action_endpoint`, `spam_protection`, `field_encryption` |
| **Validation** | max 8 alan; email format |
| **SEO** | düşük |
| **GEO** | form başlığında lokasyon önerisi |

### `blog_list`

| | |
|--|--|
| **Editable** | `source` (site blog), `limit`, `category_filter`, `show_excerpt` |
| **Locked** | `article_schema`, `canonical_rules` |
| **Validation** | limit 1–24 |
| **SEO** | yüksek — internal linking |
| **GEO** | kategori = geo tag önerisi |

### `product_grid`

| | |
|--|--|
| **Editable** | `items[]` veya `data_source` (CMS manual / marketplace sync metadata), `columns`, `card_fields` |
| **Locked** | `product_schema`, `price_display_rules` |
| **Validation** | her üründe title, image, url; fiyat yoksa Offer schema kapatılır |
| **SEO** | Product snippet |
| **GEO** | kategori bazlı landing link |

### `category_grid`

| | |
|--|--|
| **Editable** | `categories[]` (title, image, slug), `columns` |
| **Locked** | `breadcrumb_schema` |
| **Validation** | slug unique per site |
| **SEO/GEO** | yüksek — cluster hub |

### `testimonials`

| | |
|--|--|
| **Editable** | `items[]` (quote, author, role, avatar) |
| **Locked** | `review_schema` (opsiyonel, onaylı) |
| **Validation** | min 1, max 12 |
| **SEO** | Review rich result (kilitli şablon) |

### `pricing`

| | |
|--|--|
| **Editable** | `plans[]` (name, price_label, features[], cta) |
| **Locked** | `currency_display`, `offer_schema` |
| **Validation** | features max 10 madde |
| **SEO** | Offer (kısıtlı) |

### `header` / `footer`

| | |
|--|--|
| **Editable** | logo ref, `nav_items[]`, `cta_button`, footer `link_groups[]`, sosyal linkler |
| **Locked** | semantic `<header>`/`<footer>`, mobile menu component, NAP block yapısı |
| **Validation** | nav max 8 üst seviye; döngüsel link yok |
| **SEO** | site-wide link graph |
| **GEO** | footer NAP |

### `custom_html_safe`

| | |
|--|--|
| **Editable** | `html` (sanitized subset: p, ul, ol, li, a, strong, em, h2, h3) |
| **Locked** | script, style, iframe, event handlers |
| **Validation** | sanitize pipeline; max 50KB |
| **SEO** | başlık hiyerarşisi uyarısı |

---

## 7. Theme System

Tema **design token** setidir; ham CSS değil. `theme_engine` Site seviyesinde uygular.

| Token | Editable | Locked |
|-------|----------|--------|
| `logo` | src, alt, max height | aspect container |
| `color_palette` | primary, secondary, accent, background, text, muted | contrast ratio min WCAG AA |
| `font` | heading family, body family (allowlist) | font loading strategy |
| `radius` | sm, md, lg (preset scale) | component mapping |
| `spacing` | section density (compact/default/spacious) | grid gutter |
| `shadow` | none/subtle/elevated | CSS variable adları |
| `header_style` | transparent/solid/sticky | header component |
| `footer_style` | minimal/extended | footer grid |

Sector Pack `design_direction` → ilk tema önerisi; kullanıcı token’ları override eder. Kontrast düşerse publish Quality Gate uyarısı.

---

## 8. Revision System

| Durum | Açıklama |
|-------|----------|
| `draft` | Düzenleme devam ediyor; canlı site etkilenmez |
| `published` | Son başarılı yayın snapshot’ı |
| `rollback` | Önceki `published` revision’a dönüş (max N=30 saklanır) |
| `autosave` | Her 30 sn veya blur’da draft yazılır; client + server |

**Akış:**

```
edit → draft (autosave) → publish request → quality_gate → published
                                    ↓ fail
                              draft + hata listesi
rollback → yeni draft oluşturur, bir tıkla published eski haline
```

Page ve Site tema revision’ları ayrı zincirlerde tutulabilir; publish genelde site-wide atomik snapshot tercih eder (MVP: sayfa bazlı).

---

## 9. Quality Gate Publish Kontrolü

Publish (`seo_quality_gate` + teknik kontroller) — Master Architecture Growth Engine.

| Kontrol | Kriter | Fail davranışı |
|---------|--------|----------------|
| **mobile ok** | breakpoint preview, taşma yok, tıklanabilir alan min 44px | publish blok |
| **SEO ok** | title, meta desc, H1 tekillik, canonical | uyarı veya blok (kritik) |
| **schema ok** | required fields dolu, JSON-LD valid | blok |
| **performance ok** | LCP tahmini, görsel boyut, lazy load | uyarı (soft) veya blok (hard) |
| **broken link yok** | internal + external HEAD/GET | blok |

Kullanıcı UI: “Yayınla” → kontrol listesi → yeşilse canlı; kırmızıda madde madde düzeltme önerisi. Architect Mode ham skor ve modül logu.

Sector Pack `growth_modules` içinde `seo_quality_gate` zorunludur.

---

## 10. AI Edit Sistemi

Doğal dil komutları → **öneri diff** → kullanıcı onayı → block field güncellemesi. Otomatik publish yok.

| Komut örneği | Hedef | Kısıt |
|--------------|-------|--------|
| “daha lüks göster” | theme tokens + hero görsel/copy tonu | layout_variant locked |
| “CTA daha güçlü olsun” | `cta` block headline/button_label | sector `cta_language` sınırı |
| “SSS ekle” | `faq` block yeni items | min kalite, schema kuralları |
| “bu sayfayı Almanca yap” | page editable text fields | slug locked; hreflang motor önerir |

**Modüller:** `ai_command_center`, `prompt_router` (Registry). AI çıktısı `custom_html_safe` dışına ham HTML yazamaz.

---

## 11. Builder Wizard ve Sector Pack ile İlişkisi

```
Wizard step 1 (sector) → Sector Pack
       ↓
default_pages + default_blocks + design_direction
       ↓
POST /api/v3/projects → build → Site/Page/Section/Block seed
       ↓
CMS editöründe açılır (draft)
```

- İlk içerik **seed**; kullanıcı silmez, düzenler (bazı bloklar pack’te zorunlu kalabilir: örn. `faq` minimum)
- `block_schema_version` = pack `cms_block_schema_version`
- `custom_pack` → minimal seed; kullanıcı blok ekler (allowlist ile)

---

## 12. Astro Renderer ile İlişkisi

Varsayılan site motoru: **Astro + HIVE CMS** (Master Architecture).

| CMS | Astro |
|-----|--------|
| Page/Section/Block JSON | `.astro` layout + island components |
| Theme tokens | CSS variables / `@theme` |
| Locked layout | `BaseLayout.astro`, `Head.astro` (schema, sitemap link) |
| Publish | `astro_factory` static build veya SSR |

**Sözleşme:** Her `block_type` → bir Astro component (`Hero.astro`, `Faq.astro`, …). CMS yalnızca component props JSON üretir; component markup locked.

Build: `POST .../build` → renderer → artifact → deploy (`hive_cloud` / agent).

---

## 13. WordPress / WooCommerce / OpenCart Adapter ile İlişkisi

Opsiyonel adaptörler; CMS **kavramsal model** aynı kalır, sync katmanı değişir.

| Motor | CMS edit | Render |
|-------|----------|--------|
| Astro (default) | HIVE CMS native | astro_factory |
| WordPress | HIVE CMS → WP REST sync veya block → Gutenberg pattern map | WP tema |
| WooCommerce | product_grid → WC product CPT | WC + tema |
| OpenCart | product_grid → OC API metadata | OC tema |

**Prensip:** HIVE CMS canonical içerik kaynağı olabilir veya adaptör “read-only mirror” modunda çalışabilir (Architect yapılandırması). Kullanıcı yine Safe Editing kurallarına tabidir; WP admin’de tema dosyası düzenleme HIVE dışı — önerilmez.

Stok, ödeme, kargo WooCommerce/OpenCart’ta kalır; HIVE yalnızca ürün başlığı/açıklama/görsel/schema SEO alanlarını senkronize eder (Sector Pack + Marketplace dokümanı ile uyumlu).

---

## 14. İlk Sprintte Minimum CMS Kapsamı

MVP — “düzenle, kaydet, yayınla” döngüsü, safe editing ile.

### Dahil

| Alan | Kapsam |
|------|--------|
| Hiyerarşi | Site → Page → Section → Block (Component iç alan) |
| Page types | `homepage`, `landing`, `contact`, `faq`, `legal` |
| Blocks | `hero`, `faq`, `cta`, `form`, `header`, `footer`, `custom_html_safe` |
| Theme | logo, color_palette (4 renk), font (2 aile), header/footer style |
| Revision | draft, published, autosave |
| Quality Gate | SEO ok, schema ok (faq), broken link, mobile preview (basit) |
| Sector Pack | seed on build — 1 paket test (`ecommerce_pack` veya `hotel_pack`) |
| Renderer | Astro only |
| UI | Page list, block editor (form fields), tema paneli, publish butonu |

### Sprint dışı (sonraki)

- AI Edit (tam)
- `gallery`, `video`, `product_grid`, `category_grid`, `blog_list`
- WordPress/WooCommerce/OpenCart adapter
- Sayfa bazlı rollback UI (site-wide rollback yeterli)
- Çoklu dil workflow (hreflang motor)

### Başarı kriteri

Kullanıcı Sector Pack ile oluşan siteyi CMS’te açar, hero başlığını ve FAQ ekler, temayı günceller, Quality Gate’den geçer, yayınlar — **responsive/schema/sitemap bozulmadan**.

---

## Özet

HIVE CMS Block Engine, geniş içerik özgürlüğünü **kilitli alanlar**, **block şemaları** ve **Quality Gate** ile güvenli hale getirir. Sector Pack tohumlar, Project Engine build eder, Astro render eder; adaptörler opsiyonel sync sağlar. Kullanıcı modül görmez; sayfa ve sonuç görür.
