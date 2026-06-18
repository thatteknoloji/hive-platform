"""
HIVE V3 Production Apply — bash script generator (no execution/sudo).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.moduller import hive_cloud_deploy, hive_production_deploy

MANUAL_STEPS = [
    "Copy script to server",
    "Review nginx config",
    "Run as root",
    "Run certbot command manually",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _bash_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _secure_source_path(source_path: str) -> Path | None:
    try:
        base = hive_cloud_deploy.PUBLIC_ROOT.resolve()
        resolved = Path(source_path).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if not str(resolved).startswith(str(base)):
        return None
    if not resolved.is_dir():
        return None
    return resolved


def _validate_production_path(production_path: str, domain: str) -> bool:
    try:
        expected = hive_production_deploy.production_path_for(domain)
    except ValueError:
        return False
    return (production_path or "").rstrip("/") == expected.rstrip("/")


def _nginx_server_block(domain: str, www_domain: str, production_path: str) -> str:
    server_names = domain
    if www_domain:
        server_names = f"{domain} {www_domain}"
    return f"""server {{
    listen 80;
    listen [::]:80;
    server_name {server_names};

    root {production_path};
    index index.html;

    gzip on;
    gzip_vary on;
    gzip_min_length 256;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {{
        try_files $uri $uri/ /index.html;
    }}

    location ~* \\.(?:css|js|jpg|jpeg|png|gif|ico|svg|webp|woff2?)$ {{
        expires 7d;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }}
}}"""


def generate_apply_script(
    *,
    domain: str,
    www_domain: str,
    source_path: str,
    target_path: str,
    nginx_available: str,
    nginx_enabled: str,
) -> str:
    nginx_block = _nginx_server_block(domain, www_domain, target_path)
    certbot_domains = f"-d {domain}"
    if www_domain:
        certbot_domains += f" -d {www_domain}"
    return f"""#!/usr/bin/env bash
# HIVE Production Apply Script — generated, review before running as root
set -euo pipefail

DOMAIN={_bash_quote(domain)}
WWW_DOMAIN={_bash_quote(www_domain)}
SOURCE_PATH={_bash_quote(source_path)}
TARGET_PATH={_bash_quote(target_path)}
NGINX_AVAILABLE={_bash_quote(nginx_available)}
NGINX_ENABLED={_bash_quote(nginx_enabled)}

mkdir -p "$TARGET_PATH"
rsync -a --delete "$SOURCE_PATH"/ "$TARGET_PATH"/
chown -R www-data:www-data "$TARGET_PATH"

cat > "$NGINX_AVAILABLE" <<'NGINXEOF'
{nginx_block}
NGINXEOF

ln -sfn "$NGINX_AVAILABLE" "$NGINX_ENABLED"
nginx -t
systemctl reload nginx

# SSL — run manually after DNS is live:
# certbot --nginx {certbot_domains}
# systemctl reload nginx
"""


def apply_script_status(project: dict[str, Any]) -> dict[str, Any]:
    stored = (project.get("metadata") or {}).get("hive_production_apply_script") or {}
    plan = (project.get("metadata") or {}).get("hive_production_deploy") or {}
    return {
        "success": True,
        "project_id": project.get("id"),
        "status": stored.get("status"),
        "domain": plan.get("domain") or stored.get("domain"),
        "created_at": stored.get("created_at"),
        "requires_root": stored.get("requires_root", True),
        "error": stored.get("error"),
    }


def generate_production_apply_script(project_id: str, project: dict[str, Any]) -> dict[str, Any]:
    pid = (project_id or "").strip()
    meta = project.get("metadata") or {}
    plan = meta.get("hive_production_deploy") or {}

    if plan.get("status") != "planned":
        return {
            "success": False,
            "status": "script_failed",
            "error": "production_plan_required",
            "project_id": pid,
        }

    domain_raw = plan.get("domain") or ""
    try:
        domain = hive_production_deploy.sanitize_domain(domain_raw)
    except ValueError as exc:
        return {
            "success": False,
            "status": "script_failed",
            "error": str(exc),
            "project_id": pid,
        }

    binding = meta.get("domain_binding") or {}
    www_domain = binding.get("www_domain") or ""
    if www_domain:
        try:
            hive_production_deploy.sanitize_domain(www_domain.removeprefix("www."))
        except ValueError:
            www_domain = ""

    source_path = plan.get("source_path") or ""
    production_path = plan.get("production_path") or ""
    if not _secure_source_path(source_path):
        return {
            "success": False,
            "status": "script_failed",
            "error": "invalid_source_path",
            "project_id": pid,
        }
    if not _validate_production_path(production_path, domain):
        return {
            "success": False,
            "status": "script_failed",
            "error": "invalid_production_path",
            "project_id": pid,
        }

    nginx_available = hive_production_deploy.nginx_config_path_for(domain)
    nginx_enabled = f"/etc/nginx/sites-enabled/{domain}"
    script = generate_apply_script(
        domain=domain,
        www_domain=www_domain if www_domain else "",
        source_path=str(_secure_source_path(source_path)),
        target_path=production_path,
        nginx_available=nginx_available,
        nginx_enabled=nginx_enabled,
    )
    created_at = _now()
    return {
        "success": True,
        "project_id": pid,
        "status": "script_ready",
        "domain": domain,
        "script": script,
        "created_at": created_at,
        "requires_root": True,
        "manual_steps": list(MANUAL_STEPS),
        "source_path": str(_secure_source_path(source_path)),
        "production_path": production_path,
        "nginx_config_path": nginx_available,
    }
