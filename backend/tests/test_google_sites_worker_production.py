"""Google Sites Worker Production Fix V1 — integration tests."""

from __future__ import annotations

import json

import pytest

from app.moduller import google_sites_worker as gsw


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "google_sites_worker_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")
    am_state = tmp_path / "authority_mesh_state.json"

    monkeypatch.setattr(gsw, "STATE_FILE", state)
    monkeypatch.setattr(gsw, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)
    import app.moduller.authority_mesh_engine as ame
    monkeypatch.setattr(ame, "STATE_FILE", am_state)
    am_state.write_text(json.dumps({
        "settings": dict(ame.DEFAULT_SETTINGS),
        "authority_sites": [],
        "mesh_plans": [],
        "tasks": [],
        "google_sites_tasks": [],
        "link_policies": [],
        "support_network_sources": [],
        "history": [],
    }), encoding="utf-8")

    monkeypatch.delenv("OPENCLAW_BROWSER_WORKER_URL", raising=False)
    monkeypatch.setenv("GOOGLE_SITES_PROVIDER", "playwright")
    monkeypatch.setenv("GOOGLE_SITES_HEADLESS", "false")
    monkeypatch.setenv("GOOGLE_SITES_USER_DATA_DIR", str(tmp_path / "browser_profiles" / "google_sites"))
    monkeypatch.setenv("GOOGLE_SITES_PROFILE", "default")
    monkeypatch.setattr(gsw, "_playwright_available", lambda: True)
    monkeypatch.setattr(gsw, "_chromium_installed", lambda: False)
    state.write_text(json.dumps({"tasks": [], "history": []}), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state, "tmp_path": tmp_path}


def test_health_browser_missing(isolated_env):
    h = gsw.health()
    assert h["ready"] is False
    assert h["playwright_installed"] is True
    assert h["chromium_installed"] is False
    assert h["provider"] == "playwright"
    assert "chromium" in (h.get("reason") or "").lower() or h.get("error") == "browser_missing"
    assert h["browser_profile_dir"]


def test_health_chromium_installed(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    h = gsw.health()
    assert h["chromium_installed"] is True
    assert h["ready"] is True
    assert h["reason"] == ""


def test_create_task_writes_state(isolated_env):
    res = gsw.create_task(site_title="Prod Test Site", target_keyword="kw", account_profile="default")
    assert res["success"] is True
    data = json.loads(isolated_env["state"].read_text(encoding="utf-8"))
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "queued"


def test_login_required_not_failed(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True,
        "chromium_installed": True, "error": None, "reason": "",
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": False, "status": "login_required", "error": "google_login_required",
        "message": "Google login gerekli",
    })
    created = gsw.create_task(site_title="Login Flow", target_keyword="kw")
    tid = created["task"]["task_id"]
    res = gsw.process_task(tid)
    assert res["task"]["status"] == "login_required"
    assert res["task"]["status"] != "failed"
    assert res["task"]["error"] == "google_login_required"


def test_resume_task_keeps_task_id(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True,
        "chromium_installed": True, "error": None, "reason": "",
    })
    calls = {"n": 0}

    def fake_auto(task):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"success": False, "status": "login_required", "error": "google_login_required"}
        return {"success": True, "status": "published", "published_url": "https://sites.google.com/view/resume-prod"}

    monkeypatch.setattr(gsw, "run_task_automation", fake_auto)
    monkeypatch.setattr(gsw, "_verify_published_url", lambda u: u.startswith("https://sites.google.com"))

    created = gsw.create_task(site_title="Resume Prod", target_keyword="kw")
    tid = created["task"]["task_id"]
    gsw.process_task(tid)
    res = gsw.resume_task(tid)
    assert res["task"]["task_id"] == tid
    assert res["task"]["status"] == "published"


def test_published_url_validation_required(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True,
        "chromium_installed": True, "error": None, "reason": "",
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": True, "status": "published", "published_url": "https://sites.google.com/view/valid",
    })
    monkeypatch.setattr(gsw, "_verify_published_url", lambda u: False)
    created = gsw.create_task(site_title="Verify Test", target_keyword="kw")
    res = gsw.process_task(created["task"]["task_id"])
    assert res["task"]["status"] == "review_required"
    assert "published_url_verification_failed" in (res["task"]["error"] or "")
    assert not res["task"].get("published_url")


def test_fake_published_rejected(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True,
        "chromium_installed": True, "error": None, "reason": "",
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": True, "status": "published", "published_url": "https://example.com/fake",
    })
    created = gsw.create_task(site_title="Fake URL", target_keyword="kw")
    res = gsw.process_task(created["task"]["task_id"])
    assert res["task"]["status"] == "review_required"
    assert res["task"].get("published_url") is None


def test_authority_factory_google_sites_writes_task_id(isolated_env, monkeypatch):
    from app.moduller import authority_factory as af

    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True,
        "chromium_installed": True, "error": None, "reason": "",
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": False, "status": "login_required", "error": "google_login_required",
    })

    item = {"item_id": "afi-1", "title": "AF GS", "target_keyword": "kw", "provider": "google_sites", "role": "support_hub"}
    batch = {"target_money_site": "https://www.balkutusu.com", "network_id": "net-1"}
    settings = {"allow_google_sites": True}
    res = af._process_google_sites_item(item, batch, settings)
    assert "task_id" in res or item.get("metadata", {}).get("google_sites_task_id")
    assert item["assigned_worker"].startswith("google_sites_worker:gsw-")


def test_authority_factory_login_required_mapping(isolated_env, monkeypatch):
    from app.moduller import authority_factory as af

    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True,
        "chromium_installed": True, "error": None, "reason": "",
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": False, "status": "login_required", "error": "captcha_or_2fa_required",
    })
    item = {"item_id": "afi-2", "title": "AF Login", "target_keyword": "kw", "provider": "google_sites"}
    batch = {"target_money_site": "https://www.balkutusu.com"}
    res = af._process_google_sites_item(item, batch, {"allow_google_sites": True})
    assert item["status"] == "login_required"
    assert item["status"] != "failed"


def test_authority_factory_provider_missing_mapping(isolated_env, monkeypatch):
    from app.moduller import authority_factory as af

    monkeypatch.setattr(gsw, "_chromium_installed", lambda: False)
    item = {"item_id": "afi-3", "title": "AF Missing", "target_keyword": "kw", "provider": "google_sites"}
    batch = {"target_money_site": "https://www.balkutusu.com"}
    af._process_google_sites_item(item, batch, {"allow_google_sites": True})
    assert item["status"] in ("browser_missing", "provider_missing")
    assert item["status"] != "failed"


def test_no_password_token_in_state(isolated_env):
    gsw.create_task(site_title="Secret Safe", target_keyword="kw", account_profile="default")
    raw = isolated_env["state"].read_text(encoding="utf-8").lower()
    for forbidden in ("password", "token", "refresh_token", "client_secret", "api_key"):
        assert forbidden not in raw


def test_brain_event_login_required_and_published(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True,
        "chromium_installed": True, "error": None, "reason": "",
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": True, "status": "published", "published_url": "https://sites.google.com/view/brain-prod",
    })
    monkeypatch.setattr(gsw, "_verify_published_url", lambda u: True)

    created = gsw.create_task(site_title="Brain Pub", target_keyword="kw", target_money_site="https://www.balkutusu.com")
    gsw.process_task(created["task"]["task_id"])
    data = json.loads(isolated_env["brain_state"].read_text(encoding="utf-8"))
    events = data.get("events") or []
    assert any(e.get("module") == "google_sites_worker" for e in events)


@pytest.mark.skipif(
    not __import__("os").environ.get("GOOGLE_SITES_LIVE_TEST"),
    reason="Set GOOGLE_SITES_LIVE_TEST=1 for live browser test",
)
def test_live_browser_health(isolated_env, monkeypatch):
    monkeypatch.undo()
    h = gsw.health()
    assert "provider" in h
    assert "chromium_installed" in h
