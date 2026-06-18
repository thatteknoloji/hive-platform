"""SSS Otomatik Zincir — smoke testler."""

from unittest.mock import MagicMock, patch

from app.moduller.sss_automation import (
    _publish_sss_page,
    sss_automation,
    _default_state,
)
from app.moduller.sss_generator import generate_sss_page
from app.moduller.wordpress_api import wp_api


def test_start_does_not_crash():
    """_default_state() + status çakışması TypeError vermemeli."""
    sss_automation._update(**_default_state())
    wp = wp_api(0)
    if not wp.connected:
        return
    result = sss_automation.start(
        city="Aydın",
        district="Kuşadası",
        category="Gece Hayatı",
        subcategory="Barlar",
        main_keyword="kuşadası test",
        keyword_count=50,
        domain_id=0,
        extra_keywords=["test kelime 1"],
    )
    assert result.get("success") is True, result.get("error")
    assert result.get("session_id")
    assert "_run_args" in result
    sss_automation._update(**_default_state())


def test_keyword_pool_min_50():
    pool = sss_automation._build_keyword_pool(
        "Aydın", "Kuşadası", "Gece Hayatı", "Barlar",
        "kuşadası gece hayatı", 50,
        extra_keywords=["ekstra test"],
    )
    assert len(pool) >= 50


def test_publish_uses_upsert_page_not_post():
    page = generate_sss_page(
        "Aydın", "Kuşadası", "Gece Hayatı", "Barlar",
        "test yayin slug",
    )
    wp = MagicMock()
    wp.upsert_page.return_value = {
        "success": True,
        "id": 99,
        "link": "https://example.com/test-yayin-slug/",
        "updated": True,
    }
    res = _publish_sss_page(wp, page)
    assert res["success"] is True
    wp.upsert_page.assert_called_once()
    wp.trash_conflicting_post.assert_called_once_with(page["slug"])
    wp.create_post.assert_not_called()


def test_preview_returns_word_stats():
    with patch("app.moduller.sss_generator._ollama_generate", return_value=("", False)):
        result = sss_automation.preview(
            "Aydın", "Kuşadası", "Gece Hayatı", "Barlar",
            "önizleme test",
            include_listings=False,
        )
    assert result["success"] is True
    assert result["page"]["word_stats"]["faq_count"] >= 20
