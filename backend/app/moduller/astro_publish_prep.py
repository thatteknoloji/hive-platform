"""
HIVE V3 Astro Publish Prep — dist/ → publish artifact copy (no deploy/shell).
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.moduller import astro_export_engine

APP_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = APP_DIR / "publish_artifacts"

MAX_FILES = 5000
MAX_TOTAL_BYTES = 250 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _artifact_dir(project_id: str) -> Path:
    safe = astro_export_engine.sanitize_project_id(project_id)
    base = ARTIFACT_ROOT.resolve()
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    target = (base / safe).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("path_traversal")
    return target


def _secure_dist_path(dist_path: str | Path) -> Path | None:
    try:
        base = astro_export_engine.EXPORT_ROOT.resolve()
        resolved = Path(dist_path).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if not str(resolved).startswith(str(base)):
        return None
    if not resolved.is_dir():
        return None
    return resolved


def prep_status(project: dict[str, Any]) -> dict[str, Any]:
    stored = (project.get("metadata") or {}).get("astro_publish_artifact") or {}
    return {
        "success": True,
        "project_id": project.get("id"),
        "status": stored.get("status"),
        "artifact_path": stored.get("artifact_path"),
        "files_count": stored.get("files_count"),
        "total_size_bytes": stored.get("total_size_bytes"),
        "entry": stored.get("entry"),
        "prepared_at": stored.get("prepared_at"),
        "error": stored.get("error"),
    }


def _copy_dist_secure(src: Path, dst: Path) -> tuple[int, int, list[str]]:
    """Copy dist files to artifact dir. Skips symlinks. Returns count, bytes, asset list."""
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    files_count = 0
    total_size = 0
    assets: list[str] = []
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
        assets.append(str(rel).replace("\\", "/"))

    return files_count, total_size, assets


def prepare_artifact(project_id: str, project: dict[str, Any]) -> dict[str, Any]:
    pid = (project_id or "").strip()
    build = (project.get("metadata") or {}).get("astro_build") or {}

    if build.get("status") != "built":
        return {
            "success": False,
            "status": "prep_failed",
            "error": "build_not_ready",
            "project_id": pid,
        }

    dist_raw = build.get("dist_path")
    if not dist_raw:
        return {
            "success": False,
            "status": "prep_failed",
            "error": "dist_missing",
            "project_id": pid,
        }

    dist_path = _secure_dist_path(dist_raw)
    if dist_path is None:
        return {
            "success": False,
            "status": "prep_failed",
            "error": "dist_missing",
            "project_id": pid,
        }

    index_file = dist_path / "index.html"
    if not index_file.is_file() or index_file.is_symlink():
        return {
            "success": False,
            "status": "prep_failed",
            "error": "index_missing",
            "project_id": pid,
            "dist_path": str(dist_path),
        }

    try:
        artifact_path = _artifact_dir(pid)
    except ValueError as exc:
        return {
            "success": False,
            "status": "prep_failed",
            "error": str(exc),
            "project_id": pid,
        }

    try:
        files_count, total_size, assets = _copy_dist_secure(dist_path, artifact_path)
    except ValueError as exc:
        err = str(exc)
        if artifact_path.exists():
            shutil.rmtree(artifact_path, ignore_errors=True)
        return {
            "success": False,
            "status": "prep_failed",
            "error": err,
            "project_id": pid,
            "dist_path": str(dist_path),
        }

    if not (artifact_path / "index.html").is_file():
        return {
            "success": False,
            "status": "prep_failed",
            "error": "index_missing",
            "project_id": pid,
            "artifact_path": str(artifact_path),
        }

    prepared_at = _now()
    return {
        "success": True,
        "project_id": pid,
        "status": "ready",
        "artifact_path": str(artifact_path),
        "files_count": files_count,
        "total_size_bytes": total_size,
        "entry": "index.html",
        "prepared_at": prepared_at,
        "public_assets": assets[:100],
        "dist_path": str(dist_path),
    }
