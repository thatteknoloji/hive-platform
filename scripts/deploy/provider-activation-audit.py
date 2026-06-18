#!/usr/bin/env python3
"""HIVE production provider activation audit — no secrets in output."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / "backend" / ".env"
ENV_EXAMPLE = ROOT / "backend" / ".env.example"
DOMAIN = os.environ.get("HIVE_DOMAIN", "https://hive.thiqos.com")

ENDPOINTS = [
    "/api/providers/list",
    "/api/data-miner/health",
    "/api/authority-factory/health",
    "/api/google-sites/health",
    "/api/github-pages/health",
    "/api/publisher-hub/health",
    "/api/campaigns/health",
    "/api/mission-control/dashboard",
]


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def fetch(path: str, api_key: str) -> tuple[int, dict | str]:
    req = urllib.request.Request(
        f"{DOMAIN}{path}",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body[:500]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body[:500]
    except Exception as e:
        return 0, str(e)


def is_set(val: str | None) -> bool:
    return bool(val and str(val).strip())


def compare_env(prod: dict[str, str], example: dict[str, str]) -> dict[str, list[str]]:
    example_keys = {k for k in example if k and not k.startswith("#")}
    prod_keys = set(prod)
    missing_in_prod = sorted(k for k in example_keys if k not in prod_keys)
    empty_in_prod = sorted(
        k for k in example_keys
        if k in prod and not is_set(prod.get(k))
    )
    extra_in_prod = sorted(k for k in prod_keys if k not in example_keys)
    return {
        "missing_keys": missing_in_prod,
        "empty_keys": empty_in_prod,
        "extra_keys": extra_in_prod,
    }


def classify_provider(p: dict) -> str:
    pid = p.get("provider") or p.get("id") or ""
    status = (p.get("status") or "").lower()
    last_error = (p.get("last_error") or p.get("error") or "").lower()
    metadata = p.get("metadata") or {}
    tokens = metadata.get("tokens") or {}

    if "invalid_grant" in last_error or "invalid_grant" in json.dumps(metadata).lower():
        return "needs_manual_oauth"
    if status == "login_required" or "login_required" in last_error or "google_login" in last_error:
        return "needs_login"
    if status == "healthy" or (p.get("connected") and status not in ("critical", "provider_missing", "warning")):
        return "working"
    if status in ("provider_missing", "not_configured") or not tokens.get("token_present", True) and not p.get("configured"):
        keys_present = tokens.get("keys_present") or []
        keys_expected = tokens.get("keys_expected") or []
        if keys_expected and not keys_present:
            return "missing_key"
        return "missing_key" if status in ("provider_missing", "not_configured") else "configured_but_failed"
    if status in ("critical", "warning", "configured_but_failed") or p.get("configured"):
        return "configured_but_failed"
    return "configured_but_failed"


def main() -> int:
    prod = load_env(ENV_FILE)
    example = load_env(ENV_EXAMPLE)
    api_key = prod.get("HIVE_API_KEY", "").strip()
    if not api_key:
        print("ERROR: HIVE_API_KEY missing in backend/.env", file=sys.stderr)
        return 1

    results: dict[str, object] = {"domain": DOMAIN, "endpoints": {}, "env_compare": compare_env(prod, example)}
    for ep in ENDPOINTS:
        code, data = fetch(ep, api_key)
        results["endpoints"][ep] = {"http_status": code, "body": data}

    out_path = ROOT / "reports" / "provider-activation-audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
