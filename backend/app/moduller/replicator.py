"""
The Replicator V3 — 301 redirect domain yönlendirici.
DNS (Cloudflare) + SSL (certbot) + Nginx 301 → ana site.
VPS komutları SSH ile çalıştırılır.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any
import requests

from app import config

logger = logging.getLogger("hive.replicator")

STATE_FILE = Path(__file__).resolve().parent.parent / "replicator_state.json"
_lock = threading.Lock()


def _env(key: str, default: str = "") -> str:
    return config.get(key, default) or os.environ.get(key, default)


class SiteReplicator:
    def __init__(self) -> None:
        self.source_domain = _env("REPLICATOR_TARGET", "balkutusu.com").replace("https://", "").replace("http://", "").strip("/")
        self.vps_ip = _env("VPS_IP", _env("VPS_HOST", "13.140.138.135"))
        self.vps_host = _env("VPS_HOST", "13.140.138.135")
        self.vps_user = _env("VPS_SSH_USER", "root")
        self.vps_pass = _env("VPS_SSH_PASS", "")
        self.cf_token = _env("CLOUDFLARE_API_TOKEN", "")
        self.cf_zone_id = _env("CLOUDFLARE_ZONE_ID", "")
        self.cert_email = _env("REPLICATOR_EMAIL", "admin@balkutusu.com")
        self.results: list[dict[str, Any]] = []
        self.is_running = False
        self._load_state()

    def _load_state(self) -> None:
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.results = data.get("results", [])
                self.is_running = bool(data.get("is_running", False))
            except (json.JSONDecodeError, OSError):
                pass

    def _save_state(self) -> None:
        try:
            STATE_FILE.write_text(
                json.dumps({"results": self.results, "is_running": self.is_running}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("replicator state yazılamadı: %s", e)

    @staticmethod
    def normalize_domain(raw: str) -> str:
        d = raw.strip().lower()
        d = re.sub(r"^https?://", "", d)
        d = d.split("/")[0].split(":")[0]
        return d.strip(".")

    def ssh_run(self, cmd: str, timeout: int = 180) -> tuple[int, str, str]:
        target = f"{self.vps_user}@{self.vps_host}"
        if self.vps_pass:
            full = [
                "sshpass", "-p", self.vps_pass,
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "PreferredAuthentications=password",
                "-o", "PubkeyAuthentication=no",
                target, cmd,
            ]
        else:
            full = ["ssh", "-o", "StrictHostKeyChecking=no", target, cmd]
        try:
            r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 1, "", "SSH zaman aşımı"
        except FileNotFoundError as e:
            return 1, "", f"SSH aracı bulunamadı: {e}"

    def ssh_write_file(self, remote_path: str, content: str) -> tuple[bool, str]:
        b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        code, out, err = self.ssh_run(
            f"mkdir -p $(dirname {remote_path}) && echo '{b64}' | base64 -d > {remote_path}"
        )
        if code != 0:
            return False, err or out or "Dosya yazılamadı"
        return True, ""

    def _cf_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.cf_token}",
            "Content-Type": "application/json",
        }

    def _cf_find_zone_id(self, domain: str) -> str | None:
        if not self.cf_token:
            return self.cf_zone_id or None
        try:
            r = requests.get(
                "https://api.cloudflare.com/client/v4/zones",
                headers=self._cf_headers(),
                params={"name": domain, "status": "active"},
                timeout=30,
            )
            data = r.json()
            if data.get("success") and data.get("result"):
                return data["result"][0]["id"]
        except requests.RequestException as e:
            logger.error("Cloudflare zone lookup: %s", e)
        return self.cf_zone_id or None

    def _cf_ensure_a_record(self, zone_id: str, record_name: str, ip: str) -> tuple[bool, str]:
        """@ veya www için A kaydı oluştur/güncelle."""
        try:
            list_r = requests.get(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                headers=self._cf_headers(),
                params={"type": "A", "name": record_name},
                timeout=30,
            )
            existing = list_r.json().get("result", [])
            payload = {"type": "A", "name": record_name, "content": ip, "ttl": 1, "proxied": True}
            if existing:
                rec_id = existing[0]["id"]
                r = requests.put(
                    f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rec_id}",
                    headers=self._cf_headers(),
                    json=payload,
                    timeout=30,
                )
            else:
                r = requests.post(
                    f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                    headers=self._cf_headers(),
                    json=payload,
                    timeout=30,
                )
            body = r.json()
            if body.get("success"):
                return True, ""
            return False, str(body.get("errors", body))
        except requests.RequestException as e:
            return False, str(e)

    def setup_dns(self, target_domain: str) -> tuple[bool, str]:
        if not self.cf_token:
            return True, "Cloudflare token yok — DNS atlandı (manuel A kaydı gerekebilir)"
        zone_id = self._cf_find_zone_id(target_domain)
        if not zone_id:
            return False, f"Cloudflare zone bulunamadı: {target_domain}"
        ok_root, err_root = self._cf_ensure_a_record(zone_id, target_domain, self.vps_ip)
        if not ok_root:
            return False, f"A kaydı (@): {err_root}"
        ok_www, err_www = self._cf_ensure_a_record(zone_id, f"www.{target_domain}", self.vps_ip)
        if not ok_www:
            return False, f"A kaydı (www): {err_www}"
        return True, "DNS A kayıtları güncellendi"

    def create_nginx_http_bootstrap(self, target_domain: str) -> tuple[bool, str]:
        """Certbot öncesi geçici HTTP vhost."""
        config = f"""# HIVE Replicator bootstrap — {target_domain}
server {{
    listen 80;
    listen [::]:80;
    server_name {target_domain} www.{target_domain};
    root /var/www/html;
    location /.well-known/acme-challenge/ {{ allow all; }}
    location / {{ try_files $uri =404; }}
}}
"""
        path = f"/etc/nginx/sites-available/replicator-{target_domain}"
        ok, err = self.ssh_write_file(path, config)
        if not ok:
            return False, err
        code, out, err = self.ssh_run(f"ln -sf {path} /etc/nginx/sites-enabled/replicator-{target_domain}")
        if code != 0:
            return False, err or out
        return self.reload_nginx()

    def setup_ssl(self, target_domain: str) -> tuple[bool, str]:
        ok, err = self.create_nginx_http_bootstrap(target_domain)
        if not ok:
            return False, f"HTTP bootstrap: {err}"
        cmd = (
            f"certbot certonly --nginx -d {target_domain} -d www.{target_domain} "
            f"--non-interactive --agree-tos --email {self.cert_email} "
            f"--keep-until-expiring 2>&1 || "
            f"certbot certonly --webroot -w /var/www/html -d {target_domain} -d www.{target_domain} "
            f"--non-interactive --agree-tos --email {self.cert_email} 2>&1"
        )
        code, out, err = self.ssh_run(cmd, timeout=300)
        combined = (out + "\n" + err).strip()
        if code == 0 or "Certificate not yet due for renewal" in combined or "Successfully received certificate" in combined:
            return True, combined[-200:] if combined else "SSL OK"
        return False, combined[-400:] or "SSL sertifikası alınamadı"

    def create_nginx_redirect(self, target_domain: str) -> tuple[bool, str]:
        target_url = f"https://{self.source_domain}"
        config = f"""# HIVE Replicator V3 — {target_domain}
server {{
    listen 80;
    listen [::]:80;
    server_name {target_domain} www.{target_domain};
    return 301 {target_url}$request_uri;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {target_domain} www.{target_domain};

    ssl_certificate /etc/letsencrypt/live/{target_domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{target_domain}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    return 301 {target_url}$request_uri;
}}
"""
        path = f"/etc/nginx/sites-available/replicator-{target_domain}"
        ok, err = self.ssh_write_file(path, config)
        if not ok:
            return False, err
        code, out, err = self.ssh_run(
            f"ln -sf {path} /etc/nginx/sites-enabled/replicator-{target_domain}"
        )
        if code != 0:
            return False, err or out
        return True, ""

    def reload_nginx(self) -> tuple[bool, str]:
        code, out, err = self.ssh_run("nginx -t && systemctl reload nginx")
        if code != 0:
            return False, (err or out)[:400]
        return True, ""

    def test_redirect(self, target_domain: str) -> tuple[bool, str]:
        for scheme in ("https", "http"):
            url = f"{scheme}://{target_domain}/"
            try:
                r = requests.get(url, allow_redirects=False, timeout=15, headers={"User-Agent": "HIVE-Replicator/3.0"})
                if r.status_code in (301, 302, 307, 308):
                    loc = r.headers.get("Location", "")
                    if self.source_domain in loc:
                        return True, f"{scheme}: {r.status_code} → {loc}"
            except requests.RequestException:
                continue
        return False, "301 yanıtı veya hedef Location doğrulanamadı"

    def _update_result(self, index: int, **kwargs: Any) -> None:
        with _lock:
            if 0 <= index < len(self.results):
                self.results[index].update(kwargs)
                self._save_state()

    def redirect_domain(self, target_domain: str, index: int) -> None:
        try:
            self._update_result(index, status="processing", error=None, step="dns")

            if target_domain == self.source_domain or target_domain.endswith(f".{self.source_domain}"):
                self._update_result(index, status="failed", error="Ana domain yönlendirilemez")
                return

            ok, msg = self.setup_dns(target_domain)
            if not ok:
                self._update_result(index, status="failed", error=f"DNS: {msg}")
                return
            self._update_result(index, status="processing", step="dns_done", detail=msg)

            time.sleep(3)

            self._update_result(index, status="processing", step="ssl")
            ok, msg = self.setup_ssl(target_domain)
            if not ok:
                self._update_result(index, status="failed", error=f"SSL: {msg}")
                return

            self._update_result(index, status="processing", step="nginx")
            ok, msg = self.create_nginx_redirect(target_domain)
            if not ok:
                self._update_result(index, status="failed", error=f"Nginx: {msg}")
                return

            ok, msg = self.reload_nginx()
            if not ok:
                self._update_result(index, status="failed", error=f"Nginx reload: {msg}")
                return

            self._update_result(index, status="processing", step="test")
            ok, msg = self.test_redirect(target_domain)
            if not ok:
                self._update_result(index, status="failed", error=f"Test: {msg}")
                return

            self._update_result(index, status="completed", error=None, detail=msg)
        except Exception as e:
            logger.exception("redirect_domain %s", target_domain)
            self._update_result(index, status="failed", error=str(e))

    def _run_all_sync(self, domains: list[str]) -> None:
        try:
            for i, domain in enumerate(domains):
                self.redirect_domain(domain, i)
        finally:
            with _lock:
                self.is_running = False
                self._save_state()

    def start_redirect_all(self, domains: list[str]) -> dict[str, Any]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in domains:
            d = self.normalize_domain(raw)
            if d and d not in seen:
                seen.add(d)
                cleaned.append(d)
        if not cleaned:
            return {"success": False, "error": "Geçerli domain bulunamadı"}

        with _lock:
            if self.is_running:
                return {"success": False, "error": "Zaten bir yönlendirme işlemi çalışıyor"}
            self.is_running = True
            self.results = [{"domain": d, "status": "pending", "error": None, "step": None} for d in cleaned]
            self._save_state()

        thread = threading.Thread(target=self._run_all_sync, args=(cleaned,), daemon=True)
        thread.start()

        return {
            "success": True,
            "message": f"{len(cleaned)} domain 301 yönlendirmeye başlandı → {self.source_domain}",
            "total": len(cleaned),
            "target": self.source_domain,
        }

    def get_status(self) -> dict[str, Any]:
        with _lock:
            results = list(self.results)
            running = self.is_running
        terminal = {"completed", "failed"}
        completed = bool(results) and all(r.get("status") in terminal for r in results) and not running
        return {
            "results": results,
            "completed": completed,
            "is_running": running,
            "target": self.source_domain,
            "vps_ip": self.vps_ip,
        }


replicator = SiteReplicator()
