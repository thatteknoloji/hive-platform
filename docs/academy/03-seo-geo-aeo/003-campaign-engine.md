---
title: "Campaign Engine Nedir?"
slug: "campaign-engine-nedir"
category: "SEO / GEO / AEO"
level: "Advanced"
order: "3"
status: "published"
version: "1.0.0"
last_updated: "2026-06-27"
owner: "HIVE Team"
---

# Campaign Engine Nedir?

Campaign Engine, HIVE'in uçtan uca kampanya orkestrasyon motorudur. Keyword keşfinden authority inşasına, citation üretiminden revenue takibine kadar tüm süreci tek bir arayüzde yönetir.

## Ne işe yarar?

- **Kampanya oluşturma**: Seed keyword'den hedef, tip ve goal seçerek kampanya oluşturur
- **Blueprint yönetimi**: SEO/GEO/AEO blueprint'lerine göre dağıtım planı yapar
- **Task orkestrasyonu**: Authority Factory, Citation Engine ve Revenue modüllerine iş dağıtır
- **Dataset entegrasyonu**: Data Miner'dan gelen dataset'ler ile kampanya oluşturur
- **Progressive planlama**: Weekly blueprint ile aşamalı içerik üretimi

## Kullanım

Panel: `/campaigns` veya modül listesinden **Campaign Engine**'i seçin.

### Adım adım:
1. **Dashboard**: Aktif kampanya özeti, timeline ve yeni kampanya formu
2. **Dataset Campaign**: Data Miner dataset'inden kampanya oluşturma
3. **Campaigns**: Tüm kampanyaların listesi ve yönetimi
4. **Blueprint**: Kampanya blueprint ve weekly plan görüntüleme
5. **Tasks**: Kampanya görevleri ve Orchestrator'a gönderme
6. **Authority**: Authority Factory görevleri
7. **Citation**: Citation Engine görevleri
8. **Revenue**: Revenue lead görevleri
9. **Progress**: Score kartları ve timeline
10. **Reports**: Dışa aktarma
11. **Settings**: Modül ayarları

## API

- `GET /api/campaigns/health` — sağlık kontrolü
- `GET /api/campaigns/dashboard` — dashboard verisi
- `GET /api/campaigns/list` — kampanya listesi
- `POST /api/campaigns/create` — yeni kampanya
- `POST /api/campaigns/generate-plan` — plan üretme
- `POST /api/campaigns/send-to-orchestrator` — orchestrator'a gönderme
- `POST /api/campaigns/create-from-dataset` — dataset'ten kampanya
- `POST /api/campaigns/generate-plan-from-dataset` — dataset plan üretme
- `POST /api/campaigns/:id/attach-dataset` — dataset bağlama
- `POST /api/campaigns/send-to-authority-factory` — authority factory
- `POST /api/campaigns/export-report` — rapor dışa aktarma
- `GET /api/campaigns/datasets` — dataset listesi
- `GET /api/campaigns/tasks` — görev listesi
- `POST /api/campaigns/settings` — ayarlar

## Görsel

> 📷 Screenshot placeholder: Campaign Engine dashboard ve timeline görünümü.

## Kampanya Tipleri

| Tip | Açıklama |
|------|-----------|
| Ranking Campaign | Sıralama hedefli standart SEO kampanyası |
| Authority Campaign | Otorite inşası odaklı |
| Citation Campaign | Citation/backlink odaklı |
| Lead Campaign | Lead generation odaklı |
| Local GEO Campaign | Hiper-lokal GEO odaklı |
| Full Domination | Tüm kanallarda dominasyon |

## Örnek senaryo

"Kuşadası gece hayatı" keyword'ü için uçtan uca kampanya oluşturmak.

1. Dashboard'da "kuşadası gece hayatı" keyword'ü ve "ranking" goal ile kampanya oluşturun
2. Blueprint sekmesinde otomatik oluşturulan içerik planını inceleyin
3. Tasks sekmesinde Authority Factory, Citation Engine ve Revenue görevlerini görün
4. Dataset Campaign sekmesinde Data Miner'dan gelen entity/FAQ verilerini kampanyaya attach edin
5. Progress sekmesinde skor kartlarını ve timeline'ı takip edin
6. Reports sekmesinde overview raporunu dışa aktarın

Beklenen sonuç: 20+ task, 4 haftalık blueprint ve 60%+ execution skoru ile aktif bir kampanya.

## İlgili konular

- [Talon Nedir?](../03-seo-geo-aeo/001-talon.md)
- [Entity & GEO Graph](../03-seo-geo-aeo/002-entity-geo-graph.md)
- [Quality Gate Nedir?](../03-seo-geo-aeo/005-quality-gate.md)
- [Data Miner Engine](../06-modul-ansiklopedisi/data_miner_engine.md)
