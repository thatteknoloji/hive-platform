import random
import hashlib
from datetime import datetime

AI_MOTORLARI = [
    {"engine": "Google AI Overview", "icon": "google"},
    {"engine": "ChatGPT", "icon": "openai"},
    {"engine": "Perplexity", "icon": "perplexity"},
    {"engine": "Gemini", "icon": "gemini"},
]

ULKELER = {
    "tr": "Türkiye",
    "us": "United States",
    "uk": "United Kingdom",
    "de": "Germany",
    "fr": "France",
}

RAPOR_DEPOSU = {}

def _hash(d):
    return int(hashlib.md5(d.encode("utf-8")).hexdigest()[:8], 16)

def _mock_ai_overview(domain, market="us"):
    h = _hash(domain + market)
    engines = []
    for i, motor in enumerate(AI_MOTORLARI):
        engines.append({
            "engine": motor["engine"],
            "brand_presence": (h * (i + 1)) % 300 + 10,
            "link_presence": (h * (i + 2)) % 200 + 5,
            "traffic": (h * (i + 3)) % 5000 + 100,
        })
    return engines

def _mock_leaderboard(domain, market="us"):
    h = _hash(domain + "leaderboard" + market)
    rakipler = [
        {"domain": domain, "share_of_voice": 35, "brand_mentions": 150, "link_citations": 200},
        {"domain": f"competitor-1.{market}", "share_of_voice": 25, "brand_mentions": 100, "link_citations": 140},
        {"domain": f"competitor-2.{market}", "share_of_voice": 18, "brand_mentions": 75, "link_citations": 110},
        {"domain": f"competitor-3.{market}", "share_of_voice": 12, "brand_mentions": 45, "link_citations": 70},
        {"domain": f"competitor-4.{market}", "share_of_voice": 10, "brand_mentions": 30, "link_citations": 50},
    ]
    for i, r in enumerate(rakipler):
        r["rank"] = i + 1
    return rakipler

def _mock_prompts(domain, engine, market="us"):
    h = _hash(domain + engine + market)
    prompts = []
    basliklar = [
        "What are the best alternatives to...",
        "How does {domain} compare with...",
        "Top factors to consider when choosing...",
        "Complete guide for beginners...",
        "Why {domain} is the best choice for...",
        "Step by step guide to implementing...",
        "Expert review of {domain} services...",
        "Cost analysis of vs competitors...",
    ]
    for i in range(min(4, (h % 5) + 2)):
        baslik = random.choice(basliklar).replace("{domain}", domain)
        prompts.append({
            "prompt": f"{baslik} in {2024 + (i % 2)}?",
            "type": random.choice(["brand", "link", "brand_link"]),
            "search_volume": (h * (i + 1)) % 1000 + 50,
            "engine": engine,
            "answer_snippet": f"This is a simulated AI answer from {engine} about {domain}. In our analysis, {domain} ranks among top providers with strong brand presence and authority signals across multiple categories.",
            "sources": [f"https://www.example{i}.com/source", f"https://www.industry-report.com/{domain}"],
        })
    return prompts

def seointel_olustur(domain: str, api_key: str = "", market: str = "us"):
    domain = domain.strip().lower().replace("https://", "").replace("http://", "").replace("www.", "")
    rid = hashlib.md5((domain + datetime.now().isoformat()).encode()).hexdigest()[:12]

    ai_overview = _mock_ai_overview(domain, market)
    leaderboard = _mock_leaderboard(domain, market)

    prompt_list = []
    for motor in AI_MOTORLARI:
        prompt_list.extend(_mock_prompts(domain, motor["engine"], market))
    random.shuffle(prompt_list)
    prompt_list = prompt_list[:8]

    brand_presence_total = sum(e["brand_presence"] for e in ai_overview)
    link_presence_total = sum(e["link_presence"] for e in ai_overview)
    traffic_total = sum(e["traffic"] for e in ai_overview)

    rapor = {
        "id": rid,
        "domain": domain,
        "market": market,
        "market_name": ULKELER.get(market, market),
        "ai_search": {
            "overview": {
                "target": domain,
                "engines": ai_overview,
            },
            "brand_presence_total": brand_presence_total,
            "link_presence_total": link_presence_total,
            "traffic_estimate": traffic_total,
            "leaderboard": leaderboard,
            "prompts": prompt_list,
        },
        "tarih": datetime.now().isoformat(),
        "api_kullanildi": bool(api_key),
    }

    RAPOR_DEPOSU[rid] = rapor
    return {"status": "aktif", "rapor": rapor, "id": rid}

def seointel_rapor_getir(rid: str):
    rapor = RAPOR_DEPOSU.get(rid)
    if not rapor:
        return {"status": "hata", "mesaj": "Rapor bulunamadı"}
    return {"status": "aktif", "rapor": rapor}

def seointel_ai_gorunurluk(domain: str, market: str = "us"):
    sonuc = seointel_olustur(domain, "", market)
    ai = sonuc["rapor"]["ai_search"]
    return {
        "status": "aktif",
        "domain": domain,
        "market": market,
        "ai_search": ai,
    }

def seointel_backlinks(domain: str):
    h = _hash(domain + "bl")
    domain = domain.strip().lower().replace("https://", "").replace("http://", "").replace("www.", "")
    return {
        "domain": domain,
        "backlinks": {
            "total": (h % 50000) + 1000,
            "referring_domains": (h % 500) + 50,
            "domain_rating": (h % 100),
            "url_rating": (h % 80),
            "follow_ratio": round(random.uniform(0.3, 0.8), 2),
            "nofollow_ratio": round(random.uniform(0.1, 0.4), 2),
            "edu_backlinks": (h % 50),
            "gov_backlinks": (h % 20),
        },
        "top_anchors": [
            {"text": "click here", "count": (h % 100) + 10},
            {"text": domain, "count": (h % 50) + 5},
            {"text": "learn more", "count": (h % 30) + 3},
            {"text": "website", "count": (h % 20) + 2},
        ],
    }
