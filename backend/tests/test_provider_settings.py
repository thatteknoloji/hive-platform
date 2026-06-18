"""Provider settings — DataForSEO opsiyonel tercih testleri."""

import json

import pytest

from app.moduller import provider_settings as ps


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    state = tmp_path / "hive_provider_settings.json"
    monkeypatch.setattr(ps, "STATE_FILE", state)
    state.write_text(json.dumps({"settings": dict(ps.DEFAULT_SETTINGS)}), encoding="utf-8")
    yield


def test_default_settings():
    s = ps.get_settings()
    assert s["backlink"] == "auto"
    assert s["domain"] == "free"


def test_update_settings():
    ps.update_settings({"backlink": "dataforseo"})
    assert ps.get_settings()["backlink"] == "dataforseo"


def test_provider_chain_auto_no_dfs(monkeypatch):
    monkeypatch.setattr(ps, "_dataforseo_ready", lambda: False)
    chain = ps.provider_chain("backlink")
    assert "dataforseo" not in chain
    assert "openseo" in chain


def test_provider_chain_auto_with_dfs(monkeypatch):
    monkeypatch.setattr(ps, "_dataforseo_ready", lambda: True)
    chain = ps.provider_chain("backlink")
    assert chain[0] == "dataforseo"


def test_provider_chain_dataforseo_required(monkeypatch):
    monkeypatch.setattr(ps, "_dataforseo_ready", lambda: True)
    ps.update_settings({"backlink": "dataforseo"})
    assert ps.require_dataforseo("backlink") is True
    assert ps.provider_chain("backlink") == ["dataforseo"]


def test_health():
    h = ps.health()
    assert h["success"] is True
    assert "backlink" in h["categories"]
