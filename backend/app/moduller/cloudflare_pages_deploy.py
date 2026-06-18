"""Cloudflare Pages Auto Deploy — Astro Site Factory entegrasyonu."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app import config
from app.moduller.storyforge_categories import _slugify
from app.moduller.astro_factory import (
    _dist_ready,
    _get_project,
    _project_path,
    _update_project,
)

logger = logging.getLogger("hive.cloudflare_pages")

CF_API_BASE = "https://api.cloudflare.com/client/v4"
DEPLOY_TIMEOUT_SEC = 600
PROJECT_NAME_MAX = 58


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _cf_token() -> str:
    return (config.get("CLOUDFLARE_API_TOKEN") or "").strip()


def _cf_account_id() -> str:
    return (config.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()


def _cf_branch() -> str:
    return (config.get("CLOUDFLARE_PAGES_BRANCH") or "main").strip()


def _cf_prefix() -> str:
    return (config.get("CLOUDFLARE_DEFAULT_PROJECT_PREFIX") or "hive-").strip()


def _scrub_secrets(text: str) -> str:
    token = _cf_token()
    if token and token in text:
        text = text.replace(token, "***")
    return text


def cf_status() -> dict[str, Any]:
    token = _cf_token()
    account = _cf_account_id()
    return {
        "success": True,
        "configured": bool(token and account),
        "account_id_present": bool(account),
        "token_present": bool(token),
        "branch": _cf_branch(),
        "project_prefix": _cf_prefix(),
    }


def sanitize_cf_project_name(raw: str) -> str:
    """Cloudflare Pages proje adı: küçük harf, rakam, tire."""
    text = (raw or "").strip()
    if ".." in text or "/" in text or "\\" in text:
        raise ValueError("Geçersiz proje adı")
    slug = _slugify(text)
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise ValueError("Geçersiz proje adı")
    return slug[:PROJECT_NAME_MAX]


def _default_cf_name(project: dict[str, Any]) -> str:
    return sanitize_cf_project_name(f"{_cf_prefix()}{project.get('slug', 'site')}")


def _cf_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_cf_token()}",
        "Content-Type": "application/json",
    }


def _cf_error_message(data: dict[str, Any]) -> str:
    errs = data.get("errors") or []
    if errs:
        return "; ".join(str(e.get("message", e)) for e in errs)
    return str(data.get("error") or "Cloudflare API hatası")


def _cf_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    if not _cf_token() or not _cf_account_id():
        return {
            "success": False,
            "error": "Cloudflare yapılandırılmamış — CLOUDFLARE_API_TOKEN ve CLOUDFLARE_ACCOUNT_ID gerekli",
        }
    url = f"{CF_API_BASE}{path}"
    try:
        resp = requests.request(method, url, headers=_cf_headers(), timeout=90, **kwargs)
        try:
            data = resp.json()
        except ValueError:
            data = {"success": False, "errors": [{"message": resp.text[:500]}]}
        if not data.get("success"):
            return {
                "success": False,
                "error": _cf_error_message(data),
                "status_code": resp.status_code,
            }
        return {"success": True, "result": data.get("result"), "status_code": resp.status_code}
    except requests.RequestException as exc:
        return {"success": False, "error": f"Cloudflare isteği başarısız: {exc}"}


def _project_url_from_result(result: dict[str, Any], name: str) -> str:
    subdomain = result.get("subdomain")
    if isinstance(subdomain, str) and subdomain:
        return f"https://{subdomain}.pages.dev"
    domains = result.get("domains") or []
    if domains:
        d0 = domains[0]
        if isinstance(d0, str):
            return f"https://{d0}" if d0.startswith("http") else f"https://{d0}"
    return f"https://{name}.pages.dev"


def get_cf_project(project_name: str) -> dict[str, Any]:
    account = _cf_account_id()
    safe = sanitize_cf_project_name(project_name)
    return _cf_request("GET", f"/accounts/{account}/pages/projects/{safe}")


def create_cf_project(project_name: str) -> dict[str, Any]:
    account = _cf_account_id()
    safe = sanitize_cf_project_name(project_name)
    body = {"name": safe, "production_branch": _cf_branch()}
    created = _cf_request("POST", f"/accounts/{account}/pages/projects", json=body)
    if created.get("success"):
        return {**created, "already_existed": False}

    err = (created.get("error") or "").lower()
    code_hit = any(
        token in err
        for token in ("already exists", "already been taken", "duplicate", "8000007", "8000095")
    )
    if code_hit or created.get("status_code") in (400, 409):
        existing = get_cf_project(safe)
        if existing.get("success"):
            return {**existing, "already_existed": True}
    return created


def list_cf_deployments(project_name: str, limit: int = 10) -> dict[str, Any]:
    account = _cf_account_id()
    safe = sanitize_cf_project_name(project_name)
    return _cf_request(
        "GET",
        f"/accounts/{account}/pages/projects/{safe}/deployments",
        params={"per_page": limit},
    )


def _append_deployment(project_id: str, entry: dict[str, Any]) -> None:
    project = _get_project(project_id)
    deployments = list(project.get("deployments") or [])
    deployments.insert(0, entry)
    _update_project(project_id, deployments=deployments[:50])


def create_pages_project(local_project_id: str, cloudflare_project_name: str = "") -> dict[str, Any]:
    st = cf_status()
    if not st["configured"]:
        return {
            **st,
            "success": False,
            "error": "Cloudflare yapılandırılmamış — CLOUDFLARE_API_TOKEN ve CLOUDFLARE_ACCOUNT_ID .env dosyasına ekleyin",
        }

    project = _get_project(local_project_id)
    name = sanitize_cf_project_name(cloudflare_project_name or _default_cf_name(project))

    cf_res = create_cf_project(name)
    if not cf_res.get("success"):
        return {"success": False, "error": cf_res.get("error", "Cloudflare proje oluşturulamadı")}

    result = cf_res.get("result") or {}
    cf_id = str(result.get("id") or name)
    latest_url = _project_url_from_result(result, name)

    existing_cf = project.get("cloudflare") or {}
    cf_state = {
        "project_name": name,
        "project_id": cf_id,
        "created_at": existing_cf.get("created_at") or _now(),
        "latest_deployment_id": existing_cf.get("latest_deployment_id"),
        "latest_url": existing_cf.get("latest_url") or latest_url,
    }
    _update_project(local_project_id, cloudflare=cf_state)

    return {
        "success": True,
        "cloudflare": cf_state,
        "already_existed": bool(cf_res.get("already_existed")),
        "project": _get_project(local_project_id),
    }


def _parse_deploy_url(text: str) -> str | None:
    match = re.search(r"https://[a-zA-Z0-9.-]+\.pages\.dev[^\s)\]]*", text)
    return match.group(0).rstrip(").,") if match else None


def _parse_deployment_id(text: str) -> str | None:
    match = re.search(r"Deployment ID:\s*([a-f0-9-]+)", text, re.I)
    if match:
        return match.group(1)
    match = re.search(r"deployment[:\s]+([a-f0-9-]{36})", text, re.I)
    return match.group(1) if match else None


def _wrangler_deploy_cmd() -> list[str]:
    for binary in ("wrangler",):
        try:
            probe = subprocess.run(
                [binary, "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
            if probe.returncode == 0:
                return [binary, "pages", "deploy", "dist"]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return ["npx", "--yes", "wrangler@3", "pages", "deploy", "dist"]


def _deploy_with_wrangler(project_path: Path, project_name: str, branch: str) -> dict[str, Any]:
    dist = project_path / "dist"
    if not dist.is_dir():
        return {"success": False, "error": "dist/ klasörü bulunamadı", "log": ""}

    base = _wrangler_deploy_cmd()
    cmd = [
        *base,
        "--project-name",
        project_name,
        "--branch",
        branch,
        "--commit-dirty=true",
    ]

    env = os.environ.copy()
    env["CLOUDFLARE_API_TOKEN"] = _cf_token()
    env["CLOUDFLARE_ACCOUNT_ID"] = _cf_account_id()
    env["CI"] = "true"
    env["WRANGLER_SEND_METRICS"] = "false"

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=DEPLOY_TIMEOUT_SEC,
            shell=False,
            env=env,
        )
        log = _scrub_secrets(
            f"$ {' '.join(cmd)}\nexit={proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout[-4000:]}\n"
            f"--- stderr ---\n{proc.stderr[-4000:]}"
        )
        if proc.returncode != 0:
            return {
                "success": False,
                "error": f"wrangler deploy başarısız (exit {proc.returncode})",
                "log": log,
            }
        combined = proc.stdout + proc.stderr
        return {
            "success": True,
            "log": log,
            "url": _parse_deploy_url(combined),
            "deployment_id": _parse_deployment_id(combined),
            "method": "wrangler",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Deploy zaman aşımı ({DEPLOY_TIMEOUT_SEC}s)", "log": ""}
    except FileNotFoundError:
        return {"success": False, "error": "npx/wrangler bulunamadı — Node.js kurulu olmalı", "log": ""}


def deploy_to_cloudflare(local_project_id: str) -> dict[str, Any]:
    st = cf_status()
    if not st["configured"]:
        return {
            **st,
            "success": False,
            "error": "Cloudflare yapılandırılmamış — CLOUDFLARE_API_TOKEN ve CLOUDFLARE_ACCOUNT_ID gerekli",
        }

    project = _get_project(local_project_id)
    project_path = _project_path(project["slug"])

    if not _dist_ready(project_path):
        return {"success": False, "error": "Build alınmamış. Önce build çalıştır."}

    cf = dict(project.get("cloudflare") or {})
    cf_name = cf.get("project_name")
    if not cf_name:
        created = create_pages_project(local_project_id)
        if not created.get("success"):
            return created
        cf = dict(created.get("cloudflare") or {})
        cf_name = cf.get("project_name")

    if not cf_name:
        return {"success": False, "error": "Cloudflare Pages proje adı oluşturulamadı"}

    deploy_res = _deploy_with_wrangler(project_path, cf_name, _cf_branch())
    entry: dict[str, Any] = {
        "provider": "cloudflare_pages",
        "status": "success" if deploy_res.get("success") else "error",
        "deployment_id": deploy_res.get("deployment_id"),
        "url": deploy_res.get("url"),
        "created_at": _now(),
        "log": (deploy_res.get("log") or "")[-8000:],
        "method": deploy_res.get("method", "wrangler"),
        "project_name": cf_name,
    }

    if not deploy_res.get("success"):
        _append_deployment(local_project_id, entry)
        return {
            "success": False,
            "error": deploy_res.get("error", "Deploy başarısız"),
            "log": entry["log"],
            "deployment": entry,
        }

    api_deps = list_cf_deployments(cf_name, limit=1)
    if api_deps.get("success"):
        items = api_deps.get("result") or []
        if isinstance(items, list) and items:
            latest = items[0]
            if isinstance(latest, dict):
                entry["deployment_id"] = entry.get("deployment_id") or latest.get("id")
                aliases = latest.get("aliases") or []
                if aliases and not entry.get("url"):
                    entry["url"] = f"https://{aliases[0]}" if not str(aliases[0]).startswith("http") else aliases[0]
                entry["url"] = entry.get("url") or latest.get("url")

    cf["latest_deployment_id"] = entry.get("deployment_id")
    if entry.get("url"):
        cf["latest_url"] = entry["url"]
    _update_project(local_project_id, cloudflare=cf, status="deployed")
    _append_deployment(local_project_id, entry)

    return {
        "success": True,
        "deployment": entry,
        "cloudflare": cf,
        "url": entry.get("url"),
        "log": entry.get("log"),
    }


def get_deployments(local_project_id: str) -> dict[str, Any]:
    project = _get_project(local_project_id)
    local_deps = list(project.get("deployments") or [])
    cf = dict(project.get("cloudflare") or {})
    remote: list[dict[str, Any]] = []

    cf_name = cf.get("project_name")
    if cf_name and cf_status()["configured"]:
        api_res = list_cf_deployments(cf_name, limit=10)
        if api_res.get("success"):
            for item in api_res.get("result") or []:
                if not isinstance(item, dict):
                    continue
                aliases = item.get("aliases") or []
                url = item.get("url")
                if not url and aliases:
                    url = f"https://{aliases[0]}" if not str(aliases[0]).startswith("http") else aliases[0]
                remote.append({
                    "id": item.get("id"),
                    "url": url,
                    "environment": item.get("environment"),
                    "created_on": item.get("created_on"),
                    "latest_stage": (item.get("latest_stage") or {}).get("name"),
                })

    return {
        "success": True,
        "project_id": local_project_id,
        "cloudflare": cf,
        "deployments": local_deps,
        "remote_deployments": remote,
    }
