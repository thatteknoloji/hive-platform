"""Black modül testleri — Medium Bot, SEO Poisoning, Maps simülasyon."""

import json

import pytest
from fastapi import HTTPException

from app.moduller import maps as maps_mod
from app.moduller import medium_bot
from app.moduller import seo_poisoning


@pytest.fixture(autouse=True)
def isolated_maps(tmp_path, monkeypatch):
    db = tmp_path / "maps_data.json"
    monkeypatch.setattr(maps_mod, "MAPS_DB_PATH", str(db))
    db.write_text(json.dumps({"yorumlar": [], "hedefler": [], "simulations": []}), encoding="utf-8")
    yield


def test_maps_simulate_review():
    res = maps_mod.simulate_review("Test Cafe", rating=3, comment="Sim test")
    assert res["success"] is True
    assert res["simulation"] is True
    assert res["live_review_sent"] is False
    assert "Simülasyon tamamlandı" in res["message"]


def test_maps_yorum_gonder_simulation_only():
    res = maps_mod.yorum_gonder("Test Shop", adet=2, puan=4)
    assert res["simulation"] is True
    assert res["simule_edilen"] == 2
    assert "gerçek yorum gönderilmedi" in res["message"]


def test_maps_health():
    h = maps_mod.health()
    assert h["simulation_only"] is True
    assert h["live_reviews"] is False


def test_medium_bot_no_token():
    import app.config as cfg
    orig = cfg.get("MEDIUM_TOKEN")
    try:
        import os
        os.environ["MEDIUM_TOKEN"] = ""
        cfg.reload_env()
        with pytest.raises(HTTPException) as exc:
            medium_bot._token()
        assert "Medium bağlantısı kurulmamış" in str(exc.value.detail)
    finally:
        if orig:
            os.environ["MEDIUM_TOKEN"] = orig
        else:
            os.environ.pop("MEDIUM_TOKEN", None)
        cfg.reload_env()


def test_seo_poisoning_health():
    h = seo_poisoning.health()
    assert h["module"] == "seo_poisoning"
    assert "disclaimer" in h


def test_seo_poisoning_generate(monkeypatch):
    monkeypatch.setattr(
        seo_poisoning,
        "generate",
        lambda prompt, max_tokens=800: ("TITLE: Test\nBODY:\nNegatif içerik test.", True),
    )
    res = seo_poisoning.generate_negative_content("example.com", ["dolandırıcı"])
    assert res["success"] is True
    assert res["content"]["target_domain"] == "example.com"
    assert res["content"]["body"]
