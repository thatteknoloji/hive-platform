# StoryForge V3 — fastCRW + Ollama + WordPress

## Kurulum

### 1. fastCRW (scraper)

```bash
# HIVE kök dizininde
npm run docker:crw

# veya manuel
docker run -d --name crw -p 3000:3000 ghcr.io/us/crw:latest
```

Health: `curl http://localhost:3000/health`

### 2. Ollama

```bash
docker ps | grep ollama
# veya: ollama serve
```

`.env`: `OLLAMA_URL`, `OLLAMA_MODEL=llama3`

### 3. WordPress

`backend/.env`:

```env
WP_URL=https://balkutusu.com
WP_USERNAME=Fada
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx
CRW_URL=http://localhost:3000
```

## Panel akışı

1. Sidebar → **StoryForge V3 (Evrensel)**
2. fastCRW / Ollama / WP durumunu kontrol et (yeşil olmalı)
3. Hikaye URL'si gir → **Hikaye Çek ve Yayınla**

## API

| Method | Endpoint |
|--------|----------|
| GET | `/api/storyforge-v3/health` |
| POST | `/api/storyforge/process` |
| POST | `/api/storyforge-v3/scrape` |
| POST | `/api/storyforge-v3/rewrite` |
| GET | `/api/storyforge-v3/history` |

Header: `X-API-Key: <HIVE_API_KEY>`

## Test

```bash
cd backend && ./venv/bin/python -m pytest tests/test_storyforge_v3.py -q
```
