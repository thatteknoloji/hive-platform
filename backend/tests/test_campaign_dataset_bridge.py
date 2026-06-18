"""Campaign Dataset Bridge V1 — Data Miner → Campaign Engine tests."""

from __future__ import annotations

import json

import pytest

from app.moduller import campaign_engine as ce


SAMPLE_JOB = {
    "job_id": "dm-test123456",
    "job_type": "keyword",
    "status": "completed",
    "source": "kuşadası gece hayatı",
    "created_at": "2026-06-15 12:00:00 UTC",
    "result": {
        "entities": [
            {"label": "Marina Gece", "type": "heading"},
            {"label": "Liman Caddesi", "type": "heading"},
        ],
        "faqs": [
            {"question": "Kuşadası gece hayatı nerede?", "answer": "Marina bölgesinde."},
            {"question": "Ne zaman açık?", "answer": "Yaz sezonu."},
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
        "id": "dm-test123456",
        "type": "keyword",
        "source": "kuşadası gece hayatı",
        "created_at": "2026-06-15 12:00:00 UTC",
        "entity_count": 2,
        "faq_count": 2,
    }
]


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "campaign_engine_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")
    dm_state = tmp_path / "data_miner_engine_state.json"
    dm_state.write_text(json.dumps({
        "settings": {},
        "jobs": {"dm-test123456": SAMPLE_JOB},
        "datasets": SAMPLE_DATASETS,
    }), encoding="utf-8")

    monkeypatch.setattr(ce, "STATE_FILE", state)
    monkeypatch.setattr(ce, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)
    import app.moduller.data_miner_engine as dme
    monkeypatch.setattr(dme, "STATE_FILE", dm_state)
    monkeypatch.setattr(ce, "collect_sources", lambda **kwargs: {
        "opportunity": {"quick_wins": 2},
        "crawl_gap": {"faq_gaps": 5, "entity_gaps": 3},
        "citation": {"citation_risks": 10},
        "serp": {},
        "revenue": {},
        "authority_factory": {},
        "support_network": {},
        "rank": {},
        "executive": {},
    })
    def _mock_safe_read(module, func, *args, default=None, **kwargs):
        if module == "authority_factory":
            import importlib
            mod = importlib.import_module(f"app.moduller.{module}")
            fn = getattr(mod, func)
            return fn(*args, **kwargs)
        return default if default is not None else {}

    monkeypatch.setattr(ce, "_safe_read", _mock_safe_read)

    state.write_text(json.dumps({
        "settings": {**ce.DEFAULT_SETTINGS, "enabled": True},
        "campaigns": [],
        "tasks": [],
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "brain_state": brain_state, "dm_state": dm_state}


def test_list_datasets(isolated_env):
    res = ce.list_datasets_for_campaign()
    assert res["success"] is True
    assert res["count"] >= 1
    assert res["datasets"][0]["dataset_id"] == "dm-test123456"
    assert res["datasets"][0]["entity_count"] == 2


def test_create_campaign_from_dataset(isolated_env):
    res = ce.create_from_dataset(
        dataset_id="dm-test123456",
        target_domain="https://www.balkutusu.com",
        primary_keyword="kuşadası gece hayatı",
        campaign_type="full_domination",
        market="kusadasi",
    )
    assert res["success"] is True
    c = res["campaign"]
    assert c["dataset_id"] == "dm-test123456"
    assert c["dataset_backed_campaign"] is True
    assert c["dataset_summary"]["entity_count"] == 2
    assert len(c["dataset_entities"]) == 2
    assert len(c["dataset_faqs"]) == 2


def test_invalid_dataset_id(isolated_env):
    res = ce.create_from_dataset(
        dataset_id="dm-nonexistent",
        primary_keyword="test",
        target_domain="https://www.balkutusu.com",
    )
    assert res["success"] is False
    assert "not_found" in (res.get("error") or "")


def test_attach_dataset_to_existing_campaign(isolated_env):
    created = ce.create_campaign(
        name="Balkutusu Index Recovery",
        target_keyword="kuşadası escort",
        target_domain="https://www.balkutusu.com",
    )
    cid = created["campaign"]["campaign_id"]
    res = ce.attach_dataset(cid, "dm-test123456")
    assert res["success"] is True
    assert res["campaign"]["dataset_id"] == "dm-test123456"
    assert res["campaign"]["index_recovery"] is True


def test_generate_plan_from_dataset(isolated_env):
    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kuşadası gece hayatı",
        target_domain="https://www.balkutusu.com",
    )
    cid = created["campaign"]["campaign_id"]
    plan = ce.generate_plan_from_dataset(cid)
    assert plan["success"] is True
    assert plan["task_count"] > 0
    assert plan.get("dataset_driven") is True
    types = {t["item_type"] for t in plan["tasks"]}
    assert "entity_page" in types
    assert "faq_page" in types
    assert "authority_source" in types


def test_entities_to_entity_page_task(isolated_env):
    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    plan = ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    entity_tasks = [t for t in plan["tasks"] if t["item_type"] == "entity_page"]
    assert len(entity_tasks) >= 2
    assert "Marina" in entity_tasks[0]["title"]


def test_faqs_to_faq_page_task(isolated_env):
    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    plan = ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    faq_tasks = [t for t in plan["tasks"] if t["item_type"] == "faq_page"]
    assert len(faq_tasks) >= 2


def test_categories_to_cluster_task(isolated_env):
    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    plan = ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    cluster_tasks = [t for t in plan["tasks"] if t["item_type"] == "cluster"]
    assert len(cluster_tasks) >= 3


def test_addresses_to_geo_page_task(isolated_env):
    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    plan = ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    geo_tasks = [t for t in plan["tasks"] if t["item_type"] == "geo_page"]
    assert len(geo_tasks) >= 2


def test_schema_types_to_citation_task(isolated_env):
    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    plan = ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    cite_tasks = [t for t in plan["tasks"] if t["item_type"] == "citation_expansion"]
    assert len(cite_tasks) >= 2


def test_authority_tasks_generated(isolated_env):
    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    plan = ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    types = {t["item_type"] for t in plan["tasks"]}
    assert "authority_source" in types
    assert "publisher_content" in types
    assert "support_site" in types


def test_send_to_authority_factory_compatible(isolated_env, monkeypatch):
    import app.moduller.authority_factory as af

    af_state = isolated_env["state"].parent / "authority_factory_state.json"
    af_state.write_text(json.dumps({
        "settings": {**af.DEFAULT_SETTINGS, "enabled": True},
        "batches": [],
        "history": [],
    }), encoding="utf-8")
    monkeypatch.setattr(af, "STATE_FILE", af_state)

    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kuşadası gece hayatı",
        target_domain="https://www.balkutusu.com",
    )
    cid = created["campaign"]["campaign_id"]
    ce.generate_plan_from_dataset(cid)
    res = ce.send_to_authority_factory(cid)
    assert res["success"] is True
    batch = res.get("batch") or {}
    assert batch.get("dataset_id") == "dm-test123456"
    items = batch.get("items") or []
    assert len(items) >= 1
    assert any(len(it.get("entities") or []) > 0 for it in items)


def test_balkutusu_index_recovery_attach(isolated_env):
    created = ce.create_campaign(
        name="Balkutusu Index Recovery",
        target_keyword="kuşadası escort",
        target_domain="https://www.balkutusu.com",
    )
    cid = created["campaign"]["campaign_id"]
    ce.attach_dataset(cid, "dm-test123456")
    plan = ce.generate_plan_from_dataset(cid)
    assert plan["success"] is True
    ir_tasks = [t for t in plan["tasks"] if (t.get("payload") or {}).get("index_recovery")]
    assert len(ir_tasks) >= 4


def test_brain_event(isolated_env):
    ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    data = json.loads(isolated_env["brain_state"].read_text(encoding="utf-8"))
    events = [e.get("metadata", {}).get("campaign_event") or e.get("type") for e in data.get("events") or []]
    assert any("dataset" in str(ev).lower() for ev in events)


def test_mission_control_payload(isolated_env):
    ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kw",
        target_domain="https://www.balkutusu.com",
    )
    mc = ce.mission_control_payload()
    assert mc.get("dataset_campaigns", 0) >= 1
    assert "dataset_attached_campaigns" in mc
    assert "campaigns_ready_for_factory" in mc


def test_executive_payload_dataset_boost(isolated_env):
    created = ce.create_from_dataset(
        dataset_id="dm-test123456",
        primary_keyword="kuşadası gece hayatı",
        target_domain="https://www.balkutusu.com",
    )
    ce.generate_plan_from_dataset(created["campaign"]["campaign_id"])
    align = ce.executive_alignment_payload()
    best = align.get("best_match") or {}
    if best:
        assert best.get("dataset_backed_campaign") is True


def test_no_fake_success_on_bad_dataset(isolated_env):
    res = ce.attach_dataset("camp-fake", "dm-test123456")
    assert res["success"] is False
    res2 = ce.generate_plan_from_dataset("camp-fake")
    assert res2["success"] is False


def test_existing_keyword_campaign_compatibility(isolated_env):
    """Keyword-only campaign hâlâ çalışmalı — dataset zorunlu değil."""
    res = ce.create_campaign(target_keyword="kuşadası escort", goal="ranking")
    assert res["success"] is True
    assert not res["campaign"].get("dataset_id")
    plan = ce.generate_plan(res["campaign"]["campaign_id"])
    assert plan["success"] is True
    assert plan["task_count"] > 0
    assert not plan.get("dataset_driven")
