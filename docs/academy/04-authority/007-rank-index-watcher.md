# Rank & Index Watcher

## Genel Bakış

Rank & Index Watcher, projelerin arama motoru sıralamalarını ve indeks durumunu takip eden modüldür. Google Search Console, AI Overview ve manuel rank takibini tek panelde birleştirir.

## Özellikler

- **Project Takibi**: Astro ve authority projelerinin rank/indeks takibi
- **Index Status**: Google indeks durumu ve indekslenme oranı
- **Rankings**: Keyword bazında sıralama takibi
- **Search Console**: GSC verileri ile performans analizi
- **AI Overview**: Google AI Overview'da görünürlük takibi
- **Alerts**: Rank düşüşü ve indeks kaybı uyarıları
- **Opportunities**: Sıralama iyileştirme fırsatları

## Kullanım

1. **Projects**: Takip edilen projelerin listesi
2. **Index Status**: İndeks durumu ve detayları
3. **Rankings**: Keyword bazında sıralama verileri
4. **Search Console**: GSC entegrasyonu
5. **AI Overview**: AI görünürlük verileri
6. **Alerts**: Sistem uyarıları
7. **Opportunities**: İyileştirme fırsatları

## API Entegrasyonu

- `GET /api/rank-watcher/health` — Sağlık kontrolü
- `GET /api/rank-watcher/projects` — Projeler
- `GET /api/rank-watcher/project/{id}` — Proje detayı
- `GET /api/rank-watcher/index-status` — İndeks durumu
- `GET /api/rank-watcher/rankings` — Sıralamalar
- `GET /api/rank-watcher/gsc` — Search Console verileri
- `GET /api/rank-watcher/ai-overview` — AI Overview
- `GET /api/rank-watcher/alerts` — Uyarılar
- `GET /api/rank-watcher/opportunities` — Fırsatlar

## Troubleshooting

- **GSC bağlantısı yok**: Search Console API kimlik doğrulamasını kontrol edin
- **Rank verisi yok**: Projenin aktif olduğundan ve keyword'lerin tanımlandığından emin olun
- **AI Overview boş**: Provider yapılandırmasını kontrol edin

## Örnek Senaryo

"Kuşadası gece hayatı" projesinin rank takibi:

1. Projects sekmesinden projeyi seçin
2. Rankings sekmesinden keyword sıralamalarını görüntüleyin
3. Index Status sekmesinden indekslenme durumunu kontrol edin
4. AI Overview sekmesinden AI görünürlüğünü inceleyin
5. Alerts sekmesinden rank düşüşü uyarılarını görün
