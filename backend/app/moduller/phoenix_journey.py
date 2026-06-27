"""Operation Phoenix — Customer Journey status for Mission Control."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent.parent
JOURNEY_FILE = ROOT / "roadmap" / "customer-journey.json"
AUDIT_FILE = ROOT / "roadmap" / "phoenix-customer-journey-audit.json"
DEMO_FILE = ROOT / "roadmap" / "demo-project.json"

DOMAIN_RE = re.compile(r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$", re.I)
DEMO_PROJECT_ID = "prj-161789b6ec"
DEMO_DOMAIN = "demo.thiqos.com"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def normalize_domain(raw: str) -> str:
    return (
        (raw or "")
        .strip()
        .lower()
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
        .rstrip(".")
    )


def is_valid_domain(domain: str) -> bool:
    d = normalize_domain(domain)
    return bool(d) and bool(DOMAIN_RE.match(d))


def load_journey_context() -> dict[str, Any]:
    """Shared context for audit and Mission Control."""
    ctx: dict[str, Any] = {"demo_project": None, "active_project_id": "", "project_record": None}
    if DEMO_FILE.is_file():
        try:
            manifest = json.loads(DEMO_FILE.read_text(encoding="utf-8"))
            ctx["demo_project"] = manifest
            ctx["active_project_id"] = manifest.get("active_project_id") or manifest.get("project_id") or ""
        except (json.JSONDecodeError, OSError):
            pass

    try:
        from app.moduller import project_context, project_engine  # noqa: WPS433

        active = project_context.get_active_project_id()
        if active:
            ctx["active_project_id"] = active
        pid = (ctx.get("active_project_id") or "").strip()
        if pid:
            loaded = project_engine.get_project(pid)
            if loaded and loaded.get("project"):
                ctx["project_record"] = loaded["project"]
    except Exception:
        pass

    return ctx


def run_data_check(check_id: str, ctx: dict[str, Any] | None = None) -> tuple[bool, str]:
    ctx = ctx or load_journey_context()
    record = ctx.get("project_record") or {}
    manifest = ctx.get("demo_project") or {}
    pid = (ctx.get("active_project_id") or "").strip()
    domain = normalize_domain(record.get("domain") or manifest.get("domain") or "")

    if check_id == "auth_backend":
        ok = (ROOT / "backend" / "app" / "auth.py").is_file()
        return ok, "auth.py mevcut" if ok else "auth.py eksik"

    if check_id == "login_page":
        ok = (ROOT / "frontend" / "src" / "pages" / "Login.js").is_file()
        return ok, "Login.js mevcut" if ok else "Login.js eksik"

    if check_id == "demo_project_exists":
        ok = bool(manifest) or bool(record)
        return ok, "demo proje seed edilmiş" if ok else "scripts/seed-customer-journey-demo.py çalıştırın"

    if check_id == "active_project_set":
        ok = bool(pid)
        return ok, f"aktif proje: {pid}" if ok else "aktif proje ayarlanmamış"

    if check_id == "demo_domain_set":
        ok = bool(domain)
        return ok, f"domain: {domain}" if ok else "proje domain'i boş"

    if check_id == "project_domain_exists":
        ok = bool(domain)
        return ok, f"project domain: {domain}" if ok else "proje domain alanı boş"

    if check_id == "domain_format_valid":
        ok = is_valid_domain(domain) if domain else False
        return ok, f"format OK: {domain}" if ok else f"geçersiz domain: {domain or '(boş)'}"

    if check_id == "domain_attached_to_active_project":
        binding = (record.get("metadata") or {}).get("domain_binding") or {}
        bound_domain = normalize_domain(binding.get("domain") or domain)
        ok = bool(pid) and bool(bound_domain) and (
            bound_domain == normalize_domain(DEMO_DOMAIN)
            or bound_domain == domain
        )
        detail = f"active={pid}, domain={bound_domain or domain or '—'}"
        if binding.get("status"):
            detail += f", bind={binding.get('status')}"
        return ok, detail if ok else f"domain aktif projeye bağlı değil ({detail})"

    return True, f"bilinmeyen check: {check_id}"


def run_domain_step_checks(ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = ctx or load_journey_context()
    journey = _load_json(JOURNEY_FILE)
    step = journey.get("steps", {}).get("domain", {})
    checks: list[dict[str, Any]] = []
    for check_id in step.get("data_checks", []):
        ok, detail = run_data_check(check_id, ctx)
        checks.append({"id": check_id, "passed": ok, "detail": detail})
    return {
        "step_id": "domain",
        "data_checks": checks,
        "data_ready": all(c["passed"] for c in checks) if checks else False,
    }


def get_status() -> dict[str, Any]:
    journey = _load_json(JOURNEY_FILE)
    audit = _load_json(AUDIT_FILE)
    demo = _load_json(DEMO_FILE)

    steps_by_id = {s.get("id"): s for s in audit.get("steps", []) if s.get("id")}
    order = journey.get("journey_order", [])

    steps_out: list[dict[str, Any]] = []
    for step_id in order:
        cfg = journey.get("steps", {}).get(step_id, {})
        audited = steps_by_id.get(step_id, {})
        complete = bool(audited.get("step_complete"))
        if complete:
            status = "completed"
        elif audited:
            status = "in_progress"
        else:
            status = "not_started"

        steps_out.append({
            "id": step_id,
            "order": cfg.get("order"),
            "label": cfg.get("label"),
            "label_tr": cfg.get("label_tr"),
            "route": cfg.get("route"),
            "status": status,
            "step_complete": complete,
            "modules_ready": audited.get("modules_ready"),
            "data_ready": audited.get("data_ready"),
        })

    active_id = demo.get("active_project_id") or demo.get("project_id") or ""
    return {
        "success": True,
        "metric": journey.get("metric", "customer_journey_completion_rate"),
        "metric_label": journey.get("metric_label", "Customer Journey Completion Rate"),
        "customer_journey_completion_rate": audit.get("customer_journey_completion_rate", 0),
        "steps_complete": audit.get("steps_complete", 0),
        "steps_total": audit.get("steps_total", len(steps_out)),
        "target": journey.get("target_percent", 100),
        "demo_project": {
            "id": active_id,
            "name": demo.get("name", ""),
            "domain": demo.get("domain", ""),
            "is_active": bool(active_id),
        },
        "domain_step": run_domain_step_checks(),
        "steps": steps_out,
    }
