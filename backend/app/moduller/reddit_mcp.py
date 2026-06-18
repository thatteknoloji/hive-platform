"""
Reddirect MCP — Reddit stdio köprüsü (jeebus87/reddirect)

REDDIT_USERNAME / REDDIT_PASSWORD .env'den okunur (yazma işlemleri için zorunlu).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app import config

logger = logging.getLogger("hive.reddit_mcp")

REDDIRECT_JS = (
    Path(__file__).resolve().parent.parent.parent
    / "mcp-servers"
    / "reddirect-src"
    / "dist"
    / "index.js"
)


def _reddit_credentials() -> tuple[str, str]:
    username = (config.get("REDDIT_USERNAME") or "").strip()
    password = (config.get("REDDIT_PASSWORD") or "").strip()
    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail="REDDIT_USERNAME ve REDDIT_PASSWORD backend/.env dosyasında tanımlı olmalı",
        )
    return username, password


class RedditMCP:
    """Reddirect MCP sunucusu ile stdio JSON-RPC iletişimi."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        self._req_id = 0
        self._initialized = False

    def _subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        user = (config.get("REDDIT_USERNAME") or "").strip()
        pwd = (config.get("REDDIT_PASSWORD") or "").strip()
        if user:
            env["REDDIT_USERNAME"] = user
        if pwd:
            env["REDDIT_PASSWORD"] = pwd
        return env

    def _ensure_server(self) -> None:
        if not REDDIRECT_JS.exists():
            raise HTTPException(
                status_code=503,
                detail=f"reddirect bulunamadı: {REDDIRECT_JS}. mcp-servers/reddirect-src build edin.",
            )
        if self._proc and self._proc.poll() is None and self._initialized:
            return
        self._start()

    def _start(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass
        try:
            env = self._subprocess_env()
        except Exception:
            env = os.environ.copy()
        self._proc = subprocess.Popen(
            ["node", str(REDDIRECT_JS)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        self._initialized = False
        res = self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "hive", "version": "3.0"},
        })
        if not res.get("result"):
            err = self._read_stderr()
            raise HTTPException(status_code=502, detail=f"reddirect başlatılamadı: {err}")
        self._notify("notifications/initialized", {})
        self._initialized = True

    def _read_stderr(self) -> str:
        if not self._proc or not self._proc.stderr:
            return ""
        try:
            import select
            if select.select([self._proc.stderr], [], [], 0.1)[0]:
                return self._proc.stderr.read(500) or ""
        except Exception:
            pass
        return ""

    def _notify(self, method: str, params: dict) -> None:
        if not self._proc or not self._proc.stdin:
            return
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    def _request(self, method: str, params: dict | None = None) -> dict[str, Any]:
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            raise HTTPException(status_code=502, detail="MCP process yok")
        self._req_id += 1
        rid = self._req_id
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": rid}
        if params is not None:
            msg["params"] = params
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            self._initialized = False
            raise HTTPException(status_code=502, detail="reddirect yanıt vermedi")
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            raise HTTPException(status_code=502, detail=f"Geçersiz MCP yanıtı: {line[:200]}")
        if data.get("id") != rid:
            line2 = self._proc.stdout.readline()
            if line2:
                data = json.loads(line2)
        if data.get("error"):
            raise HTTPException(status_code=422, detail=data["error"].get("message", str(data["error"])))
        return data

    def _call_tool(self, name: str, arguments: dict | None = None) -> Any:
        with self._lock:
            self._ensure_server()
            try:
                data = self._request("tools/call", {"name": name, "arguments": arguments or {}})
            except HTTPException:
                self._initialized = False
                self._ensure_server()
                data = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        result = data.get("result", {})
        content = result.get("content", [])
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        if not texts:
            return result
        combined = "\n".join(texts)
        try:
            parsed = json.loads(combined)
            if isinstance(parsed, dict) and result.get("isError"):
                parsed["isError"] = True
            return parsed
        except json.JSONDecodeError:
            return {"raw": combined, "isError": result.get("isError", False)}

    def _ensure_write_session(self) -> dict[str, Any]:
        """Yazma işlemi öncesi credential + oturum kontrolü."""
        username, _ = _reddit_credentials()
        session = self.check_session()
        if isinstance(session, dict):
            can_write = session.get("can_write") or session.get("status") == "authenticated"
            if can_write:
                return session
        raise HTTPException(
            status_code=401,
            detail=(
                f"Reddit yazma oturumu yok (u/{username}). "
                "Önce POST /api/reddit/authorize ile tarayıcıda giriş yapın."
            ),
        )

    def check_session(self) -> dict[str, Any]:
        return self._call_tool("check_session")

    def authorize(self) -> dict[str, Any]:
        _reddit_credentials()
        return self._call_tool("authorize")

    def search(self, query: str, limit: int = 10, subreddit: str = "") -> dict[str, Any]:
        args: dict[str, Any] = {"query": query, "limit": min(max(limit, 1), 100)}
        if subreddit:
            args["subreddit"] = subreddit.replace("r/", "").strip()
        return self._call_tool("search_reddit", args)

    def browse_subreddit(self, subreddit: str, limit: int = 10, sort: str = "hot") -> dict[str, Any]:
        return self._call_tool("browse_subreddit", {
            "subreddit": subreddit.replace("r/", "").strip(),
            "sort": sort,
            "limit": min(max(limit, 1), 100),
        })

    def get_post(self, post_url: str) -> dict[str, Any]:
        return self._call_tool("get_post", {"url": post_url})

    def submit_comment(self, post_url: str, text: str) -> dict[str, Any]:
        """Gerçek Reddit yorumu — reddirect MCP reply aracı."""
        if not post_url.strip() or not text.strip():
            raise HTTPException(status_code=400, detail="post_url ve text gerekli")
        self._ensure_write_session()
        result = self._call_tool("reply", {"url": post_url.strip(), "text": text.strip()})
        if isinstance(result, dict) and (result.get("isError") or result.get("success") is False):
            raise HTTPException(status_code=422, detail=result.get("error") or result.get("raw") or "Yorum gönderilemedi")
        return {"success": True, "result": result, "engine": "reddirect"}

    def submit_post(self, subreddit: str, title: str, text: str) -> dict[str, Any]:
        """Gerçek Reddit postu — reddirect MCP create_post aracı."""
        if not subreddit.strip() or not title.strip():
            raise HTTPException(status_code=400, detail="subreddit ve title gerekli")
        self._ensure_write_session()
        result = self._call_tool("create_post", {
            "subreddit": subreddit.replace("r/", "").strip(),
            "title": title.strip(),
            "type": "text",
            "body": text.strip(),
        })
        if isinstance(result, dict) and (result.get("isError") or result.get("success") is False):
            raise HTTPException(status_code=422, detail=result.get("error") or result.get("raw") or "Post oluşturulamadı")
        return {"success": True, "result": result, "engine": "reddirect"}

    def reply(self, post_url: str, text: str) -> dict[str, Any]:
        return self.submit_comment(post_url, text)

    def create_post(self, subreddit: str, title: str, text: str) -> dict[str, Any]:
        return self.submit_post(subreddit, title, text)

    def list_tools(self) -> list[str]:
        with self._lock:
            self._ensure_server()
            data = self._request("tools/list", {})
        tools = data.get("result", {}).get("tools", [])
        return [t.get("name", "") for t in tools if t.get("name")]


reddit_mcp = RedditMCP()
