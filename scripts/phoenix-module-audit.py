#!/usr/bin/env python3
"""Operation Phoenix — modül production audit (116 modül).

Kullanım:
  python scripts/phoenix-module-audit.py
  python scripts/phoenix-module-audit.py --json roadmap/phoenix-audit.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_MOD = ROOT / "backend" / "app" / "moduller"
FRONTEND_PAGES = ROOT / "frontend" / "src" / "pages"
ACADEMY_ENC = ROOT / "docs" / "academy" / "06-modul-ansiklopedisi"
SCREENSHOTS = ROOT / "docs" / "academy" / "screenshots"
OUT_DEFAULT = ROOT / "roadmap" / "phoenix-audit.json"

sys.path.insert(0, str(ROOT / "backend"))

from app.moduller.liste import MODULLER  # noqa: E402


def _page_file_candidates(mod_id: str) -> list[Path]:
    parts = mod_id.split("_")
    pascal = "".join(p[:1].upper() + p[1:] for p in parts)
    names = [
        f"{pascal}.js",
        f"{pascal}.jsx",
        f"{mod_id}.js",
        f"{mod_id}.jsx",
    ]
    return [FRONTEND_PAGES / n for n in names if (FRONTEND_PAGES / n).is_file()]


def _score_doc(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {"documentation": 0, "workflow": 0, "api": 0, "screenshot": 0, "academy": 0}
    text = path.read_text(encoding="utf-8")
    slug = path.stem
    scores = {
        "documentation": 40,
        "workflow": 10,
        "api": 10,
        "screenshot": 10,
        "academy": 30,
    }
    if len(text) > 800:
        scores["documentation"] = 70
    if "published" in text[:400]:
        scores["documentation"] += 20
    elif "auto-draft" in text[:400]:
        scores["documentation"] = 30
    if "```mermaid" in text or "## Workflow" in text or "## İş akışı" in text:
        scores["workflow"] = 80
    if "/api/" in text or "## API" in text:
        scores["api"] = 80
    if (SCREENSHOTS / slug).is_dir() and any((SCREENSHOTS / slug).iterdir()):
        scores["screenshot"] = 90
    elif "Screenshot" in text:
        scores["screenshot"] = 30
    if "AI_UPDATE_SLOT" in text or "<!-- TODO -->" in text:
        scores["academy"] = 50
    if "status: \"published\"" in text or 'status: "published"' in text:
        scores["academy"] = 95
    return scores


def audit_module(mod: dict) -> dict:
    mid = mod["id"]
    py_path = BACKEND_MOD / f"{mid}.py"
    doc_path = ACADEMY_ENC / f"{mid}.md"
    pages = _page_file_candidates(mid)

    code = 90 if py_path.is_file() else 0
    ui = 85 if pages else 40
    api = 80 if mod.get("endpoint") else 30

    doc_scores = _score_doc(doc_path)
    doc_total = round(sum(doc_scores.values()) / 5, 1)

    # HIVE Quality Score weights (simplified for automation)
    dimensions = {
        "code": code,
        "ui": ui,
        "ux": 70 if pages else 40,
        "api": api,
        "documentation": doc_scores["documentation"],
        "performance": 70,
        "security": 75,
        "accessibility": 60,
        "production": 80 if code and pages and doc_path.is_file() else 35,
    }
    total = round(sum(dimensions.values()) / len(dimensions), 1)
    ready = total >= 95 and doc_scores["academy"] >= 90

    gaps = []
    if not py_path.is_file():
        gaps.append("backend_missing")
    if not pages:
        gaps.append("frontend_page_missing")
    if not doc_path.is_file():
        gaps.append("academy_doc_missing")
    if doc_scores["workflow"] < 50:
        gaps.append("workflow_missing")
    if doc_scores["api"] < 50:
        gaps.append("api_section_missing")
    if doc_scores["screenshot"] < 50:
        gaps.append("screenshot_missing")
    if "auto-draft" in (doc_path.read_text(encoding="utf-8")[:500] if doc_path.is_file() else ""):
        gaps.append("doc_auto_draft")

    return {
        "id": mid,
        "name": mod.get("ad", mid),
        "group": mod.get("grup", ""),
        "endpoint": mod.get("endpoint", ""),
        "scores": dimensions,
        "doc_breakdown": doc_scores,
        "total": total,
        "production_ready": ready,
        "gaps": gaps,
        "has_backend": py_path.is_file(),
        "has_frontend": bool(pages),
        "has_academy": doc_path.is_file(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Phoenix module audit")
    parser.add_argument("--json", default=str(OUT_DEFAULT), help="Output JSON path")
    args = parser.parse_args()

    results = [audit_module(m) for m in MODULLER]
    results.sort(key=lambda x: x["total"])

    ready_count = sum(1 for r in results if r["production_ready"])
    below_95 = [r for r in results if r["total"] < 95]

    report = {
        "operation": "PHOENIX",
        "module_count": len(results),
        "production_ready": ready_count,
        "below_threshold_95": len(below_95),
        "threshold": 95,
        "modules": results,
        "summary_gaps": {},
    }
    for r in results:
        for g in r["gaps"]:
            report["summary_gaps"][g] = report["summary_gaps"].get(g, 0) + 1

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Phoenix Audit: {len(results)} modül")
    print(f"  Production ready (≥95): {ready_count}")
    print(f"  Below 95: {len(below_95)}")
    print(f"  Report: {out}")
    if below_95[:5]:
        print("  Lowest scores:")
        for r in below_95[:5]:
            print(f"    - {r['id']}: {r['total']} ({', '.join(r['gaps'][:3])})")


if __name__ == "__main__":
    main()
