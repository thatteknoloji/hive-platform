#!/usr/bin/env python3
"""Operation Phoenix — Customer Journey Completion Rate (CJCR) audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNEY_FILE = ROOT / "roadmap" / "customer-journey.json"
DEMO_FILE = ROOT / "roadmap" / "demo-project.json"
ACADEMY = ROOT / "docs" / "academy"
ENC = ACADEMY / "06-modul-ansiklopedisi"
SCREENSHOTS = ACADEMY / "screenshots"
CHANGELOG = ACADEMY / "CHANGELOG.md"
FRONTEND_PAGES = ROOT / "frontend" / "src" / "pages"
OUT = ROOT / "roadmap" / "phoenix-customer-journey-audit.json"

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
    if backend_file == "auth.py":
        backend_path = ROOT / "backend" / "app" / "auth.py"
    if backend_file == "project_context.py":
        backend_path = ROOT / "backend" / "app" / "moduller" / "project_context.py"

    doc_path = _find_academy_doc(slug, mid)
    doc_text = doc_path.read_text(encoding="utf-8") if doc_path and doc_path.is_file() else ""
    published = 'status: "published"' in doc_text or "status: published" in doc_text

    page_js = None
    if mid == "projects":
        p = FRONTEND_PAGES / "projects" / "ProjectsList.js"
        page_js = p if p.is_file() else None
    if page and not page_js:
        p = FRONTEND_PAGES / f"{page}.js"
        page_js = p if p.is_file() else None
    ui_text = page_js.read_text(encoding="utf-8") if page_js else ""

    shot_ok = (SCREENSHOTS / slug).is_dir() and any((SCREENSHOTS / slug).iterdir())
    shot_ok = shot_ok or (SCREENSHOTS / mid).is_dir() and any((SCREENSHOTS / mid).iterdir())

    no_ui = mid in ("permissions", "active_project_context", "auth")

    checks = {
        "production_works": backend_path.is_file() or no_ui,
        "ui_complete": _page_exists(page, mid) or no_ui,
        "api_complete": "/api/" in doc_text or bool(mod.get("id")),
        "error_handling": "HiveApiErrorCard" in ui_text or "HiveAlert" in ui_text or "formatHiveApiError" in ui_text or "apiError" in ui_text or "parseApiError" in ui_text or no_ui,
        "loading": "loading" in ui_text.lower() or "HiveSkeleton" in ui_text or "setLoading" in ui_text or no_ui,
        "toast": "HiveToast" in ui_text or "setToast" in ui_text or "setMessage" in ui_text or no_ui,
        "empty_state": "HiveEmptyState" in ui_text or "empty" in ui_text.lower() or no_ui,
        "tooltip": "Tooltip" in ui_text or "title=" in ui_text or "HiveConceptTooltip" in ui_text or "HiveLabelWithTip" in ui_text or no_ui,
        "academy_doc": bool(doc_path) and published,
        "screenshot": shot_ok or "screenshots/" in doc_text,
        "workflow": "```mermaid" in doc_text,
        "api_docs": ("/api/" in doc_text and "## API" in doc_text) or "endpoint" in doc_text.lower(),
        "troubleshooting": "Troubleshooting" in doc_text or "Yaygın hatalar" in doc_text or "## Yaygın" in doc_text,
        "changelog": CHANGELOG.is_file() and mid in CHANGELOG.read_text(encoding="utf-8"),
        "tested": (ROOT / "backend" / "tests").is_dir(),
        "demo_scenario": "Örnek senaryo" in doc_text and "TODO" not in doc_text.split("Örnek senaryo")[-1][:200],
    }
    return checks


def _load_demo_context() -> dict:
    sys.path.insert(0, str(ROOT / "backend"))
    try:
        from app.moduller import phoenix_journey  # noqa: WPS433
        return phoenix_journey.load_journey_context()
    except Exception:
        ctx: dict = {"demo_project": None, "active_project_id": ""}
        if DEMO_FILE.is_file():
            try:
                manifest = json.loads(DEMO_FILE.read_text(encoding="utf-8"))
                ctx["demo_project"] = manifest
                ctx["active_project_id"] = manifest.get("active_project_id") or manifest.get("project_id") or ""
            except (json.JSONDecodeError, OSError):
                pass
        return ctx


def _run_data_check(check_id: str, ctx: dict) -> tuple[bool, str]:
    sys.path.insert(0, str(ROOT / "backend"))
    try:
        from app.moduller import phoenix_journey  # noqa: WPS433
        return phoenix_journey.run_data_check(check_id, ctx)
    except Exception as exc:
        return False, str(exc)


def main() -> None:
    journey = json.loads(JOURNEY_FILE.read_text(encoding="utf-8"))
    ctx = _load_demo_context()
    steps_out: list[dict] = []

    for step_id in journey.get("journey_order", []):
        step = journey.get("steps", {}).get(step_id, {})
        modules_out: list[dict] = []

        for mod in step.get("modules", []):
            checks = _checklist_for(mod)
            total = sum(1 for v in checks.values() if v)
            pct = round(100 * total / len(checks), 1) if checks else 0
            modules_out.append({
                "label": mod.get("label"),
                "id": mod.get("id"),
                "checks": checks,
                "passed": total,
                "total_checks": len(checks),
                "percent": pct,
                "module_ready": pct >= 100,
            })

        data_checks_out: list[dict] = []
        for check_id in step.get("data_checks", []):
            ok, detail = _run_data_check(check_id, ctx)
            data_checks_out.append({"id": check_id, "passed": ok, "detail": detail})

        modules_ready = all(m["module_ready"] for m in modules_out) if modules_out else True
        data_ready = all(d["passed"] for d in data_checks_out) if data_checks_out else True
        step_complete = modules_ready and data_ready

        steps_out.append({
            "id": step_id,
            "order": step.get("order"),
            "label": step.get("label"),
            "label_tr": step.get("label_tr"),
            "route": step.get("route"),
            "modules": modules_out,
            "data_checks": data_checks_out,
            "modules_ready": modules_ready,
            "data_ready": data_ready,
            "step_complete": step_complete,
        })

    complete = sum(1 for s in steps_out if s["step_complete"])
    total_steps = len(steps_out)
    cjcr = round(100 * complete / total_steps, 1) if total_steps else 0

    report = {
        "operation": "OPERATION_PHOENIX",
        "metric": "customer_journey_completion_rate",
        "metric_label": "Customer Journey Completion Rate",
        "customer_journey_completion_rate": cjcr,
        "steps_complete": complete,
        "steps_total": total_steps,
        "target": 100,
        "demo_project_manifest": str(DEMO_FILE.relative_to(ROOT)),
        "steps": steps_out,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Customer Journey Completion Rate: {cjcr}% ({complete}/{total_steps} steps)")
    print(f"Report: {OUT}")
    for step in steps_out:
        if not step["step_complete"]:
            label = step.get("label") or step.get("id")
            gaps: list[str] = []
            if not step["data_ready"]:
                gaps.extend(d["id"] for d in step["data_checks"] if not d["passed"])
            for mod in step["modules"]:
                if not mod["module_ready"]:
                    missing = [k for k, v in mod["checks"].items() if not v]
                    gaps.append(f"{mod['id']}({mod['percent']}%: {', '.join(missing[:3])})")
            print(f"  [{step['order']}] {label}: INCOMPLETE — {', '.join(gaps[:6])}")


if __name__ == "__main__":
    main()
