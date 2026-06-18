"""Authority Factory V1 — üretim orkestrasyon testleri."""

import json

import pytest

from app.moduller import authority_factory as af


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "authority_factory_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")
    mesh_state = tmp_path / "authority_mesh_engine_state.json"
    mesh_state.write_text(json.dumps({
        "settings": {"enabled": True, "default_money_site": "https://www.balkutusu.com"},
        "authority_sites": [], "mesh_plans": [], "tasks": [], "google_sites_tasks": [],
        "link_policies": [], "support_network_sources": [], "history": [],
    }), encoding="utf-8")

    monkeypatch.setattr(af, "STATE_FILE", state)
    monkeypatch.setattr(af, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)
    import app.moduller.authority_mesh_engine as ame
    monkeypatch.setattr(ame, "STATE_FILE", mesh_state)

    state.write_text(json.dumps({
        "settings": {**af.DEFAULT_SETTINGS, "enabled": True},
        "batches": [],
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state}


def test_health(isolated_env):
    h = af.health()
    assert h["success"] is True
    assert h["module"] == "authority_factory"
    assert "github_pages" in h["providers"]


def test_create_batch(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.create_site_plan",
        lambda kw, **kwargs: {
            "success": True,
            "plan": {
                "plan_id": "ame-plan-test",
                "keyword": kw,
                "items": [
                    {"provider": "blogger", "provider_type": "api", "title": f"{kw} — Blogger", "role": "blog_hub", "link_policy": {"link_type": "brand"}},
                    {"provider": "github_pages", "provider_type": "api", "title": f"{kw} — GitHub", "role": "support_hub", "link_policy": {"link_type": "no_link"}},
                ],
            },
        },
    )
    res = af.create_batch("kuşadası gece hayatı", money_site="https://www.balkutusu.com")
    assert res["success"] is True
    batch = res["batch"]
    assert batch["batch_id"].startswith("af-")
    assert batch["target_keyword"] == "kuşadası gece hayatı"
    assert len(batch["items"]) >= 2
    assert batch["status"] == "queued"


def test_duplicate_control(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.create_site_plan",
        lambda kw, **kwargs: {
            "success": True,
            "plan": {
                "plan_id": "p1",
                "keyword": kw,
                "items": [{"provider": "blogger", "provider_type": "api", "title": "dup title", "role": "blog_hub", "link_policy": {}}],
            },
        },
    )
    r1 = af.create_batch("test kw")
    assert r1["success"] is True
    r2 = af.create_batch("test kw")
    assert r2["success"] is False
    assert "duplicate" in r2.get("error", "").lower() or r2.get("warnings")


def test_link_policy_validation(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.generate_link_policy",
        lambda kw, money, **kwargs: [
            {"anchor": kw, "target_url": money, "link_type": "partial"},
            {"anchor": kw, "target_url": money, "link_type": "partial"},
            {"anchor": kw, "target_url": money, "link_type": "partial"},
        ],
    )
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.create_site_plan",
        lambda kw, **kwargs: {
            "success": True,
            "plan": {"plan_id": "p1", "keyword": kw, "items": [
                {"provider": "blogger", "provider_type": "api", "title": "t1", "role": "blog_hub", "link_policy": {}},
            ]},
        },
    )
    res = af.create_batch("exact match keyword")
    assert res["success"] is True
    assert res["link_policy_check"]["exact_ratio"] > 0.15
    assert any("exact_anchor" in w for w in (res.get("warnings") or []))


def test_process_github_pages_item(isolated_env, monkeypatch):
    af.update_settings({"allow_github_pages": True})
    batch = af.create_batch("gh kw", factory_counts={"github_pages": 1, "blogger": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    assert batch["success"] is True
    bid = batch["batch"]["batch_id"]

    monkeypatch.setattr("app.moduller.github_pages_worker.health", lambda: {"provider_ready": True})
    monkeypatch.setattr(
        "app.moduller.github_pages_worker.create_site_from_mesh_item",
        lambda **kw: {"success": True, "site": {"status": "published", "pages_url": "https://user.github.io/test"}},
    )
    monkeypatch.setattr(af, "_register_support_network", lambda *a, **k: {"success": True})
    monkeypatch.setattr(af, "_track_rank_watcher", lambda *a, **k: {"success": True})

    res = af.process_batch(bid)
    assert res["success"] is True
    item = res["batch"]["items"][0]
    assert item["status"] == "published"
    assert "github.io" in item["result_url"]


def test_process_google_sites_item(isolated_env, monkeypatch):
    af.update_settings({"allow_google_sites": True})
    batch = af.create_batch("gs kw", factory_counts={"google_sites": 1, "github_pages": 0, "blogger": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    bid = batch["batch"]["batch_id"]

    monkeypatch.setattr("app.moduller.google_sites_worker.health", lambda: {"provider_ready": True})
    monkeypatch.setattr(
        "app.moduller.google_sites_worker.create_task_from_mesh_item",
        lambda **kw: {"success": True, "task": {"task_id": "gs-task-1", "status": "queued"}},
    )
    monkeypatch.setattr(
        "app.moduller.google_sites_worker.process_task",
        lambda tid, **kw: {"success": True, "task": {"task_id": tid, "status": "published", "published_url": "https://sites.google.com/view/test"}},
    )
    monkeypatch.setattr(af, "_register_support_network", lambda *a, **k: {"success": True})
    monkeypatch.setattr(af, "_track_rank_watcher", lambda *a, **k: {"success": True})

    res = af.process_batch(bid)
    assert res["batch"]["items"][0]["status"] == "published"


def test_process_publisher_item(isolated_env, monkeypatch):
    batch = af.create_batch("pub kw", factory_counts={"blogger": 1, "github_pages": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    bid = batch["batch"]["batch_id"]

    monkeypatch.setattr(af, "_publisher_ready", lambda ch: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda item: {"passed": True, "score": 90})
    monkeypatch.setattr("app.moduller.publisher_hub.enqueue", lambda item, **kw: {"success": True, "publish_id": "pub-1"})
    monkeypatch.setattr(
        "app.moduller.publisher_hub.publish_item",
        lambda pid, **kw: {"success": True, "status": "published", "channel_results": {"blogger": {"success": True, "url": "https://blog.example.com/p"}}},
    )
    monkeypatch.setattr(af, "_register_support_network", lambda *a, **k: {"success": True})
    monkeypatch.setattr(af, "_track_rank_watcher", lambda *a, **k: {"success": True})

    res = af.process_batch(bid)
    assert res["batch"]["items"][0]["status"] == "published"


def test_provider_missing(isolated_env, monkeypatch):
    af.update_settings({"allow_github_pages": True})
    batch = af.create_batch("pm kw", factory_counts={"github_pages": 1, "blogger": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    monkeypatch.setattr("app.moduller.github_pages_worker.health", lambda: {"provider_ready": False, "error": "provider_missing"})
    res = af.process_batch(batch["batch"]["batch_id"])
    assert res["batch"]["items"][0]["status"] == "provider_missing"


def test_login_required(isolated_env, monkeypatch):
    af.update_settings({"allow_google_sites": True})
    batch = af.create_batch("login kw", factory_counts={"google_sites": 1, "github_pages": 0, "blogger": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    monkeypatch.setattr("app.moduller.google_sites_worker.health", lambda: {"provider_ready": True})
    monkeypatch.setattr(
        "app.moduller.google_sites_worker.create_task_from_mesh_item",
        lambda **kw: {"success": True, "task": {"task_id": "gs-1"}},
    )
    monkeypatch.setattr(
        "app.moduller.google_sites_worker.process_task",
        lambda tid, **kw: {"success": False, "task": {"task_id": tid, "status": "login_required", "error": "login_required"}},
    )
    res = af.process_batch(batch["batch"]["batch_id"])
    assert res["batch"]["items"][0]["status"] == "login_required"


def test_brain_hook(isolated_env, monkeypatch):
    events = []
    import app.moduller.hive_brain_engine as brain

    def capture(event_type, module, **kwargs):
        events.append({"event_type": event_type, "module": module, **kwargs})
        return {"success": True}

    monkeypatch.setattr(brain, "record_event", capture)
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.create_site_plan",
        lambda kw, **kwargs: {"success": True, "plan": {"plan_id": "p", "keyword": kw, "items": [
            {"provider": "medium", "provider_type": "browser", "title": "t", "role": "blog_hub", "link_policy": {}},
        ]}},
    )
    af.create_batch("brain kw")
    assert any(e["event_type"] == "authority_factory_batch_created" for e in events)


def test_mission_control_payload(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.create_site_plan",
        lambda kw, **kwargs: {"success": True, "plan": {"plan_id": "p", "keyword": kw, "items": [
            {"provider": "quora", "provider_type": "browser", "title": "t", "role": "blog_hub", "link_policy": {}},
        ]}},
    )
    af.create_batch("mc kw")
    payload = af.mission_control_payload()
    assert payload["success"] is True
    assert payload["factory_batches"] >= 1


def test_action_orchestrator_import(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.create_site_plan",
        lambda kw, **kwargs: {"success": True, "plan": {"plan_id": "p", "keyword": kw, "items": [
            {"provider": "github_pages", "provider_type": "api", "title": "gh", "role": "support_hub", "link_policy": {}},
        ]}},
    )
    action = {"action_type": "github_page", "keyword": "ao kw", "payload": {"count": 1}}
    res = af.create_batch_from_orchestrator(action)
    assert res["success"] is True
    assert res["batch"]["source"] == "action_orchestrator"


def test_support_network_hook(isolated_env, monkeypatch):
    calls = []
    monkeypatch.setattr(af, "_register_support_network", lambda url, role, net, kw: calls.append(url) or {"success": True})
    af.update_settings({"allow_github_pages": True})
    batch = af.create_batch("sn kw", factory_counts={"github_pages": 1, "blogger": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    monkeypatch.setattr("app.moduller.github_pages_worker.health", lambda: {"provider_ready": True})
    monkeypatch.setattr(
        "app.moduller.github_pages_worker.create_site_from_mesh_item",
        lambda **kw: {"success": True, "site": {"status": "published", "pages_url": "https://x.github.io/s"}},
    )
    monkeypatch.setattr(af, "_track_rank_watcher", lambda *a, **k: {"success": True})
    af.process_batch(batch["batch"]["batch_id"])
    assert len(calls) == 1


def test_rank_watcher_hook(isolated_env, monkeypatch):
    calls = []
    monkeypatch.setattr(af, "_track_rank_watcher", lambda url, kw, p: calls.append((url, kw)) or {"success": True})
    monkeypatch.setattr(af, "_register_support_network", lambda *a, **k: {"success": True})
    af.update_settings({"allow_github_pages": True})
    batch = af.create_batch("rw kw", factory_counts={"github_pages": 1, "blogger": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    monkeypatch.setattr("app.moduller.github_pages_worker.health", lambda: {"provider_ready": True})
    monkeypatch.setattr(
        "app.moduller.github_pages_worker.create_site_from_mesh_item",
        lambda **kw: {"success": True, "site": {"status": "published", "pages_url": "https://y.github.io/r"}},
    )
    af.process_batch(batch["batch"]["batch_id"])
    assert len(calls) == 1
    assert calls[0][0].startswith("https://")


def test_export_report(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.create_site_plan",
        lambda kw, **kwargs: {"success": True, "plan": {"plan_id": "p", "keyword": kw, "items": [
            {"provider": "medium", "provider_type": "browser", "title": "t", "role": "blog_hub", "link_policy": {}},
        ]}},
    )
    res = af.export_report("overview")
    assert res["success"] is True
    assert res["path"]
