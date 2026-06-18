from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import project_engine as pe


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    monkeypatch.setattr(pe, "STATE_FILE", tmp_path / "project_engine_state.json")
    panel_identity.bootstrap()
    from app.auth import create_access_token
    client = TestClient(app)
    token = create_access_token(email="hive@thiqos.com")
    return client, {"Authorization": f"Bearer {token}"}


def test_create_hotel_project_site_skeleton(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post("/api/v3/projects", headers=headers, json={
        "name": "Karaburun Boutique",
        "sector": "otel",
        "business_brief": "Karaburun'da deniz manzaralı lüks butik otel.",
        "design": {
            "wizard_version": 2,
            "brand_personality": ["premium", "ultra_luks"],
            "design_dna": "hotel_luxury",
            "color_identity": "gold_luxury",
            "conversion_goal": "rezervasyon",
            "creative_director_brief": "Lüks ve güven.",
        },
        "deploy_mode": "hive_cloud",
    })
    assert res.status_code == 200
    project = res.json()["project"]
    assert project["site"]["pages_count"] == 7
    titles = [p["title"] for p in project["pages"]]
    assert titles == ["Ana Sayfa", "Odalar", "Galeri", "Hakkımızda", "Blog", "İletişim", "SSS"]
    assert project["navigation"][1] == {"label": "Odalar", "href": "/odalar"}
    assert project["theme"]["design_dna"] == "hotel_luxury"
    assert project["theme"]["font_style"] == "serif"
    assert all(len(p["sections"]) >= 2 for p in project["pages"])
