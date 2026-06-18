"""Web Scraper — gerçek parse testleri (HTTP mock)."""

import pytest

from app.moduller import webscraper as ws
from app.moduller.scrape_utils import parse_page, extract_contacts


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Kuşadası Gece Hayatı Rehberi</title>
  <meta name="description" content="Kuşadası bar ve kulüp rehberi">
</head>
<body>
  <h1>Gece Hayatı</h1>
  <h2>Barlar</h2>
  <p>Kuşadası gece hayatı için en iyi mekanlar burada listelenmiştir.</p>
  <a href="/iletisim">İletişim</a>
  <a href="https://balkutusu.com/hakkimizda">Hakkımızda</a>
  <a href="mailto:info@balkutusu.com">Mail</a>
  <img src="/images/bar.jpg" alt="Bar foto">
  <p>Bizi arayın: 0532 111 22 33 veya info@balkutusu.com</p>
</body>
</html>
"""


def test_parse_page_extracts_structure():
    parsed = parse_page(SAMPLE_HTML, "https://balkutusu.com/gece-hayati")
    assert parsed["title"] == "Kuşadası Gece Hayatı Rehberi"
    assert "kuşadası" in parsed["meta_description"].lower()
    assert len(parsed["headings"]) >= 2
    assert len(parsed["links"]) >= 2
    assert len(parsed["images"]) == 1
    assert "info@balkutusu.com" in parsed["emails"]


def test_extract_contacts():
    c = extract_contacts("info@test.com ve 0532 444 55 66")
    assert "info@test.com" in c["emails"]
    assert c["phones"]


def test_kazi_requires_url():
    res = ws.kazi("")
    assert res.get("status") == "hata"


def test_kazi_fetch_mock(monkeypatch):
    def fake_fetch(url):
        return SAMPLE_HTML, None

    monkeypatch.setattr(ws, "fetch_html", fake_fetch)
    res = ws.kazi("https://balkutusu.com", derinlik=1, max_pages=3)
    assert res.get("success") is True
    assert res["taranan_sayfa"] >= 1
    assert res["sayfalar"][0]["title"]


def test_health():
    h = ws.health()
    assert h["success"] is True
    assert h["module"] == "webscraper"
