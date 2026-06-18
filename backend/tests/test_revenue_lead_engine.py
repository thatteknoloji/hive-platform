"""Revenue / Lead Engine V1 testleri."""

import json

import pytest

from app.moduller import revenue_lead_engine as rle


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "revenue_lead_engine_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(rle, "STATE_FILE", state)
    monkeypatch.setattr(rle, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "settings": dict(rle.DEFAULT_SETTINGS),
        "leads": [],
        "visits": [],
        "rate_buckets": {},
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "reports": reports}


def test_health(isolated_env):
    h = rle.health()
    assert h["success"] is True
    assert h["module"] == "revenue_lead_engine"
    assert "whatsapp_click" in h["event_types"]


def test_track_lead(isolated_env):
    res = rle.track_lead(
        "whatsapp_click",
        source_url="https://www.balkutusu.com/kusadasi",
        keyword="kuşadası gece hayatı",
        target="905551234567",
        client_ip="127.0.0.1",
    )
    assert res["success"] is True
    lead = res["lead"]
    assert lead["lead_id"].startswith("lead-")
    assert lead["lead_type"] == "whatsapp"
    assert lead["commercial_intent_score"] >= 70


def test_duplicate_spam_filter(isolated_env):
    args = dict(
        event_type="phone_click",
        source_url="https://example.com/page",
        target="905551234567",
        client_ip="10.0.0.1",
    )
    r1 = rle.track_lead(**args)
    r2 = rle.track_lead(**args)
    assert r1["success"] is True
    assert r2["success"] is False
    assert r2["error"] == "spam_duplicate"


def test_whatsapp_redirect(isolated_env):
    res = rle.track_and_redirect("whatsapp_click", "905551234567", source_url="https://site.com", client_ip="1.2.3.4")
    assert res["success"] is True
    assert res["redirect_url"].startswith("https://wa.me/")


def test_phone_redirect(isolated_env):
    res = rle.track_and_redirect("phone_click", "905551234567", source_url="https://site.com", client_ip="1.2.3.5")
    assert res["success"] is True
    assert res["redirect_url"].startswith("tel:")


def test_email_redirect(isolated_env):
    res = rle.track_and_redirect("email_click", "info@example.com", source_url="https://site.com", client_ip="1.2.3.6")
    assert res["success"] is True
    assert res["redirect_url"].startswith("mailto:")


def test_open_redirect_block(isolated_env):
    rle.update_settings({"allowed_redirect_domains": ["balkutusu.com"]})
    res = rle.track_and_redirect(
        "external_link_click",
        "https://evil-phish.example.com/steal",
        source_url="https://balkutusu.com",
        client_ip="1.2.3.7",
    )
    assert res["success"] is False
    assert res["error"] == "open_redirect_blocked"


def test_lead_status_update(isolated_env, monkeypatch):
    events = []
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "record_event", lambda et, mod, **kw: events.append(et) or {"success": True})

    lead = rle.track_lead("form_submit", source_url="https://x.com", client_ip="9.9.9.9")["lead"]
    res = rle.update_lead_status(lead["lead_id"], "qualified")
    assert res["success"] is True
    assert res["lead"]["status"] == "qualified"
    assert "lead_qualified" in events


def test_source_attribution(isolated_env):
    res = rle.track_lead(
        "publisher_referral",
        source_url="https://myblog.blogspot.com/post",
        keyword="test",
        metadata={"source_module": "publisher_hub:blogger"},
        client_ip="8.8.8.8",
    )
    assert res["lead"]["source_module"] == "publisher_hub:blogger"


def test_keyword_attribution(isolated_env):
    res = rle.track_lead("phone_click", source_url="https://a.com", keyword="bodrum otel", target="90555", client_ip="7.7.7.7")
    kw = rle.list_keywords()
    assert kw["success"] is True
    assert any("bodrum otel" in (k.get("keyword") or "") for k in kw["keywords"])


def test_brain_hook(isolated_env, monkeypatch):
    events = []
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "record_event", lambda et, mod, **kw: events.append(et) or {"success": True})
    rle.track_lead("whatsapp_click", source_url="https://z.com", target="90555", client_ip="6.6.6.6")
    assert "lead_created" in events


def test_mission_control_payload(isolated_env):
    rle.track_lead("phone_click", source_url="https://b.com", keyword="kw", target="90555", client_ip="5.5.5.5")
    payload = rle.mission_control_payload()
    assert payload["success"] is True
    assert payload["today_leads"] >= 1


def test_opportunity_scoring_payload(isolated_env):
    rle.track_lead("whatsapp_click", source_url="https://c.com", keyword="commercial kw", target="90555", client_ip="4.4.4.4")
    rle.track_lead("whatsapp_click", source_url="https://c.com", keyword="commercial kw", target="90556", client_ip="4.4.4.5")
    payload = rle.opportunity_scoring_payload()
    assert payload["success"] is True
    assert any(s.get("boost") for s in payload["signals"])


def test_export_report(isolated_env):
    rle.track_lead("email_click", source_url="https://d.com", target="a@b.com", client_ip="3.3.3.3")
    res = rle.export_report("overview")
    assert res["success"] is True
    assert res["path"]
