"""Tumblr API yardımcıları — blog tanımlayıcı normalizasyonu."""

import pytest
from fastapi import HTTPException

from app.moduller import tumblr_api


def test_normalize_blog_short_name():
    assert tumblr_api.normalize_blog_identifier("balkutumcom") == "balkutumcom.tumblr.com"


def test_normalize_blog_full_hostname():
    assert tumblr_api.normalize_blog_identifier("balkutumcom.tumblr.com") == "balkutumcom.tumblr.com"


def test_normalize_blog_url():
    assert tumblr_api.normalize_blog_identifier("https://balkutumcom.tumblr.com/") == "balkutumcom.tumblr.com"


def test_normalize_blog_uuid():
    assert tumblr_api.normalize_blog_identifier("t:abc123") == "t:abc123"


def test_normalize_blog_empty_raises(monkeypatch):
    monkeypatch.delenv("TUMBLR_DEFAULT_BLOG", raising=False)
    with pytest.raises(HTTPException) as exc:
        tumblr_api.normalize_blog_identifier("")
    assert exc.value.status_code == 400


def test_pick_primary_blog_prefers_primary():
    blogs = [
        {"identifier": "a.tumblr.com", "admin": True, "primary": False},
        {"identifier": "b.tumblr.com", "admin": True, "primary": True},
    ]
    assert tumblr_api._pick_primary_blog(blogs) == "b.tumblr.com"


def test_content_to_html_wraps_title():
    html = tumblr_api._content_to_html("<p>Merhaba</p>", title="Başlık")
    assert "<h1>Başlık</h1>" in html
    assert "<p>Merhaba</p>" in html
