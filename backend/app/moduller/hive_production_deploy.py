"""
HIVE V3 Production Deploy — domain binding, deploy plan, nginx preview (no shell/sudo).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

PRODUCTION_WEB_ROOT = "/var/www/hive-sites"
NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"

_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def sanitize_domain(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s:
        raise ValueError("empty_domain")
    if "://" in s:
        s = s.split("://", 1)[1]
    if "/" in s or "?" in s or "#" in s:
        raise ValueError("path_not_allowed")
    if ":" in s:
        host, _, port = s.rpartition(":")
        if port.isdigit():
            s = host
        else:
            raise ValueError("invalid_domain")
    s = s.rstrip(".")
    if not _DOMAIN_RE.match(s):
        raise ValueError("invalid_domain")
    return s


def production_path_for(domain: str) -> str:
    return f"{PRODUCTION_WEB_ROOT}/{sanitize_domain(domain)}"


def nginx_config_path_for(domain: str) -> str:
    return f"{NGINX_SITES_AVAILABLE}/{sanitize_domain(domain)}"


def bind_domain(domain: str, *, include_www: bool = True) -> dict[str, Any]:
    clean = sanitize_domain(domain)
    www_domain = f"www.{clean}" if include_www else ""
    created_at = _now()
    return {
        "success": True,
        "domain": clean,
        "www_domain": www_domain,
        "target_type": "hive_cloud",
        "status": "configured",
        "ssl_status": "pending",
        "created_at": created_at,
    }


def domain_status(project: dict[str, Any]) -> dict[str, Any]:
    stored = (project.get("metadata") or {}).get("domain_binding") or {}
    return {
        "success": True,
        "project_id": project.get("id"),
        "domain": stored.get("domain"),
        "www_domain": stored.get("www_domain"),
        "target_type": stored.get("target_type"),
        "status": stored.get("status"),
        "ssl_status": stored.get("ssl_status"),
        "created_at": stored.get("created_at"),
    }


def production_deploy_status(project: dict[str, Any]) -> dict[str, Any]:
    stored = (project.get("metadata") or {}).get("hive_production_deploy") or {}
    return {
        "success": True,
        "project_id": project.get("id"),
        "status": stored.get("status"),
        "domain": stored.get("domain"),
        "production_path": stored.get("production_path"),
        "source_path": stored.get("source_path"),
        "nginx_config_path": stored.get("nginx_config_path"),
        "live_url": stored.get("live_url"),
        "planned_at": stored.get("planned_at"),
        "error": stored.get("error"),
    }


def generate_nginx_config(domain: str, www_domain: str, production_path: str) -> str:
    server_names = domain
    if www_domain:
        server_names = f"{domain} {www_domain}"
    return f"""# HIVE Production Deploy — nginx preview (not applied)
# SSL: run certbot after DNS points to this server
#   certbot --nginx -d {domain}{f" -d {www_domain}" if www_domain else ""}

server {{
    listen 80;
    listen [::]:80;
    server_name {server_names};

    root {production_path};
    index index.html;

    # gzip basic
    gzip on;
    gzip_vary on;
    gzip_min_length 256;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # security headers basic
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

    # SSL placeholder — uncomment after certbot
    # listen 443 ssl http2;
    # listen [::]:443 ssl http2;
    # ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
}}
"""


def nginx_preview(project: dict[str, Any]) -> dict[str, Any]:
    meta = project.get("metadata") or {}
    binding = meta.get("domain_binding") or {}
    plan = meta.get("hive_production_deploy") or {}

    domain = binding.get("domain") or plan.get("domain")
    if not domain:
        return {"success": False, "error": "domain_binding_required", "project_id": project.get("id")}

    production_path = plan.get("production_path") or production_path_for(domain)
    www_domain = binding.get("www_domain") or ""
    config = generate_nginx_config(domain, www_domain, production_path)
    return {
        "success": True,
        "project_id": project.get("id"),
        "domain": domain,
        "config": config,
    }


def plan_production_deploy(project_id: str, project: dict[str, Any]) -> dict[str, Any]:
    pid = (project_id or "").strip()
    meta = project.get("metadata") or {}

    cloud = meta.get("hive_cloud_deploy") or {}
    if cloud.get("status") != "deployed":
        return {
            "success": False,
            "status": "plan_failed",
            "error": "local_deploy_required",
            "project_id": pid,
        }

    binding = meta.get("domain_binding") or {}
    if binding.get("status") != "configured" or not binding.get("domain"):
        return {
            "success": False,
            "status": "plan_failed",
            "error": "domain_binding_required",
            "project_id": pid,
        }

    domain = binding["domain"]
    source_path = cloud.get("deploy_path") or ""
    if not source_path:
        return {
            "success": False,
            "status": "plan_failed",
            "error": "source_path_missing",
            "project_id": pid,
        }

    production_path = production_path_for(domain)
    planned_at = _now()
    return {
        "success": True,
        "project_id": pid,
        "status": "planned",
        "domain": domain,
        "production_path": production_path,
        "source_path": source_path,
        "nginx_config_path": nginx_config_path_for(domain),
        "live_url": f"https://{domain}",
        "planned_at": planned_at,
    }
