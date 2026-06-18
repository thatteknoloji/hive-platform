"""
HIVE provider tercihleri — DataForSEO opsiyonel, kullanıcı seçimi.

Modlar:
- auto: DataForSEO yapılandırılmışsa önce dene, yoksa ücretsiz zincir
- free: Sadece ücretsiz provider'lar
- dataforseo: Sadece DataForSEO (yapılandırılmamışsa provider_missing)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.provider_settings")

STATE_FILE = Path(__file__).resolve().parent.parent / "hive_provider_settings.json"

CATEGORIES = ("backlink", "domain", "rank", "serp", "keyword", "ai_overview")
PROVIDER_MODES = ("auto", "free", "dataforseo")

DEFAULT_SETTINGS: dict[str, str] = {
    "backlink": "auto",
    "domain": "free",
    "rank": "auto",
    "serp": "auto",
    "keyword": "auto",
    "ai_overview": "auto",
}

CATEGORY_LABELS = {
    "backlink": "Backlink",
    "domain": "Domain Sorgu",
    "rank": "Sıra Takibi",
    "serp": "SERP",
    "keyword": "Keyword Verisi",
    "ai_overview": "AI Overview",
}


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings = data.setdefault("settings", dict(DEFAULT_SETTINGS))
                for k, v in DEFAULT_SETTINGS.items():
                    settings.setdefault(k, v)
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"settings": dict(DEFAULT_SETTINGS)}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, str]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(patch: dict[str, Any]) -> dict[str, str]:
    st = _load_state()
    cur = st.setdefault("settings", dict(DEFAULT_SETTINGS))
    for k, v in (patch or {}).items():
        if k in DEFAULT_SETTINGS and v in PROVIDER_MODES:
            cur[k] = v
    _save_state(st)
    return dict(cur)


def _dataforseo_ready() -> bool:
    try:
        from app.moduller.dataforseo_client import is_configured
        return is_configured()
    except Exception:
        return False


def resolve_mode(category: str, override: str | None = None) -> str:
    """Geçerli mod: auto | free | dataforseo."""
    if override and override in PROVIDER_MODES:
        return override
    settings = get_settings()
    mode = settings.get(category) or DEFAULT_SETTINGS.get(category, "auto")
    return mode if mode in PROVIDER_MODES else "auto"


def should_try_dataforseo(category: str, override: str | None = None) -> bool:
    mode = resolve_mode(category, override)
    if mode == "free":
        return False
    if mode == "dataforseo":
        return True
    return _dataforseo_ready()


def require_dataforseo(category: str, override: str | None = None) -> bool:
    return resolve_mode(category, override) == "dataforseo"


def provider_chain(category: str, override: str | None = None) -> list[str]:
    """Denenecek provider sırası."""
    mode = resolve_mode(category, override)
    dfs_ok = _dataforseo_ready()
    if mode == "dataforseo":
        return ["dataforseo"] if dfs_ok else []
    if mode == "free":
        if category == "backlink":
            return ["openseo", "dataseo_mcp", "dataseo_free"]
        if category == "domain":
            return ["mcp", "whois", "dns"]
        return ["free"]
    # auto
    if category == "backlink":
        chain = []
        if dfs_ok:
            chain.append("dataforseo")
        chain.extend(["openseo", "dataseo_mcp", "dataseo_free"])
        return chain
    if category == "domain":
        return ["mcp", "whois", "dns"]
    if category in ("rank", "serp", "keyword", "ai_overview"):
        return ["dataforseo", "free"] if dfs_ok else ["free"]
    return ["free"]


def health() -> dict[str, Any]:
    settings = get_settings()
    dfs = _dataforseo_ready()
    per_category: dict[str, Any] = {}
    for cat in CATEGORIES:
        mode = settings.get(cat, "auto")
        chain = provider_chain(cat)
        per_category[cat] = {
            "mode": mode,
            "label": CATEGORY_LABELS.get(cat, cat),
            "chain": chain,
            "dataforseo_available": dfs,
            "ready": bool(chain) or cat == "domain",
        }
    return {
        "success": True,
        "module": "provider_settings",
        "settings": settings,
        "dataforseo_configured": dfs,
        "categories": per_category,
        "modes": list(PROVIDER_MODES),
    }
