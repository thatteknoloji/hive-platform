import os

import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def get_github_token() -> str:
    return os.getenv("GITHUB_TOKEN", "").strip()


def _headers() -> dict[str, str]:
    token = get_github_token()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def github_repos() -> dict:
    if not get_github_token():
        return {"success": False, "error": "GITHUB_TOKEN not configured", "repos": []}
    try:
        resp = requests.get(
            "https://api.github.com/user/repos",
            headers=_headers(),
            params={"per_page": 50, "sort": "updated"},
            timeout=30,
        )
        resp.raise_for_status()
        repos = [
            {"name": item.get("full_name"), "url": item.get("html_url"), "private": item.get("private")}
            for item in resp.json()
        ]
        return {"success": True, "repos": repos, "count": len(repos)}
    except Exception as exc:
        return {"success": False, "error": str(exc), "repos": []}


def github_create_gist(
    filename: str,
    content: str,
    description: str = "HIVE config backup",
    public: bool = False,
) -> dict:
    if not get_github_token():
        return {"success": False, "error": "GITHUB_TOKEN not configured"}
    try:
        resp = requests.post(
            "https://api.github.com/gists",
            headers=_headers(),
            json={
                "description": description,
                "public": public,
                "files": {filename or "hive_config_backup.json": {"content": content or ""}},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"success": True, "gist_url": data.get("html_url"), "id": data.get("id")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
