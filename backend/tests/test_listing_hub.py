"""Listing Hub — gerçek CRUD, medya, SEO, toplu işlem, quality gate testleri."""

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.moduller import listing_hub as lh


def _base(**extra):
    return {
        "title": "Test İlan",
        "city": "Kuşadası",
        "district": "Merkez",
        "categories": ["kuşadası"],
        "phone": "5551234567",
        **extra,
    }


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "listing_hub_state.json"
    media = tmp_path / "uploads" / "listings"
    media.mkdir(parents=True)
    state.write_text(
        json.dumps({"listings": {}, "bulk_jobs": {}, "import_staging": {}, "counters": {"ilan_no": 10000}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(lh, "STATE_FILE", state)
    monkeypatch.setattr(lh, "MEDIA_DIR", media)
    monkeypatch.setenv("DEFAULT_LISTING_VIDEO_URL", "https://www.youtube.com/watch?v=TESTVID")
    yield {"state": state, "media": media}


def test_health(isolated_env):
    result = lh.health()
    assert result["success"] is True
    assert result["module"] == "Listing Hub"
    assert "TESTVID" in result["default_video_url"]


def test_crud(isolated_env):
    created = lh.create_listing(_base())
    assert created["success"] is True
    lid = created["listing"]["id"]
    assert created["listing"]["ilan_no"] == "10001"
    assert created["listing"]["status"] == "draft"

    got = lh.get_listing(lid)
    assert got["listing"]["title"] == "Test İlan"

    updated = lh.update_listing(lid, {"status": "review", "price": 1500})
    assert updated["listing"]["status"] == "review"
    assert updated["listing"]["price"] == 1500

    listed = lh.list_listings()
    assert listed["total"] == 1

    deleted = lh.delete_listing(lid)
    assert deleted["success"] is True
    assert lh.get_listing(lid)["success"] is False


def test_required_fields_validation(isolated_env):
    assert lh.create_listing({"title": "X"})["success"] is False
    assert lh.create_listing({"title": "X", "city": "A"})["success"] is False
    assert lh.create_listing({"title": "X", "city": "A", "categories": ["c"]})["success"] is False


def test_multi_category_and_services(isolated_env):
    res = lh.create_listing(_base(categories=["a", "b", "c"], services=["s1", "s2"]))
    l = res["listing"]
    assert len(l["categories"]) == 3
    assert len(l["services"]) == 2


def test_default_video_assignment(isolated_env):
    res = lh.create_listing(_base())
    l = lh.apply_media_defaults(res["listing"])
    assert "TESTVID" in l["video_url"]
    assert l["video_embed_url"] == "https://www.youtube.com/embed/TESTVID"


def test_video_url_normalize():
    watch, embed = lh.normalize_youtube_url("https://youtu.be/abc123?t=1")
    assert watch == "https://www.youtube.com/watch?v=abc123"
    assert embed == "https://www.youtube.com/embed/abc123"


def test_map_embed_generation(isolated_env):
    res = lh.create_listing(_base(address="Atatürk Cad.", district="Merkez", city="Kuşadası"))
    l = lh.apply_media_defaults(res["listing"])
    assert l["map_embed_url"]
    assert "maps.google.com" in l["map_embed_url"] or "openstreetmap" in l["map_embed_url"]

    res2 = lh.create_listing(_base(latitude=37.85, longitude=27.25))
    l2 = lh.apply_media_defaults(res2["listing"])
    assert "openstreetmap" in l2["map_embed_url"]


def test_publish_blocked_without_cover(isolated_env):
    res = lh.create_listing(_base())
    pub = lh.publish_listing(res["listing"]["id"])
    assert pub["success"] is False
    assert "cover_missing" in pub.get("publish_blockers", [])


def test_publish_blocked_without_map(isolated_env):
    listing = lh._default_listing("1")
    listing.update({
        "title": "T", "phone": "555", "categories": ["x"], "city": "", "district": "", "address": "",
        "cover_image": "pub:cover.jpg",
    })
    listing = lh.apply_media_defaults(listing)
    listing["map_embed_url"] = ""
    v = lh.validate_publish_allowed(listing)
    assert "map_missing" in v["publish_blockers"]


def test_publish_blocked_without_category(isolated_env):
    listing = lh._default_listing("1")
    listing["title"] = "T"
    listing["phone"] = "555"
    v = lh.validate_publish_allowed(lh.apply_media_defaults(listing))
    assert "category_missing" in v["publish_blockers"]


def test_media_upload_path_safety(isolated_env):
    res = lh.create_listing(_base())
    with pytest.raises(ValueError):
        lh._listing_media_dir("../evil")


def test_media_upload_and_reorder(isolated_env):
    res = lh.create_listing(_base(ilan_no="12345"))
    lid = res["listing"]["id"]
    up1 = lh.upload_media(lid, "12345_1.jpg", b"fake-jpeg-bytes", "image/jpeg", set_cover=True)
    up2 = lh.upload_media(lid, "12345_2.jpg", b"more-bytes", "image/jpeg")
    assert up1["success"] and up2["success"]
    got = lh.get_listing(lid)["listing"]
    assert len(got["gallery_images"]) == 2
    assert got["cover_image"] == up1["media"]["id"]

    reordered = lh.reorder_media(lid, [up2["media"]["id"], up1["media"]["id"]])
    assert reordered["listing"]["gallery_images"][0]["id"] == up2["media"]["id"]


def test_bulk_import_preview(isolated_env):
    csv_content = "title,city,category,phone\nTest CSV,Kuşadası,escort,555\n"
    preview = lh.import_preview(csv_content, "csv")
    assert preview["success"] is True
    assert preview["valid_count"] == 1
    assert preview["preview"][0].get("title") == "Test CSV"


def test_bulk_import_commit(isolated_env):
    csv_content = "title,city,category,phone\nİlan A,Aydın,cat,555\nİlan B,İzmir,cat,556\n"
    preview = lh.import_preview(csv_content, "csv")
    result = lh.import_commit(preview["job_id"])
    assert result["success"] is True
    assert result["created"] == 2
    assert lh.list_listings()["total"] == 2


def test_zip_media_matching(isolated_env):
    lh.create_listing(_base(ilan_no="99999", title="ZIP İlan"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("99999_1.jpg", b"photo1")
        zf.writestr("99999_cover.jpg", b"photo2")
    result = lh.bulk_media_zip(buf.getvalue())
    assert result["success"] is True
    assert result["matched"] == 2


def test_generate_seo(isolated_env):
    res = lh.create_listing(_base(title="Kuşadası Escort"))
    lid = res["listing"]["id"]
    seo = lh.listing_hub.generate_seo(lid)
    assert seo["success"] is True
    assert seo["listing"]["slug"]
    assert seo["listing"]["meta_title"]
    assert seo["listing"]["schema_jsonld"]


def test_run_quality_gate(isolated_env):
    res = lh.create_listing(_base(description="Detaylı açıklama " * 20))
    lid = res["listing"]["id"]
    lh.upload_media(lid, "cover.jpg", b"bytes", "image/jpeg", set_cover=True)
    gate = lh.listing_hub.run_quality_gate(lid)
    assert gate["success"] is True
    assert gate["listing"]["seo_score"] >= 0


@patch("app.moduller.listing_hub.run_quality_gate")
@patch("app.moduller.listing_hub.wp_api")
def test_wordpress_missing_provider_fallback(mock_wp_api, mock_gate, isolated_env):
    mock_wp = MagicMock()
    mock_wp.connected = False
    mock_wp_api.return_value = mock_wp

    def _pass_gate(listing):
        listing = lh.validate_publish_allowed(listing, after_gate=False)
        listing["seo_score"] = 80
        listing["geo_score"] = 80
        listing["publish_allowed"] = True
        listing["publish_blockers"] = []
        return listing

    mock_gate.side_effect = _pass_gate

    res = lh.create_listing(_base())
    lid = res["listing"]["id"]
    lh.upload_media(lid, "cover.jpg", b"bytes", "image/jpeg", set_cover=True)
    pub = lh.publish_listing(lid)
    assert pub["success"] is True
    assert pub["listing"]["status"] == "active"
    assert pub["listing"]["wp_status"] == "provider_missing"


@patch("app.moduller.listing_hub.run_quality_gate")
@patch("app.moduller.listing_hub.wp_api")
def test_publish_to_wordpress(mock_wp_api, mock_gate, isolated_env):
    mock_wp = MagicMock()
    mock_wp.connected = True
    mock_wp.resolve_companion_category_ids.return_value = [1]
    mock_wp.upload_media.return_value = {"success": True, "id": 55, "source_url": "https://x/img.jpg"}
    mock_wp.create_profile.return_value = {
        "success": True, "id": 100, "link": "https://www.balkutusu.com/profil/test/",
    }
    mock_wp_api.return_value = mock_wp

    def _pass_gate(listing):
        listing = lh.validate_publish_allowed(listing, after_gate=False)
        listing["seo_score"] = 85
        listing["geo_score"] = 85
        listing["publish_allowed"] = True
        listing["publish_blockers"] = []
        return listing

    mock_gate.side_effect = _pass_gate

    res = lh.create_listing(_base())
    lid = res["listing"]["id"]
    lh.upload_media(lid, "cover.jpg", b"bytes", "image/jpeg", set_cover=True)
    pub = lh.publish_listing(lid)
    assert pub["success"] is True
    assert pub["listing"]["wp_post_id"] == 100
    assert pub["listing"]["status"] == "active"
    mock_wp.create_profile.assert_called_once()
