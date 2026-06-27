---
title: "Entity & GEO Graph Nedir?"
slug: "entity-geo-graph-nedir"
category: "SEO / GEO / AEO"
level: "Intermediate"
order: "2"
status: "published"
version: "1.0.0"
last_updated: "2026-06-27"
owner: "HIVE Team"
---

# Entity & GEO Graph Nedir?

Entity & GEO Graph, sayfalar, lokasyonlar, entity'ler ve keyword'ler arasındaki ilişkileri görselleştiren bir grafik analiz motorudur. Topic cluster'ları, iç link planlarını ve GEO fırsatlarını otomatik olarak çıkarır.

## Ne işe yarar?

- **Entity graph**: Proje sayfalarındaki entity'ler ve aralarındaki ilişkiler
- **GEO expand**: Lokasyon bazlı entity genişletmesi ve coğrafi fırsat keşfi
- **Topic clusters**: Keyword'leri anlamsal kümelere ayırır
- **Internal link plan**: Entity bazlı iç link önerileri üretir
- **Missing entities**: Rakiplerin sahip olduğu eksik entity'leri tespit eder

## Kullanım

Panel: `/entity-geo` veya modül listesinden **Entity & GEO Graph**'ı seçin.

### Adım adım:
1. **Build Graph**: Astro proje seçin, seed keyword ve lokasyon girin, "Build Graph" butonuna tıklayın
2. **Graph Summary**: Node, edge, entity strength, GEO coverage ve topic authority skorlarını görüntüleyin
3. **GEO Expand**: Lokasyon bazlı yeni coğrafi entity'ler keşfedin
4. **Topic Clusters**: Keyword cluster analizi yapın
5. **Internal Link Plan**: Otomatik iç link önerileri alın
6. **Missing Entities**: Eksik entity'leri ve önerilen sayfaları görün
7. **Export**: Graph'ı JSON veya Markdown olarak dışa aktarın

## API

- `GET /api/entity-geo-graph/health` — sağlık kontrolü
- `POST /api/entity-geo-graph/build-project-graph` — graph oluşturma
- `POST /api/entity-geo-graph/geo-expand` — GEO genişletme
- `POST /api/entity-geo-graph/topic-clusters` — topic cluster analizi
- `POST /api/entity-geo-graph/internal-link-plan` — iç link planı
- `POST /api/entity-geo-graph/missing-entities` — eksik entity tespiti
- `POST /api/entity-geo-graph/analyze-url` — URL analizi
- `POST /api/entity-geo-graph/export` — dışa aktarma

## Görsel

> 📷 Screenshot placeholder: Entity graph görseli ve skor kartları.

## Örnek senaryo

"Kuşadası" lokasyonu için entity graph oluşturup GEO fırsatları keşfetmek.

1. **Build Graph**: Projekte "kuşadası" seed keyword'ü ve "kusadasi" lokasyonu ile graph oluşturun
2. Graph Summary'de entity sayısı ve topic authority skorlarını inceleyin
3. **GEO Expand**: Çevre ilçeler (Selçuk, Söke) için yeni coğrafi entity'ler keşfedin
4. **Topic Clusters**: "gece hayatı", "plaj", "tarih" kümelerini analiz edin
5. **Internal Link Plan**: Entity'ler arası iç link önerilerini uygulayın
6. **Missing Entities**: Rakip sitelerde olup sizde olmayan entity'leri tespit edin

Beklenen sonuç: 20+ entity, 3 topic cluster ve 15 iç link önerisi içeren bir graph.

## İpuçları

- **Nominatim**: GEO expand için Nominatim servisinin erişilebilir olduğundan emin olun
- **Astro entegrasyonu**: Graph, Astro projesindeki sayfalarla entegre çalışır
- **Seed keyword**: Merkez keyword ne kadar spesifik olursa graph o kadar anlamlı olur

## İlgili konular

- [Talon Nedir?](../03-seo-geo-aeo/001-talon.md)
- [SEO, GEO ve AEO Nedir?](../00-baslangic/003-seo-geo-aeo-nedir.md)
- [Campaign Engine](../06-modul-ansiklopedisi/campaign_engine.md)
