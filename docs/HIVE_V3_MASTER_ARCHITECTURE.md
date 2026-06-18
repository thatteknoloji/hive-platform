# HIVE V3 MASTER ARCHITECTURE

## Ana Tanım

HIVE, işletmenin dijital varlığını oluşturan, büyüten ve Google'da üstte tutan bir Growth Operating System'dir.

HIVE şunlar değildir:
- Muhasebe programı
- ERP
- CRM
- POS sistemi
- Kargo takip sistemi
- Pazaryeri paneli

HIVE bunlara bağlanır ama onların işini yapmaz.

---

## Ana Katmanlar

1. Projects
2. Builder
3. HIVE CMS
4. Content Center
5. Growth Engine
6. Publishing Network
7. Integrations
8. Marketplace
9. AI Command Center
10. Architect Mode

---

## Sol Menü

- Dashboard
- Projects
- Builder
- Content
- Growth
- Publishing
- Integrations
- Marketplace
- AI Center
- Settings
- Architect Mode

---

## Project Engine

Her şey proje bazlıdır.

Örnek projeler:
- Pentera Evleri
- BalKutusu
- Kuşadası Gece Hayatı
- Ankara Diş Kliniği

Her proje:
- sektör
- domain
- site motoru
- yayın tipi
- SEO skoru
- GEO skoru
- içerik sayısı
- yayın ağı
- entegrasyonlar

bilgilerini taşır.

---

## Builder

Yeni proje oluşturma akışı:

1. Sektör seç
2. İşletmeyi anlat
3. Domain ekle
4. Tasarım karakteri seç
5. Yayın modelini seç
6. Oluştur

---

## Sektör Paketleri

İlk sektörler:

- Otel / Pansiyon / Villa / Bungalov
- E-Ticaret
- Emlak
- Restoran / Kafe
- Klinik
- Diş Kliniği
- Veteriner
- Petshop
- Rent A Car
- Gelinlik / Damatlık / Abiye
- Ayakkabı
- Giyim
- İç Giyim
- Kozmetik
- Mobilya
- Oto Servis
- Güzellik Merkezi
- Kuaför / Barber
- Avukat
- Mali Müşavir
- Eğitim
- İlan Sitesi
- Arkadaşlık Sitesi
- Haber / Blog / Rehber
- Gece Hayatı
- Kurumsal
- Özel

Her sektör paketi:
- sayfa yapısı
- blok yapısı
- schema
- SEO stratejisi
- GEO stratejisi
- CTA dili
- tasarım yönü

içerir.

---

## Site Engine Kararı

Varsayılan:
- Astro + HIVE CMS

Opsiyonel adaptörler:
- WordPress
- WooCommerce
- OpenCart
- NextJS

Astro render motorudur. Entegrasyonlar backend servislerinde çalışır.

---

## HIVE CMS

CMS kullanıcıya geniş kontrol verir ama siteyi bozmasına izin vermez.

Kullanıcı yapabilir:
- sayfa oluştur
- sayfa düzenle
- banner ekle
- galeri ekle
- blog oluştur
- SSS oluştur
- renk değiştir
- logo değiştir
- menü değiştir
- footer düzenle
- kategori aç/kapat
- form ekle
- harita ekle
- video ekle

Kullanıcı yapamaz:
- responsive sistemi bozmak
- schema altyapısını silmek
- sitemap/robots sistemini bozmak
- core layout engine'i kırmak

---

## CMS Veri Modeli

Project
  Site
    Page
      Section
        Block

Temel bloklar:
- Hero
- Banner
- Gallery
- Video
- FAQ
- CTA
- Map
- Form
- BlogList
- ProductGrid
- CategoryGrid
- Testimonials
- Pricing
- Footer
- Header

---

## Growth Engine

Amaç:
- SEO
- GEO
- AEO
- Entity
- Schema
- Citation
- Rank
- Index
- Quality Gate

---

## Publishing Network

Ana siteyi besleyen ağ:

- Google Sites
- Blogger
- Medium
- WordPress
- Tumblr
- GitHub Pages
- Cloudflare Pages
- LinkedIn
- Pinterest
- YouTube
- X
- Instagram
- TikTok

---

## Integrations

HIVE entegrasyonlara bağlanır, onların yerine geçmez.

Ödeme:
- iyzico
- PayTR
- Stripe
- Shopier
- EsnekPos
- Banka Sanal POS

Muhasebe:
- Paraşüt
- Logo
- Mikro
- BirFatura
- BizimHesap
- KolayBi

WhatsApp:
- QR ile bağlantı

CRM:
- HubSpot
- Zoho
- Pipedrive

---

## Marketplace

Amaç ürünleri satmak değil, ürünlerden SEO/GEO uyumlu dijital varlık üretmektir.

Bağlanabilir kaynaklar:
- Trendyol
- Hepsiburada
- N11
- Amazon
- Etsy
- Shopify
- WooCommerce
- ikas
- Ticimax
- XML
- CSV

HIVE ilgilenir:
- ürün başlığı
- açıklama
- görsel
- kategori
- marka
- schema
- product SEO
- internal link
- GEO destek sayfası
- sosyal yayın

HIVE ilgilenmez:
- kargo operasyonu
- muhasebe
- iade yönetimi
- stok ERP mantığı
- POS sistemi

---

## Deploy Model

1. HIVE Cloud
Site bizim sunucuda çalışır.

2. Customer Server
Müşteri sunucusuna sadece HIVE Agent kurulur.

3. Enterprise Agent
Büyük müşteriler için gelişmiş agent.

Ana HIVE beyni müşterinin sunucusuna kurulmaz.

---

## Architect Mode

Eski 1000+ modül burada yaşar.

Kullanıcıya gösterilmez.

Modüller şu kategorilere ayrılır:
- Site & Deploy
- SEO
- GEO
- AEO
- Publisher
- Social
- Data Sources
- Integrations
- Monitoring
- Utilities
- Experimental
- Deprecated
