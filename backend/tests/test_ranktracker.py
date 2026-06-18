"""Rank Tracker — DataForSEO + GSC entegrasyon testleri."""

import json

import pytest

from app.moduller import ranktracker as rt


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "rank_tracker.json"
    db.write_text(json.dumps({"keywords": [], "history": []}), encoding="utf-8")
    monkeypatch.setattr(rt, "RT_DB_PATH", str(db))
    yield db


def test_health_no_providers(monkeypatch):
    monkeypatch.setattr(rt, "_gsc_configured", lambda: False)
    monkeypatch.setattr(rt, "_dataforseo_configured", lambda: False)
    h = rt.health()
    assert h["success"] is True
    assert h["ready"] is False
    assert h["search_console"] is False
    assert h["dataforseo"] is False


def test_takip_et_provider_missing(monkeypatch):
    monkeypatch.setattr(rt, "_gsc_configured", lambda: False)
    monkeypatch.setattr(rt, "_dataforseo_configured", lambda: False)
    res = rt.takip_et("kuşadası gece hayatı", "balkutusu.com")
    assert res["status"] == "hata"
    assert res["hata"] == "provider_missing"


def test_takip_et_dataforseo_only(monkeypatch):
    monkeypatch.setattr(rt, "_gsc_configured", lambda: False)
    monkeypatch.setattr(rt, "_dataforseo_configured", lambda: True)
    monkeypatch.setattr(rt, "_dataforseo_rank", lambda kw, dom: {
        "position": 8,
        "first_url": "https://balkutusu.com/test",
        "serp_snapshot": [{"position": 8, "url": "https://balkutusu.com/test"}],
        "source": "dataforseo",
    })
    res = rt.takip_et("kuşadası gece hayatı", "balkutusu.com")
    assert res.get("status") != "hata"
    assert res["guncel_pozisyon"] == 8
    assert res["kaynak"] == "dataforseo"
    assert len(res["gecmis"]) >= 1


def test_takip_et_gsc_fallback(monkeypatch):
    monkeypatch.setattr(rt, "_gsc_configured", lambda: True)
    monkeypatch.setattr(rt, "_dataforseo_configured", lambda: False)
    monkeypatch.setattr(rt, "_gsc_keyword_metrics", lambda kw, days=28: {
        "position": 12.4,
        "clicks": 40,
        "impressions": 900,
        "ctr": 0.044,
        "daily": [{"tarih": "2026-06-01", "pozisyon": 12.4}],
        "source": "search_console",
    })
    res = rt.takip_et("kuşadası gece hayatı", "balkutusu.com")
    assert res["guncel_pozisyon"] == 12.4
    assert "search_console" in res["kaynak"]
    assert res["search_console"]["clicks"] == 40


def test_takip_et_both_providers(monkeypatch):
    monkeypatch.setattr(rt, "_gsc_configured", lambda: True)
    monkeypatch.setattr(rt, "_dataforseo_configured", lambda: True)
    monkeypatch.setattr(rt, "_dataforseo_rank", lambda kw, dom: {
        "position": 5,
        "first_url": "https://balkutusu.com/",
        "serp_snapshot": [],
        "source": "dataforseo",
    })
    monkeypatch.setattr(rt, "_gsc_keyword_metrics", lambda kw, days=28: {
        "position": 6.1,
        "clicks": 10,
        "impressions": 200,
        "ctr": 0.05,
        "daily": [],
        "source": "search_console",
    })
    res = rt.takip_et("test keyword", "balkutusu.com")
    assert res["guncel_pozisyon"] == 5
    assert res["kaynak"] == "dataforseo+search_console"
    assert res["dataforseo"]["position"] == 5
    assert res["search_console"]["position"] == 6.1


def test_keyword_kaydet_and_listele(isolated_db):
    rt.keyword_kaydet("kuşadası escort", "balkutusu.com")
    listed = rt.keyword_listele()
    assert listed["toplam"] == 1
    assert listed["keywords"][0]["kelime"] == "kuşadası escort"


def test_toplu_kontrol(monkeypatch):
    monkeypatch.setattr(rt, "_gsc_configured", lambda: True)
    monkeypatch.setattr(rt, "_dataforseo_configured", lambda: False)
    monkeypatch.setattr(rt, "_gsc_keyword_metrics", lambda kw, days=28: {
        "position": 15,
        "clicks": 1,
        "impressions": 50,
        "ctr": 0.02,
        "daily": [],
        "source": "search_console",
    })
    res = rt.toplu_kontrol(["kw1", "kw2"], domain="balkutusu.com")
    assert res["toplam"] == 2
    assert len(res["sonuclar"]) == 2
