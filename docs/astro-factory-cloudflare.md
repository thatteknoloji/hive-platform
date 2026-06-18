# Astro Site Factory — Cloudflare Pages Auto Deploy

HIVE panelinden `generated-sites/{slug}/dist/` klasörünü Cloudflare Pages'e tek tıkla yayınlama.

## Cloudflare API Token Alma

1. [Cloudflare Dashboard](https://dash.cloudflare.com/) → **My Profile** → **API Tokens**
2. **Create Token** → **Create Custom Token**
3. Gerekli izinler:
   - **Account** → **Cloudflare Pages** → **Edit**
   - **Account** → **Account Settings** → **Read** (Account read)
4. Token'ı kopyalayın (bir daha gösterilmez).

## Account ID

Cloudflare Dashboard → sağ sidebar veya **Workers & Pages** → Account ID.

## `.env` Örneği

```env
CLOUDFLARE_API_TOKEN=your_api_token_here
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
CLOUDFLARE_DEFAULT_PROJECT_PREFIX=hive-
CLOUDFLARE_PAGES_BRANCH=main
```

## Panel Akışı (Tek Tık Deploy)

1. **Astro Site Factory** → **1. Proje** → Proje oluştur
2. **2. Plan** → Plan üret
3. **3. İçerik** → Sayfaları üret
4. **4. Build & Export** → `npm install && npm run build` (dist oluşmalı)
5. **Cloudflare Deploy** bölümünde:
   - Env durumunun yeşil olduğunu kontrol et
   - İsteğe bağlı: Cloudflare proje adını düzenle
   - **Create Pages Project** (ilk seferde)
   - **Deploy to Cloudflare Pages**
6. Deployment URL ve logları aynı sekmede görünür.

## API Endpoint'leri

| Method | Endpoint |
|--------|----------|
| GET | `/api/astro-factory/cloudflare/status` |
| POST | `/api/astro-factory/cloudflare/create-project` |
| POST | `/api/astro-factory/cloudflare/deploy` |
| GET | `/api/astro-factory/cloudflare/deployments/{project_id}` |

Tüm isteklerde: `X-API-Key: <HIVE_API_KEY>`

## Deploy Yöntemi

Gerçek deploy `wrangler pages deploy` ile yapılır (`npx wrangler@3` veya sistemdeki `wrangler`).  
`CLOUDFLARE_API_TOKEN` ve `CLOUDFLARE_ACCOUNT_ID` ortam değişkenleri subprocess'e aktarılır.

## Test

```bash
cd backend && ./venv/bin/python -m pytest tests/test_cloudflare_pages_deploy.py -q
# Gerçek API (env varsa):
./venv/bin/python -m pytest tests/test_cloudflare_pages_deploy.py -m integration -q
```
