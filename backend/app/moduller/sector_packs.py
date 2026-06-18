"""Load HIVE V3 sector packs from packs/v1/*.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PACKS_DIR = Path(__file__).resolve().parent.parent / "packs" / "v1"


@lru_cache(maxsize=32)
def load_pack(sector_id: str) -> dict[str, Any] | None:
    sid = (sector_id or "").strip()
    path = PACKS_DIR / f"{sid}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def get_default_pages(sector_id: str) -> list[dict[str, Any]]:
    pack = load_pack(sector_id)
    if pack and isinstance(pack.get("default_pages"), list):
        return list(pack["default_pages"])
    fallback = load_pack("ozel")
    if fallback and isinstance(fallback.get("default_pages"), list):
        return list(fallback["default_pages"])
    return []


def list_sectors() -> list[str]:
    manifest = PACKS_DIR / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            sectors = data.get("sectors")
            if isinstance(sectors, list):
                return [str(s) for s in sectors]
        except (json.JSONDecodeError, OSError):
            pass
    return sorted(p.stem for p in PACKS_DIR.glob("*.json") if p.stem != "manifest")
