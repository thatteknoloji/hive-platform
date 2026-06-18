"""Publisher Hub V1 — orchestration tests."""

import json
from unittest.mock import patch

import pytest

from app.moduller import publisher_hub as ph


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    state = tmp_path / "publisher_hub_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    gate_state = tmp_path / "seo_quality_gate_state.json"
    gate_state.write_text(json.dumps({"reports": {}}), encoding="utf-8")
    monkeypatch.setattr(ph, "STATE_FILE", state)
    monkeypatch.setattr(ph, "REPORTS_DIR", reports)
    state.write_text(json.dumps({
        "settings": dict(ph.DEFAULT_SETTINGS),
        "queue": [],
        "drafts": [],
        "published": [],
        "jobs": {},
        "running_job": "",
        "channel_stats": {},
        "network_dispatch": [],
    }), encoding="utf-8")
    yield state


def test_health():
    h = ph.health()
    assert h["success"] is True
    assert h["min_quality_score"] == 85
    assert h["channels_total"] == 10


def test_list_channels():
    channels = ph.list_channels()
    assert len(channels) == 10
    ids = {c["id"] for c in channels}
    assert "wordpress" in ids
    assert "medium" in ids


def test_enqueue_quality_fail():
    with patch.object(ph, "_quality_check", return_value={
        "passed": False, "score": 60, "min_required": 85, "publisher_hub_allowed": False, "analysis": {},
    }):
        res = ph.enqueue({
            "title": "Test",
            "content_html": "<p>zayıf</p>",
            "keyword": "test",
        }, channels=["wordpress"])
    assert res["status"] == "review_required"
    drafts = ph.get_drafts()
    assert drafts["count"] == 1


def test_enqueue_and_publish_wordpress():
    with patch.object(ph, "_quality_check", return_value={
        "passed": True, "score": 90, "min_required": 85, "publisher_hub_allowed": True, "analysis": {},
    }), patch.object(ph, "_publish_to_channel", return_value={
        "success": True, "post_id": 42, "url": "https://example.com/post",
    }):
        enq = ph.enqueue({
            "title": "Kuşadası Rehber",
            "content_html": "<p>Güçlü içerik</p>" * 30,
            "keyword": "kuşadası",
            "source": "astro_factory",
            "source_id": "p1:home",
        }, channels=["wordpress"])
        assert enq["success"] is True
        pub = ph.publish_item(enq["publish_id"])
        assert pub["success"] is True
        assert pub["status"] == "published"
    published = ph.get_published()
    assert published["count"] >= 1


def test_draft_channel_review_required():
    ph.update_settings({"channels": {"medium": True}})
    with patch.object(ph, "_quality_check", return_value={
        "passed": True, "score": 88, "min_required": 85, "publisher_hub_allowed": True, "analysis": {},
    }), patch.object(ph, "_publish_to_channel", return_value={
        "success": True, "draft": True, "review_required": True, "channel": "medium",
    }):
        enq = ph.enqueue({
            "title": "Medium Post",
            "content_html": "<p>İçerik</p>",
            "keyword": "seo",
        }, channels=["medium"])
        pub = ph.publish_item(enq["publish_id"])
    assert pub["status"] == "review_required"


def test_scan_sources_empty():
    with patch.dict(ph.SOURCE_SCANNERS, {k: lambda: [] for k in ph.SOURCE_SCANNERS}):
        res = ph.scan_sources()
    assert res["success"] is True
    assert res["count"] == 0


def test_approve_draft():
    st = ph._load_state()
    st["drafts"] = [{
        "publish_id": "pub-test1",
        "title": "Taslak",
        "content_html": "<p>x</p>",
        "channels": ["wordpress"],
        "status": "review_required",
    }]
    ph._save_state(st)
    res = ph.approve_draft("pub-test1")
    assert res["success"] is True
    assert ph.get_queue()["count"] == 1
    assert ph.get_drafts()["count"] == 0


def test_export_report(isolated_state):
    res = ph.export_report()
    assert res["success"] is True
    assert isolated_state.parent.joinpath(res["path"].split("/")[-1]).exists() or __import__("pathlib").Path(res["path"]).is_file()


def test_default_channels_new_install(tmp_path, monkeypatch):
    state = tmp_path / "publisher_hub_state.json"
    monkeypatch.setattr(ph, "STATE_FILE", state)
    loaded = ph._load_state()
    ch = loaded["settings"]["channels"]
    for cid in ("wordpress", "tumblr", "devto"):
        assert ch[cid] is True, f"{cid} yeni kurulumda aktif olmalı"
    assert ch["ghost"] is False
    assert ch["medium"] is False


def test_default_channels_include_blogger_when_connected(monkeypatch):
    with patch("app.moduller.blogger_api.is_configured", return_value=True), patch(
        "app.moduller.blogger_api.get_status", return_value={"connected": True}
    ):
        ch = ph._default_channels()
    assert ch["blogger"] is True
    assert ch["wordpress"] is True
    assert ch["tumblr"] is True
    assert ch["devto"] is True


def test_existing_channel_settings_preserved(tmp_path, monkeypatch):
    state = tmp_path / "publisher_hub_state.json"
    monkeypatch.setattr(ph, "STATE_FILE", state)
    state.write_text(json.dumps({
        "settings": {
            **dict(ph.DEFAULT_SETTINGS),
            "channels": {
                "wordpress": True,
                "ghost": False,
                "hashnode": False,
                "devto": False,
                "medium": False,
                "linkedin": False,
                "quora": False,
                "tumblr": False,
                "blogger": False,
                "google_sites": False,
            },
        },
        "queue": [],
        "drafts": [],
        "published": [],
        "jobs": {},
        "running_job": "",
        "channel_stats": {},
        "network_dispatch": [],
    }), encoding="utf-8")
    ch = ph.get_settings()["channels"]
    assert ch["blogger"] is False
    assert ch["devto"] is False
    assert ch["tumblr"] is False
    assert ch["wordpress"] is True
