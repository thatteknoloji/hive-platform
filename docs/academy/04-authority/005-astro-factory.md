# Astro Site Factory

## Genel Bakış

Astro Site Factory, Astro tabanlı statik sitelerin üretim ve deploy sürecini yöneten modüldür. Cloudflare Pages, GitHub Pages ve VPS hedeflerine site oluşturma, build alma ve deploy etme işlemlerini otomatize eder.

## Özellikler

- **Site Planlama**: Keyword ve template bazında site planı oluşturma
- **Build Pipeline**: Astro build sürecini yönetme
- **Multi-Target Deploy**: Cloudflare Pages, GitHub Pages, VPS
- **Export**: Build çıktısını zip olarak dışa aktarma
- **Quality Gate**: SEO/GEO/AEO kalite kontrolünden geçmiş içerik

## Kullanım

1. **Project**: Yeni Astro projesi oluşturma ve yönetme
2. **Plan**: Template ve keyword seçimi ile site planlama
3. **Build**: Astro build işlemini çalıştırma
4. **Deploy**: Cloudflare Pages veya diğer hedeflere deploy
5. **Export**: Build çıktısını zip olarak indirme
6. **Settings**: Build ve deploy yapılandırması

## API Entegrasyonu

- `GET /api/astro-factory/health` — Sağlık kontrolü
- `POST /api/astro-factory/create-project` — Proje oluşturma
- `POST /api/astro-factory/plan-site` — Site planlama
- `POST /api/astro-factory/build` — Build çalıştırma
- `POST /api/astro-factory/deploy` — Deploy etme
- `GET /api/astro-factory/export` — Build çıktısını indirme

## Troubleshooting

- **Build hatası**: Node.js sürümünü ve bağımlılıkları kontrol edin
- **Deploy hatası**: Cloudflare API token veya GitHub token'ını kontrol edin
- **Plan oluşturulamıyor**: Keyword ve template seçimini kontrol edin

## Örnek Senaryo

"Kuşadası gece hayatı" keyword'ü için Astro site oluşturma:

1. Project sekmesinde yeni proje oluşturun
2. Plan sekmesinde keyword ve template seçin
3. Build sekmesinden build işlemini başlatın
4. Deploy sekmesinden Cloudflare Pages hedefini seçip deploy edin
5. Export sekmesinden build çıktısını yedekleyin
