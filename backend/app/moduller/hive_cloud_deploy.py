"""
HIVE V3 HIVE Cloud Deploy — publish artifact → public_sites (no shell/Cloudflare).
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.moduller import astro_export_engine, astro_publish_prep

APP_DIR = Path(__file__).resolve().parent.parent
PUBLIC_ROOT = APP_DIR / "public_sites"

MAX_FILES = 5000
MAX_TOTAL_BYTES = 250 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _deploy_dir(project_id: str) -> Path:
    safe = astro_export_engine.sanitize_project_id(project_id)
    base = PUBLIC_ROOT.resolve()
    PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
    target = (base / safe).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("path_traversal")
    return target


def _secure_artifact_path(artifact_path: str | Path) -> Path | None:
    try:
        base = astro_publish_prep.ARTIFACT_ROOT.resolve()
        resolved = Path(artifact_path).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if not str(resolved).startswith(str(base)):
        return None
    if not resolved.is_dir():
        return None
    return resolved


def live_url_for(project_id: str) -> str:
    safe = astro_export_engine.sanitize_project_id(project_id)
    return f"/sites/{safe}/"


def deploy_status(project: dict[str, Any]) -> dict[str, Any]:
    stored = (project.get("metadata") or {}).get("hive_cloud_deploy") or {}
    return {
        "success": True,
        "project_id": project.get("id"),
        "status": stored.get("status"),
        "deploy_path": stored.get("deploy_path"),
        "live_url": stored.get("live_url"),
        "files_count": stored.get("files_count"),
        "total_size_bytes": stored.get("total_size_bytes"),
        "deployed_at": stored.get("deployed_at"),
        "error": stored.get("error"),
    }


def _copy_artifact_secure(src: Path, dst: Path) -> tuple[int, int]:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    files_count = 0
    total_size = 0
    dst_base = dst.resolve()

    for item in sorted(src.rglob("*")):
        if item.is_symlink():
            continue
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        target = (dst / rel).resolve()
        if not str(target).startswith(str(dst_base)):
            raise ValueError("path_traversal")
        try:
            size = item.stat().st_size
        except OSError:
            continue
        files_count += 1
        total_size += size
        if files_count > MAX_FILES:
            raise ValueError("too_many_files")
        if total_size > MAX_TOTAL_BYTES:
            raise ValueError("too_large")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target, follow_symlinks=False)

    return files_count, total_size


def deploy_to_hive_cloud(project_id: str, project: dict[str, Any]) -> dict[str, Any]:
    pid = (project_id or "").strip()
    prep = (project.get("metadata") or {}).get("astro_publish_artifact") or {}

    if prep.get("status") != "ready":
        return {
            "success": False,
            "status": "deploy_failed",
            "error": "artifact_not_ready",
            "project_id": pid,
        }

    artifact_raw = prep.get("artifact_path")
    if not artifact_raw:
        return {
            "success": False,
            "status": "deploy_failed",
            "error": "artifact_missing",
            "project_id": pid,
        }

    artifact_path = _secure_artifact_path(artifact_raw)
    if artifact_path is None:
        return {
            "success": False,
            "status": "deploy_failed",
            "error": "artifact_missing",
            "project_id": pid,
        }

    index_file = artifact_path / "index.html"
    if not index_file.is_file() or index_file.is_symlink():
        return {
            "success": False,
            "status": "deploy_failed",
            "error": "index_missing",
            "project_id": pid,
        }

    try:
        deploy_path = _deploy_dir(pid)
    except ValueError as exc:
        return {
            "success": False,
            "status": "deploy_failed",
            "error": str(exc),
            "project_id": pid,
        }

    try:
        files_count, total_size = _copy_artifact_secure(artifact_path, deploy_path)
    except ValueError as exc:
        err = str(exc)
        if deploy_path.exists():
            shutil.rmtree(deploy_path, ignore_errors=True)
        return {
            "success": False,
            "status": "deploy_failed",
            "error": err,
            "project_id": pid,
        }

    if not (deploy_path / "index.html").is_file():
        return {
            "success": False,
            "status": "deploy_failed",
            "error": "index_missing",
            "project_id": pid,
        }

    deployed_at = _now()
    return {
        "success": True,
        "project_id": pid,
        "status": "deployed",
        "deploy_path": str(deploy_path),
        "live_url": live_url_for(pid),
        "files_count": files_count,
        "total_size_bytes": total_size,
        "deployed_at": deployed_at,
    }
