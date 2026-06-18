"""Black modül testleri v3 — Zeus + Backlink Hijacker (simülasyon yok)."""

import json

import pytest

from app.moduller import backlinkhijacker as hijacker
from app.moduller import zeus as zeus_mod


@pytest.fixture(autouse=True)
def isolated_dbs(tmp_path, monkeypatch):
    hij_db = tmp_path / "hijack_results.json"
    zeus_db = tmp_path / "zeus_pages.json"
    monkeypatch.setattr(hijacker, "HIJACK_DB_PATH", str(hij_db))
    monkeypatch.setattr(zeus_mod, "ZEUS_DB_PATH", str(zeus_db))
    hij_db.write_text("[]", encoding="utf-8")
    zeus_db.write_text("[]", encoding="utf-8")
    yield


def test_zeus_platforms_no_google_sites():
    assert "Google Sites" not in zeus_mod.PLATFORMLAR
    assert "Medium" in zeus_mod.PLATFORMLAR
    assert "GitHub" in zeus_mod.PLATFORMLAR


def test_zeus_missing_api_key(monkeypatch):
    monkeypatch.setattr(zeus_mod.config, "get", lambda k, d="": "")
    res = zeus_mod.parazit_yerlestir("Medium", konu="Test", hedef_url="https://example.com")
    assert res["status"] == "hata"
    assert "API anahtarı eksik" in res["hata"]
    assert "MEDIUM_TOKEN" in res["eksik_anahtarlar"]


def test_zeus_invalid_platform():
    res = zeus_mod.parazit_yerlestir("Google Sites", konu="X")
    assert res["status"] == "hata"
    assert "Geçersiz platform" in res["hata"]


def test_zeus_health():
    h = zeus_mod.health()
    assert h["module"] == "zeus"
    assert h["simulation"] is False
    assert "Medium" in h["platformlar"]
    assert "configured" in h


def test_zeus_platform_analiz():
    a = zeus_mod.platform_analiz()
    assert a["google_sites_kaldirildi"] is True
    assert "Google Sites" not in a["desteklenen_platformlar"]


def test_zeus_publish_medium_mock(monkeypatch):
    monkeypatch.setattr(zeus_mod, "_missing_keys", lambda p: [])

    def fake_medium(konu, hedef_url, tags=None):
        return {"durum": "yayında", "kaynak": "medium_api", "url": "https://medium.com/p/abc", "success": True}

    monkeypatch.setitem(zeus_mod._PUBLISHERS, "Medium", fake_medium)
    res = zeus_mod.parazit_yerlestir("Medium", konu="SEO Test", hedef_url="https://balkutusu.com")
    assert res["durum"] == "aktif"
    assert res["kaynak"] == "medium_api"
    assert res["page_id"].startswith("ZEUS-")
    pages = zeus_mod.parazit_listele()
    assert pages["toplam"] == 1


def test_hijacker_health(monkeypatch):
    monkeypatch.setattr(
        "app.moduller.backlink_hunter.health",
        lambda: {"providers": ["openseo", "dataseo_mcp"], "openseo_live": False},
    )
    h = hijacker.health()
    assert h["module"] == "backlinkhijacker"
    assert h["simulation"] is False


def test_find_broken_backlinks_provider_unavailable(monkeypatch):
    monkeypatch.setattr(
        hijacker,
        "get_backlinks",
        lambda domain, limit=50: {"success": False, "error": "provider_unavailable", "message": "test"},
    )
    res = hijacker.find_broken_backlinks("example.com")
    assert res["status"] == "hata"


def test_find_broken_backlinks_detects_broken(monkeypatch):
    monkeypatch.setattr(
        hijacker,
        "get_backlinks",
        lambda domain, limit=50: {
            "success": True,
            "provider": "openseo",
            "links": [
                {"source_url": "https://a.com/post", "target_url": "https://dead.example/404", "anchor": "link", "rank": 40},
                {"source_url": "https://b.com/x", "target_url": "https://live.example/", "anchor": "ok", "rank": 50},
            ],
        },
    )

    def fake_check(url):
        broken = "dead.example" in url
        return {"url": url, "reachable": not broken, "status": 404 if broken else 200, "broken": broken}

    monkeypatch.setattr(hijacker, "_http_check", fake_check)
    res = hijacker.find_broken_backlinks("example.com")
    assert res["status"] == "aktif"
    assert res["tespit_edilen_kirik"] == 1
    assert res["kirilan_linkler"][0]["target_url"] == "https://dead.example/404"


def test_steal_backlink_outreach(monkeypatch):
    class FakeResp:
        status_code = 200
        text = '<a href="https://broken.old/page">eski</a>'

    monkeypatch.setattr(hijacker.requests, "get", lambda *a, **k: FakeResp())
    monkeypatch.setattr(
        hijacker,
        "_http_check",
        lambda url: {"url": url, "broken": "broken.old" in url, "status": 404, "reachable": False},
    )
    res = hijacker.steal_backlink("https://source.com/article", "https://mysite.com/replacement")
    assert res["status"] == "aktif"
    assert res["durum"] == "outreach_hazir"
    assert "mysite.com" in res["outreach_pitch"]


def test_cal_requires_domain():
    res = hijacker.cal("")
    assert res["status"] == "hata"


def test_hijacker_export_json(monkeypatch):
    monkeypatch.setattr(
        hijacker,
        "find_broken_backlinks",
        lambda domain, limit=50: {
            "status": "aktif",
            "domain": domain,
            "tespit_edilen_kirik": 1,
            "kirilan_linkler": [
                {"source_url": "https://a.com", "target_url": "https://dead.com", "anchor": "x", "rank": 10},
            ],
            "provider": "openseo",
            "kaynak": "test",
            "olusturma": "2026-01-01",
        },
    )
    res = hijacker.export("example.com", format="json")
    assert res["format"] == "json"
    assert "icerik" in res
