# SEOctopus — Research Analysis (HIVE Integration Pack V2)

## Repo özeti

[SEOctopus](https://github.com/itsjwill/seoctopus) TypeScript MCP + CLI. 23 araç: GSC keywords, competitive analyze, content gap, SERP share, site audit, `octo_score` (0–100 SEO faktör ağırlıkları).

**HIVE yaklaşımı:** MCP/CLI kurulmadı. Competitive gap, opportunity scoring ve site health mantığı Entity GEO Graph + SEO Gate içine taşındı.

## Faydalı algoritmalar (çıkarılan)

| Kavram | SEOctopus | HIVE karşılığı |
|--------|-----------|----------------|
| keywords_gaps (pos 4–20, yüksek impression) | Quick wins | `opportunity_finder` (mevcut, genişletilebilir) |
| competitive_content_gap | Eksik topic/heading | `entity_gap` skoru |
| competitive_analyze | Word count, schema, headings | Entity node authority |
| octo_score / site health | E-E-A-T, freshness | `competitive_strength`, Network `content_freshness` |
| opportunity scoring | Commercial intent × gap | `entity_strength` composite |

## Kullanılmayan parçalar

- MCP server / CLI binary
- Google Analytics arm (HIVE AnalyticsHub ayrı)
- octo_score tam faktör matrisi (sadece gap + authority özü alındı)
- SERP share calculator (DataForSEO ile ileride)

## HIVE entegrasyon noktaları

- **Entity GEO Graph:** `entity_authority`, `entity_visibility`, `entity_gap`, `entity_strength` per node
- **SEO Gate:** `_research_competitive_gap_score` → authority blend
- **Network Replicator:** `authority_score`, `content_freshness`, `entity_density`, `ai_visibility` per domain
- **Frontend:** `EntityGeoGraph.js` entity skor tablosu; NetworkReplicator mevcut domain listesi zengin state döner

## Önerilen geliştirmeler

1. `competitive_content_gap` için rakip URL crawl (opsiyonel, mevcut competitor modülü)
2. Hard/soft/positioning gap tipleri (goose-skills seo-opportunity-finder)
3. Network domain `rank_status` / `index_status` Rank Watcher sync
