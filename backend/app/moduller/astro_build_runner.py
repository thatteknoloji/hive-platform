"""
HIVE V3 Astro Build Runner — opt-in npm install + build (publish gate required).
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.moduller import astro_export_engine
from app.moduller.astro_build_validator import resolve_export_path

INSTALL_TIMEOUT_SEC = 180
BUILD_TIMEOUT_SEC = 120
OUTPUT_TAIL_CHARS = 4000

CmdRunner = Callable[[list[str], Path, int], dict[str, Any]]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _tail(text: str) -> str:
    if not text:
        return ""
    return text[-OUTPUT_TAIL_CHARS:]


def _default_cmd_runner(cmd: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    label = " ".join(cmd)
    started = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "cmd": label,
            "exit_code": result.returncode,
            "duration_ms": duration_ms,
            "stdout_tail": _tail(result.stdout or ""),
            "stderr_tail": _tail(result.stderr or ""),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "cmd": label,
            "exit_code": -1,
            "duration_ms": duration_ms,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
            "timed_out": True,
        }
    except FileNotFoundError:
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "cmd": label,
            "exit_code": -1,
            "duration_ms": duration_ms,
            "stdout_tail": "",
            "stderr_tail": "npm executable not found",
            "timed_out": False,
        }


def _secure_export_path(project_id: str, project: dict[str, Any]) -> Path | None:
    try:
        astro_export_engine.sanitize_project_id(project_id)
    except ValueError:
        return None
    export_path = resolve_export_path(project_id, project)
    if export_path is None:
        return None
    base = astro_export_engine.EXPORT_ROOT.resolve()
    resolved = export_path.resolve()
    if not str(resolved).startswith(str(base)):
        return None
    if not resolved.is_dir():
        return None
    return resolved


def build_status(project: dict[str, Any]) -> dict[str, Any]:
    stored = (project.get("metadata") or {}).get("astro_build") or {}
    return {
        "success": True,
        "project_id": project.get("id"),
        "status": stored.get("status"),
        "dist_path": stored.get("dist_path"),
        "built_at": stored.get("built_at"),
        "commands": stored.get("commands") or [],
        "errors_count": stored.get("errors_count", 0),
        "error": stored.get("error"),
        "stdout_tail": stored.get("stdout_tail"),
        "stderr_tail": stored.get("stderr_tail"),
    }


def run_build(
    project_id: str,
    project: dict[str, Any],
    *,
    gate: dict[str, Any],
    cmd_runner: CmdRunner | None = None,
) -> dict[str, Any]:
    """Run npm install + npm run build inside export_path when publish gate is open."""
    runner = cmd_runner or _default_cmd_runner
    pid = (project_id or "").strip()

    if not gate.get("can_publish"):
        return {
            "success": False,
            "status": "build_failed",
            "error": "publish_gate_blocked",
            "project_id": pid,
            "reasons": list(gate.get("reasons") or []),
            "commands": [],
        }

    export_path = _secure_export_path(pid, project)
    if export_path is None:
        return {
            "success": False,
            "status": "build_failed",
            "error": "export_path_invalid",
            "project_id": pid,
            "commands": [],
        }

    if not (export_path / "package.json").is_file():
        return {
            "success": False,
            "status": "build_failed",
            "error": "package_json_missing",
            "project_id": pid,
            "export_path": str(export_path),
            "commands": [],
        }

    commands: list[dict[str, Any]] = []

    install_res = runner(["npm", "install", "--no-audit"], export_path, INSTALL_TIMEOUT_SEC)
    commands.append({k: install_res[k] for k in ("cmd", "exit_code", "duration_ms")})
    if install_res.get("timed_out"):
        return _failed(
            pid, export_path, commands, install_res,
            error="npm_install_timeout",
        )
    if install_res.get("exit_code") != 0:
        return _failed(
            pid, export_path, commands, install_res,
            error="npm_install_failed",
        )

    build_res = runner(["npm", "run", "build"], export_path, BUILD_TIMEOUT_SEC)
    commands.append({k: build_res[k] for k in ("cmd", "exit_code", "duration_ms")})
    if build_res.get("timed_out"):
        return _failed(
            pid, export_path, commands, build_res,
            error="npm_build_timeout",
        )
    if build_res.get("exit_code") != 0:
        return _failed(
            pid, export_path, commands, build_res,
            error="npm_build_failed",
        )

    dist_path = export_path / "dist"
    if not dist_path.is_dir() or not (dist_path / "index.html").is_file():
        return {
            "success": False,
            "status": "build_failed",
            "error": "dist_missing",
            "project_id": pid,
            "export_path": str(export_path),
            "commands": commands,
            "stdout_tail": build_res.get("stdout_tail", ""),
            "stderr_tail": build_res.get("stderr_tail", ""),
        }

    built_at = _now()
    return {
        "success": True,
        "project_id": pid,
        "status": "built",
        "export_path": str(export_path),
        "dist_path": str(dist_path),
        "commands": commands,
        "built_at": built_at,
        "errors_count": 0,
    }


def _failed(
    project_id: str,
    export_path: Path,
    commands: list[dict[str, Any]],
    last_cmd: dict[str, Any],
    *,
    error: str,
) -> dict[str, Any]:
    return {
        "success": False,
        "status": "build_failed",
        "error": error,
        "project_id": project_id,
        "export_path": str(export_path),
        "commands": commands,
        "stdout_tail": last_cmd.get("stdout_tail", ""),
        "stderr_tail": last_cmd.get("stderr_tail", ""),
        "errors_count": 1,
    }
