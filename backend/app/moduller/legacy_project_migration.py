"""
Legacy system-project migration — removes Balkutusu (and similar) from panel identity and module state files.
Archived entries live under state['legacy_migrations'].
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

LEGACY_SYSTEM_PROJECT_IDS = frozenset({"balkutusu"})
_BALKUTUSU_RE = re.compile(r"balkutusu", re.IGNORECASE)
_STATE_GLOB = "*_state.json"
_EXTRA_STATE_FILES = ("hive_data.json",)


def _contains_balkutusu(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_BALKUTUSU_RE.search(value))
    if isinstance(value, dict):
        return any(_contains_balkutusu(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_balkutusu(v) for v in value)
    return False


def _strip_balkutusu_strings(value: Any) -> Any:
    if isinstance(value, str):
        if _BALKUTUSU_RE.search(value):
            return ""
        return value
    if isinstance(value, dict):
        return {k: _strip_balkutusu_strings(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_balkutusu_strings(v) for v in value]
    return value


def migrate_panel_identity_state(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    changed = False
    legacy_bucket = state.setdefault("legacy_migrations", {})
    archived: list[dict[str, Any]] = []

    kept: list[dict[str, Any]] = []
    for project in state.get("projects", []):
        pid = (project.get("project_id") or "").strip()
        if pid in LEGACY_SYSTEM_PROJECT_IDS or _contains_balkutusu(project):
            archived.append(project)
            changed = True
        else:
            kept.append(project)

    if archived:
        legacy_bucket["panel_system_projects"] = archived
        state["projects"] = kept
        changed = True

    active = (state.get("active_project_id") or "").strip()
    if active in LEGACY_SYSTEM_PROJECT_IDS:
        legacy_bucket["archived_active_project_id"] = active
        state["active_project_id"] = ""
        changed = True

    return state, changed


def _archive_dict_entries(
    state: dict[str, Any],
    bucket_key: str,
    source_key: str,
) -> bool:
    bucket = state.get(source_key)
    if not isinstance(bucket, dict):
        return False
    changed = False
    legacy = state.setdefault("legacy_migrations", {})
    archived = legacy.setdefault(bucket_key, {})
    remove: list[str] = []
    for entry_id, entry in bucket.items():
        if _contains_balkutusu(entry):
            archived[entry_id] = entry
            remove.append(entry_id)
            changed = True
    for entry_id in remove:
        del bucket[entry_id]
    return changed


def _archive_list_entries(
    state: dict[str, Any],
    bucket_key: str,
    source_key: str,
) -> bool:
    items = state.get(source_key)
    if not isinstance(items, list):
        return False
    changed = False
    legacy = state.setdefault("legacy_migrations", {})
    archived = legacy.setdefault(bucket_key, [])
    kept: list[Any] = []
    for item in items:
        if _contains_balkutusu(item):
            archived.append(item)
            changed = True
        else:
            kept.append(item)
    if changed:
        state[source_key] = kept
    return changed


def migrate_module_state(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    changed = False

    active = (state.get("active_project_id") or "").strip()
    if active in LEGACY_SYSTEM_PROJECT_IDS:
        legacy = state.setdefault("legacy_migrations", {})
        legacy["archived_active_project_id"] = active
        state["active_project_id"] = ""
        changed = True

    for key in ("projects", "campaigns", "networks"):
        if _archive_dict_entries(state, f"archived_{key}", key):
            changed = True

    for key in ("jobs", "tasks", "batches"):
        if _archive_dict_entries(state, f"archived_{key}", key):
            changed = True

    for key in ("logs", "events", "timeline"):
        if _archive_list_entries(state, f"archived_{key}", key):
            changed = True

    legacy_before = state.get("legacy_migrations")
    stripped = _strip_balkutusu_strings({k: v for k, v in state.items() if k != "legacy_migrations"})
    if legacy_before:
        stripped["legacy_migrations"] = legacy_before
    if stripped != {k: v for k, v in state.items() if k != "legacy_migrations"} or (
        legacy_before and stripped.get("legacy_migrations") != legacy_before
    ):
        state = stripped
        if legacy_before:
            state["legacy_migrations"] = legacy_before
        changed = True

    return state, changed


def migrate_state_file(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(state, dict):
        return False

    active_slice = {k: v for k, v in state.items() if k != "legacy_migrations"}
    if not _contains_balkutusu(active_slice):
        return False

    if path.name == "panel_identity_state.json":
        state, changed = migrate_panel_identity_state(state)
    else:
        state, changed = migrate_module_state(state)

    if changed:
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def migrate_all_state_files(app_dir: Path | None = None) -> list[str]:
    base = app_dir or Path(__file__).resolve().parent.parent
    migrated: list[str] = []
    paths = sorted(base.glob(_STATE_GLOB))
    for name in _EXTRA_STATE_FILES:
        p = base / name
        if p not in paths:
            paths.append(p)
    for path in paths:
        if migrate_state_file(path):
            migrated.append(path.name)
    return migrated


def strip_legacy_active_project_id(active_id: str) -> str:
    pid = (active_id or "").strip()
    if pid in LEGACY_SYSTEM_PROJECT_IDS:
        return ""
    return pid
