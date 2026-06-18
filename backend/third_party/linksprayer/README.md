# LinkSprayer Entegrasyonu

HIVE Backlink Suite, [Therenizm/LinkSprayer](https://github.com/Therenizm/LinkSprayer) mantığını `backend/app/moduller/linksprayer.py` içinde uygular:

- Ollama ile AI yorum üretimi (`OLLAMA_URL`, `OLLAMA_MODEL`)
- Hedef site listesi: `backend/data/linksprayer_targets.json`
- Kampanya API: `POST /api/linksprayer/campaign`

Orijinal repoyu klonlamak için:

```bash
git clone https://github.com/Therenizm/LinkSprayer.git backend/third_party/linksprayer/upstream
```

HIVE paneli upstream repo olmadan da çalışır; kampanyalar HIVE API üzerinden yönetilir.
