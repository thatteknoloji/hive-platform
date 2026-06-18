import os
import json
import app.config as config

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")

KEY_MAP = {
    "serpapi": "SERPAPI_KEY",
    "github": "GITHUB_TOKEN",
    "github_api": "GITHUB_API_KEY",
    "kf_github": "KF_GITHUB_TOKEN",
    "praw_client_id": "PRAW_CLIENT_ID",
    "praw_client_secret": "PRAW_CLIENT_SECRET",
    "namecheap_user": "NAMECHEAP_API_USER",
    "namecheap_key": "NAMECHEAP_API_KEY",
    "openseo": "OPENSEO_API_KEY",
    "proxy": "PROXY_LIST",
    "selenium": "SELENIUM_DRIVER",
    "btk_ihbar": "BTK_IHBAR_URL",
    "gsc_client_id": "GSC_CLIENT_ID",
    "gsc_client_secret": "GSC_CLIENT_SECRET",
    "gsc_site_url": "GSC_SITE_URL",
    "ga4_measurement_id": "GA4_MEASUREMENT_ID",
    "ga4_property_id": "GA4_PROPERTY_ID",
    "ga4_service_account_file": "GA4_SERVICE_ACCOUNT_FILE",
    "google_client_id": "GOOGLE_CLIENT_ID",
    "google_client_secret": "GOOGLE_CLIENT_SECRET",
    "google_refresh_token": "GOOGLE_REFRESH_TOKEN",
    "blogger_default_blog_id": "BLOGGER_DEFAULT_BLOG_ID",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "cohere": "COHERE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "replicate": "REPLICATE_API_TOKEN",
    "huggingface": "HF_TOKEN",
    "together": "TOGETHER_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "elevenlabs": "ELEVEN_API_KEY",
    "stability": "STABILITY_API_KEY",
    "cloudflare": "CLOUDFLARE_API_TOKEN",
    "cloudflare_zone_id": "CLOUDFLARE_ZONE_ID",
    "dataforseo_login": "DATAFORSEO_LOGIN",
    "dataforseo_password": "DATAFORSEO_PASSWORD",
    "tavily": "TAVILY_API_KEY",
    "exa": "EXA_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "searxng_url": "SEARXNG_URL",
    "vps_ssh_pass": "VPS_SSH_PASS",
    "ipstack": "IPSTACK_KEY",
    "tumblr_consumer_key": "TUMBLR_CONSUMER_KEY",
    "tumblr_consumer_secret": "TUMBLR_CONSUMER_SECRET",
    "tumblr_callback_url": "TUMBLR_CALLBACK_URL",
    "ghost_api_url": "GHOST_API_URL",
    "ghost_admin_api_key": "GHOST_ADMIN_API_KEY",
    "hashnode_api_token": "HASHNODE_API_TOKEN",
    "hashnode_publication_id": "HASHNODE_PUBLICATION_ID",
    "devto_api_key": "DEVTO_API_KEY",
}

def get_key(servis_adi: str) -> str | None:
    env_key = KEY_MAP.get(servis_adi)
    if not env_key:
        return None
    val = config.get(env_key)
    return val if val else None

def set_key(servis_adi: str, key: str) -> bool:
    env_key = KEY_MAP.get(servis_adi)
    if not env_key:
        return False
    try:
        os.environ[env_key] = key
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r") as f:
                lines = f.readlines()
            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(env_key + "="):
                    lines[i] = f"{env_key}={key}\n"
                    found = True
                    break
            if not found:
                lines.append(f"{env_key}={key}\n")
            with open(ENV_PATH, "w") as f:
                f.writelines(lines)
        return True
    except Exception:
        return False

def get_all_keys() -> dict:
    return {s: config.get(e) for s, e in KEY_MAP.items()}

def get_available_services() -> list:
    return sorted(KEY_MAP.keys())

def uyar(servis_adi: str, ek_bilgi: str = "") -> str:
    env_key = KEY_MAP.get(servis_adi, servis_adi.upper())
    msg = f"{env_key} eksik, lütfen ayarlardan girin"
    if ek_bilgi:
        msg += f" ({ek_bilgi})"
    return msg
