"""HIVE — birleşik LLM yönlendirici: API key'ler + Ollama + worker fallback."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

import requests

from app import config
from app.moduller.api_key_manager import get_key

logger = logging.getLogger("hive.llm")

WORKER_URL = "https://hive-ai-worker.boxxhoneyy.workers.dev"

_SQLITE_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "together": "TOGETHER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
}


def _key(service: str) -> str:
    val = (get_key(service) or "").strip()
    if val:
        return val
    try:
        from app.moduller.talon_db import api_key_getir
        return (api_key_getir(service) or "").strip()
    except Exception:
        return ""


def _ollama_base() -> str:
    raw = (config.get("OLLAMA_URL") or "http://127.0.0.1:11434/api/generate").strip()
    return raw.replace("/api/generate", "").rstrip("/")


def ensure_ollama_running() -> bool:
    """Ollama kapalıysa arka planda başlatmayı dene."""
    base = _ollama_base()
    try:
        r = requests.get(f"{base}/api/tags", timeout=3)
        if r.status_code == 200:
            return True
    except requests.RequestException:
        pass
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        for _ in range(8):
            time.sleep(0.5)
            try:
                r = requests.get(f"{base}/api/tags", timeout=2)
                if r.status_code == 200:
                    logger.info("Ollama başlatıldı")
                    return True
            except requests.RequestException:
                continue
    except (OSError, FileNotFoundError) as e:
        logger.debug("Ollama serve başlatılamadı: %s", e)
    return False


def resolve_ollama_model() -> str:
    configured = (config.get("OLLAMA_MODEL") or "llama3.2:3b").strip()
    base = _ollama_base()
    try:
        r = requests.get(f"{base}/api/tags", timeout=5)
        if r.status_code != 200:
            return configured
        names = [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
        if not names:
            return configured
        if configured in names:
            return configured
        prefix = configured.split(":")[0]
        for name in names:
            if name.startswith(prefix) or prefix in name:
                return name
        return names[0]
    except requests.RequestException:
        return configured


_PROVIDER_LABELS: dict[str, str] = {
    "groq": "Groq",
    "openrouter": "OpenRouter",
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "deepseek": "DeepSeek",
    "perplexity": "Perplexity",
    "together": "Together AI",
    "mistral": "Mistral",
    "anthropic": "Anthropic",
    "cohere": "Cohere",
    "ollama": "Yerel Ollama",
    "hive_worker": "HIVE Cloud Worker",
}


def _provider_model(name: str, ollama_model: str = "") -> str:
    models = {
        "groq": (config.get("GROQ_MODEL") or "llama-3.3-70b-versatile").strip(),
        "openrouter": (config.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini").strip(),
        "openai": (config.get("OPENAI_MODEL") or "gpt-4o-mini").strip(),
        "gemini": (config.get("GEMINI_MODEL") or "gemini-2.0-flash").strip(),
        "deepseek": "deepseek-chat",
        "perplexity": "sonar",
        "together": (config.get("TOGETHER_MODEL") or "meta-llama/Llama-3-8b-chat-hf").strip(),
        "ollama": (ollama_model or resolve_ollama_model()).strip(),
        "hive_worker": "ücretsiz yedek",
    }
    return models.get(name, "")


def _provider_ready(name: str, apis: dict[str, bool], ollama_ok: bool) -> bool:
    if name == "ollama":
        return ollama_ok
    if name == "hive_worker":
        return True
    return bool(apis.get(name))


def _build_provider_info(name: str, ollama_model: str = "") -> dict[str, str]:
    return {
        "id": name,
        "label": _PROVIDER_LABELS.get(name, name),
        "model": _provider_model(name, ollama_model),
        "type": "local" if name == "ollama" else "cloud",
    }


def _resolve_engine_chain(
    priority: list[str],
    apis: dict[str, bool],
    ollama_ok: bool,
    ollama_model: str,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    available: list[str] = [
        name for name in priority if _provider_ready(name, apis, ollama_ok)
    ]
    if not available:
        return _build_provider_info("hive_worker", ollama_model), []
    primary_name = available[0]
    fallbacks = [
        _build_provider_info(name, ollama_model) for name in available[1:]
    ]
    return _build_provider_info(primary_name, ollama_model), fallbacks


def list_engines() -> dict[str, Any]:
    """Panelde hangi motorların hazır olduğunu göster."""
    ollama_ok = False
    ollama_model = ""
    try:
        ensure_ollama_running()
        base = _ollama_base()
        r = requests.get(f"{base}/api/tags", timeout=3)
        if r.status_code == 200:
            ollama_ok = True
            ollama_model = resolve_ollama_model()
    except requests.RequestException:
        pass

    apis = {}
    for svc in _SQLITE_KEY_MAP:
        apis[svc] = bool(_key(svc))

    apis["tavily"] = bool((config.get("TAVILY_API_KEY") or "").strip())
    apis["exa"] = bool((config.get("EXA_API_KEY") or "").strip())
    apis["hive_worker"] = True

    priority = _engine_priority()
    primary, fallbacks = _resolve_engine_chain(priority, apis, ollama_ok, ollama_model)

    return {
        "ollama": {"ready": ollama_ok, "model": ollama_model},
        "apis": apis,
        "priority": priority,
        "primary": primary,
        "fallbacks": fallbacks,
        "chain": [primary, *fallbacks],
    }


def _engine_priority() -> list[str]:
    order = []
    for name in ("groq", "openrouter", "openai", "gemini", "deepseek", "perplexity", "together", "mistral", "anthropic"):
        if _key(name):
            order.append(name)
    order.append("ollama")
    order.append("hive_worker")
    return order


def _chat_openai_compatible(
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    system: str = "",
    max_tokens: int = 2500,
    extra_headers: dict[str, str] | None = None,
) -> str:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    r = requests.post(
        url,
        headers=headers,
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
        timeout=120,
    )
    if r.status_code == 200:
        return (r.json()["choices"][0]["message"]["content"] or "").strip()
    logger.debug("LLM %s hata %s: %s", url, r.status_code, r.text[:200])
    return ""


def _try_groq(prompt: str, system: str, max_tokens: int) -> str:
    key = _key("groq")
    if not key:
        return ""
    model = (config.get("GROQ_MODEL") or "llama-3.3-70b-versatile").strip()
    return _chat_openai_compatible(
        "https://api.groq.com/openai/v1/chat/completions",
        key,
        model,
        prompt,
        system,
        max_tokens,
    )


def _try_openrouter(prompt: str, system: str, max_tokens: int) -> str:
    key = _key("openrouter")
    if not key:
        return ""
    model = (config.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini").strip()
    return _chat_openai_compatible(
        "https://openrouter.ai/api/v1/chat/completions",
        key,
        model,
        prompt,
        system,
        max_tokens,
        {"HTTP-Referer": "https://balkutusu.com", "X-Title": "HIVE StoryForge"},
    )


def _try_openai(prompt: str, system: str, max_tokens: int) -> str:
    key = _key("openai")
    if not key:
        return ""
    model = (config.get("OPENAI_MODEL") or "gpt-4o-mini").strip()
    return _chat_openai_compatible(
        "https://api.openai.com/v1/chat/completions",
        key,
        model,
        prompt,
        system,
        max_tokens,
    )


def _try_gemini(prompt: str, system: str, max_tokens: int) -> str:
    key = _key("gemini")
    if not key:
        return ""
    model = (config.get("GEMINI_MODEL") or "gemini-2.0-flash").strip()
    full = f"{system}\n\n{prompt}" if system else prompt
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    r = requests.post(
        url,
        json={"contents": [{"parts": [{"text": full}]}], "generationConfig": {"maxOutputTokens": max_tokens}},
        timeout=120,
    )
    if r.status_code == 200:
        parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return (parts[0].get("text") or "").strip() if parts else ""
    return ""


def _try_deepseek(prompt: str, system: str, max_tokens: int) -> str:
    key = _key("deepseek")
    if not key:
        return ""
    return _chat_openai_compatible(
        "https://api.deepseek.com/v1/chat/completions",
        key,
        "deepseek-chat",
        prompt,
        system,
        max_tokens,
    )


def _try_perplexity(prompt: str, system: str, max_tokens: int) -> str:
    key = _key("perplexity")
    if not key:
        return ""
    return _chat_openai_compatible(
        "https://api.perplexity.ai/chat/completions",
        key,
        "sonar",
        prompt,
        system,
        max_tokens,
    )


def _try_together(prompt: str, system: str, max_tokens: int) -> str:
    key = _key("together")
    if not key:
        return ""
    model = (config.get("TOGETHER_MODEL") or "meta-llama/Llama-3-8b-chat-hf").strip()
    return _chat_openai_compatible(
        "https://api.together.xyz/v1/chat/completions",
        key,
        model,
        prompt,
        system,
        max_tokens,
    )


def _try_ollama(prompt: str, system: str, max_tokens: int) -> str:
    ensure_ollama_running()
    base = _ollama_base()
    model = resolve_ollama_model()
    payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    try:
        r = requests.post(f"{base}/api/generate", json=payload, timeout=180)
        if r.status_code == 200:
            return (r.json().get("response") or "").strip()
    except requests.RequestException as e:
        logger.debug("Ollama hata: %s", e)
    return ""


def _try_worker(prompt: str) -> str:
    try:
        r = requests.post(WORKER_URL, json={"prompt": prompt.strip()}, timeout=60)
        if r.status_code != 200:
            return ""
        data = r.json()
        return (data.get("response") or data.get("reply") or "").strip()
    except requests.RequestException:
        return ""


_PROVIDERS = [
    ("groq", _try_groq),
    ("openrouter", _try_openrouter),
    ("openai", _try_openai),
    ("gemini", _try_gemini),
    ("deepseek", _try_deepseek),
    ("perplexity", _try_perplexity),
    ("together", _try_together),
    ("ollama", _try_ollama),
]


def generate(
    prompt: str,
    system: str = "",
    max_tokens: int = 2500,
    min_length: int = 200,
) -> tuple[str, str]:
    """
    Metin üret. Dönüş: (metin, engine_adı).
    engine boş string ise hiçbir motor çalışmadı.
    """
    if not prompt or not prompt.strip():
        return "", ""

    for name, fn in _PROVIDERS:
        if name != "ollama" and not _key(name):
            continue
        try:
            text = fn(prompt, system, max_tokens)
            if text and len(text) >= min_length:
                logger.info("LLM motor: %s (%d karakter)", name, len(text))
                return text, name
        except Exception as e:
            logger.warning("LLM %s exception: %s", name, e)

    text = _try_worker(prompt)
    if text and len(text) >= min_length:
        return text, "hive_worker"

    return "", ""
