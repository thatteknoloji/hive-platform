"""Astro Site Factory — gerçek filesystem testleri."""

import json
from pathlib import Path

import pytest

from app.moduller import astro_factory as af


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    state_file = tmp_path / "astro_factory_state.json"
    gen_dir = tmp_path / "generated-sites"
    gen_dir.mkdir()
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "package.json").write_text('{"name":"t"}', encoding="utf-8")
    (template_dir / "astro.config.mjs").write_text("export default {}", encoding="utf-8")
    (template_dir / "src" / "data").mkdir(parents=True)
    (template_dir / "src" / "data" / "pages.json").write_text("{}", encoding="utf-8")
    (template_dir / "src" / "data" / "faqs.json").write_text("[]", encoding="utf-8")
    (template_dir / "src" / "data" / "blog.json").write_text("[]", encoding="utf-8")
    (template_dir / "public").mkdir(parents=True)

    monkeypatch.setattr(af, "STATE_FILE", state_file)
    monkeypatch.setattr(af, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(af, "TEMPLATE_DIR", template_dir)
    state_file.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    yield


def test_health_endpoint():
    result = af.health()
    assert result["success"] is True
    assert result["status"] == "ok"
    assert "npm" in result


def test_create_project_creates_real_folder():
    result = af.create_project({
        "site_name": "Test Astro Site",
        "domain": "test.example.com",
        "seed_keyword": "kuşadası test",
        "location": "Kuşadası",
        "main_site_url": "https://www.balkutusu.com",
    })
    assert result["success"] is True
    assert result["package_json_exists"] is True
    path = Path(result["filesystem_path"])
    assert path.is_dir()
    assert (path / "package.json").is_file()
    assert (path / "src" / "data" / "pages.json").is_file()


def test_generate_site_plan():
    result = af.generate_site_plan(
        seed_keyword="kuşadası marina",
        location="Kuşadası",
        niche="Gece Hayatı",
        page_count=8,
    )
    assert result["success"] is True
    plan = result["plan"]
    assert plan["seed_keyword"] == "kuşadası marina"
    assert "geo_pages" in plan
    assert "talon_meta" in plan


def test_path_traversal_blocked():
    with pytest.raises(ValueError):
        af._safe_slug("../../etc/passwd")


def test_build_without_files_returns_error():
    created = af.create_project({"site_name": "Build Test", "seed_keyword": "test"})
    pid = created["project"]["id"]
    # Remove package.json to simulate missing generate
    slug = created["project"]["slug"]
    pkg = af._project_path(slug) / "package.json"
    if pkg.exists():
        pkg.unlink()
    result = af.build_astro_project(pid)
    assert result["success"] is False
    assert "generate-pages" in result.get("error", "").lower() or "package" in result.get("error", "").lower()


def test_export_stays_inside_generated_dir(tmp_path, monkeypatch):
    gen_dir = tmp_path / "generated-sites"
    monkeypatch.setattr(af, "GENERATED_DIR", gen_dir)
    gen_dir.mkdir(parents=True, exist_ok=True)
    created = af.create_project({
        "site_name": "Export Test",
        "seed_keyword": "export test",
        "domain": "https://export.test",
    })
    pid = created["project"]["id"]
    result = af.export_project(pid)
    assert result["success"] is True
    export_path = Path(result["export_path"])
    assert export_path.exists()
    assert export_path.parent.resolve() == gen_dir.resolve()


def test_write_outside_generated_dir_blocked(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError):
        af._project_path(str(outside / "hack"))
