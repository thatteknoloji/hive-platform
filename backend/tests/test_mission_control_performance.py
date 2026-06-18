"""Mission Control performance telemetry — Optimization Sprint."""

import json

import pytest

from app.moduller import mission_control_center as mcc


@pytest.fixture(autouse=True)
def isolated_perf(tmp_path, monkeypatch):
    db = tmp_path / "mission_control_center_state.json"
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "small_state.json").write_text('{"history": [1, 2]}', encoding="utf-8")
    big = {"outputs": list(range(3000))}
    (app_dir / "big_state.json").write_text(json.dumps(big), encoding="utf-8")

    monkeypatch.setattr(mcc, "STATE_FILE", db)
    monkeypatch.setattr(mcc, "APP_DIR", app_dir)
    db.write_text('{"settings": {}, "actions": [], "history": []}', encoding="utf-8")
    mcc._PERF_CACHE.clear()
    mcc._PERF_CACHE.update({
        "timings": [], "endpoint_stats": {}, "large_responses": [],
        "last_score": 0, "last_risk": 0, "perf_history": [],
        "dirty": False, "last_flush": 0.0, "loaded": False,
    })
    mcc._PERF_STATUS_CACHE.clear()
    mcc._PERF_STATUS_CACHE.update({"at": 0.0, "data": None})
    yield


def test_record_request_timing():
    mcc.record_request_timing("/api/mission-control/dashboard", 950.0, 200, 600_000)
    mcc._flush_perf_cache(force=True)
    st = mcc._load_state()
    assert len(st.get("performance", {}).get("timings", [])) >= 1
    bucket = st["performance"]["endpoint_stats"]["/api/mission-control/dashboard"]
    assert bucket["slow_count"] >= 1


def test_top_slow_endpoints_p95():
    mcc.record_request_timing("/api/test/a", 100, 200, 1000)
    mcc.record_request_timing("/api/test/a", 2000, 200, 1000)
    eps = mcc.top_slow_endpoints(5)
    hit = next(e for e in eps if e["path"] == "/api/test/a")
    assert "p95_response_ms" in hit
    assert hit["avg_response_ms"] > 0


def test_scan_state_files():
    files = mcc.scan_state_files(10)
    assert len(files) >= 1
    assert files[0]["bytes"] >= files[-1]["bytes"]


def test_build_performance_status_lite():
    status = mcc.build_performance_status(full=False)
    assert "performance_score" in status
    assert status["queue_analysis"].get("lite") is True


def test_build_performance_report():
    report = mcc.build_performance_report()
    assert report["success"] is True
    assert "top_20_slow_endpoints" in report
    assert "top_20_largest_states" in report
    assert "recommendations" in report
