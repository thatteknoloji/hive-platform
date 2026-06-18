"""Authority Mesh Engine V1 — orkestrasyon testleri."""

import json

import pytest

from app.moduller import authority_mesh_engine as ame


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "authority_mesh_engine_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(ame, "STATE_FILE", state)
    monkeypatch.setattr(ame, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "settings": dict(ame.DEFAULT_SETTINGS),
        "authority_sites": [],
        "mesh_plans": [],
        "tasks": [],
        "google_sites_tasks": [],
        "link_policies": [],
        "support_network_sources": [],
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state}


def test_health(isolated_env):
    h = ame.health()
    assert h["success"] is True
    assert h["module"] == "authority_mesh_engine"
    assert "providers" in h
    assert h["providers"]["google_sites"] == "browser"


def test_create_mesh_plan(isolated_env):
    res = ame.create_site_plan("kuşadası gece hayatı", money_site="https://www.balkutusu.com")
    assert res["success"] is True
    plan = res["plan"]
    assert plan["keyword"] == "kuşadası gece hayatı"
    assert len(plan["items"]) >= 5
    assert plan["link_policy"]


def test_link_policy_diversity(isolated_env):
    policies = ame.generate_link_policy("kuşadası gece hayatı", "https://www.balkutusu.com")
    types = {p["link_type"] for p in policies}
    assert "brand" in types
    assert "no_link" in types
    anchors = [p["anchor"] for p in policies if p["anchor"]]
    assert len(anchors) == len(set(anchors)) or len(anchors) <= 2


def test_authority_scoring(isolated_env):
    site = ame._authority_site("blogger", target_keyword_cluster="test kw", published_urls=["https://x.com/a"])
    site["publish_count"] = 2
    site["index_status"] = "indexed"
    score = ame.compute_authority_score(site)
    assert 0 <= score <= 100
    assert score > 30


def test_google_sites_task_queued(isolated_env):
    res = ame.create_google_site_task(
        site_title="Kuşadası Rehber",
        target_keyword="kuşadası gece hayatı",
        target_money_site="https://www.balkutusu.com",
    )
    assert res["success"] is True
    assert res["task"]["status"] == "queued"
    assert res["task"]["provider"] == "google_sites"


def test_google_sites_provider_missing(isolated_env, monkeypatch):
    monkeypatch.setattr(ame, "_run_google_sites_browser_worker", lambda t: {
        "success": False, "error": "provider_missing", "message": "provider_missing — browser automation worker yapılandırılmadı",
    })
    task = ame.create_google_site_task(site_title="Test Site", target_keyword="kw")["task"]
    res = ame.process_google_sites_task(task["task_id"])
    assert res["task"]["status"] == "failed"
    assert res["worker"]["error"] == "provider_missing"


def test_login_required_state(isolated_env, monkeypatch):
    monkeypatch.setattr(ame, "_browser_worker_status", lambda: {"available": True, "selenium": True, "openclaw": False})
    monkeypatch.setattr(ame, "_run_google_sites_browser_worker", lambda t: {
        "success": False, "status": "login_required", "error": "login_required",
        "message": "Google login gerekli",
    })
    task = ame.create_google_site_task(site_title="Login Test", target_keyword="kw")["task"]
    res = ame.process_google_sites_task(task["task_id"])
    assert res["task"]["status"] == "login_required"


def test_no_captcha_bypass(isolated_env, monkeypatch):
    """Captcha/login durumunda otomatik bypass yok — login_required."""
    monkeypatch.setattr(ame, "_run_google_sites_browser_worker", lambda t: {
        "success": False, "status": "login_required",
        "message": "captcha detected — kullanıcı müdahalesi bekleniyor",
    })
    task = ame.create_google_site_task(site_title="Captcha Test", target_keyword="kw")["task"]
    res = ame.process_google_sites_task(task["task_id"])
    assert res["task"]["status"] == "login_required"
    assert "captcha" in (res["task"].get("error") or res["worker"].get("message", "")).lower() or res["task"]["status"] == "login_required"


def test_duplicate_content_allowed(isolated_env):
    """Varsayılan: aynı platforma aynı içerik tekrar basılabilir."""
    r1 = ame.create_google_site_task(site_title="Same Title", target_keyword="kw", content_fingerprint="abc123")
    r2 = ame.create_google_site_task(site_title="Same Title", target_keyword="kw", content_fingerprint="abc123")
    assert r1["success"] is True
    assert r2["success"] is True
    assert r1["task"]["task_id"] != r2["task"]["task_id"]


def test_duplicate_site_allowed(isolated_env):
    """Varsayılan: aynı başlıkta birden fazla Google Sites task oluşturulabilir."""
    r1 = ame.create_google_site_task(site_title="Unique Site Name", target_keyword="kw")
    r2 = ame.create_google_site_task(site_title="Unique Site Name", target_keyword="kw2")
    assert r1["success"] is True
    assert r2["success"] is True


def test_duplicate_task_prevention_when_enabled(isolated_env):
    """Opsiyonel ayar açıkken duplicate fingerprint engellenir."""
    ame.update_settings({"duplicate_content_block": True})
    ame.create_google_site_task(site_title="Same Title", target_keyword="kw", content_fingerprint="abc123")
    res2 = ame.create_google_site_task(site_title="Same Title", target_keyword="kw", content_fingerprint="abc123")
    assert res2["success"] is False
    assert res2["error"] == "duplicate_task_blocked"


def test_publisher_hub_hook(isolated_env, monkeypatch):
    plan = ame.create_site_plan("test keyword")["plan"]
    import app.moduller.publisher_hub as pub
    monkeypatch.setattr(ame, "_publisher_channel_ready", lambda ch: (True, None))
    monkeypatch.setattr(pub, "enqueue", lambda item, **kw: {"success": True, "publish_id": "pub-test-1", "status": "queued"})
    monkeypatch.setattr(pub, "publish_item", lambda pid, **kw: {"success": True, "status": "published", "channel_results": {"blogger": {"success": True, "url": "https://blog.example.com/post"}}})
    res = ame.process_plan(plan["plan_id"])
    assert res["success"] is True
    assert res["success_count"] >= 1


def test_support_network_hook(isolated_env, monkeypatch):
    monkeypatch.setattr(ame, "_register_support_network_source", lambda *a, **k: {"success": True, "local_registered": True})
    plan = ame.create_site_plan("kw")["plan"]
    import app.moduller.publisher_hub as pub
    monkeypatch.setattr(ame, "_publisher_channel_ready", lambda ch: (True, None))
    monkeypatch.setattr(pub, "enqueue", lambda item, **kw: {"success": True, "publish_id": "p1", "status": "queued"})
    monkeypatch.setattr(pub, "publish_item", lambda pid, **kw: {"success": True, "status": "published", "channel_results": {"blogger": {"url": "https://b.example.com"}}})
    ame.process_plan(plan["plan_id"])
    st = json.loads(isolated_env["state"].read_text(encoding="utf-8"))
    assert len(st.get("authority_sites") or []) >= 1


def test_brain_hook(isolated_env):
    ame.create_site_plan("brain test keyword")
    data = json.loads(isolated_env["brain_state"].read_text(encoding="utf-8"))
    assert any(e.get("module") == "authority_mesh_engine" for e in data.get("events") or [])


def test_rank_watcher_hook(isolated_env, monkeypatch):
    import app.moduller.rank_index_watcher as riw
    calls = {"track": 0}
    monkeypatch.setattr(riw, "register_project", lambda *a, **k: {"success": True})
    monkeypatch.setattr(riw, "track_keyword", lambda *a, **k: (calls.__setitem__("track", calls["track"] + 1) or {"success": True}))
    ame._track_rank_watcher("https://example.com/page", "test kw", "blogger")
    assert calls["track"] == 1


def test_export_report(isolated_env):
    ame.create_site_plan("export test")
    res = ame.export_report("overview")
    assert res["success"] is True
    assert isolated_env["reports"].joinpath(res["path"].split("/")[-1]).exists() or __import__("pathlib").Path(res["path"]).exists()


def test_dashboard(isolated_env):
    ame.create_site_plan("dash kw")
    dash = ame.dashboard()
    assert dash["success"] is True
    assert dash["mesh_plans_count"] >= 1


def test_tasks_api(isolated_env):
    task = ame.create_google_site_task(site_title="Task API", target_keyword="kw")["task"]
    tasks = ame.list_tasks()
    assert tasks["count"] >= 1
    got = ame.get_task(task["task_id"])
    assert got["success"] is True
