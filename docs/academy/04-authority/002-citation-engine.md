# Citation Engine

## Genel Bakış

Citation Engine, içeriklerin AI citation ve görünürlük analizini yapan modüldür. Google AI Overview, ChatGPT, Perplexity ve diğer AI platformlarında içeriklerin ne kadar cite edilebilir olduğunu ölçer.

## Özellikler

- **Citation Score**: Sayfa bazında AI citation uygunluk skoru (0-100)
- **AI Visibility**: AI platformlarında görünürlük tahmini
- **Entity Trust**: Entity güven skoru ve destek sayfası analizi
- **Competitor Gap**: Rakip citation skorlarıyla karşılaştırma
- **Quick Wins**: Düşük skorlu sayfalar için hızlı kazanım fırsatları
- **Revenue Impact**: Citation skoru ile lead/ revenue korelasyonu

## Kullanım

1. **Dashboard**: Genel citation health, sayfa sayıları ve fırsatlar
2. **Pages**: Analiz edilen sayfaların listesi ve citation skorları
3. **Entities**: Entity güven ve destek sayfası verileri
4. **Visibility**: AI görünürlük ve citation/trust/overview olasılıkları
5. **Competitors**: Rakip karşılaştırma ve gap analizi
6. **Opportunities**: Citation fırsatları ve quick win'ler
7. **Revenue Impact**: Citation → Revenue etkisi
8. **Reports**: Rapor export
9. **Settings**: Citation, visibility ve trust threshold ayarları

## API Entegrasyonu

- `GET /api/citation/health` — Sağlık kontrolü
- `GET /api/citation/dashboard` — Dashboard verileri
- `GET /api/citation/settings` — Ayarlar
- `POST /api/citation/settings` — Ayarları kaydet
- `POST /api/citation/analyze-page` — Sayfa analizi
- `POST /api/citation/analyze-project` — Proje analizi
- `GET /api/citation/pages` — Sayfalar
- `GET /api/citation/entities` — Entity listesi
- `GET /api/citation/visibility` — Visibility verileri
- `GET /api/citation/competitors` — Rakip analizi
- `GET /api/citation/opportunities` — Citation fırsatları
- `POST /api/citation/export-report` — Rapor export

## Troubleshooting

- **Analiz çalışmıyor** — Settings'ten enabled=true olduğundan emin olun
- **Visibility verisi yok** — Önce proje analizi çalıştırın
- **Entity verisi yok** — Proje analizi entity taramasını da içerir
- **Revenue Impact boş** — Önce Dashboard'dan bir sayfa analiz edin

## Örnek Senaryo

"Kuşadası gece hayatı" keyword'ü için bir sayfanın citation analizi:

1. Dashboard sekmesine gidin
2. URL alanına analiz edilecek sayfa URL'sini girin
3. Project ID alanına Rank Watcher proje ID'sini yazın
4. "Analyze Page" butonuna tıklayın
5. Citation skoru ve AI visibility sonuçlarını görüntüleyin
6. Eksik sinyaller varsa bunları not alın
7. Pages sekmesinden tüm analiz edilen sayfaları görün
8. Opportunities sekmesinden quick win fırsatlarını değerlendirin
