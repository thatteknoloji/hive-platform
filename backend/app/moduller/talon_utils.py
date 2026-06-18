import json
import logging
from pathlib import Path

import requests

from app import config
from .talon_db import api_key_getir

logger = logging.getLogger("hive.talon")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

KUSADASI_MAHALLELER = [
    "Kadınlar Denizi", "Yılancı Burnu", "Güvercinada", "Davutlar", "Merkez",
    "Türkmen", "Soğucak", "Güzelçamlı", "Kirazlı", "Değirmendere",
]
KUSADASI_CADDELER = [
    "Atatürk Bulvarı", "Liman Caddesi", "İstiklal Caddesi", "Gazi Bulvarı",
    "Barbaros Caddesi", "Sahil Caddesi", "Marina Caddesi", "Davutlar Caddesi",
]
KUSADASI_SOKAKLAR = [
    "2. Sokak", "5. Sokak", "Çınar Sokak", "Deniz Sokak", "Zeytin Sokak",
    "Gül Sokak", "Lale Sokak", "Papatya Sokak", "Menekşe Sokak",
]


def _load_json(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize(text: str) -> str:
    return (
        text.lower()
        .replace("ı", "i").replace("ü", "u").replace("ö", "o")
        .replace("ç", "c").replace("ş", "s").replace("ğ", "g")
    )


def _get_env_key(service: str) -> str:
    env_map = {
        "dataforseo_login": "DATAFORSEO_LOGIN",
        "dataforseo_password": "DATAFORSEO_PASSWORD",
        "serpapi": "SERPAPI_KEY",
        "ollama_host": "OLLAMA_URL",
    }
    env_name = env_map.get(service)
    if env_name:
        val = (config.get(env_name) or "").strip()
        if val:
            return val
    return (api_key_getir(service) or "").strip()


class LocationService:
    @staticmethod
    def lokasyon_ara(sehir):
        fallback = _load_json("turkey_locations.json")
        sehir_lower = _normalize(sehir or "")

        if sehir_lower in ("kusadasi", "kusadası", "kuşadası"):
            return "Kuşadası", KUSADASI_MAHALLELER, KUSADASI_CADDELER, KUSADASI_SOKAKLAR

        for gercek_sehir, sehir_data in fallback.get("sehirler", {}).items():
            key = _normalize(gercek_sehir)
            if key == sehir_lower or key.startswith(sehir_lower) or sehir_lower.startswith(key):
                ilceler = sehir_data.get("ilceler", [])
                caddeler = fallback.get("caddeler", {}).get(gercek_sehir, [])
                sokaklar = fallback.get("sokaklar", {}).get(gercek_sehir, [])
                return gercek_sehir, ilceler, caddeler, sokaklar

        for gercek_sehir, sehir_data in fallback.get("sehirler", {}).items():
            for ilce in sehir_data.get("ilceler", []):
                ilce_key = _normalize(ilce)
                if ilce_key == sehir_lower or sehir_lower in ilce_key or ilce_key in sehir_lower:
                    ilceler = [ilce] + [i for i in sehir_data.get("ilceler", []) if i != ilce]
                    caddeler = fallback.get("caddeler", {}).get(gercek_sehir, [])
                    sokaklar = fallback.get("sokaklar", {}).get(gercek_sehir, [])
                    if _normalize(ilce) in ("kusadasi", "kusadası", "kuşadası"):
                        return "Kuşadası", KUSADASI_MAHALLELER, KUSADASI_CADDELER, KUSADASI_SOKAKLAR
                    return ilce, ilceler, caddeler, sokaklar

        try:
            overpass_url = "https://overpass-api.de/api/interpreter"
            query = f"""
            [out:json];
            area[name="{sehir}"]["boundary"="administrative"]["admin_level"~"4|6"];
            (node(area)["place"="suburb"]; node(area)["place"="neighbourhood"];);
            out body;
            """
            resp = requests.get(overpass_url, params={"data": query}, timeout=10)
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                yerler = list({e.get("tags", {}).get("name", "") for e in elements if e.get("tags", {}).get("name")})
                if yerler:
                    return sehir, yerler, [], []
        except requests.RequestException as e:
            logger.debug("Overpass lookup failed: %s", e)

        return sehir, [], [], []

    @staticmethod
    def sehir_dogrula(sehir):
        gercek, ilceler, _, _ = LocationService.lokasyon_ara(sehir)
        if ilceler:
            return gercek
        if sehir.lower() in (
            "istanbul", "ankara", "izmir", "antalya", "bursa", "adana", "mersin",
            "konya", "gaziantep", "eskişehir", "muğla", "aydın", "balıkesir",
            "denizli", "trabzon", "samsun", "kayseri", "kocaeli", "sakarya",
            "tekirdağ", "manisa", "hatay", "diyarbakır", "şanlıurfa", "malatya",
            "erzurum", "van", "elazığ", "afyonkarahisar", "edirne", "bolu",
            "kuşadası", "kusadasi",
        ):
            return sehir
        return "kuşadası"


def _use_legacy_apis() -> bool:
    return (config.get("TALON_USE_LEGACY_APIS") or "").lower() in ("1", "true", "yes")


class DataForSEOService:
    """DEPRECATED — yalnızca TALON_USE_LEGACY_APIS=true iken kullanılır."""

    @staticmethod
    def keyword_analiz(ana_kelime):
        if not _use_legacy_apis():
            return None
        login = _get_env_key("dataforseo_login")
        password = _get_env_key("dataforseo_password")
        if not login or not password:
            return None
        try:
            from .dataforseo_client import keyword_search_volume
            return keyword_search_volume(ana_kelime)
        except Exception as e:
            logger.warning("DataForSEO keyword analiz hatası: %s", e)
            return None

    @staticmethod
    def is_configured() -> bool:
        if not _use_legacy_apis():
            return False
        return bool(_get_env_key("dataforseo_login") and _get_env_key("dataforseo_password"))


class SerpAPIService:
    """V2 default: SearXNG → Tavily → Exa. SerpAPI yalnızca legacy modda."""

    @staticmethod
    def rakip_kontrol(kelime):
        try:
            from .talon_stack.services.talon_search_service import talon_search_service
            comp = talon_search_service.find_competitors(kelime)
            urls = comp.get("serp_urls") or []
            if urls:
                return {
                    "rakip_sayisi": len(comp.get("competitors", [])),
                    "toplam_sonuc": len(urls) * 10,
                    "ilk_sayfa": urls[:5],
                    "kaynak": "v2_stack",
                }
        except Exception as e:
            logger.debug("V2 rakip kontrol: %s", type(e).__name__)

        if not _use_legacy_apis():
            return None

        api_key = _get_env_key("serpapi")
        if not api_key:
            return None

        try:
            params = {
                "q": kelime,
                "api_key": api_key,
                "hl": "tr",
                "gl": "tr",
                "num": 10,
            }
            resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                organic = data.get("organic_results", [])
                total = data.get("search_information", {}).get("total_results")
                return {
                    "rakip_sayisi": len(organic),
                    "toplam_sonuc": total or len(organic) * 100,
                    "ilk_sayfa": [r.get("link", "") for r in organic[:5]],
                    "kaynak": "serpapi_legacy",
                }
        except requests.RequestException as e:
            logger.warning("SerpAPI legacy hatası: %s", type(e).__name__)
        return None

    @staticmethod
    def is_configured() -> bool:
        try:
            from .talon_stack.providers.base import provider_health
            ph = provider_health()
            if ph.get("searxng") == "configured" or ph.get("tavily") == "configured" or ph.get("exa") == "configured":
                return True
        except Exception:
            pass
        if _use_legacy_apis():
            return bool(_get_env_key("serpapi"))
        return False


class OllamaService:
    @staticmethod
    def _host() -> str:
        return _get_env_key("ollama_host") or "http://localhost:11434"

    @staticmethod
    def kelime_grupla(kelimeler):
        host = OllamaService._host()
        if not host:
            return None

        try:
            kelime_listesi = "\n".join(f"- {k['kelime']}" for k in kelimeler[:50])
            prompt = f"""Aşağıdaki anahtar kelimeleri mantıklı gruplara ayır.
Gruplar: lokasyon_bazli (yer/mekan içerenler), hizmet_bazli (hizmet türü içerenler), fiyat_bazli (fiyat/vip/ekonomik/ucuz içerenler), zaman_bazli (zaman içerenler), diger (hiçbirine uymayanlar).

Her kelime için sadece grup adını yaz. Format:
kelime1: grup
kelime2: grup

Kelimeler:
{kelime_listesi}"""

            model = (config.get("OLLAMA_MODEL") or "llama3").strip()
            resp = requests.post(
                f"{host.rstrip('/')}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                gruplar = {"lokasyon_bazli": [], "hizmet_bazli": [], "fiyat_bazli": [], "zaman_bazli": [], "diger": []}
                for satir in text.strip().split("\n"):
                    if ":" in satir:
                        kelime_adi, grup = satir.split(":", 1)
                        kelime_adi = kelime_adi.strip().strip('"').strip("- ")
                        grup = grup.strip().strip('"').strip("- ")
                        for item in kelimeler:
                            if item["kelime"] == kelime_adi or item["kelime"] in kelime_adi or kelime_adi in item["kelime"]:
                                if grup in gruplar:
                                    gruplar[grup].append(item)
                                else:
                                    gruplar["diger"].append(item)
                                break
                return gruplar
        except requests.RequestException as e:
            logger.warning("Ollama gruplama hatası: %s", e)
        return None

    @staticmethod
    def anlam_filtrele(kelimeler, negatif_anlam):
        host = OllamaService._host()
        if not host or not negatif_anlam:
            return None

        try:
            kelime_listesi = "\n".join(f"- {k}" for k in kelimeler[:30])
            prompt = f"""Aşağıdaki anahtar kelimelerden "{negatif_anlam}" anlamına gelenleri (yakın anlamlı, eş anlamlı, alakalı olanları) filtrele.
Sadece filtre DIŞINDA kalanları (istenmeyen anlamı İÇERMEYENLERİ) sırala.
Format: Her satıra bir kelime.

Kelimeler:
{kelime_listesi}"""

            model = (config.get("OLLAMA_MODEL") or "llama3").strip()
            resp = requests.post(
                f"{host.rstrip('/')}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                return [s.strip() for s in text.split("\n") if s.strip() and not s.startswith("-")]
        except requests.RequestException as e:
            logger.warning("Ollama anlam filtresi hatası: %s", e)
        return None

    @staticmethod
    def is_configured() -> bool:
        host = OllamaService._host()
        if not host:
            return False
        try:
            resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return bool(host)
