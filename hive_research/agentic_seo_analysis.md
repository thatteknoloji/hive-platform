# Agentic SEO — Research Analysis (HIVE Integration Pack V2)

## Repo özeti

[agentic-seo](https://github.com/addyosmani/agentic-seo) (Addy Osmani) dokümantasyon sitelerinin AI coding agent'lar tarafından keşfedilip parse edilebilirliğini ölçer. 10 kontrol, 5 kategori, 100 puanlık skor: robots.txt, llms.txt, heading hierarchy, token budget, meta tags.

İlgili kavramlar: CPS (Citation Probability Score), GEO atomic answer blocks, Athena Citation Engine — block-level citation probability.

**HIVE yaklaşımı:** Repo kurulumu yok. AEO/citation/LLM visibility heuristikleri SEO Quality Gate'e eklendi.

## Faydalı algoritmalar (çıkarılan)

| Kavram | Kaynak | HIVE skoru |
|--------|--------|------------|
| Declarative opening | CPS / GEO | `citation_score` |
| Direct answer blocks | AEO / answerability | `answerability_score` |
| Semantic containment | AI Overview research | `overview_probability_score` |
| Heading hierarchy + extractable structure | agentic-seo | `llm_visibility_score` |
| Q-shaped headings | Contently LLMO | `answerability_score` bonus |
| Citation-anchor density | LLMO v4 | `citation_score` fact density |

## Kullanılmayan parçalar

- llms.txt / AGENTS.md dosya kontrolleri (Astro static site farklı stack)
- gpt-tokenizer per-page budget (ileride dist HTML için)
- Cheerio CLI audit aracı
- Agent simulation fetch

## HIVE entegrasyon noktaları

- **Modül:** `backend/app/moduller/seo_quality_gate.py`
- **Fonksiyonlar:** `_research_citation_score`, `_research_answerability_score`, `_research_overview_probability`, `_research_llm_visibility`
- **Overall ağırlık:** SEO 25%, GEO 20%, AEO 20%, ENTITY 15%, AUTHORITY 10%, CITATION 5%, AI VISIBILITY 5%
- **Endpoint:** Mevcut `analyze-project`, `analyze-url`, `analyze_page` response genişletildi
- **Frontend:** `SEOQualityGate.js` — 4 yeni skor kartı

## Önerilen geliştirmeler

1. Block-level scoring (paragraf bazlı CPS)
2. dist/ HTML post-build gate (agentic-seo token budget)
3. Rank Watcher AI Overview sonuçları ile `overview_probability` kalibrasyonu
