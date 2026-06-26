from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.moduller.legacy_project_migration import (
    migrate_panel_identity_state,
    migrate_module_state,
    strip_legacy_active_project_id,
    LEGACY_SYSTEM_PROJECT_IDS,
)


def test_strip_legacy_active_project_id():
    assert strip_legacy_active_project_id("balkutusu") == ""
    assert strip_legacy_active_project_id("prj-abc") == "prj-abc"


def test_migrate_panel_identity_archives_balkutusu():
    state = {
        "projects": [
            {"project_id": "balkutusu", "name": "Bal Kutusu", "domain": "https://www.balkutusu.com"},
            {"project_id": "enamou", "name": "Enamou", "domain": "https://enamou.com"},
        ],
        "active_project_id": "balkutusu",
    }
    migrated, changed = migrate_panel_identity_state(state)
    assert changed is True
    assert migrated["active_project_id"] == ""
    assert len(migrated["projects"]) == 1
    assert migrated["projects"][0]["project_id"] == "enamou"
    archived = migrated["legacy_migrations"]["panel_system_projects"]
    assert any(p["project_id"] == "balkutusu" for p in archived)


def test_migrate_module_state_archives_jobs_with_balkutusu():
    state = {
        "jobs": {
            "job-1": {"main_site_url": "https://www.balkutusu.com", "status": "done"},
            "job-2": {"main_site_url": "https://example.com", "status": "active"},
        }
    }
    migrated, changed = migrate_module_state(state)
    assert changed is True
    assert "job-1" not in migrated["jobs"]
    assert "job-2" in migrated["jobs"]
    assert "job-1" in migrated["legacy_migrations"]["archived_jobs"]


def test_migrate_panel_identity_no_balkutusu_unchanged():
    state = {"projects": [], "active_project_id": ""}
    _, changed = migrate_panel_identity_state(state)
    assert changed is False
