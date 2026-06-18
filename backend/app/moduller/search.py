import requests
import json

SERPAPI_KEY = "49dca5ae9234f5c5f4da8c0b9afc81c9bfd4f5a53922573d5ae6b37d19966405"

def search_serpapi(query: str, num: int = 10):
    if not query:
        return {"hata": "query parametresi gerekli"}
    try:
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": num,
            "engine": "google",
        }
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return {"hata": f"SERPAPI hatası: {resp.status_code}", "detay": resp.text[:200]}
        data = resp.json()
        organic = data.get("organic_results", [])
        sonuclar = []
        for r in organic[:num]:
            sonuclar.append({
                "baslik": r.get("title", ""),
                "link": r.get("link", ""),
                "aciklama": r.get("snippet", ""),
                "goruntulenme_linki": r.get("displayed_link", ""),
            })
        return {
            "sorgu": query,
            "toplam": data.get("search_information", {}).get("total_results", 0),
            "sonuclar": sonuclar,
            "kaynak": "serpapi",
        }
    except requests.exceptions.Timeout:
        return {"hata": "SERPAPI zaman aşımı"}
    except Exception as e:
        return {"hata": f"SERPAPI hatası: {str(e)}"}
