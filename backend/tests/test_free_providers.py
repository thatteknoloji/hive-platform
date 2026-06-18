"""Ücretsiz domain/backlink provider testleri."""

import pytest

from app.moduller import (
    backlink_hunter,
    competitor_hijacker,
    expireddomain,
    free_provider_clients as fpc,
)


@pytest.fixture(autouse=True)
def mock_providers(monkeypatch):
    monkeypatch.setattr(
        fpc,
        "check_domain",
        lambda domain, provider=None: {
            "success": True,
            "domain": domain,
            "available": domain.startswith("free-"),
            "provider": "test",
        },
    )
    monkeypatch.setattr(
        fpc,
        "get_backlinks",
        lambda domain, limit=50, provider=None: {
            "success": True,
            "domain": domain,
            "provider": "dataseo_free",
            "summary": {"backlinks": 10, "referring_domains": 5, "rank": 42},
            "links": [
                {
                    "source_url": f"https://ref-{domain}/post",
                    "target_url": f"https://{domain}/",
                    "domain_from": f"ref-{domain}",
                    "anchor": "test anchor",
                    "rank": 55,
                    "dofollow": True,
                    "simulasyon": False,
                }
            ],
        },
    )
    monkeypatch.setattr(
        fpc,
        "provider_health",
        lambda: {
            "domain_ready": True,
            "backlink_ready": True,
            "namecheap_required": False,
            "dataforseo_required": False,
            "dataforseo_configured": False,
            "provider_settings": {"backlink": "auto"},
            "backlink_chain": ["openseo", "dataseo_free"],
        },
    )
    monkeypatch.setattr(
        "app.moduller.provider_settings.get_settings",
        lambda: {"backlink": "auto", "domain": "free"},
    )
    monkeypatch.setattr(
        "app.moduller.provider_settings.health",
        lambda: {"categories": {"backlink": {"mode": "auto", "chain": ["openseo"]}}},
    )


def test_check_domain_example():
    res = fpc.check_domain("free-test.com")
    assert res["success"] is True
    assert res["available"] is True


def test_expireddomain_health():
    h = expireddomain.health()
    assert h["free_stack"] is True
    assert h["version"] == "v2"
    assert "whois_available" in h


def test_expireddomain_bul(monkeypatch):
    monkeypatch.setattr(expireddomain.shutil, "which", lambda _: "/usr/bin/npx")
    monkeypatch.setattr(expireddomain, "_aday_domainler_uret", lambda k, a: ["testkeyword.com"])
    monkeypatch.setattr(expireddomain, "check_bulk_domains", lambda d: [{"success": True, "domain": "testkeyword.com", "available": True}])
    monkeypatch.setattr(expireddomain, "_emit_brain_event", lambda *a, **k: None)
    res = expireddomain.domain_bul("testkeyword", adet=5)
    assert "domainler" in res
    assert res.get("kaynak") == "agent-domain-service-mcp"


def test_backlink_hunter_get_backlinks():
    res = backlink_hunter.get_backlinks("example.com")
    assert res["success"] is True
    assert len(res["links"]) >= 1


def test_backlink_hunter_opportunities():
    res = backlink_hunter.opportunities(["example.com"], our_domain="mysite.com")
    assert res["status"] == "aktif"
    assert res["dataforseo"] is False
    assert res["provider_mode"] == "auto"
    assert res["toplam"] >= 1


def test_competitor_hijacker_analyze():
    res = competitor_hijacker.analyze_competitor("example.com", send_to_hunter=False)
    assert res["status"] == "aktif"
    assert res["dataforseo"] is False
    assert res["backlink_sayisi"] >= 1


def test_provider_health_flags():
    ph = fpc.provider_health()
    assert ph["namecheap_required"] is False
    assert ph["dataforseo_required"] is False
    assert "provider_settings" in ph or "dataforseo" in ph
