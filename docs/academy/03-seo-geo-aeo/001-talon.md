---
title: "Talon Nedir?"
slug: "talon-nedir"
category: "SEO / GEO / AEO"
level: "Intermediate"
order: "1"
status: "published"
version: "1.0.0"
last_updated: "2026-06-27"
owner: "HIVE Team"
---

# Talon Nedir?

Talon, HIVE'in hiper-lokal anahtar kelime araştırma motorudur. Birden fazla search provider'ı (SearXNG, Tavily, Exa) kullanarak intent bazlı, sayfa tipi odaklı ve lokasyon hassasiyetli keyword verisi üretir.

## Ne işe yarar?

- **Anahtar kelime keşfi**: Seed keyword'den binlerce long-tail varyasyon üretir
- **Intent sınıflandırması**: Her keyword'ü informational, navigational, commercial veya transactional olarak etiketler
- **Page type mapping**: Keyword'ün hangi sayfa tipinde (blog, kategori, ürün, SSS) yayınlanması gerektiğini belirler
- **GEO cluster**: Coğrafi bazlı keyword kümeleri oluşturur
- **Rakip analizi**: Rakip domain'lerin hangi keyword'lerde sıralandığını tespit eder

## Kullanım

Panel: `/talon` veya modül listesinden **Talon**'u seçin.

### Adım adım:
1. Aktif projenizin olduğundan emin olun
2. **Anahtar Kelime Avcısı** sekmesine geçin
3. Seed keyword girin (ör: "kuşadası gece hayatı")
4. Provider'ları seçin (SearXNG, Tavily, Exa)
5. "Ara" butonuna tıklayın
6. Sonuçları intent, page type ve lokasyon bazında filtreleyin

### Orchestrator Kullanımı:
1. **Full Research** sekmesine geçin
2. Keyword, lokasyon ve hedef site bilgilerini girin
3. Orchestrator intent, GEO cluster ve rakip analizini otomatik yapar
4. Sonuçları içerik brief olarak dışa aktarabilirsiniz

## API

Talon API endpoint'leri:
- `GET /api/talon/health` — sağlık kontrolü
- `GET /api/talon/status` — provider durumu
- `POST /api/talon/search` — keyword araştırması
- `GET /api/talon/orchestrator/health` — orchestrator durumu

## Görsel

> 📷 Screenshot placeholder: Talon ana sayfa ve keyword sonuçları.

## Örnek senaryo

Bir turizm ajansı "kuşadası gece hayatı" keyword'ü için içerik stratejisi oluşturmak istiyor.

1. Talon'da seed keyword olarak "kuşadası gece hayatı" girin
2. SearXNG ve Tavily provider'larını seçin
3. "Ara" butonuna tıklayın — Talon 100+ long-tail varyasyon bulur
4. Intent filtresinden "commercial" ve "transactional" seçin
5. Page type filtresinden "blog" ve "listing" işaretleyin
6. Bulunan keyword'leri Campaign Engine'e gönderin
7. Orchestrator ile intent-based content brief oluşturun

Beklenen sonuç: Hedef kitlenin aradığı spesifik sorulara yanıt veren, yüksek dönüşüm potansiyelli keyword listesi.

## İpuçları

- **Provider ayarları**: API Ayarları butonundan SearXNG, Tavily ve Exa API key'lerini yapılandırın
- **V2 Stack**: En az bir V2 provider aktif olmalıdır
- **Orchestrator**: Full Research için OpenRouter veya Ollama gereklidir

## İlgili konular

- [SEO, GEO ve AEO Nedir?](../00-baslangic/003-seo-geo-aeo-nedir.md)
- [Entity & GEO Graph](../03-seo-geo-aeo/002-entity-geo-graph.md)
- [Quality Gate Nedir?](../03-seo-geo-aeo/005-quality-gate.md)
