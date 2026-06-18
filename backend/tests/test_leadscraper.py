"""Lead Scraper — toplama testleri."""

import pytest

from app.moduller import leadscraper as ls


CONTACT_HTML = """
<html><head><title>İletişim</title></head>
<body>
  <p>info@otelkusadasi.com</p>
  <p>Telefon: 0532 999 88 77</p>
</body></html>
"""


def test_health():
    h = ls.health()
    assert h["success"] is True
    assert h["module"] == "leadscraper"


def test_topla_requires_input():
    res = ls.topla()
    assert res.get("status") == "hata"


def test_topla_direct_url(monkeypatch):
    monkeypatch.setattr(ls, "fetch_html", lambda url: (CONTACT_HTML, None))
    res = ls.topla(url="https://example.com/iletisim", adet=10)
    assert res.get("success") is True
    assert res["bulunan_lead"] >= 2
    types = {l["type"] for l in res["leads"]}
    assert "email" in types
    assert "phone" in types


def test_topla_keyword_no_provider(monkeypatch):
    monkeypatch.setattr(ls, "_search_urls", lambda q, limit: ([], "", "provider missing"))
    res = ls.topla(kelime="kuşadası otel", adet=5)
    assert res.get("status") == "hata"
    assert res.get("hata") == "provider_missing"


def test_topla_keyword_with_search(monkeypatch):
    monkeypatch.setattr(
        ls,
        "_search_urls",
        lambda q, limit: (["https://example.com/contact"], "searxng", None),
    )
    monkeypatch.setattr(ls, "fetch_html", lambda url: (CONTACT_HTML, None))
    res = ls.topla(kelime="kuşadası otel", adet=5)
    assert res.get("success") is True
    assert res["kaynak"] == "searxng"
    assert res["bulunan_lead"] >= 1
