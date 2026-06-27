# Authority Mesh Engine

## Genel Bakış

Authority Mesh Engine, otorite ağı orkestrasyon modülüdür. Google Sites, GitHub Pages, Blogger, Tumblr, Dev.to ve WordPress gibi farklı platformlarda otorite siteleri oluşturur ve tek bir mesh altında yönetir.

## Özellikler

- **Authority Sites**: Birden fazla platformda otorite sitesi oluşturma
- **Mesh Plans**: Keyword bazında site planı oluşturma
- **Google Sites**: Browser automation ile Google Sites yayını
- **GitHub Pages**: REST API ile GitHub Pages repo oluşturma ve yayınlama
- **Publisher Sources**: Blogger, Tumblr, Dev.to, WordPress entegrasyonu
- **Link Policy**: Otomatik anchor text ve link politikası oluşturma
- **Task Management**: Task kuyruğu, işleme, login ve resume yönetimi
- **Worker Health**: Browser ve API worker sağlık durumu izleme
- **Interactive Graph**: Otorite ağını görselleştiren interaktif grafik

## Kullanım

1. **Dashboard**: Genel durum, published/authority site sayıları, grafik
2. **Authority Sites**: Tüm authority sitelerin listesi
3. **Mesh Plans**: Keyword girerek site planı oluşturma
4. **Google Sites**: Browser automation ile Google Sites task yönetimi
5. **GitHub Pages**: GitHub Pages repo ve yayın yönetimi
6. **Publisher Sources**: API ve browser provider listesi
7. **Link Policy**: Anchor text ve link politikası görüntüleme
8. **Tasks**: Tüm task'ların durumu ve timeline
9. **Reports**: Rapor export (overview, sites, plans, tasks, link_policy)
10. **Settings**: Varsayılan money site, network ID ve duplicate ayarları

## API Entegrasyonu

- `GET /api/authority-mesh/health` — Sağlık kontrolü
- `GET /api/authority-mesh/dashboard` — Dashboard verileri
- `GET /api/authority-mesh/settings` — Ayarlar
- `POST /api/authority-mesh/settings` — Ayarları kaydet
- `GET /api/authority-mesh/sites` — Authority siteleri
- `POST /api/authority-mesh/create-site-plan` — Site planı oluştur
- `POST /api/authority-mesh/create-publisher-plan` — Publisher planı
- `POST /api/authority-mesh/process-plan` — Planı işle
- `GET /api/authority-mesh/tasks` — Task listesi
- `GET /api/authority-mesh/reports` — Rapor verileri
- `POST /api/authority-mesh/export-report` — Rapor export
- `GET /api/github-pages/health` — GitHub Pages sağlık
- `GET /api/github-pages/sites` — GitHub siteleri
- `POST /api/github-pages/create-site` — GitHub sitesi oluştur
- `POST /api/github-pages/publish-site` — GitHub sitesi yayınla
- `GET /api/google-sites/health` — Google Sites sağlık
- `GET /api/google-sites/tasks` — Google Sites task'ları
- `POST /api/google-sites/create-task` — Google Sites task oluştur
- `POST /api/google-sites/process-task` — Task işle
- `POST /api/google-sites/resume-task` — Task devam ettir

## Troubleshooting

- **Browser worker provider_missing**: Backend'de Chromium kurulu değil — `python -m playwright install chromium`
- **Google Sites login_required**: Tarayıcı profilinde Google hesabına giriş yapın, ardından Resume Task
- **GitHub Pages provider_missing**: GITHUB_TOKEN ortam değişkenini kontrol edin
- **Mesh plan oluşturulamıyor**: Keyword ve Money Site URL'sini kontrol edin
- **Duplicate site hatası**: Settings'ten duplicate site block'u devre dışı bırakabilirsiniz

## Örnek Senaryo

"Kuşadası gece hayatı" keyword'ü için authority mesh oluşturma:

1. Mesh Plans sekmesine gidin
2. Keyword alanına "kuşadası gece hayatı" yazın
3. Money Site URL'sini girin
4. "Mesh Plan Oluştur" butonuna tıklayın
5. Plan ID'sini not alın
6. "Planı İşle" butonuyla planı işleme alın
7. Google Sites sekmesinden browser automation task'larını yönetin
8. GitHub Pages sekmesinden repo oluşturma ve yayınlama yapın
9. Dashboard'daki interaktif grafta otorite ağını görüntüleyin
10. Link Policy sekmesinden otomatik oluşturulan anchor politikasını inceleyin
