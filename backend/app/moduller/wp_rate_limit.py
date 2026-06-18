"""WordPress API rate limiter — dakikada 60 istek / client IP."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

_LIMIT = 60
_WINDOW = 60
_buckets: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def check_wp_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    now = time.time()
    with _lock:
        hits = [t for t in _buckets[client] if now - t < _WINDOW]
        if len(hits) >= _LIMIT:
            raise HTTPException(
                status_code=429,
                detail="WordPress API rate limit aşıldı (60/dk). Biraz bekleyin.",
            )
        hits.append(now)
        _buckets[client] = hits
