# SerpBear — Research Analysis (HIVE Integration Pack V2)

## Repo özeti

[SerpBear](https://github.com/towfiqi/serpbear) açık kaynak, self-hosted SERP rank tracker. Next.js tabanlı; ScrapingAnt/SerpAPI/proxy ile Google sonuçlarını çeker, keyword pozisyon geçmişi tutar, GSC entegrasyonu ve e-posta alert sunar. Cron ile günlük tarama yapar.

**HIVE yaklaşımı:** Repo fork/embed **yok**. Sadece ranking history ve alert mantığı Rank & Index Watcher'a taşındı.

## Faydalı algoritmalar (çıkarılan)

| Kavram | SerpBear kaynağı | HIVE karşılığı |
|--------|------------------|----------------|
| Position history | Zaman serisi pozisyon kaydı | `keywords[].history[]` |
| Position movement | Son vs önceki delta | `ranking_velocity` |
| Ranking momentum | Çoklu ölçüm trendi | `ranking_momentum` (ağırlıklı delta) |
| Content decay | Pozisyon düşüşü alert | `ranking_decay_score` + `decay_detector` |
| Recovery | Düşüş sonrası toparlanma | `ranking_recovery_score`, `trend_direction=recovering` |
| Keyword strength | Pozisyon + trend bileşimi | `keyword_strength_score` |
| Trend direction | up/down/flat | `trend_direction` |

## Kullanılmayan parçalar

- ScrapingAnt/SerpAPI scraper katmanı (HIVE zaten DataForSEO kullanıyor)
- Next.js dashboard / PWA
- Google Ads keyword research entegrasyonu
- E-posta SMTP alert (HIVE NotificationCenter ayrı)
- Smart scrape strategy (num=100 workaround)

## HIVE entegrasyon noktaları

- **Modül:** `backend/app/moduller/rank_index_watcher.py`
- **Fonksiyonlar:** `compute_keyword_rank_metrics`, `_apply_keyword_metrics`
- **State:** Her keyword entry'de 6 yeni alan
- **Endpoint:** Yeni endpoint yok — `GET /api/rank-watcher/project/{id}`, `POST track-keyword`, `POST decay` genişletildi
- **Frontend:** `RankIndexWatcher.js` Rankings sekmesi — metrik tablosu

## Önerilen geliştirmeler

1. Scheduler ile otomatik bulk_track + decay (cron)
2. GSC query dimension ile keyword strength blend
3. Content Refresh Engine'e `decay_detected` sinyali (Astro Auto Publisher queue'da hazır)
