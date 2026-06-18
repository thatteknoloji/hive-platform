"""Balkutusu SEO Index Recovery Sprint — unit tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.moduller.indexing_fix import (
    build_redirect_map,
    classify_url,
    enhanced_robots_content,
    propose_clean_url,
    run_balkutusu_index_recovery,
)
from app.moduller.storyforge_categories import normalize_seo_slug

SITE = "https://www.balkutusu.com"


class TestSlugNormalizer:
    def test_duplicate_kusadas_removed(self):
        slug = normalize_seo_slug("kusadas-kusadas-kusadas-escort-ne-kadar-sss")
        assert "kusadas-kusadas" not in slug
        assert slug.startswith("kusadasi")
        assert slug.count("kusadasi") == 1

    def test_escort_duplicate_removed(self):
        slug = normalize_seo_slug("escort-escort-bayan")
        assert slug.count("escort") == 1

    def test_gece_hayati_duplicate(self):
        slug = normalize_seo_slug("gece-hayati-gece-hayati-liman")
        assert slug.count("gece-hayati") == 1

    def test_turkish_chars_normalized(self):
        slug = normalize_seo_slug("kuşadası gece hayatı")
        assert "ş" not in slug
        assert "ı" not in slug
        assert "kusadasi" in slug
        assert "gece-hayati" in slug

    def test_max_words(self):
        slug = normalize_seo_slug("a-b-c-d-e-f-g-h-i-j-k-l-m", max_words=7)
        assert len(slug.split("-")) <= 7


class TestStoryQueryRedirect:
    def test_luna_to_profil(self):
        url = propose_clean_url(f"{SITE}/?story=luna")
        assert url == f"{SITE}/profil/luna/"

    def test_gece_modu_to_hikaye(self):
        url = propose_clean_url(f"{SITE}/?story=gece-modu")
        assert url == f"{SITE}/hikaye/gece-modu/"

    def test_redirect_map_includes_story_queries(self):
        inventory = [
            {
                "url": f"{SITE}/?story=bella",
                "content_type": "story_query",
                "issues": ["query_param_story"],
                "proposed_url": f"{SITE}/profil/bella/",
            }
        ]
        redirects = build_redirect_map(inventory)
        olds = [r["old_url"] for r in redirects]
        assert any("story=bella" in o for o in olds)


class TestCanonicalGeneration:
    def test_legacy_profil_path(self):
        url = propose_clean_url(f"{SITE}/profiller/luna/")
        assert url == f"{SITE}/profil/luna/"

    def test_legacy_hikaye_path(self):
        url = propose_clean_url(f"{SITE}/hikayeler/gece-hikaye/")
        assert url == f"{SITE}/hikaye/gece-hikaye/"

    def test_sss_slug_cleanup(self):
        bad = f"{SITE}/kusadas-kusadas-escort-yorumlar-nasil-sss/"
        url = propose_clean_url(bad)
        assert "/sss/" in url
        assert "kusadasi-escort-yorumlari" in url or "escort-yorumlari" in url


class TestSitemapExclusion:
    def test_story_query_classified_noindex(self):
        info = classify_url(f"{SITE}/?story=luna")
        assert info["content_type"] == "story_query"
        assert "query_param_story" in info["issues"]

    def test_search_classified(self):
        info = classify_url(f"{SITE}/?s=escort")
        assert info["content_type"] in ("search", "story_query", "other")


class TestRobotsPolicy:
    def test_enhanced_robots_allows_index_paths(self):
        content = enhanced_robots_content(SITE)
        assert "Allow: /profil/" in content
        assert "Allow: /hikaye/" in content
        assert "wp-sitemap.xml" in content
        assert "Disallow: /*?s=" in content


class TestRecoveryRun:
    @patch("app.moduller.indexing_fix.fetch_sitemap_urls")
    @patch("app.moduller.campaign_engine.create_campaign")
    @patch("app.moduller.rank_index_watcher.track_keyword")
    @patch("app.moduller.rank_index_watcher.register_project")
    def test_run_generates_reports(
        self, mock_register, mock_track, mock_create, mock_fetch, tmp_path, monkeypatch,
    ):
        mock_fetch.return_value = {
            "success": True,
            "sitemap_url": f"{SITE}/wp-sitemap.xml",
            "urls": [
                f"{SITE}/profiller/luna/",
                f"{SITE}/kusadas-kusadas-escort-sss/",
            ],
            "count": 2,
            "errors": [],
        }
        mock_register.return_value = {"success": True}
        mock_track.return_value = {"success": True}
        mock_create.return_value = {"success": True, "campaign": {"campaign_id": "camp-test"}}
        reports = tmp_path / "reports"
        monkeypatch.setattr("app.moduller.indexing_fix.REPORTS_DIR", reports)

        with patch("app.moduller.indexing_fix._emit_brain"):
            result = run_balkutusu_index_recovery(SITE, analyze_quality=False)

        assert result["success"] is True
        assert Path(result["redirect_map_path"]).exists()
        assert Path(result["report_path"]).exists()
        data = json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))
        assert data["inventory_total"] >= 2
        assert data["redirects_generated"] >= 1
