"""Google Sites Worker V1 testleri."""

import json
import os

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
    monkeypatch.setattr(gsw, "_playwright_available", lambda: False)
    state.write_text(json.dumps({"tasks": [], "history": []}), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state, "am_state": am_state}


def test_health_provider_missing(isolated_env):
    h = gsw.health()
    assert h["success"] is True
    assert h["ready"] is False
    assert h["provider_ready"] is False
    assert h["playwright_installed"] is False
    assert h["chromium_installed"] is False
    assert h["provider"] in ("missing", "playwright")
    assert h.get("reason") or h.get("error")


def test_create_task(isolated_env):
    res = gsw.create_task(
        site_title="Kuşadası Gece Hayatı Rehberi",
        target_keyword="kuşadası gece hayatı",
        target_money_site="https://www.balkutusu.com",
        account_profile="default",
    )
    assert res["success"] is True
    task = res["task"]
    assert task["task_id"].startswith("gsw-")
    assert task["status"] == "queued"
    assert task["site_slug"]
    assert len(task["pages"]) >= 1
    assert "answer-box" in task["pages"][0]["content_html"]


def test_task_validation(isolated_env):
    res = gsw.create_task(site_title="")
    assert res["success"] is False
    assert res["error"] == "validation_error"


def test_duplicate_task_prevention(isolated_env):
    r1 = gsw.create_task(site_title="Dup Site", site_slug="dup-site", account_profile="default")
    assert r1["success"] is True
    r2 = gsw.create_task(site_title="Dup Site 2", site_slug="dup-site", account_profile="default")
    assert r2["success"] is False
    assert r2["error"] == "duplicate_task_blocked"


def test_login_required_state(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_playwright_available", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True, "error": None,
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": False, "status": "login_required", "error": "login_required",
        "message": "Google login gerekli",
    })
    created = gsw.create_task(site_title="Login Test", target_keyword="kw")
    res = gsw.process_task(created["task"]["task_id"])
    assert res["task"]["status"] == "login_required"


def test_resume_task(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_playwright_available", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True, "error": None,
    })
    calls = {"n": 0}

    def fake_auto(task):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"success": False, "status": "login_required", "message": "login required"}
        return {"success": True, "status": "published", "published_url": "https://sites.google.com/view/test-site"}

    monkeypatch.setattr(gsw, "run_task_automation", fake_auto)
    monkeypatch.setattr(gsw, "_verify_published_url", lambda u: u.startswith("https://sites.google.com"))

    created = gsw.create_task(site_title="Resume Test", target_keyword="kw")
    tid = created["task"]["task_id"]
    gsw.process_task(tid)
    res = gsw.resume_task(tid)
    assert res["task"]["status"] == "published"
    assert res["task"]["published_url"]


def test_link_policy_application():
    html_content = gsw.build_page_html(
        site_title="Test",
        target_keyword="kuşadası gece hayatı",
        link_policies=[
            {"anchor": "Balkutusu", "target_url": "https://www.balkutusu.com", "link_type": "brand"},
            {"anchor": "Balkutusu", "target_url": "https://www.balkutusu.com", "link_type": "brand"},
            {"anchor": "", "target_url": "", "link_type": "no_link"},
        ],
    )
    assert "balkutusu.com" in html_content.lower()
    assert html_content.lower().count("balkutusu") <= 2
    assert "faq" in html_content.lower()
    assert "answer-box" in html_content


def test_authority_mesh_hook(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_playwright_available", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True, "error": None,
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": True, "status": "published", "published_url": "https://sites.google.com/view/hook-test",
    })
    monkeypatch.setattr(gsw, "_verify_published_url", lambda u: True)

    created = gsw.create_task(site_title="Hook Test", target_keyword="kw", target_money_site="https://www.balkutusu.com")
    gsw.process_task(created["task"]["task_id"])
    am = json.loads(isolated_env["am_state"].read_text(encoding="utf-8"))
    assert len(am.get("authority_sites") or []) >= 1


def test_brain_hook(isolated_env):
    gsw.create_task(site_title="Brain Test", target_keyword="kw")
    data = json.loads(isolated_env["brain_state"].read_text(encoding="utf-8"))
    assert any(e.get("module") == "google_sites_worker" for e in data.get("events") or [])


def test_rank_watcher_hook(isolated_env, monkeypatch):
    import app.moduller.rank_index_watcher as riw
    calls = {"track": 0}
    monkeypatch.setattr(riw, "register_project", lambda *a, **k: {"success": True})
    monkeypatch.setattr(riw, "track_keyword", lambda *a, **k: (calls.__setitem__("track", calls["track"] + 1) or {"success": True}))
    task = {
        "task_id": "gsw-test",
        "published_url": "https://sites.google.com/view/rank-test",
        "target_keyword": "test kw",
        "target_money_site": "",
        "site_title": "Rank",
    }
    gsw._notify_integrations(task)
    assert calls["track"] == 1


def test_support_network_hook(isolated_env):
    from app.moduller.authority_mesh_engine import register_external_publish
    reg = register_external_publish(
        "google_sites",
        url="https://sites.google.com/view/support-test",
        keyword="kw",
        role="support_hub",
    )
    am = json.loads(isolated_env["am_state"].read_text(encoding="utf-8"))
    assert len(am.get("support_network_sources") or []) >= 1
    assert reg["success"]


def test_provider_missing_explicit(isolated_env):
    res = gsw.get_task("gsw-nonexistent")
    assert res["success"] is False
    assert res["error"] == "task_not_found"

    ready, err, _, err_code = gsw._provider_ready()
    assert ready is False
    assert err_code in ("provider_missing", "browser_missing")

    created = gsw.create_task(site_title="Provider Test", target_keyword="kw")
    res = gsw.process_task(created["task"]["task_id"])
    assert res["success"] is False
    assert res["error"] == "provider_missing"


def test_no_captcha_bypass(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_playwright_available", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True, "error": None,
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": False, "status": "login_required",
        "message": "captcha detected — kullanıcı müdahanesi bekleniyor (bypass yok)",
    })
    created = gsw.create_task(site_title="Captcha Test", target_keyword="kw")
    res = gsw.process_task(created["task"]["task_id"])
    assert res["task"]["status"] == "login_required"
    assert "captcha" in (res["task"].get("error") or res["worker"].get("message", "")).lower()


def test_export_report(isolated_env):
    gsw.create_task(site_title="Report Test", target_keyword="kw")
    res = gsw.export_report("overview")
    assert res["success"] is True
    assert __import__("pathlib").Path(res["path"]).exists()


def test_authority_mesh_delegation(isolated_env, monkeypatch):
    import app.moduller.authority_mesh_engine as ame
    monkeypatch.setattr(ame, "_run_google_sites_browser_worker", lambda t: gsw.run_task_automation(t))
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": False, "error": "provider_missing", "message": "provider_missing",
    })
    task = ame.create_google_site_task(site_title="Mesh Delegation", target_keyword="kw")["task"]
    res = ame.process_google_sites_task(task["task_id"])
    assert res["task"]["status"] == "failed"
    assert res["worker"]["error"] == "provider_missing"


def test_fake_published_url_rejected(isolated_env, monkeypatch):
    monkeypatch.setattr(gsw, "_playwright_available", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True, "provider": "playwright", "openclaw": False, "playwright": True, "error": None,
    })
    monkeypatch.setattr(gsw, "run_task_automation", lambda t: {
        "success": True, "status": "published", "published_url": "https://example.com/fake",
    })
    monkeypatch.setattr(gsw, "_verify_published_url", lambda u: False)
    created = gsw.create_task(site_title="Fake URL", target_keyword="kw")
    res = gsw.process_task(created["task"]["task_id"])
    assert res["task"]["status"] == "review_required"
    assert "published_url_verification_failed" in (res["task"]["error"] or "")


def test_new_url_rejected_as_published():
    assert gsw._normalize_published_view_url("https://sites.google.com/new") is None
    assert gsw._normalize_published_view_url("https://sites.google.com/view/my-site") == "https://sites.google.com/view/my-site"


def test_fit_sites_slug():
    assert gsw._fit_sites_slug("Balkutusu Test Yayın!!!") == "balkutusu-test-yay-n"
    assert len(gsw._fit_sites_slug("a" * 50)) <= 30
    assert gsw._fit_sites_slug("") == "site"


def test_editor_and_new_home_url_helpers():
    assert gsw._is_sites_new_home_url("https://sites.google.com/new")
    assert gsw._is_sites_homescreen_url("https://sites.google.com/u/0/")
    assert gsw._is_sites_homescreen_url("https://sites.google.com/new")
    assert not gsw._is_sites_homescreen_url("https://sites.google.com/view/my-site")
    assert not gsw._is_sites_editor_url("https://sites.google.com/new")
    assert gsw._is_sites_editor_url("https://sites.google.com/site/d/abc123/edit")
    assert gsw._is_sites_editor_url("https://sites.google.com/u/0/d/abc123/edit")


def test_openclaw_priority(isolated_env, monkeypatch):
    monkeypatch.setenv("OPENCLAW_BROWSER_WORKER_URL", "http://127.0.0.1:9999")
    monkeypatch.setattr(gsw, "_playwright_available", lambda: True)
    info = gsw.detect_browser_provider()
    assert info["ready"] is True
    assert info["provider"] == "openclaw"


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_SITES_LIVE_TEST"),
    reason="GOOGLE_SITES_LIVE_TEST yok — canlı browser testi atlandı",
)
def test_live_playwright_health():
    try:
        import playwright  # noqa: F401
    except ImportError:
        pytest.skip("Playwright yüklü değil")
    h = gsw.health()
    assert h["playwright_available"] is True
