"""Cloudflare Pages Auto Deploy testleri."""

import json

import pytest

from app.moduller import astro_factory as af
from app.moduller import cloudflare_pages_deploy as cf


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    state_file = tmp_path / "astro_factory_state.json"
    gen_dir = tmp_path / "generated-sites"
    gen_dir.mkdir()
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(af, "STATE_FILE", state_file)
    monkeypatch.setattr(af, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(af, "TEMPLATE_DIR", template_dir)
    state_file.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "")
    yield


def test_status_configured_false_without_env():
    result = cf.cf_status()
    assert result["configured"] is False
    assert result["token_present"] is False
    assert result["account_id_present"] is False
    assert "token" not in json.dumps(result).lower() or result.get("token_present") is False


def test_token_not_in_status_response(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "secret-token-xyz")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc123")
    result = cf.cf_status()
    dumped = json.dumps(result)
    assert "secret-token-xyz" not in dumped
    assert result["token_present"] is True
    assert result["configured"] is True


def test_project_name_sanitize():
    assert cf.sanitize_cf_project_name("Kuşadası Gece!") == "kusadasi-gece"
    assert cf.sanitize_cf_project_name("hive-my-site") == "hive-my-site"


def test_path_traversal_project_name_blocked():
    with pytest.raises(ValueError):
        cf.sanitize_cf_project_name("../../etc/passwd")


def test_deploy_without_dist_returns_clear_error(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc")
    created = af.create_project({"site_name": "CF Deploy Test", "seed_keyword": "test"})
    pid = created["project"]["id"]
    result = cf.deploy_to_cloudflare(pid)
    assert result["success"] is False
    assert "build" in result["error"].lower()


def test_create_project_requires_cloudflare_env(monkeypatch):
    created = af.create_project({"site_name": "CF Create", "seed_keyword": "test"})
    pid = created["project"]["id"]
    result = cf.create_pages_project(pid)
    assert result["success"] is False
    assert result["configured"] is False


@pytest.mark.integration
def test_cloudflare_create_project_integration(monkeypatch):
    """Gerçek API — CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID gerekli."""
    from app import config as real_config

    token = (real_config.get("CLOUDFLARE_API_TOKEN") or "").strip()
    account = (real_config.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    if not token or not account:
        pytest.skip("Cloudflare env eksik")

    monkeypatch.setattr(cf, "config", real_config)
    created = af.create_project({
        "site_name": "CF Integration Test",
        "seed_keyword": "integration test",
        "slug": "cf-integration-test",
    })
    pid = created["project"]["id"]
    name = "hive-cf-integration-test"
    result = cf.create_pages_project(pid, name)
    assert result["success"] is True
    assert result["cloudflare"]["project_name"] == name
