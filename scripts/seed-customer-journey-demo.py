#!/usr/bin/env python3
"""Seed Operation Phoenix Customer Journey demo project."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.moduller import project_context, project_engine  # noqa: E402

JOURNEY_FILE = ROOT / "roadmap" / "customer-journey.json"
OUT_FILE = ROOT / "roadmap" / "demo-project.json"

DEMO_NAME = "Phoenix Demo — Thiqos Turizm"
DEMO_SECTOR = "tourism"
DEMO_DOMAIN = "demo.thiqos.com"
DEMO_BRIEF = (
    "Antalya merkezli kültür ve doğa tur operatörü. Hedef: Avrupa ve Türkiye içi "
    "organik trafik. Ana kelimeler: antalya kültür turu, kapadokya balon turu, "
    "türkiye özel tur, antalya çıkışlı turlar. Çok dilli site (TR/EN/DE), "
    "yerel entity graph ve authority mesh ile SERP savunması."
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _find_demo_project() -> dict | None:
    result = project_engine.list_projects(search="Phoenix Demo", limit=200)
    for project in result.get("projects", []):
        meta = project.get("metadata") or {}
        if meta.get("phoenix_demo") or meta.get("customer_journey_demo"):
            return project
    for project in result.get("projects", []):
        if project.get("name") == DEMO_NAME:
            return project
    return None


def main() -> None:
    journey = json.loads(JOURNEY_FILE.read_text(encoding="utf-8"))
    existing = _find_demo_project()

    metadata = {
        "phoenix_demo": True,
        "customer_journey_demo": True,
        "journey_version": journey.get("version", "2.0.0"),
        "scenario": "thiqos_tourism",
        "seeded_at": _now(),
        "keywords": [
            "antalya kültür turu",
            "kapadokya balon turu",
            "türkiye özel tur",
            "antalya çıkışlı turlar",
        ],
        "locales": ["tr", "en", "de"],
    }

    if existing:
        pid = existing["id"]
        project_engine.update_project(
            pid,
            {
                "name": DEMO_NAME,
                "sector": DEMO_SECTOR,
                "domain": DEMO_DOMAIN,
                "business_brief": DEMO_BRIEF,
                "status": "active",
                "deploy_mode": "hive_cloud",
                "metadata": metadata,
            },
        )
        action = "updated"
    else:
        created = project_engine.create_project(
            name=DEMO_NAME,
            sector=DEMO_SECTOR,
            domain=DEMO_DOMAIN,
            business_brief=DEMO_BRIEF,
            deploy_mode="hive_cloud",
            status="active",
        )
        if not created.get("success"):
            print(f"ERROR: create_project failed: {created}", file=sys.stderr)
            sys.exit(1)
        pid = created["project"]["id"]
        project_engine.update_project(pid, {"metadata": metadata})
        action = "created"

    ctx = project_context.set_active_project(pid)
    if not ctx.get("success"):
        print(f"ERROR: set_active_project failed: {ctx}", file=sys.stderr)
        sys.exit(1)

    bind_result = project_engine.bind_project_domain(pid, DEMO_DOMAIN, include_www=True)
    if not bind_result.get("success"):
        print(f"WARN: domain bind failed: {bind_result}", file=sys.stderr)

    project = project_engine.get_project(pid)
    manifest = {
        "operation": "OPERATION_PHOENIX",
        "customer_journey": journey.get("metric"),
        "action": action,
        "seeded_at": _now(),
        "project_id": pid,
        "active_project_id": pid,
        "name": DEMO_NAME,
        "sector": DEMO_SECTOR,
        "domain": DEMO_DOMAIN,
        "status": "active",
        "journey_steps": journey.get("journey_order", []),
        "project": project.get("project") if project else None,
    }
    OUT_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Demo project {action}: {pid}")
    print(f"Active project: {pid}")
    print(f"Domain: {DEMO_DOMAIN}")
    print(f"Manifest: {OUT_FILE}")


if __name__ == "__main__":
    main()
