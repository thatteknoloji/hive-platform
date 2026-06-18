"""Backlink Suite — ortak durum, entegrasyon ve dashboard."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.database import get_all_logs, log_module_run
from .modul_base import simdi

STATE_FILE = Path(__file__).resolve().parent.parent / "backlink_hub_state.json"
_lock = threading.Lock()

MODULE_IDS = [
    "backlink_hunter",
    "linksprayer",
    "directory_submitter",
    "internal_link_builder",
    "competitor_hijacker",
    "seo_content_agent",
]


def _default_state() -> dict[str, Any]:
    return {
        "opportunities": [],
        "campaigns": [],
        "directory_jobs": [],
        "link_suggestions": [],
        "scheduled_posts": [],
        "running": {},
        "stats": {m: {"toplam": 0, "son": None} for m in MODULE_IDS},
    }


def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return _default_state()


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _touch(mod_id: str) -> None:
    with _lock:
        st = load_state()
        st["stats"].setdefault(mod_id, {"toplam": 0, "son": None})
        st["stats"][mod_id]["toplam"] += 1
        st["stats"][mod_id]["son"] = simdi()
        save_state(st)


def log_activity(mod_id: str, mod_ad: str, inputs: dict, output: dict) -> None:
    _touch(mod_id)
    log_module_run(mod_id, mod_ad, inputs, output)


def add_opportunities(items: list[dict], kaynak: str = "") -> int:
    with _lock:
        st = load_state()
        existing = {(o.get("source_url"), o.get("domain_from")) for o in st["opportunities"]}
        added = 0
        for it in items:
            key = (it.get("source_url", ""), it.get("domain_from", ""))
            if key in existing or not key[0]:
                continue
            it["kaynak_modul"] = kaynak
            it["eklendi"] = simdi()
            st["opportunities"].append(it)
            existing.add(key)
            added += 1
        st["opportunities"] = st["opportunities"][-2000:]
        save_state(st)
    return added


def get_opportunities(limit: int = 100) -> list[dict]:
    return load_state()["opportunities"][-limit:]


def set_running(mod_id: str, running: bool) -> None:
    with _lock:
        st = load_state()
        st["running"][mod_id] = running
        save_state(st)


def is_running(mod_id: str) -> bool:
    return bool(load_state()["running"].get(mod_id))


def dashboard() -> dict[str, Any]:
    st = load_state()
    logs = get_all_logs(50)
    backlink_logs = [l for l in logs if l.get("mod_id") in MODULE_IDS][-20:]
    return {
        "moduller": MODULE_IDS,
        "stats": st.get("stats", {}),
        "running": st.get("running", {}),
        "opportunities_count": len(st.get("opportunities", [])),
        "campaigns_count": len(st.get("campaigns", [])),
        "directory_jobs_count": len(st.get("directory_jobs", [])),
        "link_suggestions_count": len(st.get("link_suggestions", [])),
        "scheduled_posts_count": len(st.get("scheduled_posts", [])),
        "son_aktiviteler": [
            {
                "modul": l.get("mod_ad", l.get("mod_id")),
                "zaman": l.get("timestamp"),
                "durum": "hata" if l.get("output", {}).get("status") == "hata" else "ok",
            }
            for l in reversed(backlink_logs)
        ],
    }
