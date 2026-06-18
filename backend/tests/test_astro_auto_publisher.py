"""Astro Auto Publisher testleri."""

import json
from unittest.mock import patch

import pytest

from app.moduller import astro_auto_publisher as aap


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "astro_auto_publisher_state.json"
    state.write_text(json.dumps({
        "settings": dict(aap.DEFAULT_SETTINGS),
        "queue": [],
        "jobs": {},
        "running_job": "",
    }), encoding="utf-8")
    monkeypatch.setattr(aap, "STATE_FILE", state)
    monkeypatch.setattr(aap, "REPORTS_DIR", tmp_path / "reports")
    yield {"state": state, "reports": tmp_path / "reports"}


def test_health(isolated_env):
    h = aap.health()
    assert h["success"] is True
    assert h["settings"]["auto_deploy"] is False
    assert h["settings"]["enabled"] is False
    assert "dashboard" in h


def test_auto_deploy_false_default(isolated_env):
    s = aap.get_settings()
    assert s["auto_deploy"] is False
    assert s["enabled"] is False


def test_scheduler_settings_persist(isolated_env):
    res = aap.update_settings({"interval_minutes": 120, "min_quality_score": 80, "max_items_per_run": 25})
    assert res["success"] is True
    s = aap.get_settings()
    assert s["interval_minutes"] == 120
    assert s["min_quality_score"] == 80
    assert s["max_items_per_run"] == 25


def test_scan_missing(isolated_env, monkeypatch):
    monkeypatch.setattr(aap, "_get_project_paths", lambda pid: ({"slug": "test-site"}, isolated_env["state"].parent / "site"))
    monkeypatch.setattr(aap, "_read_astro_index", lambda pid: {})
    monkeypatch.setattr(aap, "scan_all_sources", lambda settings=None: [
        aap._normalize_item("page_hub", "1", "Test Page", "test-page", "<h1>Test</h1>", "landing"),
    ])
    monkeypatch.setattr(aap, "_run_quality_gate", lambda item, settings, **kw: {"passed": True, "score": 90, "report_id": "qg-1", "critical_count": 0})

    result = aap.scan_missing("proj-1")
    assert result["success"] is True
    assert len(result["missing"]) == 1
    assert result["synced"] == []


def test_outdated_detection(isolated_env, monkeypatch):
    item = aap._normalize_item("sss_automation", "s1", "FAQ", "faq-1", "<p>new content</p>", "faq")
    monkeypatch.setattr(aap, "_get_project_paths", lambda pid: ({"slug": "t"}, isolated_env["state"].parent / "site"))
    monkeypatch.setattr(aap, "_read_astro_index", lambda pid: {
        "faq-1": {"hash": "oldhash1234567890", "file": "faqs.json", "entry": {}},
    })
    monkeypatch.setattr(aap, "_run_quality_gate", lambda item, settings, **kw: {"passed": True, "score": 90, "report_id": "qg-1", "critical_count": 0})
    classified = aap._classify_items("proj-1", [item], aap.get_settings())
    assert len(classified["outdated"]) == 1
    assert classified["missing"] == []


def test_already_synced_detection(isolated_env, monkeypatch):
    item = aap._normalize_item("sss_automation", "s1", "FAQ", "faq-1", "<p>content</p>", "faq")
    monkeypatch.setattr(aap, "_get_project_paths", lambda pid: ({"slug": "t"}, isolated_env["state"].parent / "site"))
    monkeypatch.setattr(aap, "_read_astro_index", lambda pid: {
        "faq-1": {"hash": item["content_hash"], "file": "faqs.json", "entry": {}},
    })
    classified = aap._classify_items("proj-1", [item], aap.get_settings())
    assert len(classified["synced"]) == 1
    assert classified["missing"] == []


def test_queue_missing(isolated_env, monkeypatch):
    monkeypatch.setattr(aap, "scan_missing", lambda pid, **kw: {
        "success": True,
        "missing": [aap._normalize_item("place_seo_pipeline", "j1:p1", "Geo", "geo-page", "<h1>G</h1>", "geo")],
        "outdated": [],
    })
    res = aap.queue_missing("proj-1")
    assert res["success"] is True
    assert res["queued"] == 1
    q = aap.get_queue()
    assert q["count"] == 1
    assert q["queue"][0]["queue_id"]
    assert q["queue"][0]["status"] == "queued"


def test_duplicate_queue_blocked(isolated_env, monkeypatch):
    item = aap._normalize_item("page_hub", "1", "T", "t", "<h1>T</h1>", "landing")
    monkeypatch.setattr(aap, "scan_missing", lambda pid, **kw: {"success": True, "missing": [item], "outdated": []})
    first = aap.queue_missing("proj-1")
    second = aap.queue_missing("proj-1")
    assert first["queued"] == 1
    assert second["queued"] == 0
    assert aap.get_queue()["count"] == 1


@patch("app.moduller.cloudflare_pages_deploy.deploy_to_cloudflare")
@patch("app.moduller.astro_factory.build_astro_project")
@patch("app.moduller.astro_factory.generate_pages")
def test_quality_gate_fail_blocks_deploy(mock_gen, mock_build, mock_deploy, isolated_env, monkeypatch, tmp_path):
    project_path = tmp_path / "site"
    (project_path / "src" / "data").mkdir(parents=True)
    monkeypatch.setattr(aap, "_get_project_paths", lambda pid: ({"slug": "test-site", "domain": "https://test.com"}, project_path))

    content_item = {
        "source": "page_hub", "source_id": "1", "title": "Low", "slug": "low-q",
        "content": "<p>bad</p>", "type": "landing", "target_keyword": "low",
        "content_hash": aap._content_hash("<p>bad</p>"),
    }
    st = aap._load_state()
    st["queue"] = [{
        "queue_id": "q-test1",
        "project_id": "proj-1",
        "content_item": content_item,
        "status": "queued",
        "created_at": "now",
    }]
    aap._save_state(st)

    monkeypatch.setattr(
        aap, "_run_quality_gate",
        lambda item, settings, **kw: {"passed": False, "score": 40, "report_id": "qg-fail", "critical_count": 1},
    )
    mock_build.return_value = {"success": True}
    mock_gen.return_value = {"success": True}

    result = aap.process_queue("proj-1", auto_deploy=True, auto_build=True)
    assert result["success"] is True
    assert result["summary"]["quality_failed"] == 1
    assert result["summary"]["deployed"] is False
    mock_deploy.assert_not_called()


@patch("app.moduller.astro_factory.generate_pages")
def test_process_queue_writes_real_astro_data(mock_gen, isolated_env, monkeypatch, tmp_path):
    project_path = tmp_path / "site"
    data_dir = project_path / "src" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "faqs.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(aap, "_get_project_paths", lambda pid: ({"slug": "test-site"}, project_path))
    mock_gen.return_value = {"success": True}

    content_item = {
        "source": "sss_automation", "source_id": "s1", "title": "FAQ Test", "slug": "faq-test",
        "content": "<h1>FAQ</h1><p>Real content here for testing sync engine.</p>",
        "type": "faq", "target_keyword": "faq test",
        "content_hash": aap._content_hash("<h1>FAQ</h1>"),
    }
    st = aap._load_state()
    st["queue"] = [{
        "queue_id": "q-test2",
        "project_id": "proj-1",
        "content_item": content_item,
        "status": "queued",
        "created_at": "now",
    }]
    aap._save_state(st)

    monkeypatch.setattr(
        aap, "_run_quality_gate",
        lambda item, settings, **kw: {"passed": True, "score": 90, "report_id": "qg-ok", "critical_count": 0},
    )
    with patch("app.moduller.astro_factory.build_astro_project", return_value={"success": True}):
        result = aap.process_queue("proj-1", auto_build=False, auto_deploy=False)

    assert result["summary"]["written"] == 1
    data = json.loads((data_dir / "faqs.json").read_text())
    assert any(x["slug"] == "faq-test" for x in data)


def test_sync_all_flow(isolated_env, monkeypatch):
    item = aap._normalize_item("page_hub", "1", "P", "p", "<h1>P</h1>", "landing")
    monkeypatch.setattr(aap, "_get_project_paths", lambda pid: ({"slug": "t"}, isolated_env["state"].parent / "site"))
    monkeypatch.setattr(aap, "scan_all_sources", lambda settings=None: [item])
    monkeypatch.setattr(aap, "_read_astro_index", lambda pid: {})
    monkeypatch.setattr(aap, "_run_quality_gate", lambda item, settings, **kw: {"passed": True, "score": 90, "report_id": "qg", "critical_count": 0})
    monkeypatch.setattr(aap, "_write_item_to_astro", lambda path, it: None)
    with patch("app.moduller.astro_factory.generate_pages", return_value={"success": True}), \
         patch("app.moduller.astro_factory.build_astro_project", return_value={"success": True}):
        result = aap.sync_all("proj-1", auto_deploy=False)
    assert result["success"] is True
    assert result["summary"]["missing"] == 1


def test_no_duplicate_jobs(isolated_env, monkeypatch):
    st = aap._load_state()
    st["running_job"] = "aap-existing"
    aap._save_state(st)
    job = aap._start_job("test", "proj-1")
    assert job is None


def test_path_traversal_guard():
    assert ".." not in aap._safe_slug("../../etc/passwd")
    assert aap._safe_slug("rehber/ex-club") == "rehber/ex-club"


def test_export_report(isolated_env):
    res = aap.export_report(project_id="proj-test")
    assert res["success"] is True
    assert isolated_env["reports"].exists()
    path = isolated_env["reports"] / "astro-auto-publisher-proj-test.json"
    assert path.exists()


def test_export_settings_get(isolated_env):
    res = aap.get_settings()
    assert "sources" in res
    assert "page_hub" in res["sources"]
    assert "sss_automation" in res["sources"]


def test_refresh_signals_on_queue(isolated_env, monkeypatch):
    item = aap._normalize_item("page_hub", "1", "Decay Page", "decay-page", "<h1>T</h1>", "landing")
    item["sync_status"] = "outdated"
    item["quality_score"] = 70
    signals = aap._refresh_signals_for_item(item, "proj-1")
    assert "refresh_priority" in signals
    assert "citation_loss" in signals
    assert "decay_detected" in signals
    assert signals["citation_loss"] > 0
    assert signals["refresh_priority"] >= 65


def test_ignore_warning_blocks_critical(isolated_env, monkeypatch):
    item = {"content": "<p>x</p>", "target_keyword": "x", "title": "x", "location": "Kuşadası"}
    monkeypatch.setattr(
        aap, "_run_quality_gate",
        lambda item, settings, **kw: {"passed": False, "score": 50, "critical_count": 2, "report_id": "qg-c"},
    )
    st = aap._load_state()
    st["queue"] = [{"queue_id": "q-crit", "content_item": item, "status": "quality_failed"}]
    aap._save_state(st)
    res = aap.ignore_queue_warning("q-crit")
    assert res["success"] is False
