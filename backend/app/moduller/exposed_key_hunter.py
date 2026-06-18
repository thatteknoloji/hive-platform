import json
import os
import re
import requests
from datetime import datetime
from typing import List, Dict
from urllib.parse import quote


class ExposedKeyHunter:
    KEY_PATTERNS = {
        "OpenAI API Key": r"sk-[A-Za-z0-9]{20,}",
        "AWS Access Key": r"AKIA[0-9A-Z]{16}",
        "AWS Secret Key": r"(?i)aws.?secret.?access.?key[^a-zA-Z0-9]+[A-Za-z0-9\/+=]{40}",
        "GitHub Token": r"ghp_[A-Za-z0-9]{36}",
        "GitHub Old Token": r"gho_[A-Za-z0-9]{36}",
        "Stripe Live Key": r"sk_live_[A-Za-z0-9]{24,}",
        "Stripe Test Key": r"sk_test_[A-Za-z0-9]{24,}",
        "Google API Key": r"AIza[0-9A-Za-z\-_]{35}",
        "Slack Token": r"xox[baprs]-[A-Za-z0-9\-]{10,}",
        "JWT Token": r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
        "Private SSH Key": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "Heroku API Key": r"h[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
        "Discord Bot Token": r"[A-Za-z0-9_\-]{24}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27}",
        "npm Token": r"npm_[A-Za-z0-9]{36}",
    }

    def __init__(self):
        self.github_token = self._resolve_token()
        self.reports_dir = os.path.join(os.path.dirname(__file__), "../../reports")
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({"Authorization": f"token {self.github_token}"})

    def _resolve_token(self):
        for var in ["KF_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"]:
            val = os.getenv(var)
            if val:
                return val
        try:
            from app.moduller.api_key_manager import get_key
            val = get_key("kf_github")
            if val:
                return val
            val = get_key("github")
            if val:
                return val
        except Exception:
            pass
        try:
            import app.config as cfg
            for key in ["KF_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"]:
                val = cfg.get(key)
                if val:
                    return val
        except Exception:
            pass
        return None

    def scan(self, query: str, limit: int = 50) -> List[Dict]:
        valid_keys = []
        seen_keys = set()
        all_items = []
        seen_urls = set()

        if not self.github_token:
            return [{"type": "error", "message": "GitHub token bulunamadı. KF_GITHUB_TOKEN veya GITHUB_TOKEN girin."}]

        try:
            env_patterns = [
                "ghp_ filename:.env",
                "sk_live_ filename:.env",
                "AKIA filename:.env",
                "filename:config ghp_",
                "filename:config sk_live_",
                "filename:config AKIA",
            ]
            generic = query.lower() in ["", "key", "token", "secret", "api_key", "apikey",
                                         "openai", "aws", "github", "stripe", "slack", "heroku"]
            if not generic and not any(query.startswith(p) for p in ["ghp_", "sk_live_", "AKIA", "sk-", "xoxb-", "npm_"]):
                env_patterns = [f"{query} filename:.env", f"{query} filename:config"]

            per_q = max(5, limit // max(len(env_patterns), 1))
            for pat in env_patterns:
                try:
                    url = f"https://api.github.com/search/code?q={quote(pat)}&per_page={per_q}&sort=indexed&order=desc"
                    resp = self.session.get(url, timeout=30)
                    if resp.status_code == 200:
                        for item in resp.json().get("items", []):
                            u = item.get("url", "")
                            if u not in seen_urls:
                                seen_urls.add(u)
                                all_items.append(item)
                except Exception:
                    continue

            for item in all_items[:limit]:
                repo_url = item.get("repository", {}).get("html_url", "")
                file_path = item.get("path", "")

                content = self._get_file_content(item)
                if not content:
                    continue

                for key_type, pattern in self.KEY_PATTERNS.items():
                    matches = list(set(re.findall(pattern, content)))
                    for match in matches:
                        dedup_key = f"{key_type}:{match[:20]}"
                        if dedup_key in seen_keys:
                            continue
                        seen_keys.add(dedup_key)

                        valid_keys.append({
                            "type": key_type,
                            "key_masked": self._mask_key(match),
                            "repo_url": repo_url,
                            "file_path": file_path,
                            "line": self._find_line(content, match),
                            "is_valid": True
                        })

        except requests.exceptions.Timeout:
            return [{"type": "error", "message": "GitHub API timeout (30s)"}]
        except Exception as e:
            return [{"type": "error", "message": "Hata: " + str(e)[:200]}]

        if valid_keys:
            os.makedirs(self.reports_dir, exist_ok=True)
            report_file = f"{self.reports_dir}/scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, "w") as f:
                json.dump(valid_keys, f, indent=2)

        return valid_keys

    def _get_file_content(self, item: dict) -> str:
        candidates = []
        html = item.get("html_url", "")
        if html:
            candidates.append(html.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/"))
        full = item.get("repository", {}).get("full_name", "")
        pth = item.get("path", "")
        if full and pth:
            candidates.append(f"https://raw.githubusercontent.com/{full}/main/{pth}")
            candidates.append(f"https://raw.githubusercontent.com/{full}/master/{pth}")
        api = item.get("url", "")
        if api:
            candidates.append(api)
        for url in candidates:
            try:
                hdrs = {}
                if "api.github.com" in url:
                    hdrs["Accept"] = "application/vnd.github.raw+json"
                resp = self.session.get(url, headers=hdrs, timeout=10)
                if resp.status_code == 200 and len(resp.text) > 20:
                    return resp.text
            except Exception:
                continue
        return ""

    def _find_line(self, content: str, match: str) -> int:
        for i, line in enumerate(content.split("\n"), 1):
            if match in line:
                return i
        return 0

    def _mask_key(self, key: str) -> str:
        if not key:
            return "***"
        if len(key) > 12:
            return key[:8] + "..." + key[-4:]
        return "***"


hunter_instance = ExposedKeyHunter()
