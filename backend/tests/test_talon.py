"""Talon modül testleri."""

import json
import tempfile
from pathlib import Path

import pytest

from app.moduller.talon import anahtar_kelime_uret, export_kelimeler, kelime_grupla
from app.moduller.talon_extensions import (
    gecmis_migrate,
    liste_sektorler,
    rakip_keyword_gap,
    rank_tracker_aktar,
    sektor_sablonu,
    trend_analiz,
)
from app.moduller.talon_utils import LocationService


def test_kusadasi_location():
    sehir, ilc, cad, sok = LocationService.lokasyon_ara("kuşadası")
    assert sehir == "Kuşadası"
    assert len(ilc) >= 5
    assert len(cad) >= 3


def test_anahtar_kelime_uret_escort():
    kw, sid = anahtar_kelime_uret("kuşadası escort", 5, "kuşadası", sektor="escort")
    assert len(kw) == 5
    assert sid
    assert "kelime" in kw[0]
    assert "rekabet" in kw[0]


def test_anahtar_kelime_uret_gece_hayati():
    kw, _ = anahtar_kelime_uret("kuşadası gece hayatı", 5, "kuşadası", sektor="gece_hayati")
    assert len(kw) == 5
    joined = " ".join(k["kelime"].lower() for k in kw)
    assert any(t in joined for t in ["bar", "kulüp", "eğlence", "gece", "müzik", "club", "pub", "disco"])


def test_sektor_sablonlari():
    sektorler = liste_sektorler()
    assert len(sektorler) >= 5
    assert sektor_sablonu("emlak") is not None
    assert sektor_sablonu("seo_dijital") is not None


def test_export_csv_quoting():
    kw, _ = anahtar_kelime_uret("test", 2, "ankara", sektor="emlak")
    out = export_kelimeler(kw, "csv")
    assert "Kelime" in out["content"]
    assert out["format"] == "csv"


def test_kelime_grupla():
    items = [
        {"kelime": "Kuşadası vip escort", "rekabet": "düşük", "arama_hacmi": "100-500", "rakip_var": False},
        {"kelime": "Gece escort kuşadası", "rekabet": "orta", "arama_hacmi": "500-1000", "rakip_var": True},
    ]
    gruplar = kelime_grupla(items)
    assert isinstance(gruplar, dict)
    assert sum(len(v) for v in gruplar.values()) >= 1


def test_trend_analiz(sample_keywords):
    result = trend_analiz(sample_keywords, "Kuşadası")
    assert result["status"] == "aktif"
    assert result["analiz_sayisi"] == 2
    assert result["aktif_sezon"] in ("yaz", "kis", "ilkbahar", "sonbahar")
    assert "aylik_tahmin" in result["analizler"][0]


def test_rakip_keyword_gap(sample_keywords):
    result = rakip_keyword_gap(sample_keywords, rakip_domain="rakip-site.com", limit=10)
    assert result["status"] == "aktif"
    assert "gap_kelimeler" in result
    assert isinstance(result["gap_kelimeler"], list)


def test_rank_tracker_aktar(sample_keywords, tmp_path, monkeypatch):
    rt_file = tmp_path / "rank_tracker.json"
    monkeypatch.setattr(
        "app.moduller.ranktracker.RT_DB_PATH",
        str(rt_file),
    )
    result = rank_tracker_aktar(sample_keywords, domain="balkutusu.com", sehir="Kuşadası")
    assert result["toplam_kaydedilen"] == 2
    assert rt_file.exists()


def test_gecmis_migrate_dry_run(monkeypatch, tmp_path):
    legacy = tmp_path / "talon_history.json"
    legacy.write_text(json.dumps([{
        "id": "test1234",
        "ana_kelime": "test",
        "sehir": "ankara",
        "adet": 2,
        "negatif_filtre": "",
        "kelimeler": [
            {"kelime": "ankara test", "rekabet": "orta", "arama_hacmi": "100-500", "rakip_var": False},
        ],
        "timestamp": "2026-01-01T00:00:00",
    }]), encoding="utf-8")
    monkeypatch.setattr("app.moduller.talon_extensions.LEGACY_HISTORY", legacy)
    monkeypatch.setattr("app.moduller.talon_extensions.search_getir", lambda _id: None)

    result = gecmis_migrate(dry_run=True)
    assert result["tasinan"] == 1
    assert result["dry_run"] is True
