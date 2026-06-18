"""GitHub Pages Worker V1 testleri."""

import json
import os

import pytest

from app.moduller import github_pages_worker as ghp


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "github_pages_worker_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")
    am_state = tmp_path / "authority_mesh_state.json"

    monkeypatch.setattr(ghp, "STATE_FILE", state)
    monkeypatch.setattr(ghp, "REPORTS_DIR", reports)
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

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    state.write_text(json.dumps({"sites": [], "history": []}), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state, "am_state": am_state}


def test_health_provider_missing(isolated_env):
    h = ghp.health()
    assert h["success"] is True
    assert h["provider_ready"] is False
    assert "provider_missing" in (h.get("error") or "")


def test_repo_name_sanitize():
    assert "gece" in ghp.sanitize_repo_name("Kuşadası Gece Hayatı!!!")
    assert ghp.sanitize_repo_name("valid-repo-123") == "valid-repo-123"
    generated = ghp.sanitize_repo_name("")
    assert generated.startswith("hive-pages-")


def test_create_site_payload_validation(isolated_env, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setattr(ghp, "_resolve_owner", lambda: ("testowner", None))
    res = ghp.create_site()
    assert res["success"] is False
    assert res["error"] == "validation_error"


def test_file_generation():
    files = ghp.generate_site_files(
        site_title="Kuşadası Gece Hayatı Rehberi",
        target_keyword="kuşadası gece hayatı",
        target_money_site="https://www.balkutusu.com",
        pages=[{"title": "Extra", "slug": "extra", "content_html": "<p>Extra</p>"}],
    )
    assert "index.html" in files
    assert "style.css" in files
    assert "sitemap.xml" in files
    assert "robots.txt" in files
    assert "README.md" in files
    assert "pages/extra.html" in files
    assert "<h1>" in files["index.html"]
    assert "application/ld+json" in files["index.html"]
    assert "faq" in files["index.html"].lower()


def test_link_policy_application():
    files = ghp.generate_site_files(
        site_title="Test",
        target_keyword="test keyword",
        target_money_site="https://www.balkutusu.com",
        link_policy=[
            {"anchor": "Balkutusu", "target_url": "https://www.balkutusu.com", "link_type": "brand"},
            {"anchor": "", "target_url": "", "link_type": "no_link"},
        ],
    )
    assert "balkutusu.com" in files["index.html"].lower() or "Balkutusu" in files["index.html"]


def test_path_traversal_blocked():
    assert ghp.sanitize_file_path("../etc/passwd") is None
    assert ghp.sanitize_file_path("../../secret") is None
    assert ghp.sanitize_file_path("index.html") == "index.html"
    assert ghp.sanitize_file_path("pages/valid-slug.html") == "pages/valid-slug.html"


def test_github_api_error_handling(isolated_env, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setattr(ghp, "_github_request", lambda *a, **k: {
        "success": False, "error": "github_api_error", "status_code": 422, "message": "Repository already exists",
    })
    monkeypatch.setattr(ghp, "_resolve_owner", lambda: ("owner", None))
    res = ghp.create_site(repo_name="dup-repo", site_title="Dup", target_keyword="kw")
    assert res["success"] is False
    assert "already exists" in (res.get("error") or "").lower() or res.get("site", {}).get("status") == "failed"


def test_state_persistence(isolated_env, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")

    def fake_github(method, path, **kw):
        if path == "/user/repos" or path.endswith("/repos"):
            return {"success": True, "data": {"html_url": "https://github.com/o/r", "login": "o"}}
        if "/contents/" in path:
            return {"success": True, "data": {"content": {}}}
        if path.endswith("/pages"):
            if method == "POST":
                return {"success": True, "data": {}}
            return {"success": True, "data": {"html_url": "https://o.github.io/r/", "status": "built"}}
        if path == "/user":
            return {"success": True, "data": {"login": "testowner"}}
        return {"success": True, "data": {}}

    monkeypatch.setattr(ghp, "_github_request", fake_github)
    monkeypatch.setattr(ghp, "_resolve_owner", lambda: ("testowner", None))

    res = ghp.create_site(repo_name="test-repo", site_title="Test Site", target_keyword="test kw",
                          target_money_site="https://www.balkutusu.com")
    assert res.get("site")
    st = json.loads(isolated_env["state"].read_text(encoding="utf-8"))
    assert len(st["sites"]) >= 1


def test_brain_hook(isolated_env, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setattr(ghp, "_resolve_owner", lambda: ("o", None))
    monkeypatch.setattr(ghp, "_create_repo", lambda o, r, v: {"success": True, "data": {"html_url": "https://github.com/o/r"}})
    monkeypatch.setattr(ghp, "_put_file", lambda *a, **k: {"success": True})
    monkeypatch.setattr(ghp, "_enable_pages", lambda *a, **k: {"success": True})
    monkeypatch.setattr(ghp, "_get_pages_info", lambda *a, **k: {"success": True, "data": {"html_url": "https://o.github.io/r/", "status": "built"}})
    monkeypatch.setattr(ghp, "_notify_integrations", lambda *a, **k: {})

    ghp.create_site(repo_name="brain-repo", site_title="Brain", target_keyword="kw")
    data = json.loads(isolated_env["brain_state"].read_text(encoding="utf-8"))
    assert any(e.get("module") == "github_pages_worker" for e in data.get("events") or [])


def test_authority_mesh_hook(isolated_env):
    from app.moduller.authority_mesh_engine import register_external_publish
    reg = register_external_publish(
        "github_pages",
        url="https://user.github.io/repo/",
        keyword="kw",
        money_site="https://www.balkutusu.com",
        role="geo_hub",
        repo_name="repo",
    )
    assert reg["success"] is True
    am = json.loads(isolated_env["am_state"].read_text(encoding="utf-8"))
    assert len(am.get("authority_sites") or []) >= 1


def test_rank_watcher_hook(isolated_env, monkeypatch):
    import app.moduller.rank_index_watcher as riw
    calls = {"track": 0}
    monkeypatch.setattr(riw, "register_project", lambda *a, **k: {"success": True})
    monkeypatch.setattr(riw, "track_keyword", lambda *a, **k: (calls.__setitem__("track", calls["track"] + 1) or {"success": True}))
    import app.moduller.authority_mesh_engine as ame
    monkeypatch.setattr(ame, "register_external_publish", lambda *a, **k: {"success": True})
    site = {
        "site_id": "x",
        "pages_url": "https://user.github.io/repo/",
        "target_keyword": "test kw",
        "target_money_site": "",
        "role": "support_hub",
        "repo_name": "r",
    }
    ghp._notify_integrations(site)
    assert calls["track"] == 1


def test_support_network_hook(isolated_env):
    from app.moduller.authority_mesh_engine import register_external_publish
    reg = register_external_publish(
        "github_pages",
        url="https://user.github.io/repo/",
        keyword="kw",
        role="support_hub",
    )
    am = json.loads(isolated_env["am_state"].read_text(encoding="utf-8"))
    assert len(am.get("support_network_sources") or []) >= 1
    assert reg["success"]


def test_export_report(isolated_env):
    res = ghp.export_report("overview")
    assert res["success"] is True
    assert __import__("pathlib").Path(res["path"]).exists()


@pytest.mark.skipif(not os.environ.get("GITHUB_TOKEN"), reason="GITHUB_TOKEN yok — canlı API testi atlandı")
def test_live_github_health():
    h = ghp.health()
    assert h["provider_ready"] is True
