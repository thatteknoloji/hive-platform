"""Authority Factory V2 — dataset / domain / campaign entegrasyon testleri."""

from __future__ import annotations

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
    dm_state = tmp_path / "data_miner_engine_state.json"
    dm_state.write_text(json.dumps({
        "settings": {},
        "jobs": {
            "dm-job-1": {
                "job_id": "dm-job-1",
                "job_type": "url",
                "source": "https://club.com",
                "status": "completed",
                "created_at": "2026-01-01",
                "result": {
                    "entities": [{"label": "Club", "type": "LocalBusiness"}],
                    "faqs": [{"question": "Hours?", "answer": "24/7"}],
                    "keyword": "kuşadası gece hayatı",
                },
            }
        },
        "datasets": [{"id": "dm-job-1", "type": "url", "source": "https://club.com", "entity_count": 1, "faq_count": 1}],
    }), encoding="utf-8")

    monkeypatch.setattr(af, "STATE_FILE", state)
    monkeypatch.setattr(af, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)
    import app.moduller.authority_mesh_engine as ame
    monkeypatch.setattr(ame, "STATE_FILE", mesh_state)
    import app.moduller.data_miner_engine as dm
    monkeypatch.setattr(dm, "STATE_FILE", dm_state)

    state.write_text(json.dumps({
        "settings": {**af.DEFAULT_SETTINGS, "enabled": True},
        "batches": [],
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "dm_state": dm_state}


def _mock_mesh(monkeypatch):
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.generate_link_policy",
        lambda kw, money, **kwargs: [{"anchor": "brand", "target_url": money, "link_type": "brand"}],
    )


def test_provider_mix_generation():
    res = af.generate_provider_mix()
    assert res["success"] is True
    assert res["provider_mix"]["tumblr"] == 5
    assert res["total_items"] == sum(res["provider_mix"].values())


def test_provider_mix_overrides():
    res = af.generate_provider_mix({"blogger": 1, "tumblr": 0})
    assert res["provider_mix"]["blogger"] == 1
    assert res["provider_mix"]["tumblr"] == 0


def test_get_provider_mix_endpoint_shape():
    res = af.get_provider_mix()
    assert "provider_mix" in res
    assert "defaults" in res


def test_create_from_dataset(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    res = af.create_from_dataset("dm-job-1")
    assert res["success"] is True
    batch = res["batch"]
    assert batch["batch_id"].startswith("af2-")
    assert batch["source"] == "data_miner"
    assert batch["dataset_id"] == "dm-job-1"
    assert batch["entity_count"] >= 1
    assert batch["faq_count"] >= 1
    assert all(it["item_id"].startswith("afi2-") for it in batch["items"])


def test_create_from_dataset_not_found(isolated_env):
    res = af.create_from_dataset("missing-id")
    assert res["success"] is False


def test_domain_score_filter():
    scores = [
        {"domain": "good.com", "overall_domain_score": 80, "spam_risk_score": 20},
        {"domain": "bad.com", "overall_domain_score": 40, "spam_risk_score": 10},
        {"domain": "spam.com", "overall_domain_score": 90, "spam_risk_score": 80},
    ]
    filtered = af._filter_domain_candidates(scores)
    assert len(filtered) == 1
    assert filtered[0]["domain"] == "good.com"


def test_spam_risk_filter():
    scores = [{"domain": "x.com", "overall_domain_score": 70, "spam_risk_score": 55}]
    assert af._filter_domain_candidates(scores) == []


def test_list_domain_candidates(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.expireddomain.list_scores",
        lambda: {"success": True, "scores": [
            {"domain": "a.com", "overall_domain_score": 70, "spam_risk_score": 30},
            {"domain": "b.com", "overall_domain_score": 50, "spam_risk_score": 10},
        ]},
    )
    res = af.list_domain_candidates()
    assert res["success"] is True
    assert res["count"] == 1
    assert res["candidates"][0]["domain"] == "a.com"


def test_create_from_domain_candidates(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    monkeypatch.setattr(
        "app.moduller.expireddomain.list_scores",
        lambda: {"success": True, "scores": [
            {"domain": "authority.com", "overall_domain_score": 72, "spam_risk_score": 25},
        ]},
    )
    res = af.create_from_domain_candidates(keyword="authority niche")
    assert res["success"] is True
    assert res["batch"]["source"] == "domain_intelligence"
    assert len(res["batch"]["domain_candidates"]) == 1


def test_create_from_campaign(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    monkeypatch.setattr(
        "app.moduller.campaign_engine.get_campaign",
        lambda cid: {
            "success": True,
            "campaign": {
                "campaign_id": cid,
                "target_keyword": "campaign kw",
                "target_domain": "https://money.com",
                "tasks": [
                    {"task_id": "ct-1", "item_type": "authority_source", "title": "Auth batch", "module": "authority_factory"},
                    {"task_id": "ct-2", "item_type": "publisher_content", "title": "Pub content"},
                ],
            },
        },
    )
    monkeypatch.setattr("app.moduller.campaign_engine.update_task_factory_status", lambda tid, st: {"success": True})
    res = af.create_from_campaign("camp-1")
    assert res["success"] is True
    assert res["batch"]["source"] == "campaign"
    assert res["batch"]["campaign_id"] == "camp-1"
    assert len(res["batch"]["items"]) == 2


def test_validate_batch_ok(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    created = af.create_from_dataset(
        "dm-job-1",
        provider_mix={"blogger": 1, "tumblr": 1, "github_pages": 0, "google_sites": 0, "devto": 0, "wordpress": 0, "astro": 0},
    )
    val = af.validate_batch(created["batch"]["batch_id"])
    assert val["success"] is True
    assert val["valid"] is True


def test_validate_batch_not_found(isolated_env):
    res = af.validate_batch("af2-missing")
    assert res["success"] is False


def test_process_github_pages_item_v2(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    af.update_settings({"allow_github_pages": True})
    created = af.create_from_dataset("dm-job-1", provider_mix={"github_pages": 1, "google_sites": 0, "blogger": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    item_id = created["batch"]["items"][0]["item_id"]
    monkeypatch.setattr("app.moduller.github_pages_worker.health", lambda: {"provider_ready": True})
    monkeypatch.setattr(
        "app.moduller.github_pages_worker.create_site_from_mesh_item",
        lambda **kw: {"success": True, "site": {"status": "published", "pages_url": "https://u.github.io/p"}},
    )
    monkeypatch.setattr(af, "_register_support_network", lambda *a, **k: {"success": True})
    monkeypatch.setattr(af, "_track_rank_watcher", lambda *a, **k: {"success": True})
    res = af.process_item(item_id)
    assert res["item"]["status"] == "published"
    assert "github.io" in res["item"]["result_url"]


def test_process_google_sites_item_v2(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    af.update_settings({"allow_google_sites": True})
    created = af.create_from_dataset("dm-job-1", provider_mix={"google_sites": 1, "github_pages": 0, "blogger": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    item_id = created["batch"]["items"][0]["item_id"]
    monkeypatch.setattr("app.moduller.google_sites_worker.health", lambda: {"provider_ready": True})
    monkeypatch.setattr(
        "app.moduller.google_sites_worker.create_task_from_mesh_item",
        lambda **kw: {"success": True, "task": {"task_id": "gs-1"}},
    )
    monkeypatch.setattr(
        "app.moduller.google_sites_worker.process_task",
        lambda tid, **kw: {"success": True, "task": {"task_id": tid, "status": "published", "published_url": "https://sites.google.com/x"}},
    )
    monkeypatch.setattr(af, "_register_support_network", lambda *a, **k: {"success": True})
    monkeypatch.setattr(af, "_track_rank_watcher", lambda *a, **k: {"success": True})
    res = af.process_item(item_id)
    assert res["item"]["status"] == "published"


def test_process_publisher_item_v2(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    created = af.create_from_dataset("dm-job-1", provider_mix={"blogger": 1, "github_pages": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    item_id = created["batch"]["items"][0]["item_id"]
    monkeypatch.setattr(af, "_publisher_ready", lambda ch: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda item: {"passed": True, "score": 90})
    monkeypatch.setattr("app.moduller.publisher_hub.enqueue", lambda item, **kw: {"success": True, "publish_id": "p1"})
    monkeypatch.setattr(af, "_register_support_network", lambda *a, **k: {"success": True})
    monkeypatch.setattr(af, "_track_rank_watcher", lambda *a, **k: {"success": True})
    res = af.process_item(item_id)
    assert res["item"]["status"] == "queued"
    assert res["item"].get("metadata", {}).get("queue_id") == "p1"


def test_login_required_v2(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    af.update_settings({"allow_google_sites": True})
    created = af.create_from_dataset("dm-job-1", provider_mix={"google_sites": 1, "github_pages": 0, "blogger": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    item_id = created["batch"]["items"][0]["item_id"]
    monkeypatch.setattr("app.moduller.google_sites_worker.health", lambda: {"provider_ready": True})
    monkeypatch.setattr(
        "app.moduller.google_sites_worker.create_task_from_mesh_item",
        lambda **kw: {"success": True, "task": {"task_id": "gs-1"}},
    )
    monkeypatch.setattr(
        "app.moduller.google_sites_worker.process_task",
        lambda tid, **kw: {"success": False, "task": {"task_id": tid, "status": "login_required"}},
    )
    res = af.process_item(item_id)
    assert res["item"]["status"] == "login_required"


def test_provider_missing_v2(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    af.update_settings({"allow_github_pages": True})
    created = af.create_from_dataset("dm-job-1", provider_mix={"github_pages": 1, "blogger": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    item_id = created["batch"]["items"][0]["item_id"]
    monkeypatch.setattr("app.moduller.github_pages_worker.health", lambda: {"provider_ready": False, "error": "provider_missing"})
    res = af.process_item(item_id)
    assert res["item"]["status"] == "provider_missing"


def test_quality_gate_review_required(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    monkeypatch.setattr(af, "_compute_item_quality_score", lambda item, settings: 50)
    created = af.create_from_dataset("dm-job-1", provider_mix={"blogger": 1, "github_pages": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    item_id = created["batch"]["items"][0]["item_id"]
    monkeypatch.setattr(af, "_publisher_ready", lambda ch: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda item: {"passed": True, "score": 90})
    monkeypatch.setattr("app.moduller.publisher_hub.enqueue", lambda item, **kw: {"success": True, "publish_id": "p1"})
    res = af.process_item(item_id)
    assert res["item"]["status"] == "review_required"


def test_brain_hook_v2(isolated_env, monkeypatch):
    events = []
    import app.moduller.hive_brain_engine as brain

    def capture(et, module, **kwargs):
        events.append(et)

    monkeypatch.setattr(brain, "record_event", capture)
    _mock_mesh(monkeypatch)
    af.create_from_dataset("dm-job-1")
    assert "authority_factory_v2_batch_created" in events


def test_mission_control_payload(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    af.create_from_dataset("dm-job-1")
    mc = af.mission_control_payload()
    assert mc["authority_factory_v2_batches"] >= 1
    assert "processing_authority_items" in mc
    assert "executive" in mc


def test_executive_payload(isolated_env):
    ex = af.executive_payload()
    assert "authority_execution_score" in ex
    assert "authority_factory_risk" in ex
    assert "authority_growth_potential" in ex


def test_settings_safety(isolated_env):
    af.update_settings({"allow_google_sites": False, "allow_github_pages": False, "auto_process": False})
    s = af.get_settings()
    assert s["allow_google_sites"] is False
    assert s["max_items_per_batch"] == 25


def test_export_report(isolated_env):
    res = af.export_report("overview")
    assert res["success"] is True
    assert res["path"]


def test_no_fake_success_on_provider_missing(isolated_env, monkeypatch):
    _mock_mesh(monkeypatch)
    af.update_settings({"allow_github_pages": True})
    created = af.create_from_dataset("dm-job-1", provider_mix={"github_pages": 1, "blogger": 0, "google_sites": 0, "tumblr": 0, "devto": 0, "wordpress": 0, "astro": 0})
    monkeypatch.setattr("app.moduller.github_pages_worker.health", lambda: {"provider_ready": False})
    res = af.process_item(created["batch"]["items"][0]["item_id"])
    assert res["item"]["status"] != "published"
    assert res["item"]["result_url"] == ""


def test_v1_create_batch_still_works(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.authority_mesh_engine.create_site_plan",
        lambda kw, **kwargs: {
            "success": True,
            "plan": {
                "plan_id": "p1",
                "keyword": kw,
                "items": [{"provider": "blogger", "provider_type": "api", "title": "v1", "role": "blog_hub", "link_policy": {}}],
            },
        },
    )
    res = af.create_batch("v1 keyword")
    assert res["success"] is True
    assert res["batch"]["batch_id"].startswith("af-")


def test_list_datasets_for_factory(isolated_env):
    res = af.list_datasets_for_factory()
    assert res["success"] is True
    assert res["count"] >= 1
