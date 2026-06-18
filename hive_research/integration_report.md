# HIVE Research Integration Pack V2 — Integration Report

**Tarih:** 2026-06-10  
**Amaç:** SerpBear, Agentic SEO, SEOctopus algoritmalarını mevcut HIVE modüllerine entegre etmek (repo kurulumu yok).

---

## İncelenen repolar

| Repo | Tür | HIVE'e alınan |
|------|-----|---------------|
| SerpBear | SERP tracker | Rank metrics, decay, recovery, strength |
| agentic-seo + CPS/GEO | AEO/citation | 4 yeni gate skoru, ağırlıklı overall |
| SEOctopus | Competitive SEO MCP | Entity gap, domain health, competitive strength |

---

## HIVE'e eklenen hesaplamalar

### Rank & Index Watcher
- `ranking_velocity`, `ranking_momentum`, `ranking_decay_score`, `ranking_recovery_score`, `keyword_strength_score`, `trend_direction`
- `compute_keyword_rank_metrics()` — history tabanlı
- Decay detector keyword_decay / keyword_recovery alert tipleri

### SEO GEO AEO Quality Gate
- `citation_score`, `answerability_score`, `overview_probability_score`, `llm_visibility_score`, `competitive_strength`
- Overall: SEO 25% + GEO 20% + AEO 20% + ENTITY 15% + AUTHORITY 10% + CITATION 5% + AI VISIBILITY 5%
- Sayfa raporlarında 4 yeni skor alanı

### Entity & GEO Graph
- Entity node: `entity_authority`, `entity_visibility`, `entity_gap`, `entity_strength`

### Astro Auto Publisher (Refresh Engine hazırlığı)
- Queue item: `refresh_priority`, `citation_loss`, `entity_loss`, `ai_visibility_loss`, `decay_detected`

### Network Replicator
- Domain: `authority_score`, `content_freshness`, `entity_density`, `ai_visibility`

---

## Güncellenen modüller

| Dosya | Değişiklik |
|-------|------------|
| `backend/app/moduller/rank_index_watcher.py` | SerpBear metrics |
| `backend/app/moduller/seo_quality_gate.py` | Agentic/AEO/SEOctopus skorları |
| `backend/app/moduller/entity_geo_graph.py` | Entity research skorları |
| `backend/app/moduller/astro_auto_publisher.py` | Refresh queue sinyalleri |
| `backend/app/moduller/network_replicator.py` | Domain research skorları |
| `frontend/src/pages/RankIndexWatcher.js` | Metrics tablosu |
| `frontend/src/pages/SEOQualityGate.js` | Yeni skor kartları |
| `frontend/src/pages/EntityGeoGraph.js` | Entity skor tablosu |

---

## Güncellenen state modelleri

- `rank_index_watcher_state.json` → keyword entry alanları genişledi
- `seo_quality_gate_state.json` → report'a research skorları
- `entity_geo_graph_state.json` → node entity_* alanları
- `astro_auto_publisher_state.json` → queue refresh alanları
- `network_replicator_state.json` → domain research alanları (runtime enrich)

---

## Endpointler

**Yeni endpoint yok.** Mevcut response'lar genişletildi:

- `/api/rank-watcher/*` — project keywords metrics
- `/api/seo-quality-gate/*` — report research skorları
- `/api/entity-geo-graph/*` — graph node skorları
- `/api/network-replicator/networks` — domain skorları

---

## Test & build

Çalıştır: `pytest tests/test_rank_index_watcher.py tests/test_seo_quality_gate.py tests/test_entity_geo_graph.py tests/test_astro_auto_publisher.py tests/test_network_replicator.py`

Frontend: `npm run build`

---

## Content Refresh Engine hazırlığı

Astro Auto Publisher kuyruk öğeleri artık şu sinyalleri taşır:
- Rank decay → `decay_detected`, `refresh_priority`
- Quality düşük → `citation_loss`, `entity_loss`, `ai_visibility_loss`

İleride Refresh Engine bu alanları okuyarak öncelikli sync/build tetikleyebilir.
