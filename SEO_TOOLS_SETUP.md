# SEO Tools Setup Guide

HIVE Panel'e 5 adet açık kaynak SEO entegrasyonu eklenmiştir. Hepsi simülasyon modunda çalışır — herhangi bir API anahtarı veya harici servis gerektirmez.

## 1. OpenSEO — Keyword Research

- **Dosya:** `backend/app/moduller/openseo_integration.py`
- **Endpoint:** `POST /api/openseo/keyword` (param: `kelime`)
- **Özellikler:** İlgili kelimeler, öneriler, fikirler — volüm/rekabet/Zorluk/CPC/niyet hesaplama
- **Simülasyon:** Türkçe SEO heuristikleri (30+ şehir, 25+ ilçe, 8 kategori, 200+ tohum kelime)

## 2. SerpBear — Rank Tracker

- **Dosya:** `backend/app/moduller/serpbear_integration.py`
- **Endpointler:**
  - `POST /api/serpbear/track` — keyword + domain sıra sorgula
  - `POST /api/serpbear/register` — keyword kaydet
  - `GET /api/serpbear/keywords` — kayıtlı kelimeler
  - `POST /api/serpbear/delete` — keyword sil
  - `POST /api/serpbear/history` — pozisyon geçmişi
  - `POST /api/serpbear/serp` — SERP ekran görüntüsü (simüle)

## 3. SEOIntel — AI Visibility

- **Dosya:** `backend/app/moduller/seointel_integration.py`
- **Endpointler:**
  - `POST /api/seointel/ai-visibility` — AI motorlarında marka görünürlüğü
  - `POST /api/seointel/brand-presence` — marka varlığı kontrolü
  - `GET /api/seointel/leaderboard` — AI liderlik tablosu
  - `POST /api/seointel/prompt` — prompt simülasyonu
  - `POST /api/seointel/backlinks` — AI backlink profili
- **Desteklenen AI Motorları:** Google AI Overview, ChatGPT, Perplexity, Gemini

## 4. DataSEO — Backlink & Keyword Metrics

- **Dosya:** `backend/app/moduller/dataseo_integration.py`
- **Endpointler:**
  - `POST /api/dataseo/backlinks` — backlink genel bakış (Ahrefs benzeri)
  - `POST /api/dataseo/backlinks/list` — backlink listesi
  - `POST /api/dataseo/backlinks/domains` — yönlendiren domainler
  - `POST /api/dataseo/keyword-ideas` — keyword fikirleri + trend
  - `POST /api/dataseo/keyword-difficulty` — keyword zorluğu + SERP
  - `POST /api/dataseo/traffic` — trafik tahmini
- **Önbellek:** 24 saat TTL JSON cache

## 5. SEOAgent — Site Crawl & Audit

- **Dosya:** `backend/app/moduller/seoagent_integration.py`
- **Wrapper:** `backend/app/scripts/seoagent_crawl.mjs` (Node.js)
- **Fonksiyonlar:** `seoagent_crawl(domain)`, `seoagent_audit_page(url)`
- **Endpointler:**
  - `POST /api/seoagent/crawl` — site tarama (param: `domain`, opsiyonel: `max_pages`)
  - `POST /api/seoagent/audit` — sayfa audit (param: `url`)
- **Not:** @seoagent/core Node.js modülü yoksa otomatik simülasyon moduna geçer

## Referans Repolar

Tüm repolar `third_party/` altında mevcuttur:

```bash
ls -la ~/Desktop/HIVE/third_party/
# open-seo/   serpbear/   seointel/   dataseo-mcp/
```

## Kurulum (Opsiyonel — SEOAgent için Node.js)

```bash
cd ~/Desktop/HIVE/backend
# @seoagent/core zaten yüklü, tekrar yüklemek için:
npm install @seoagent/core
```

## Çalıştırma

```bash
# Backend (port 4001)
cd ~/Desktop/HIVE/backend && python3 run.py

# Frontend (port 4000)
cd ~/Desktop/HIVE/frontend && npm start
```

Tüm modüller otomatik olarak HIVE Panel arayüzünde görünür.
