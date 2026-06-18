"""Metin üretimi — llm_router üzerinden API + Ollama."""

from __future__ import annotations

from app.moduller import llm_router


def generate(prompt: str, max_tokens: int = 800) -> tuple[str, bool]:
    """(metin, ai_kullanildi) — geriye uyumluluk."""
    llm_router.ensure_ollama_running()
    text, engine = llm_router.generate(prompt, max_tokens=max_tokens, min_length=50)
    return text, bool(text and engine)


def get_model() -> str:
    return llm_router.resolve_ollama_model()
