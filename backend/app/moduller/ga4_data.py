"""
GA4 Data API — canlı trafik ve grafik verisi (service account)
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app import config

logger = logging.getLogger("hive.ga4")

CREDENTIALS_DIR = Path(__file__).resolve().parent.parent.parent / "credentials"
DEFAULT_SA_FILE = CREDENTIALS_DIR / "ga4-service-account.json"


def _property_id() -> str:
    raw = (config.get("GA4_PROPERTY_ID") or "").strip()
    return raw.replace("properties/", "")


def _service_account_path() -> Path | None:
    custom = (config.get("GA4_SERVICE_ACCOUNT_FILE") or "").strip()
    path = Path(custom) if custom else DEFAULT_SA_FILE
    if path.is_file():
        return path
    return None


def data_api_ready() -> dict[str, Any]:
    prop = _property_id()
    sa = _service_account_path()
    return {
        "ready": bool(prop and sa),
        "property_id": prop,
        "service_account_configured": bool(sa),
        "service_account_path": str(sa) if sa else str(DEFAULT_SA_FILE),
        "hint": None if (prop and sa) else _setup_hint(prop, sa),
    }


def _setup_hint(prop: str, sa: Path | None) -> str:
    if not sa:
        return "Analytics Hub → Service account JSON yükle (Property ID otomatik bulunur)"
    if not prop:
        return "JSON yükledikten sonra «Property ID Otomatik Bul» butonuna basın"
    return ""


def _get_admin_client():
    try:
        from google.analytics.admin import AnalyticsAdminServiceClient
    except ImportError as e:
        raise RuntimeError(
            "google-analytics-admin paketi eksik. backend dizininde: pip install google-analytics-admin"
        ) from e

    sa = _service_account_path()
    if not sa:
        raise RuntimeError(_setup_hint(_property_id(), None))

    return AnalyticsAdminServiceClient.from_service_account_file(str(sa))


def discover_property_id(measurement_id: str | None = None) -> dict[str, Any]:
    """Measurement ID (G-...) ile GA4 mülk kimliğini Admin API üzerinden bul."""
    mid = (measurement_id or config.get("GA4_MEASUREMENT_ID") or "").strip().upper()
    if not mid:
        return {"success": False, "error": "Measurement ID tanımlı değil"}

    if not _service_account_path():
        return {"success": False, "error": "Önce service account JSON yükleyin"}

    try:
        client = _get_admin_client()
        for account in client.list_account_summaries():
            for prop_summary in account.property_summaries:
                prop_resource = prop_summary.property
                prop_id = prop_resource.split("/")[-1]
                try:
                    streams = client.list_data_streams(parent=prop_resource)
                except Exception:
                    continue
                for stream in streams:
                    ws = getattr(stream, "web_stream_data", None)
                    if not ws:
                        continue
                    stream_mid = (getattr(ws, "measurement_id", "") or "").strip().upper()
                    if stream_mid == mid:
                        from app.moduller.api_key_manager import set_key
                        set_key("ga4_property_id", prop_id)
                        stream_id = stream.name.split("/")[-1] if stream.name else ""
                        return {
                            "success": True,
                            "property_id": prop_id,
                            "stream_id": stream_id,
                            "property_name": prop_summary.display_name,
                            "measurement_id": mid,
                            "message": f"Mülk bulundu: {prop_summary.display_name} ({prop_id})",
                        }
        return {
            "success": False,
            "error": (
                f"{mid} için mülk bulunamadı. GA4 → Yönetici → Mülk erişimi → "
                "service account e-postasını Görüntüleyici olarak ekleyin."
            ),
        }
    except Exception as e:
        logger.warning("GA4 property discover hatası: %s", e)
        return {"success": False, "error": str(e)}


def _get_client():
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
    except ImportError as e:
        raise RuntimeError(
            "google-analytics-data paketi eksik. backend dizininde: pip install google-analytics-data"
        ) from e

    sa = _service_account_path()
    if not sa:
        raise RuntimeError(_setup_hint(_property_id(), None))

    return BetaAnalyticsDataClient.from_service_account_file(str(sa))


def _property_resource() -> str:
    prop = _property_id()
    if not prop:
        raise RuntimeError(_setup_hint("", None))
    return f"properties/{prop}"


def get_realtime() -> dict[str, Any]:
    """Son 30 dk gerçek zamanlı özet."""
    try:
        from google.analytics.data_v1beta.types import (
            Dimension,
            Metric,
            RunRealtimeReportRequest,
        )
    except ImportError as e:
        return {"success": False, "error": str(e), "mode": "setup_required"}

    try:
        client = _get_client()
        req = RunRealtimeReportRequest(
            property=_property_resource(),
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
            ],
            dimensions=[Dimension(name="country")],
            limit=10,
        )
        resp = client.run_realtime_report(req)

        active_users = 0
        page_views = 0
        countries: list[dict[str, Any]] = []

        for row in resp.rows:
            m = [int(float(v.value or 0)) for v in row.metric_values]
            d = row.dimension_values[0].value if row.dimension_values else ""
            if m:
                active_users += m[0]
                if len(m) > 1:
                    page_views += m[1]
            if d:
                countries.append({"country": d, "activeUsers": m[0] if m else 0})

        countries.sort(key=lambda x: x["activeUsers"], reverse=True)

        return {
            "success": True,
            "active_users": active_users,
            "page_views_30min": page_views,
            "countries": countries[:5],
            "updated_at": date.today().isoformat(),
            "mode": "live",
        }
    except Exception as e:
        logger.warning("GA4 realtime hatası: %s", e)
        return {"success": False, "error": str(e), "mode": "error", "setup": data_api_ready()}


def get_chart(days: int = 7) -> dict[str, Any]:
    """Son N gün oturum ve sayfa görüntüleme."""
    try:
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )
    except ImportError as e:
        return {"success": False, "error": str(e), "data": []}

    days = max(1, min(days, 90))
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    end = date.today().isoformat()

    try:
        client = _get_client()
        req = RunReportRequest(
            property=_property_resource(),
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
            ],
            order_bys=[{"dimension": {"dimension_name": "date"}}],
        )
        resp = client.run_report(req)
        rows = []
        for row in resp.rows:
            d = row.dimension_values[0].value
            metrics = [int(float(v.value or 0)) for v in row.metric_values]
            rows.append({
                "date": d,
                "label": f"{d[6:8]}.{d[4:6]}" if len(d) == 8 else d,
                "sessions": metrics[0] if metrics else 0,
                "users": metrics[1] if len(metrics) > 1 else 0,
                "pageviews": metrics[2] if len(metrics) > 2 else 0,
            })
        return {"success": True, "data": rows, "days": days, "mode": "live"}
    except Exception as e:
        logger.warning("GA4 chart hatası: %s", e)
        return {"success": False, "error": str(e), "data": [], "setup": data_api_ready()}


def get_top_pages(limit: int = 10) -> dict[str, Any]:
    """Son 7 gün en çok görüntülenen sayfalar."""
    try:
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )
    except ImportError as e:
        return {"success": False, "error": str(e), "pages": []}

    limit = max(1, min(limit, 25))
    start = (date.today() - timedelta(days=6)).isoformat()
    end = date.today().isoformat()

    try:
        client = _get_client()
        req = RunReportRequest(
            property=_property_resource(),
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="screenPageViews"), Metric(name="activeUsers")],
            order_bys=[{"metric": {"metric_name": "screenPageViews"}, "desc": True}],
            limit=limit,
        )
        resp = client.run_report(req)
        pages = []
        for row in resp.rows:
            path = row.dimension_values[0].value
            views = int(float(row.metric_values[0].value or 0))
            users = int(float(row.metric_values[1].value or 0)) if len(row.metric_values) > 1 else 0
            pages.append({"path": path, "views": views, "users": users})
        return {"success": True, "pages": pages, "mode": "live"}
    except Exception as e:
        logger.warning("GA4 top pages hatası: %s", e)
        return {"success": False, "error": str(e), "pages": [], "setup": data_api_ready()}


def save_service_account_json(content: bytes) -> dict[str, Any]:
    """Service account JSON dosyasını credentials/ altına kaydet."""
    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"success": False, "error": "Geçersiz JSON dosyası"}

    if data.get("type") != "service_account" or not data.get("client_email"):
        return {"success": False, "error": "Bu bir Google service account JSON dosyası değil"}

    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    dest = DEFAULT_SA_FILE
    dest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    try:
        from app.moduller.api_key_manager import set_key
        set_key("ga4_service_account_file", str(dest))
    except Exception:
        pass

    discover = discover_property_id()
    result: dict[str, Any] = {
        "success": True,
        "message": "Service account kaydedildi",
        "client_email": data.get("client_email"),
        "path": str(dest),
        "next_step": f"GA4 → Yönetici → Mülk erişimi → {data.get('client_email')} e-postasını Görüntüleyici olarak ekle",
        "discover": discover,
    }
    if discover.get("success"):
        result["message"] += f" — Property ID: {discover['property_id']}"
        result["property_id"] = discover["property_id"]
        result["next_step"] = "Grafikler hazır — sayfayı yenileyin"
    return result
