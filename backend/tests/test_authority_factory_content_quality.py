from __future__ import annotations

import json

from app.main import AuthorityFactoryPreviewContentBody, authority_factory_preview_content
from app.moduller import authority_factory as af


def _mk_item(role: str = "entity_hub", entities: list | None = None, faqs: list | None = None) -> dict:
    return {
        "item_id": "afi2-test",
        "provider": "blogger",
        "provider_type": "api",
        "role": role,
        "title": "Kusadasi Authority Guide",
        "target_keyword": "kusadasi escort",
        "target_url": "https://www.balkutusu.com",
        "entities": entities if entities is not None else [{"label": "Marina Club"}],
        "faqs": faqs if faqs is not None else [{"question": "Nerede?", "answer": "Marina bolgesinde."}],
        "categories": ["Nightlife"],
        "addresses": ["Kusadasi Marina"],
        "status": "queued",
        "link_policy": {"link_type": "brand", "target_url": "https://www.balkutusu.com", "anchor": "Balkutusu"},
    }


def _mk_batch(item: dict) -> dict:
    return {
        "batch_id": "af2-test",
        "target_money_site": "https://www.balkutusu.com",
        "dataset_id": "dm-test",
        "items": [item],
    }


def test_build_content_html_has_h1():
    html = af._build_content_html("Title", "kw", {"target_url": "https://x.com"}, item=_mk_item(), batch=_mk_batch(_mk_item()))
    assert "<h1>Title</h1>" in html


def test_includes_dataset_entities():
    item = _mk_item(entities=[{"label": "Marina Club"}])
    html = af._build_content_html(item["title"], item["target_keyword"], item["link_policy"], item=item, batch=_mk_batch(item))
    assert "Marina Club" in html


def test_includes_dataset_faqs():
    item = _mk_item(faqs=[{"question": "Nasil?", "answer": "Planli."}])
    html = af._build_content_html(item["title"], item["target_keyword"], item["link_policy"], item=item, batch=_mk_batch(item))
    assert "Nasil?" in html


def test_includes_geo_section():
    item = _mk_item(role="geo_hub")
    html = af._build_content_html(item["title"], item["target_keyword"], item["link_policy"], item=item, batch=_mk_batch(item))
    assert "Local / GEO Section" in html


def test_includes_citation_block():
    item = _mk_item(role="citation_hub")
    html = af._build_content_html(item["title"], item["target_keyword"], item["link_policy"], item=item, batch=_mk_batch(item))
    assert "Citation / Source Block" in html


def test_includes_money_site_link():
    item = _mk_item()
    html = af._build_content_html(item["title"], item["target_keyword"], item["link_policy"], item=item, batch=_mk_batch(item))
    assert "https://www.balkutusu.com" in html


def test_word_count_over_150():
    item = _mk_item()
    html = af._build_content_html(item["title"], item["target_keyword"], item["link_policy"], item=item, batch=_mk_batch(item))
    stats = af._content_stats(html, af._normalize_entities(item["entities"]), af._normalize_faqs(item["faqs"]), {"passed": True})
    assert stats["word_count"] >= 150


def test_quality_score_over_85_for_rich_item(tmp_path, monkeypatch):
    state = tmp_path / "authority_factory_state.json"
    item = _mk_item()
    state.write_text(json.dumps({"settings": {**af.DEFAULT_SETTINGS, "enabled": True}, "batches": [_mk_batch(item)], "history": []}), encoding="utf-8")
    monkeypatch.setattr(af, "STATE_FILE", state)
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda payload: {"passed": True, "score": 89, "analysis": {}})
    prev = af.preview_content(item["item_id"])
    assert prev["success"] is True
    assert prev["quality_score"] >= 85


def test_thin_item_review_required(monkeypatch):
    item = _mk_item(entities=[])
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (True, None))
    res = af._process_publisher_item(item, _mk_batch(item), af.DEFAULT_SETTINGS)
    assert res["status"] == "review_required"


def test_preview_endpoint_works(tmp_path, monkeypatch):
    state = tmp_path / "authority_factory_state.json"
    item = _mk_item()
    state.write_text(json.dumps({"settings": {**af.DEFAULT_SETTINGS, "enabled": True}, "batches": [_mk_batch(item)], "history": []}), encoding="utf-8")
    monkeypatch.setattr(af, "STATE_FILE", state)
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda item: {"passed": True, "score": 90, "analysis": {}})
    body = authority_factory_preview_content(AuthorityFactoryPreviewContentBody(item_id=item["item_id"], format="html"))
    assert body["quality_score"] >= 85
    assert body["word_count"] >= 150


def test_publisher_item_enqueues_when_quality_high(monkeypatch):
    item = _mk_item()
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda payload: {"passed": True, "score": 90, "analysis": {}})
    monkeypatch.setattr("app.moduller.publisher_hub.enqueue", lambda payload: {"success": True, "publish_id": "q-123"})
    res = af._process_publisher_item(item, _mk_batch(item), af.DEFAULT_SETTINGS)
    assert res["success"] is True
    assert item["status"] == "queued"


def test_publisher_item_not_enqueue_when_low_quality(monkeypatch):
    item = _mk_item()
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda payload: {"passed": False, "score": 74, "analysis": {}})
    res = af._process_publisher_item(item, _mk_batch(item), af.DEFAULT_SETTINGS)
    assert res["status"] == "review_required"


def test_queue_id_stored(monkeypatch):
    item = _mk_item()
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda payload: {"passed": True, "score": 91, "analysis": {}})
    monkeypatch.setattr("app.moduller.publisher_hub.enqueue", lambda payload: {"success": True, "publish_id": "q-999"})
    af._process_publisher_item(item, _mk_batch(item), af.DEFAULT_SETTINGS)
    assert item.get("metadata", {}).get("queue_id") == "q-999"


def test_publisher_ready_requires_connected_not_only_configured(monkeypatch):
    monkeypatch.setattr(
        "app.moduller.publisher_hub._channel_status",
        lambda channel: {"configured": True, "connected": False, "error": None},
    )
    monkeypatch.setattr(
        "app.moduller.blogger_api.get_status",
        lambda: {"connected": False, "error": "invalid_grant: Token has been expired or revoked."},
    )
    ready, err = af._publisher_ready("blogger")
    assert ready is False
    assert "invalid_grant" in (err or "").lower()


    item = _mk_item()
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (False, "provider_missing"))
    res = af._process_publisher_item(item, _mk_batch(item), af.DEFAULT_SETTINGS)
    assert res["success"] is False
    assert item["status"] == "provider_missing"


def test_no_fake_published(monkeypatch):
    item = _mk_item()
    monkeypatch.setattr(af, "_publisher_ready", lambda channel: (True, None))
    monkeypatch.setattr("app.moduller.publisher_hub._quality_check", lambda payload: {"passed": True, "score": 88, "analysis": {}})
    monkeypatch.setattr("app.moduller.publisher_hub.enqueue", lambda payload: {"success": True, "publish_id": "q-1"})
    res = af._process_publisher_item(item, _mk_batch(item), af.DEFAULT_SETTINGS)
    assert res["success"] is True
    assert item["status"] != "published"
    assert not item.get("result_url")
