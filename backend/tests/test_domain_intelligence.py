"""Domain Intelligence Engine V2 — unit tests."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.moduller import expireddomain as ed


@pytest.fixture
def temp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([], f)
    monkeypatch.setattr(ed, "EXP_DB_PATH", path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def test_normalize_domain():
    assert ed._normalize_domain("HTTPS://WWW.Example.COM/path") == "example.com"


def test_expiry_status_from_days():
    assert ed._expiry_status_from_days(None) == "provider_missing"
    assert ed._expiry_status_from_days(-1) == "expired"
    assert ed._expiry_status_from_days(15) == "expiring_30"
    assert ed._expiry_status_from_days(45) == "expiring_60"
    assert ed._expiry_status_from_days(75) == "expiring_90"
    assert ed._expiry_status_from_days(120) == "active"


def test_parse_date_iso():
    dt = ed._parse_date("2026-12-31")
    assert dt is not None
    assert dt.year == 2026


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_v2_layers():
    h = ed.health()
    assert h["module"] == "expireddomain"
    assert h["version"] == "v2"
    assert "expiry_watcher" in h["layers"]
    assert "authority_discovery" in h["layers"]


# ── Expiry Watcher ────────────────────────────────────────────────────────────

def test_check_expiry_provider_missing(monkeypatch):
    monkeypatch.setattr(ed.shutil, "which", lambda _: None)
    with patch.object(ed, "_rdap_expiry", return_value={"success": False, "error": "fail"}):
        result = ed.check_expiry("example.com")
    assert result["status"] == "provider_missing"
    assert result["expires_at"] is None
    assert result["days_remaining"] is None


def test_check_expiry_whois_success(monkeypatch):
    future = (datetime.now(timezone.utc) + timedelta(days=45)).strftime("%Y-%m-%d")
    monkeypatch.setattr(
        ed, "_whois_expiry",
        lambda d: {"success": True, "provider": "whois", "expires_at": future, "days_remaining": 45, "status": "expiring_60"},
    )
    result = ed.check_expiry("example.com")
    assert result["status"] == "expiring_60"
    assert result["expires_at"] == future
    assert result["provider"] == "whois"


def test_check_expiry_rdap_fallback(monkeypatch):
    future = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
    monkeypatch.setattr(ed, "_whois_expiry", lambda d: {"success": False, "error": "not found"})
    monkeypatch.setattr(
        ed, "_rdap_expiry",
        lambda d: {"success": True, "provider": "rdap", "expires_at": future, "days_remaining": 10, "status": "expiring_30"},
    )
    result = ed.check_expiry("example.com")
    assert result["provider"] == "rdap"
    assert result["status"] == "expiring_30"


# ── Authority Discovery ─────────────────────────────────────────────────────────

def test_authority_unknown_on_empty_wayback(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"]]
    monkeypatch.setattr(ed.requests, "get", lambda *a, **k: mock_resp)
    result = ed.discover_authority("empty-domain.com")
    assert result["status"] == "unknown"
    assert result["first_seen"] == "unknown"
    assert result["historical_category"] == "unknown"


def test_authority_with_snapshots(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        ["timestamp", "original", "statuscode", "mime"],
        ["20180101120000", "http://shop.example.com/", "200", "text/html"],
        ["20200101120000", "http://shop.example.com/buy", "200", "text/html"],
    ]
    monkeypatch.setattr(ed.requests, "get", lambda *a, **k: mock_resp)
    monkeypatch.setattr(ed, "_emit_brain_event", lambda *a, **k: None)
    result = ed.discover_authority("shop-example.com")
    assert result["status"] == "ok"
    assert result["archive_snapshots"] == 2
    assert result["first_seen"] == "2018-01-01"
    assert result["last_seen"] == "2020-01-01"


def test_infer_category_unknown():
    assert ed._infer_category_from_urls([]) == "unknown"


def test_brand_signals_unknown_short():
    result = ed._brand_signals("x1.com", 0, None)
    assert result["status"] == "unknown"


# ── Domain Score ──────────────────────────────────────────────────────────────

def test_compute_domain_score_structure(monkeypatch):
    monkeypatch.setattr(ed, "discover_authority", lambda d: ed._authority_unknown(d))
    monkeypatch.setattr(ed, "check_expiry", lambda d: {"status": "provider_missing", "expires_at": None})
    monkeypatch.setattr(ed, "check_domain", lambda d: {"success": True, "available": True})
    monkeypatch.setattr(ed, "_emit_brain_event", lambda *a, **k: None)
    result = ed.compute_domain_score("brandname.com", "brand")
    assert 0 <= result["overall_domain_score"] <= 100
    assert "brandability_score" in result
    assert "authority_score" in result
    assert "spam_risk_score" in result
    assert result["authority_status"] == "unknown"


def test_topical_match_with_keyword(monkeypatch):
    monkeypatch.setattr(ed, "discover_authority", lambda d: ed._authority_unknown(d))
    monkeypatch.setattr(ed, "check_expiry", lambda d: {"status": "active"})
    monkeypatch.setattr(ed, "check_domain", lambda d: {"success": True, "available": False})
    monkeypatch.setattr(ed, "_emit_brain_event", lambda *a, **k: None)
    result = ed.compute_domain_score("seotools.com", "seotools")
    assert result["topical_match_score"] >= 45


# ── Watchlist / State ─────────────────────────────────────────────────────────

def test_domain_kaydet_and_listele(temp_db, monkeypatch):
    monkeypatch.setattr(ed, "check_domain", lambda d: {"success": True, "available": False, "provider": "test"})
    monkeypatch.setattr(ed, "check_expiry", lambda d: {
        "domain": d, "last_checked": "2026-01-01", "expires_at": None,
        "days_remaining": None, "status": "provider_missing",
    })
    monkeypatch.setattr(ed, "_emit_brain_event", lambda *a, **k: None)
    res = ed.domain_kaydet("watch-test.com")
    assert res["durum"] == "kaydedildi"
    liste = ed.domain_listele()
    assert liste["toplam"] == 1
    assert liste["domainler"][0]["domain"] == "watch-test.com"
    assert "expiry" in liste["domainler"][0]


def test_domain_sil(temp_db, monkeypatch):
    monkeypatch.setattr(ed, "check_domain", lambda d: {"success": True, "available": True})
    monkeypatch.setattr(ed, "check_expiry", lambda d: {"status": "provider_missing"})
    monkeypatch.setattr(ed, "_emit_brain_event", lambda *a, **k: None)
    ed.domain_kaydet("remove-me.com")
    ed.domain_sil("remove-me.com")
    assert ed.domain_listele()["toplam"] == 0


def test_list_expiring(temp_db, monkeypatch):
    monkeypatch.setattr(ed, "check_domain", lambda d: {"success": True, "available": False})
    monkeypatch.setattr(ed, "check_expiry", lambda d: {
        "domain": d, "last_checked": "2026-01-01", "expires_at": "2026-02-01",
        "days_remaining": 20, "status": "expiring_30",
    })
    monkeypatch.setattr(ed, "_emit_brain_event", lambda *a, **k: None)
    ed.domain_kaydet("soon.com")
    result = ed.list_expiring(90)
    assert result["toplam"] >= 1
    assert result["domainler"][0]["expiry"]["status"] == "expiring_30"


def test_refresh_expiry_watch(temp_db, monkeypatch):
    monkeypatch.setattr(ed, "check_domain", lambda d: {"success": True, "available": False})
    monkeypatch.setattr(ed, "_emit_brain_event", lambda *a, **k: None)

    def fake_expiry(d):
        return {"domain": d, "last_checked": "2026-06-01", "expires_at": "2026-09-01", "days_remaining": 80, "status": "expiring_90"}

    monkeypatch.setattr(ed, "check_expiry", fake_expiry)
    ed.domain_kaydet("refresh.com")
    res = ed.refresh_expiry_watch()
    assert res["success"] is True
    assert res["updated"] == 1


# ── Dashboard / Integrations ──────────────────────────────────────────────────

def test_dashboard(temp_db, monkeypatch):
    monkeypatch.setattr(ed, "hive_integrations", lambda: {"success": True, "read_only": True, "ready": True, "integrations": {}})
    result = ed.dashboard()
    assert result["success"] is True
    assert result["version"] == "v2"
    assert "watchlist_total" in result


def test_hive_integrations_read_only(monkeypatch):
    monkeypatch.setattr(ed, "_safe_health", lambda fn: {"ok": True, "detail": {"success": True}})
    import app.moduller.hive_brain_engine as hbe
    monkeypatch.setattr(hbe.hive_brain, "list_events", lambda **kw: {"events": []})
    result = ed.hive_integrations()
    assert result["read_only"] is True
    assert "integrations" in result


def test_reports_overview():
    result = ed.reports("overview")
    assert result["success"] is True
    assert result["report_type"] == "overview"
    assert "data" in result


# ── Layer 1 preserved ─────────────────────────────────────────────────────────

def test_check_bulk_domains_limit(monkeypatch):
    monkeypatch.setattr(ed, "check_domain", lambda d: {"success": True, "domain": d, "available": True})
    results = ed.check_bulk_domains([f"d{i}.com" for i in range(60)])
    assert len(results) == 50


def test_domain_bul_no_keyword():
    assert ed.domain_bul("")["status"] == "hata"


def test_export_csv_fields(monkeypatch):
    monkeypatch.setattr(ed, "domain_bul", lambda k, adet=10: {
        "domainler": [{"domain": "a.com", "musait": True, "durum": "müsait", "kaynak": "test"}],
    })
    result = ed.export("test", "csv")
    assert result["format"] == "csv"
    assert "a.com" in result["icerik"]
