"""OpenStreetMap / Nominatim GEO provider."""

from __future__ import annotations

from urllib.parse import quote_plus

from .base import DEFAULT_TIMEOUT, make_result, safe_get

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


class OpenStreetMapProvider:
    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def search(query: str, limit: int = 10, country: str = "tr") -> list[dict]:
        if not query or not query.strip():
            return []

        q = quote_plus(f"{query.strip()}, {country.upper()}" if country else query.strip())
        url = f"{NOMINATIM_URL}?format=json&q={q}&limit={limit}&addressdetails=1"
        resp = safe_get(url, timeout=DEFAULT_TIMEOUT)
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except ValueError:
            return []

        results = []
        for item in data if isinstance(data, list) else []:
            addr = item.get("address") or {}
            location = {
                "name": item.get("display_name", ""),
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "type": item.get("type"),
                "class": item.get("class"),
                "city": addr.get("city") or addr.get("town") or addr.get("province"),
                "district": addr.get("suburb") or addr.get("city_district") or addr.get("county"),
                "neighbourhood": addr.get("neighbourhood") or addr.get("quarter"),
            }
            results.append(make_result(
                "osm",
                query,
                title=item.get("display_name", ""),
                snippet=item.get("display_name", ""),
                location=location,
                raw=item,
            ))
        return results

    @staticmethod
    def geo_clusters(location_keyword: str, mahalleler: list[str] | None = None) -> list[dict]:
        clusters = []
        base_results = OpenStreetMapProvider.search(location_keyword, limit=5)
        clusters.extend(base_results)

        for m in (mahalleler or [])[:8]:
            sub = OpenStreetMapProvider.search(f"{m}, {location_keyword}", limit=3)
            clusters.extend(sub)

        seen: set[str] = set()
        unique = []
        for c in clusters:
            key = (c.get("title") or "")[:80]
            if key and key not in seen:
                seen.add(key)
                unique.append(c)
        return unique
