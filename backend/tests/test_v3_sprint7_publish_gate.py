from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import astro_export_engine, project_engine as pe


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    monkeypatch.setattr(pe, "STATE_FILE", tmp_path / "project_engine_state.json")
    monkeypatch.setattr(astro_export_engine, "EXPORT_ROOT", tmp_path / "generated_sites")
    panel_identity.bootstrap()
    from app.auth import create_access_token
    client = TestClient(app)
    token = create_access_token(email="hive@thiqos.com")
    return client, {"Authorization": f"Bearer {token}"}


def _create_and_export(client, headers, domain: str = ""):
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "Sitemap Hotel",
        "sector": "otel",
        "domain": domain,
        "business_brief": "Karaburun'da butik otel.",
        "design": {"design_dna": "hotel_luxury", "color_identity": "gold_luxury", "conversion_goal": "rezervasyon"},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    export = client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    assert export.status_code == 200
    return pid, Path(export.json()["export_path"])


def test_export_creates_sitemap_xml(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, export_path = _create_and_export(client, headers, domain="hotelsite.com")
    sitemap = export_path / "public" / "sitemap.xml"
    assert sitemap.is_file()
    text = sitemap.read_text(encoding="utf-8")
    assert "<urlset" in text
    assert "https://hotelsite.com/" in text
    assert "<loc>" in text
    assert "<lastmod>" in text
    assert "<priority>" in text


def test_robots_contains_sitemap_reference(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    _, export_path = _create_and_export(client, headers, domain="hotelsite.com")
    robots = (export_path / "public" / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: *" in robots
    assert "Allow: /" in robots
    assert "Sitemap: https://hotelsite.com/sitemap.xml" in robots


def test_site_json_has_base_url(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    _, export_path = _create_and_export(client, headers, domain="mybrand.com")
    site = json.loads((export_path / "src" / "data" / "site.json").read_text(encoding="utf-8"))
    assert site["base_url"] == "https://mybrand.com"
    assert site["domain"] == "https://mybrand.com"


def test_validation_passes_sitemap_checks(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_and_export(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    assert res.status_code == 200
    names = {c["name"] for c in res.json()["checks"]}
    for check in (
        "sitemap_xml_exists",
        "sitemap_contains_urlset",
        "robots_contains_sitemap",
        "site_json_base_url",
        "base_layout_canonical_base",
    ):
        assert check in names
    assert all(c["ok"] for c in res.json()["checks"] if c["name"] in (
        "sitemap_xml_exists", "sitemap_contains_urlset", "robots_contains_sitemap",
        "site_json_base_url", "base_layout_canonical_base",
    ))


def test_publish_gate_false_without_export(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "No Export",
        "sector": "blog",
        "business_brief": "Blog",
        "design": {},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    res = client.get(f"/api/v3/projects/{pid}/publish-gate", headers=headers)
    assert res.status_code == 200
    astro = res.json()["astro"]
    assert astro["can_publish"] is False
    assert "astro_export_missing" in astro["reasons"]


def test_publish_gate_false_without_validation(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_and_export(client, headers)
    res = client.get(f"/api/v3/projects/{pid}/publish-gate", headers=headers)
    astro = res.json()["astro"]
    assert astro["can_publish"] is False
    assert "astro_validation_missing" in astro["reasons"]


def test_publish_gate_true_after_export_and_validation(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_and_export(client, headers)
    client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    res = client.get(f"/api/v3/projects/{pid}/publish-gate", headers=headers)
    assert res.status_code == 200
    astro = res.json()["astro"]
    assert astro["can_publish"] is True
    assert astro["reasons"] == []
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    assert project["metadata"]["astro_publish_gate"]["can_publish"] is True


def test_publish_gate_false_when_sitemap_removed(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, export_path = _create_and_export(client, headers)
    client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    (export_path / "public" / "sitemap.xml").unlink()
    res = client.get(f"/api/v3/projects/{pid}/publish-gate", headers=headers)
    assert res.json()["astro"]["can_publish"] is False
    assert "sitemap_missing" in res.json()["astro"]["reasons"]
