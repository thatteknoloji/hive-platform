"""StoryForge V3 testleri."""

import json

import pytest

from app.moduller import storyforge_v3 as sf3


def test_health_without_crw(monkeypatch):
    monkeypatch.setenv("CRW_URL", "http://127.0.0.1:59999")
    monkeypatch.setattr(sf3, "_check_wordpress", lambda: {
        "connected": False, "url": "", "username_present": False,
        "password_present": False, "error": "test",
    })
    monkeypatch.setattr(sf3, "_check_ollama", lambda: {
        "available": False, "model": "llama3", "error": "test",
    })
    result = sf3.health()
    assert result["success"] is True
    assert result["crw"]["available"] is False
    assert result["ready"] is False
    assert "checked_at" in result


def test_smoke_test_fails_without_crw(monkeypatch):
    monkeypatch.setenv("CRW_URL", "http://127.0.0.1:59999")
    monkeypatch.setattr(sf3, "health", lambda: {
        "success": True,
        "crw": {"available": False, "url": "http://127.0.0.1:59999", "error": "down"},
        "ready": False,
    })
    result = sf3.smoke_test()
    assert result["success"] is False
    assert "fastcrw" in result.get("error", "").lower()


def test_invalid_url_blocked():
    with pytest.raises(ValueError):
        sf3._validate_url("not-a-url")


def test_scrape_error_when_crw_down(monkeypatch):
    monkeypatch.setenv("CRW_URL", "http://127.0.0.1:59999")
    result = sf3.scrape_url("https://example.com")
    assert result["success"] is False
    assert "fastCRW" in result.get("error", "")


def test_rewrite_requires_min_length():
    result = sf3.rewrite_story("kısa")
    assert result["success"] is False


def test_extract_scrape_content_markdown():
    payload = {
        "success": True,
        "data": {
            "markdown": "# Başlık\n\nUzun bir hikaye metni " + ("kelime " * 40),
            "metadata": {"title": "Test"},
        },
    }
    text, title = sf3._extract_scrape_content(payload)
    assert title == "Test"
    assert len(text) > 100


def test_get_rules():
    result = sf3.get_rules()
    assert result["success"] is True
    assert "rules" in result
    assert isinstance(result["rules"], dict)


def test_merge_rules_custom():
    merged = sf3._merge_rules(custom_rules="Özel kural metni")
    assert "Özel kural metni" in merged.get("custom_rules", "")


def test_preview_publish_no_wp(monkeypatch):
    monkeypatch.setattr(
        sf3,
        "wp_api",
        lambda: type("W", (), {"connected": False})(),
    )
    import app.moduller.wordpress_api as wp_mod

    monkeypatch.setattr(
        wp_mod,
        "ensure_wp_connected",
        lambda verify=True: {"connected": False, "error": "WP yok"},
    )
    result = sf3.preview_publish("Test Başlık", "<p>İçerik metni uzun</p>")
    assert result["success"] is False
    assert "WP yok" in result.get("error", "")


def test_preview_publish_success(monkeypatch):
    class FakeApi:
        connected = True

        def list_story_categories(self):
            return {"success": True, "terms": [{"slug": "gece-hikaye", "id": 1}]}

        def create_story_category(self, name, slug, parent=0):
            return {"success": True, "id": 99, "slug": slug}

    monkeypatch.setattr(sf3, "wp_api", lambda: FakeApi())
    monkeypatch.setattr(sf3, "resolve_term_ids", lambda api, cat_info: [1])
    monkeypatch.setenv("WP_URL", "https://www.balkutusu.com")
    result = sf3.preview_publish(
        "Kuşadası Gecesi",
        "<p>" + "kelime " * 60 + "</p>",
        lokasyon="Kadınlar Denizi",
        category_slug="gece-hikaye",
    )
    assert result["success"] is True
    assert result["post_type"] == "erotic_story"
    assert "balkutusu.com" in result["estimated_url"]
    assert result["slug"]


def test_verify_publication(monkeypatch):
    class FakeApi:
        connected = True

        def _request(self, method, path):
            return {
                "success": True,
                "id": 42,
                "status": "publish",
                "link": "https://www.balkutusu.com/erotic_story/test/",
                "title": {"rendered": "Test"},
            }

    monkeypatch.setattr(sf3, "wp_api", lambda: FakeApi())
    monkeypatch.setattr(
        sf3.storyforge_v2,
        "verify_live_url",
        lambda url: {"live": True, "status_code": 200, "final_url": url},
    )
    result = sf3.verify_publication(42)
    assert result["success"] is True
    assert result["verified"] is True
    assert result["live"] is True
    assert result["proof"]["wp_api_ok"] is True


def test_publish_story_with_verification(monkeypatch):
    monkeypatch.setattr(
        sf3,
        "publish_to_wordpress",
        lambda **kw: {
            "success": True,
            "post_id": 99,
            "link": "https://www.balkutusu.com/erotic_story/foo/",
            "display_url": "www.balkutusu.com/erotic_story/foo/",
            "live": True,
        },
    )
    monkeypatch.setattr(
        sf3,
        "verify_publication",
        lambda post_id, link="": {
            "success": True,
            "verified": True,
            "message": "Yayın doğrulandı ✓",
            "live": True,
            "status_code": 200,
        },
    )
    monkeypatch.setattr(sf3, "_save_history", lambda entry: None)
    result = sf3.publish_story("Başlık", "<p>İçerik</p>", source_url="https://example.com/x")
    assert result["success"] is True
    assert result["verified"] is True
    assert "proof_message" in result


def test_process_publish_failure_returns_error(monkeypatch):
    monkeypatch.setattr(sf3, "scrape_url", lambda url: {
        "success": True,
        "text": "x " * 200,
        "title": "Kaynak",
        "source_url": url,
    })
    monkeypatch.setattr(sf3, "rewrite_story", lambda text, title="": {
        "success": True,
        "content": "<p>rewritten</p>",
        "suggested_title": "Test Başlık",
        "suggested_lokasyon": "Kuşadası",
        "suggested_excerpt": "özet",
        "engine": "ollama",
    })
    monkeypatch.setattr(sf3, "publish_to_wordpress", lambda **kw: {
        "success": False,
        "error": "WordPress bağlantısı yok",
    })
    result = sf3.process_story("https://example.com/story")
    assert result["success"] is True
    assert result["status"] == "publish_failed"
    assert "WordPress" in result.get("publish_error", "")
