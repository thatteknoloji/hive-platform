"""HIVE LIVE CHAIN UNBLOCK SPRINT V1 — canlı zincir kırıkları."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.moduller import authority_factory as af
from app.moduller import campaign_engine as ce
from app.moduller import google_sites_worker as gsw


SAMPLE_JOB = {
    "job_id": "dm-unblock12345",
    "job_type": "keyword",
    "status": "completed",
    "source": "kuşadası gece hayatı",
    "created_at": "2026-06-15 12:00:00 UTC",
    "result": {
        "entities": [
            {"label": "Marina Gece", "type": "heading"},
            {"label": "Liman Caddesi", "type": "heading"},
            {"label": "Bar Street", "type": "heading"},
        ],
        "faqs": [
            {"question": "Kuşadası gece hayatı nerede?", "answer": "Marina bölgesinde."},
            {"question": "Ne zaman açık?", "answer": "Yaz sezonu."},
            {"question": "Giriş ücreti var mı?", "answer": "Mekana göre değişir."},
        ],
        "categories": ["Bar", "Kulüp", "Marina"],
        "addresses": ["Marina Kuşadası", "Liman Caddesi"],
        "phones": ["+905551112233"],
        "emails": ["info@example.com"],
        "schema_types": ["FAQPage", "LocalBusiness"],
    },
}

SAMPLE_DATASETS = [
    {
        "id": "dm-unblock12345",
        "type": "keyword",
        "source": "kuşadası gece hayatı",
        "created_at": "2026-06-15 12:00:00 UTC",
        "entity_count": 3,
        "faq_count": 3,
    }
]

EXPECTED_TASK_TYPES = {
    "entity_page",
    "faq_page",
    "cluster",
    "geo_page",
    "authority_source",
    "support_site",
    "publisher_content",
    "citation_expansion",
}


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "campaign_engine_state.json"
    af_state = tmp_path / "authority_factory_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")
    dm_state = tmp_path / "data_miner_engine_state.json"
    dm_state.write_text(json.dumps({
        "settings": {},
        "jobs": {"dm-unblock12345": SAMPLE_JOB},
        "datasets": SAMPLE_DATASETS,
    }), encoding="utf-8")

    monkeypatch.setattr(ce, "STATE_FILE", state)
    monkeypatch.setattr(ce, "REPORTS_DIR", reports)
    monkeypatch.setattr(af, "STATE_FILE", af_state)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)
    import app.moduller.data_miner_engine as dme
    monkeypatch.setattr(dme, "STATE_FILE", dm_state)

    def _mock_safe_read(module, func, *args, default=None, **kwargs):
        if module == "authority_factory":
            import importlib
            mod = importlib.import_module(f"app.moduller.{module}")
            fn = getattr(mod, func)
            return fn(*args, **kwargs)
        return default if default is not None else {}

    monkeypatch.setattr(ce, "_safe_read", _mock_safe_read)
    monkeypatch.setattr(ce, "collect_sources", lambda **kwargs: {
        "opportunity": {}, "crawl_gap": {}, "citation": {}, "serp": {},
        "revenue": {}, "authority_factory": {}, "support_network": {}, "rank": {}, "executive": {},
    })

    state.write_text(json.dumps({
        "settings": {**ce.DEFAULT_SETTINGS, "enabled": True},
        "campaigns": [],
        "tasks": [],
        "history": [],
    }), encoding="utf-8")
    af_state.write_text(json.dumps({
        "settings": {**af.DEFAULT_SETTINGS, "enabled": True},
        "batches": [],
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "brain_state": brain_state, "af_state": af_state}


def _create_campaign_with_plan():
    created = ce.create_from_dataset(
        dataset_id="dm-unblock12345",
        primary_keyword="kuşadası gece hayatı",
        target_domain="https://www.balkutusu.com",
    )
    plan = ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    return created, plan


def test_generate_plan_not_blocked_by_blogger_invalid_grant(isolated_env, monkeypatch):
    monkeypatch.setattr(ce, "_collect_provider_warnings", lambda: ["blogger:provider_auth_failed:invalid_grant"])
    created, plan = _create_campaign_with_plan()
    assert plan["success"] is True
    assert plan["task_count"] > 0
    types = {t["item_type"] for t in plan["tasks"]}
    assert EXPECTED_TASK_TYPES.issubset(types)


def test_plan_generated_with_warnings(isolated_env, monkeypatch):
    monkeypatch.setattr(ce, "_collect_provider_warnings", lambda: ["blogger:provider_auth_failed:invalid_grant"])
    _, plan = _create_campaign_with_plan()
    assert plan["plan_status"] == "generated_with_warnings"
    assert any("invalid_grant" in w for w in plan.get("warnings") or [])


def test_dataset_entities_stored_in_campaign(isolated_env):
    created, _ = _create_campaign_with_plan()
    c = created["campaign"]
    assert len(c.get("dataset_entities") or []) == 3
    assert c.get("dataset_summary", {}).get("entity_count") == 3


def test_dataset_faqs_stored_in_campaign(isolated_env):
    created, _ = _create_campaign_with_plan()
    c = created["campaign"]
    assert len(c.get("dataset_faqs") or []) == 3
    assert c.get("dataset_summary", {}).get("faq_count") == 3


def test_task_payload_carries_entities(isolated_env):
    _, plan = _create_campaign_with_plan()
    auth_tasks = [t for t in plan["tasks"] if t["item_type"] == "authority_source"]
    assert auth_tasks
    payload = auth_tasks[0].get("payload") or {}
    assert len(payload.get("entities") or []) >= 3


def test_task_payload_carries_faqs(isolated_env):
    _, plan = _create_campaign_with_plan()
    auth_tasks = [t for t in plan["tasks"] if t["item_type"] == "authority_source"]
    assert auth_tasks
    payload = auth_tasks[0].get("payload") or {}
    assert len(payload.get("faqs") or []) >= 3


def test_authority_factory_item_receives_entities(isolated_env):
    created, _ = _create_campaign_with_plan()
    cid = created["campaign"]["campaign_id"]
    batch_res = ce.send_to_authority_factory(cid)
    assert batch_res["success"] is True
    items = (batch_res.get("batch") or {}).get("items") or []
    assert items
    assert len(items[0].get("entities") or []) >= 3


def test_authority_factory_item_receives_faqs(isolated_env):
    created, _ = _create_campaign_with_plan()
    cid = created["campaign"]["campaign_id"]
    batch_res = ce.send_to_authority_factory(cid)
    items = (batch_res.get("batch") or {}).get("items") or []
    assert items
    assert len(items[0].get("faqs") or []) >= 3


def test_preview_quality_at_least_85_with_dataset_entities_faqs(isolated_env, monkeypatch):
    created, _ = _create_campaign_with_plan()
    cid = created["campaign"]["campaign_id"]
    batch_res = ce.send_to_authority_factory(cid)
    items = (batch_res.get("batch") or {}).get("items") or []
    assert items
    item = max(items, key=lambda i: len(i.get("entities") or []) + len(i.get("faqs") or []))
    assert len(item.get("entities") or []) >= 1
    assert len(item.get("faqs") or []) >= 1
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda payload: {
        "passed": True, "score": 89, "analysis": {},
    })
    prev = af.preview_content(item["item_id"])
    assert prev["success"] is True
    assert prev["quality_score"] >= 85
    assert prev.get("entity_count", 0) >= 1
    assert prev.get("faq_count", 0) >= 1


def test_publisher_item_queues_when_quality_passes(isolated_env, monkeypatch):
    item = {
        "item_id": "afi2-queue-test",
        "provider": "blogger",
        "provider_type": "api",
        "role": "entity_hub",
        "title": "Kusadasi Authority Guide",
        "target_keyword": "kusadasi",
        "target_url": "https://www.balkutusu.com",
        "entities": SAMPLE_JOB["result"]["entities"],
        "faqs": SAMPLE_JOB["result"]["faqs"],
        "categories": ["Nightlife"],
        "status": "queued",
        "link_policy": {"link_type": "brand", "target_url": "https://www.balkutusu.com"},
    }
    batch = {"batch_id": "af2-q", "items": [item], "target_money_site": "https://www.balkutusu.com"}
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda payload: {
        "passed": True, "score": 90, "analysis": {},
    })
    monkeypatch.setattr("app.moduller.publisher_hub.enqueue", lambda payload: {
        "success": True, "publish_id": "q-live-unblock-001",
    })
    res = af._process_publisher_item(item, batch, af.DEFAULT_SETTINGS)
    assert res["success"] is True
    assert item["status"] == "queued"


def test_queue_id_stored_on_publisher_item(isolated_env, monkeypatch):
    item = {
        "item_id": "afi2-qid-test",
        "provider": "blogger",
        "provider_type": "api",
        "role": "entity_hub",
        "title": "Guide",
        "target_keyword": "kusadasi",
        "target_url": "https://www.balkutusu.com",
        "entities": SAMPLE_JOB["result"]["entities"],
        "faqs": SAMPLE_JOB["result"]["faqs"],
        "status": "queued",
        "link_policy": {"target_url": "https://www.balkutusu.com"},
    }
    batch = {"batch_id": "af2-qid", "items": [item]}
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda payload: {
        "passed": True, "score": 91, "analysis": {},
    })
    monkeypatch.setattr("app.moduller.publisher_hub.enqueue", lambda payload: {
        "success": True, "publish_id": "q-live-unblock-002",
    })
    af._process_publisher_item(item, batch, af.DEFAULT_SETTINGS)
    assert item.get("metadata", {}).get("queue_id") == "q-live-unblock-002"


def test_google_sites_health_checks_runtime_chromium(monkeypatch):
    monkeypatch.setattr(gsw, "_playwright_available", lambda: True)
    monkeypatch.setattr(gsw, "_chromium_executable_path", lambda: "/tmp/chromium-test")
    monkeypatch.setattr(gsw, "_chromium_installed", lambda: True)
    monkeypatch.setattr(gsw, "detect_browser_provider", lambda: {
        "ready": True,
        "provider": "playwright",
        "chromium_installed": True,
        "playwright": True,
    })
    h = gsw.health()
    assert h["playwright_installed"] is True
    assert h["chromium_installed"] is True
    assert h["ready"] is True
    assert "chromium_executable_path" in h


def test_campaign_dataset_plan_generated_event(isolated_env, monkeypatch):
    monkeypatch.setattr(ce, "_collect_provider_warnings", lambda: ["blogger:provider_auth_failed:invalid_grant"])
    events: list = []
    monkeypatch.setattr(ce, "_record_brain", lambda event, **kwargs: events.append((event, kwargs)))
    created = ce.create_from_dataset(
        dataset_id="dm-unblock12345",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    names = [e[0] for e in events]
    assert "campaign_dataset_plan_generated" in names


def test_campaign_sent_to_authority_factory_event(isolated_env, monkeypatch):
    events: list = []
    monkeypatch.setattr(ce, "_record_brain", lambda event, **kwargs: events.append((event, kwargs)))
    created, _ = _create_campaign_with_plan()
    ce.send_to_authority_factory(created["campaign"]["campaign_id"])
    names = [e[0] for e in events]
    assert "campaign_sent_to_authority_factory" in names


def test_provider_auth_failed_on_invalid_grant(isolated_env, monkeypatch):
    item = {
        "item_id": "afi2-auth-fail",
        "provider": "blogger",
        "provider_type": "api",
        "role": "entity_hub",
        "title": "Guide",
        "target_keyword": "kw",
        "target_url": "https://www.balkutusu.com",
        "entities": SAMPLE_JOB["result"]["entities"],
        "faqs": SAMPLE_JOB["result"]["faqs"],
        "status": "queued",
        "link_policy": {},
    }
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (False, "invalid_grant: Token has been expired or revoked."))
    res = af._process_publisher_item(item, {"batch_id": "b", "items": [item]}, af.DEFAULT_SETTINGS)
    assert res["success"] is False
    assert item["status"] == "provider_auth_failed"


def test_endpoint_requires_x_api_key_header(monkeypatch):
    monkeypatch.setattr("app.main.HIVE_API_KEY", "test-key-unblock")
    client = TestClient(app)
    res = client.get("/api/campaign-engine/datasets")
    assert res.status_code == 401
    assert "API key" in res.json().get("detail", "")
    ok = client.get("/api/campaign-engine/datasets", headers={"X-API-Key": "test-key-unblock"})
    assert ok.status_code != 401


def test_collect_sources_lite_skips_provider_fanout():
    sources = ce.collect_sources_lite(keyword="test", domain="https://x.com")
    assert "executive" in sources
    assert sources.get("authority_factory") == {}


def test_plan_uses_lite_sources_not_full_collect(isolated_env, monkeypatch):
    called = {"full": 0, "lite": 0}
    orig_lite = ce.collect_sources_lite

    def _full(**kwargs):
        called["full"] += 1
        raise RuntimeError("collect_sources should not block plan")

    def _lite(**kwargs):
        called["lite"] += 1
        return orig_lite(**kwargs)

    monkeypatch.setattr(ce, "collect_sources", _full)
    monkeypatch.setattr(ce, "collect_sources_lite", _lite)
    monkeypatch.setattr(ce, "_collect_provider_warnings", lambda: [])
    _create_campaign_with_plan()
    assert called["lite"] >= 1
    assert called["full"] == 0
