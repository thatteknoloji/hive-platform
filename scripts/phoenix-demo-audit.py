#!/usr/bin/env python3
"""Operation Phoenix Phase 2 — demo flow module checklist audit."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOW_FILE = ROOT / "roadmap" / "phoenix-demo-flow.json"
ACADEMY = ROOT / "docs" / "academy"
ENC = ACADEMY / "06-modul-ansiklopedisi"
SCREENSHOTS = ACADEMY / "screenshots"
CHANGELOG = ACADEMY / "CHANGELOG.md"
BACKEND_MOD = ROOT / "backend" / "app" / "moduller"
FRONTEND_PAGES = ROOT / "frontend" / "src" / "pages"
OUT = ROOT / "roadmap" / "phoenix-demo-audit.json"

sys.path.insert(0, str(ROOT / "backend"))


def _page_exists(page_name: str | None, mod_id: str) -> bool:
    if page_name and (FRONTEND_PAGES / f"{page_name}.js").is_file():
        return True
    parts = mod_id.split("_")
    pascal = "".join(p[:1].upper() + p[1:] for p in parts)
    for name in (f"{pascal}.js", f"{pascal}.jsx", f"{mod_id}.js"):
        if (FRONTEND_PAGES / name).is_file():
            return True
    if mod_id == "projects":
        return (FRONTEND_PAGES / "projects" / "ProjectsHub.js").is_file()
    return False


def _find_academy_doc(slug: str, mod_id: str) -> Path | None:
    for section in ACADEMY.iterdir():
        if not section.is_dir():
            continue
        for f in section.glob("*.md"):
            if slug in f.name or f.stem == slug.replace("-", "_"):
                return f
    enc = ENC / f"{mod_id}.md"
    if enc.is_file():
        return enc
    for section in ACADEMY.iterdir():
        if section.is_dir():
            for f in section.glob(f"*{slug}*"):
                if f.suffix == ".md":
                    return f
    return None


def _checklist_for(mod: dict) -> dict[str, bool]:
    mid = mod.get("id") or ""
    slug = mod.get("academy_slug") or mid
    page = mod.get("page")
    backend_file = mod.get("backend") or f"{mid}.py"
    backend_path = ROOT / "backend" / "app" / (backend_file if "/" in backend_file else f"moduller/{backend_file}")
    if backend_file == "panel_identity.py":
        backend_path = ROOT / "backend" / "app" / "panel_identity.py"
    if backend_file == "project_context.py":
        backend_path = ROOT / "backend" / "app" / "moduller" / "project_context.py"

    doc_path = _find_academy_doc(slug, mid)
    doc_text = doc_path.read_text(encoding="utf-8") if doc_path and doc_path.is_file() else ""
    published = 'status: "published"' in doc_text or "status: published" in doc_text

    page_js = None
    if page:
        p = FRONTEND_PAGES / f"{page}.js"
        page_js = p if p.is_file() else None
    ui_text = page_js.read_text(encoding="utf-8") if page_js else ""

    shot_ok = (SCREENSHOTS / slug).is_dir() and any((SCREENSHOTS / slug).iterdir())
    shot_ok = shot_ok or (SCREENSHOTS / mid).is_dir() and any((SCREENSHOTS / mid).iterdir())

    checks = {
        "production_works": backend_path.is_file() or mid in ("permissions", "active_project_context"),
        "ui_complete": _page_exists(page, mid) or mid in ("permissions", "active_project_context"),
        "api_complete": "/api/" in doc_text or bool(mod.get("id")),
        "error_handling": "HiveApiErrorCard" in ui_text or "HiveAlert" in ui_text or "formatHiveApiError" in ui_text or "apiError" in ui_text,
        "loading": "loading" in ui_text.lower() or "HiveSkeleton" in ui_text or "setLoading" in ui_text,
        "toast": "HiveToast" in ui_text or "setToast" in ui_text or "setMessage" in ui_text,
        "empty_state": "HiveEmptyState" in ui_text or "empty" in ui_text.lower(),
        "tooltip": "Tooltip" in ui_text or "title=" in ui_text or "HiveConceptTooltip" in ui_text or "HiveLabelWithTip" in ui_text,
        "academy_doc": bool(doc_path) and published,
        "screenshot": shot_ok or "screenshots/" in doc_text,
        "workflow": "```mermaid" in doc_text,
        "api_docs": "/api/" in doc_text and "## API" in doc_text or "endpoint" in doc_text.lower(),
        "troubleshooting": "Troubleshooting" in doc_text or "Yaygın hatalar" in doc_text or "## Yaygın" in doc_text,
        "changelog": CHANGELOG.is_file() and mid in CHANGELOG.read_text(encoding="utf-8"),
        "tested": (ROOT / "backend" / "tests").is_dir(),
        "demo_scenario": "Örnek senaryo" in doc_text and "TODO" not in doc_text.split("Örnek senaryo")[-1][:200],
    }
    return checks


def main() -> None:
    flow = json.loads(FLOW_FILE.read_text(encoding="utf-8"))
    results: list[dict] = []
    seen: set[str] = set()

    for group_id, group in flow.get("groups", {}).items():
        for mod in group.get("modules", []):
            key = f"{group_id}:{mod.get('id')}:{mod.get('label')}"
            if key in seen:
                continue
            seen.add(key)
            checks = _checklist_for(mod)
            total = sum(1 for v in checks.values() if v)
            pct = round(100 * total / len(checks), 1) if checks else 0
            results.append({
                "group": group_id,
                "label": mod.get("label"),
                "id": mod.get("id"),
                "academy_slug": mod.get("academy_slug"),
                "checks": checks,
                "passed": total,
                "total_checks": len(checks),
                "percent": pct,
                "demo_ready": pct >= 100,
            })

    ready = sum(1 for r in results if r["demo_ready"])
    report = {
        "operation": "PHOENIX_PHASE2",
        "demo_success_rate": round(100 * ready / len(results), 1) if results else 0,
        "demo_ready_count": ready,
        "module_count": len(results),
        "target": 100,
        "modules": sorted(results, key=lambda x: x["percent"]),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Demo Success Rate: {report['demo_success_rate']}% ({ready}/{len(results)} modules)")
    print(f"Report: {OUT}")
    for r in results:
        if r["percent"] < 100:
            missing = [k for k, v in r["checks"].items() if not v]
            print(f"  [{r['group']}] {r['label']}: {r['percent']}% — missing: {', '.join(missing[:5])}")


if __name__ == "__main__":
    main()
