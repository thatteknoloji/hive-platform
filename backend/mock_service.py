"""
Docker mock servisleri — seo-tools compose için FastAPI wrapper.
Ana HIVE backend (port 4001) bu modülleri zaten in-process kullanır;
Docker yalnızca izole microservice testi / opsiyonel dağıtım içindir.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="HIVE Mock Service", version="1.0")
SERVICE = os.environ.get("HIVE_MOCK_SERVICE", "openseo")


class GenericBody(BaseModel):
    kelime: str = ""
    keyword: str = ""
    domain: str = ""
    marka: str = ""
    mod: str = "auto"
    limit: int = 50
    lokasyon: str = "TR"
    ulke: str = "tr"
    max_pages: int = 500
    url: str = ""


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE, "mode": "mock"}


if SERVICE == "openseo":
    from app.moduller.openseo_integration import openseo_keyword_research

    @app.post("/keyword")
    @app.post("/api/openseo/keyword")
    def keyword(body: GenericBody):
        return openseo_keyword_research(body.kelime, body.mod, body.limit, body.lokasyon)

elif SERVICE == "serpbear":
    from app.moduller.serpbear_integration import (
        serpbear_ekle,
        serpbear_goruntule,
        serpbear_liste,
        serpbear_simulasyon_sonuclari,
    )

    @app.get("/keywords")
    def keywords():
        return {"status": "aktif", "keywords": serpbear_liste()}

    @app.post("/track")
    def track(body: GenericBody):
        return serpbear_goruntule(body.keyword)

    @app.post("/register")
    def register(body: GenericBody):
        return serpbear_ekle(body.keyword, body.domain)

    @app.post("/serp")
    def serp(body: GenericBody):
        return serpbear_simulasyon_sonuclari(body.keyword)

elif SERVICE == "seointel":
    from app.moduller.seointel_integration import (
        seointel_ai_gorunurluk,
        seointel_olustur,
    )

    @app.post("/ai-visibility")
    def ai_visibility(body: GenericBody):
        return seointel_ai_gorunurluk(body.marka or body.domain)

    @app.post("/brand-presence")
    def brand_presence(body: GenericBody):
        return seointel_olustur(body.marka or body.domain)

elif SERVICE == "dataseo":
    from app.moduller.dataseo_integration import (
        dataseo_backlinks,
        dataseo_keyword_difficulty,
        dataseo_keyword_ideas,
        dataseo_traffic,
    )

    @app.post("/backlinks")
    def backlinks(body: GenericBody):
        return dataseo_backlinks(body.domain)

    @app.post("/keyword-ideas")
    def keyword_ideas(body: GenericBody):
        return dataseo_keyword_ideas(body.kelime, body.ulke)

    @app.post("/keyword-difficulty")
    def keyword_difficulty(body: GenericBody):
        return dataseo_keyword_difficulty(body.kelime, body.ulke)

    @app.post("/traffic")
    def traffic(body: GenericBody):
        return dataseo_traffic(body.domain, body.ulke)

elif SERVICE == "seoagent":
    from app.moduller.seoagent_integration import seoagent_audit_page, seoagent_crawl

    @app.post("/crawl")
    def crawl(body: GenericBody):
        return seoagent_crawl(body.domain, body.max_pages)

    @app.post("/audit")
    def audit(body: GenericBody):
        return seoagent_audit_page(body.url or f"https://{body.domain}")

else:
    @app.get("/")
    def unknown():
        return {"status": "hata", "mesaj": f"Bilinmeyen HIVE_MOCK_SERVICE: {SERVICE}"}
